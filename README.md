# ESO-value
Receiving stock options from your company? Wondering what they are worth? ESO-value calculates the value of
Employee Stock Options based on the Hull-White model[1][2].
This library is used in the [ESO valuation app](https://eso.stephanethibaud.xyz/).

## Installation
Run `pip install esovalue`

## Usage
```python
from esovalue.eso import value_eso

value_eso(strike_price=50, stock_price=50, volatility=0.3, risk_free_rate=0.075,
          dividend_rate=0.025, exit_rate=0.03, vesting_years=3, expiration_years=10, 
          iterations=1000, m=3)
```
Description of the parameters:
```
strike_price		- Strike price
stock_price		- Current price of the underlying stock
iterations		- More iterations is more precise but requires more memory/CPU
risk_free_rate		- Risk-free interest rate
dividend_rate		- Dividend rate
exit_rate		- Employee exit rate (over a year)
vesting_years		- Vesting period (in years)
expiration_years	- Years until expiration
volatility		- Volatility (standard deviation on returns)
m			- Strike price multiplier for early exercise 
                          (exercise when the strike_price*m >= stock_price)
```

## References
[1]: Hull, J, and White, A:  How to Value Employee Stock Options Financial Analysts Journal, Vol. 60, No. 1,
    January/February 2004, 114-119.\
[2]: Hull, J. (2018). Options, Futures, and Other Derivatives (Global Edition).
