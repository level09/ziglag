"""Move a database created by ZigLag on stk 16 onto the stk 17 migration lineages."""

import click
from alembic import command
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from quart import current_app
from quart.cli import with_appcontext
from sqlalchemy import create_engine, inspect, text
from stk.extensions import NAMING_CONVENTION
from stk.migrations import CORE_LABEL, build_alembic_config, sync_url

APP_LABEL = "ziglag"
LAST_STK16_REVISION = "20261006_0002"
STK_BASE_REVISION = "stk_0001"
STK_17_TABLES = {"stk_job", "stk_file", "stk_notification", "stk_mcp_token"}
LEGACY_TABLES = {"user", "business_settings", "client", "invoice", "payment"}


def name_unique_constraints(connection):
    """Give stk 16's unnamed unique constraints the names stk 17 expects.

    Without this, autogenerate against an adopted database proposes to add each
    one again. PostgreSQL renames in place; SQLite copies the table with names.
    Row counts must match afterwards, or this raises before the version rewrite.
    """
    inspector = inspect(connection)
    quote = connection.dialect.identifier_preparer.quote
    tables = inspector.get_table_names()
    counts = {
        t: connection.execute(text(f"select count(*) from {quote(t)}")).scalar()
        for t in tables
    }
    operations = Operations(MigrationContext.configure(connection))
    rebuild = set()
    for table in tables:
        for unique in inspector.get_unique_constraints(table):
            columns = unique["column_names"]
            expected = NAMING_CONVENTION["uq"] % {
                "table_name": table,
                "column_0_name": columns[0],
            }
            if len(columns) != 1 or unique["name"] == expected:
                continue
            if connection.dialect.name == "sqlite":
                rebuild.add(table)
            else:
                connection.execute(
                    text(
                        f"alter table {quote(table)} rename constraint"
                        f" {quote(unique['name'])} to {quote(expected)}"
                    )
                )
    for table in sorted(rebuild):
        with operations.batch_alter_table(
            table, recreate="always", naming_convention=NAMING_CONVENTION
        ):
            pass
    for table, count in counts.items():
        if (
            connection.execute(text(f"select count(*) from {quote(table)}")).scalar()
            != count
        ):
            raise click.ClickException(
                f"row count of {table} changed: restore the backup"
            )


def adopt(config, database_url):
    """Move a database from the last stk 16 revision onto both stk 17 lineages.

    The schema at the last stk 16 revision is what stk_0001 and the app's first
    revision create, so the first and third steps only rewrite alembic_version.
    In between, stk_0002 and later add their own tables. The app's first revision
    depends on stk's head, so the two cannot be stamped together up front.
    Raises click.ClickException when the database is not exactly at that revision.
    """
    engine = create_engine(sync_url(database_url))
    try:
        with engine.begin() as connection:
            tables = set(inspect(connection).get_table_names())
            if "alembic_version" not in tables:
                raise click.ClickException(
                    "no alembic_version table: not a ZigLag database"
                )
            versions = set(
                connection.execute(
                    text("select version_num from alembic_version")
                ).scalars()
            )
            if versions != {LAST_STK16_REVISION}:
                raise click.ClickException(
                    f"database is at {sorted(versions) or 'no revision'}, expected only"
                    f" {LAST_STK16_REVISION}. Already adopted: run `stk db upgrade`."
                    " Older: upgrade with the last stk 16 based ZigLag release first."
                )
            if missing := LEGACY_TABLES - tables:
                raise click.ClickException(f"missing ZigLag tables: {sorted(missing)}")
            if present := STK_17_TABLES & tables:
                raise click.ClickException(
                    f"stk 17 tables already exist: {sorted(present)}"
                )
            name_unique_constraints(connection)
            connection.execute(text("delete from alembic_version"))
            connection.execute(
                text("insert into alembic_version (version_num) values (:revision)"),
                {"revision": STK_BASE_REVISION},
            )
    finally:
        engine.dispose()
    command.upgrade(config, f"{CORE_LABEL}@head")
    # Only the lineage's first revision carries its branch label.
    script = ScriptDirectory.from_config(config)
    (base,) = [
        r.revision for r in script.walk_revisions() if APP_LABEL in r.branch_labels
    ]
    command.stamp(config, base)
    command.upgrade(config, "heads")


@click.command("adopt-stk16")
@with_appcontext
def adopt_stk16():
    """Adopt a database created by ZigLag on stk 16 (back it up first)."""
    adopt(
        build_alembic_config(current_app), current_app.config["SQLALCHEMY_DATABASE_URI"]
    )
    click.echo("Adopted. Run `stk db current` and `stk db check` to confirm.")
