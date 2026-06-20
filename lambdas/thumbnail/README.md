# Thumbnail Lambda Local Requirements

The thumbnail lambda renders PDFs and PowerPoint decks with native host tools when
you run the LOCAL catalog.

## Required host tools

```text
- PDF thumbnails: Poppler (`pdftoppm`)
- PPTX thumbnails: LibreOffice on PATH (`libreoffice` or `soffice`)
```

The Lambda/AWS container image installs these separately. In LOCAL mode, the tools
must already be installed on the machine that launches the lambda subprocess.

## Install by platform

### Linux

Ubuntu / Debian:

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils libreoffice
```

Fedora:

```bash
sudo dnf install -y poppler-utils libreoffice
```

### macOS

Homebrew installs LibreOffice as `soffice`, which the lambda resolves automatically:

```bash
brew install poppler libreoffice
```

### Windows

1. Install LibreOffice from https://www.libreoffice.org/download/download-libreoffice/
2. Add `C:\Program Files\LibreOffice\program` to `PATH` so `soffice.exe` is visible.
3. Install a Poppler build that includes `pdftoppm.exe`.
4. Add the Poppler `bin` directory to `PATH`.

## Verify before starting the LOCAL catalog

Run these commands in the same shell that starts `quilt3 catalog`:

```bash
command -v pdftoppm
command -v libreoffice || command -v soffice
```

If LibreOffice is missing, PPTX previews fail with an explicit error that points back
to this file.