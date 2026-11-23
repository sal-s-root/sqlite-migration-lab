from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from migrate import migrate


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / "lab.db"
        self.directory = self.root / "migrations"
        shutil.copytree(Path(__file__).parent / "migrations", self.directory)

    def rows(self, sql):
        db = sqlite3.connect(self.database)
        try:
            return db.execute(sql).fetchall()
        finally:
            db.close()

    def test_fresh_schema_and_ledger(self):
        self.assertEqual(len(migrate(self.database, self.directory)), 2)
        self.assertEqual(self.rows("SELECT hostname,environment FROM inventory"), [("lab-node-1", "lab")])
        self.assertEqual(self.rows("SELECT version FROM schema_migrations ORDER BY version"), [(1,), (2,)])

    def test_repeat_application_is_noop(self):
        migrate(self.database, self.directory)
        self.assertEqual(migrate(self.database, self.directory), [])
        self.assertEqual(self.rows("SELECT count(*) FROM inventory"), [(1,)])

    def test_failed_migration_rolls_back_schema_and_preserves_data(self):
        migrate(self.database, self.directory)
        (self.directory / "003_failure.sql").write_text(
            "ALTER TABLE inventory ADD COLUMN transient TEXT;\nINSERT INTO missing VALUES (1);\n")
        with self.assertRaises(sqlite3.OperationalError):
            migrate(self.database, self.directory)
        self.assertNotIn("transient", [r[1] for r in self.rows("PRAGMA table_info(inventory)")])
        self.assertEqual(self.rows("SELECT count(*) FROM inventory"), [(1,)])
        self.assertEqual(self.rows("SELECT count(*) FROM schema_migrations"), [(2,)])

    def test_applied_file_edits_are_refused(self):
        migrate(self.database, self.directory)
        file = self.directory / "001_create_inventory.sql"
        file.write_text(file.read_text() + "\n-- altered after application\n")
        with self.assertRaisesRegex(ValueError, "applied migration changed"):
            migrate(self.database, self.directory)

    def test_missing_applied_file_is_refused(self):
        migrate(self.database, self.directory)
        (self.directory / "002_add_environment.sql").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            migrate(self.database, self.directory)

    def test_transaction_control_inside_migration_is_refused(self):
        migrate(self.database, self.directory)
        (self.directory / "003_escape.sql").write_text("CREATE TABLE surprise(id INTEGER);\nCOMMIT;\n")
        with self.assertRaises(sqlite3.DatabaseError):
            migrate(self.database, self.directory)
        self.assertEqual(self.rows("SELECT name FROM sqlite_master WHERE name='surprise'"), [])

    def test_writer_lock_does_not_apply_pending_migration(self):
        migrate(self.database, self.directory)
        (self.directory / "003_pending.sql").write_text("CREATE TABLE pending(id INTEGER);\n")
        db = sqlite3.connect(self.database, isolation_level=None)
        try:
            db.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                migrate(self.database, self.directory, timeout=0.05)
        finally:
            db.close()
        self.assertEqual(self.rows("SELECT count(*) FROM schema_migrations"), [(2,)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
