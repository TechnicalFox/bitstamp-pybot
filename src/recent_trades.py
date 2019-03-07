"""
    Filename: recent_trades.py
    Author: Jim Craveiro <jim.craveiro@gmail.com>
    Date: 03/07/2019

    RecentTrades class used to store recent trade history and calculate values 
"""

import time
import threading

CLEANUP_INTERVAL = 30

"""
    class used as an in-memory container for recent trades
"""
class RecentTrades():
    
    """
        init function sets up values and dict for recent trades, also starts the 
        cleanup thread to remove trades older than specified lifetime from recent 
        trades
        params:
            None
        returns:
            NoneType
    """
    def __init__(self):
        self.new_trade = False
        self.initial_value = False
        self.price_string  = '0'
        self.recent_trades = {}

        cleanup_thread = threading.Thread(target=self.remove_old_trades)
        cleanup_thread.daemon = True
        cleanup_thread.start()

    """
        function that initializes and adds a trade tracker for a specific lifetime of 
        trades (for example trades for the last 15 minutes, or last hour)
        params:
            name (str) - name of the tracker, usually just a nice string
                         representation of the lifetime
            lifetime (int) - the amount of time, in seconds, that you want the 
                             tracker to save trades for (for example trades for the 
                             last 15 minutes would have a lifetime of 900) anything 
                             older is removed by the cleanup thread
        returns:
            NoneType
    """
    def add_tracker(self, name, lifetime):
        self.recent_trades[name] = {
            'lifetime': lifetime,
            'trades':         [],
            'volume':        0.0,
            'price_volume':  0.0,
            'average_price': 0.0
        }

    """
        getter function for the price, as a string, of the most recent trade
        params:
            None
        returns:
            (string) - string representation of the most recent trade price
    """
    def price(self):
        return self.price_string

    """
        getter function for the lifetime of the specified tracker
        params:
            tracker (str) - string key (in recent_trades dict) for the tracker 
                            you want the int lifetime of
        returns:
            (int) - lifetime of the specified tracker
    """
    def lifetime(self, tracker):
        return self.recent_trades[tracker]['lifetime']

    """
        getter function that returns a list of all the added trackers' names
        params:
            None
        returns:
            (list) - list of strings that are the keys in the recent_trades dict
    """
    def trackers(self):
        return [key for key in self.recent_trades]

    """
        function that returns the recent trades for a specified tracker, or 
        appends/sets the trades for a specified tracker, depending on params
        params:
            tracker (str) - key for specified tracker in recent_trades dict
            trades (list, dict, NoneType) - defaults to None, list of trades to set 
                                            list to, or a trade dict to append to the 
                                            existing list
            append (bool) - boolean on whether or not to append the specified trades to
                            the tracker's existing trade list
        returns:
            (list) - returns the list of recent trades for the specified tracker only
                     if the trades param is None (default)
    """
    def trades(self, tracker, trades=None, append=False):
        if trades == None:
            return self.recent_trades[tracker]['trades']
        else:
            if append:
                self.recent_trades[tracker]['trades'].append(trades)
            else:
                self.recent_trades[tracker]['trades'] = trades
    
    """
        function to get and set the trade volume (total number of trades in a specific
        amount of time) for the specified tracker
        params:
            tracker (str) - key for specified tracker in recent_trades dict
            volume (float, NoneType) - defaults to None, float value to set the
                                       trade volume to in the specified tracker
        returns:
            (float) - returns a float of the trade volume for the specified tracker
                      only if no volume was specified (default)
    """
    def volume(self, tracker, volume=None):
        if volume == None:
            return self.recent_trades[tracker]['volume']
        else:
            self.recent_trades[tracker]['volume'] = volume

    """
        function to get and set the price volume (total amount of cashflow in a specific
        amount of time) for the specified tracker
        params:
            tracker (str) - key for specified tracker in recent_trades dict
            volume (float, NoneType) - defaults to None, float value to set the
                                       price volume to in the specified tracker
        returns:
            (float) - returns a float of the price volume for the specified tracker
                      only if no volume was specified (default)
    """
    def price_volume(self, tracker, volume=None):
        if volume == None:
            return self.recent_trades[tracker]['price_volume']
        else:
            self.recent_trades[tracker]['price_volume'] = volume

    """
        function to get and set the average price for the specified tracker
        params:
            tracker (str) - key for specified tracker in recent_trades dict
            price (float, NoneType) - defaults to None, float value to set the
                                      average price to in the specified tracker
        returns:
            (float) - returns a float of the average price for the specified tracker
                      only if no price was specified (default)
    """
    def average_price(self, tracker, price=None):
        if price == None:
            return self.recent_trades[tracker]['average_price']
        else:
            self.recent_trades[tracker]['average_price'] = price
    
    """
        function for the cleanup thread to remove old trades from each tracker's
        trade list. runs on an infinite loop that creates a new list made from only
        trades that are within the specified lifetime, and sets the tracker's trade list
        to this new list. does this for each tracker, then sleeps for CLEANUP_INTERVAL
        number of seconds
        params:
            None
        returns:
            NoneType
    """
    # TODO: make this less inefficient (only one list of trades for example, and
    #       removing trades from a master list that fall outside of all trackers
    def remove_old_trades(self):
        while True:
            cur_time = time.time()
            for tracker in self.trackers():
                num_trades = len(self.trades(tracker))
                
                # sets the trades in the tracker to a new list of trades that omits
                # any trades that fall outside of the lifetime
                self.trades(tracker,
                    [trade for trade in self.trades(tracker)
                        if int(trade['timestamp']) > cur_time - self.lifetime(tracker)])
                
                if len(self.trades(tracker)) < num_trades: self.new_trade = True
            time.sleep(CLEANUP_INTERVAL)

    """
        function that recalculates and sets different metrics only when there is a new
        trade that hasn't yet been calculated. called by the main program loop
        params:
            None
        returns:
            NoneType
    """
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

    """
        function that stores a new trade in each tracker's list, and sets a flag to
        run calculations
        params:
            trade (dict) - trade object converted from a json object sent from
                           bitstamp's api, documentation can be found here:
                           https://www.bitstamp.net/websocket/
        returns:
            NoneType
    """
    def store_trade(self, trade):
        self.initial_value = True
        self.new_trade = True
        self.price_string = trade['price_str']
        for tracker in self.trackers():
            self.trades(tracker, trade, True)

