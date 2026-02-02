"""
pyseekdb CLI tool for debugging and managing collections.

This module provides a command-line interface for:
- Listing collections
- Showing collection details
- Deleting collections
- Querying collection data
- Showing collection statistics
"""

import sys
import json
from typing import Any

import click
from tabulate import tabulate

from . import Client


@click.group()
@click.option(
    "--host",
    "-h",
    default=None,
    help="Server address (for remote server mode)",
)
@click.option(
    "--port",
    "-p",
    default=2881,
    help="Server port (default: 2881)",
)
@click.option(
    "--tenant",
    "-t",
    default="sys",
    help="Tenant name (default: sys for seekdb Server)",
)
@click.option(
    "--database",
    "-d",
    default="test",
    help="Database name",
)
@click.option(
    "--user",
    "-u",
    default=None,
    help="Username (without tenant suffix)",
)
@click.option(
    "--password",
    "-P",
    default="",
    help="Password (or use SEEKDB_PASSWORD env var)",
)
@click.option(
    "--path",
    default=None,
    help="Path to seekdb data directory (for embedded mode)",
)
@click.pass_context
def cli(
    ctx: click.Context,
    host: str | None,
    port: int,
    tenant: str,
    database: str,
    user: str | None,
    password: str,
    path: str | None,
) -> None:
    """
    pyseekdb CLI - Debug and manage collections
    
    This tool provides commands to inspect and manage pyseekdb collections.
    """
    # Store connection parameters in context
    ctx.ensure_object(dict)
    ctx.obj["host"] = host
    ctx.obj["port"] = port
    ctx.obj["tenant"] = tenant
    ctx.obj["database"] = database
    ctx.obj["user"] = user
    ctx.obj["password"] = password
    ctx.obj["path"] = path


def _get_client(ctx: click.Context) -> Any:
    """Get a pyseekdb client from context."""
    params = ctx.obj
    return Client(
        host=params.get("host"),
        port=params.get("port"),
        tenant=params.get("tenant"),
        database=params.get("database"),
        user=params.get("user"),
        password=params.get("password"),
        path=params.get("path"),
    )


