"""Unit tests for CLI module"""

import pytest
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
        from pyseekdb.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.0.1" in result.output or "version" in result.output.lower()
