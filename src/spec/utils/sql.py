from __future__ import annotations

import os
import re
import threading
import urllib.parse
import uuid
from contextlib import contextmanager

import jinja2
import pandas as pd
import psycopg2

__all__ = ["SQLNotebook"]


class SQLNotebook:
    """
    A miniature SQL‑first notebook for PostgreSQL with:

        • automatic rollback on error (SAVEPOINT based)
        • safe concurrent use by multiple users
        • read‑only `run()` (except for the internal temp‑table materialisation)
        • unrestricted `update()` for data‑changing commands
    """

    # ───────────────────────────── class‑level helpers ──────────────────────────
    _READONLY_OK_RE = re.compile(
        r"^\s*(?:WITH\b.*?SELECT|SELECT)\b", re.IGNORECASE | re.DOTALL
    )
    _DANGEROUS_RE = re.compile(
        r"\b(INSERT|UPDATE|DELETE|MERGE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|COPY)\b",
        re.IGNORECASE,
    )
    _LOCK = threading.RLock()

    # ───────────────────────────── constructor ─────────────────────────────────
    def __init__(
        self,
        *,
        dsn: str | None = None,
        schema: str = "pg_temp",
        user_id: str | None = None,
    ) -> None:
        """
        Parameters
        ----------
        dsn       : full PostgreSQL DSN string; if *None* it is built from
                    PGHOST / PGUSER / PGPASSWORD / PGDATABASE / PGPORT env‑vars.
        schema    : where temporary objects are created (defaults to pg_temp).
        user_id   : an arbitrary identifier (username, email …).  Used only to
                    prefix temp objects so different users never collide.
        """
        if dsn is None:
            host = os.getenv("PGHOST")
            user = os.getenv("PGUSER")
            password = os.getenv("PGPASSWORD")
            dbname = os.getenv("PGDATABASE", os.getenv("PGDB"))
            port = os.getenv("PGPORT", "5432")
            sslmode = os.getenv("PGSSLMODE", "require")

            missing = [
                n
                for v, n in [
                    (host, "HOST"),
                    (user, "USER"),
                    (password, "PASSWORD"),
                    (dbname, "DATABASE/DB"),
                ]
                if v is None
            ]
            if missing:
                raise ValueError(
                    "Missing env‑vars {} (or supply *dsn*)".format(", ".join(missing))
                )

            dsn = (
                "postgresql://"
                f"{urllib.parse.quote_plus(user)}:"
                f"{urllib.parse.quote_plus(password)}@{host}:{port}/{dbname}"
                f"?sslmode={sslmode}"
            )

        # Each notebook gets its *own* connection → natural isolation.
        self._conn = psycopg2.connect(dsn)
        # We keep autocommit *off* so we can use SAVEPOINTs for true rollbacks.
        self._conn.autocommit = False

        self._schema = schema
        self._user_prefix = self._make_safe_ident(user_id or "user") + "_"
        self._counter = 0  # used to build deterministic temp‑table names

        self._store: dict[str, str] = {}  # alias  → temp‑table
        self._jenv = jinja2.Environment(undefined=jinja2.StrictUndefined)

    # ───────────────────────────── public API ──────────────────────────────────
    # -- run (read‑only) --------------------------------------------------------
    def run(
        self,
        sql: str,
        *,
        name: str | None = None,
        materialise: bool = True,
    ) -> pd.DataFrame:
        """
        Execute *sql* strictly in **read‑only** mode.

        Rules
        -----
        1. The statement must start with `SELECT` or `WITH … SELECT`.
        2. A temporary table/view is created automatically when *name* is given.
        3. Any violation of (1) raises `PermissionError`.
        4. Errors are rolled back to the last SAVEPOINT without killing the
           session or losing earlier temp objects.

        Returns
        -------
        pandas.DataFrame with the query result.
        """
        rendered = self._render(sql)

        # ── enforce read‑only discipline ───────────────────────────────────────
        if not self._READONLY_OK_RE.match(rendered) or self._DANGEROUS_RE.search(
            rendered
        ):
            raise PermissionError(
                "Only pure SELECT statements are allowed in run(). "
                "Use update() for commands that change the database."
            )

        # ── actually execute the query ─────────────────────────────────────────
        df = self._fetch(rendered)

        # ── optionally persist as temp object for later reuse ──────────────────
        if name:
            temp_name = self._next_temp_name()
            with self._cursor() as cur:
                if materialise:
                    cur.execute(
                        f"CREATE TEMP TABLE {temp_name} AS ({rendered}) "
                        "ON COMMIT PRESERVE ROWS;"
                    )
                else:
                    cur.execute(
                        f"CREATE TEMP VIEW  {temp_name} AS ({rendered});"
                    )
                self._store[name] = temp_name
                self._conn.commit()

        return df

    # -- update (full privileges) ----------------------------------------------
    def update(self, sql: str | list[str]) -> None:
        """
        Execute one or many SQL statements that **may** modify the database.

        • Statements are rendered through the template engine, so you can refer
          to previous aliases (`{{my_alias}}`).

        • Every statement is wrapped in a SAVEPOINT; on failure we roll back to
          that SAVEPOINT and re‑raise the exception.

        • On success we commit so the changes become visible to other sessions.
        """
        if isinstance(sql, str):
            statements = [sql]
        else:
            statements = list(sql)

        with self._cursor() as cur:
            for stmt in statements:
                rendered = self._render(stmt)
                savepoint = f"sp_{uuid.uuid4().hex[:8]}"
                cur.execute(f"SAVEPOINT {savepoint};")
                try:
                    cur.execute(rendered)
                    cur.execute(f"RELEASE SAVEPOINT {savepoint};")
                except Exception:
                    cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint};")
                    raise
            self._conn.commit()  # all fine → make durable

    # -- convenience helpers ----------------------------------------------------
    def to_df(self, name: str) -> pd.DataFrame:
        """Load a previously‑stored alias back into a DataFrame."""
        return self._fetch(f"SELECT * FROM {self._store[name]}")

    def sql(self, name: str) -> str:  # debugging nicety
        return f"SELECT * FROM {self._store[name]}"

    # ───────────────────────────── implementation details ─────────────────────
    def _render(self, text: str) -> str:
        tmpl = self._jenv.from_string(text)
        return tmpl.render(**self._store)

    def _fetch(self, sql: str) -> pd.DataFrame:
        with self._cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]
            return pd.DataFrame(rows, columns=cols)

    @contextmanager
    def _cursor(self):
        """
        Context‑manager that provides a cursor **and** guarantees automatic
        rollback to the outermost level if anything inside fails.
        """
        with self._LOCK:
            cur = self._conn.cursor()
            try:
                yield cur
            except Exception:
                # Roll back the *transaction* (but not the whole session) so the
                # connection stays usable.
                self._conn.rollback()
                raise
            finally:
                cur.close()

    # ───────────────────────────── utilities ──────────────────────────────────
    def _next_temp_name(self) -> str:
        self._counter += 1
        return f"{self._schema}.{self._user_prefix}{self._counter:04d}"

    @staticmethod
    def _make_safe_ident(raw: str) -> str:
        """
        Lower‑case, replace non‑alnum with underscores and collapse repeats
        → safe for use as an identifier fragment.
        """
        return re.sub(r"[^0-9a-z]+", "_", raw.lower()).strip("_")[:30]

    # ───────────────────────────── tear‑down ───────────────────────────────────
    def close(self):
        self._conn.close()

    def __enter__(self):  # so `with SQLNotebook() as nb: …` works
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
