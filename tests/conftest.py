import duckdb
import pytest

import generator


@pytest.fixture(scope="session")
def db_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "payments.duckdb"
    generator.build(path)
    return path


@pytest.fixture(scope="session")
def con(db_path):
    return duckdb.connect(str(db_path), read_only=True)
