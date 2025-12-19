import decimal
from models import MONEY_STEP, Side, OrderType
from exchange import Exchange


def parse_money(token: str):
    s = token.strip()
    if s.startswith('$'):
        s = s[1:]

    value = decimal.Decimal(s)
    return value.quantize(MONEY_STEP, rounding=decimal.ROUND_HALF_UP)


def parse_action(line: str):
    parts = line.split()
    if not parts:
        return None

    if len(parts) >= 2 and parts[0] == 'VIEW' and parts[1] == 'ORDERS':
        return {'cmd': 'VIEW_ORDERS'}
    elif parts[0] == 'QUOTE':
        if len(parts) != 2:
            raise ValueError('Формат команды: QUOTE <SYMBOL>')
        return {'cmd': 'QUOTE', 'symbol': parts[1]}
    elif parts[0] == 'QUIT':
        return {'cmd': 'QUIT'}
    elif parts[0] in (Side.BUY, Side.SELL):
        if len(parts) < 3:
            raise ValueError(
                f'Неполная команда {parts[0]}.Ожидается: {parts[0]} <SYMBOL> <TYPE> ...')
        if parts[2] == OrderType.MARKET:
            if len(parts) < 4:
                raise ValueError('Для MARKET ордера нужно указать количество.')
            price = None
            qty = int(parts[3])
        elif parts[2] == OrderType.LIMIT:
            if len(parts) < 5:
                raise ValueError('Для LIMIT ордера нужны цена и количество.')
            price = parse_money(parts[3])
            qty = int(parts[4])
        else:
            raise ValueError(f'Неизвестный тип ордера: {parts[2]}')
        return {'cmd': 'PLACE', 'side': parts[0], 'symbol': parts[1],
                'type': parts[2], 'price': price, 'qty': qty}
    else:
        raise ValueError(f"Неизвестная команда: {parts[0]}")


def main():
    ex = Exchange()

    while True:
        try:
            line = input()
            cmd = parse_action(line)

            if cmd is None:
                continue

            if cmd['cmd'] == 'VIEW_ORDERS':
                ex.view_orders()
            elif cmd['cmd'] == 'QUOTE':
                print(ex.quote(cmd['symbol']))
            elif cmd['cmd'] == 'PLACE':
                ex.place_order(cmd)
            elif cmd['cmd'] == 'QUIT':
                break
        except (EOFError, KeyboardInterrupt):
            print('\nВыход из программы.')
            break
        except ValueError as e:
            print(f'Ошибка ввода: {e}')
        except Exception as e:
            print(f'Произошла ошибка: {e}')


if __name__ == '__main__':
    main()
