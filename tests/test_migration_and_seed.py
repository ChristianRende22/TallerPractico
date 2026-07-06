import os
import sqlite3
import subprocess
import sys


def test_migration_creates_schema_and_seed(tmp_path):
    db_path = tmp_path / "mig.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"}

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    con = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"users", "posts"} <= tables

    names = [row[0] for row in con.execute("SELECT name FROM users ORDER BY id")]
    assert names == ["Ana", "Luis"]
    con.close()
