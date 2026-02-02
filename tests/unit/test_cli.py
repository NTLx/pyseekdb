"""
Tests for pyseekdb CLI tool.
"""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner

from pyseekdb.cli import cli, list_collections, collection_info, delete_collection


class TestCLICollections:
    """Test cases for CLI collection management commands."""

    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_client(self):
        """Create a mock client."""
        mock = Mock()
        mock.list_collections.return_value = [
            {"id": 1, "name": "test_collection", "count": 100, "status": "READY"},
            {"id": 2, "name": "another_collection", "count": 50, "status": "READY"},
        ]
        return mock

    def test_list_collections_empty(self, runner, mock_client):
        """Test listing collections when none exist."""
        mock_client.list_collections.return_value = []
        
        with patch("pyseekdb.cli._get_client", return_value=mock_client):
            result = runner.invoke(list_collections, [], obj={})
        
        assert result.exit_code == 0
        assert "No collections found" in result.output

    def test_list_collections_with_data(self, runner, mock_client):
        """Test listing collections with data."""
        with patch("pyseekdb.cli._get_client", return_value=mock_client):
            result = runner.invoke(list_collections, [], obj={})
        
        assert result.exit_code == 0
        assert "test_collection" in result.output
        assert "another_collection" in result.output

    def test_collection_info_not_found(self, runner, mock_client):
        """Test getting info for non-existent collection."""
        mock_client.get_collection.return_value = None
        
        with patch("pyseekdb.cli._get_client", return_value=mock_client):
            result = runner.invoke(
                collection_info,
                ["nonexistent_collection"],
                obj={}
            )
        
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_delete_collection_confirmed(self, runner, mock_client):
        """Test deleting collection with confirmation."""
        mock_client.get_collection.return_value = Mock()
        mock_collection = Mock()
        mock_collection.count.return_value = 10
        mock_client.get_collection.return_value = mock_collection
        
        with patch("pyseekdb.cli._get_client", return_value=mock_client):
            with patch("pyseekdb.cli.click.confirm", return_value=True):
                result = runner.invoke(
                    delete_collection,
                    ["test_collection"],
                    obj={}
                )
        
        assert result.exit_code == 0
        mock_client.delete_collection.assert_called_once_with("test_collection")

    def test_delete_collection_cancelled(self, runner, mock_client):
        """Test cancelling collection deletion."""
        mock_collection = Mock()
        mock_collection.count.return_value = 10
        mock_client.get_collection.return_value = mock_collection

        with patch("pyseekdb.cli._get_client", return_value=mock_client):
            with patch("pyseekdb.cli.click.confirm", return_value=False):
                result = runner.invoke(
                    delete_collection,
                    ["test_collection"],
                    obj={}
                )
        
        assert result.exit_code == 0
        assert "cancelled" in result.output
        mock_client.delete_collection.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
