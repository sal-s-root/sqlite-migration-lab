# SQLite migration lab

Practice versioned schema changes, immutable migration checksums, and rollback of
a failed migration using Python's standard SQLite module.

## Run

Requirements: Python 3.11+ and Make.

```sh
make test
python3 migrate.py lab.db migrations
python3 migrate.py lab.db migrations
```

The first invocation creates an inventory table, adds an environment column, and
records both migrations. The second invocation reports that the schema is current.
Remove the disposable `lab.db` after inspecting it.

## Migration rules

Use consecutive names such as `001_create_inventory.sql`. Put each complete SQL
statement on its own line or multiline block, ending in a semicolon. Applied files
are immutable: corrections belong in a new migration. The runner owns transaction
boundaries and refuses transaction control and attached databases in migration SQL.
Migration files are trusted local source code, not an input format for untrusted SQL.

Each pending file uses its own `BEGIN IMMEDIATE` transaction. A failed file rolls
back its changes and ledger entry while earlier completed migrations stay applied.
A concurrent writer causes a bounded lock error. Review migrations against a copy
of important data and keep a recoverable backup before applying schema changes.

[Validation](VALIDATION.md) · [SQLite transactions](https://www.sqlite.org/lang_transaction.html) ·
[Python sqlite3](https://docs.python.org/3/library/sqlite3.html)
