import sqlite3


class SchemaConnection(sqlite3.Connection):
    def execute(self, sql, parameters=(), /):
        stripped = sql.strip()
        if " ".join(stripped.upper().split()).startswith("CREATE TABLE IF NOT EXISTS"):
            if not self.in_transaction:
                super().execute("BEGIN IMMEDIATE")
            with sqlite3.connect(":memory:") as reference:
                reference.execute(sql)
                table = reference.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name != 'sqlite_sequence'").fetchone()[0]
                expected = reference.execute(f'PRAGMA table_info("{table}")').fetchall()
            existing = {row[1] for row in super().execute(f'PRAGMA table_info("{table}")')}
            if existing:
                for _, name, kind, required, default, primary in expected:
                    if name in existing:
                        continue
                    if primary:
                        raise RuntimeError(f"Database table {table} is missing identity column {name}; restore a valid backup")
                    declaration = kind or "TEXT"
                    if default is not None and str(default).upper() != "CURRENT_TIMESTAMP":
                        declaration += f" DEFAULT {default}"
                        if required:
                            declaration += " NOT NULL"
                    super().execute(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {declaration}')
        return super().execute(sql, parameters)

    def executescript(self, sql_script, /):
        statement = ""
        cursor = None
        for character in sql_script:
            statement += character
            if character == ";" and sqlite3.complete_statement(statement):
                cursor = self.execute(statement)
                statement = ""
        if statement.strip():
            cursor = self.execute(statement)
        return cursor
