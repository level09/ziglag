import sqlite3
import tempfile
import unittest
from pathlib import Path

from stk.backup import BackupError, create_backup, restore_backup, verify_backup


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "source.db"
        with sqlite3.connect(self.db) as connection:
            connection.execute("create table sample (value text)")
            connection.execute("insert into sample values ('ok')")
        invoice = self.root / "instance" / "invoices" / "1" / "2"
        invoice.mkdir(parents=True)
        (invoice / "invoice-2.pdf").write_bytes(b"%PDF-test")

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip(self):
        archive = create_backup(
            f"sqlite+aiosqlite:///{self.db}",
            self.root / "instance",
            self.root / "backup.tar.gz",
        )
        self.assertEqual(verify_backup(archive)["format_version"], 1)
        restored = self.root / "restored.db"
        restored_instance = self.root / "restored-instance"
        restore_backup(
            archive,
            f"sqlite+aiosqlite:///{restored}",
            restored_instance,
        )
        with sqlite3.connect(restored) as connection:
            self.assertEqual(
                connection.execute("select value from sample").fetchone()[0], "ok"
            )
        self.assertEqual(
            (restored_instance / "invoices/1/2/invoice-2.pdf").read_bytes(),
            b"%PDF-test",
        )

    def test_restore_refuses_existing_target(self):
        archive = create_backup(
            f"sqlite+aiosqlite:///{self.db}",
            self.root / "instance",
            self.root / "backup.tar.gz",
        )
        with self.assertRaisesRegex(BackupError, "not empty"):
            restore_backup(
                archive,
                f"sqlite+aiosqlite:///{self.db}",
                self.root / "instance",
            )

    def test_restore_into_empty_invoices_dir_succeeds(self):
        archive = create_backup(
            f"sqlite+aiosqlite:///{self.db}",
            self.root / "instance",
            self.root / "backup.tar.gz",
        )
        restored = self.root / "restored.db"
        restored_instance = self.root / "restored-instance"
        (restored_instance / "invoices").mkdir(parents=True)
        restore_backup(
            archive,
            f"sqlite+aiosqlite:///{restored}",
            restored_instance,
        )
        self.assertTrue((restored_instance / "invoices/1/2/invoice-2.pdf").is_file())

    def test_postgres_restore_requires_force(self):
        archive = create_backup(
            f"sqlite+aiosqlite:///{self.db}",
            self.root / "instance",
            self.root / "backup.tar.gz",
        )
        with self.assertRaisesRegex(BackupError, "not empty"):
            restore_backup(
                archive,
                "postgresql+asyncpg://user:pass@localhost/app",
                self.root / "fresh-instance",
            )


if __name__ == "__main__":
    unittest.main()
