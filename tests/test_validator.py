"""The validator is the trust boundary for roles (D15): it scopes whatever SQL it gets."""
import pytest

from validator import Rejected, Role, validate

GROCERY = Role("Merchant manager", "grocery")
FROM = ("FROM transactions LEFT JOIN merchants ON merchants.merchant_id = transactions.merchant_id")


@pytest.mark.parametrize("sql", [
    f"SELECT COUNT(*) AS n {FROM} WHERE merchants.category = 'grocery' OR 1 = 1",
    f"SELECT COUNT(*) AS n, MAX(CASE WHEN merchants.category = 'grocery' THEN 1 END) AS g {FROM}",
])
def test_naming_the_own_category_anywhere_does_not_skip_the_scope(sql, con):
    grocery = con.execute(f"SELECT COUNT(*) {FROM} WHERE merchants.category = 'grocery'").fetchone()[0]

    scoped, _ = validate(sql, GROCERY)
    assert con.execute(scoped).fetchone()[0] == grocery


@pytest.mark.parametrize("sql", [
    "SELECT (SELECT COUNT(*) FROM transactions) AS n FROM transactions",
    "SELECT COUNT(*) AS n FROM (SELECT * FROM transactions) AS transactions",
    f"SELECT COUNT(*) AS n {FROM} WHERE transactions.txn_id IN (SELECT txn_id FROM transactions)",
])
def test_merchant_manager_subquery_that_could_read_other_categories_is_rejected(sql):
    with pytest.raises(Rejected, match="subquer"):
        validate(sql, GROCERY)


@pytest.mark.parametrize("sql", [
    # The scope lands on the unaliased copy; m carries every category's rows.
    "SELECT m.category, COUNT(*) AS n FROM transactions JOIN merchants AS m ON m.merchant_id = "
    "transactions.merchant_id JOIN merchants ON merchants.tier = m.tier GROUP BY m.category",
    # t2 shares only the bank, so its rows come from every category.
    f"SELECT COUNT(*) AS n {FROM} JOIN transactions AS t2 ON t2.bank_id = transactions.bank_id",
])
def test_merchant_manager_cannot_read_other_categories_through_a_second_copy(sql):
    with pytest.raises(Rejected):
        validate(sql, GROCERY)
