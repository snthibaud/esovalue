from dataclasses import dataclass
from typing import Optional
from mpmath import mpf, ln, mp

ONE = mpf("1")
ZERO = mpf("0")


@dataclass
class TrinomialNode:
    stock_value: Optional[mpf] = None
    option_value: Optional[mpf] = None
    up: Optional['TrinomialNode'] = None
    middle: Optional['TrinomialNode'] = None
    down: Optional['TrinomialNode'] = None


def get_trinomial_tree(depth: int) -> TrinomialNode:
    assert depth > 0
    lattice = [[TrinomialNode()]]
    for level in range(1, depth):
        lattice.append([TrinomialNode() for _ in range(-level, level+1)])
    for i in range(0, len(lattice)-1):
        width = len(lattice[i])
        for j in range(0, width):
            lattice[i][j].down = lattice[i+1][j]
            lattice[i][j].middle = lattice[i+1][j+1]
            lattice[i][j].up = lattice[i+1][j+2]
    return lattice[0][0]


def set_stock_prices(s0: mpf, u: mpf, root: TrinomialNode):
    q = [(s0, root, True, True)]
    while q:
        s, n, h, l = q.pop()
        if n is not None:
            n.stock_value = s
            if h:
                q.append((s*u, n.up, True, False))
            if l:
                q.append((s/u, n.down, False, True))
            q.append((s, n.middle, False, False))


def present_value(fv: mpf, dt: mpf, r: mpf):
    """
    Calculate present value
    :param fv: Future value
    :param dt: Time difference (in years)
    :param r: Risk-free interest rate
    :return: Present value
    """
    return mp.e**(-r*dt)*fv


def calculate_eso_prices(root: TrinomialNode, k: mpf, dt: mpf, s: mpf, r: mpf, q: mpf, er: mpf, v: mpf,
                         m: Optional[mpf]):
    """
    Calculate the price of an employee stock option over time
    :param root: Root node
    :param k: Strike price
    :param dt: Length of one time step (in years)
    :param s: Volatility (standard deviation)
    :param r: Risk-free interest rate
    :param q: Dividend rate
    :param er: Employee exit rate (over a year)
    :param v: Vesting period (in years)
    :param m: Multiplier for early exercise
    """
    level = [root]
    levels = [level]
    while level:
        children = []
        for i, n in enumerate(level):
            middle_child = n.middle
            if middle_child:
                if i == 0:
                    children.append(n.down)
                children.append(middle_child)
                if i + 1 == len(level):
                    children.append(n.up)
            else:
                break
        level = children
        if level:
            levels.append(level)
    leaves = levels[-1]
    total_steps = len(levels)
    for n in leaves:
        n.option_value = max(ZERO, n.stock_value - k) if (total_steps-1)*dt >= v else ZERO
    for i in range(len(levels)-2, -1, -1):
        for node in levels[i]:
            vested = i * dt >= v
            if vested and m and node.stock_value >= k*m:
                node.option_value = node.stock_value - k
            else:
                a = mp.sqrt(dt/(12*s**2))*(r-q-s**2/2) if s > ZERO else ZERO
                b = ONE/6
                pd = -a + b
                pm = 4*b
                pu = a + b
                if pu <= 0 or pd <= 0 or pm <= 0:
                    raise ValueError("Unexpected probability")
                er_dt = ln(ONE+er)*dt
                option_value = (ONE-er_dt)*present_value(
                    pd*node.down.option_value + pm*node.middle.option_value + pu*node.up.option_value, dt, r)
                if vested:
                    option_value += er_dt*max(node.stock_value-k, ZERO)
                node.option_value = option_value
