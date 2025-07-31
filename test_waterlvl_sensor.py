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
        if not self.debug:,
            self.set_up_gpio()
        self.debug_value = debug_value

    def set_up_gpio(self):
        GPIO.setup(self.IN_GPIO_W, GPIO.IN)
        GPIO.setup(self.OUT_GPIO_W, GPIO.OUT)

    def check_water_level(self):
        if self.debug:
            return self.debug_value
        else:
            GPIO.output(self.OUT_GPIO_W, GPIO.HIGH)
            res = GPIO.input(self.IN_GPIO_W)
            GPIO.output(self.OUT_GPIO_W, GPIO.LOW)
            return bool(res)

    def check_water_with_delay(self):
        if self.check_water_level():
            return True
        else:
            time.sleep(1)
            return self.check_water_level()
        
W = WaterLevelSensor(IN_GPIO_W, OUT_GPIO_W)