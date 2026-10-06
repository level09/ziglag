"""ZigLag backup commands."""

from datetime import UTC, datetime
from pathlib import Path

import click
from quart.cli import with_appcontext


@click.group("backup")
def backup():
    """Create, verify, and restore application backups."""


@backup.command("create")
@click.option("--output", type=click.Path(path_type=Path))
@with_appcontext
def backup_create(output):
    from quart import current_app

    from stk.backup import BackupError, create_backup

    target = (
        output or Path("backups") / f"ziglag-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.tar.gz"
    )
    try:
        archive = create_backup(
            current_app.config["SQLALCHEMY_DATABASE_URI"],
            Path(current_app.instance_path),
            target,
        )
    except BackupError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(str(archive))


@backup.command("verify")
@click.argument("archive", type=click.Path(exists=True, path_type=Path))
def backup_verify(archive):
    from stk.backup import BackupError, verify_backup

    try:
        verify_backup(archive)
    except BackupError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo("Backup verified")


@backup.command("restore")
@click.argument("archive", type=click.Path(exists=True, path_type=Path))
@click.option("--force", is_flag=True)
@with_appcontext
def backup_restore(archive, force):
    from quart import current_app

    from stk.backup import BackupError, restore_backup

    try:
        restore_backup(
            archive,
            current_app.config["SQLALCHEMY_DATABASE_URI"],
            Path(current_app.instance_path),
            force=force,
        )
    except BackupError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo("Backup restored")
