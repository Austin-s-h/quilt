<!-- markdownlint-disable-next-line first-line-h1 -->
The Quilt catalog renders previews of the following file types.
Whenever possible, Quilt streams the smallest possible subset of the data
needed to generate the preview.

Previews are supported for uncompressed files as well as for gzip archives (.gz).

## Plain text previews

Quilt can display any plaintext file format, including the following.

* Most programming languages, with syntax highlighting
  (.cpp, .json, .js, .py, .sh,  .sql, etc.)
* Biological file formats
  (.bed, .cef, .gff, .fasta, .fastq, .sam, .pdbqt, .vcf, etc.)
* Text files (.csv, .md, .readme, .tsv, .txt, etc.)

## Chemical structures

The Quilt catalog uses the [NGL Viewer library](https://github.com/nglviewer/ngl)
to render structures.
By default, v3000 Molfiles are converted to v2000 by the JavaScript client
for rendering.

The following file formats are supported:

* Mol files (.mol, .mol2, .sdf)
* .cif
* .ent
* .pdb

## Image previews

The Quilt Catalog uses a [Lambda
function](https://github.com/quiltdata/quilt/tree/master/lambdas/thumbnail)
to automatically generate thumbnail previews of common image formats
and select microscopy image formats such as .bmp, .gif, .jpg, .jpeg,
.png, .webp, .tif, .tiff (including `OME-TIFF`), and .czi.

### Known limitations

Automated previews of 8-bit depth and higher image files are not
currently supported.

## Binary and special file format previews

* FCS Flow Cytometry files (.fcs)
* Media (.mp4, .webm, .flac, .m2t, .mp3, .mp4, .ogg, .ts, .tsa, .tsv, .wav)
* Jupyter notebooks (.ipynb)
* .parquet
* PDF (.pdf)
* PowerPoint (.pptx)
* Excel (.xls, .xlsx)

## Verifying PDF previews locally

For source-tree frontend changes, run the Catalog in LOCAL-mode proxy setup so
your webpack build talks to the real LOCAL backend routes.

Update `catalog/static-dev/config.js` to point at the LOCAL-mode prefixes:

```js
window.QUILT_CATALOG_CONFIG = {
   region: 'us-east-1',
   registryUrl: '/__reg',
   alwaysRequiresAuth: false,
   apiGatewayEndpoint: '/__lambda',
   s3Proxy: '/__s3proxy',
   passwordAuth: 'DISABLED',
   ssoAuth: 'DISABLED',
   ssoProviders: '',
   stackVersion: 'local-dev',
   mode: 'LOCAL',
   mixpanelToken: '',
   serviceBucket: '',
   noDownload: false,
}
```

Then start webpack and the LOCAL backend in separate terminals:

```bash
cd catalog
PORT=3001 npm start
```

```bash
cd api/python
uv sync --python 3.11 --no-dev --extra catalog
PYTHONPATH=$PWD \
QUILT_CATALOG_URL=http://localhost:3001 \
   uv run --no-dev --extra catalog quilt3 catalog --host localhost --port 3000 --no-browser
```

Browse `http://localhost:3000` so requests for `/graphql`, `/__lambda`, and
other LOCAL-mode routes stay on the Python app while frontend assets proxy to
webpack.

For offline preview validation, switch LOCAL mode to the filesystem backend:

```bash
cd api/python
PYTHONPATH=$PWD \
QUILT_LOCAL_OBJECT_BACKEND=filesystem \
QUILT_LOCAL_DATA_DIR=/tmp/quilt-local-data \
QUILT_CATALOG_URL=http://localhost:3001 \
   uv run --python 3.11 --no-dev --extra catalog quilt3 catalog --host localhost --port 3000 --no-browser
```

In LOCAL mode, object URLs now route through `/__s3proxy`, so PDF previews and
thumbnails can be generated from either real S3 objects or the filesystem-backed
local object store described in [docs/Catalog/LocalMode.md](./LocalMode.md).

This is still a read-oriented local environment. It does not yet provide the
entire production GraphQL mutation surface or the full production upload path.

## PDF Demo Checklist

Use the following checklist when the goal is to demo a PDF-preview change in the
real UI without depending on the production Catalog API.

Checklist:

```text
1. Start webpack on port 3001 and the LOCAL backend on port 3000.
2. Ensure the PDF is reachable through either a real S3-backed bucket/package or the filesystem LOCAL object store.
3. Confirm the frontend requests /__lambda/thumbnail with input=pdf and the expected preview size.
4. Confirm the first-page preview loads and returns page_count in X-Quilt-Info.
5. Confirm later page navigation also uses the same preview size.
6. Compare the old and new preview sizes at the same browser zoom level.
7. Validate one large multi-page PDF before concluding the change is safe for Lambda production limits.
```

What this local demo proves:

```text
- the real Catalog frontend requests a larger PDF preview image
- the LOCAL backend can fetch the source PDF and invoke the thumbnail lambda path
- page navigation and first-page loading behave correctly in the UI
- the visual quality difference is observable in a real browser flow
```

What this local demo does not prove:

```text
- that the production thumbnail Lambda stays within memory and timeout limits for large PDFs
- that the production Catalog GraphQL API behaves identically to LOCAL mode
- that write or search flows unrelated to previewing are ready in LOCAL mode
```

## PDF Resolution Notes

The current PDF preview quality issue is not primarily caused by Poppler's
default DPI. The more important bottleneck is in
[lambdas/thumbnail/src/t4_lambda_thumbnail/__init__.py](/home/hovland/quilt/lambdas/thumbnail/src/t4_lambda_thumbnail/__init__.py),
where `pdf_thumb()` renders directly to the requested width using:

```python
pdf2image.convert_from_path(..., size=(size, None), ...)
```

That means the PDF is effectively rasterized straight to the thumbnail width.
For a sharper result, the safer shape is:

```text
- render the source page at a configurable DPI
- cap that DPI at a sane upper bound such as 300
- downsample to the final thumbnail size with a high-quality filter such as Lanczos
- validate memory and runtime on a large multi-page PDF before shipping the change
```

Repeatable benchmark workflow:

```bash
cd lambdas/thumbnail
uv run python dev/generate_pdf_preview_sample.py --pages 75 /tmp/pdf-preview-benchmark.pdf
uv run python dev/benchmark_pdf_preview.py /tmp/pdf-preview-benchmark.pdf --size w2048h1536 --repeat 3 --count-pages
```

The benchmark prints JSON with per-run durations, output size, render DPI, and
best-effort max RSS so you can compare changes before and after adjusting the
thumbnail lambda. It requires Poppler tools such as `pdftoppm` and `pdfinfo`
to be installed and available on `PATH`.

This is different from PNG previews, where the source image is typically already
pixel-native and the resize path does not throw away vector detail up front.

To compare PDF quality before and after this change, generate a lightweight test
document with `uv run python dev/generate_pdf_preview_sample.py --pages 25
/tmp/pdf-preview-sample.pdf`, upload it to a bucket or package you can browse,
then compare `size=w1024h768` versus `size=w2048h1536` in the Catalog request.

## Advanced: HTML rendering and Quilt Package File Server

The Quilt Catalog supports HTML and JavaScript in preview via iframes. By
default, preview iframes do not have IAM permissions and are therefore unable to
access private files in S3.

If you wish for your HTML to access data within the enclosing package or bucket
(at the viewer's level of permissions) and/or use origin-aware Web APIs such as
data storage/cookies, you must opt in to `Enable permissive HTML rendering` in
[Bucket settings](Admin.md#buckets). This explicitly allows cross-origin resource
sharing (CORS).

> You should _only enable this feature for buckets where you implicitly
> trust_ the contents of the HTML files.

Depending on the context where the HTML file is rendered (package vs bucket
view), the iframe gets the following origin:

* Inside a package view with permissive rendering **enabled**:
  the origin is the **Quilt Package File Server**.

* Inside a bucket view with permissive rendering **enabled**:
  the origin is the AWS S3 bucket endpoint.

* With permissive rendering **disabled** (irrespective of package or bucket
  view): the resource is treated as being from a special origin that always
  fails the same-origin policy ([`allow-same-origin` iframe sandbox
  token](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#sandbox)
  is not set).

> An important implication of same-origin policy is that the scripts
> executed under the same origin share LocalStorage data and cookies.

### Allowing Forms and Popups

> New in Quilt Platform version 1.59.0 or higher

Enabling Permissive HTML now allows forms and popups to work from iframes.

### Package view example with permissive rendering enabled

1. `report.html` is a file in a package that includes a publicly available JS
   library and a custom embedded script.
2. Opening `report.html` in a package view generates a new session `temporary-session-id`.
3. The file is served by the **Quilt Package File Server** under the
   `/temporary-session-id/report.html` path.
4. All relative media and scripts are rendered in the same iframe relative-path
   format:
    * `./img.jpg` is resolved to `/temporary-session-id/img.jpg`
    * `script.js` is resolved to `/temporary-session-id/script.js`
5. The `allow-same-origin` iframe sandbox token is enabled,
   the origin is the **Quilt Package File Server**,
   the LocalStorage API is **available**.

### Bucket view example with permissive rendering enabled

1. `report.html` is a file in a bucket `example-bucket` that includes a publicly
   available JS library and custom embedded script.
2. When opening `report.html` in bucket view, it is served directly by S3
   via a signed HTTPS URL, e.g.
   `https://example-bucket.s3.region.amazonaws.com/report.html?versionId=...&X-Amz-...`.
3. All relative media and scripts are rendered in the same iframe relative-path
   format:
    * `./img.jpg` is resolved to `/img.jpg`
    * `script.js` is resolved to `/script.js`
4. The `allow-same-origin` iframe sandbox token is **enabled**,
   the origin is the **S3 bucket endpoint**
   (e.g. `https://example-bucket.s3.region.amazonaws.com`),
   the LocalStorage API is **available**.

### Example with permissive rendering disabled

1. `report.html` is a file in a bucket `example-bucket` that includes a publicly
   available JS library and custom embedded script.
2. When opening `report.html` in any view it is served directly by S3 via a
   signed HTTPS URL, e.g.
   `https://example-bucket.s3.region.amazonaws.com/report.html?versionId=...&X-Amz-...`.
3. All relative media and scripts are rendered in the same iframe relative-path
   format:
    * `./img.jpg` is resolved to `/img.jpg`
    * `script.js` is resolved to `/script.js`
4. The `allow-same-origin` iframe sandbox token is **disabled**,
   a virtual unique origin is used (always failing the same-origin policy),
   the LocalStorage API is **unavailable**.

### Live packages

* [Dynamic visualizations; interactive IGV dashboard; Perspective datagrids with
images](https://open.quiltdata.com/b/quilt-example/packages/examples/package-file-server)
