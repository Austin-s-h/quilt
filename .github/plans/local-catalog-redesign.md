# Local Catalog Redesign Plan

## Problem Statement

The current `quilt3_local/` implementation mirrors the cloud stack by spoofing AWS
services (S3 proxy, Lambda stubs, fake credentials). This creates maintenance burden
because every cloud behavior change requires updating the local mock, and it makes the
architecture hard to reason about — developers must understand both the real cloud
contracts AND the local shims simultaneously.

## Current Architecture (Mirror)

```
catalog (React) → API Gateway stubs → Lambda stubs → S3 proxy → local filesystem
                     ↓                      ↓
              quilt3_local/api.py    quilt3_local/lambdas/
                                    (preview, thumbnail, tabular_preview, shared)
```

- `s3proxy.py` — translates S3 API calls (ListObjectsV2, GetObject, HeadObject,
  PutObject) into filesystem reads/writes under `QUILT_LOCAL_DATA_DIR`
- `api.py` — returns fake credentials, stubs search
- `lambdas/` — re-implements preview/thumbnail/tabular logic from upstream lambdas
- `buckets.py` — hardcodes a single bucket backed by the filesystem
- Frontend talks to the same API shape as production, unaware it's local

## Proposed Architecture (Build On Top)

Instead of re-implementing cloud services, build on top of what `quilt3` already knows
how to do natively:

```
catalog (React) → Local Catalog API → quilt3 Package/Bucket API → local filesystem
                                            ↑
                                     Uses existing quilt3 package ops
                                     (browse, push, install, data_transfer)
```

### Key Principles

1. **No credential spoofing** — local mode doesn't need auth; remove the fake
   credential endpoint entirely and configure the frontend to skip auth flows.

2. **Reuse `quilt3.Package` for all package operations** — browse, list revisions,
   read manifests, etc. should call the existing package code path that already
   supports local registries (`file://` URIs).

3. **Direct file serving for previews** — instead of routing through a Lambda-shaped
   stub, serve file previews via a simple endpoint that reads from the package's
   physical data (already accessible via `quilt3.Package["key"].get()`).

4. **Thin API adapter** — a FastAPI app that translates catalog REST calls into
   `quilt3` library calls. The catalog frontend already defines its API contract;
   the adapter just needs to implement those endpoints using native operations.

5. **No S3 protocol emulation** — the frontend should get a local-mode adapter
   that understands file paths, not an S3 look-alike that happens to read from disk.

### Migration Path

| Current | Proposed |
|---------|----------|
| `s3proxy.py` (S3 API emulation) | Drop. Serve objects via `/api/objects/<bucket>/<key>` |
| `api.py` fake credentials | Drop. Frontend skips auth in LOCAL mode |
| `lambdas/preview.py` | Reuse `t4_lambda_shared.preview` directly (it's now in workspace) |
| `lambdas/thumbnail.py` | Call `t4_lambda_thumbnail.handle_image()` directly |
| `lambdas/tabular_preview.py` | Call upstream tabular logic directly |
| `buckets.py` (hardcoded bucket) | Use `quilt3.Bucket` with local registry config |
| `packages.py` | Use `quilt3.Package.browse()` / `quilt3.list_packages()` |

### Frontend Changes Required

The catalog frontend currently assumes cloud-shaped endpoints. For LOCAL mode:
- `config.json` already signals `mode: "LOCAL"` — extend this to skip auth
- Replace S3 presigned-URL fetches with direct `/api/objects/...` fetches
- Package listing/browsing calls go to `/api/packages/...` instead of S3 manifest reads

### What Stays

- `main.py` FastAPI app shell (mounts API + serves SPA)
- The fixture staging script (`tests/preview_fixtures.py`)
- The poe task workflow (`catalog-test`, `catalog-test-ci`)
- The test suite (`tests/test_local_mode.py`)

### Scope for Follow-up PR

This redesign is **out of scope for PR #12** (packaging modernization). Proposed as a
separate follow-up with:
1. Refactor `quilt3_local/` to the new architecture
2. Update catalog frontend LOCAL mode paths
3. Update tests to verify the new flow
4. Remove dead S3-proxy / Lambda-stub code

## Open Questions

- Should the local catalog support writes (package push) or be read-only initially?
- Should previews be generated on-demand or pre-computed during staging?
- Can we reuse the catalog's existing `mode: "LOCAL"` config to switch API base paths
  entirely, or do we need a more granular feature flag?
