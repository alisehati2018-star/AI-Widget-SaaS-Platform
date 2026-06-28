"""Apply db/migrations/*.sql to the configured Postgres (one-off dev helper)."""
from __future__ import annotations

import asyncio
import glob
import os

import asyncpg


async def main() -> None:
    dsn = os.environ.get(
        "PG_DSN",
        "postgresql://acip:1234@localhost:5433/acip",
    )
    conn = await asyncpg.connect(dsn)
    for path in sorted(glob.glob("db/migrations/*.sql")):
        sql = open(path, encoding="utf-8").read()
        await conn.execute(sql)
        print("applied", path)
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1"
    )
    print("tables:", [r["tablename"] for r in tables])
    versions = await conn.fetch("SELECT version FROM schema_migrations ORDER BY 1")
    print("migrations:", [r["version"] for r in versions])
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
