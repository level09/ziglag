import sqlite3
import unittest
from pathlib import Path

import click
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text
from stk.migrations import (
    build_alembic_config,
    get_target_metadata,
    include_object,
    throwaway_database_url,
)

import ziglag.invoicing.models  # noqa: F401  (registers the invoicing tables)
from ziglag.adopt import adopt
from ziglag.settings import Config

LEGACY_SQL = Path(__file__).with_name("legacy_stk16.sql").read_text()


def drift(url):
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection,
                opts={
                    "compare_type": True,
                    "compare_server_default": True,
                    "include_object": include_object,
                },
            )
            return compare_metadata(context, get_target_metadata())
    finally:
        engine.dispose()


def scalars(url, sql):
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return connection.execute(text(sql)).scalars().all()
    finally:
        engine.dispose()


class MigrationTests(unittest.TestCase):
    def setUp(self):
        context = throwaway_database_url(Config.SQLALCHEMY_DATABASE_URI, sync=True)
        self.url = context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)
        self.config = build_alembic_config("ziglag", self.url, quiet=True)

    def legacy(self, revision="20261006_0002"):
        connection = sqlite3.connect(self.url.removeprefix("sqlite:///"))
        connection.executescript(LEGACY_SQL)
        connection.execute("update alembic_version set version_num = ?", (revision,))
        connection.commit()
        connection.close()

    def test_fresh_upgrade_has_no_drift_and_downgrades(self):
        command.upgrade(self.config, "heads")
        self.assertEqual(drift(self.url), [])
        command.downgrade(self.config, "ziglag@base")
        self.assertNotIn("invoice", scalars(self.url, "select name from sqlite_master"))
        command.upgrade(self.config, "heads")
        self.assertEqual(drift(self.url), [])

    def test_adopts_stk16_database(self):
        self.legacy()
        tables = ("user", "business_settings", "client", "invoice", "invoice_item")
        before = {t: scalars(self.url, f'select * from "{t}"') for t in tables}
        adopt(self.config, self.url)
        self.assertEqual(
            {t: scalars(self.url, f'select * from "{t}"') for t in tables}, before
        )
        self.assertEqual(
            scalars(self.url, "select invoice_number from invoice"), ["INV-0001"]
        )
        self.assertEqual(scalars(self.url, "select count(*) from stk_job"), [0])
        self.assertEqual(drift(self.url), [])
        # stk_0007 confirms accounts that never had to confirm.
        self.assertIsNotNone(scalars(self.url, "select confirmed_at from user")[0])

    def test_adoption_refuses_other_revisions_and_runs_once(self):
        self.legacy(revision="20261006_0001")
        with self.assertRaises(click.ClickException):
            adopt(self.config, self.url)
        self.assertEqual(
            scalars(self.url, "select version_num from alembic_version"),
            ["20261006_0001"],
        )
        self.assertNotIn("stk_job", scalars(self.url, "select name from sqlite_master"))

        connection = sqlite3.connect(self.url.removeprefix("sqlite:///"))
        connection.execute("update alembic_version set version_num = '20261006_0002'")
        connection.commit()
        connection.close()
        adopt(self.config, self.url)
        with self.assertRaises(click.ClickException):
            adopt(self.config, self.url)


if __name__ == "__main__":
    unittest.main()
