# from typing import Optional, Dict
# from hypothesis import given, assume, reproduce_failure
# from hypothesis.strategies import composite, none, one_of, fixed_dictionaries, integers, lists, data, SearchStrategy, \
#     DataObject, just
# from mpmath import mpf, mp, ceil, ncdf
# from esovalue.eso import value_eso
# mp.dps = 50
#
#
# dollar_values = integers(min_value=1, max_value=100000).map(lambda v: mpf(v) / 100)
# stock_prices = integers(min_value=100, max_value=100000).map(lambda v: mpf(v) / 100)
# rates = integers(min_value=0, max_value=200).map(lambda v: mpf(v) / 1000)
# years = integers(min_value=250, max_value=100000).map(lambda v: mpf(v) / 1000)
#
#
# Parameters = Dict[str, Optional[float]]
# m_values = one_of(integers(min_value=0, max_value=100000).map(lambda v: mpf(v) / 1000), none())
#
#
# @composite
# def value_eso_parameters(draw, with_m: bool = True, with_vesting_years: bool = True, with_exit_rate: bool = True,
#                          with_dividends: bool = True) -> Parameters:
#     return draw(fixed_dictionaries(dict(
#         strike_price=dollar_values, stock_price=one_of(stock_prices, none()),
#         volatility=integers(min_value=1, max_value=100).map(lambda v: mpf(v) / 10), risk_free_rate=rates,
#         dividend_rate=rates if with_dividends else just(mpf(0)),
#         exit_rate=integers(min_value=0, max_value=1000).map(
#             lambda v: mpf(v) / 1000) if with_exit_rate else just(mpf(0)),
#         vesting_years=years if with_vesting_years else just(mpf(0)), expiration_years=years,
#         m=m_values if with_m else none()
#     )))
#
#
# def get_iterations(parameters: Parameters, max_iterations: int) -> SearchStrategy[int]:
#     y = parameters["expiration_years"]
#     r = parameters["risk_free_rate"]
#     q = parameters["dividend_rate"]
#     s = parameters["volatility"]
#     min_iterations = max(100, ceil(3*y*(r-q-s**2)**2/s**2, prec=0))
#     assume(min_iterations <= max_iterations)
#     return integers(min_value=min_iterations, max_value=max_iterations)
#
#
# # @given(value_eso_parameters(), data())
# # def test_positive_option_value(parameters: Parameters, d):
# #     iterations = d.draw(get_iterations(parameters, 250))
# #     assert value_eso(**dict(iterations=iterations), **parameters) >= 0
# #
# #
# # @given(value_eso_parameters(), data())
# # def test_conversion(parameters: Parameters, d):
# #     valuations = [value_eso(**dict(iterations=i), **parameters)
# #                   for i in sorted(d.draw(lists(get_iterations(parameters, 50), unique=True)))]
# #     last_differences = [abs(valuations[i]-valuations[-1]) for i in range(len(valuations)-1)]
# #     assume(all(abs(last_differences[i] - last_differences[i + 1]) >= mpf("0.01")
# #                for i in range(len(last_differences) - 1)))
# #     assert last_differences == list(sorted(last_differences, reverse=True))
# #
# #
#
# # @reproduce_failure('6.36.1', b'AAE49wEAHwItAAAAAAAAAAAJoQEBAA==')
# @given(value_eso_parameters(), data(), m_values)
# def test_higher_m_has_higher_value(parameters: Parameters, d: DataObject, m2: Optional[int]):
#     m1 = parameters["m"]
#     del parameters["m"]
#     iterations = d.draw(get_iterations(parameters, 250))
#     if m1 and m2:
#         ml, mh = sorted([m1, m2])
#     elif m1:
#         ml, mh = m1, m2
#     else:
#         ml, mh = m2, m1
#     assert value_eso(**dict(iterations=iterations, m=mh), **parameters) \
#         - value_eso(**dict(iterations=iterations, m=ml), **parameters) > -0.005
#
#
# def black_scholes(s0: mpf, k: mpf, r: mpf, e: mpf, v: mpf) -> mpf:
#     """
#     Value call option with Black-Scholes model
#     :param s0: Stock price at time 0
#     :param k: Strike price of option
#     :param r: Risk-free rate
#     :param e: Expiration (years)
#     :param v: Volatility
#     :return: Price at time 0
#     """
#     d1 = (1/(v*mp.sqrt(e)))*(mp.ln(s0/k)+(r+v**2/2)*e)
#     d2 = d1 - v*mp.sqrt(e)
#     return ncdf(d1)*s0-ncdf(d2)*k*mp.e**(-r*e)
#
#
# @given(value_eso_parameters(with_m=False, with_vesting_years=False, with_exit_rate=False, with_dividends=False), data())
# def test_converges_to_black_scholes_merton(parameters: Parameters, d: DataObject):
#     value_bs = black_scholes(
#         parameters["strike_price"] if parameters["stock_price"] is None else parameters["stock_price"],
#         parameters["strike_price"], parameters["risk_free_rate"],
#         parameters["expiration_years"], parameters["volatility"])
#     i = d.draw(get_iterations(parameters, 250))
#     assert (abs(value_bs - value_eso(**dict(iterations=i), **parameters))
#             - abs(value_bs-value_eso(**dict(iterations=i+1), **parameters))) > -0.1
