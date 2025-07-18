#!/usr/bin/env python3
"""rss_tool.py — generate a podcast RSS feed OR upload media files.

Update (Path Policy Enhancement) – 2025‑07‑18
---------------------------------------------
* RSS command now **ignores --rss** (removed) and always targets
  `<audio-dir>/<channel-title>.rss`.
* Incremental update: if that file already exists it is parsed & only new
  audio files (matching --exts) are appended; otherwise a fresh feed is
  created.
* Upload command unchanged (still only uploads, and can optionally include a
  feed if you list it explicitly with --feed-path). For clarity we rename the
  upload option from `--rss` to `--feed-path`.
* Fixed stray newline bug in xml write string and ensured atomic write.

Examples
--------
Generate / update `./shows/My Show.rss` using mp3 files in ./shows:
  python rss_tool.py rss --audio-dir ./shows --channel-title "My Show" \
      --web-url https://cdn.example.com/ --exts mp3

Upload mp3 files and an existing feed file:
  python rss_tool.py upload --audio-dir ./shows --exts mp3 rss \
      --feed-path ./shows/My%20Show.rss
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

###############################################################################
# 1. Helpers & data classes
###############################################################################

def _pubdate(ts: float) -> str:
    return time.strftime("%a, %d %b %Y %H:%M:%S %z", time.localtime(ts))

@dataclass
class FileObj:
    path: Path
    size: int

    @property
    def key(self) -> str:
        return self.path.name

    @property
    def title(self) -> str:
        return self.path.stem.replace("_", " ").replace("-", " ")

###############################################################################
# 2. Directory scanning
###############################################################################

def scan_dir(directory: Path, exts: Sequence[str]) -> List[FileObj]:
    wanted = {e.lower().lstrip('.') for e in exts}
    files: List[FileObj] = []
    for p in directory.rglob('*'):
        if p.is_file() and p.suffix.lower().lstrip('.') in wanted:
            files.append(FileObj(p, p.stat().st_size))
    return sorted(files, key=lambda f: f.path.stat().st_mtime, reverse=True)

###############################################################################
# 3. RSS generation utilities
###############################################################################

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"  # explicit attribute only


def _fresh_tree(title: str, image_url: str) -> ET.ElementTree:
    root = ET.Element('rss', attrib={'version': '2.0', 'xmlns:itunes': ITUNES_NS})
    chan = ET.SubElement(root, 'channel')
    ET.SubElement(chan, 'title').text = title
    ET.SubElement(chan, f'{{{ITUNES_NS}}}image', href=image_url)
    ET.SubElement(chan, 'link').text = image_url.rsplit('/', 2)[0] + '/'
    ET.SubElement(chan, 'language').text = 'en-us'
    ET.SubElement(chan, 'description').text = title
    ET.SubElement(chan, f'{{{ITUNES_NS}}}summary').text = title
    ET.SubElement(chan, f'{{{ITUNES_NS}}}explicit').text = 'no'
    return ET.ElementTree(root)


def _safe_url(base_url: str, filename: str) -> str:
    return base_url + urllib.parse.quote(filename)


def update_rss(
    rss_path: Path,
    channel_title: str,
    base_url: str,
    audio_files: Iterable[FileObj],
    image_file: str = 'img.jpg',
) -> Tuple[int, bool]:
    """Create or update feed safely. Returns (added_count, created_flag)."""
    created = False
    rebuild = False
    if rss_path.exists():
        try:
            tree = ET.parse(rss_path)
            root = tree.getroot()
            if root.tag != 'rss':
                rebuild = True
            chan = root.find('channel')
            if chan is None:
                rebuild = True
            if root.get('xmlns:itunes') != ITUNES_NS:
                root.set('xmlns:itunes', ITUNES_NS)
        except ET.ParseError:
            rebuild = True
        if rebuild:
            created = True
    else:
        created = True

    if created:
        tree = _fresh_tree(channel_title, f'{base_url}{image_file}')
        root = tree.getroot()
        chan = root.find('channel')  # type: ignore[attr-defined]
    else:
        chan = tree.getroot().find('channel')  # type: ignore[attr-defined]

    img = chan.find(f'{{{ITUNES_NS}}}image')
    if img is None:
        img = ET.SubElement(chan, f'{{{ITUNES_NS}}}image')
    img.set('href', f'{base_url}{image_file}')

    existing = {Path(e.get('url', '')).name for e in tree.getroot().findall('.//item/enclosure')}
    added = 0
    for f in audio_files:
        if f.key in existing:
            continue
        item = ET.SubElement(chan, 'item')
        ET.SubElement(item, 'title').text = f.title
        url = _safe_url(base_url, f.key)
        mime = 'audio/mpeg' if f.path.suffix.lower() == '.mp3' else 'audio/mp4'
        ET.SubElement(item, 'enclosure', url=url, length=str(f.size), type=mime)
        ET.SubElement(item, 'guid', isPermaLink='true').text = url
        ET.SubElement(item, 'pubDate').text = _pubdate(f.path.stat().st_mtime)
        added += 1

    xml_text = ('<?xml version="1.0" encoding="UTF-8"?>' +
                ET.tostring(tree.getroot(), encoding='unicode'))
    tmp = rss_path.with_suffix(rss_path.suffix + '.tmp')
    tmp.write_text(xml_text, encoding='utf-8')
    tmp.replace(rss_path)
    return added, created

###############################################################################
# 4. Upload helpers
###############################################################################

try:  # optional dependency
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
except ModuleNotFoundError:
    boto3 = None  # type: ignore

DEFAULT_CFG = Path('./config/settings.json')


def _load_cfg(path: Path) -> dict:
    if not path.exists():
        logging.error('Config file %s not found.', path)
        sys.exit(1)
    return json.loads(path.read_text())


def build_bucket(cfg_path: Path = DEFAULT_CFG):
    if boto3 is None:
        logging.error('boto3 not installed; cannot upload.')
        sys.exit(2)
    cfg = _load_cfg(cfg_path).get('bucket', {})
    need = ('endpoint_url', 'aws_access_key_id', 'aws_secret_access_key', 'bucket_name', 'bucket_url')
    if any(not cfg.get(k) for k in need):
        logging.error('Incomplete bucket configuration.')
        sys.exit(1)
    s3 = boto3.resource(
        's3',
        endpoint_url=cfg['endpoint_url'],
        aws_access_key_id=cfg['aws_access_key_id'],
        aws_secret_access_key=cfg['aws_secret_access_key'],
        config=Config(proxies=None),
    )
    return s3.Bucket(cfg['bucket_name']), cfg['bucket_url'].rstrip('/') + '/'


def upload_files(bucket, items: Iterable[FileObj]):  # type: ignore
    for f in items:
        try:
            bucket.upload_file(str(f.path), f.key)
            logging.info('Uploaded %s', f.key)
        except (BotoCoreError, ClientError) as e:
            logging.error('%s ⇒ %s', f.key, e)

###############################################################################
# 5. CLI command handlers
###############################################################################

def cmd_rss(args):
    audio = scan_dir(args.audio_dir, args.exts)
    logging.info('Found %d candidate audio file(s)', len(audio))
    if not audio:
        logging.warning('No audio files found matching extensions: %s', ','.join(args.exts))
        return
    # Deterministic feed path: <audio-dir>/<channel-title>.rss
    safe_title = args.channel_title.strip().replace('/', '_')
    rss_path = args.audio_dir / f'{safe_title}.rss'
    base_url = args.web_url.rstrip('/') + '/'
    added, created = update_rss(rss_path, args.channel_title, base_url, audio, args.image_file)
    logging.info('%s %s (%d new item%s).', 'Created' if created else 'Updated', rss_path, added, '' if added == 1 else 's')


def cmd_upload(args):
    bucket, _ = build_bucket(args.cfg)
    files = scan_dir(args.audio_dir, args.exts)
    # optional inclusion of feed file when explicitly provided AND listed in exts
    if 'rss' in {e.lower().lstrip('.') for e in args.exts} and args.feed_path:
        if args.feed_path.exists():
            files.append(FileObj(args.feed_path, args.feed_path.stat().st_size))
        else:
            logging.warning('Feed path %s does not exist, skipping.', args.feed_path)
    if not files:
        logging.warning('No matching files to upload.')
        return
    upload_files(bucket, files)

###############################################################################
# 6. Argument parser / entry point
###############################################################################

def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Generate podcast RSS or upload media')
    sub = p.add_subparsers(dest='cmd', required=True)

    r = sub.add_parser('rss', help='build / update feed only')
    r.add_argument('--audio-dir', type=Path, required=True)
    r.add_argument('--channel-title', required=True)
    r.add_argument('--web-url', required=True)
    r.add_argument('--exts', nargs='*', default=['mp3'], help='audio file extensions to include')
    r.add_argument('--image-file', default='img.jpg', help='cover image file name under base URL')

    u = sub.add_parser('upload', help='upload files only')
    u.add_argument('--audio-dir', type=Path, required=True)
    u.add_argument('--exts', nargs='*', default=['mp3'], help='file extensions to upload (include rss to also upload feed)')
    u.add_argument('--feed-path', type=Path, help='existing feed file to upload when "rss" in --exts')
    u.add_argument('--cfg', type=Path, default=DEFAULT_CFG, help='settings.json path')

    return p


def main(argv: Sequence[str] | None = None):
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    args = make_parser().parse_args(argv)
    if args.cmd == 'rss':
        cmd_rss(args)
    elif args.cmd == 'upload':
        cmd_upload(args)
    else:
        raise SystemExit('Unknown command')


if __name__ == '__main__':
    main()
