# PySeekDB CLI Collection Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Design and implement a CLI tool for inspecting and managing SeekDB collections, providing a developer-friendly interface for common operations.

**Architecture:** The CLI will be built using Python's `click` library, providing a hierarchical command structure (`seekdb collection list`, `seekdb collection info`, etc.). It connects to SeekDB via the existing `RemoteServerClient`, reading connection parameters from environment variables or command-line options.

**Tech Stack:** Python 3.11+, click (CLI framework), rich (terminal formatting), existing pyseekdb client library

---

## Task 1: Add CLI Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add click and rich to dependencies**

Edit `pyproject.toml` to add CLI dependencies:

```toml
dependencies = [
    "pymysql>=1.1.1",
    "pylibseekdb; sys_platform == \"linux\"",
    "onnxruntime>=1.19.0",
    "tokenizers>=0.15.0",
    "httpx",
    "tqdm",
    "tenacity",
    "numpy>=1.26",
    "click>=8.1.0",
    "rich>=13.0.0",
]
```

**Step 2: Add console script entry point**

Add after `[project.urls]` section:

```toml
[project.scripts]
seekdb = "pyseekdb.cli:main"
```

**Step 3: Sync dependencies**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && proxy && uv sync`
Expected: Dependencies installed successfully

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "build: add click and rich dependencies for CLI tool"
```

---

## Task 2: Create CLI Module Structure with Basic Commands

**Files:**
- Create: `src/pyseekdb/cli.py`
- Test: `tests/unit_tests/test_cli.py`

**Step 1: Write the failing test for CLI module import**

Create `tests/unit_tests/test_cli.py`:

```python
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
        assert "1.0.0" in result.output or "version" in result.output.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'pyseekdb.cli'"

**Step 3: Write minimal CLI implementation**

Create `src/pyseekdb/cli.py`:

```python
"""
PySeekDB Command Line Interface

A CLI tool for inspecting and managing SeekDB collections.
"""

import click

from pyseekdb import __version__


@click.group()
@click.version_option(version=__version__, prog_name="seekdb")
@click.option(
    "--host",
    envvar="SEEKDB_HOST",
    default="127.0.0.1",
    help="SeekDB server host (env: SEEKDB_HOST)",
)
@click.option(
    "--port",
    envvar="SEEKDB_PORT",
    default=2881,
    type=int,
    help="SeekDB server port (env: SEEKDB_PORT)",
)
@click.option(
    "--user",
    envvar="SEEKDB_USER",
    default="root@test",
    help="Database user (env: SEEKDB_USER)",
)
@click.option(
    "--password",
    envvar="SEEKDB_PASSWORD",
    default="",
    help="Database password (env: SEEKDB_PASSWORD)",
)
@click.option(
    "--database",
    envvar="SEEKDB_DATABASE",
    default="test",
    help="Database name (env: SEEKDB_DATABASE)",
)
@click.pass_context
def main(ctx, host, port, user, password, database):
    """PySeekDB CLI - Manage and inspect SeekDB collections.

    Connection can be configured via command-line options or environment variables:

    \b
    SEEKDB_HOST     - Server hostname (default: 127.0.0.1)
    SEEKDB_PORT     - Server port (default: 2881)
    SEEKDB_USER     - Database user (default: root@test)
    SEEKDB_PASSWORD - Database password
    SEEKDB_DATABASE - Database name (default: test)
    """
    ctx.ensure_object(dict)
    ctx.obj["connection"] = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/pyseekdb/cli.py tests/unit_tests/test_cli.py
git commit -m "feat(cli): add basic CLI structure with click"
```

---

## Task 3: Implement `collection list` Command

**Files:**
- Modify: `src/pyseekdb/cli.py`
- Modify: `tests/unit_tests/test_cli.py`

**Step 1: Write the failing test for collection list**

Add to `tests/unit_tests/test_cli.py`:

```python
from unittest.mock import MagicMock, patch


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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestCollectionListCommand -v`
Expected: FAIL with "No such command 'collection'"

**Step 3: Implement collection list command**

Add to `src/pyseekdb/cli.py` after the `main` function:

```python
from rich.console import Console
from rich.table import Table

from pyseekdb import Client


def get_client(ctx):
    """Create a client from context connection info."""
    conn = ctx.obj["connection"]
    return Client(
        mode="server",
        host=conn["host"],
        port=conn["port"],
        user=conn["user"],
        password=conn["password"],
        database=conn["database"],
    )


@main.group()
def collection():
    """Manage collections."""
    pass


