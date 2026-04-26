<a id="quilt3.admin.api_keys"></a>

# api\_keys

Admin API for managing API keys.

<a id="quilt3.admin.api_keys.list"></a>

## list(email: T.Optional[str] = None, key\_name: T.Optional[str] = None, fingerprint: T.Optional[str] = None, status: T.Optional[APIKeyStatus] = None)

List API keys. Optionally filter by user email, key name, fingerprint, or status.

**Arguments**:

- `email` - Filter by user email.
- `key_name` - Filter by key name.
- `fingerprint` - Filter by key fingerprint.
- `status` - Filter by "ACTIVE" or "EXPIRED". None returns all.
  

**Returns**:

  List of API keys matching the filters.

<a id="quilt3.admin.api_keys.get"></a>

## get(id: str)

Get a specific API key by ID.

**Arguments**:

- `id` - The API key ID.
  

**Returns**:

  The API key, or None if not found.

<a id="quilt3.admin.api_keys.revoke"></a>

## revoke(id: str)

Revoke an API key.

**Arguments**:

- `id` - The API key ID to revoke.
  

**Raises**:

- `Quilt3AdminError` - If the operation fails.

<a id="quilt3.admin.types"></a>

# types

<a id="quilt3.admin.types.PolicySummary"></a>

# PolicySummary

Policy without back-references to roles (avoids circular nesting).

<a id="quilt3.admin.tabulator"></a>

# tabulator

<a id="quilt3.admin.tabulator.list_tables"></a>

## list\_tables(bucket\_name: str)

List all tabulator tables in a bucket.

<a id="quilt3.admin.tabulator.set_table"></a>

## set\_table(bucket\_name: str, table\_name: str, config: T.Optional[str])

Set the tabulator table configuration. Pass `None` to remove the table.

<a id="quilt3.admin.tabulator.rename_table"></a>

## rename\_table(bucket\_name: str, table\_name: str, new\_table\_name: str)

Rename tabulator table.

<a id="quilt3.admin.tabulator.get_open_query"></a>

## get\_open\_query()

Get the **open query** status.

<a id="quilt3.admin.tabulator.set_open_query"></a>

## set\_open\_query(enabled: bool)

Set the **open query** status.

<a id="quilt3.admin.roles"></a>

# roles

<a id="quilt3.admin.roles.get"></a>

## get(id\_or\_name: str)

Get a role by ID or name. Return `None` if the role does not exist.

**Arguments**:

- `id_or_name` - Role ID or name.

<a id="quilt3.admin.roles.get_default"></a>

## get\_default()

Get the default role from the registry. Return `None` if no default role is set.

<a id="quilt3.admin.roles.list"></a>

## list()

Get a list of all roles in the registry.

<a id="quilt3.admin.roles.create_managed"></a>

## create\_managed(name: str, policies: T.List[str] = ())

Create a managed role in the registry.

**Arguments**:

- `name` - Role name.
- `policies` - Policy IDs to attach to the role.

<a id="quilt3.admin.roles.create_unmanaged"></a>

## create\_unmanaged(name: str, arn: str)

Create an unmanaged role in the registry.

**Arguments**:

- `name` - Role name.
- `arn` - Existing IAM role ARN.

<a id="quilt3.admin.roles.update_managed"></a>

## update\_managed(id\_or\_name: str, \*, name: str, policies: T.List[str])

Update a managed role in the registry (full replacement).

**Arguments**:

- `id_or_name` - Role ID or name.
- `name` - New role name.
- `policies` - Policy IDs to attach to the role.

<a id="quilt3.admin.roles.update_unmanaged"></a>

## update\_unmanaged(id\_or\_name: str, \*, name: str, arn: str)

Update an unmanaged role in the registry (full replacement).

**Arguments**:

- `id_or_name` - Role ID or name.
- `name` - New role name.
- `arn` - Existing IAM role ARN.

<a id="quilt3.admin.roles.patch_managed"></a>

## patch\_managed(id\_or\_name: str, \*, name: T.Optional[str] = None, policies: T.Optional[T.List[str]] = None)

