# backend/pump.py
from gpiozero import Device, LED
from gpiozero.pins.lgpio import LGPIOFactory     # <-- add
Device.pin_factory = LGPIOFactory()              # <-- add

from time import sleep
def blink_led(pin: int = 17, duration: int = 2):
    led = LED(pin, active_high=False)            # LOW-active relay
    led.on()
    sleep(duration)
    led.off()
