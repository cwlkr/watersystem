from threading import Thread
import threading
import time
from flask_socketio import emit
import warnings
try:
    import RPi.GPIO as GPIO
except RuntimeError:
    pass

class WaterLevelSensor():
    def __init__(self, IN_GPIO_W, OUT_GPIO_W, debug_value=0, debug=False):
        self.IN_GPIO_W = IN_GPIO_W
        self.OUT_GPIO_W = OUT_GPIO_W
        self.debug = debug
        if not self.debug:
            self.set_up_gpio()
        self.debug_value = debug_value
    
    def set_up_gpio(self):
        if type(self.IN_GPIO_W) is not list:
            self.IN_GPIO_W = [self.IN_GPIO_W]
        for gpio in self.IN_GPIO_W:
            GPIO.setup(gpio, GPIO.IN)
        GPIO.setup(self.OUT_GPIO_W, GPIO.OUT)

    def check_water_level(self):
        if self.debug:
            return self.debug_value
        else:
            GPIO.output(self.OUT_GPIO_W, GPIO.HIGH)
            res = []
            for gpio in self.OUT_GPIO_W:
                time.sleep(0.01)
                res.append(GPIO.input(gpio))
                time.sleep(0.01)
            GPIO.output(self.OUT_GPIO_W, GPIO.LOW)
            water_lvl_perc =  (sum(res)-1)/(len(self.IN_GPIO_W))
            if water_lvl_perc == 0:
                water_lvl_perc = 5
            if water_lvl_perc == -0.25:
                water_lvl_perc == 0
            return water_lvl_perc

    def check_water_with_delay(self):
        res = self.check_water_level()
        if res:
            return res
        else:
            time.sleep(0.01)
            return self.check_water_level()

class cleanGPIO:

    def __init__(self, verbose=False):
        self.verbose=verbose
        
    def __enter__(self, *args):
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            print('Something went wrong, cleaning up!')

        with warnings.catch_warnings():
            warnings.simplefilter("error") #turn warning into exceptions
            try:
                GPIO.cleanup()
            except( RuntimeWarning, NameError):
                pass # silence it
        if not self.verbose:  # silence the exception if not verbose
            return True


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class PumpObserver():
    def __init__(self, app):
        self.app = app
    def notify(self, current_pump_state):
        with self.app.app_context():
            emit('updated_pump_state', current_pump_state, broadcast=True, namespace='/')

class SwitchObserver():
    def __init__(self, sensor, app):
        self.app = app
        self.sensor = sensor

    def notify(self, switch_state):
        # what to do if switch has been turned off.
        if not switch_state:
            with self.app.app_context():
                emit('waterlevel_update', self.sensor.check_water_level(), broadcast=True, namespace='/')

class Pump(metaclass=Singleton):
    # make singleton
    def __init__(self, RELAIS_1_GPIO, debug=False):
        self.is_running = False
        self.RELAIS_1_GPIO = RELAIS_1_GPIO
        self.debug=debug
        self.pump_states = (True, False)
        self.observers = []
        if not self.debug: self.set_up_gpio() 
        ## make sure in init to set gpio to off! Then we always know where pump starts from.
        # maybe check a temp file that keeps a persistent log of the current pump state or just check GPIO.input(RELAIS_1_GPIO)
        
    def set_up_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.RELAIS_1_GPIO, GPIO.OUT)
        GPIO.output(self.RELAIS_1_GPIO, GPIO.LOW) # aus
        
    def change_pump_state(self, state):
        assert state in self.pump_states
        self.is_running = state
        self.notify()

    def start(self):
        if not self.debug:
            GPIO.output(self.RELAIS_1_GPIO, GPIO.HIGH) # ein    
        else:
            print('debug mode: pump on')
        self.change_pump_state(True)
        
    def stop(self):
        if not self.debug:
            GPIO.output(self.RELAIS_1_GPIO, GPIO.LOW) # aus
        else:
            print('debug mode: pump off')
        self.change_pump_state(False)
    
    def register(self, observer):
        self.observers.append(observer)
        
    def notify(self):
        for observer in self.observers:
            observer.notify(self.is_running)

class ProtectedPumpSwitch():
    def __init__(self, pump, max_time_on=240):
        self.pump = pump
        self.max_time_on = max_time_on
        self.switch_states = (False, True)
        self.switch_state = False
        self.current_thread = None
        self.observers = []

    def set_switch_state(self, state):
        if self.switch_state != state:
            self.switch_state = state
            self.notify()

    def switch_on_with_timout(self, timeout):
        timeout = min(timeout, self.max_time_on)
        self.pump.start()
        self.current_thread = Thread(target=self.auto_off, args=(timeout,))
        self.current_thread.start()
        self.set_switch_state(True)
        return timeout
        
    def switch_on(self):
        self.pump.start()
        # self.set_switch(True)
        self.current_thread = Thread(target=self.auto_off, args=(self.max_time_on,))
        self.current_thread.start()
        self.set_switch_state(True)
        
    def switch_off(self):
        self.pump.stop()
        if self.current_thread.is_alive():
            self.current_thread.do_run = False
        self.set_switch_state(False)
        
    def auto_off(self, timeout):
        t = threading.currentThread()
        total_secs = 0
        while getattr(t, "do_run", True) and (total_secs < timeout):
            total_secs +=1
            time.sleep(1)
        if getattr(t, "do_run", True): # and self.pump.is_running
            self.switch_off()
            
    def flip_switch(self):
        if self.pump.is_running:            
            self.switch_off()
        else:
            self.switch_on()

    def register(self, observer):
        self.observers.append(observer)
        
    def notify(self):
        for observer in self.observers:
            observer.notify(self.switch_state)