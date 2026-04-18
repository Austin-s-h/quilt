#!/usr/bin/env python3

"""Benchmark the PDF thumbnail path on a local sample document."""

import argparse
import json
import shutil
import statistics
import time
from pathlib import Path

import t4_lambda_thumbnail

try:
    import resource
except ImportError:  # pragma: no cover
    resource = None


def _max_rss_mb():
    if resource is None:
        return None
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / 1024


def _require_poppler(*, count_pages: bool):
    missing = []
    if shutil.which("pdftoppm") is None:
        missing.append("pdftoppm")
    if count_pages and shutil.which("pdfinfo") is None:
        missing.append("pdfinfo")
    if missing:
        tools = ", ".join(missing)
        raise SystemExit(
            f"Missing required Poppler tool(s): {tools}. Install poppler-utils and ensure the binaries are on PATH."
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="Path to a local PDF file")
    parser.add_argument("--page", type=int, default=1, help="Page number to preview")
    parser.add_argument(
        "--size",
        default="w2048h1536",
        choices=sorted(t4_lambda_thumbnail.SIZE_PARAMETER_MAP),
        help="Thumbnail size preset",
    )
    parser.add_argument("--repeat", type=int, default=3, help="Number of benchmark iterations")
    parser.add_argument(
        "--count-pages",
        action="store_true",
        help="Include page counting in the benchmark",
    )
    args = parser.parse_args()

    _require_poppler(count_pages=args.count_pages)

    size = t4_lambda_thumbnail.SIZE_PARAMETER_MAP[args.size][0]
    durations = []
    last_info = None
    last_bytes = b""

    for _ in range(args.repeat):
        started = time.perf_counter()
        info, data = t4_lambda_thumbnail.handle_pdf(
            path=str(args.pdf),
            page=args.page,
            size=size,
            count_pages=args.count_pages,
        )
        durations.append(time.perf_counter() - started)
        last_info = info
        last_bytes = data

    result = {
        "pdf": str(args.pdf),
        "page": args.page,
        "size": args.size,
        "repeat": args.repeat,
        "durations_seconds": durations,
        "mean_seconds": statistics.mean(durations),
        "max_seconds": max(durations),
        "thumbnail_bytes": len(last_bytes),
        "max_rss_mb": _max_rss_mb(),
        "info": last_info,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()