@collection.command("list")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def collection_list(ctx, output_format):
    """List all collections in the database."""
    console = Console()

    try:
        with get_client(ctx) as client:
            collections = client.list_collections()

            if not collections:
                console.print("[yellow]No collections found.[/yellow]")
                return

            if output_format == "json":
                import json
                data = []
                for coll in collections:
                    try:
                        count = coll.count()
                    except Exception:
                        count = "N/A"
                    data.append({
                        "name": coll.name,
                        "dimension": coll.dimension,
                        "count": count,
                    })
                console.print(json.dumps(data, indent=2))
            else:
                table = Table(title="Collections")
                table.add_column("Name", style="cyan", no_wrap=True)
                table.add_column("Dimension", justify="right", style="green")
                table.add_column("Count", justify="right", style="magenta")

                for coll in collections:
                    try:
                        count = str(coll.count())
                    except Exception:
                        count = "N/A"
                    table.add_row(coll.name, str(coll.dimension or "N/A"), count)

                console.print(table)
                console.print(f"\n[dim]Total: {len(collections)} collection(s)[/dim]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestCollectionListCommand -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/pyseekdb/cli.py tests/unit_tests/test_cli.py
git commit -m "feat(cli): add 'collection list' command with table/json output"
```

---

## Task 4: Implement `collection info` Command

**Files:**
- Modify: `src/pyseekdb/cli.py`
- Modify: `tests/unit_tests/test_cli.py`

**Step 1: Write the failing test for collection info**

Add to `tests/unit_tests/test_cli.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestCollectionInfoCommand -v`
Expected: FAIL with "No such command 'info'"

**Step 3: Implement collection info command**

Add to `src/pyseekdb/cli.py` after the `collection_list` function:

```python
from rich.panel import Panel
from rich.text import Text


@collection.command("info")
@click.argument("name")
@click.option("--peek", "peek_count", default=0, type=int, help="Preview N records (default: 0)")
@click.pass_context
def collection_info(ctx, name, peek_count):
    """Show detailed information about a collection.

    NAME is the collection name to inspect.
    """
    console = Console()

    try:
        with get_client(ctx) as client:
            try:
                coll = client.get_collection(name)
            except Exception as e:
                console.print(f"[red]Error:[/red] Collection '{name}' not found: {e}")
                raise SystemExit(1)

            # Build info display
            info_text = Text()
            info_text.append("Name: ", style="bold")
            info_text.append(f"{coll.name}\n", style="cyan")
            info_text.append("Dimension: ", style="bold")
            info_text.append(f"{coll.dimension or 'N/A'}\n", style="green")
            info_text.append("Distance: ", style="bold")
            info_text.append(f"{coll.distance or 'N/A'}\n", style="yellow")

            try:
                count = coll.count()
                info_text.append("Count: ", style="bold")
                info_text.append(f"{count}\n", style="magenta")
            except Exception:
                info_text.append("Count: ", style="bold")
                info_text.append("N/A\n", style="dim")

            if coll.metadata:
                info_text.append("Metadata: ", style="bold")
                info_text.append(f"{coll.metadata}\n", style="dim")

            console.print(Panel(info_text, title=f"Collection: {name}", border_style="blue"))

            # Peek records if requested
            if peek_count > 0:
                console.print(f"\n[bold]Sample Records (first {peek_count}):[/bold]")
                try:
                    records = coll.peek(limit=peek_count)
                    if records.get("ids"):
                        table = Table()
                        table.add_column("ID", style="cyan")
                        table.add_column("Document", style="white", max_width=50)
                        table.add_column("Metadata", style="dim")

                        for i, id_ in enumerate(records["ids"]):
                            doc = records.get("documents", ["N/A"] * len(records["ids"]))[i]
                            meta = records.get("metadatas", [{}] * len(records["ids"]))[i]
                            # Truncate long documents
                            if doc and len(doc) > 50:
                                doc = doc[:47] + "..."
                            table.add_row(str(id_), str(doc), str(meta))

                        console.print(table)
                    else:
                        console.print("[yellow]No records found.[/yellow]")
                except Exception as e:
                    console.print(f"[red]Error peeking records:[/red] {e}")
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestCollectionInfoCommand -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/pyseekdb/cli.py tests/unit_tests/test_cli.py
git commit -m "feat(cli): add 'collection info' command with peek option"
```

---

## Task 5: Implement `collection delete` Command

**Files:**
- Modify: `src/pyseekdb/cli.py`
- Modify: `tests/unit_tests/test_cli.py`

**Step 1: Write the failing test for collection delete**

Add to `tests/unit_tests/test_cli.py`:

```python
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
            result = runner.invoke(main, ["collection", "delete", "test_coll"], input="n\n")
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestCollectionDeleteCommand -v`
Expected: FAIL with "No such command 'delete'"

**Step 3: Implement collection delete command**

Add to `src/pyseekdb/cli.py`:

```python
@collection.command("delete")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def collection_delete(ctx, name, yes):
    """Delete a collection.

    NAME is the collection name to delete.

    WARNING: This operation is irreversible!
    """
    console = Console()

    if not yes:
        console.print(f"[yellow]Warning:[/yellow] You are about to delete collection '[bold]{name}[/bold]'")
        console.print("[red]This action cannot be undone![/red]")
        if not click.confirm("Are you sure?"):
            console.print("[dim]Aborted.[/dim]")
            return

    try:
        with get_client(ctx) as client:
            client.delete_collection(name)
            console.print(f"[green]Successfully deleted collection '[bold]{name}[/bold]'[/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestCollectionDeleteCommand -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/pyseekdb/cli.py tests/unit_tests/test_cli.py
git commit -m "feat(cli): add 'collection delete' command with safety confirmation"
```

---

## Task 6: Implement `collection create` Command

**Files:**
- Modify: `src/pyseekdb/cli.py`
- Modify: `tests/unit_tests/test_cli.py`

**Step 1: Write the failing test for collection create**

Add to `tests/unit_tests/test_cli.py`:

```python
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

            result = runner.invoke(main, [
                "collection", "create", "new_collection",
                "--dimension", "128"
            ])
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

            result = runner.invoke(main, [
                "collection", "create", "cosine_collection",
                "--dimension", "256",
                "--distance", "cosine"
            ])
            assert result.exit_code == 0
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestCollectionCreateCommand -v`
Expected: FAIL with "No such command 'create'"

**Step 3: Implement collection create command**

Add to `src/pyseekdb/cli.py`:

```python
from pyseekdb import HNSWConfiguration


@collection.command("create")
@click.argument("name")
@click.option("--dimension", "-d", type=int, required=True, help="Vector dimension (required)")
@click.option(
    "--distance",
    type=click.Choice(["l2", "cosine", "inner_product"]),
    default="l2",
    help="Distance metric (default: l2)",
)
@click.pass_context
def collection_create(ctx, name, dimension, distance):
    """Create a new collection.

    NAME is the collection name to create.
    """
    console = Console()

    try:
        with get_client(ctx) as client:
            config = HNSWConfiguration(dimension=dimension, distance=distance)
            coll = client.create_collection(name, configuration=config)
            console.print(f"[green]Successfully created collection '[bold]{coll.name}[/bold]'[/green]")
            console.print(f"  Dimension: {dimension}")
            console.print(f"  Distance: {distance}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestCollectionCreateCommand -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/pyseekdb/cli.py tests/unit_tests/test_cli.py
git commit -m "feat(cli): add 'collection create' command"
```

---

## Task 7: Implement `collection count` Command

**Files:**
- Modify: `src/pyseekdb/cli.py`
- Modify: `tests/unit_tests/test_cli.py`

**Step 1: Write the failing test**

Add to `tests/unit_tests/test_cli.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestCollectionCountCommand -v`
Expected: FAIL

**Step 3: Implement collection count command**

Add to `src/pyseekdb/cli.py`:

```python
@collection.command("count")
@click.argument("name")
@click.pass_context
def collection_count(ctx, name):
    """Get the number of records in a collection.

    NAME is the collection name to count.
    """
    console = Console()

    try:
        with get_client(ctx) as client:
            coll = client.get_collection(name)
            count = coll.count()
            console.print(f"Collection '[bold cyan]{name}[/bold cyan]' has [bold green]{count}[/bold green] records.")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestCollectionCountCommand -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/pyseekdb/cli.py tests/unit_tests/test_cli.py
git commit -m "feat(cli): add 'collection count' command"
```

---

## Task 8: Add Error Handling and Connection Test Command

**Files:**
- Modify: `src/pyseekdb/cli.py`
- Modify: `tests/unit_tests/test_cli.py`

**Step 1: Write the failing test**

Add to `tests/unit_tests/test_cli.py`:

```python
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
            mock_client_class.return_value.__enter__ = MagicMock(
                side_effect=Exception("Connection refused")
            )
            mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(main, ["ping"])
            assert result.exit_code != 0
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestPingCommand -v`
Expected: FAIL

**Step 3: Implement ping command**

Add to `src/pyseekdb/cli.py` (after the `main` function, before `collection` group):

```python
@main.command()
@click.pass_context
def ping(ctx):
    """Test database connection."""
    console = Console()
    conn = ctx.obj["connection"]

    console.print(f"Connecting to [cyan]{conn['host']}:{conn['port']}[/cyan]...")

    try:
        with get_client(ctx) as client:
            # Try a simple operation to verify connection
            client.list_collections()
            console.print("[green]Successfully connected to SeekDB![/green]")
            console.print(f"  Host: {conn['host']}")
            console.print(f"  Port: {conn['port']}")
            console.print(f"  User: {conn['user']}")
            console.print(f"  Database: {conn['database']}")
    except Exception as e:
        console.print(f"[red]Connection failed:[/red] {e}")
        raise SystemExit(1)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py::TestPingCommand -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/pyseekdb/cli.py tests/unit_tests/test_cli.py
git commit -m "feat(cli): add 'ping' command for connection testing"
```

---

## Task 9: Run Full Test Suite and Lint

**Files:**
- None (verification only)

**Step 1: Run all CLI tests**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run pytest tests/unit_tests/test_cli.py -v`
Expected: All tests PASS

**Step 2: Run linter**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run ruff check src/pyseekdb/cli.py`
Expected: No errors (or fix any reported issues)

**Step 3: Run formatter**

Run: `cd /Users/lx/Projects/2026.01.31/pyseekdb && uv run ruff format src/pyseekdb/cli.py tests/unit_tests/test_cli.py`
Expected: Files formatted

**Step 4: Final commit if any formatting changes**

```bash
git add -A
git commit -m "style: format CLI code with ruff"
```

---

## Task 10: Update Documentation

**Files:**
- Create: `docs/cli.md`

**Step 1: Create CLI documentation**

Create `docs/cli.md`:

```markdown
# PySeekDB CLI Reference

The PySeekDB CLI (`seekdb`) provides a command-line interface for managing and inspecting SeekDB collections.

## Installation

The CLI is installed automatically with pyseekdb:

```bash
pip install pyseekdb
```

## Configuration

Connection settings can be provided via command-line options or environment variables:

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `--host` | `SEEKDB_HOST` | 127.0.0.1 | SeekDB server host |
| `--port` | `SEEKDB_PORT` | 2881 | SeekDB server port |
| `--user` | `SEEKDB_USER` | root@test | Database user |
| `--password` | `SEEKDB_PASSWORD` | (empty) | Database password |
| `--database` | `SEEKDB_DATABASE` | test | Database name |

## Commands

### Test Connection

```bash
seekdb ping
```

### List Collections

```bash
# Table format (default)
seekdb collection list

# JSON format
seekdb collection list --format json
```

### Show Collection Info

```bash
# Basic info
seekdb collection info my_collection

# With sample records
seekdb collection info my_collection --peek 5
```

### Create Collection

```bash
# With L2 distance (default)
seekdb collection create my_collection --dimension 384

# With cosine distance
seekdb collection create my_collection --dimension 384 --distance cosine
```

### Count Records

```bash
seekdb collection count my_collection
```

### Delete Collection

```bash
# With confirmation prompt
seekdb collection delete my_collection

# Skip confirmation
seekdb collection delete my_collection --yes
```

## Examples

```bash
# Connect to a remote server
export SEEKDB_HOST=10.0.0.5
export SEEKDB_PORT=2881
export SEEKDB_USER=admin@tenant
export SEEKDB_PASSWORD=secret
export SEEKDB_DATABASE=production

# Test connection
seekdb ping

# List all collections
seekdb collection list

# Get detailed info about a specific collection
seekdb collection info documents --peek 3
```
```

**Step 2: Commit documentation**

```bash
git add docs/cli.md
git commit -m "docs: add CLI reference documentation"
```

---

## Summary

This plan implements a full-featured CLI tool for PySeekDB with the following commands:

| Command | Description |
|---------|-------------|
| `seekdb ping` | Test database connection |
| `seekdb collection list` | List all collections |
| `seekdb collection info NAME` | Show collection details |
| `seekdb collection create NAME` | Create a new collection |
| `seekdb collection count NAME` | Count records in collection |
| `seekdb collection delete NAME` | Delete a collection |

**Total estimated implementation time:** 30-45 minutes

**Key design decisions:**
1. Uses `click` for CLI framework (industry standard, excellent composability)
2. Uses `rich` for beautiful terminal output (tables, colors, panels)
3. Supports both environment variables and CLI options for connection config
4. Includes safety confirmation for destructive operations (delete)
5. Provides JSON output option for scripting/automation use cases
