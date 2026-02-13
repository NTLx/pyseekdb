"""
PySeekDB Command Line Interface

A CLI tool for inspecting and managing SeekDB collections.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pyseekdb import Client, HNSWConfiguration, __version__


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
    "--tenant",
    envvar="SEEKDB_TENANT",
    default="sys",
    help="Tenant name (env: SEEKDB_TENANT)",
)
@click.option(
    "--user",
    envvar="SEEKDB_USER",
    default="root",
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
def main(ctx, host, port, tenant, user, password, database):
    """PySeekDB CLI - Manage and inspect SeekDB collections.

    Connection can be configured via command-line options or environment variables:

    \b
    SEEKDB_HOST     - Server hostname (default: 127.0.0.1)
    SEEKDB_PORT     - Server port (default: 2881)
    SEEKDB_TENANT   - Tenant name (default: sys)
    SEEKDB_USER     - Database user (default: root)
    SEEKDB_PASSWORD - Database password
    SEEKDB_DATABASE - Database name (default: test)
    """
    ctx.ensure_object(dict)
    ctx.obj["connection"] = {
        "host": host,
        "port": port,
        "tenant": tenant,
        "user": user,
        "password": password,
        "database": database,
    }


def get_client(ctx):
    """Create a client from context connection info."""
    conn = ctx.obj["connection"]
    return Client(
        host=conn["host"],
        port=conn["port"],
        tenant=conn["tenant"],
        user=conn["user"],
        password=conn["password"],
        database=conn["database"],
    )


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
            console.print(f"  Tenant: {conn['tenant']}")
            console.print(f"  User: {conn['user']}")
            console.print(f"  Database: {conn['database']}")
    except Exception as e:
        console.print(f"[red]Connection failed:[/red] {e}")
        raise SystemExit(1) from e


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
        raise SystemExit(1) from e


def _render_collection_panel(coll) -> Panel:
    """Render the collection info panel."""
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

    return Panel(info_text, title=f"Collection: {coll.name}", border_style="blue")


def _render_peek_table(records) -> Table:
    """Render the sample records table."""
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
    return table


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
                raise SystemExit(1) from e

            console.print(_render_collection_panel(coll))

            # Peek records if requested
            if peek_count > 0:
                console.print(f"\n[bold]Sample Records (first {peek_count}):[/bold]")
                try:
                    records = coll.peek(limit=peek_count)
                    if records.get("ids"):
                        console.print(_render_peek_table(records))
                    else:
                        console.print("[yellow]No records found.[/yellow]")
                except Exception as e:
                    console.print(f"[red]Error peeking records:[/red] {e}")
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from e


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
        raise SystemExit(1) from e


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
        raise SystemExit(1) from e


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
        raise SystemExit(1) from e
