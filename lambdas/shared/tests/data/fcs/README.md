<!-- markdownlint-disable first-line-h1 -->
See `FCS_flowio.ipynb` for the source of fixture files.

* `normal.fcs` is generated with `flowio.create_fcs` and should parse with full data.
* `meta_only.fcs` is generated from `normal.fcs` by corrupting `$DATATYPE` so full parsing fails but metadata-only parsing succeeds.
