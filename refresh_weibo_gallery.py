#!/usr/bin/env python3
"""Download recent Weibo images and rebuild the public gallery manifest."""

from __future__ import annotations

import html
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(
    os.environ.get("RAINIE_STATION_ROOT", Path(__file__).resolve().parent)
).resolve()
STATIC = ROOT / "static"
IMAGE_ROOT = STATIC / "img" / "weibo"
MANIFEST = STATIC / "data" / "gallery.json"
COOKIE_FILE = ROOT / "secrets" / "weibo-cookies.txt"
ARCHIVE_FILE = ROOT / "db" / "weibo-download-archive.txt"
GALLERY_DL = ROOT / "venv" / "bin" / "gallery-dl"
LOG_FILE = ROOT / "logs" / "weibo-gallery.log"

ACCOUNTS = {
    "3511727907": "杨丞琳",
    "6409176005": "杨丞琳工作室",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_IMAGES_PER_ACCOUNT = 150
FETCH_SCAN_LIMIT = 200


def configure_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


def download_account(uid: str) -> bool:
    destination = IMAGE_ROOT / uid
    destination.mkdir(parents=True, exist_ok=True)
    account_url = f"https://weibo.com/u/{uid}"
    if uid == "6409176005":
        account_url += "?tabtype=album"
    command = [
        str(GALLERY_DL),
        "--cookies",
        str(COOKIE_FILE),
        "--download-archive",
        str(ARCHIVE_FILE),
        "--write-metadata",
        "--range",
        f"1-{FETCH_SCAN_LIMIT}",
        "--sleep-request",
        "2.0-4.0",
        "-o",
        "extractor.weibo.videos=false",
        "-o",
        "extractor.weibo.livephoto=false",
        "-o",
        "extractor.weibo.retweets=false",
        "-o",
        "extractor.cookies-update=false",
        "-D",
        str(destination),
        account_url,
    ]
    logging.info("Checking %s (%s)", ACCOUNTS[uid], uid)
    result = subprocess.run(command, text=True, capture_output=True)
    if result.stdout.strip():
        logging.info("%s", result.stdout.strip())
    if result.returncode:
        logging.error("%s", result.stderr.strip() or f"gallery-dl exited {result.returncode}")
        return False
    return True


def clean_text(value: object) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:38] + ("…" if len(text) > 38 else "") if text else "微博图片"


def nested(data: dict, *keys: str) -> object:
    current: object = data
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key, "")
    return current


def metadata_for(image: Path) -> dict:
    sidecar = Path(f"{image}.json")
    if not sidecar.exists():
        return {}
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        logging.warning("Ignoring invalid metadata %s: %s", sidecar, error)
        return {}


def parse_record_date(metadata: dict, image: Path) -> datetime:
    status = metadata.get("status") if isinstance(metadata.get("status"), dict) else {}
    value = status.get("date") or status.get("created_at")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    if value:
        normalized = str(value).replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except ValueError:
            pass
    return datetime.fromtimestamp(image.stat().st_mtime)


def prune_to_account_limits() -> int:
    removed = 0
    for uid in ACCOUNTS:
        account_root = IMAGE_ROOT / uid
        images = [
            image
            for image in account_root.rglob("*")
            if image.is_file() and image.suffix.lower() in IMAGE_EXTENSIONS
        ]
        images.sort(
            key=lambda image: (
                parse_record_date(metadata_for(image), image),
                image.name,
            ),
            reverse=True,
        )
        for image in images[MAX_IMAGES_PER_ACCOUNT:]:
            resolved = image.resolve()
            if account_root.resolve() not in resolved.parents:
                raise RuntimeError(
                    f"Refusing to remove file outside account image root: {image}"
                )
            sidecar = Path(f"{image}.json")
            image.unlink()
            if sidecar.exists():
                sidecar.unlink()
            removed += 1
        logging.info(
            "%s retention: kept %d newest images",
            ACCOUNTS[uid],
            min(len(images), MAX_IMAGES_PER_ACCOUNT),
        )
    logging.info("Count-based retention removed %d old images", removed)
    return removed


def build_weibo_records() -> list[dict]:
    records = []
    for image in IMAGE_ROOT.rglob("*"):
        if not image.is_file() or image.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        metadata = metadata_for(image)
        status = metadata.get("status") if isinstance(metadata.get("status"), dict) else {}
        uid = str(
            nested(status, "user", "idstr")
            or nested(status, "user", "id")
            or image.relative_to(IMAGE_ROOT).parts[0]
        )
        if uid not in ACCOUNTS:
            continue
        status_id = str(status.get("idstr") or status.get("id") or image.stem)
        bid = str(status.get("mblogid") or status.get("bid") or "")
        number = str(metadata.get("num") or image.stem.rsplit("_", 1)[-1])
        date_value = status.get("date") or status.get("created_at") or ""
        if isinstance(date_value, (int, float)):
            date_value = datetime.fromtimestamp(date_value).isoformat()
        relative = image.relative_to(STATIC).as_posix()
        width = metadata.get("width")
        height = metadata.get("height")
        records.append(
            {
                "id": f"weibo-{uid}-{status_id}-{number}",
                "title": clean_text(status.get("text_raw") or status.get("text")),
                "source": ACCOUNTS[uid],
                "date": str(date_value)[:10],
                "image": f"/static/{relative}",
                "original": f"/static/{relative}",
                "postUrl": (
                    f"https://weibo.com/{uid}/{bid}"
                    if bid
                    else f"https://weibo.com/u/{uid}"
                ),
                "width": int(width) if isinstance(width, (int, float)) and width > 0 else None,
                "height": int(height) if isinstance(height, (int, float)) and height > 0 else None,
            }
        )
    return sorted(records, key=lambda item: (item["date"], item["id"]), reverse=True)


def rebuild_manifest() -> int:
    try:
        existing = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        existing = []
    preserved = []
    weibo_records = build_weibo_records()
    temporary = MANIFEST.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(weibo_records + preserved, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(MANIFEST)
    logging.info(
        "Gallery manifest updated: %d Weibo images, %d preserved images",
        len(weibo_records),
        len(preserved),
    )
    return len(weibo_records)


def main() -> int:
    configure_logging()
    if "--manifest-only" in sys.argv:
        rebuild_manifest()
        return 0
    if not COOKIE_FILE.exists() or COOKIE_FILE.stat().st_size < 100:
        logging.error(
            "Weibo cookie file is missing. Export a Netscape cookies.txt file to %s",
            COOKIE_FILE,
        )
        return 2
    COOKIE_FILE.chmod(0o600)
    successes = [download_account(uid) for uid in ACCOUNTS]
    COOKIE_FILE.chmod(0o600)
    prune_to_account_limits()
    count = rebuild_manifest()
    logging.info("Refresh finished with %d Weibo images", count)
    return 0 if all(successes) else 1


if __name__ == "__main__":
    sys.exit(main())
