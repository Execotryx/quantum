"""One-sided Poisson failure pricing for the vendored DQI screen."""

from math import ceil

from scipy.stats import chi2


def pooled_failures(failures: list[int]) -> int:
    """Return the 95% upper bound per salt, rounded up to a shot count."""
    if not failures or any(type(count) is not int or count < 0 for count in failures):
        raise ValueError("need nonnegative integer failure counts from at least one salt")
    upper = float(chi2.ppf(0.95, 2 * sum(failures) + 2)) / 2
    return ceil(upper / len(failures))
