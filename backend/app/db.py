"""Acceso a MariaDB con PyMySQL. Una conexión por petición (suficiente para un local)."""
import os
from contextlib import contextmanager

import pymysql
import pymysql.cursors

CFG = dict(
    host=os.getenv("KDS_DB_HOST", "localhost"),
    port=int(os.getenv("KDS_DB_PORT", "3306")),
    user=os.getenv("KDS_DB_USER", "kds"),
    password=os.getenv("KDS_DB_PASS", ""),
    database=os.getenv("KDS_DB_NAME", "kds_tpv"),
    unix_socket=os.getenv("KDS_DB_SOCKET") or None,
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=False,
)


@contextmanager
def conn():
    c = pymysql.connect(**CFG)
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def q(sql, args=None):
    with conn() as c, c.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def q1(sql, args=None):
    rows = q(sql, args)
    return rows[0] if rows else None
