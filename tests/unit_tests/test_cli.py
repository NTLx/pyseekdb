"""Unit tests for CLI module"""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner


class TestCLIBasics:
    """Test CLI basic structure"""

    def test_cli_module_imports(self):
        """Test that CLI module can be imported"""
        from pyseekdb.cli import main

        assert main is not None

    def test_cli_help_works(self):
        """Test that --help flag works"""
        from pyseekdb.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "PySeekDB" in result.output or "seekdb" in result.output.lower()

    def test_cli_version_flag(self):
        """Test that --version flag works"""
        from pyseekdb import __version__
        from pyseekdb.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output


class TestCollectionListCommand:
    """Test collection list command"""

    def test_collection_list_command_exists(self):
        """Test that collection list command is registered"""
        from pyseekdb.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["collection", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output

    def test_collection_list_no_collections(self):
        """Test listing when no collections exist"""
        from pyseekdb.cli import main

        runner = CliRunner()

        with patch("pyseekdb.cli.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_collections.return_value = []
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(main, ["collection", "list"])
            assert result.exit_code == 0
            assert "No collections" in result.output or "0" in result.output

    def test_collection_list_with_collections(self):
        """Test listing with existing collections"""
        from pyseekdb.cli import main

        runner = CliRunner()

        mock_collection1 = MagicMock()
        mock_collection1.name = "test_collection"
        mock_collection1.dimension = 128
        mock_collection1.count.return_value = 100

        mock_collection2 = MagicMock()
        mock_collection2.name = "another_collection"
        mock_collection2.dimension = 256
        mock_collection2.count.return_value = 50

        with patch("pyseekdb.cli.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_collections.return_value = [mock_collection1, mock_collection2]
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(main, ["collection", "list"])
            assert result.exit_code == 0
            assert "test_collection" in result.output
            assert "another_collection" in result.output


class TestCollectionInfoCommand:
    """Test collection info command"""

    def test_collection_info_command_exists(self):
        """Test that collection info command is registered"""
        from pyseekdb.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["collection", "info", "--help"])
        assert result.exit_code == 0
        assert "NAME" in result.output or "name" in result.output

    def test_collection_info_not_found(self):
        """Test info for non-existent collection"""
        from pyseekdb.cli import main

        runner = CliRunner()

        with patch("pyseekdb.cli.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_collection.side_effect = ValueError("Collection not found")
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(main, ["collection", "info", "nonexistent"])
            assert result.exit_code != 0

    def test_collection_info_success(self):
        """Test info for existing collection"""
        from pyseekdb.cli import main

        runner = CliRunner()

        mock_collection = MagicMock()
        mock_collection.name = "my_collection"
        mock_collection.dimension = 384
        mock_collection.distance = "cosine"
        mock_collection.count.return_value = 1000
        mock_collection.metadata = {"created": "2026-01-01"}
        mock_collection.peek.return_value = {
            "ids": ["id1", "id2"],
            "documents": ["doc1", "doc2"],
            "metadatas": [{}, {}],
        }

        with patch("pyseekdb.cli.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_collection.return_value = mock_collection
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(main, ["collection", "info", "my_collection"])
            assert result.exit_code == 0
            assert "my_collection" in result.output
            assert "384" in result.output
            assert "1000" in result.output


class TestCollectionDeleteCommand:
    """Test collection delete command"""

    def test_collection_delete_requires_confirmation(self):
        """Test that delete requires --yes flag or confirmation"""
        from pyseekdb.cli import main

        runner = CliRunner()

        with patch("pyseekdb.cli.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            # Without --yes, should prompt (input 'n' to abort)
            runner.invoke(main, ["collection", "delete", "test_coll"], input="n\n")
            assert mock_client.delete_collection.call_count == 0

    def test_collection_delete_with_yes_flag(self):
        """Test that delete with --yes skips confirmation"""
        from pyseekdb.cli import main

        runner = CliRunner()

        with patch("pyseekdb.cli.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(main, ["collection", "delete", "test_coll", "--yes"])
            assert result.exit_code == 0
            mock_client.delete_collection.assert_called_once_with("test_coll")


class TestCollectionCreateCommand:
    """Test collection create command"""

    def test_collection_create_basic(self):
        """Test creating a collection with required args"""
        from pyseekdb.cli import main

        runner = CliRunner()

        mock_collection = MagicMock()
        mock_collection.name = "new_collection"
        mock_collection.dimension = 128

        with patch("pyseekdb.cli.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.create_collection.return_value = mock_collection
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(main, ["collection", "create", "new_collection", "--dimension", "128"])
            assert result.exit_code == 0
            assert "new_collection" in result.output
            mock_client.create_collection.assert_called_once()

    def test_collection_create_with_distance(self):
        """Test creating a collection with custom distance metric"""
        from pyseekdb.cli import main

        runner = CliRunner()

        mock_collection = MagicMock()
        mock_collection.name = "cosine_collection"
        mock_collection.dimension = 256

        with patch("pyseekdb.cli.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.create_collection.return_value = mock_collection
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(
                main, ["collection", "create", "cosine_collection", "--dimension", "256", "--distance", "cosine"]
            )
            assert result.exit_code == 0


class TestCollectionCountCommand:
    """Test collection count command"""

    def test_collection_count_success(self):
        """Test counting records in a collection"""
        from pyseekdb.cli import main

        runner = CliRunner()

        mock_collection = MagicMock()
        mock_collection.count.return_value = 42

        with patch("pyseekdb.cli.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_collection.return_value = mock_collection
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(main, ["collection", "count", "my_collection"])
            assert result.exit_code == 0
            assert "42" in result.output


class TestPingCommand:
    """Test ping command for connection testing"""

    def test_ping_success(self):
        """Test successful connection"""
        from pyseekdb.cli import main

        runner = CliRunner()

        with patch("pyseekdb.cli.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_collections.return_value = []
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(main, ["ping"])
            assert result.exit_code == 0
            assert "success" in result.output.lower() or "connected" in result.output.lower()

    def test_ping_failure(self):
        """Test failed connection"""
        from pyseekdb.cli import main

        runner = CliRunner()

        with patch("pyseekdb.cli.Client") as mock_client_class:
            mock_client_class.return_value.__enter__ = MagicMock(side_effect=Exception("Connection refused"))
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(main, ["ping"])
            assert result.exit_code != 0
