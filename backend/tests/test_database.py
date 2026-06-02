from sqlalchemy import text

from haxjobs_api.database import create_database_engine, create_session_factory


def test_database_session_can_execute_queries(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'haxjobs-test.db'}"
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        result = session.execute(text("select 1"))

    assert result.scalar_one() == 1
