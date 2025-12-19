import unittest
from decimal import Decimal

from models import Order, Side, OrderType, OrderStatus
from exchange import Exchange, OrderBook
from main import parse_action


class TestParser(unittest.TestCase):
    def test_empty_input(self):
        # Проверяем, что пустая строка возвращает None, а не падает
        self.assertIsNone(parse_action(""))
        self.assertIsNone(parse_action("   "))

    def test_unknown_command(self):
        # Проверяем, что на неизвестную команду летит ошибка
        with self.assertRaisesRegex(ValueError, "Неизвестная команда"):
            parse_action("HELLO WORLD")

    def test_incomplete_buy_order(self):
        # Пользователь ввел только "BUY"
        with self.assertRaisesRegex(ValueError, "Неполная команда"):
            parse_action("BUY")

        # Пользователь ввел "BUY AAPL" (забыл тип)
        with self.assertRaisesRegex(ValueError, "Неполная команда"):
            parse_action("BUY AAPL")

    def test_bad_market_order(self):
        # MARKET ордер без количества: BUY AAPL MKT
        with self.assertRaisesRegex(ValueError, "нужно указать количество"):
            parse_action("BUY AAPL MKT")

    def test_bad_limit_order(self):
        # LIMIT ордер без цены: BUY AAPL LMT
        with self.assertRaisesRegex(ValueError, "нужны цена и количество"):
            parse_action("BUY AAPL LMT")

    def test_valid_parsing(self):
        # Проверяем, что нормальный ввод все еще работает
        res = parse_action("BUY AAPL LMT 100 5")
        self.assertEqual(res['cmd'], 'PLACE')
        self.assertEqual(res['price'], Decimal("100"))


class TestOrder(unittest.TestCase):
    def test_status_update(self):
        # ... твои старые проверки (PENDING, PARTIAL, FILLED) ...
        o = Order(1, "SNAP", Side.BUY, OrderType.LIMIT, Decimal("10"), 100)
        self.assertEqual(o.status, OrderStatus.PENDING)

        # ... (остальной старый код) ...

    def test_invalid_status_error(self):
        # Создаем ордер
        o = Order(1, "SNAP", Side.BUY, OrderType.LIMIT, Decimal("10"), 100)

        # Симулируем баг: заполнили больше, чем заказывали
        o.filled = 150

        # Проверяем, что вылетает ошибка при попытке узнать статус
        with self.assertRaises(ValueError):
            _ = o.status


class TestExchange(unittest.TestCase):
    def setUp(self):
        self.ex = Exchange()

    def test_place_order_from_parser_output(self):
        # Симулируем, как будто данные пришли из main.py
        cmd = {
            'cmd': 'PLACE',
            'side': Side.BUY,
            'symbol': 'TSLA',
            'type': OrderType.LIMIT,
            'price': Decimal('200'),
            'qty': 10
        }
        order = self.ex.place_order(cmd)

        self.assertEqual(order.symbol, 'TSLA')
        self.assertEqual(len(self.ex.books['TSLA'].bids), 1)


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
