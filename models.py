import decimal
from enum import Enum
from dataclasses import dataclass
from typing import Optional

MONEY_STEP = decimal.Decimal('0.01')


class Side(str, Enum):
    BUY = 'BUY'
    SELL = 'SELL'


class OrderType(str, Enum):
    LIMIT = 'LMT'
    MARKET = 'MKT'


class OrderStatus(str, Enum):
    PENDING = 'PENDING'
    PARTIAL = 'PARTIAL'
    FILLED = 'FILLED'


@dataclass
class Order:
    id: int
    symbol: str
    side: Side
    order_type: OrderType
    price: Optional[decimal.Decimal]
    qty: int
    filled: int = 0

    @property
    def status(self) -> OrderStatus:
        if self.filled == 0:
            return OrderStatus.PENDING
        elif 0 < self.filled < self.qty:
            return OrderStatus.PARTIAL
        elif self.filled == self.qty:
            return OrderStatus.FILLED
        else:
            raise ValueError(
                f'Некорректное значение filled: {self.filled} (qty: {self.qty})')
