#!/home/vaspol/Research/MobileWebOptimization/scripts/venv/bin/python
from argparse import ArgumentParser
from ConfigParser import ConfigParser
from PageLoadException import PageLoadException

import common_module
import paramiko
import os
import signal
import subprocess
import requests
import time

from time import sleep
from utils import replay_config_utils
from utils import chrome_utils

WAIT = 2
TIMEOUT = 3 * 60

def main(config_filename, pages, iterations, device_name, mode, output_dir):
    signal.signal(signal.SIGALRM, timeout_handler) # Setup the timeout handler
    device_info = common_module.get_device_config(device_name) # Get the information about the device.
    common_module.initialize_browser(device_info) # Start the browser
    replay_configurations = replay_config_utils.get_page_replay_config(config_filename)
    current_time = time.time()
    if args.time is not None:
        # For replay mode.
        current_time = args.time

    for page in pages:
        print 'Page: ' + page
        start_proxy(mode, page, current_time, replay_configurations)
        print 'Started Proxy'
        # Load the page.
        returned_page = load_one_website(page, iterations, output_dir, device_info)
        if returned_page is not None:
            # There was an exception
            pages.append(returned_page)
            common_module.initialize_browser(device_info) # Restart the browser
        stop_proxy(mode, replay_configurations)
        print 'Stopped Proxy'
        sleep(5) # Default shutdown wait for squid
    done(replay_configurations)

def done(replay_configurations):
    start_proxy_url = 'http://{0}:{1}/done'.format( \
            replay_configurations[replay_config_utils.SERVER_HOSTNAME], \
            replay_configurations[replay_config_utils.SERVER_PORT])
    result = requests.get(start_proxy_url)
    print 'Done'

def start_proxy(mode, page, time, replay_configurations):
    '''
    Starts the proxy
    '''
    # proxy_started = check_proxy_running(replay_configurations, mode)
    proxy_started = False
    # Ensure that the proxy has started before start loading the page
    while not proxy_started:
        if mode == 'record':
            server_mode = 'start_recording'
        elif mode == 'replay':
            server_mode = 'start_proxy'

        start_proxy_url = 'http://{0}:{1}/{2}?page={3}&time={4}'.format( \
                replay_configurations[replay_config_utils.SERVER_HOSTNAME], \
                replay_configurations[replay_config_utils.SERVER_PORT], \
                server_mode, page, time)
        result = requests.get(start_proxy_url)
        # proxy_started = result.status_code == 200 and result.text.strip() == 'Proxy Started' \
        #         and check_proxy_running(replay_configurations, mode)
        proxy_started = result.status_code == 200 and result.text.strip() == 'Proxy Started'
        print 'request result: ' + result.text
        if proxy_started:
            return proxy_started
        sleep(1) # Have a 1 second interval between iterations

def stop_proxy(mode, replay_configurations):
    '''
    Stops the proxy
    '''
    if mode == 'record':
        server_mode = 'stop_recording'
    elif mode == 'replay':
        server_mode = 'stop_proxy'

    # proxy_started = check_proxy_running(replay_configurations, mode)
    proxy_started = True
    while proxy_started:
        # Try every 10 iterations
        url = 'http://{0}:{1}/{2}'.format( \
                    replay_configurations[replay_config_utils.SERVER_HOSTNAME], \
                    replay_configurations[replay_config_utils.SERVER_PORT], \
                    server_mode)
        result = requests.get(url)
        # proxy_started = not (result.status_code == 200 and result.text.strip() == 'Proxy Stopped') \
        #         and check_proxy_running(replay_configurations, mode)
        proxy_started = not (result.status_code == 200 and result.text.strip() == 'Proxy Stopped')
        if proxy_started:
            return proxy_started
        print 'request result: ' + result.text
        sleep(10)

def load_one_website(page, iterations, output_dir, device_info):
    '''
    Loads one website
    '''
    for run_index in range(0, iterations):
        try:
            signal.alarm(TIMEOUT)
            load_page(page, run_index, output_dir, False, device_info, True)
            while common_module.check_previous_page_load(run_index, output_dir, page):
                load_page(page, run_index, output_dir, False, device_info, True)
            signal.alarm(0)
        except PageLoadException as e:
            print 'Timeout for {0}-th load. Append to end of queue...'.format(run_index)
            # Kill the browser and append a page.
            chrome_utils.close_all_tabs(device_info[2])
            common_module.initialize_browser(device_info) # Start the browser
            return page
    return None

def timeout_handler(signum, frame):
    '''
    Handle the case where the page fails to load
    '''
    raise PageLoadException('Time\'s up for this load.')

def check_proxy_running(config, mode):
    print 'Checking if proxy running'
    if mode == 'record':
        server_check = 'is_recording'
    elif mode == 'replay':
        server_check = 'is_proxy_running'

    url = 'http://{0}:{1}/{2}'.format( \
                config[replay_config_utils.SERVER_HOSTNAME], \
                config[replay_config_utils.SERVER_PORT], \
                server_check)
    result = requests.get(url)
    print 'proxy_running: ' + result.text
    return result.status_code == 200 and \
            result.text != ''

def load_page(raw_line, run_index, output_dir, start_measurements, device_info, disable_tracing):
    # Create necessary directories
    base_output_dir = output_dir
    if not os.path.exists(base_output_dir):
        os.mkdir(base_output_dir)
    output_dir_run = os.path.join(base_output_dir, str(run_index))
    if not os.path.exists(output_dir_run):
        os.mkdir(output_dir_run)
    
    line = raw_line.strip()
    cmd = 'python /home/vaspol/Research/MobileWebOptimization/scripts/ChromeMessageCollector/get_chrome_messages.py {1} {2} {0} --output-dir {3}'.format(line, device_info[1], device_info[0], output_dir_run) 
    if disable_tracing:
        cmd += ' --disable-tracing'
    # if run_index > 0:
    #     cmd += ' --reload-page'
    subprocess.Popen(cmd, shell=True).wait()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('pages_filename')
    parser.add_argument('replay_config_filename')
    parser.add_argument('device_name')
    parser.add_argument('iterations', type=int)
    parser.add_argument('mode')
    parser.add_argument('output_dir')
    parser.add_argument('--time', default=None)
    args = parser.parse_args()
    pages = common_module.get_pages(args.pages_filename)
    main(args.replay_config_filename, pages, args.iterations, args.device_name, args.mode, args.output_dir)