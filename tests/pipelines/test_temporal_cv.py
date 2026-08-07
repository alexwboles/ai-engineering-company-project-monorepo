from __future__ import annotations

from scripts.evaluate_sales_model import temporal_cv_splits
from scripts.train_sales_model import load_sales, split_by_year


def test_temporal_cv_preserves_chronological_order() -> None:
    train, _test = split_by_year(load_sales())
    folds = temporal_cv_splits(len(train), n_splits=5)

    assert len(folds) == 5
    validation_ranges: list[tuple[int, int]] = []
    for train_idx, validation_idx in folds:
        assert list(train_idx) == sorted(train_idx)
        assert list(validation_idx) == sorted(validation_idx)
        assert max(train_idx) < min(validation_idx)
        validation_ranges.append((int(validation_idx[0]), int(validation_idx[-1])))

    assert all(
        earlier_end < later_start
        for (_, earlier_end), (later_start, _) in zip(validation_ranges, validation_ranges[1:])
    )
