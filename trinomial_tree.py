from decimal import Decimal
from typing import NamedTuple, Optional, List


class TrinomialNode(NamedTuple):
    stock_value: Decimal
    option_value: Optional[Decimal]
    up: Optional['TrinomialTreeNode']
    middle: Optional['TrinomialTreeNode']
    down: Optional['TrinomialTreeNode']


def make_empty_node(stock_value: Decimal):
    return TrinomialNode(stock_value=stock_value, up=None, middle=None, down=None)


def get_stock_price(s0: Decimal, u: Decimal, up_movements: int) -> Decimal:
    """
    Get stock price after up_movements up movements.
    :param s0: Stock price at T0
    :param u: Up movement
    :param up_movements: The net number of up-movements (can be negative for down movements).
    :return: Stock price
    """
    return s0*u**up_movements


def get_stock_price_lattice(s0: Decimal, u: Decimal, depth: int) -> List[List[Decimal]]:
    if depth < 1:
        return []
    lattice = [[s0]]
    for level in range(1, depth):
        lattice.append([None for _ in range(-level, level+1)])
    for i in range(1, len(lattice)):
        width = len(lattice[i])
        for j in range(width):
            if j == 0:
                lattice[i][j] = lattice[i-1][0]/u
            elif j == width - 1:
                lattice[i][j] = lattice[i-1][j-2]*u
            else:
                lattice[i][j] = lattice[i-1][j-1]
    return lattice
