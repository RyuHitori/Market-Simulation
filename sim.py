import threading
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random
import time
import heapq
import numpy as np
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
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

class MarketSimulator:
    def __init__(self, ax):
        self.ax = ax
        self.running = False

    def start(
        self,
        start_price,
        n_traders,
        p_market,
        sleep,
        ticks_per_candle,
        redraw_every
    ):
        self.running = True

        self.book = OrderBook()
        self.traders = [HybridTrader(p_market=p_market) for _ in range(n_traders)]

        self.last_price = start_price
        self.ticks = [start_price]
        self.tick_count = 0
        self.start_time = datetime.now()

        self.MAX_CANDLES = 100

        while self.running:
            for trader in self.traders:
                trade_price = trader.act(self.book, self.last_price)
                if trade_price:
                    self.last_price = trade_price
                    self.ticks.append(self.last_price)
                    self.tick_count += 1

            if self.tick_count >= ticks_per_candle and self.tick_count % redraw_every == 0:
                ohlc = ticks_to_ohlc(self.ticks, self.start_time)
                ohlc = ohlc.iloc[-self.MAX_CANDLES:]

                self.ax.clear()
                mpf.plot(
                    ohlc,
                    ax=self.ax,
                    type='candle',
                    style='yahoo',
                    show_nontrading=True
                )

                self.ax.figure.canvas.draw_idle()

            time.sleep(max(sleep, 0.001))

    def stop(self):
        self.running = False
    
    def zoom_in(self):
        self.MAX_CANDLES = max(20, self.MAX_CANDLES - 20)

    def zoom_out(self):
        self.MAX_CANDLES += 20
    
    def reset(self, start_price):
        self.book = OrderBook()
        self.last_price = start_price
        self.ticks = [start_price]
        self.tick_count = 0
        self.start_time = datetime.now()

        self.ax.clear()
        self.ax.figure.canvas.draw_idle()



root = tk.Tk()
root.title("Market Simulator")
controls = ttk.Frame(root)
controls.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

def labeled_entry(label, default):
    ttk.Label(controls, text=label).pack(anchor="w")
    var = tk.StringVar(value=str(default))
    entry = ttk.Entry(controls, textvariable=var)
    entry.pack(fill="x")
    return var

def labeled_slider(parent, label, from_, to_, resolution, default):
    frame = ttk.Frame(parent)
    frame.pack(fill="x", pady=5)

    # Top label
    ttk.Label(frame, text=label).pack(anchor="w")

    var = tk.DoubleVar(value=default)

    slider = ttk.Scale(
        frame,
        from_=from_,
        to=to_,
        orient="horizontal",
        variable=var
    )
    slider.pack(fill="x")

    # Value label under slider
    value_label = ttk.Label(frame, text=f"{default:.2f}")
    value_label.pack(anchor="e")

    # Update label when slider moves
    def update_label(*_):
        value_label.config(text=f"{var.get():.2f}")

    var.trace_add("write", update_label)

    return var


start_price_var = labeled_entry("Start Price", 100)
n_traders_var   = labeled_entry("Number of Traders", 30)
p_market_var    = labeled_slider(controls, "Market Order Probability", 0, 0.99, 0.01, 0.8)
speed_var = labeled_entry("Sleep", 0.01)
ticks_per_candle_var = labeled_entry("Ticks per Candle", 10)
redraw_every_var = labeled_entry("Redraw Every", 5)

fig = mpf.figure(style='yahoo', figsize=(8, 6))
ax = fig.add_subplot(111)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)


simulator = MarketSimulator(ax)
sim_thread = None

def start_sim():
    global sim_thread

    if sim_thread and sim_thread.is_alive():
        return

    sim_thread = threading.Thread(
        target=simulator.start,
        args=(
            float(start_price_var.get()),
            int(n_traders_var.get()),
            float(p_market_var.get()),
            float(speed_var.get()),
            int(ticks_per_candle_var.get()),
            int(redraw_every_var.get())
        ),
        daemon=True
    )
    sim_thread.start()

def stop_sim():
    simulator.stop()

ttk.Button(controls, text="Start", command=start_sim).pack(fill="x", pady=5)
ttk.Button(controls, text="Stop", command=stop_sim).pack(fill="x")
ttk.Button(controls, text="Zoom In", command=simulator.zoom_in).pack(fill="x")
ttk.Button(controls, text="Zoom Out", command=simulator.zoom_out).pack(fill="x")

def reset_sim():
    simulator.reset(float(start_price_var.get()))

ttk.Button(controls, text="Reset", command=reset_sim).pack(fill="x", pady=10)

root.mainloop()
