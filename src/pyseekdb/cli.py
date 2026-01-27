"""
PySeekDB Command Line Interface

A CLI tool for inspecting and managing SeekDB collections.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from pyseekdb import __version__
from pyseekdb import Client


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
