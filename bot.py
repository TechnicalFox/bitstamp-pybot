#!/usr/bin/env python3

"""
    Filename: bot.py
    Author: Jim Craveiro <jim.craveiro@gmail.com>
    Date: 03/07/2019

    Python 3 Bitstamp trading bot
"""

import os
import sys
import time
import json
import signal
import curses
import logging
import requests
from src.client import Client
from src.recent_trades import RecentTrades

LOG_PATH            = './log/'
ONE_HOUR            = 3600
FIFTEEN_MIN         = 900
CREDENTIALS         = {}
RETRY_INTERVAL      = 30
PUSHOVER_URL        = 'https://api.pushover.net/1/messages.json'
PUSHOVER_RETRIES    = 5
PUSHOVER_PRIORITY   = {'silent'   :'-2',
                       'low'      :'-1',
                       'default'  : '0',
                       'high'     : '1',
                       'emergency': '2'}
PUSHOVER_ERROR = 'push notification failed on try {}/{} with status code: {}\n    error text: {}\n'

"""
    function that sends a push notification using the Pushover API, requests,
    and credentials provided in the credentials.json file. 
    Pushover documentation can be found here: https://pushover.net/api
    params:
        message (str) - the push notification message body
        title (str) - the title of the push notification,
                      defaults to empty string which lets Pushover use its default
        priority (str) - priority string that corresponds to Pushover priority levels
                         using PUSHOVER_PRIORITY to convert, defaults to 'default'
        retries (int) - the number of retries to attempt if the post request to the 
                        Pushover API fails, defaults to PUSHOVER_RETRIES constant
    returns:
        NoneType
"""
def push_notification(message, title='', priority='default', retries=PUSHOVER_RETRIES):
    payload = {
        'token'   : CREDENTIALS['pushover']['token'],
        'user'    : CREDENTIALS['pushover']['user'],
        'message' : message,
        'title'   : title,
        'priority': PUSHOVER_PRIORITY[priority]
    }
    
    response = requests.post(PUSHOVER_URL, data=payload)
    if response.status_code >= 400:
        logging.getLogger('debug').error(PUSHOVER_ERROR.format(
            (PUSHOVER_RETRIES - retries + 1), PUSHOVER_RETRIES, 
            response.status_code, response.text))
        if retries > 1: 
            time.sleep(RETRY_INTERVAL)
            push_notification(message, title, priority, retries - 1)

"""
    function that creates a very basic logger that appends to a file
    params:
        name (str) - name of the logger
    returns:
        NoneType
"""
def make_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.FileHandler('{}{}.log'.format(
        LOG_PATH, name), mode='a'))

"""
    function that calculates the uptime of the program and returns an uptime string
    params:
        start_time (float) - time recorded at start of program
    returns:
        (str) - string containing calculated days, hours, minutes, 
                and seconds of uptime
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
        signum (int) [unused] - number representing the signal being 
                                passed to handler
        frame (object) [unused] - stack frame interrupted by signal
    returns:
        NoneType
"""
def on_sigint(signum, frame):
    sys.exit()

"""
    function that updates the curses display with most recent data
    params:
        stdscr (Window) - curses screen to add text to
        recent_trades (RecentTrades) - in memory container of recent trades
        start_time (float) - time that program was initialized
    returns:
        NoneType
"""
def update_display(stdscr, recent_trades, start_time):
    cursor_pos = 0
    stdscr.addstr(cursor_pos, 0, 'Bitstamp Pybot - uptime: {}'.format(
        calc_uptime(start_time)))
    cursor_pos += 2
    stdscr.addstr(cursor_pos, 0, 'Current Price: ${} USD'.format(
        recent_trades.price()))
    cursor_pos += 2
    
    for tracker in recent_trades.trackers():
        stdscr.addstr(cursor_pos, 0, '{} Trade Volume:  {:.8f} XRP'.format(
            tracker, recent_trades.volume(tracker)))
        cursor_pos += 1
        stdscr.addstr(cursor_pos, 4, 'Price Volume:    ${:.5f} USD'.format(
            recent_trades.price_volume(tracker)))
        cursor_pos += 1
        stdscr.addstr(cursor_pos, 4, 'Average Price:   ${:.5f} USD'.format(
            recent_trades.average_price(tracker)))
        cursor_pos += 2
    
    stdscr.refresh()

"""
    function to read in credentials from a json file for bitstamp & pushover
    and put it in a global dict
    format:
        {
          "bitstamp":{
            "key":"<BITSTAMP_API_KEY>",
            "secret":"<BITSTAMP_API_SECRET>",
            "pusher":"<BITSTAMP_WEBSOCKET_KEY>"
          },
          "pushover":{
            "token":"<PUSHOVER_API_TOKEN>",
            "user":"<PUSHOVER_APU_USER>"
          }
        }
    params:
        None
    returns:
        NoneType
"""
def read_credentials():
    global CREDENTIALS
    with open('credentials.json', 'r') as file:
        CREDENTIALS = json.loads(file.read())

"""
    function that sets up the signal handler for sigint, 
    reads in credentials, and sets up loggers
    params:
        None
    returns:
        start_time (float) - time that program was initialized
        recent_trades (RecentTrades) - in memory container of recent trades
"""
def init():
    signal.signal(signal.SIGINT, on_sigint)
    curses.curs_set(0)
    start_time = time.time()
    read_credentials()
    
    if not os.path.exists(LOG_PATH): os.mkdir(LOG_PATH)
    make_logger('debug')
    make_logger('trades')
    
    recent_trades = RecentTrades()
    recent_trades.add_tracker('15 Min', FIFTEEN_MIN)
    recent_trades.add_tracker('1 Hour', ONE_HOUR)
    return start_time, recent_trades    

"""
    function where main loop is held, calls init and creates the client
    wrapped in curses wrapper for output
    params:
        stdscr (Window) - curses screen to add text to
    returns:
        NoneType
"""
def main(stdscr):
    start_time, recent_trades = init()
    client = Client(recent_trades, CREDENTIALS['bitstamp']['pusher'])
    start_notification = False
    
    while True:
        recent_trades.run_calculations()
        update_display(stdscr, recent_trades, start_time)
        
        if start_notification and recent_trades.initial_value:
            push_notification('Start time: {}\nPrice: {}'.format(
                time.strftime('%m/%d/%y - %I:%M %p', time.localtime(start_time)), 
                recent_trades.price_string), 'Bot Started')
        
        time.sleep(1)

# run main with curses wrapper
if __name__ == '__main__': curses.wrapper(main)
