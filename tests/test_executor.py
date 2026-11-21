"""The executor stops a query that runs too long and says why."""
import pytest

from executor import run
from validator import Rejected


def test_slow_query_is_cut_off_with_a_reason(db_path):
    slow = "SELECT COUNT(*) FROM transactions AS a, transactions AS b, transactions AS c"
    with pytest.raises(Rejected, match="cut off after 0.2 seconds"):
        run(slow, db_path, timeout=0.2)


def test_query_cannot_read_files_outside_the_database(db_path):
    with pytest.raises(Rejected, match="could not run.*file system operations are disabled"):
        run("SELECT content FROM read_text('/etc/hosts')", db_path)
