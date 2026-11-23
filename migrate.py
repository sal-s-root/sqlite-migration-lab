"""Apply numbered local SQLite migrations with per-file atomicity and checksums."""
import argparse
from contextlib import closing
import hashlib
from pathlib import Path
import re
import sqlite3
import sys


def migration_files(directory):
    files = sorted(Path(directory).glob("*.sql"))
    if not files:
        raise ValueError("migration directory must contain numbered SQL files")
    result = []
    for file in files:
        match = re.fullmatch(r"([0-9]{3})_[a-z0-9_]+\.sql", file.name)
        if not match:
            raise ValueError("invalid migration filename: " + file.name)
        version = int(match[1])
        sql = file.read_text(encoding="utf-8")
        result.append((version, file.name, hashlib.sha256(sql.encode()).hexdigest(), sql))
    if [r[0] for r in result] != list(range(1, len(result) + 1)):
        raise ValueError("migration versions must be consecutive starting at 001")
    return result


def statements(sql):
    pending = ""
    for line in sql.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            yield pending
            pending = ""
    if pending.strip():
        raise ValueError("incomplete SQL statement; end every statement with a semicolon")


def restrict_transaction_control(action, _one, _two, _database, _trigger):
    denied = {sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT,
              sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH}
    return sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK


def migrate(database, directory, timeout=1.0):
    migrations = migration_files(directory)
    with closing(sqlite3.connect(database, isolation_level=None, timeout=timeout)) as db:
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                   "version INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                   "sha256 TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        applied = {version: (name, sha) for version, name, sha in
                   db.execute("SELECT version,name,sha256 FROM schema_migrations")}
        available = {row[0] for row in migrations}
        if set(applied) - available:
            raise ValueError("an applied migration is missing from the directory")
        for version, name, sha, _sql in migrations:
            if version in applied and applied[version] != (name, sha):
                raise ValueError("applied migration changed: " + name)
        completed = []
        for version, name, sha, sql in migrations:
            if version in applied:
                continue
            db.execute("BEGIN IMMEDIATE")
            try:
                db.set_authorizer(restrict_transaction_control)
                try:
                    for statement in statements(sql):
                        db.execute(statement)
                finally:
                    db.set_authorizer(None)
                db.execute("INSERT INTO schema_migrations(version,name,sha256) VALUES (?,?,?)",
                           (version, name, sha))
                db.execute("COMMIT")
            except BaseException:
                db.set_authorizer(None)
                if db.in_transaction:
                    db.execute("ROLLBACK")
                raise
            completed.append(name)
        return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        completed = migrate(args.database, args.directory)
    except (OSError, sqlite3.Error, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print("Applied: " + (", ".join(completed) if completed else "none; schema is current"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
