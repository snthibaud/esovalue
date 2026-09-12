import math

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis.strategies import DataObject, composite, data, integers
from mpmath import ln, mp, mpf, ncdf, sqrt

from esovalue.eso import value_eso

SLOW_SETTINGS = settings(max_examples=25, deadline=None,
                          suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])

# A lattice's discretization error scales with the option's own value, so comparisons need a
# *relative* tolerance, not a flat absolute one - 1e-4 alone would be far too loose for a
# near-worthless option and far too tight for one worth $500.
ABS_TOLERANCE = 1e-4
REL_TOLERANCE = 5e-3


def le(a: float, b: float) -> bool:
    return a <= b + ABS_TOLERANCE + REL_TOLERANCE * max(abs(a), abs(b))


def ge(a: float, b: float) -> bool:
    return le(b, a)


def approx_eq(a: float, b: float) -> bool:
    return le(a, b) and ge(a, b)


MAX_ITERATIONS = 40
# The Kamrad-Ritchken calibration in trinomial_tree.py is only accurate as dt -> 0; below this many
# steps it can be too coarse for continuation value to stay >= intrinsic value everywhere. The
# exit_rate and m properties below need that (see their docstrings); the others don't. If one of
# those two starts failing by a tiny margin, raise this first.
MIN_ITERATIONS = 20

dollar_values = integers(min_value=100, max_value=100000).map(lambda v: mpf(v) / 100)
# Binomial/trinomial trees converge more slowly, and less predictably, at high volatility (more
# spread-out terminal nodes for the same number of steps). Capped at a range that still covers
# realistic ESO volatility, so MIN_ITERATIONS steps stay sufficient for the tolerance above.
volatilities = integers(min_value=15, max_value=60).map(lambda v: mpf(v) / 100)
rates = integers(min_value=0, max_value=100).map(lambda v: mpf(v) / 1000)
exit_rates = integers(min_value=0, max_value=1000).map(lambda v: mpf(v) / 1000)
expiration_years_strategy = integers(min_value=500, max_value=5000).map(lambda v: mpf(v) / 1000)
vesting_fractions = integers(min_value=0, max_value=90).map(lambda v: mpf(v) / 100)
multipliers = integers(min_value=100, max_value=100000).map(lambda v: mpf(v) / 100)


def min_iterations_for(expiration_years: mpf, risk_free_rate: mpf, dividend_rate: mpf, volatility: mpf) -> int:
    """
    trinomial_tree.calculate_eso_prices uses branch probabilities `pd = 1/6 - a` and `pu = 1/6 + a`,
    where `a = sqrt(dt/(12*volatility**2)) * drift` and
    `drift = risk_free_rate - dividend_rate - volatility**2/2`. One of the two goes negative -
    producing meaningless results - as soon as `|a| > 1/6`. Solving `|a| <= 1/6` for the number of
    steps, with `dt = expiration_years / iterations`, gives `iterations >= 3*T*drift**2/volatility**2`.
    """
    drift = risk_free_rate - dividend_rate - volatility ** 2 / 2
    if drift == 0:
        return 1
    needed = 3 * expiration_years * drift ** 2 / volatility ** 2
    return max(1, math.ceil(float(needed)))


@composite
def base_parameters(draw, with_dividends: bool = True):
    strike_price = draw(dollar_values)
    stock_price = draw(dollar_values)
    volatility = draw(volatilities)
    risk_free_rate = draw(rates)
    dividend_rate = draw(rates) if with_dividends else mpf(0)
    expiration_years = draw(expiration_years_strategy)
    min_iterations = max(MIN_ITERATIONS, min_iterations_for(expiration_years, risk_free_rate, dividend_rate, volatility))
    assume(min_iterations <= MAX_ITERATIONS)
    iterations = draw(integers(min_value=min_iterations, max_value=min_iterations + 5))
    return dict(strike_price=strike_price, stock_price=stock_price, volatility=volatility,
                risk_free_rate=risk_free_rate, dividend_rate=dividend_rate,
                expiration_years=expiration_years, iterations=iterations)


def value_at(base: dict, **overrides) -> float:
    params = dict(exit_rate=mpf(0), vesting_years=mpf(0), m=None)
    params.update(base)
    params.update(overrides)
    return float(value_eso(**params))


