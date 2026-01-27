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
