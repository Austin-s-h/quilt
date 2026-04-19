from __future__ import annotations

import importlib.util
import json
import tempfile
import urllib.parse
from pathlib import Path

import requests
from PIL import Image

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

SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string"},
        "size": {"enum": list(SIZE_PARAMETER_MAP)},
        "input": {"enum": ["pdf"]},
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


@api(cors_origins=get_default_origins())
@validate(SCHEMA)
@handle_exceptions(PDFThumbError)
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
    if args.get("input") == "pdf":
        return _pdf_lambda_handler(event, context)
    return load_module("lambdas.thumbnail").lambda_handler(event, context)
