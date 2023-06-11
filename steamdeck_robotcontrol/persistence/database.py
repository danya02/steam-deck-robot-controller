import json
import pathlib
import sqlite3
from typing import Any
from functools import wraps

def mutates_database(func):
    """Decorator to perform commit after the function returns."""
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        finally:
            self.conn.commit()
    return wrapped

class KVDatabase:
    """
    A wrapper around a SQLite database connection that provides dict-like key-value storage for JSONable types.

    Performance is a focus. Every operation that can be cached, is.
    For this reason, it is important that there is only one instance of this object for every connection,
    and that the database isn't being written by any other process;
    these are considerations external to this class.

    Has a special state where the cache is complete.
    When this is the case, operations like enumerating the items or getting the length
    will not hit the underlying SQLite database.
    """
    @mutates_database
    def __init__(self, conn: sqlite3.Connection, key: str, path: pathlib.Path, perform_init=True):
        self.conn = conn
        self.key = key
        self.path = path
        if perform_init:
            conn.execute("CREATE TABLE IF NOT EXISTS props(key TEXT PRIMARY KEY, value_json TEXT)")
        self.cache = dict()
        self.cache_is_complete = False
    
    def discard_cache(self):
        """
        Clears the cache so that every value will need to be acquired from the database.
        Run this if you have reasons to believe that the database has changed on disk.
        """
        self.cache.clear()
        self.cache_is_complete = False

    def __getitem__(self, key: str) -> Any:
        """Get a data item by key, from cache if possible, raising a KeyError if not there."""
        if not isinstance(key, str): raise TypeError("Keys should be strings")

        if key in self.cache:
            return self.cache[key]
        else:
            if self.cache_is_complete: raise KeyError(f"Key {key} not in KVDatabase for scope key {self.key} (and the database is completely cached)")
            cursor = self.conn.execute("SELECT value_json FROM props WHERE key=? LIMIT 1", (key,))
            data = cursor.fetchone()
            if data is None: raise KeyError(f"Key {key} not in KVDatabase for scope key {self.key}")
            else:
                self.cache[key] = json.loads(data[0])
                return self.cache[key]

    def get(self, key: str, if_not_found=None) -> Any:
        """Get a data item by key, from cache if possible, returning the provided value or None if not found."""
        try:
            return self.__getitem__(key)
        except KeyError:
            return if_not_found
    
    def get_or_create(self, key: str, if_not_found: Any) -> Any:
        """Get a data item by key, but if it's not there, return the provided value and also save it."""
        try:
            return self.__getitem__(key)
        except:
            self.__setitem__(key, if_not_found)
            return if_not_found

    @mutates_database
    def __setitem__(self, key: str, value: Any):
        """Set a data item, creating it if not exists, and updating the cache."""
        json_val = json.dumps(value)
        self.conn.execute("INSERT INTO props(key, value_json) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value_json=?", (key, json_val, json_val))
        self.cache[key] = value

    @mutates_database
    def __delitem__(self, key: str):
        """Delete a key from the database, as well as from the cache."""
        # We need to raise exceptions for keys that don't exist, so we'll try getting the value first, ignoring the result.
        self.__getitem__(key)
        self.conn.execute("DELETE FROM props WHERE key=?", (key,))
        del self.cache[key]

    def __contains__(self, key: str) -> bool:
        """
        Returns whether the key is in the database.
        Consults but does not update the cache.
        """
        if key in self.cache:
            return True
        else:
            if self.cache_is_complete: return False
            return self.conn.execute("SELECT 1 FROM props WHERE key=? LIMIT 1", (key,)).fetchone() is not None

    def __iter__(self):
        """
        Returns an iterator over the keys.
        Does not load the keys into memory or into the cache,
        so it is expensive to call unless the database is in the cache_is_complete state.
        """
        if self.cache_is_complete:
            return iter(self.cache)

        cursor = self.conn.execute("SELECT key FROM props")
        def next_item():
            item = cursor.fetchone()
            if item: return item[0]
            else: return None
        
        return iter(next_item, None)

    def keys(self):
        """
        Returns an iterator over the keys.
        Does not load the keys into memory or into the cache,
        so it is expensive to call unless the database is in the cache_is_complete state.
        """
        return self.__iter__()
    
    def items(self, load_into_cache=True):
        """
        Returns an iterator over key-value pairs.
        Also optionally loads the values yielded into cache,
        but this does not put the database into the fully-cached state (because the database may have been mutated during the iteration);
        for that, see populate_cache().
        """
        if self.cache_is_complete:
            return iter(self.cache.items())

        cursor = self.conn.execute("SELECT key, value_json FROM props")
        def next_item():
            item = cursor.fetchone()
            if item:
                k,v = item
                if load_into_cache: self.cache[k] = json.loads(v)
                return (k,v)
            else: return None
        return iter(next_item, None)
    
    def values(self, load_into_cache=True):
        """
        Returns an iterator over the values.
        Is a wrapper around items(), and can do the same caching.
        """
        underlying_iter = self.items(load_into_cache=load_into_cache)
        second_item = lambda x: x[1] if x is not None else None
        return iter(lambda: second_item(next(underlying_iter)))
    
    @mutates_database
    def wipe_everything(self):
        """
        Delete every key and value in the database.
        Also puts the database into the cache_is_complete state
        since after this there are zero items in the database.
        """
        self.conn.execute("DELETE FROM props WHERE 1=1")
        self.cache.clear()
        self.cache_is_complete = True

    def __len__(self) -> int:
        """
        Return the number of rows in the database.
        If cache_is_complete, does not hit the database.
        """
        if self.cache_is_complete:
            return len(self.cache)
        else:
            return self.conn.execute("SELECT count(*) FROM props").fetchone()[0]
        
    def populate_cache(self):
        """
        Iterate over the database, reading every item into cache.
        After this, the database has cache_is_complete, which speeds up many operations.
        """
        # Iterating over self.items() will load every value into the cache,
        # and doing it here ensures that the database will not be changed in the meantime.
        _ = list(self.items(load_into_cache=True))
        self.cache_is_complete = True