@cli.command()
@click.pass_context
def list_collections(ctx: click.Context) -> None:
    """
    List all collections in the database.
    """
    try:
        client = _get_client(ctx)
        
        # Get all collections
        collections = client.list_collections()
        
        if not collections:
            click.echo("No collections found in the database.")
            return
        
        # Display as table
        table_data = []
        for coll in collections:
            table_data.append([
                coll.get("id", "N/A"),
                coll.get("name", "N/A"),
                coll.get("count", 0),
                coll.get("status", "N/A"),
            ])
        
        headers = ["ID", "Name", "Document Count", "Status"]
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
        
    except Exception as e:
        click.echo(f"Error listing collections: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("collection_name")
@click.pass_context
def collection_info(ctx: click.Context, collection_name: str) -> None:
    """
    Show detailed information about a collection.
    
    COLLECTION_NAME: Name of the collection to inspect
    """
    try:
        client = _get_client(ctx)
        
        # Get collection
        collection = client.get_collection(collection_name)
        
        if collection is None:
            click.echo(f"Collection '{collection_name}' not found.", err=True)
            sys.exit(1)
        
        # Get collection count
        count = collection.count()
        
        click.echo(f"\n=== Collection: {collection_name} ===")
        click.echo(f"Document Count: {count}")
        
        # Get collection schema if available
        collection_id = getattr(collection, "collection_id", None)
        if collection_id:
            click.echo(f"Collection ID: {collection_id}")

        # Show index information
        click.echo("\n--- Index Information ---")
        click.echo("Index information: Not available in current version")

        click.echo("")
        
    except Exception as e:
        click.echo(f"Error getting collection info: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("collection_name")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force deletion without confirmation",
)
@click.pass_context
def delete_collection(ctx: click.Context, collection_name: str, force: bool) -> None:
    """
    Delete a collection from the database.
    
    COLLECTION_NAME: Name of the collection to delete
    """
    try:
        client = _get_client(ctx)
        
        # Check if collection exists
        collection = client.get_collection(collection_name)
        if collection is None:
            click.echo(f"Collection '{collection_name}' not found.", err=True)
            sys.exit(1)
        
        # Confirm deletion
        if not force:
            count = collection.count()
            if not click.confirm(
                f"Are you sure you want to delete collection '{collection_name}' "
                f"({count} documents)?"
            ):
                click.echo("Deletion cancelled.")
                return
        
        # Delete collection
        client.delete_collection(collection_name)
        click.echo(f"Collection '{collection_name}' deleted successfully.")
        
    except Exception as e:
        click.echo(f"Error deleting collection: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("collection_name")
@click.option(
    "--limit",
    "-l",
    default=10,
    help="Maximum number of documents to show (default: 10)",
)
@click.option(
    "--output",
    "-O",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format (default: table)",
)
@click.pass_context
def query_collection(
    ctx: click.Context,
    collection_name: str,
    limit: int,
    output: str,
) -> None:
    """
    Query and display documents from a collection.
    
    COLLECTION_NAME: Name of the collection to query
    """
    try:
        client = _get_client(ctx)
        
        # Get collection
        collection = client.get_collection(collection_name)
        if collection is None:
            click.echo(f"Collection '{collection_name}' not found.", err=True)
            sys.exit(1)
        
        # Get documents using peek
        result = collection.peek(limit=limit)
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        embeddings = result.get("embeddings", [])

        if not documents:
            click.echo(f"No documents found in collection '{collection_name}'.")
            return

        if output == "json":
            # Output as JSON
            docs_data = []
            for i, doc in enumerate(documents):
                docs_data.append({
                    "id": ids[i] if i < len(ids) else None,
                    "document": doc,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "embedding": embeddings[i] if i < len(embeddings) else None,
                })
            click.echo(json.dumps(docs_data, indent=2, default=str))
        else:
            # Output as table
            table_data = []
            for i, doc in enumerate(documents):
                # Truncate long documents for display
                doc_preview = doc[:100] + "..." if len(doc) > 100 else doc
                table_data.append([
                    ids[i] if i < len(ids) else f"doc_{i}",
                    doc_preview,
                    "Present" if i < len(embeddings) else "N/A",
                ])

            headers = ["ID", "Document Preview", "Embedding"]
            click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))

        click.echo(f"\nShowing {len(documents)} documents")
        
    except Exception as e:
        click.echo(f"Error querying collection: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("collection_name")
@click.pass_context
def collection_stats(ctx: click.Context, collection_name: str) -> None:
    """
    Show statistics for a collection.

    COLLECTION_NAME: Name of the collection
    """
    try:
        client = _get_client(ctx)

        # Get collection
        collection = client.get_collection(collection_name)
        if collection is None:
            click.echo(f"Collection '{collection_name}' not found.", err=True)
            sys.exit(1)

        # Get count
        count = collection.count()

        # Display statistics
        click.echo(f"\n=== Collection Statistics: {collection_name} ===")
        click.echo(f"Total Documents: {count}")

        # Show sample data statistics
        if count > 0:
            sample_limit = min(100, count)
            result = collection.peek(limit=sample_limit)
            documents = result.get("documents", [])

            # Calculate average document length
            doc_lengths = [len(doc) for doc in documents if isinstance(doc, str)]
            avg_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0

            click.echo(f"Sample Size: {sample_limit}")
            click.echo(f"Average Document Length: {avg_length:.2f} characters")
            click.echo(f"Min Document Length: {min(doc_lengths) if doc_lengths else 0}")
            click.echo(f"Max Document Length: {max(doc_lengths) if doc_lengths else 0}")

        click.echo("")
        
    except Exception as e:
        click.echo(f"Error getting collection stats: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def collections_summary(ctx: click.Context) -> None:
    """
    Show a summary of all collections with statistics.
    """
    try:
        client = _get_client(ctx)
        
        # Get all collections
        collections = client.list_collections()
        
        if not collections:
            click.echo("No collections found in the database.")
            return
        
        # Get statistics for each collection
        table_data = []
        for coll in collections:
            name = coll.get("name", "N/A")
            try:
                collection = client.get_collection(name)
                if collection:
                    count = collection.count()
                else:
                    count = 0
            except Exception:
                count = "?"
            
            table_data.append([
                name,
                str(count),
                coll.get("status", "N/A"),
            ])
        
        headers = ["Name", "Documents", "Status"]
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Total count
        total_docs = sum(
            int(row[1]) for row in table_data if row[1].isdigit()
        )
        click.echo(f"\nTotal documents across all collections: {total_docs}")
        click.echo(f"Total collections: {len(table_data)}")
        
    except Exception as e:
        click.echo(f"Error getting collections summary: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI tool."""
    cli(obj={})


if __name__ == "__main__":
    main()
