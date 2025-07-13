#!/usr/bin/env python3
"""rss_tool.py – Maintain a simple podcast feed (audio + RSS).

Configuration
-------------
The tool now expects **settings.json** in the working directory by default:

```
{
  "tg": {                         # ⚠ not used – kept for future use
    "token": "telegram bot token",
    "chat_id": "chat id"
  },
  "bucket": {
    "endpoint_url": "https://xxx.r2.cloudflarestorage.com",
    "aws_access_key_id": "…",
    "aws_secret_access_key": "…",
    "bucket_name": "my-podcast",
    "bucket_url": "https://pub-xxx.r2.dev/"
  }
}
```

• **bucket** – required when you use `--upload`; if any field is missing the
  script aborts.  
• **tg** – currently ignored (placeholder for notifications).

All previous CLI flags remain; `--bucket-cfg` now defaults to *settings.json* so
most users can omit it.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

###############################################################################
# 1. Utilities and data structures
###############################################################################

def _pubdate(ts: float) -> str:
    return time.strftime("%a, %d %b %Y %H:%M:%S %z", time.localtime(ts))

@dataclass
class AudioFile:
    path: Path
    size: int

    @property
    def object_name(self) -> str:
        return self.path.name

    @property
    def title(self) -> str:
        return self.path.stem.replace("_", " ").replace("-", " ")

###############################################################################
# 2. Local file discovery
###############################################################################

def scan_audio_dir(audio_dir: Path, exts: Sequence[str] = ("m4a",)) -> List[AudioFile]:
    files: List[AudioFile] = []
    for p in audio_dir.rglob("*"):
        if p.is_file() and p.suffix.lower().lstrip(".") in exts:
            files.append(AudioFile(path=p, size=p.stat().st_size))
    return sorted(files, key=lambda af: af.path.stat().st_mtime, reverse=True)

###############################################################################
# 3. RSS generation / update helpers
###############################################################################

RSS_NS_ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", RSS_NS_ITUNES)


def _append_item(channel_el: ET.Element, af: AudioFile, base_url: str):
    item = ET.Element("item")
    ET.SubElement(item, "title").text = af.title
    url = base_url + urllib.parse.quote(af.object_name)
    enc = ET.SubElement(item, "enclosure", {
        "url": url, "length": str(af.size), "type": "audio/mp4",
    })
    ET.SubElement(item, "guid", isPermaLink="true").text = url
    ET.SubElement(item, "pubDate").text = _pubdate(af.path.stat().st_mtime)
    channel_el.append(item)


def _ensure_root(channel_title: str, channel_image: str | None) -> ET.ElementTree:
    root = ET.Element("rss", version="2.0")
    chan = ET.SubElement(root, "channel")
    ET.SubElement(chan, "title").text = channel_title
    if channel_image:
        ET.SubElement(chan, f"{{{RSS_NS_ITUNES}}}image", href=channel_image)
    return ET.ElementTree(root)


def update_rss_file(
    rss_path: Path,
    channel_title: str,
    web_base_url: str,
    audio_files: Iterable[AudioFile],
    channel_image: str | None = None,
) -> List[AudioFile]:
    """Write/append items and return list of newly added AudioFile."""

    if rss_path.exists():
        try:
            tree = ET.parse(rss_path)
            root = tree.getroot()
            channel = root.find("channel")
            if channel is None:
                raise ET.ParseError("<channel> missing")
        except ET.ParseError as e:
            print(f"[WARN] RSS invalid, recreating: {e}")
            tree = _ensure_root(channel_title, channel_image)
            channel = tree.getroot().find("channel")  # type: ignore
    else:
        tree = _ensure_root(channel_title, channel_image)
        channel = tree.getroot().find("channel")  # type: ignore

    present = {Path(e.attrib.get("url", "")).name for e in tree.findall(".//item/enclosure")}

    added: List[AudioFile] = []
    for af in audio_files:
        if af.object_name in present:
            continue
        _append_item(channel, af, web_base_url)
        added.append(af)

    # Write XML
    rss_path.write_text(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" +
        ET.tostring(tree.getroot(), encoding="unicode"),
        encoding="utf-8",
    )
    return added

###############################################################################
# 4. Object‑storage upload helpers (Cloudflare R2, MinIO, etc.)
###############################################################################

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
except ModuleNotFoundError:
    boto3 = None  # type: ignore

DEFAULT_CFG = Path("settings.json")


def build_bucket(cfg_path: Path = DEFAULT_CFG):
    if boto3 is None:
        print("boto3 not found – install it or skip --upload", file=sys.stderr)
        sys.exit(2)
    if not cfg_path.exists():
        print(f"Config file '{cfg_path}' missing", file=sys.stderr)
        sys.exit(1)

    cfg = json.loads(cfg_path.read_text()).get("bucket", {})
    required = ("endpoint_url", "aws_access_key_id", "aws_secret_access_key", "bucket_name", "bucket_url")
    if any(k not in cfg or not cfg[k] for k in required):
        print("Incomplete 'bucket' section in settings.json", file=sys.stderr)
        sys.exit(1)

    s3 = boto3.resource(
        "s3",
        endpoint_url=cfg["endpoint_url"],
        aws_access_key_id=cfg["aws_access_key_id"],
        aws_secret_access_key=cfg["aws_secret_access_key"],
        config=Config(proxies=None),
    )
    return s3.Bucket(cfg["bucket_name"]), cfg["bucket_url"].rstrip("/") + "/"


def upload_paths(bucket, paths: Iterable[Path]):  # type: ignore
    for p in paths:
        try:
            bucket.upload_file(str(p), p.name)
            print(f"[UPLOAD] {p.name} -> {bucket.name}")
        except (BotoCoreError, ClientError) as e:
            print(f"[ERROR] upload {p}: {e}")

###############################################################################
# 5. CLI – orchestrates the functions above
###############################################################################

def _cli_update(args):
    audio_files = scan_audio_dir(args.audio_dir, args.exts)
    if not audio_files:
        print("Nothing to process."); return

    added = update_rss_file(
        rss_path=args.rss,
        channel_title=args.channel_title,
        web_base_url=args.web_url.rstrip("/") + "/",
        audio_files=audio_files,
        channel_image=args.image_url,
    )
    print(f"RSS updated: {len(added)} item(s) added.")

    if args.upload and added:
        bucket, _ = build_bucket(args.bucket_cfg)
        upload_paths(bucket, [*added, args.rss])


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Podcast RSS helper (settings.json aware)")
    sub = p.add_subparsers(dest="cmd", required=True)

    u = sub.add_parser("update", help="scan folder, update RSS, optional upload")
    u.add_argument("--rss", type=Path, required=True)
    u.add_argument("--audio-dir", type=Path, required=True)
    u.add_argument("--channel-title", required=True)
    u.add_argument("--web-url", required=True)
    u.add_argument("--image-url")
    u.add_argument("--exts", nargs="*", default=["m4a"], help="audio extensions")
    u.add_argument("--upload", action="store_true")
    u.add_argument("--bucket-cfg", type=Path, default=DEFAULT_CFG,
                   help="settings.json path (default: settings.json)")
    return p

###############################################################################
# 6. Main entry
###############################################################################

def main(argv: Sequence[str] | None = None):
    # the upload function should be pure for only upload designated types of files
    # it should get a list of the designated types of files in the folder, use the items in the list to update the rss file
    # for each item in list
    # use bucket_url + item file name as rss audio file's access url
    args = _build_parser().parse_args(argv)
    if args.cmd == "update":
        if args.upload and not args.bucket_cfg.exists():
            print(f"Config file '{args.bucket_cfg}' not found", file=sys.stderr)
            sys.exit(1)
        _cli_update(args)


if __name__ == "__main__":
    main()
