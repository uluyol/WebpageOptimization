import simplejson as json
import websocket
import threading

from utils import navigation_utils

from time import sleep

METHOD = 'method'
PARAMS = 'params'
REQUEST_ID = 'requestId'
TIMESTAMP = 'timestamp'

class ChromeRDPWithoutTracing(object):

    def __init__(self, url, target_url):
        self.url = target_url
        self.debugging_url = url
        self.ws = websocket.WebSocket()
        self.ws.connect(self.debugging_url)

    def navigate_to_page(self, url):
        navigation_utils.navigate_to_page(self.ws, url)
        result = self.ws.recv()
        start_time, end_time = navigation_utils.get_start_end_time_with_socket(self.ws)
        navigation_utils.clear_cache(self.ws)
        return start_time, end_time

    def __del__(self):
        self.ws.close()