Partially update a managed role — only specified fields are changed.

**Arguments**:

- `id_or_name` - Role ID or name.
- `name` - New role name (keeps current if not specified).
- `policies` - Policy IDs to attach (keeps current if not specified).

<a id="quilt3.admin.roles.patch_unmanaged"></a>

## patch\_unmanaged(id\_or\_name: str, \*, name: T.Optional[str] = None, arn: T.Optional[str] = None)

Partially update an unmanaged role — only specified fields are changed.

**Arguments**:

- `id_or_name` - Role ID or name.
- `name` - New role name (keeps current if not specified).
- `arn` - New IAM role ARN (keeps current if not specified).

<a id="quilt3.admin.roles.delete"></a>

## delete(id\_or\_name: str)

Delete a role from the registry.

**Arguments**:

- `id_or_name` - Role ID or name.

<a id="quilt3.admin.roles.set_default"></a>

## set\_default(id\_or\_name: str)

Set the default role in the registry.

**Arguments**:

- `id_or_name` - Role ID or name.

<a id="quilt3.admin.sso_config"></a>

# sso\_config

<a id="quilt3.admin.sso_config.get"></a>

## get()

Get the current SSO configuration.

<a id="quilt3.admin.sso_config.set"></a>

## set(config: T.Optional[str])

Set the SSO configuration. Pass `None` to remove SSO configuration.

<a id="quilt3.admin.users"></a>

# users

<a id="quilt3.admin.users.get"></a>

## get(name: str)

Get a specific user from the registry. Return `None` if the user does not exist.

**Arguments**:

- `name` - Username of user to get.

<a id="quilt3.admin.users.list"></a>

## list()

Get a list of all users in the registry.

<a id="quilt3.admin.users.create"></a>

## create(name: str, email: str, role: str, extra\_roles: T.Optional[T.List[str]] = None)

Create a new user in the registry.

**Arguments**:

- `name` - Username of user to create.
- `email` - Email of user to create.
- `role` - Active role of the user.
- `extra_roles` - Additional roles to assign to the user.

<a id="quilt3.admin.users.delete"></a>

## delete(name: str)

Delete user from the registry.

**Arguments**:

- `name` - Username of user to delete.

<a id="quilt3.admin.users.set_email"></a>

## set\_email(name: str, email: str)

Set the email for a user.

**Arguments**:

- `name` - Username of user to update.
- `email` - Email to set for the user.

<a id="quilt3.admin.users.set_admin"></a>

## set\_admin(name: str, admin: bool)

Set the admin status for a user.

**Arguments**:

- `name` - Username of user to update.
- `admin` - Admin status to set for the user.

<a id="quilt3.admin.users.set_active"></a>

## set\_active(name: str, active: bool)

Set the active status for a user.

**Arguments**:

- `name` - Username of user to update.
- `active` - Active status to set for the user.

<a id="quilt3.admin.users.reset_password"></a>

## reset\_password(name: str)

Reset the password for a user.

**Arguments**:

- `name` - Username of user to update.

<a id="quilt3.admin.users.set_role"></a>

## set\_role(name: str, role: str, extra\_roles: T.Optional[T.List[str]] = None, \*, append: bool = False)

Set the active and extra roles for a user.

**Arguments**:

- `name` - Username of user to update.
- `role` - Role to be set as the active role.
- `extra_roles` - Additional roles to assign to the user.
- `append` - If True, append the extra roles to the existing roles. If False, replace the existing roles.

<a id="quilt3.admin.users.add_roles"></a>

## add\_roles(name: str, roles: T.List[str])

Add roles to a user.

**Arguments**:

- `name` - Username of user to update.
- `roles` - Roles to add to the user.

<a id="quilt3.admin.users.remove_roles"></a>

## remove\_roles(name: str, roles: T.List[str], fallback: T.Optional[str] = None)

Remove roles from a user.

**Arguments**:

- `name` - Username of user to update.
- `roles` - Roles to remove from the user.
- `fallback` - If set, the role to assign to the user if the active role is removed.

