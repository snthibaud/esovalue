from typing import Optional, Dict
from hypothesis import given, reproduce_failure, assume
from hypothesis.strategies import composite, none, one_of, fixed_dictionaries, integers, lists, data, SearchStrategy
from mpmath import mpf, mp, ceil
from esovalue.eso import value_eso
mp.dps = 100


dollar_values = integers(min_value=0, max_value=100000).map(lambda v: mpf(v) / 100)
rates = integers(min_value=0, max_value=1000).map(lambda v: mpf(v) / 1000)
years = integers(min_value=0, max_value=100000).map(lambda v: mpf(v) / 1000)


Parameters = Dict[str, Optional[float]]


@composite
def value_eso_parameters(draw) -> Parameters:
    return draw(fixed_dictionaries(dict(
        strike_price=dollar_values, stock_price=one_of(dollar_values, none()),
        volatility=integers(min_value=1, max_value=10000).map(lambda v: mpf(v) / 100), risk_free_rate=rates,
        dividend_rate=rates, exit_rate=integers(min_value=0, max_value=1000).map(lambda v: mpf(v) / 1000),
        vesting_years=years, expiration_years=years,
        m=one_of(integers(min_value=0, max_value=100000).map(lambda v: mpf(v) / 1000), none())
    )))


def get_iterations(parameters: Parameters, max_iterations: int) -> SearchStrategy[int]:
    y = parameters["expiration_years"]
    r = parameters["risk_free_rate"]
    q = parameters["dividend_rate"]
    s = parameters["volatility"]
    min_iterations = max(1, int(ceil(y * (r - q) ** 2 / (2 * s ** 2), prec=0)))
    assume(min_iterations <= max_iterations)
    return integers(min_value=min_iterations, max_value=max_iterations)


@given(value_eso_parameters(), data())
def test_positive_option_value(parameters: Parameters, d):
    iterations = d.draw(get_iterations(parameters, 250))
    assert value_eso(**dict(iterations=iterations), **parameters) >= 0


@given(value_eso_parameters(), data())
def test_conversion(parameters: Parameters, d):
    valuations = [value_eso(**dict(iterations=i), **parameters)
                  for i in sorted(d.draw(lists(get_iterations(parameters, 50), unique=True)))]
    last_differences = [abs(valuations[i]-valuations[-1]) for i in range(len(valuations)-1)]
    assume(all(abs(last_differences[i] - last_differences[i + 1]) >= mpf("0.01")
               for i in range(len(last_differences) - 1)))
    assert last_differences == list(sorted(last_differences, reverse=True))
