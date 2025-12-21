import decimal
from typing import Optional

from models import Side, Order, OrderType


class OrderBook():
    def __init__(self, symbol: str):
        self.symbol = symbol
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


class Exchange():
    def __init__(self):
        self.orders_all = []
        self.books = {}
        self.next_id = 1

    def place_order(self, cmd):
        order_side = Side(cmd['side'])
        order_symbol = cmd['symbol']
        order_type = OrderType(cmd['type'])
        if order_type == OrderType.LIMIT:
            order_price = cmd.get('price')
            if order_price is None:
                raise ValueError('Для LIMIT ордера нужна цена.')
            elif order_price <= 0:
                raise ValueError('Для LIMIT цена должна быть больше 0')
            order_qty = cmd['qty']
        else:
            if cmd.get('price') is not None:
                raise ValueError('Для MARKET ордера цена не указывается.')
            order_price = None
            order_qty = cmd['qty']

        if order_qty <= 0:
            raise ValueError('Количество (qty) должно быть больше 0')

        order_id = self.next_id
        self.next_id += 1

        order = Order(order_id, order_symbol, order_side,
                      order_type, order_price, order_qty, 0)

        self.orders_all.append(order)
        if order_symbol not in self.books:
            self.books[order_symbol] = OrderBook(order_symbol)
        book = self.books[order_symbol]
        book.add(order)
        book.match()
        if order.order_type == OrderType.MARKET and order.filled < order.qty:
            book_list = book.bids if order.side == Side.BUY else book.asks
            if order in book_list:
                book_list.remove(order)

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
            return f'{symbol} BID: N/A ASK: N/A'
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

        return f'{symbol} BID: {isnoneprice(bid)} ASK: {isnoneprice(ask)}'
