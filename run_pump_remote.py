import argparse
import time
import sys
import logging
import socketio
from logging.handlers import RotatingFileHandler
try:
    import RPi.GPIO as GPIO
except RuntimeError:
    pass
import requests

_MAX_SCHEDULABLE_ON_TIME = 4
_MIN_SCHEDULABLE_ON_TIME = 0.016

def check_waterlvl():
    request = requests.get("http://192.168.0.25/get_waterlvl")
    if request.status_code == 200:
        return request.json()
    else:
        raise requests.exceptions.ConnectionError

def wait_for_pump_off(runtime):
    start_time = time.time()
    event, data = sio.receive(timeout=runtime+1)
    while not (event == 'updated_pump_state' and not data):
        event, data = sio.receive(timeout=runtime+1)
    return round(time.time() - start_time, 0)

def main(args):
    runtime = int(args.time*60)
    logging.info(f'Started Watersystem. Planned on time: {args.time} minutes')
    if check_waterlvl() or args.force:
        excepted_run_time = sio.call('switch_pump_on_with_timeout', runtime, timeout=10)['timed']
        time_run = wait_for_pump_off(excepted_run_time)
        if time_run == round(runtime, 0):
            logging.info(f'Watersystem finished successfully')
        elif time_run == excepted_run_time:
            logging.info(f'Watersystem terminated by server after {round(time_run/60,1)} minutes, due to max_time_on')
        else:
            logging.info(f'Watersystem externally stoped after {round(time_run/60,1)} minutes')
        if not check_waterlvl():
            logging.warning(f'Waterlevels after run low, next scheduled run will most likely not start sucessfully')
    else:
        logging.warning('Watertank appears to be empty. Run apported')

def initialize_logger():
    handlers = [RotatingFileHandler(filename='/home/ws/watersys_server/watersys_cron.log',
                                 backupCount=4,
                                 maxBytes=20000)]
    if args.verbose:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
               datefmt="%Y-%m-%d %H:%M:%S",
               handlers=handlers,
               level=logging.INFO)
        
if __name__ == "__main__":

    parser = argparse.ArgumentParser(
                        prog='Watersystem',
                        description='Run a remote waterpump for a specific amount of time')

    parser.add_argument('-t', '--time', default=1, type=float)
    parser.add_argument('-f', '--force', action='store_true', default=False)
    parser.add_argument('-v', '--verbose', action='store_true', default=False)
    args = parser.parse_args()
    
    initialize_logger()
    
    sio = socketio.SimpleClient()
    
    try:
        sio.connect('http://192.168.0.25:80')
    except socketio.exceptions.ConnectionError:
        logging.error('Watersystem not started, as server cannot be reached. Is server down?')
        sys.exit(1)
        
    if args.time >= _MAX_SCHEDULABLE_ON_TIME:
        if not args.force:
            logging.error('Watersystem not started. as time set too high, are you sure time is minutes?')
            sys.exit(1)
        else:
            logging.warning('Watersystem start forced, despite time set too high. Run time will not exceed pumps max_time_on')
    elif args.time < _MIN_SCHEDULABLE_ON_TIME:
        logging.warning('Watersystem time might be inacturate, due to very low scheduled time.')

    try:
        main(args)
    except  (requests.exceptions.ConnectionError, socketio.exceptions.TimeoutError) as e:
        logging.error('Watersystem terminated because of failure to communicate with server. Is server down?')
    finally:
        sio.disconnect()
