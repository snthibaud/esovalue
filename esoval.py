import math
from decimal import Decimal
from typing import List, Optional


def stock_prices(s0: Decimal, n: int, u: Decimal, d: Decimal) -> List[List[Optional[Decimal]]]:
    """
    Stock prices in the future.
    :param s0: Current stock price
    :param n: Number of time steps
    :param u: Upper factor
    :param d: Lower factor
    :return: Matrix in which row i contains all prices at quarter i.
    """
    s:  List[List[Optional[Decimal]]]
    s = [[None]*(2**k) for k in range(n+1)]
    s[0][0] = s0
    for i in range(1, n+1):
        for j in range(0, 2**i):
            # print(i,j)
            s[i][j] = s[i-1][j//2]*(u if j % 2 == 0 else d)
    return s


def eso_value(s0: Decimal, vo: Decimal, q: Decimal, k: Decimal, r: Decimal, m: Decimal, ve: int, l: Decimal,
              t: Decimal, n: int = 100) -> Decimal:
    """
    Value an employee stock option based on the Hull/White pricing model.
    (Hull, J., & White, A. (2004). How to value employee stock options. Financial Analysts Journal, 60(1), 114-119.)
    Useful summary for parameters-> https://www.macroption.com/cox-ross-rubinstein-formulas/
    :param s0: Current stock price
    :param vo: Volatility per period
    :param q: Dividend yield per period
    :param n: Number of time steps to calculate
    :param t: Time to expiration in years
    :param k: Strike price
    :param r: Risk-free rate per period
    :param m: Assume options are immediately exercised if the stock price is a multiple m of strike price
        (k*m >= stock price).
    :param ve: First period after vesting ends
    :param l: Rate of employees leaving each year
    :return: Value of employee stock option
    """
    dt = Decimal(t/n)
    u = Decimal(math.e)**(vo * Decimal(math.sqrt(dt)))
    d = 1/u
    s = stock_prices(s0, n, u, d)
    p = Decimal(math.e)**((r-q)*dt)
    f: List[List[Optional[Decimal]]]
    f = [[None]*(2**n) for _ in range(n)]
    f.append([max(sp - k, Decimal(0)) for sp in s[n]])
    for i in range(n-1, -1, -1):
        for j in range(0, 2**i):
            # print("b", i, j)
            y = Decimal(math.e) ** (-l * dt)
            x = y * Decimal(math.e) ** (-r*dt) * (p * f[i + 1][j + 1] + (1 - p) * f[i + 1][j])
            if i*dt > ve:
                intrinsic = s[i][j] - k
                if s[i][j] >= k*m:
                    f[i][j] = intrinsic
                else:
                    f[i][j] = x + (1 - y)*max(intrinsic, Decimal(0))
            else:
                f[i][j] = x
    return f[0][0]