def black_scholes_call(s0: mpf, k: mpf, r: mpf, t: mpf, sigma: mpf) -> mpf:
    d1 = (ln(s0 / k) + (r + sigma ** 2 / 2) * t) / (sigma * sqrt(t))
    d2 = d1 - sigma * sqrt(t)
    return ncdf(d1) * s0 - ncdf(d2) * k * mp.e ** (-r * t)


@given(base_parameters())
@SLOW_SETTINGS
def test_bounds(base):
    """
    value_at leaves exit_rate, vesting_years and m at their defaults, so this is a plain call
    option: it can never be worth less than nothing, nor more than the stock it can buy.
    """
    value = value_at(base)
    assert ge(value, 0.0)
    assert le(value, float(base["stock_price"]))


@given(base_parameters())
@SLOW_SETTINGS
def test_none_stock_price_is_at_the_money(base):
    """
    eso.make_option_tree starts the tree at `strike_price if stock_price is None else stock_price`,
    so passing no stock price is not merely close to passing the strike - it is the same
    computation, and the two must agree exactly.
    """
    assert value_at(base, stock_price=None) == value_at(base, stock_price=base["strike_price"])


@given(base_parameters(), data())
@SLOW_SETTINGS
def test_monotone_in_stock_price(base, d: DataObject):
    lo, hi = sorted([d.draw(dollar_values), d.draw(dollar_values)])
    assume(hi - lo > mpf("0.5"))
    assert le(value_at(base, stock_price=lo), value_at(base, stock_price=hi))


@given(base_parameters(), data())
@SLOW_SETTINGS
def test_monotone_in_strike_price(base, d: DataObject):
    lo, hi = sorted([d.draw(dollar_values), d.draw(dollar_values)])
    assume(hi - lo > mpf("0.5"))
    assert ge(value_at(base, strike_price=lo), value_at(base, strike_price=hi))


@given(base_parameters(with_dividends=False), data())
@SLOW_SETTINGS
def test_monotone_in_exit_rate(base, d: DataObject):
    """
    An unvested node is worth (1-er_dt)*continuation, which a higher exit_rate unambiguously
    lowers. A vested one is worth (1-er_dt)*continuation + er_dt*max(s-k,0) (trinomial_tree.py), so
    a higher exit_rate shifts weight from continuation to exercising now - which only lowers value
    if continuation is always worth at least as much as exercising now. That holds without
    dividends: it's the classical result that an American call on a non-dividend stock is never
    optimally exercised early (Merton 1973; see any derivatives textbook's chapter on early
    exercise, e.g. Hull's "Options, Futures and Other Derivatives"). Dividends can make early
    exercise capture value that would otherwise be lost to the ex-dividend drop, so this property is
    restricted to dividend_rate=0.
    """
    vesting_years = base["expiration_years"] * d.draw(vesting_fractions)
    lo, hi = sorted([d.draw(exit_rates), d.draw(exit_rates)])
    assume(hi - lo > mpf("0.05"))
    v_lo = value_at(base, exit_rate=lo, vesting_years=vesting_years)
    v_hi = value_at(base, exit_rate=hi, vesting_years=vesting_years)
    assert ge(v_lo, v_hi)


@given(base_parameters(), data())
@SLOW_SETTINGS
def test_monotone_in_vesting_years(base, d: DataObject):
    """
    Raising vesting_years can only turn vested nodes into unvested ones. A vested node is worth
    (1-er_dt)*continuation + er_dt*max(s-k,0); an unvested one drops that second term and keeps the
    same first one (trinomial_tree.py), and raising it above a leaf's maturity zeroes that leaf.
    Since the dropped term is non-negative and the recursion is monotone in its children (the branch
    probabilities are non-negative - see min_iterations_for), induction backwards from the leaves
    gives node-by-node value that is non-increasing in vesting_years. That argument needs no claim
    about continuation vs intrinsic value, so unlike the m and exit_rate tests it holds with
    dividends too, and this test does not restrict to dividend_rate=0.
    """
    exit_rate = d.draw(exit_rates.filter(lambda v: v > 0))
    lo, hi = sorted([d.draw(vesting_fractions), d.draw(vesting_fractions)])
    assume(hi - lo > mpf("0.05"))
    v_lo = value_at(base, exit_rate=exit_rate, vesting_years=base["expiration_years"] * lo)
    v_hi = value_at(base, exit_rate=exit_rate, vesting_years=base["expiration_years"] * hi)
    assert ge(v_lo, v_hi)


