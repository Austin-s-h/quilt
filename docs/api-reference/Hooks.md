<a id="quilt3.hooks"></a>

# hooks

<a id="quilt3.hooks.get_build_s3_client_hook"></a>

## get\_build\_s3\_client\_hook()

Return build S3 client hook.

<a id="quilt3.hooks.set_build_s3_client_hook"></a>

## set\_build\_s3\_client\_hook(hook: T.Optional[BuildClientHook])

Set build S3 client hook.

Example for overriding `ServerSideEncryption` parameter for certain S3 operations:


```python
from quilt3.hooks import set_build_s3_client_hook

def event_handler(params, **kwargs):
    # Be mindful with parameters you set here.
    # Specifically it's not recommended to override/delete already set parameters
    # because that can break quilt3 logic.
    params.setdefault("ServerSideEncryption", "AES256")

def hook(build_client_base, session, client_kwargs, **kwargs):
    client = build_client_base(session, client_kwargs, **kwargs)
    # Docs for boto3 events system we use below:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/events.html
    for op in (
        "CreateMultipartUpload",
        "CopyObject",
        "PutObject",
    ):
        client.meta.events.register(f"before-parameter-build.s3.{op}", event_handler)
    return client

old_hook = set_build_s3_client_hook(hook)
```

**Arguments**:

- `hook` - Build client hook.
  

**Returns**:

  Old build client hook.

