import unittest
import decimal
from decimal import Decimal

from models import Side, OrderType, OrderStatus
from exchange import Exchange
from main import parse_action, parse_money


class TestParser(unittest.TestCase):
    """Тесты для парсинга команд из main.py"""

    def test_parse_money(self):
        self.assertEqual(parse_money("100"), Decimal("100.00"))
        self.assertEqual(parse_money("$100.5"), Decimal("100.50"))
        self.assertEqual(parse_money("0.001"), Decimal("0.00"))  # Округление

    def test_parse_place_limit(self):
        cmd = parse_action("BUY ABC LMT $150 10")
        self.assertEqual(cmd['cmd'], 'PLACE')
        self.assertEqual(cmd['side'], 'BUY')
        self.assertEqual(cmd['type'], 'LMT')
        self.assertEqual(cmd['price'], Decimal('150.00'))
        self.assertEqual(cmd['qty'], 10)

    def test_parse_place_market(self):
        cmd = parse_action("SELL AAPL MKT 5")
        self.assertEqual(cmd['cmd'], 'PLACE')
        self.assertEqual(cmd['type'], 'MKT')
        self.assertIsNone(cmd['price'])
        self.assertEqual(cmd['qty'], 5)

    def test_parse_errors(self):
        # Не хватает аргументов
        with self.assertRaises(ValueError):
            parse_action("BUY ABC LMT 100")
        # Неизвестный тип
        with self.assertRaises(ValueError):
            parse_action("BUY ABC STOP 100 10")


class TestExchangeValidation(unittest.TestCase):
    """Тесты защиты от дурака в Exchange"""

    def setUp(self):
        self.ex = Exchange()

    def test_negative_qty(self):
        cmd = {
            'side': 'BUY', 'symbol': 'TEST', 'type': 'LMT',
            'price': Decimal('10'), 'qty': -5
        }
        with self.assertRaisesRegex(ValueError, "Количество.*должно быть больше 0"):
            self.ex.place_order(cmd)

    def test_zero_qty(self):
        cmd = {
            'side': 'SELL', 'symbol': 'TEST', 'type': 'MKT',
            'price': None, 'qty': 0
        }
        with self.assertRaisesRegex(ValueError, "Количество.*должно быть больше 0"):
            self.ex.place_order(cmd)

    def test_limit_negative_price(self):
        cmd = {
            'side': 'BUY', 'symbol': 'TEST', 'type': 'LMT',
            'price': Decimal('-10'), 'qty': 5
        }
        with self.assertRaisesRegex(ValueError, "цена должна быть больше 0"):
            self.ex.place_order(cmd)

    def test_limit_no_price(self):
        cmd = {
            'side': 'BUY', 'symbol': 'TEST', 'type': 'LMT',
            'price': None, 'qty': 5
        }
        with self.assertRaisesRegex(ValueError, "нужна цена"):
            self.ex.place_order(cmd)

    def test_market_with_price(self):
        cmd = {
            'side': 'BUY', 'symbol': 'TEST', 'type': 'MKT',
            'price': Decimal('100'), 'qty': 5
        }
        with self.assertRaisesRegex(ValueError, "цена не указывается"):
            self.ex.place_order(cmd)


