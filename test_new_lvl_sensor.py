import time 
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

IN_GPIO = 5
GPIO.setup(IN_GPIO, GPIO.IN)
IN_GPIO = 6
GPIO.setup(IN_GPIO, GPIO.IN)
IN_GPIO = 13
GPIO.setup(IN_GPIO, GPIO.IN)
IN_GPIO = 19
GPIO.setup(IN_GPIO, GPIO.IN)
IN_GPIO = 26
GPIO.setup(IN_GPIO, GPIO.IN)
OUT_GPIO = 20
GPIO.setup(OUT_GPIO, GPIO.OUT)

def level(x = [5,6,13,19,26]):
    ll = {}
    GPIO.output(OUT_GPIO, GPIO.HIGH)
    for i in [5,6,13,19,26]:
        time.sleep(0.1)
        ll[i] = GPIO.input(i)
    GPIO.output(OUT_GPIO, GPIO.LOW)
    return sum(ll.values()), ll

for i in range(5000):
    print(str(level()) + "\r", end="")
    time.sleep(0.5)
