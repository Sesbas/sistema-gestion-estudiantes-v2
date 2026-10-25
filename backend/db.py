"""MySQL in normal operation; SQLite only for isolated automated tests."""
import sqlite3
from contextlib import contextmanager

import pymysql
from flask import current_app, g
from config import DatabaseConfig


def connection():
    if 'db' not in g:
        if current_app.config.get('TEST_DATABASE'):
            g.db = sqlite3.connect(current_app.config['TEST_DATABASE'])
            g.db.row_factory = sqlite3.Row
        else:
            g.db = pymysql.connect(host=DatabaseConfig.HOST, port=DatabaseConfig.PORT,
                user=DatabaseConfig.USER, password=DatabaseConfig.PASSWORD,
                database=DatabaseConfig.DATABASE, charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor, autocommit=False)
    return g.db


def query(sql, params=(), one=False):
    db = connection()
    if isinstance(db, sqlite3.Connection):
        sql = sql.replace('%s', '?')
    cursor = db.cursor()
    try:
        cursor.execute(sql, params)
        if cursor.description:
            rows = [dict(row) for row in cursor.fetchall()]
            return (rows[0] if rows else None) if one else rows
        return cursor.lastrowid
    finally:
        cursor.close()


@contextmanager
def transaction():
    try:
        yield
        connection().commit()
    except Exception:
        connection().rollback()
        raise


def close_db(_error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
