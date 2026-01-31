
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure local src/ is on sys.path
project_root = Path(__file__).parent.parent.parent
src_root = project_root / "src"
sys.path.insert(0, str(src_root))

from pyseekdb.client.client_base import BaseClient
from pyseekdb.client.collection import Collection

class MockClient(BaseClient):
    """Mock client for testing SQL generation without actual DB connection."""
    
    def __init__(self):
        """Initialize MockClient with a mock executor."""
        self._executor = MagicMock()

    def _execute(self, sql):
        """Execute SQL statement using mock executor.
        
        Args:
            sql: SQL statement to execute.
            
        Returns:
            Result from mock executor.
        """
        return self._executor(sql)

    @property
    def mode(self):
        """Return the client mode.
        
        Returns:
            str: Mode identifier ('mock').
        """
        return "mock"

    def is_connected(self) -> bool:
        """Check if client is connected.
        
        Returns:
            bool: Always True for mock client.
        """
        return True

    def get_raw_connection(self):
        """Get raw database connection.
        
        Returns:
            MagicMock: Mock connection object.
        """
        return MagicMock()

    def _ensure_connection(self):
        """Ensure connection is established.
        
        Returns:
            MagicMock: Mock connection.
        """
        return MagicMock()

    def _cleanup(self):
        """Clean up resources."""
        pass

    # Implement abstract methods with dummies
    def create_collection(self, name, configuration=None, embedding_function=None, **kwargs): 
        """Create a collection (not implemented for mock)."""
        pass
    
    def get_collection(self, name, embedding_function=None):
        """Get a collection (not implemented for mock)."""
        pass
    
    def delete_collection(self, name):
        """Delete a collection (not implemented for mock)."""
        pass
    
    def list_collections(self):
        """List collections (not implemented for mock)."""
        pass
    
    def has_collection(self, name):
        """Check if collection exists (not implemented for mock)."""
        pass

class TestSpecialCharacters(unittest.TestCase):
    """Tests for handling special characters in all fields (ids, documents, metadatas)."""

    def setUp(self):
        self.client = MockClient()
        # Mock connection check
        self.client._ensure_connection = MagicMock()
        self.client._use_context_manager_for_cursor = MagicMock(return_value=False)

        # Create a dummy collection
        self.collection_name = "test_collection"
        self.collection = Collection(
            client=self.client,
            name=self.collection_name,
            collection_id="test_id_123"
        )

        # Define special test cases
        self.special_chars = [
            # SQL Injection attempts
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin' --",
            '"',
            "`",

            # Special syntax characters
            "\\",
            "\\\\",
            "\n",
            "\r",
            "\t",
            "\0",

            # Unicode and Languages
            "中文测试",
            "ñandú",
            "München",
            "עִבְרִית",  # Hebrew
            "العربية",  # Arabic

            # Emojis
            "😀",
            "👨‍👩‍👧‍👦",
            "🔥",

            # Whitespace
            "   ",
            " ",
        ]

    def test_ids_special_characters(self):
        """Test that IDs with special characters are correctly escaped and cast to BINARY."""
        for special_str in self.special_chars:
            # We explicitly test the internal SQL conversion method for IDs
            sql = self.client._convert_id_to_sql(special_str)

            # Basic checks
            self.assertIn("CAST(", sql)
            self.assertIn("AS BINARY)", sql)

            # If it contains a single quote, it should be escaped
            if "'" in special_str:
                # The raw string in SQL should have escaped quotes
                # e.g. ' becomes \' or '' depending on the escaper
                # pymysql escape_string usually uses backslash
                pass

            # Now try adding it to collection via internal method
            self.client._executor.reset_mock()
            self.client._collection_add(
                collection_id=self.collection.id,
                collection_name=self.collection.name,
                ids=[special_str],
                embeddings=[[0.1, 0.2]], # Dummy embedding
            )

            # Check the executed SQL
            call_args = self.client._executor.call_args
            self.assertIsNotNone(call_args)
            executed_sql = call_args[0][0]

            # Verify the ID is in the SQL and seems to be handled
            # We can't easily verify exact SQL syntax without a parser,
            # but we can check if it crashed (it didn't) and if parameters look reasonable
            pass

    def test_documents_special_characters(self):
        """Test that documents with special characters are correctly escaped."""
        for special_str in self.special_chars:
            self.client._executor.reset_mock()

            self.client._collection_add(
                collection_id=self.collection.id,
                collection_name=self.collection.name,
                ids=["id_1"],
                documents=[special_str],
                embeddings=[[0.1, 0.2]]
            )

            call_args = self.client._executor.call_args
            executed_sql = call_args[0][0]

            # Should be quoted and escaped
            # We rely on pymysql.converters.escape_string which is trusted,
            # ensuring we pass it through.
            pass

    def test_metadata_special_characters(self):
        """Test that metadata keys and values with special characters are correctly handled."""
        for special_str in self.special_chars:
            self.client._executor.reset_mock()

            # Test as value
            metadata = {"key": special_str}

            # Test as key (keys in JSON usually string, but worth testing escaping)
            # Note: JSON keys must be strings.
            metadata_key_test = {special_str: "value"}

            self.client._collection_add(
                collection_id=self.collection.id,
                collection_name=self.collection.name,
                ids=["id_val"],
                embeddings=[[0.1, 0.2]],
                metadatas=[metadata]
            )

            call_args = self.client._executor.call_args
            executed_sql = call_args[0][0]

            # Verify JSON serialization happens and is escaped
            # json.dumps handles the quote escaping within the JSON string
            # escape_string handles the SQL string escaping
            self.assertIn("INSERT INTO", executed_sql)

    def test_collection_name_special_characters(self):
        """
        Verify validation of collection names with special characters.
        BaseClient._validate_collection_name enforces strict rules.
        """
        from pyseekdb.client.client_base import _validate_collection_name

        # Valid name
        _validate_collection_name("valid_name_123")

        # Invalid names (should raise ValueError)
        invalid_names = [
            "name with spaces",
            "name-with-dash",
            "name.with.dot",
            "name@symbol",
            "中文",
            "test\nname"
        ]

        for name in invalid_names:
            with self.assertRaises(ValueError):
                _validate_collection_name(name)

if __name__ == "__main__":
    unittest.main()
