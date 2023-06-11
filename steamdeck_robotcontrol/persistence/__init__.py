"""
For the use of application screens, a persistence layer is provided.
This is a scoped key-value store, backed by SQLite databases, where the values are JSON objects.
"""
import sqlite3
from typing import Dict, Tuple
import weakref
import pathlib
from .database import KVDatabase

# Holds opened sqlite3 connections
# These will get closed automatically on program shutdown, so strong references are held here.
CONNECTIONS: Dict[str, Tuple[pathlib.Path, sqlite3.Connection]] = dict()

# Holds weak references to KVDatabases, so that we can return the same one
# in order to share their cache.
DATABASES: weakref.WeakValueDictionary[str, KVDatabase] = weakref.WeakValueDictionary()

def get_path_for_key(key: str) -> pathlib.Path:
    return pathlib.Path(f"./{key}.sqlite3")  # TODO: store this in a well-known location


def get_database(key: str) -> KVDatabase:
    # First check if the database already exists. If it does, produce that.
    if key in DATABASES:
        return DATABASES[key]
    # Then check if the database was opened. If it was, wrap it in a KVDatabase.
    elif key in CONNECTIONS:
        db = KVDatabase(CONNECTIONS[key][1], key, CONNECTIONS[key][0], perform_init=False)  # No init needed, because it will have been done at least once.
        DATABASES[key] = db
        return get_database(key)
    # If not, open it, store it, then wrap it.
    else:
        path = get_path_for_key(key)
        conn = sqlite3.connect(get_path_for_key(key))
        CONNECTIONS[key] = (path, conn)
        DATABASES[key] = KVDatabase(conn, key, path, perform_init=True)
        return get_database(key)