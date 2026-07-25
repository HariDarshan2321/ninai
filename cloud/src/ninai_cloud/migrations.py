from __future__ import annotations

import os
from pathlib import Path


def migration_files() -> list[Path]:
    root = Path(__file__).resolve().parents[2] / "migrations"
    return sorted(root.glob("*.sql"))


def apply_migrations(database_url: str) -> None:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - packaging guard
        raise RuntimeError("Install ninai-cloud before applying migrations") from exc

    with psycopg.connect(database_url) as connection:
        # A deploy platform may start several replicas at once. Keep schema
        # changes serialized for the lifetime of this transaction rather than
        # allowing two entrypoints to apply the same migration concurrently.
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (0x4E494E4149,))
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        for path in migration_files():
            version = path.stem
            exists = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version=%s", (version,)
            ).fetchone()
            if exists:
                continue
            connection.execute(path.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO schema_migrations(version) VALUES (%s)", (version,)
            )


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    apply_migrations(database_url)


if __name__ == "__main__":
    main()