class TestMatchingEngine(unittest.TestCase):
    """Тесты логики сведения ордеров"""

    def setUp(self):
        self.ex = Exchange()
        self.symbol = "AAPL"

    def _place(self, side, type_, qty, price=None):
        cmd = {
            'side': side,
            'symbol': self.symbol,
            'type': type_,
            'qty': qty,
            'price': Decimal(str(price)) if price is not None else None
        }
        return self.ex.place_order(cmd)

    def test_simple_match(self):
        # 1. Размещаем продажу: 10 шт по 100
        sell_order = self._place('SELL', 'LMT', 10, 100)
        self.assertEqual(sell_order.status, OrderStatus.PENDING)

        # 2. Размещаем покупку: 10 шт по 100
        buy_order = self._place('BUY', 'LMT', 10, 100)

        # 3. Проверяем исполнение
        self.assertEqual(sell_order.status, OrderStatus.FILLED)
        self.assertEqual(buy_order.status, OrderStatus.FILLED)

        # Стакан должен быть пуст
        book = self.ex.books[self.symbol]
        self.assertEqual(len(book.bids), 0)
        self.assertEqual(len(book.asks), 0)

    def test_no_match_price_mismatch(self):
        # Продают по 100, хотят купить по 90 -> Сделки нет
        s = self._place('SELL', 'LMT', 10, 100)
        b = self._place('BUY', 'LMT', 10, 90)

        self.assertEqual(s.status, OrderStatus.PENDING)
        self.assertEqual(b.status, OrderStatus.PENDING)

        quote = self.ex.quote(self.symbol)
        self.assertIn("BID: $90.00", quote)
        self.assertIn("ASK: $100.00", quote)

    def test_partial_fill(self):
        # Продают 10
        self._place('SELL', 'LMT', 10, 100)
        # Покупают 5
        b = self._place('BUY', 'LMT', 5, 100)

        self.assertEqual(b.status, OrderStatus.FILLED)
        # В стакане должно остаться 5 на продажу
        book = self.ex.books[self.symbol]
        self.assertEqual(len(book.asks), 1)
        self.assertEqual(book.asks[0].qty, 10)
        self.assertEqual(book.asks[0].filled, 5)
        self.assertEqual(book.asks[0].status, OrderStatus.PARTIAL)

    def test_market_ioc_full_fill(self):
        # Есть ликвидность: 10 шт по 100
        self._place('SELL', 'LMT', 10, 100)

        # Маркет покупка 10 шт
        mkt = self._place('BUY', 'MKT', 10)

        self.assertEqual(mkt.status, OrderStatus.FILLED)
        self.assertEqual(len(self.ex.books[self.symbol].asks), 0)

    def test_market_ioc_partial_cancel(self):
        # ВАЖНЫЙ ТЕСТ: Проверка логики удаления остатка

        # Есть ликвидность: только 5 шт по 100
        self._place('SELL', 'LMT', 5, 100)

        # Хочу купить 20 шт по Маркету
        mkt = self._place('BUY', 'MKT', 20)

        # Должно купиться 5, статус PARTIAL
        self.assertEqual(mkt.filled, 5)
        self.assertEqual(mkt.status, OrderStatus.PARTIAL)

        # САМОЕ ГЛАВНОЕ: Остаток (15 шт) не должен висеть в bids
        book = self.ex.books[self.symbol]
        self.assertEqual(len(book.bids), 0)  # IOC сработал, заявку удалили
        self.assertEqual(len(book.asks), 0)  # Продавца съели

    def test_sorting_priority(self):
        # Добавляем заявки в разнобой
        o1 = self._place('BUY', 'LMT', 10, 100)
        o2 = self._place('BUY', 'LMT', 10, 102)  # Лучшая цена
        o3 = self._place('BUY', 'LMT', 10, 101)

        book = self.ex.books[self.symbol]
        # Порядок должен быть: 102, 101, 100
        self.assertEqual(book.bids[0].price, Decimal('102'))
        self.assertEqual(book.bids[1].price, Decimal('101'))
        self.assertEqual(book.bids[2].price, Decimal('100'))

    def test_market_is_cancelled_if_no_liquidity(self):
        # Стоит Лимит на покупку по 100
        limit_order = self._place('BUY', 'LMT', 10, 100)

        # Приходит Маркет на покупку. Продавцов нет.
        mkt = self._place('BUY', 'MKT', 10)

        book = self.ex.books[self.symbol]

        # Проверяем IOC логику:
        # 1. В стакане должен остаться ТОЛЬКО Лимитный ордер
        self.assertEqual(len(book.bids), 1)
        self.assertEqual(book.bids[0], limit_order)

        # 2. Рыночный ордер должен быть удален (не добавлен)
        self.assertNotIn(mkt, book.bids)

    def test_quote_display(self):
        self.assertEqual(self.ex.quote('UNKNOWN'), "UNKNOWN BID: N/A ASK: N/A")

        self._place('BUY', 'LMT', 10, 150.50)
        self._place('SELL', 'LMT', 5, 160.00)

        q = self.ex.quote(self.symbol)
        self.assertEqual(q, f"{self.symbol} BID: $150.50 ASK: $160.00")


if __name__ == '__main__':
    unittest.main()
