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
import requests
import pusherclient

CREDENTIALS         = {}
BITSTAMP_PUSHER_KEY = 'de504dc5763aeef9ff52'
PUSHOVER_URL        = 'https://api.pushover.net/1/messages.json'
PUSHOVER_RETRIES    = 2
PUSHOVER_PRIORITY   = {'silent'   :'-2',
                       'low'      :'-1',
                       'default'  : '0',
                       'high'     : '1',
                       'emergency': '2'}

""" Client
    class used to control websocket/pusher connection to bitstamp
"""
class Client():

    """ __init__
        init function sets up the connection to bitstamp
    """
    def __init__(self):
        self.last_trade = '{"price_str":"0"}';
        self.logger = logging.getLogger('trades')
        self.client = pusherclient.Pusher(BITSTAMP_PUSHER_KEY)
        self.client.connection.bind('pusher:connection_established', self.on_connect)
        self.client.connect()

    """ subscribe
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
        returns:
            (string) - price of the most recent trade
    """
    def cur_price(self):
        data = json.loads(self.last_trade)
        return data['price_str']

""" push_notification
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
    if(priority == 'emergency'):
        payload['retry']  = 120
        payload['expire'] = 600
    
    response = requests.post(PUSHOVER_URL, data=payload)
    if(response.status_code >= 400):
        try_fraction = str((retries - 3) * -1) + '/' + str(PUSHOVER_RETRIES + 1)
        logging.getLogger('errors').error('push notification failed on try ' + try_fraction +
                                          ' with status code: ' + str(response.status_code) +
                                          '\n    error text: ' + response.text + '\n')
        if(retries > 0): 
            time.sleep(1)
            push_notification(message, title, priority, retries-1)

""" make_logger
    function that creates a very basic logger that appends to a file
    params:
        name (string) - name of the logger
"""
def make_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.FileHandler(name + '.log', mode='a'))

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
    function that sets up the signal handler for sigint, 
    reads in credentials, then sets up loggers
"""
def init():
    signal.signal(signal.SIGINT, on_sigint)
    
    global CREDENTIALS
    with open('credentials.json', 'r') as file:
        CREDENTIALS = json.loads(file.read())
    
    make_logger('errors')
    make_logger('trades')

""" main
    function where main loop is held, calls init and creates the client
"""
def main():
    init()
    client = Client()
    
    while True:    
        sys.stdout.write('\rCurrent Price: ' + client.cur_price())
        sys.stdout.flush()
        time.sleep(1)

if __name__ == '__main__': main()
