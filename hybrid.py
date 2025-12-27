import random
import time
import heapq
import numpy as np
import pandas as pd

import mplfinance as mpf
import matplotlib.pyplot as plt
import time
from datetime import datetime

def ticks_to_ohlc(ticks, start_time, freq="1s"):
    """
    ticks: list of trade prices
    """
    times = pd.date_range(start=start_time, periods=len(ticks), freq="100ms")
    s = pd.Series(ticks, index=times)

    ohlc = s.resample(freq).ohlc()
    return ohlc.dropna()

class OrderBook:
    def __init__(self):
        self.bids = []  # max heap via negative prices
        self.asks = []  # min heap

    def add_limit(self, side, price, qty):
        if side == "buy":
            heapq.heappush(self.bids, (-price, qty))
        else:
            heapq.heappush(self.asks, (price, qty))

    def market_order(self, side):
        if side == "buy" and self.asks:
            price, qty = heapq.heappop(self.asks)
            return price
        elif side == "sell" and self.bids:
            price, qty = heapq.heappop(self.bids)
            return -price
        return None

class HybridTrader:
    def __init__(self, spread=0.01, p_market = 0.2):
        self.spread = spread
        self.p_market = p_market  # probability of market order

    def act(self, book, last_price):
        if random.random() < self.p_market:
            # Market order
            side = random.choice(["buy", "sell"])
            return book.market_order(side)
        else:
            # Limit order
            side = random.choice(["buy", "sell"])
            price = last_price * (1 + random.uniform(-self.spread, self.spread))
            qty = random.randint(1, 10)
            book.add_limit(side, price, qty)
            return None


def run_market_hybrid(
    start_price=100,
    n_traders=30,
    p_market=0.2,
    ticks_per_candle=10,
    redraw_every=5
):
    MAX_CANDLES = 100
    paused = False
    SLEEP = 0.05

    def on_key(event):
        nonlocal paused, MAX_CANDLES, SLEEP

        if event.key == ' ':
            paused = not paused
            print("Paused" if paused else "Resumed")

        elif event.key == '+':
            MAX_CANDLES = max(20, MAX_CANDLES - 20)
            print(f"Zoom in: {MAX_CANDLES}")

        elif event.key == '-':
            MAX_CANDLES += 20
            print(f"Zoom out: {MAX_CANDLES}")

        elif event.key == 'e':
            SLEEP = max(0.01, SLEEP - 0.01)
            print(f"Speeding up: {SLEEP}")

        elif event.key == 'r':
            SLEEP += 0.01
            print(f"Slowing down: {SLEEP}")
    

    book = OrderBook()
    traders = [HybridTrader(p_market=p_market) for _ in range(n_traders)]

    last_price = start_price
    ticks = [last_price]
    tick_count = 0

    start_time = datetime.now()

    plt.ion()
    fig = mpf.figure(style='yahoo', figsize=(10, 6))
    ax = fig.add_subplot(111)
    fig.canvas.mpl_connect('key_press_event', on_key)

    try:
        while True:
            if not paused:
                for trader in traders:
                    trade_price = trader.act(book, last_price)

                    if trade_price is not None:
                        last_price = trade_price
                        ticks.append(last_price)
                        tick_count += 1


            if tick_count >= ticks_per_candle and tick_count % redraw_every == 0:
                ohlc = ticks_to_ohlc(ticks, start_time)
                
                ohlc = ohlc.iloc[-MAX_CANDLES:]

                ax.clear()
                mpf.plot(
                    ohlc,
                    ax=ax,
                    type='candle',
                    style='yahoo',
                    show_nontrading=True
                )
                plt.pause(SLEEP)

            # ticks = ticks[-5000:]
            # time.sleep(SLEEP)

    except KeyboardInterrupt:
        plt.ioff()
        plt.show()

run_market_hybrid(
    start_price=100,
    n_traders=30,
    p_market=0.8,
    ticks_per_candle=10,
    redraw_every=5
)
