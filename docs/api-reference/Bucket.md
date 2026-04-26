<a id="quilt3.bucket"></a>

# bucket

bucket.py

Contains the Bucket class, which provides several useful functions
    over an s3 bucket.

<a id="quilt3.bucket.Bucket"></a>

# Bucket

Bucket interface for Quilt.

<a id="quilt3.bucket.Bucket.__init__"></a>

## Bucket.\_\_init\_\_(bucket\_uri)

Creates a Bucket object.

**Arguments**:

- `bucket_uri(str)` - URI of bucket to target. Must start with 's3://'
  

**Returns**:

  A new Bucket

<a id="quilt3.bucket.Bucket.search"></a>

## Bucket.search(query: T.Union[str, dict], limit: int = 10)

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

<a id="quilt3.bucket.Bucket.put_file"></a>

## Bucket.put\_file(key, path)

Stores file at path to key in bucket.

**Arguments**:

- `key(str)` - key in bucket to store file at
- `path(str)` - string representing local path to file
  

**Returns**:

  None
  

**Raises**:

  * if no file exists at path
  * if copy fails

<a id="quilt3.bucket.Bucket.put_dir"></a>

## Bucket.put\_dir(key, directory)

Stores all files in the `directory` under the prefix `key`.

**Arguments**:

- `key(str)` - prefix to store files under in bucket
- `directory(str)` - path to directory to grab files from
  

**Returns**:

  None
  

**Raises**:

  * if writing to bucket fails

<a id="quilt3.bucket.Bucket.keys"></a>

## Bucket.keys()

Lists all keys in the bucket.

**Returns**:

  List of strings

<a id="quilt3.bucket.Bucket.delete"></a>

## Bucket.delete(key)

Deletes a key from the bucket.

**Arguments**:

- `key(str)` - key to delete
  

**Returns**:

  None
  

**Raises**:

  * if delete fails

<a id="quilt3.bucket.Bucket.delete_dir"></a>

## Bucket.delete\_dir(path)

Delete a directory and all of its contents from the bucket.

**Arguments**:

- `path` _str_ - path to the directory to delete

<a id="quilt3.bucket.Bucket.ls"></a>

## Bucket.ls(path=None, recursive=False)

List data from the specified path.

**Arguments**:

- `path` _str_ - bucket path to list
- `recursive` _bool_ - show subdirectories and their contents as well
  

**Returns**:

- ``list`` - Return value structure has not yet been permanently decided
  Currently, it's a `tuple` of `list` objects, containing the
- `following` - (directory info, file/object info, delete markers).

<a id="quilt3.bucket.Bucket.fetch"></a>

## Bucket.fetch(key, path)

Fetches file (or files) at `key` to `path`.

If `key` ends in '/', then all files with the prefix `key` will match and
will be stored in a directory at `path`.

Otherwise, only one file will be fetched and it will be stored at `path`.

**Arguments**:

- `key(str)` - key in bucket to fetch
- `path(str)` - path in local filesystem to store file or files fetched
  

**Returns**:

  None
  

**Raises**:

  * if path doesn't exist
  * if download fails

<a id="quilt3.bucket.Bucket.select"></a>

## Bucket.select(key, query, raw=False)

Selects data from an S3 object.

**Arguments**:

- `key(str)` - key to query in bucket
- `query(str)` - query to execute (SQL by default)
- `query_type(str)` - other query type accepted by S3 service
- `raw(bool)` - return the raw (but parsed) response
  

**Returns**:

- `pandas.DataFrame` - results of query

