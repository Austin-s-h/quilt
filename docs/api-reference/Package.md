<a id="quilt3.packages"></a>

# packages

<a id="quilt3.packages.PackageEntry"></a>

# PackageEntry

Represents an entry at a logical key inside a package.

<a id="quilt3.packages.PackageEntry.__init__"></a>

## PackageEntry.\_\_init\_\_(physical\_key, size, hash\_obj, meta)

Creates an entry.

**Arguments**:

- `physical_key` - a URI (either `s3://` or `file://`)
- `size(number)` - size of object in bytes
- `hash({'type'` - string, 'value': string}): hash object
  for example: {'type': 'SHA256', 'value': 'bb08a...'}
- `meta(dict)` - metadata dictionary
  

**Returns**:

  a PackageEntry

<a id="quilt3.packages.PackageEntry.as_dict"></a>

## PackageEntry.as\_dict()

Returns dict representation of entry.

<a id="quilt3.packages.PackageEntry.set_meta"></a>

## PackageEntry.set\_meta(meta)

Sets the user_meta for this PackageEntry.

<a id="quilt3.packages.PackageEntry.set"></a>

## PackageEntry.set(path=None, meta=None)

Returns self with the physical key set to path.

**Arguments**:

- `path(string)` - new path to place at logical_key in the package
  Currently only supports a path on local disk
- `meta(dict)` - metadata dict to attach to entry. If meta is provided, set just
  updates the meta attached to logical_key without changing anything
  else in the entry
  

**Returns**:

  self

<a id="quilt3.packages.PackageEntry.get"></a>

## PackageEntry.get()

Returns the physical key of this PackageEntry.

<a id="quilt3.packages.PackageEntry.get_cached_path"></a>

## PackageEntry.get\_cached\_path()

Returns a locally cached physical key, if available.

<a id="quilt3.packages.PackageEntry.get_bytes"></a>

## PackageEntry.get\_bytes(use\_cache\_if\_available=True)

Returns the bytes of the object this entry corresponds to. If 'use_cache_if_available'=True, will first try to
retrieve the bytes from cache.

<a id="quilt3.packages.PackageEntry.get_as_json"></a>

## PackageEntry.get\_as\_json(use\_cache\_if\_available=True)

Returns a JSON file as a `dict`. Assumes that the file is encoded using utf-8.

If 'use_cache_if_available'=True, will first try to retrieve the object from cache.

<a id="quilt3.packages.PackageEntry.get_as_string"></a>

## PackageEntry.get\_as\_string(use\_cache\_if\_available=True)

Return the object as a string. Assumes that the file is encoded using utf-8.

If 'use_cache_if_available'=True, will first try to retrieve the object from cache.

<a id="quilt3.packages.PackageEntry.deserialize"></a>

## PackageEntry.deserialize(func=None, \*\*format\_opts)

Returns the object this entry corresponds to.

**Arguments**:

- `func` - Skip normal deserialization process, and call func(bytes),
  returning the result directly.
- `**format_opts` - Some data formats may take options.  Though
  normally handled by metadata, these can be overridden here.
  

**Returns**:

  The deserialized object from the logical_key
  

**Raises**:

  physical key failure
  hash verification fail
  when deserialization metadata is not present

<a id="quilt3.packages.PackageEntry.fetch"></a>

## PackageEntry.fetch(dest=None)

Gets objects from entry and saves them to dest.

**Arguments**:

- `dest` - where to put the files
  Defaults to the entry name
  

**Returns**:

  None

<a id="quilt3.packages.PackageEntry.__call__"></a>

## PackageEntry.\_\_call\_\_(func=None, \*\*kwargs)

Shorthand for self.deserialize()

<a id="quilt3.packages.Package"></a>

# Package

In-memory representation of a package

<a id="quilt3.packages.Package.__repr__"></a>

## Package.\_\_repr\_\_(max\_lines=20)

String representation of the Package.

<a id="quilt3.packages.Package.install"></a>

## Package.install(cls, name, registry=None, top\_hash=None, dest=None, dest\_registry=None, \*, path=None)

Installs a named package to the local registry and downloads its files.

**Arguments**:

- `name(str)` - Name of package to install.
- `registry(str)` - Registry where package is located.
  Defaults to the default remote registry.
