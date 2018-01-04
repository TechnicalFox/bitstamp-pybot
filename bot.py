#!/usr/bin/env python3
""" bot.py
    Author: Jim Craveiro <jim.craveiro@gmail.com>
    Date: 1/03/2018

    Python 3 Bitstamp trading bot.
"""

import sys
import time
import json
import signal
import logging
import pusherclient

PUSHER_KEY = 'de504dc5763aeef9ff52'

""" Client
    class used to control websocket/pusher connection to bitstamp
"""
class Client():

    """ __init__
        init function sets up the connection to bitstamp
        params:
            logger (object) - from logging library
    """
    def __init__(self, logger):
        self.last_trade = '{"price_str":"0"}';
        self.logger = logger
        self.client = pusherclient.Pusher(PUSHER_KEY)
        self.client.connection.bind('pusher:connection_established', self.on_connect)
        self.client.connect()

    """ subscription
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
    
    """ on_connect
        callback function that is called when connected to bitstamp/pusher
        params:
            data (json string) [unused] - contains socket id of connection
    """
    def on_connect(self, data):
        self.subscribe('live_trades_xrpusd', [
            { 'event': 'trade',
              'callback': self.on_trade }
        ])
    
    """ on_trade
        callback function that is called when a trade event is fired
        params:
            data (json string) - contains information on the trade that was executed,
                bitstamp's api docs can be found here: https://www.bitstamp.net/websocket/
    """
    def on_trade(self, data):
        self.logger.info(str(data))
        self.last_trade = str(data)

    """ cur_price
        parses the last (most recent) trade and returns the price string
    """
    def cur_price(self):
        data = json.loads(self.last_trade)
        return data['price_str']

""" on_sigint
    signal handler for sigint; exits program
    params:
        signum (int) [unused] - number representing the signal being passed to handler
        frame (object) [unused] - stack frame interrupted by signal
"""
def on_sigint(signum, frame):
    print('\nExiting...')
    sys.exit()

""" init
    function that sets up the signal handler for sigint and sets up, then returns, the logger
"""
def init():
    signal.signal(signal.SIGINT, on_sigint)
    
    logger = logging.getLogger('trade_log')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.FileHandler('trades.log', mode='a'))
    return logger

""" main
    function where main loop is held, calls init and creates the client
"""
def main():
    logger = init()
    client = Client(logger)
    
    while True:    
        sys.stdout.write('\rCurrent Price: ' + client.cur_price())
        sys.stdout.flush()
        time.sleep(1)

if __name__ == '__main__': main()
