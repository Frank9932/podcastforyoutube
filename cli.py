#!/usr/bin/env python3
"""rss_tool.py – Minimal uploader & (optional) RSS helper.

核心逻辑
────────
1. scan_dir()         → 找到指定拓展名的文件列表
2. upload_files()     → 将这些文件上传到 S3‧兼容对象存储
3. update_rss()       → *只有当 exts 包含 "rss" 时才执行*

用法示例
────────
# 只上传 *.m4a（不会动 RSS）
python rss_tool.py update \
    --audio-dir ./assets --rss feed.rss --channel-title "Demo" \
    --upload

# 同时上传 *.m4a 与 feed.rss（因为 --exts m4a rss）
python rss_tool.py update \
    --audio-dir ./assets --rss feed.rss --channel-title "Demo" \
    --exts m4a rss --upload
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
# 1. 通用工具
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
# 2. 扫描目录
###############################################################################

def scan_dir(directory: Path, exts: Sequence[str]) -> List[FileObj]:
    wanted = {e.lower().lstrip(".") for e in exts}
    result: List[FileObj] = []
    for p in directory.rglob("*"):
        if p.is_file() and p.suffix.lower().lstrip(".") in wanted:
            result.append(FileObj(p, p.stat().st_size))
    return sorted(result, key=lambda f: f.path.stat().st_mtime, reverse=True)

###############################################################################
# 3. （可选）RSS 处理
###############################################################################

RSS_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", RSS_NS)

def _new_tree(title: str, image_url: str | None) -> ET.ElementTree:
    root = ET.Element("rss", version="2.0")
    chan = ET.SubElement(root, "channel")
    ET.SubElement(chan, "title").text = title
    if image_url:
        ET.SubElement(chan, f"{{{RSS_NS}}}image", href=image_url)
    return ET.ElementTree(root)

def _append_item(chan: ET.Element, f: FileObj, base_url: str):
    item = ET.SubElement(chan, "item")
    ET.SubElement(item, "title").text = f.title
    url = base_url + urllib.parse.quote(f.key)
    ET.SubElement(item, "enclosure", {
        "url": url,
        "length": str(f.size),
        "type": "audio/mp4",
    })
    ET.SubElement(item, "guid", isPermaLink="true").text = url
    ET.SubElement(item, "pubDate").text = _pubdate(f.path.stat().st_mtime)

def update_rss(
    rss_path: Path,
    channel_title: str,
    base_url: str,
    audio_files: Iterable[FileObj],
    image_url: str | None = None,
):
    # 解析或新建
    if rss_path.exists():
        try:
            tree = ET.parse(rss_path)
            chan = tree.getroot().find("channel")
            if chan is None:
                raise ET.ParseError
        except ET.ParseError:
            tree = _new_tree(channel_title, image_url)
            chan = tree.getroot().find("channel")  # type: ignore
    else:
        tree = _new_tree(channel_title, image_url)
        chan = tree.getroot().find("channel")      # type: ignore

    existing = {Path(e.get("url", "")).name
                for e in tree.getroot().findall(".//item/enclosure")}
    for f in audio_files:
        if f.key not in existing:
            _append_item(chan, f, base_url)

    rss_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n' +
        ET.tostring(tree.getroot(), encoding="unicode"),
        encoding="utf-8",
    )

###############################################################################
# 4. S3 / R2 上传
###############################################################################

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
except ModuleNotFoundError:   # 单元测试可不装 boto3
    boto3 = None  # type: ignore

DEFAULT_CFG = Path("./config/settings.json")

def _load_cfg(path: Path) -> dict:
    if not path.exists():
        print(f"[ERR] 缺少配置文件 {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text())

def build_bucket(cfg_path: Path = DEFAULT_CFG):
    if boto3 is None:
        print("[ERR] 未安装 boto3，无法上传", file=sys.stderr)
        sys.exit(2)
    cfg = _load_cfg(cfg_path).get("bucket", {})
    req = ("endpoint_url", "aws_access_key_id", "aws_secret_access_key",
           "bucket_name", "bucket_url")
    if any(not cfg.get(k) for k in req):
        print("[ERR] settings.json › bucket 配置不完整", file=sys.stderr)
        sys.exit(1)
    s3 = boto3.resource(
        "s3",
        endpoint_url=cfg["endpoint_url"],
        aws_access_key_id=cfg["aws_access_key_id"],
        aws_secret_access_key=cfg["aws_secret_access_key"],
        config=Config(proxies=None),
    )
    return s3.Bucket(cfg["bucket_name"]), cfg["bucket_url"].rstrip("/") + "/"

def upload_files(bucket, files: Iterable[FileObj]):  # type: ignore
    for f in files:
        try:
            bucket.upload_file(str(f.path), f.key)
            print(f"[OK ] 上传 {f.key}")
        except (BotoCoreError, ClientError) as e:
            print(f"[ERR] {f.key}: {e}")

###############################################################################
# 5. CLI
###############################################################################

def _cmd_update(args):
    files = scan_dir(args.audio_dir, args.exts)
    if not files:
        print("目录内未找到指定类型的文件。")
        return

    # 判断是否需要上传
    if args.upload:
        bucket, base_url = build_bucket(args.cfg)
    else:
        if not args.web_url:
            print("--web-url 不能为空（除非使用 --upload）", file=sys.stderr)
            sys.exit(2)
        bucket = None  # type: ignore
        base_url = args.web_url.rstrip("/") + "/"

    # 如果用户把 rss 写进 --exts，则进行 RSS 合并 / 生成
    if "rss" in {e.lower().lstrip(".") for e in args.exts}:
        audio_like = [f for f in files if f.path.suffix.lower() != ".rss"]
        if audio_like:
            update_rss(args.rss, args.channel_title, base_url,
                       audio_like, args.image_url)

    # 执行上传（只传 --exts 里列出的文件）
    if args.upload:
        upload_files(bucket, files)

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Upload audio / update RSS")
    # 所有选项直接加到顶层
    p.add_argument("--audio-dir", type=Path, required=True)
    p.add_argument("--upload", action="store_true", help="push to bucket")
    p.add_argument("--exts", nargs="+", default=["m4a"],
                   help="file suffix list, e.g. m4a rss")
    p.add_argument("--rss", type=Path,
                   help="rss path (required IF you put 'rss' in --exts)")
    p.add_argument("--channel-title",
                   help="podcast title (required when updating rss)")
    p.add_argument("--image-url")
    p.add_argument("--web-url",
                   help="base URL when *not* uploading")
    p.add_argument("--cfg", type=Path, default=DEFAULT_CFG,
                   help="settings.json location")
    return p

def main(argv: Sequence[str] | None = None):
    args = _build_parser().parse_args(argv)
    _cmd_update(args)          # 直接调用即可

if __name__ == "__main__":
    main()
