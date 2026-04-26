<a id="quilt3"></a>

# quilt3

Quilt API

<a id="quilt3.api_keys"></a>

# api\_keys

API for managing your own API keys.

<a id="quilt3.api_keys.APIKey"></a>

# APIKey

An API key for programmatic access.

<a id="quilt3.api_keys.APIKeyError"></a>

# APIKeyError

Error during API key operation.

<a id="quilt3.api_keys.list"></a>

## list(name: T.Optional[str] = None, fingerprint: T.Optional[str] = None, status: T.Optional[APIKeyStatus] = None)

List your API keys. Optionally filter by name, fingerprint, or status.

**Arguments**:

- `name` - Filter by key name.
- `fingerprint` - Filter by key fingerprint.
- `status` - Filter by "ACTIVE" or "EXPIRED". None returns all.
  

**Returns**:

  List of your API keys matching the filters.

<a id="quilt3.api_keys.get"></a>

## get(id: str)

Get a specific API key by ID.

**Arguments**:

- `id` - The API key ID.
  

**Returns**:

  The API key, or None if not found.

<a id="quilt3.api_keys.create"></a>

## create(name: str, expires\_in\_days: int = 90)

Create a new API key for yourself.

**Arguments**:

- `name` - Name for the API key.
- `expires_in_days` - Days until expiration (1-365, default 90).
  

**Returns**:

  Tuple of (APIKey, secret). The secret is only returned once - save it securely!
  

**Raises**:

- `APIKeyError` - If the operation fails.

<a id="quilt3.api_keys.revoke"></a>

## revoke(id: T.Optional[str] = None, secret: T.Optional[str] = None)

Revoke an API key. Provide either the key ID or the secret.

**Arguments**:

- `id` - The API key ID to revoke.
- `secret` - The API key secret to revoke.
  

**Raises**:

- `ValueError` - If neither id nor secret is provided.
- `APIKeyError` - If the operation fails.

<a id="quilt3.session"></a>

# session

Helper functions for connecting to the Quilt Registry.

<a id="quilt3.session.login_with_api_key"></a>

## login\_with\_api\_key(key: str)

Authenticate using an API key.

The API key is stored in memory only (no disk persistence).
While set, the API key overrides any interactive session.
Use clear_api_key() to revert to interactive session.

**Arguments**:

- `key` - API key string (starts with 'qk_')
  

**Raises**:

- `ValueError` - If the key doesn't start with 'qk_' prefix.

<a id="quilt3.session.clear_api_key"></a>

## clear\_api\_key()

Clear the API key and fall back to interactive session (if available).

<a id="quilt3.session.login"></a>

## login()

Authenticate to your Quilt stack and assume the role assigned to you by
your stack administrator. Not required if you have existing AWS credentials.

Launches a web browser and asks the user for a token.

<a id="quilt3.session.logout"></a>

## logout()

Do not use Quilt credentials. Useful if you have existing AWS credentials.

<a id="quilt3.session.logged_in"></a>

## logged\_in()

Return catalog URL if Quilt client is authenticated, `None` otherwise.

<a id="quilt3.session.get_boto3_session"></a>

## get\_boto3\_session(\*, fallback: bool = True)

Return a Boto3 session with Quilt stack credentials and AWS region.
In case of no Quilt credentials found, return a "normal" Boto3 session if `fallback` is `True`,
otherwise raise a `QuiltException`.

> Note: you need to call `quilt3.config("https://your-catalog-homepage/")` to have region set on the session,
if you previously called it in quilt3 < 6.1.0.

<a id="quilt3.api"></a>

# api

<a id="quilt3.api.delete_package"></a>

## delete\_package(name, registry=None, top\_hash=None)

Delete a package. Deletes only the manifest entries and not the underlying files.

**Arguments**:

- `name` _str_ - Name of the package
- `registry` _str_ - The registry the package will be removed from
- `top_hash` _str_ - Optional. A package hash to delete, instead of the whole package.

<a id="quilt3.api.list_packages"></a>

## list\_packages(registry=None)

Lists Packages in the registry.

Returns an iterable of all named packages in a registry.
If the registry is None, default to the local registry.

**Arguments**:

- `registry` _str_ - location of registry to load package from.
  

**Returns**:

  An iterable of strings containing the names of the packages

<a id="quilt3.api.list_package_versions"></a>

## list\_package\_versions(name, registry=None)

Lists versions of a given package.

Returns an iterable of (latest_or_unix_ts, hash) of package revisions.
If the registry is None, default to the local registry.

**Arguments**:

- `name` _str_ - Name of the package
- `registry` _str_ - location of registry to load package from.
  

**Returns**:

  An iterable of tuples containing the version and hash for the package.

<a id="quilt3.api.config"></a>

## config(\*catalog\_url, \*\*config\_values)

Set or read the QUILT configuration.

To retrieve the current config, call directly, without arguments:

import quilt3
quilt3.config()

To trigger autoconfiguration, call with just the navigator URL:

import quilt3
quilt3.config('https://YOUR-CATALOG-URL.com')

To set config values, call with one or more key=value pairs:

import quilt3
quilt3.config(navigator_url='http://example.com')

Default config values can be found in `quilt3.util.CONFIG_TEMPLATE`.

**Arguments**:

- `catalog_url` - A (single) URL indicating a location to configure from
- `**config_values` - `key=value` pairs to set in the config
  

**Returns**:

- `QuiltConfig` - (an ordered Mapping)

<a id="quilt3.api.search"></a>

## search(query: T.Union[str, dict], limit: int = 10)

Execute a search against the configured search endpoint.

**Arguments**:

- `query` - query string to query if passed as `str`, DSL query body if passed as `dict`
- `limit` - maximum number of results to return. Defaults to 10
  
  Query Syntax:
  [Query String Query](
  https://www.elastic.co/guide/en/elasticsearch/reference/7.10/query-dsl-query-string-query.html)
  [Query DSL](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/query-dsl.html)
  
  Index schemas and search examples can be found in the
  [Quilt Search documentation](https://docs.quilt.bio/quilt-platform-catalog-user/search).
  

**Returns**:

  search results

