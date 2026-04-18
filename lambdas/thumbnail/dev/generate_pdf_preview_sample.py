#!/usr/bin/env python3

"""Generate a lightweight PDF for manual Catalog preview checks."""

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PAGE_SIZE = (850, 1100)
MARGIN = 72
LINE_HEIGHT = 22
BODY_WIDTH = 74
FONT = ImageFont.load_default()

BODY_LINES = [
    "Sample metadata fields: specimen_id, assay_type, donor_id, pipeline_version, and release tag.",
    "This page intentionally mixes headings, short paragraphs, and numbered rows so text stays readable but lightweight.",
    "Expected use: open this PDF in a package or bucket, then compare preview sharpness at the same browser zoom level.",
    "Use later pages to confirm that page navigation keeps the same visual fidelity after the preview-size change.",
]


def _wrap(text):
    return textwrap.wrap(text, width=BODY_WIDTH)


def _draw_block(draw, *, x, y, lines, fill):
    for line in lines:
        draw.text((x, y), line, font=FONT, fill=fill)
        y += LINE_HEIGHT
    return y


def _page_color(page_number):
    tint = 240 - (page_number % 5) * 8
    return (tint, tint, 248)


def _make_page(page_number, page_count):
    image = Image.new("RGB", PAGE_SIZE, _page_color(page_number))
    draw = ImageDraw.Draw(image)

    y = MARGIN
    draw.text((MARGIN, y), "PDF Preview Validation Sample", font=FONT, fill=(24, 24, 32))
    y += LINE_HEIGHT * 2

    y = _draw_block(
        draw,
        x=MARGIN,
        y=y,
        lines=_wrap(
            f"Page {page_number} of {page_count}. This synthetic document is intentionally small, "
            "but its mixed text layout should still make blur or compression artifacts obvious."
        ),
        fill=(40, 40, 48),
    )
    y += LINE_HEIGHT

    for line in BODY_LINES:
        y = _draw_block(draw, x=MARGIN, y=y, lines=_wrap(line), fill=(56, 56, 68))
        y += 8

    y += LINE_HEIGHT
    draw.text((MARGIN, y), "Quick scan rows", font=FONT, fill=(24, 24, 32))
    y += LINE_HEIGHT * 2

    for offset in range(1, 9):
        row = (
            f"{page_number:02d}-{offset:02d}  "
            f"gene_set_{offset:<2}  normalized_counts={page_number * offset:>4}  "
            f"review_status=ready"
        )
        draw.text((MARGIN, y), row, font=FONT, fill=(48, 48, 60))
        y += LINE_HEIGHT

    footer = (
        "Tip: compare this page at the same browser zoom before and after the Catalog "
        "change, and verify the thumbnail request size in DevTools."
    )
    _draw_block(draw, x=MARGIN, y=PAGE_SIZE[1] - 120, lines=_wrap(footer), fill=(72, 72, 88))
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Output PDF path")
    parser.add_argument("--pages", type=int, default=5, help="Number of pages to generate")
    args = parser.parse_args()

    if args.pages < 1:
        raise SystemExit("--pages must be at least 1")

    pages = [_make_page(page_number, args.pages) for page_number in range(1, args.pages + 1)]
    first_page, *rest = pages
    args.output.parent.mkdir(parents=True, exist_ok=True)
    first_page.save(args.output, format="PDF", save_all=True, append_images=rest, resolution=144)
    print(f"Wrote {args.output} with {args.pages} pages")


if __name__ == "__main__":
    main()