<a id="quilt3.admin.buckets"></a>

# buckets

<a id="quilt3.admin.buckets.get"></a>

## get(name: str)

Get a specific bucket configuration from the registry.
Returns `None` if the bucket does not exist.

**Arguments**:

- `name` - Name of the bucket to get.

<a id="quilt3.admin.buckets.list"></a>

## list()

List all bucket configurations in the registry.

<a id="quilt3.admin.buckets.add"></a>

## add(name: str, title: str, \*, description: T.Optional[str] = None, icon\_url: T.Optional[str] = None, overview\_url: T.Optional[str] = None, tags: T.Optional[T.List[str]] = None, relevance\_score: T.Optional[int] = None, sns\_notification\_arn: T.Optional[str] = None, scanner\_parallel\_shards\_depth: T.Optional[int] = None, skip\_meta\_data\_indexing: T.Optional[bool] = None, file\_extensions\_to\_index: T.Optional[T.List[str]] = None, index\_content\_bytes: T.Optional[int] = None, delay\_scan: T.Optional[bool] = None, browsable: T.Optional[bool] = None, prefixes: T.Optional[T.List[str]] = None)

Add a new bucket to the registry.

**Arguments**:

- `name` - S3 bucket name.
- `title` - Display title for the bucket.
- `description` - Optional description.
- `icon_url` - Optional URL for bucket icon.
- `overview_url` - Optional URL for bucket overview page.
- `tags` - Optional list of tags.
- `relevance_score` - Optional relevance score for bucket ordering.
- `sns_notification_arn` - Optional SNS topic ARN for notifications.
- `scanner_parallel_shards_depth` - Optional depth for parallel scanning.
- `skip_meta_data_indexing` - If True, skip metadata indexing.
- `file_extensions_to_index` - Optional list of file extensions to index content.
- `index_content_bytes` - Optional max bytes of content to index.
- `delay_scan` - If True, delay initial bucket scan.
- `browsable` - If True, bucket is browsable.
- `prefixes` - Optional list of S3 prefixes to scope bucket access to.
  If provided, only these prefixes will be indexed and verified for access.

<a id="quilt3.admin.buckets.update"></a>

## update(name: str, title: str, \*, description: T.Optional[str] = None, icon\_url: T.Optional[str] = None, overview\_url: T.Optional[str] = None, tags: T.Optional[T.List[str]] = None, relevance\_score: T.Optional[int] = None, sns\_notification\_arn: T.Optional[str] = None, scanner\_parallel\_shards\_depth: T.Optional[int] = None, skip\_meta\_data\_indexing: T.Optional[bool] = None, file\_extensions\_to\_index: T.Optional[T.List[str]] = None, index\_content\_bytes: T.Optional[int] = None, browsable: T.Optional[bool] = None, prefixes: T.Optional[T.List[str]] = None)

Update an existing bucket configuration.

**Arguments**:

- `name` - S3 bucket name.
- `title` - Display title for the bucket.
- `description` - Optional description.
- `icon_url` - Optional URL for bucket icon.
- `overview_url` - Optional URL for bucket overview page.
- `tags` - Optional list of tags.
- `relevance_score` - Optional relevance score for bucket ordering.
- `sns_notification_arn` - Optional SNS topic ARN for notifications.
- `scanner_parallel_shards_depth` - Optional depth for parallel scanning.
- `skip_meta_data_indexing` - If True, skip metadata indexing.
- `file_extensions_to_index` - Optional list of file extensions to index content.
- `index_content_bytes` - Optional max bytes of content to index.
- `browsable` - If True, bucket is browsable.
- `prefixes` - Optional list of S3 prefixes to scope bucket access to.
  If provided, only these prefixes will be indexed and verified for access.
  Changing prefixes will trigger permission re-verification.

<a id="quilt3.admin.buckets.remove"></a>

## remove(name: str)

Remove a bucket from the registry.

**Arguments**:

- `name` - Name of the bucket to remove.