- `top_hash(str)` - Hash of package to install. Defaults to latest.
- `dest(str)` - Local path to download files to.
- `dest_registry(str)` - Registry to install package to. Defaults to local registry.
- `path(str)` - If specified, downloads only `path` or its children.

<a id="quilt3.packages.Package.resolve_hash"></a>

## Package.resolve\_hash(cls, name, registry, hash\_prefix)

Find a hash that starts with a given prefix.

**Arguments**:

- `name` _str_ - name of package
- `registry` _str_ - location of registry
- `hash_prefix` _str_ - hash prefix with length between 6 and 64 characters

<a id="quilt3.packages.Package.browse"></a>

## Package.browse(cls, name, registry=None, top\_hash=None)

Load a package into memory from a registry without making a local copy of
the manifest.

**Arguments**:

- `name(string)` - name of package to load
- `registry(string)` - location of registry to load package from
- `top_hash(string)` - top hash of package version to load

<a id="quilt3.packages.Package.__contains__"></a>

## Package.\_\_contains\_\_(logical\_key)

Checks whether the package contains a specified logical_key.

**Returns**:

  True or False

<a id="quilt3.packages.Package.__getitem__"></a>

## Package.\_\_getitem\_\_(logical\_key)

Filters the package based on prefix, and returns either a new Package
or a PackageEntry.

**Arguments**:

- `prefix(str)` - prefix to filter on
  

**Returns**:

  PackageEntry if prefix matches a logical_key exactly
  otherwise Package

<a id="quilt3.packages.Package.fetch"></a>

## Package.fetch(dest='./')

Copy all descendants to `dest`. Descendants are written under their logical
names _relative_ to self.

**Arguments**:

- `dest` - where to put the files (locally)
  

**Returns**:

  A new Package object with entries from self, but with physical keys
  pointing to files in `dest`.

<a id="quilt3.packages.Package.keys"></a>

## Package.keys()

Returns logical keys in the package.

<a id="quilt3.packages.Package.walk"></a>

## Package.walk()

Generator that traverses all entries in the package tree and returns tuples of (key, entry),
with keys in alphabetical order.

<a id="quilt3.packages.Package.load"></a>

## Package.load(cls, readable\_file)

Loads a package from a readable file-like object.

**Arguments**:

- `readable_file` - readable file-like object to deserialize package from
  

**Returns**:

  A new Package object
  

**Raises**:

  file not found
  json decode error
  invalid package exception

<a id="quilt3.packages.Package.set_dir"></a>

## Package.set\_dir(lkey, path=None, meta=None, update\_policy="incoming", unversioned: bool = False)

Adds all files from `path` to the package.

Recursively enumerates every file in `path`, and adds them to
the package according to their relative location to `path`.

**Arguments**:

- `lkey(string)` - prefix to add to every logical key,
  use '/' for the root of the package.
- `path(string)` - path to scan for files to add to package.
  If None, lkey will be substituted in as the path.
- `meta(dict)` - user level metadata dict to attach to lkey directory entry.
- `update_policy(str)` - can be either 'incoming' (default) or 'existing'.
  If 'incoming', whenever logical keys match, always take the new entry from set_dir.
  If 'existing', whenever logical keys match, retain existing entries
  and ignore new entries from set_dir.
- `unversioned(bool)` - when True, do not retrieve VersionId for S3 physical keys.
  

**Returns**:

  self
  

**Raises**:

- `PackageException` - When `path` doesn't exist.
- `ValueError` - When `update_policy` is invalid.

<a id="quilt3.packages.Package.get"></a>

## Package.get(logical\_key)

Gets object from logical_key and returns its physical path.
Equivalent to self[logical_key].get().

**Arguments**:

- `logical_key(string)` - logical key of the object to get
  

**Returns**:

  Physical path as a string.
  

**Raises**:

- `KeyError` - when logical_key is not present in the package
- `ValueError` - if the logical_key points to a Package rather than PackageEntry.

<a id="quilt3.packages.Package.readme"></a>

## Package.readme()

Returns the README PackageEntry

The README is the entry with the logical key 'README.md' (case-sensitive). Will raise a QuiltException if
no such entry exists.

<a id="quilt3.packages.Package.set_meta"></a>

## Package.set\_meta(meta)

Sets user metadata on this Package.

<a id="quilt3.packages.Package.build"></a>

