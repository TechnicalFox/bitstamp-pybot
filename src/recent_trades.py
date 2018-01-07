"""
    Filename: recent_trades.py
    Author: Jim Craveiro <jim.craveiro@gmail.com>
    Date: 1/07/2018

    RecentTrades class used to store recent trade history and calculate values 
"""

import time
import threading

CLEANUP_INTERVAL = 30

"""
    class used as an in-memory container for recent trades
"""
class RecentTrades():
    #TODO: comment this class and its functions
    def __init__(self):
        self.new_trade = False
        self.price_string  = '0'
        self.recent_trades = {}

        cleanup_thread = threading.Thread(target=self.remove_old_trades)
        cleanup_thread.daemon = True
        cleanup_thread.start()

    def add_tracker(self, name, age):
        self.recent_trades[name] = {
            'age':           age,
            'trades':         [],
            'volume':        0.0,
            'price_volume':  0.0,
            'average_price': 0.0
        }

    def price(self):
        return self.price_string

    def age(self, name):
        return self.recent_trades[name]['age']

    def trackers(self):
        return [key for key in self.recent_trades]

    def trades(self, name, trades=None, append=False):
        if trades == None:
            return self.recent_trades[name]['trades']
        else:
            if append:
                self.recent_trades[name]['trades'].append(trades)
            else:
                self.recent_trades[name]['trades'] = trades
    
    def volume(self, name, volume=None):
        if volume == None:
            return self.recent_trades[name]['volume']
        else:
            self.recent_trades[name]['volume'] = volume

    def price_volume(self, name, volume=None):
        if volume == None:
            return self.recent_trades[name]['price_volume']
        else:
            self.recent_trades[name]['price_volume'] = volume

    def average_price(self, name, price=None):
        if price == None:
            return self.recent_trades[name]['average_price']
        else:
            self.recent_trades[name]['average_price'] = price

    def remove_old_trades(self):
        while True:
            cur_time = time.time()
            for tracker in self.trackers():
                num_trades = len(self.trades(tracker))
                self.trades(tracker,
                    [trade for trade in self.trades(tracker) if int(trade['timestamp']) > cur_time - self.age(tracker)]
                )
                if len(self.trades(tracker)) > num_trades: self.new_trade = True
            time.sleep(CLEANUP_INTERVAL)

    def run_calculations(self):
        if self.new_trade:
            for tracker in self.trackers():
                temp_volume    = 0.0
                temp_price_vol = 0.0
                temp_avg_price = 0.0
                temp_avg_count = 0
                for trade in self.trades(tracker):
                    temp_volume    += trade['amount']
                    temp_price_vol += trade['amount'] * trade['price']
                    temp_avg_price += trade['price']
                    temp_avg_count += 1

                temp_avg_price /= temp_avg_count
                self.volume(tracker, temp_volume)
                self.price_volume(tracker, temp_price_vol)
                self.average_price(tracker, temp_avg_price)
                self.new_trade = False

    def store_trade(self, trade):
        self.new_trade = True
        self.price_string = trade['price_str']
        for tracker in self.trackers():
            self.trades(tracker, trade, True)

