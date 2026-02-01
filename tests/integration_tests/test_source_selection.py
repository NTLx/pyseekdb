#!/usr/bin/env python3
"""
Integration tests for _source field selection feature
Tests against real database connection: biodev.cm.com:2881
"""

import pytest

from pyseekdb import HNSWConfiguration, RemoteServerClient


class TestSourceSelection:
    """Test suite for _source field selection functionality"""

    @pytest.fixture(scope="class")
    def client(self):
        """Create database client"""
        client = RemoteServerClient(host="biodev.cm.com", port=2881, user="root", password="", database="test")
        yield client
        # Note: RemoteServerClient doesn't have close() method, connection is auto-managed

    @pytest.fixture
    def collection(self, client):
        """Create test collection with sample data"""
        collection_name = "test_source_selection"

        # Clean up if exists
        if client.has_collection(collection_name):
            client.delete_collection(collection_name)

        # Create collection
        collection = client.create_collection(
            name=collection_name,
            embedding_function=None,
            configuration=HNSWConfiguration(dimension=3, distance="cosine"),
        )

        # Insert test data with nested metadata
        test_metadata = {
            "title": "SeekDB 性能测试",
            "author": {"name": "Claude", "id": 101, "org": "Anthropic"},
            "tags": ["AI", "Database", "Vector"],
            "info": {"year": 2024, "status": "published", "nested": {"deep": {"value": "deeply_nested"}}},
            "secret": "top-secret-value",
        }

        collection.add(
            ids="doc_1",
            embeddings=[0.1, 0.2, 0.3],
            metadatas=test_metadata,
            documents="This is a test document for _source field selection.",
        )

        yield collection

        # Cleanup
        client.delete_collection(collection_name)

    # ==================== Basic Field Projection Tests ====================

    def test_source_id_only(self, collection):
        """Test: Only return ID field"""
        result = collection.get(ids="doc_1", _source=["id"])

        assert result["ids"] == ["doc_1"]
        assert result["documents"] == [None]
        assert result["metadatas"] == [{}]

    def test_source_id_and_document(self, collection):
        """Test: Return ID and document only"""
        result = collection.get(ids="doc_1", _source=["id", "document"])

        assert result["ids"] == ["doc_1"]
        assert result["documents"][0] == "This is a test document for _source field selection."
        assert result["metadatas"] == [{}]

    def test_source_all_core_fields(self, collection):
        """Test: Return all core fields (id, document, embedding)"""
        result = collection.get(ids="doc_1", _source=["id", "document", "vector"], include=["embeddings"])

        assert result["ids"] == ["doc_1"]
        assert result["documents"][0] is not None
        assert len(result["embeddings"][0]) == 3
        # Note: metadatas is not included because it was not requested in _source or include
        assert "metadatas" not in result

    # ==================== Metadata Projection Tests ====================

    def test_source_full_metadata(self, collection):
        """Test: Return full metadata object"""
        result = collection.get(ids="doc_1", _source=["metadata"])

        meta = result["metadatas"][0]
        assert "title" in meta
        assert "author" in meta
        assert "secret" in meta

    def test_source_single_metadata_field(self, collection):
        """Test: Return single top-level metadata field"""
        result = collection.get(ids="doc_1", _source=["metadata.title"])

        meta = result["metadatas"][0]
        assert meta == {"title": "SeekDB 性能测试"}

    def test_source_nested_metadata_field(self, collection):
        """Test: Return nested metadata field (2 levels)"""
        result = collection.get(ids="doc_1", _source=["metadata.author.name"])

        meta = result["metadatas"][0]
        assert meta == {"author": {"name": "Claude"}}

    def test_source_deeply_nested_metadata(self, collection):
        """Test: Return deeply nested metadata field (4 levels)"""
        result = collection.get(ids="doc_1", _source=["metadata.info.nested.deep.value"])

        meta = result["metadatas"][0]
        assert meta == {"info": {"nested": {"deep": {"value": "deeply_nested"}}}}

    def test_source_multiple_metadata_fields(self, collection):
        """Test: Return multiple metadata fields from different paths"""
        result = collection.get(ids="doc_1", _source=["metadata.title", "metadata.author.name", "metadata.info.year"])

        meta = result["metadatas"][0]
        assert "title" in meta
        assert meta["title"] == "SeekDB 性能测试"
        assert "author" in meta
        assert meta["author"]["name"] == "Claude"
        assert "info" in meta
        assert meta["info"]["year"] == 2024
        # Verify other fields are NOT present
        assert "secret" not in meta
        assert "org" not in meta.get("author", {})

    # ==================== Mixed Field Tests ====================

    def test_source_mixed_fields(self, collection):
        """Test: Mix of core fields and metadata fields"""
        result = collection.get(ids="doc_1", _source=["id", "document", "metadata.author.name"])

        assert result["ids"] == ["doc_1"]
        assert result["documents"][0] is not None
        meta = result["metadatas"][0]
        assert meta == {"author": {"name": "Claude"}}

    # ==================== Edge Cases ====================

    def test_source_empty_list(self, collection):
        """Test: Empty _source list should return only ID"""
        result = collection.get(ids="doc_1", _source=[])

        assert result["ids"] == ["doc_1"]
        assert result["documents"] == [None]
        assert result["metadatas"] == [{}]

    def test_source_nonexistent_field(self, collection):
        """Test: Non-existent metadata field returns None (silent mode)"""
        result = collection.get(ids="doc_1", _source=["metadata.nonexistent"])

        # Should not raise error, should return empty metadata
        meta = result["metadatas"][0]
        # JSON_EXTRACT returns NULL for non-existent paths
        assert meta == {} or meta.get("nonexistent") is None

    def test_source_invalid_characters(self, collection):
        """Test: Invalid characters in field path are rejected"""
        # This should skip invalid fields due to regex validation
        result = collection.get(ids="doc_1", _source=["metadata.title", "metadata.author'; DROP TABLE--"])

        # Should only return title, malicious path should be skipped
        meta = result["metadatas"][0]
        assert "title" in meta
        # Verify no SQL injection occurred (collection still exists)
        assert collection.count() == 1

    # ==================== Backward Compatibility Tests ====================

    def test_no_source_with_include(self, collection):
        """Test: Backward compatibility - no _source parameter"""
        result = collection.get(ids="doc_1", include=["documents", "metadatas"])

        assert result["ids"] == ["doc_1"]
        assert result["documents"][0] is not None
        meta = result["metadatas"][0]
        # Should return full metadata
        assert "secret" in meta
        assert "author" in meta

    def test_source_and_include_merge(self, collection):
        """Test: _source and include work together (additive)"""
        result = collection.get(ids="doc_1", _source=["metadata.title"], include=["documents"])

        assert result["documents"][0] is not None
        meta = result["metadatas"][0]
        assert meta == {"title": "SeekDB 性能测试"}

    # ==================== Query Method Tests ====================

    def test_query_with_source(self, collection):
        """Test: query() method supports _source"""
        result = collection.query(
            query_embeddings=[0.1, 0.2, 0.3], n_results=1, _source=["metadata.title", "metadata.author.name"]
        )

        assert len(result["ids"]) == 1
        assert len(result["ids"][0]) == 1
        meta = result["metadatas"][0][0]
        assert "title" in meta
        assert "author" in meta
        assert meta["author"]["name"] == "Claude"
        # Verify secret is NOT returned
        assert "secret" not in meta

    def test_query_source_document_only(self, collection):
        """Test: query() with document only"""
        result = collection.query(query_embeddings=[0.1, 0.2, 0.3], n_results=1, _source=["document"])

        assert result["documents"][0][0] is not None
        assert result["metadatas"][0] == [{}]

    # ==================== Performance & Scale Tests ====================

    def test_source_many_fields(self, collection):
        """Test: Requesting many nested fields simultaneously"""
        result = collection.get(
            ids="doc_1",
            _source=[
                "metadata.title",
                "metadata.author.name",
                "metadata.author.id",
                "metadata.author.org",
                "metadata.info.year",
                "metadata.info.status",
            ],
        )

        meta = result["metadatas"][0]
        assert "title" in meta
        assert "author" in meta
        assert len(meta["author"]) == 3  # name, id, org
        assert "info" in meta
        assert len(meta["info"]) == 2  # year, status

    # ==================== Array Field Tests ====================

    def test_source_array_field(self, collection):
        """Test: Extracting array field from metadata"""
        result = collection.get(ids="doc_1", _source=["metadata.tags"])

        meta = result["metadatas"][0]
        assert "tags" in meta
        assert meta["tags"] == ["AI", "Database", "Vector"]

    # ==================== Type Validation Tests ====================

    def test_source_invalid_type_string(self, collection):
        """Test: _source must be list, not string"""
        with pytest.raises(TypeError):
            # This should fail because _source expects list[str]
            collection.get(ids="doc_1", _source="metadata.title")

    def test_source_invalid_type_dict(self, collection):
        """Test: _source must be list, not dict"""
        with pytest.raises(TypeError):
            collection.get(ids="doc_1", _source={"metadata": ["title"]})


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
