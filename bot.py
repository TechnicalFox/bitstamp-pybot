#!/usr/bin/env python3

"""
    Filename: bot.py
    Author: Jim Craveiro <jim.craveiro@gmail.com>
    Date: 1/03/2018

    Python 3 Bitstamp trading bot.
"""

import sys
import time
import json
import signal
import curses
import logging
import requests
import threading
import pusherclient

ONE_HOUR            = 3600
FIFTEEN_MIN         = 900
CLEANUP_INTERVAL    = 30
CREDENTIALS         = {}
BITSTAMP_PUSHER_KEY = 'de504dc5763aeef9ff52'
PUSHOVER_URL        = 'https://api.pushover.net/1/messages.json'
PUSHOVER_RETRIES    = 2
PUSHOVER_PRIORITY   = {'silent'   :'-2',
                       'low'      :'-1',
                       'default'  : '0',
                       'high'     : '1',
                       'emergency': '2'}
PUSHOVER_EMERGENCY_RETRY  = 120
PUSHOVER_EMERGENCY_EXPIRE = 600

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
                self.trades(tracker,
                    [trade for trade in self.trades(tracker) if int(trade['timestamp']) > cur_time - self.age(tracker)]
                )
            logging.getLogger('debug').debug('removing old trades')
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

"""
    class used to control connection to bitstamp/pusher
"""
class Client():

    """
        init function sets up the connection to bitstamp/pusher
    """
    def __init__(self, recent_trades):
        self.recent_trades = recent_trades
        self.logger = logging.getLogger('trades')
        self.client = pusherclient.Pusher(BITSTAMP_PUSHER_KEY)
        self.client.connection.bind('pusher:connection_established', self.on_connect)
        self.client.connect()

    """
        channel subscription function for pusher
        params:
            channel (string) - name of channel to subscribe to
            events (list) - list of events and callbacks formatted like so:
                [{'event':'event_name','callback':callback_name}]
                event_name (string) - name of the event to listen for
                callback_name (function) - function to call when event triggered
    """
    def subscribe(self, channel, events):
        subscription = self.client.subscribe(channel)
        for item in events:
            subscription.bind(item['event'], item['callback'])
    
    """
        callback function that is called when connected to bitstamp/pusher
        params:
            data (json string) [unused] - contains socket id of connection
    """
    def on_connect(self, data):
        self.subscribe('live_trades_xrpusd', [
            { 'event': 'trade',
              'callback': self.on_trade }
        ])
    
    """
        callback function that is called when a trade event is fired
        sets the current price, as well as storing trades and calculating the trade volume
        params:
            data (json string) - contains information on the trade that was executed,
                bitstamp's api docs can be found here: https://www.bitstamp.net/websocket/
    """
    #TODO: update comments here
    def on_trade(self, data):
        self.logger.info(data)
        cur_trade = json.loads(data)
        self.recent_trades.store_trade(cur_trade)
        
"""
    function that sends a push notification using the Pushover API, requests,
    and credentials provided in the credentials.json file. 
    Pushover documentation can be found here: https://pushover.net/api
    params:
        message (string) - the push notification message body
        title (string) - the title of the push notification,
                         defaults to empty string which lets Pushover use its default
        priority (string) - priority string that corresponds to Pushover priority levels
                            using PUSHOVER_PRIORITY to convert, defaults to 'default'
        retries (int) - the number of retries (total attempts - 1) to attempt if the post
                        request to the Pushover API fails, defaults to PUSHOVER_RETRIES constant
"""
def push_notification(message, title='', priority='default', retries=PUSHOVER_RETRIES):
    payload = {
        'token'   : CREDENTIALS['pushover']['token'],
        'user'    : CREDENTIALS['pushover']['user'],
        'message' : message,
        'title'   : title,
        'priority': PUSHOVER_PRIORITY[priority]
    }
    if priority == 'emergency':
        payload['retry']  = PUSHOVER_EMERGENCY_RETRY
        payload['expire'] = PUSHOVER_EMERGENCY_EXPIRE
    
    response = requests.post(PUSHOVER_URL, data=payload)
    if response.status_code >= 400:
        logging.getLogger('debug').error('push notification failed on try {}/{} with status code: {}\n    error text: {}\n'.format(
            (retries - 3) * -1, PUSHOVER_RETRIES + 1, response.status_code, response.text
        ))
        if retries > 0: 
            time.sleep(1)
            push_notification(message, title, priority, retries-1)

"""
    function that creates a very basic logger that appends to a file
    params:
        name (string) - name of the logger
"""
def make_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.FileHandler('{}.log'.format(name), mode='a'))

"""
    function that calculates the uptime of the program and returns an uptime string
    params:
        start_time (float) - time recorded at start of program
    return:
        (string) - string containing calculated days, hours, minutes, and seconds of uptime
"""
def calc_uptime(start_time):
    seconds = int(time.time() - start_time)
    minutes = int(seconds / 60)
    hours   = int(minutes / 60)
    days    = int(hours   / 24)
    
    seconds = str(seconds - (minutes * 60)).zfill(2)
    minutes = str(minutes - (hours   * 60)).zfill(2)
    hours   = str(hours   - (days    * 24)).zfill(2)

    return '{} days, {}:{}:{}'.format(days, hours, minutes, seconds)

"""
    signal handler for sigint; exits program
    params:
        signum (int) [unused] - number representing the signal being passed to handler
        frame (object) [unused] - stack frame interrupted by signal
"""
def on_sigint(signum, frame):
    sys.exit()

def update_display(stdscr, recent_trades, start_time):
    cursor_pos = 0
    stdscr.addstr(cursor_pos, 0, 'Bitstamp Pybot - uptime: {}'.format(calc_uptime(start_time))); cursor_pos+=2
    stdscr.addstr(cursor_pos, 0, 'Current Price: ${} USD'.format(recent_trades.price())); cursor_pos+=2
    
    for tracker in recent_trades.trackers():
        stdscr.addstr(cursor_pos, 0, '{} Trade Volume:  {:.8f} XRP'.format(tracker, recent_trades.volume(tracker))); cursor_pos+=1
        stdscr.addstr(cursor_pos, 4, 'Price Volume:    ${:.5f} USD'.format(recent_trades.price_volume(tracker))); cursor_pos+=1
        stdscr.addstr(cursor_pos, 4, 'Average Price:   ${:.5f} USD'.format(recent_trades.average_price(tracker))); cursor_pos+=2
    
    stdscr.refresh()

"""
    function that sets up the signal handler for sigint, 
    reads in credentials, and sets up loggers
"""
#TODO: update comments
def init():
    curses.curs_set(0)
    signal.signal(signal.SIGINT, on_sigint)
    
    global CREDENTIALS
    with open('credentials.json', 'r') as file:
        CREDENTIALS = json.loads(file.read())
    
    make_logger('debug')
    make_logger('trades')
    
    recent_trades = RecentTrades()
    recent_trades.add_tracker('15 Min', FIFTEEN_MIN)
    recent_trades.add_tracker('1 Hour', ONE_HOUR)
    return recent_trades    

"""
    function where main loop is held, calls init and creates the client
    wrapped in curses wrapper for output
"""
def main(stdscr):
    start_time = time.time()
    recent_trades = init()
    client = Client(recent_trades)
    
    while True:
        recent_trades.run_calculations()
        update_display(stdscr, recent_trades, start_time)
        time.sleep(1)

if __name__ == '__main__': curses.wrapper(main)
