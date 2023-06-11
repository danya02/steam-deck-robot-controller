from .. import persistence
import pytest
import uuid
import random

def purge_connections():
    """
    Clear all connections and databases, as if performing a clean launch.
    """
    persistence.CONNECTIONS.clear()
    persistence.DATABASES.clear()


def test_database_read_write():
    db = persistence.get_database("test_suite")
    db['hello'] = 'World!'

    # Now we need to remove the database and connections.
    del db
    purge_connections()

    db = persistence.get_database("test_suite")
    assert db['hello'] == 'World!'

def test_database_delete():
    db = persistence.get_database("test_suite")
    db['hello'] = 'World!'
    db.discard_cache()
    assert db['hello'] == 'World!'
    del db['hello']
    db.discard_cache()
    with pytest.raises(KeyError):
        db['hello']
    assert db.get('hello') is None

    del db
    purge_connections()

    db = persistence.get_database('test_suite')
    assert db.get('hello') is None

def test_database_wipe():
    db = persistence.get_database('test_suite')
    db.wipe_everything()
    assert len(db) == 0

    for count in range(100):
        assert len(db) == count
        del db
        purge_connections()
        db = persistence.get_database('test_suite')
        db[str(uuid.uuid4())] = random.random()
    
    db.wipe_everything()
    assert len(db) == 0

def test_database_complete():
    db = persistence.get_database('test_suite')
    db.wipe_everything()
    assert len(db) == 0
    assert db.cache_is_complete

    data = dict()

    for count in range(100):
        assert len(db) == count
        key = str(uuid.uuid4())
        value = random.random()
        data[key] = value
        db[key] = value

    del db
    purge_connections()
    db = persistence.get_database('test_suite')
    db.populate_cache()
    # Break the connection, so that any operation with it would error out
    db.conn = ...  # Ellipsis object: look for this in logs
    # No write operations past this point
    assert db.cache_is_complete
    assert len(db) == len(data)
    for key in db:
        assert data[key] == db[key]
    
    assert set(db) == set(data)
    assert set(db.items()) == set(data.items())
    