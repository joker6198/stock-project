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


class OrderBook():
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.last_price: Optional[decimal.Decimal] = None
        self.bids: list[Order] = []
        self.asks: list[Order] = []

    def add(self, order: Order):
        if order.side == Side.BUY:
            self.bids.append(order)
            self.bids.sort(key=lambda o: decimal.Decimal(
                'Infinity') if o.price is None else o.price, reverse=True)
        elif order.side == Side.SELL:
            self.asks.append(order)
            self.asks.sort(key=lambda o: 0 if o.price is None else o.price)

    def match(self):
        while True:
            if not self.bids or not self.asks:
                return

            best_buy = self.bids[0]
            best_sell = self.asks[0]

            if best_buy.price is not None and best_sell.price is not None:
                if best_buy.price < best_sell.price:
                    return

            buy_remaining = best_buy.qty - best_buy.filled
            sell_remaining = best_sell.qty - best_sell.filled
            trade_qty = min(buy_remaining, sell_remaining)
            best_buy.filled += trade_qty
            best_sell.filled += trade_qty

            if best_buy.filled == best_buy.qty:
                self.bids.pop(0)
            if best_sell.filled == best_sell.qty:
                self.asks.pop(0)

            trade_price = best_sell.price if best_sell.price is not None else best_buy.price
            self.last_price = trade_price


class Exchange():
    def __init__(self):
        self.orders_all = []
        self.books = {}
        self.last_price = {}
        self.next_id = 1

    def place_order(self, cmd):
        order_side = cmd['side']
        order_symbol = cmd['symbol']
        order_type = cmd['type']
        if order_type == OrderType.LIMIT:
            order_price = cmd['price']
            order_qty = cmd['qty']
        else:
            order_price = None
            order_qty = cmd['qty']

        order_id = self.next_id
        self.next_id += 1

        order = Order(order_id, order_symbol, order_side,
                      order_type, order_price, order_qty, 0)

        self.orders_all.append(order)
        if order_symbol not in self.books:
            self.books[order_symbol] = OrderBook(order_symbol)
        self.books[order_symbol].add(order)
        self.books[order_symbol].match()

        return order

    def view_orders(self):
        for order in self.orders_all:
            if order.order_type == OrderType.MARKET:
                print(
                    f"{order.id}. {order.symbol} {order.order_type.value} {order.side.value} N/A {order.filled}/{order.qty} {order.status.value}")
            else:
                print(
                    f"{order.id}. {order.symbol} {order.order_type.value} {order.side.value} ${order.price:.2f} {order.filled}/{order.qty} {order.status.value}")

    def quote(self, symbol):
        def isnoneprice(price: Optional[decimal.Decimal]):
            if price is None:
                return 'N/A'
            else:
                return f'${price:.2f}'

        if symbol not in self.books:
            return f'{symbol} BID: N/A ASK: N/A LAST: N/A'
        else:
            book = self.books[symbol]

        bid = None
        ask = None
        for order in book.bids:
            if order.price is not None:
                bid = order.price
                break

        for order in book.asks:
            if order.price is not None:
                ask = order.price
                break

        last = book.last_price

        return f'{symbol} BID: {isnoneprice(bid)} ASK: {isnoneprice(ask)} LAST: {isnoneprice(last)}'


def parse_money(token: str):
    s = token.strip()
    if s.startswith('$'):
        s = s[1:]

    value = decimal.Decimal(s)
    return value.quantize(MONEY_STEP, rounding=decimal.ROUND_HALF_UP)


def parse_action(line: str):
    parts = line.split()
    if parts[0] == 'VIEW' and parts[1] == 'ORDERS':
        return {'cmd': 'VIEW_ORDERS'}
    elif parts[0] == 'QUOTE' and len(parts) == 2:
        return {'cmd': 'QUOTE', 'symbol': parts[1]}
    elif parts[0] == 'QUIT':
        return {'cmd': 'QUIT'}
    elif parts[0] in (Side.BUY, Side.SELL):
        if parts[2] == OrderType.MARKET:
            price = None
            qty = int(parts[3])
        else:
            price = parse_money(parts[3])
            qty = int(parts[4])
        return {'cmd': 'PLACE', 'side': parts[0], 'symbol': parts[1],
                'type': parts[2], 'price': price, 'qty': qty}


def main():
    ex = Exchange()

    while True:
        line = input()
        cmd = parse_action(line)

        if cmd['cmd'] == 'VIEW_ORDERS':
            ex.view_orders()
        elif cmd['cmd'] == 'QUOTE':
            print(ex.quote(cmd['symbol']))
        elif cmd['cmd'] == 'PLACE':
            ex.place_order(cmd)
        elif cmd['cmd'] == 'QUIT':
            break


if __name__ == '__main__':
    main()
