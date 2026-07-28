from contextlib import contextmanager

import psycopg2

from .config import Settings


def get_connection(settings: Settings):
    conn = psycopg2.connect(settings.dsn)
    conn.autocommit = False
    return conn


@contextmanager
def transaction(conn):
    #Run a block atomically: commit on success, rollback on any error.
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise