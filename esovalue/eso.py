from math import sqrt, e
from typing import Optional
from mpmath import mpf, mp
from esovalue.trinomial_tree import get_trinomial_tree, set_stock_prices, calculate_eso_prices
mp.dps = 100


def make_option_tree(strike_price: mpf, stock_price: Optional[mpf], volatility: mpf, risk_free_rate: mpf,
                     dividend_rate: mpf, exit_rate: mpf, vesting_years: mpf, expiration_years: mpf,
                     iterations: int, m: Optional[mpf]) -> mpf:
    strike_price, stock_price, volatility, risk_free_rate, dividend_rate, exit_rate, vesting_years, expiration_years, \
        m = [mpf(v) if v else v
             for v in [strike_price, stock_price, volatility, risk_free_rate, dividend_rate,
                       exit_rate, vesting_years, expiration_years, m]]
    dt = expiration_years / iterations
    root = get_trinomial_tree(iterations + 1)
    set_stock_prices(strike_price if stock_price is None else stock_price, e ** (volatility * sqrt(3 * dt)), root)
    calculate_eso_prices(root, strike_price, dt, volatility, risk_free_rate, dividend_rate, exit_rate, vesting_years,
                         m)
    return root


def value_eso(strike_price: mpf, stock_price: Optional[mpf], volatility: mpf, risk_free_rate: mpf,
              dividend_rate: mpf, exit_rate: mpf, vesting_years: mpf, expiration_years: mpf,
              iterations: int, m: Optional[mpf]) -> mpf:
    """
    Calculate the final value of an employee stock option (assumed 'at the money' if no stock price is given)
    :param strike_price: Strike price
    :param stock_price: Current price of the underlying stock
    :param iterations: More iterations is more precise but requires more memory/CPU
    :param risk_free_rate: Risk-free interest rate
    :param dividend_rate: Dividend rate
    :param exit_rate: Employee exit rate (over a year)
    :param vesting_years: Vesting period (in years)
    :param expiration_years: Years until expiration
    :param volatility: Volatility (standard deviation on returns)
    :param m: Strike price multiplier for early exercise (exercise when the strike_price*m >= stock_price)
    :return: Value in same currency as given strike price
    """
    return make_option_tree(strike_price, stock_price, volatility, risk_free_rate, dividend_rate, exit_rate,
                            vesting_years, expiration_years, iterations, m).option_value
