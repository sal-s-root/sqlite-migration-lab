# Validation

Seven tests passed against temporary SQLite databases.

## Coverage

Fresh schema, repeat application, rollback of a failed migration, changed-file refusal, missing-file refusal, transaction-control refusal, and writer-lock handling. Atomicity is per migration file.
