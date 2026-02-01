import os


def fix_project():
    # 1. Fix Test File (B017)
    test_path = "tests/integration_tests/test_source_selection.py"
    if os.path.exists(test_path):
        with open(test_path) as f:
            content = f.read()
        content = content.replace("with pytest.raises(Exception):", "with pytest.raises(TypeError):")
        with open(test_path, "w") as f:
            f.write(content)
        print(f"Fixed {test_path}")

    # 2. Fix client_base.py
    client_path = "src/pyseekdb/client/client_base.py"
    if os.path.exists(client_path):
        with open(client_path) as f:
            content = f.read()

        # A. Clean bad imports
        content = content.replace("from .utils import unflatten_dict", "")

        # B. Add unflatten_dict if missing
        if "def unflatten_dict" not in content:
            import_marker = "logger = logging.getLogger(__name__)"
            unflatten_code = '''
def unflatten_dict(d: dict[str, Any], delimiter: str = ".") -> dict[str, Any]:
    """Unflatten a dictionary with delimited keys into a nested dictionary."""
    result = {}
    for key, value in d.items():
        parts = key.split(delimiter)
        target = result
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
    return result
'''
            content = content.replace(import_marker, import_marker + "\n" + unflatten_code)

        # C. Define Helper Methods to be inserted
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
        if _source is not None and (field in _source or (alt_name and alt_name in _source)):
            return True
        if not whitelist_mode and (include_fields.get(include_key) or include_fields.get(field)):
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
        if not full_meta and not whitelist_mode and (include_fields.get("metadatas") or include_fields.get("metadata")):
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
        # D. Insert helpers before _build_projection_sql
        if "_should_include_core_field" not in content:
            content = content.replace(
                "    def _build_projection_sql(", helpers + "\n\n    def _build_projection_sql(", 1
            )

        # E. Replace _build_projection_sql Body (Regex to be safe against indentation variations)
        # We replace the function definition block.
        # Original starts with def and ends with return ...

        new_projection = '''    def _build_projection_sql(
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

        # Naive replacement if precise match fails
        old_signature = "def _build_projection_sql(\n        self, _source: list[str] | None, include_fields: dict[str, bool], include: list[str] | None = None\n    ) -> str:"
        idx = content.find(old_signature)
        if idx != -1:
            # Find end of function (heuristic: next def)
            next_def = content.find("    def _build_select_clause", idx)
            if next_def != -1:
                content = content[:idx] + new_projection + "\n\n" + content[next_def:]

        # F. Replace _process_query_row logic
        old_logic = """        # Check for partial/nested metadata fields (projected fields)
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

        new_logic = """        # Check for partial/nested metadata fields (projected fields)
        metadata = self._merge_projected_metadata(row, metadata)"""

        content = content.replace(old_logic, new_logic)

        # G. Fix SIM102 Nested IFs
        sim1_old = """            if _source is not None:
                # Check if any metadata field is requested in _source
                if "metadata" in _source or any(f.startswith("metadata.") for f in _source):
                    should_have_metadata = True"""
        sim1_new = """            if _source is not None and ("metadata" in _source or any(f.startswith("metadata.") for f in _source)):
                should_have_metadata = True"""
        content = content.replace(sim1_old, sim1_new)

        sim2_old = """        if _source is not None:
            if "metadata" in _source or any(f.startswith("metadata.") for f in _source):
                should_have_metadata = True"""
        sim2_new = """        if _source is not None and ("metadata" in _source or any(f.startswith("metadata.") for f in _source)):
            should_have_metadata = True"""
        content = content.replace(sim2_old, sim2_new)

        with open(client_path, "w") as f:
            f.write(content)
        print(f"Fixed {client_path}")


if __name__ == "__main__":
    fix_project()
