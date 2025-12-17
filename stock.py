import decimal

MONEY_STEP = decimal.Decimal('0.01')


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
        order_status = 'PENDING'
        if order_type == 'LMT':
            order_price = cmd['price']
            order_qty = cmd['qty']
        else:
            order_price = None
            order_qty = cmd['qty']

        order_id = self.next_id
        self.next_id += 1

        order = {'id': order_id, 'symbol': order_symbol, 'side': order_side,
                 'type': order_type, 'price': order_price, 'qty': order_qty,
                 'filled': 0, 'status': order_status}

        self.orders_all.append(order)

        if order_symbol not in self.books:
            self.books[order_symbol] = {'buy': [], 'sell': []}
        side_key = 'buy' if order_side == 'BUY' else 'sell'
        self.books[order_symbol][side_key].append(order)

        self.match(order['symbol'])

        return order

    def view_orders(self):
        for order in self.orders_all:
            if order['type'] == 'MKT':
                return (
                    f"{order['id']} {order['symbol']} {order['type']} {order['side']} N/A {order['filled']}/{order['qty']} {order['status']}")
            else:
                return (
                    f"{order['id']} {order['symbol']} {order['type']} {order['side']} ${order['price']:.2f} {order['filled']}/{order['qty']} {order['status']}")

    def quote(self, symbol):
        if symbol not in self.books:
            bid = None
            ask = None
            last = self.last_price.get(symbol)
        else:
            buy_cand = []
            sell_cand = []

            for i in self.books[symbol]['buy']:
                if i['type'] == 'LMT' and i['filled'] < i['qty']:
                    buy_cand.append(i)
            for i in self.books[symbol]['sell']:
                if i['type'] == 'LMT' and i['filled'] < i['qty']:
                    sell_cand.append(i)

            if buy_cand:
                best_buy = max(buy_cand, key=lambda o: o['price'])
                bid = best_buy['price']
            else:
                bid = None

            if sell_cand:
                best_sell = min(sell_cand, key=lambda o: o['price'])
                ask = best_sell['price']
            else:
                ask = None
            last = self.last_price.get(symbol)

        if bid is None:
            bid_print = 'N/A'
        else:
            bid_print = f"${bid:.2f}"

        if ask is None:
            ask_print = 'N/A'
        else:
            ask_print = f"${ask:.2f}"

        if last is None:
            last_print = 'N/A'
        else:
            last_print = f"${last:.2f}"

        return f'{symbol} BID: {bid_print} ASK: {ask_print} LAST: {last_print}'

    def best_buy_order(self, symbol):
        actives = []
        lmt_actives = []
        if symbol in self.books:
            for order in self.books[symbol]['buy']:
                if order['filled'] < order['qty']:
                    actives.append(order)

            for order in actives:
                if order['type'] == 'LMT':
                    lmt_actives.append(order)

            if lmt_actives:
                best_lmt = max(lmt_actives, key=lambda o: (
                    o['price'], -o['id']))
            else:
                best_lmt = None
        else:
            best_lmt = None
        return best_lmt

    def best_sell_order(self, symbol):
        actives = []
        lmt_actives = []
        if symbol in self.books:
            for order in self.books[symbol]['sell']:
                if order['filled'] < order['qty']:
                    actives.append(order)

            for order in actives:
                if order['type'] == 'LMT':
                    lmt_actives.append(order)

            if lmt_actives:
                best_lmt = min(
                    lmt_actives, key=lambda o: (o['price'], o['id']))
            else:
                best_lmt = None
        else:
            best_lmt = None
        return best_lmt

    def match(self, symbol):
        while True:
            buy = self.best_buy_order(symbol)
            sell = self.best_sell_order(symbol)

            if buy is None or sell is None:
                return

            if buy['price'] < sell['price']:
                return

            trade_qty = min(buy['qty'] - buy['filled'],
                            sell['qty'] - sell['filled'])

            if trade_qty == 0:
                return

            buy['filled'] += trade_qty
            sell['filled'] += trade_qty

            if buy['filled'] == 0:
                buy['status'] = 'PENDING'
            elif 0 < buy['filled'] < buy['qty']:
                buy['status'] = 'PARTIAL'
            elif buy['filled'] == buy['qty']:
                buy['status'] = 'FILLED'
                self.books[symbol]['buy'].remove(buy)

            if sell['filled'] == 0:
                sell['status'] = 'PENDING'
            elif 0 < sell['filled'] < sell['qty']:
                sell['status'] = 'PARTIAL'
            elif sell['filled'] == sell['qty']:
                sell['status'] = 'FILLED'
                self.books[symbol]['sell'].remove(sell)

            self.last_price[symbol] = sell['price']


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
    elif parts[0] in ('BUY', 'SELL'):
        if parts[2] == 'MKT':
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
            print(ex.view_orders())
        elif cmd['cmd'] == 'QUOTE':
            print(ex.quote(cmd['symbol']))
        elif cmd['cmd'] == 'PLACE':
            ex.place_order(cmd)
        elif cmd['cmd'] == 'QUIT':
            break
