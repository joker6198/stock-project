import unittest
from decimal import Decimal
from stock import Order, OrderBook, Exchange, Side, OrderType, OrderStatus


class TestOrder(unittest.TestCase):
    def test_status_update(self):
        o = Order(1, "SNAP", Side.BUY, OrderType.LIMIT, Decimal("10"), 100)
        self.assertEqual(o.status, OrderStatus.PENDING)

        o.filled = 50
        self.assertEqual(o.status, OrderStatus.PARTIAL)

        o.filled = 100
        self.assertEqual(o.status, OrderStatus.FILLED)


class TestOrderBook(unittest.TestCase):
    def test_sorting_buy(self):
        book = OrderBook("SNAP")
        o1 = Order(1, "SNAP", Side.BUY, OrderType.LIMIT, Decimal("10"), 10)
        o2 = Order(2, "SNAP", Side.BUY, OrderType.LIMIT, Decimal("20"), 10)
        o3 = Order(3, "SNAP", Side.BUY, OrderType.MARKET, None, 10)

        book.add(o1)
        book.add(o2)
        book.add(o3)

        self.assertIsNone(book.bids[0].price)
        self.assertEqual(book.bids[1].price, Decimal("20"))
        self.assertEqual(book.bids[2].price, Decimal("10"))


class TestExchange(unittest.TestCase):
    def setUp(self):
        self.ex = Exchange()

    def test_simple_match(self):
        self.ex.place_order({
            'side': Side.SELL, 'symbol': 'AAPL', 'type': OrderType.LIMIT,
            'price': Decimal("100"), 'qty': 10
        })

        buy_order = self.ex.place_order({
            'side': Side.BUY, 'symbol': 'AAPL', 'type': OrderType.LIMIT,
            'price': Decimal("100"), 'qty': 5
        })

        self.assertEqual(buy_order.status, OrderStatus.FILLED)
        self.assertEqual(buy_order.filled, 5)

        book = self.ex.books['AAPL']
        self.assertEqual(len(book.asks), 1)
        self.assertEqual(book.asks[0].filled, 5)

    def test_market_order_match(self):
        self.ex.place_order({
            'side': Side.SELL, 'symbol': 'FB', 'type': OrderType.LIMIT,
            'price': Decimal("50"), 'qty': 10
        })

        mkt_order = self.ex.place_order({
            'side': Side.BUY, 'symbol': 'FB', 'type': OrderType.MARKET,
            'price': None, 'qty': 10
        })

        self.assertEqual(mkt_order.status, OrderStatus.FILLED)
        self.assertEqual(self.ex.books['FB'].last_price, Decimal("50"))


if __name__ == '__main__':
    unittest.main()
