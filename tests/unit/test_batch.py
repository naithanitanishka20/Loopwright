import math

import pytest

from loopwright.batch import MAX_WORKERS, p50_p95, run_batch, sample


@pytest.mark.parametrize("workers", [0, -1, True, 1.5])
def test_run_batch_rejects_invalid_worker_counts(workers):
    with pytest.raises(ValueError, match="workers must be a positive integer"):
        run_batch([], workers=workers)


def test_run_batch_rejects_unbounded_worker_counts():
    with pytest.raises(ValueError, match=f"workers must be at most {MAX_WORKERS}"):
        run_batch([], workers=MAX_WORKERS + 1)


@pytest.mark.parametrize("size", [0, -1, True, 1.5])
def test_sample_rejects_invalid_sizes(size):
    with pytest.raises(ValueError, match="sample size must be a positive integer"):
        sample([1, 2], size, seed=7)


def test_percentiles_reject_empty_input():
    with pytest.raises(ValueError, match="at least one runtime"):
        p50_p95([])


@pytest.mark.parametrize("times", [[math.nan], [math.inf], [True]])
def test_percentiles_reject_non_finite_or_boolean_runtimes(times):
    with pytest.raises(ValueError, match="finite non-negative numbers"):
        p50_p95(times)