## Package.build(name, registry=None, message=None, \*, workflow=...)

Serializes this package to a registry.

**Arguments**:

- `name` - optional name for package
- `registry` - registry to build to
  defaults to local registry
- `message` - the commit message of the package
  %(workflow)s
  

**Returns**:

  The top hash as a string.

<a id="quilt3.packages.Package.dump"></a>

## Package.dump(writable\_file)

Serializes this package to a writable file-like object.

**Arguments**:

- `writable_file` - file-like object to write serialized package.
  

**Returns**:

  None
  

**Raises**:

  fail to create file
  fail to finish write

<a id="quilt3.packages.Package.manifest"></a>

## Package.manifest()

Provides a generator of the dicts that make up the serialized package.

<a id="quilt3.packages.Package.set"></a>

## Package.set(logical\_key, entry=None, meta=None, serialization\_location=None, serialization\_format\_opts=None, unversioned: bool = False)

Returns self with the object at logical_key set to entry.

**Arguments**:

- `logical_key(string)` - logical key to update
  entry(PackageEntry OR string OR object): new entry to place at logical_key in the package.
  If entry is a string, it is treated as a URL, and an entry is created based on it.
  If entry is None, the logical key string will be substituted as the entry value.
  If entry is an object and quilt knows how to serialize it, it will immediately be serialized and
  written to disk, either to serialization_location or to a location managed by quilt. List of types that
  Quilt can serialize is available by calling `quilt3.formats.FormatRegistry.all_supported_formats()`
- `meta(dict)` - user level metadata dict to attach to entry
- `serialization_format_opts(dict)` - Optional. If passed in, only used if entry is an object. Options to help
  Quilt understand how the object should be serialized. Useful for underspecified file formats like csv
  when content contains confusing characters. Will be passed as kwargs to the FormatHandler.serialize()
  function. See docstrings for individual FormatHandlers for full list of options -
  https://github.com/quiltdata/quilt/blob/master/api/python/quilt3/formats.py
- `serialization_location(string)` - Optional. If passed in, only used if entry is an object. Where the
  serialized object should be written, e.g. "./mydataframe.parquet"
- `unversioned(bool)` - when True, do not retrieve VersionId for S3 physical keys.
  

**Returns**:

  self

<a id="quilt3.packages.Package.delete"></a>

## Package.delete(logical\_key)

Returns self with logical_key removed.

**Returns**:

  self
  

**Raises**:

- `KeyError` - when logical_key is not present to be deleted

<a id="quilt3.packages.Package.top_hash"></a>

## Package.top\_hash()

Returns the top hash of the package.

Note that physical keys are not hashed because the package has
the same semantics regardless of where the bytes come from.

**Returns**:

  A string that represents the top hash of the package

<a id="quilt3.packages.Package.push"></a>

## Package.push(name, registry=None, dest=None, message=None, selector\_fn=None, \*, workflow=..., force: bool = False, dedupe: bool = False)

Creates a new package, or a new revision of an existing package in a
package registry in Amazon S3.

By default, any files not currently in the destination bucket are copied to
the destination S3 bucket at a path matching logical key structure. Files
in the destination bucket are not copied even if they are not located in
in the location matching the logical key. After objects are copied, a new
package manifest is package manifest is created that points to the objects
in their new locations.

The optional parameter `selector_fn` allows callers to choose which
files are copied to the destination bucket, and which retain their
existing physical key. When using selector functions, it is important to
always copy local files to S3, otherwise the resulting package will be
inaccessible to users accessing it from Amazon S3.

The Package class includes two additional built-in selector functions:

* `Package.selector_fn_copy_all` copies all files to the destination path
regardless of their current location.
* `Package.selector_fn_copy_local` copies only local files to the
destination path. Any PackageEntry's with physical keys pointing to
objects in other buckets will retain their existing physical keys in
the resulting package.

If we have a package with entries:

* `pkg["entry_1"].physical_key = s3://bucket1/folder1/entry_1`
* `pkg["entry_2"].physical_key = s3://bucket2/folder2/entry_2`

And, we call `pkg.push("user/pkg_name", registry="s3://bucket2")`, the
file referenced by `entry_1` will be copied, while the file referenced by
`entry_2` will not. The resulting package will have the following entries:

