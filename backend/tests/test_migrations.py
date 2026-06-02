from pathlib import Path

from alembic import command
from alembic.config import Config


def test_alembic_can_create_initial_sqlite_database(tmp_path):
    database_path = tmp_path / 'haxjobs-migration-test.db'
    config = Config('alembic.ini')
    config.set_main_option('sqlalchemy.url', f'sqlite:///{database_path}')

    command.upgrade(config, 'head')

    assert database_path.exists()


def test_alembic_has_versions_directory():
    assert Path('backend/alembic/versions').is_dir()
