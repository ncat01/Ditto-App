"""Choose the isolated test database before any test module imports the application."""
import os, tempfile
from pathlib import Path
TEST_DIRECTORY=tempfile.TemporaryDirectory(prefix='ditto-tests-')
os.environ['DITTO_DATABASE_URL']='sqlite:///'+(Path(TEST_DIRECTORY.name)/'test.db').as_posix()
os.environ['DITTO_MEDIA_ROOT']=(Path(TEST_DIRECTORY.name)/'media').as_posix()
os.environ['DITTO_DEMO_MODE']='true'
from app.database.db import engine

def pytest_sessionfinish(session,exitstatus):
    engine.dispose()
    resolved=Path(TEST_DIRECTORY.name).resolve()
    if resolved.parent==Path(tempfile.gettempdir()).resolve() and resolved.name.startswith('ditto-tests-'):
        TEST_DIRECTORY.cleanup()
