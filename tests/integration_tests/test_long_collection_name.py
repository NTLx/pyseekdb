"""
Test collection name length > 64 characters
测试 collection name 长度超过 64 字符的情况

Issue: https://github.com/oceanbase/pyseekdb/issues/121
"""
import pytest
import os
from typing import List, Union


class Simple3DEmbeddingFunction:
    """Simple 3D embedding function for testing"""
    
    def __init__(self):
        self.dimension = 3

    def __call__(self, input: Union[str, List[str]]) -> List[List[float]]:
        if isinstance(input, str):
            input = [input]
        embeddings = []
        for doc in input:
            hash_val = hash(doc) % 1000
            embedding = [
                float((hash_val % 10) / 10.0),
                float(((hash_val // 10) % 10) / 10.0),
                float(((hash_val // 100) / 10. % 10)0)
            ]
            embeddings.append(embedding)
        return embeddings


class TestLongCollectionName:
    """Test collection operations with name > 64 chars"""
    
    # 测试用长名称
    LONG_NAMES = [
        "a" * 65,      # 边界值 + 1
        "b" * 128,     # 128 字符
        "c" * 512,     # 512 字符（最大）
    ]

    @pytest.fixture
    def server_client(self):
        """Create server mode client from environment variables"""
        import pyseekdb
        
        # Get configuration from environment variables with defaults
        host = os.environ.get('SERVER_HOST', '127.0.0.1')
        port = int(os.environ.get('SERVER_PORT', '2881'))
        database = os.environ.get('SERVER_DATABASE', 'test')
        user = os.environ.get('SERVER_USER', 'root')
        password = os.environ.get('SERVER_PASSWORD', '')
        
        # Skip if host is not configured
        if not host:
            pytest.skip("SERVER_HOST not configured")
        
        client = pyseekdb.Client(
            host=host,
            port=port,
            tenant="sys",
            database=database,
            user=user,
            password=password
        )
        yield client
        
        # Cleanup: close client connection if method exists
        if hasattr(client, 'close'):
            client.close()

    def test_create_collection_with_long_name(self, server_client):
        """Test create collection with name > 64 chars"""
        print("\n" + "="*60)
        print("Testing create collection with long names (>64 chars)")
        print("="*60)

        for name in self.LONG_NAMES:
            print(f"\n✅ Creating collection with name length: {len(name)}")
            try:
                collection = server_client.create_collection(
                    name=name,
                    embedding_function=Simple3DEmbeddingFunction()
                )
                assert collection.name == name, f"Collection name mismatch: {collection.name} != {name}"
                print(f"   Created successfully: {name[:50]}...")
            finally:
                # Cleanup regardless of result
                if server_client.has_collection(name=name):
                    server_client.delete_collection(name=name)
                    print("   Deleted successfully")

    @pytest.mark.xfail(reason="Bug: get_or_create implementation uses collection name as table identifier, hitting DB limit (Issue #121)")
    def test_get_or_create_collection_with_long_name(self, server_client):
        """Test get_or_create_collection with long name"""
        print("\n" + "="*60)
        print("Testing get_or_create_collection with long names")
        print("="*60)

        name = "x" * 100
        print(f"\n✅ Testing get_or_create with name length: {len(name)}")

        try:
            # First creation
            collection = server_client.get_or_create_collection(
                name=name,
                embedding_function=Simple3DEmbeddingFunction()
            )
            assert collection.name == name
            print("   Created collection")

            # Get existing
            collection2 = server_client.get_or_create_collection(
                name=name,
                embedding_function=Simple3DEmbeddingFunction()
            )
            assert collection2.name == name
            print("   Retrieved existing collection successfully")
        finally:
            # Cleanup
            if server_client.has_collection(name=name):
                server_client.delete_collection(name=name)
                print("   Cleaned up")

    def test_delete_collection_with_long_name(self, server_client):
        """Test delete collection with long name"""
        print("\n" + "="*60)
        print("Testing delete collection with long names")
        print("="*60)

        name = "y" * 200
        print(f"\n✅ Testing delete with name length: {len(name)}")

        try:
            # Create first
            server_client.create_collection(
                name=name,
                embedding_function=Simple3DEmbeddingFunction()
            )
            print("   Created collection")

            # Verify exists
            assert server_client.has_collection(name=name)
            print("   Verified collection exists")

            # Delete
            server_client.delete_collection(name=name)
            print("   Deleted successfully")

            # Verify deleted
            assert not server_client.has_collection(name=name)
            print("   Verified collection deleted")
        except Exception as e:
            # Cleanup on failure
            if server_client.has_collection(name=name):
                server_client.delete_collection(name=name)
            raise

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
            try:
                collection = server_client.create_collection(
                    name=name,
                    embedding_function=Simple3DEmbeddingFunction()
                )
                assert len(collection.name) == length
                print(f"   Success: {name[:50]}...")
            finally:
                # Cleanup
                if server_client.has_collection(name=name):
                    server_client.delete_collection(name=name)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("pyseekdb - Long Collection Name Tests")
    print("="*60)
    print(f"\nEnvironment Configuration:")
    print(f"  Server: {os.environ.get('SERVER_HOST', '127.0.0.1')}:{os.environ.get('SERVER_PORT', '2881')}")
    print(f"  Database: {os.environ.get('SERVER_DATABASE', 'test')}")
    print("="*60 + "\n")
    pytest.main([__file__, "-v", "-s"])