* `pkg["entry_1"].physical_key = s3://bucket2/user/pkg_name/entry_1`
* `pkg["entry_2"].physical_key = s3://bucket2/folder1/entry_2`

Quilt3 Versions 6.3.1 and earlier copied all files to the destination
path by default. To match this behavior in later versions, callers
should use `selector_fn=Package.selector_fn_copy_all`.

Using the same initial package and push, but adding
`selector_fn=Package.selector_fn_copy_all` will result in both files
being copied to the destination path, producing the following package:

* `pkg["entry_1"].physical_key = s3://bucket2/user/pkg_name/entry_1`
* `pkg["entry_2"].physical_key = s3://bucket2/user/pkg_name/entry_2`

Note that push is careful to not push data unnecessarily. To illustrate,
imagine you have a PackageEntry:
`pkg["entry_1"].physical_key = "/tmp/package_entry_1.json"`

If that entry would be pushed to `s3://bucket/prefix/entry_1.json`, but
`s3://bucket/prefix/entry_1.json` already contains the exact same bytes
as '/tmp/package_entry_1.json', `quilt3` will not push the bytes to S3,
no matter what `selector_fn('entry_1', pkg["entry_1"])` returns.

By default, push will not overwrite an existing package if its top hash does not match
the parent hash of the package being pushed. Use `force=True` to skip the check.

**Arguments**:

- `name` - name for package in registry
- `dest` - where to copy the objects in the package. Must be either an S3 URI prefix (e.g., s3://$bucket/$key)
  in the registry bucket, or a callable that takes logical_key and package_entry, and returns an S3 URI.
  (Changed in 6.0.0a1) previously top_hash was passed to the callable dest as a third argument.
- `registry` - registry where to create the new package
- `message` - the commit message for the new package
- `selector_fn` - An optional function that determines which package entries should be copied to S3.
  The function takes in two arguments, logical_key and package_entry, and should return False if that
  PackageEntry should not be copied to the destination registry during push.
  If for example you have a package where the files are spread over multiple buckets
  and you add a single local file, you can use selector_fn to only
  push the local file to S3 (instead of pushing all data to the destination bucket).
  %(workflow)s
- `force` - skip the top hash check and overwrite any existing package
- `dedupe` - don't push if the top hash matches the existing package top hash; return the current package
  

**Returns**:

  A new package that points to the copied objects.

<a id="quilt3.packages.Package.rollback"></a>

## Package.rollback(cls, name, registry, top\_hash)

Set the "latest" version to the given hash.

**Arguments**:

- `name(str)` - Name of package to rollback.
- `registry(str)` - Registry where package is located.
- `top_hash(str)` - Hash to rollback to.

<a id="quilt3.packages.Package.diff"></a>

## Package.diff(other\_pkg)

Returns three lists -- added, modified, deleted.

Added: present in other_pkg but not in self.
Modified: present in both, but different.
Deleted: present in self, but not other_pkg.

**Arguments**:

- `other_pkg` - Package to diff
  

**Returns**:

  added, modified, deleted (all lists of logical keys)

<a id="quilt3.packages.Package.map"></a>

## Package.map(f, include\_directories=False)

Performs a user-specified operation on each entry in the package.

**Arguments**:

  f(x, y): function
  The function to be applied to each package entry.
  It should take two inputs, a logical key and a PackageEntry.
- `include_directories` - bool
  Whether or not to include directory entries in the map.
  
- `Returns` - list
  The list of results generated by the map.

<a id="quilt3.packages.Package.filter"></a>

## Package.filter(f, include\_directories=False)

Applies a user-specified operation to each entry in the package,
removing results that evaluate to False from the output.

**Arguments**:

  f(x, y): function
  The function to be applied to each package entry.
  It should take two inputs, a logical key and a PackageEntry.
  This function should return a boolean.
- `include_directories` - bool
  Whether or not to include directory entries in the map.
  

**Returns**:

  A new package with entries that evaluated to False removed

<a id="quilt3.packages.Package.verify"></a>

## Package.verify(src, extra\_files\_ok=False)

Check if the contents of the given directory matches the package manifest.

**Arguments**:

- `src(str)` - URL of the directory
- `extra_files_ok(bool)` - Whether extra files in the directory should cause a failure.
  

**Returns**:

  True if the package matches the directory; False otherwise.

