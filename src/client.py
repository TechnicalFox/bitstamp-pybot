"""
    Filename: client.py
    Author: Jim Craveiro <jim.craveiro@gmail.com>
    Date: 03/07/2019
    
    Client class for connection to bitstamp/pusher
"""

import json
import logging
import pusherclient

"""
    class used to control connection to bitstamp/pusher
"""
class Client():

    """
        init function sets up the connection to bitstamp/pusher
        params:
            recent_trades (RecentTrades) - in memory container of recent trades
            pusher_key (str) - key used to connect to bitstamp websocket api
                               (not to be confused with user api key and secret)
        returns:
            NoneType
    """
    def __init__(self, recent_trades, pusher_key):
        self.recent_trades = recent_trades
        self.logger = logging.getLogger('trades')
        self.client = pusherclient.Pusher(pusher_key)
        self.client.connection.bind('pusher:connection_established', self.on_connect)
        self.client.connect()

    """
        channel subscription function for pusher
        params:
            channel (str) - name of channel to subscribe to
            events (list) - list of dicts containing events and callbacks,
                            formatted like so:
                [{'event':'<EVENT_NAME>','callback':'<CALLBACK_NAME>'}]
                    event_name (str) - name of the event to listen for
                    callback_name (function) - function to call when event triggered
        returns:
            NoneType
    """
    def subscribe(self, channel, events):
        subscription = self.client.subscribe(channel)
        for item in events:
            subscription.bind(item['event'], item['callback'])

    """
        callback function that is called when connected to bitstamp/pusher
        params:
            data (json string) [unused] - contains socket id of connection
        returns:
            NoneType
    """
    def on_connect(self, data):
        self.subscribe('live_trades_xrpusd', [
            { 'event': 'trade',
              'callback': self.on_trade }
        ])

    """
        callback function that is called when a trade event is fired; store_trade
        is what actually handles 
        params:
            data (json string) - contains information on the trade that was executed,
                                 bitstamp's api docs can be found here: 
                                 https://www.bitstamp.net/websocket/
        returns:
            NoneType
    """
    def on_trade(self, data):
        self.logger.info(data)
        cur_trade = json.loads(data)
        self.recent_trades.store_trade(cur_trade)
