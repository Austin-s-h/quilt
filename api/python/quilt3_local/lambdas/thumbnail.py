from __future__ import annotations

import importlib.util
import json
import tempfile
import textwrap
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from .._upstream import load_module
from .shared.decorator import QUILT_INFO_HEADER, api, validate
from .shared.utils import get_default_origins, make_json_response

SUPPORTED_SIZES = [
    (32, 32),
    (64, 64),
    (128, 128),
    (256, 256),
    (480, 320),
    (640, 480),
    (960, 640),
    (1024, 768),
    (2048, 1536),
]
SIZE_PARAMETER_MAP = {f"w{width}h{height}": (width, height) for width, height in SUPPORTED_SIZES}

_pdf_helper_path = (
    Path(__file__).resolve().parents[4] / "lambdas" / "thumbnail" / "src" / "t4_lambda_thumbnail" / "pdf_thumbnail.py"
)
_pdf_helper_spec = importlib.util.spec_from_file_location("_quilt_pdf_thumbnail", _pdf_helper_path)
if _pdf_helper_spec is None or _pdf_helper_spec.loader is None:
    raise ImportError(f"Unable to load PDF helper module from {_pdf_helper_path}")
_pdf_helper = importlib.util.module_from_spec(_pdf_helper_spec)
_pdf_helper_spec.loader.exec_module(_pdf_helper)

PDFThumbError = _pdf_helper.PDFThumbError
count_pdf_pages = _pdf_helper.count_pdf_pages
get_pdf_render_dpi = _pdf_helper.get_pdf_render_dpi
render_pdf_page = _pdf_helper.render_pdf_page
resize_pdf_page = _pdf_helper.resize_pdf_page


class OfficePreviewError(RuntimeError):
    pass

SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string"},
        "size": {"enum": list(SIZE_PARAMETER_MAP)},
        "input": {"enum": ["pdf", "pptx"]},
        "page": {
            "type": "string",
            "pattern": r"^\d+$",
        },
        "countPages": {"enum": ["true", "false"]},
    },
    "required": ["url", "size"],
    "additionalProperties": False,
}


def handle_exceptions(*exception_types):
    def decorator(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exception_types as exc:
                return make_json_response(500, {"error": str(exc)})

        return wrapper

    return decorator


def pdf_thumb(*, path: str, page: int, size: int):
    render_dpi = get_pdf_render_dpi()
    page_image = render_pdf_page(path=path, page=page, dpi=render_dpi)
    return resize_pdf_page(page_image, size=size), render_dpi


def handle_pdf(*, path: str, page: int, size: int, count_pages: bool):
    thumb, render_dpi = pdf_thumb(path=path, page=page, size=size)
    info = {
        "thumbnail_format": "JPEG",
        "thumbnail_size": thumb.size,
        "pdf_render_dpi": render_dpi,
        "pdf_resize_filter": "LANCZOS",
    }
    if count_pages:
        info["page_count"] = count_pdf_pages(path)

    with tempfile.NamedTemporaryFile(suffix=".jpg") as out_file:
        thumb.save(out_file, "JPEG")
        out_file.flush()
        data = Path(out_file.name).read_bytes()
    return info, data


def _pptx_slide_paths(archive: zipfile.ZipFile) -> list[str]:
    def slide_number(name: str) -> int:
        return int(name.rsplit("slide", 1)[1].split(".", 1)[0])

    return sorted(
        [name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")],
        key=slide_number,
    )


def _pptx_slide_text(archive: zipfile.ZipFile, slide_path: str) -> list[str]:
    root = ET.fromstring(archive.read(slide_path))
    return [text.strip() for elem in root.iter() if elem.tag.endswith("}t") and (text := elem.text or "").strip()]


def _load_font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _render_pptx_preview(lines: list[str], *, slide_number: int, slide_count: int, size: tuple[int, int]) -> bytes:
    image = Image.new("RGB", size, color=(250, 248, 244))
    draw = ImageDraw.Draw(image)
    title_font = _load_font(max(size[0] // 22, 18))
    body_font = _load_font(max(size[0] // 34, 14))
    text_color = (36, 40, 46)
    accent = (195, 131, 62)
    margin_x = max(size[0] // 14, 32)
    top = max(size[1] // 12, 28)
    line_gap = max(size[1] // 60, 10)
    body_width = max(40, size[0] // 14)

    draw.rounded_rectangle((margin_x, top, size[0] - margin_x, top + 8), radius=4, fill=accent)
    top += 28
    draw.text((margin_x, top), f"PowerPoint Preview  {slide_number}/{slide_count}", font=title_font, fill=text_color)
    top += max(size[1] // 10, 72)

    wrapped_lines: list[str] = []
    for line in lines:
        wrapped_lines.extend(textwrap.wrap(line, width=body_width) or [""])
        if len(wrapped_lines) >= 14:
            break

    if not wrapped_lines:
        wrapped_lines = ["This slide contains no extractable text."]

    for line in wrapped_lines[:14]:
        draw.text((margin_x, top), line, font=body_font, fill=text_color)
        top += body_font.size + line_gap
        if top >= size[1] - margin_x:
            break

    with tempfile.NamedTemporaryFile(suffix=".jpg") as out_file:
        image.save(out_file, "JPEG", quality=90)
        out_file.flush()
        return Path(out_file.name).read_bytes()


def handle_pptx(*, path: str, page: int, size: tuple[int, int], count_pages: bool):
    with zipfile.ZipFile(path) as archive:
        slide_paths = _pptx_slide_paths(archive)
        if not slide_paths:
            raise OfficePreviewError("PowerPoint file contains no slides")
        if page < 1 or page > len(slide_paths):
            raise OfficePreviewError(f"Requested slide {page} is out of range")

        slide_count = len(slide_paths)
        slide_lines = _pptx_slide_text(archive, slide_paths[page - 1])

    data = _render_pptx_preview(slide_lines, slide_number=page, slide_count=slide_count, size=size)
    info = {
        "thumbnail_format": "JPEG",
        "thumbnail_size": size,
        "office_preview_engine": "local-pptx-text",
    }
    if count_pages:
        info["page_count"] = slide_count
    return info, data


@api(cors_origins=get_default_origins())
@validate(SCHEMA)
@handle_exceptions(PDFThumbError, OfficePreviewError)
def _pdf_lambda_handler(request):
    url = request.args["url"]
    size = SIZE_PARAMETER_MAP[request.args["size"]]
    page = int(request.args.get("page", "1"))
    count_pages = request.args.get("countPages") == "true"

    resp = requests.get(url)
    if not resp.ok:
        return make_json_response(resp.status_code, {"error": resp.reason, "text": resp.text})

    filename_suffix = urllib.parse.unquote(urllib.parse.urlparse(url).path.split("/")[-1])
    with tempfile.NamedTemporaryFile(suffix=filename_suffix) as src_file:
        src_file.write(resp.content)
        src_file.flush()
        input_type = request.args.get("input")
        if input_type == "pptx":
            info, data = handle_pptx(path=src_file.name, page=page, size=size, count_pages=count_pages)
        else:
            info, data = handle_pdf(path=src_file.name, page=page, size=size[0], count_pages=count_pages)

    return (
        200,
        data,
        {
            "Content-Type": "image/jpeg",
            QUILT_INFO_HEADER: json.dumps(info),
        },
    )


def lambda_handler(event, context):
    args = event.get("queryStringParameters") or {}
    if args.get("input") in {"pdf", "pptx"}:
        return _pdf_lambda_handler(event, context)
    return load_module("lambdas.thumbnail").lambda_handler(event, context)
