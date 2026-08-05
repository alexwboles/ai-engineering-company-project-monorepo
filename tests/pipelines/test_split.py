from __future__ import annotations

from scripts.train_sales_model import load_sales, split_by_year


def test_split_respects_eight_year_training_and_two_year_test_rule() -> None:
    train, test = split_by_year(load_sales())
    train_years = set(train["month"].dt.year)
    test_years = set(test["month"].dt.year)

    assert len(train_years) == 8
    assert len(test_years) == 2
    assert train_years.isdisjoint(test_years)
    assert max(train_years) < min(test_years)
    assert set(train["month"]).isdisjoint(set(test["month"]))
