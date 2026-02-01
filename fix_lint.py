import os


def fix_client_base():
    path = "src/pyseekdb/client/client_base.py"
    with open(path) as f:
        content = f.read()

    content = content.replace("from .utils import unflatten_dict", "")

    helpers = '''    def _should_include_core_field(
        self,
        field: str,
        include_key: str,
        _source: list[str] | None,
        include_fields: dict[str, bool],
        whitelist_mode: bool,
        alt_name: str | None = None,
    ) -> bool:
        """Helper to determine if a core field (document/embedding) should be included"""
        if _source is not None:
            if field in _source or (alt_name and alt_name in _source):
                return True
        if not whitelist_mode:
            if include_fields.get(include_key) or include_fields.get(field):
                return True
        return False

    def _add_metadata_projection_columns(
        self, columns: list[str], _source: list[str] | None, include_fields: dict[str, bool], whitelist_mode: bool
    ) -> None:
        """Helper to add metadata columns to projection list"""
        if _source is None:
            if include_fields.get("metadatas") or include_fields.get("metadata"):
                columns.append("metadata")
            return

        # Source selection mode
        full_meta = "metadata" in _source
        if not full_meta and not whitelist_mode:
            if include_fields.get("metadatas") or include_fields.get("metadata"):
                full_meta = True

        if full_meta:
            columns.append("metadata")

        # Partial metadata extraction (dot notation)
        for field in _source:
            if field.startswith("metadata.") and len(field) > 9:
                json_path = field[9:]
                if re.match(r"^[a-zA-Z0-9_\\.]+$", json_path):
                    columns.append(f"JSON_EXTRACT(metadata, '$.{json_path}') AS `metadata.{json_path}`")
                else:
                    logger.warning(f"Skipping invalid json path: {json_path}")

    def _merge_projected_metadata(self, row: dict[str, Any], metadata: dict[str, Any] | None) -> dict[str, Any] | None:
        """Helper to unflatten and merge metadata fields starting with 'metadata.'"""
        projected_metadata = {}
        has_projected = False
        for k, v in row.items():
            if k.startswith("metadata."):
                projected_metadata[k] = self._parse_row_value(v)
                has_projected = True

        if has_projected:
            if metadata is None:
                metadata = {}
            # Unflatten and merge
            nested = unflatten_dict(projected_metadata)
            if "metadata" in nested and isinstance(nested["metadata"], dict):
                metadata.update(nested["metadata"])
        return metadata
'''
    if "_should_include_core_field" not in content:
        content = content.replace("    def _build_projection_sql(", helpers + "\n    def _build_projection_sql(", 1)

    new_build_projection = '''    def _build_projection_sql(
        self, _source: list[str] | None, include_fields: dict[str, bool], include: list[str] | None = None
    ) -> str:
        """
        Build SQL projection clause based on _source and include parameters.
        """
        columns = []
        use_source_as_whitelist = _source is not None and include is None

        # 1. Handle document
        if self._should_include_core_field("document", "documents", _source, include_fields, use_source_as_whitelist):
            columns.append("document")

        # 2. Handle embedding
        if self._should_include_core_field(
            "embedding", "embeddings", _source, include_fields, use_source_as_whitelist, alt_name="vector"
        ):
            columns.append("embedding")

        # 3. Handle metadata
        self._add_metadata_projection_columns(columns, _source, include_fields, use_source_as_whitelist)

        return ", ".join(columns) if columns else ""'''

    old_sim1 = """            if _source is not None:
                # Check if any metadata field is requested in _source
                if "metadata" in _source or any(f.startswith("metadata.") for f in _source):
                    should_have_metadata = True"""
    new_sim1 = """            if _source is not None and ("metadata" in _source or any(f.startswith("metadata.") for f in _source)):
                should_have_metadata = True"""
    content = content.replace(old_sim1, new_sim1)

    old_sim2 = """        if _source is not None:
            if "metadata" in _source or any(f.startswith("metadata.") for f in _source):
                should_have_metadata = True"""
    new_sim2 = """        if _source is not None and ("metadata" in _source or any(f.startswith("metadata.") for f in _source)):
            should_have_metadata = True"""
    content = content.replace(old_sim2, new_sim2)

    old_process = """        # Check for partial/nested metadata fields (projected fields)
        # Scan for keys starting with "metadata."
        projected_metadata = {}
        has_projected = False
        for k, v in row.items():
            if k.startswith("metadata."):
                projected_metadata[k] = self._parse_row_value(v)
                has_projected = True

        if has_projected:
            if metadata is None:
                metadata = {}
            # Unflatten and merge
            nested = unflatten_dict(projected_metadata)
            if "metadata" in nested and isinstance(nested["metadata"], dict):
                metadata.update(nested["metadata"])"""

    new_process = """        # Check for partial/nested metadata fields (projected fields)
        metadata = self._merge_projected_metadata(row, metadata)"""

    if old_process in content:
        content = content.replace(old_process, new_process)

    start_marker = "    def _build_projection_sql("
    end_marker = "    def _build_select_clause("

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx != -1 and end_idx != -1:
        content = content[:start_idx] + new_build_projection + "\n\n" + content[end_idx:]

    with open(path, "w") as f:
        f.write(content)
    print("Fixed client_base.py")


def fix_test():
    path = "tests/integration_tests/test_source_selection.py"
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
        content = content.replace("with pytest.raises(Exception):", "with pytest.raises(TypeError):")
        with open(path, "w") as f:
            f.write(content)
        print("Fixed test_source_selection.py")


if __name__ == "__main__":
    fix_test()
    fix_client_base()