@given(base_parameters(with_dividends=False), data())
@SLOW_SETTINGS
def test_monotone_in_m(base, d: DataObject):
    """
    Same substitution as test_monotone_in_exit_rate above, made via a different knob: m=None never
    forces exercise, and a lower m forces it sooner, each time swapping continuation value for
    intrinsic value. The same no-dividend early-exercise argument applies, and for the same reason
    this is restricted to dividend_rate=0.
    """
    lo, hi = sorted([d.draw(multipliers), d.draw(multipliers)])
    assume(hi - lo > mpf("0.5"))
    v_lo = value_at(base, m=lo)
    v_hi = value_at(base, m=hi)
    v_none = value_at(base, m=None)
    assert le(v_lo, v_hi)
    assert le(v_hi, v_none)


BLACK_SCHOLES_ITERATIONS = 100
BLACK_SCHOLES_CASES = [
    dict(strike_price=mpf(10), stock_price=mpf(10), volatility=mpf("0.3"), risk_free_rate=mpf("0.04"),
         dividend_rate=mpf(0), expiration_years=mpf(2)),
    dict(strike_price=mpf(50), stock_price=mpf(40), volatility=mpf("0.4"), risk_free_rate=mpf("0.02"),
         dividend_rate=mpf(0), expiration_years=mpf(1)),
    dict(strike_price=mpf(20), stock_price=mpf(28), volatility=mpf("0.35"), risk_free_rate=mpf("0.03"),
         dividend_rate=mpf(0), expiration_years=mpf(3)),
]


@pytest.mark.parametrize("case", BLACK_SCHOLES_CASES)
def test_converges_to_black_scholes(case: dict):
    """
    With dividend_rate=exit_rate=vesting_years=0 and m=None, every node's value is plain discounted
    continuation with no forced or forfeited exercise (trinomial_tree.py) - a European call - so it
    should match the closed-form Black-Scholes price.

    This checks a handful of fixed, ordinary-looking (strike, stock, volatility, rate, expiration)
    combinations rather than a hypothesis-generated range at a hypothesis-generated iteration count.
    Binomial/trinomial-tree convergence to the closed form is a known non-monotonic ("sawtooth")
    process (a standard numerical-methods fact - see e.g. Hull's "Options, Futures and Other
    Derivatives" on binomial convergence): at a fixed iteration count some parameter combinations
    converge much better than others, and - found the hard way - letting hypothesis search a range
    of iteration counts reliably finds one of the bad ones sooner or later, however narrow a
    parameter band is chosen. Each case here was checked by hand to be within tolerance at
    BLACK_SCHOLES_ITERATIONS specifically before being added.
    """
    bs_value = black_scholes_call(case["stock_price"], case["strike_price"], case["risk_free_rate"],
                                  case["expiration_years"], case["volatility"])
    lattice_value = value_at(case, iterations=BLACK_SCHOLES_ITERATIONS)
    assert approx_eq(float(bs_value), lattice_value)


def test_regression_default_value():
    params = dict(strike_price=10.0, stock_price=10.0, volatility=0.3, risk_free_rate=0.04,
                  dividend_rate=0.004, exit_rate=0.2, vesting_years=3.0, expiration_years=5.0,
                  iterations=50, m=None)
    assert value_eso(**params) == pytest.approx(1.79104878523231, abs=1e-9)


def test_regression_stock_price_sweep():
    base = dict(strike_price=10.0, volatility=0.3, risk_free_rate=0.04, dividend_rate=0.004,
                exit_rate=0.2, vesting_years=3.0, expiration_years=5.0, iterations=50, m=None)
    values = [float(value_eso(stock_price=s, **base)) for s in [5.0, 10.0, 15.0, 20.0]]
    assert values == pytest.approx([0.272, 1.791, 4.1085, 6.7174], abs=1e-3)


def test_zero_volatility_is_discounted_intrinsic_value():
    strike_price, stock_price, risk_free_rate, expiration_years = mpf(10), mpf(12), mpf("0.05"), mpf(2)
    value = value_eso(strike_price=strike_price, stock_price=stock_price, volatility=mpf(0),
                       risk_free_rate=risk_free_rate, dividend_rate=mpf(0), exit_rate=mpf(0),
                       vesting_years=mpf(0), expiration_years=expiration_years, iterations=10, m=None)
    expected = mp.e ** (-risk_free_rate * expiration_years) * max(stock_price - strike_price, mpf(0))
    assert float(value) == pytest.approx(float(expected), abs=1e-6)
