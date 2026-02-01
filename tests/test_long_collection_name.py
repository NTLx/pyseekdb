"""
Test collection name length > 64 characters
Issue: https://github.com/oceanbase/pyseekdb/issues/121
"""
import os
import pytest
from typing import List, Union, ClassVar


class Simple3DEmbeddingFunction:
    """Simple 3D embedding function for testing"""
    def __init__(self):
        self.dimension = 3

    def __call__(self, docs: Union[str, List[str]]) -> List[List[float]]:
        if isinstance(docs, str):
            docs = [docs]
        embeddings = []
        for doc in docs:
            hash_val = hash(doc) % 1000
            embedding = [
                float((hash_val % 10) / 10.0),
                float(((hash_val // 10) % 10) / 10.0),
                float(((hash_val // 100) % 10) / 10.0)
            ]
            embeddings.append(embedding)
        return embeddings


class TestLongCollectionName:
    """Test collection operations with name > 64 chars"""

    # 测试用长名称
    LONG_NAMES: ClassVar[List[str]] = [
        "a" * 65,      # 边界值 + 1
        "b" * 128,     # 128 字符
        "c" * 512,     # 512 字符(最大)
    ]

    # Server configuration from environment variables
    SERVER_HOST = os.environ.get("SEEKDB_HOST")
    SERVER_PORT = int(os.environ.get("SEEKDB_PORT", "2881"))
    SERVER_DATABASE = os.environ.get("SEEKDB_DATABASE", "test")
    SERVER_USER = os.environ.get("SEEKDB_USER", "root")
    SERVER_PASSWORD = os.environ.get("SEEKDB_PASSWORD", "")

    @pytest.fixture
    def server_client(self):
        """Create server mode client"""
        if not self.SERVER_HOST:
            pytest.skip("SEEKDB_HOST not configured, skipping remote server tests")

        import pyseekdb
        client = pyseekdb.Client(
            host=self.SERVER_HOST,
            port=self.SERVER_PORT,
            tenant="sys",
            database=self.SERVER_DATABASE,
            user=self.SERVER_USER,
            password=self.SERVER_PASSWORD
        )
        yield client

    def test_create_collection_with_long_name(self, server_client):
        """Test create collection with name > 64 chars"""
        print("\n" + "="*60)
        print("Testing create collection with long names (>64 chars)")
        print("="*60)

        for name in self.LONG_NAMES:
            print(f"\n✅ Creating collection with name length: {len(name)}")
            collection = server_client.create_collection(
                name=name,
                embedding_function=Simple3DEmbeddingFunction()
            )
            assert collection.name == name, f"Collection name mismatch: {collection.name} != {name}"
            print(f"   Created successfully: {name[:50]}...")

            # Cleanup
            server_client.delete_collection(name=name)
            print(f"   Deleted successfully")

    @pytest.mark.xfail(reason="Bug: get_or_create implementation uses collection name as table identifier, hitting DB limit (Issue #121)")
    def test_get_or_create_collection_with_long_name(self, server_client):
        """Test get_or_create_collection with long name"""
        print("\n" + "="*60)
        print("Testing get_or_create_collection with long names")
        print("="*60)

        name = "x" * 100
        print(f"\n✅ Testing get_or_create with name length: {len(name)}")

        # First creation
        collection = server_client.get_or_create_collection(
            name=name,
            embedding_function=Simple3DEmbeddingFunction()
        )
        assert collection.name == name
        print(f"   Created: {name[:50]}...")

        # Get existing
        collection2 = server_client.get_or_create_collection(
            name=name,
            embedding_function=Simple3DEmbeddingFunction()
        )
        assert collection2.name == name
        print(f"   Retrieved existing collection successfully")

        # Cleanup
        server_client.delete_collection(name=name)
        print(f"   Cleaned up")

    def test_delete_collection_with_long_name(self, server_client):
        """Test delete collection with long name"""
        print("\n" + "="*60)
        print("Testing delete collection with long names")
        print("="*60)

        name = "y" * 200
        print(f"\n✅ Testing delete with name length: {len(name)}")

        # Create first
        server_client.create_collection(
            name=name,
            embedding_function=Simple3DEmbeddingFunction()
        )
        print(f"   Created collection")

        # Verify exists
        assert server_client.has_collection(name=name)
        print(f"   Verified collection exists")

        # Delete
        server_client.delete_collection(name=name)
        print(f"   Deleted successfully")

        # Verify deleted
        assert not server_client.has_collection(name=name)
        print(f"   Verified collection deleted")

    def test_boundary_cases_long_name(self, server_client):
        """Test boundary cases: 64, 65, 512 characters"""
        print("\n" + "="*60)
        print("Testing boundary cases (64, 65, 512 chars)")
        print("="*60)

        boundary_cases = [
            (64, "64 chars boundary"),
            (65, "65 chars (boundary + 1)"),
            (512, "512 chars (max)"),
        ]

        for length, desc in boundary_cases:
            name = "a" * length
            print(f"\n✅ Testing name length: {len(name)} ({desc})")
            collection = server_client.create_collection(
                name=name,
                embedding_function=Simple3DEmbeddingFunction()
            )
            assert len(collection.name) == length
            print(f"   Success: {name[:50]}...")
            server_client.delete_collection(name=name)
