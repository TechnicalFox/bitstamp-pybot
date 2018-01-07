"""
    Filename: client.py
    Author: Jim Craveiro <jim.craveiro@gmail.com>
    Date: 1/07/2018
    
    Client class for connection to bitstamp/pusher
"""

import json
import logging
import pusherclient

BITSTAMP_PUSHER_KEY = 'de504dc5763aeef9ff52'

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
