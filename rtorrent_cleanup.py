#!/usr/bin/env python3
import os
import sys
import time
import shutil
import logging
import pathlib
import xmlrpc.client

def parse_labels(env_value: str):
    if not env_value:
        return {"notes", "whitepapers"}
    return {x.strip().lower() for x in env_value.split(",") if x.strip()}

def parse_int(env_value: str, default: int):
    try:
        return int(env_value)
    except (TypeError, ValueError):
        return default

RPC_URL = os.environ.get("RTORRENT_RPC_URL", "http://127.0.0.1/RPC2")

LABELS = parse_labels(os.environ.get("LABELS"))
MIN_AGE_DAYS = parse_int(os.environ.get("MIN_AGE_DAYS"), 28)

DRY_RUN = os.environ.get("DRY_RUN", "1") != "0"
LOGFILE = os.environ.get("LOGFILE", os.path.expanduser("~/rtorrent_cleanup.log"))


logging.basicConfig(
    filename=LOGFILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

def log(msg: str) -> None:
    print(msg)
    logging.info(msg)

def safe_remove_path(path_str: str) -> None:
    path = pathlib.Path(path_str)

    if not path.exists():
        log(f"Path already missing, skipping delete: {path}")
        return

    # Defensive guardrails. Adjust if your downloads live elsewhere.
    allowed_roots = [
        pathlib.Path("/downloads"),
        pathlib.Path("/data"),
        pathlib.Path.home() / "downloads",
    ]

    resolved = path.resolve()
    if not any(str(resolved).startswith(str(root.resolve())) for root in allowed_roots if root.exists()):
        raise RuntimeError(
            f"Refusing to delete path outside allowed roots: {resolved}. "
            f"Edit allowed_roots in the script."
        )

    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()

def main() -> int:
    now = int(time.time())
    min_age_seconds = MIN_AGE_DAYS * 24 * 60 * 60

    server = xmlrpc.client.ServerProxy(RPC_URL, allow_none=True)

    try:
        # row = [hash, name, complete, label, finished_epoch, is_multi_file, directory]
        rows = server.d.multicall2(
            "",
            "main",
            "d.hash=",
            "d.name=",
            "d.complete=",
            "d.custom1=",
            "d.timestamp.finished=",
            "d.is_multi_file=",
            "d.directory="
        )
    except Exception as exc:
        log(f"Failed to query rTorrent at {RPC_URL}: {exc}")
        return 1

    matched = 0

    for row in rows:
        try:
            info_hash, name, complete, label, finished_epoch, is_multi_file, directory = row
        except Exception:
            log(f"Unexpected row shape, skipping: {row!r}")
            continue

        label = (label or "").strip().lower()
        complete = int(complete)
        finished_epoch = int(finished_epoch or 0)
        is_multi_file = int(is_multi_file)
        directory = directory or ""

        if complete != 1:
            continue

        if label not in LABELS:
            continue

        if finished_epoch == 0:
            continue

        age_seconds = now - finished_epoch
        if age_seconds < min_age_seconds:
            continue

        matched += 1

        # rTorrent docs describe directory as always a directory.
        # For single-file torrents, data path is directory/name.
        # For multi-file torrents, data path is directory.
        if is_multi_file:
            data_path = directory
        else:
            data_path = str(pathlib.Path(directory) / name)

        log(
            f"MATCH label={label} age_days={age_seconds // 86400} "
            f"name={name!r} hash={info_hash} path={data_path!r}"
        )

        if DRY_RUN:
            continue

        try:
            # Stop first, then delete files, then erase torrent entry.
            server.d.stop(info_hash)
        except Exception as exc:
            log(f"Warning: could not stop {name!r}: {exc}")

        try:
            safe_remove_path(data_path)
            log(f"Deleted data for {name!r}")
        except Exception as exc:
            log(f"ERROR deleting data for {name!r}: {exc}")
            # Don't erase from rTorrent if file deletion failed.
            continue

        try:
            server.d.erase(info_hash)
            log(f"Erased torrent {name!r} from rTorrent")
        except Exception as exc:
            log(f"ERROR erasing torrent {name!r}: {exc}")

    log(f"Done. Matched {matched} torrents. Dry run: {DRY_RUN}")
    return 0

if __name__ == "__main__":
    sys.exit(main())