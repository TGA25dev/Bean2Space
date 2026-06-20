from machine import Pin

class LEDManager:
    def __init__(self, pin_number=1, active_low=False):
        self.led_pin = Pin(pin_number, Pin.OUT)
        self.active_low = active_low

    def on(self):
        value = 0 if self.active_low else 1
        self.led_pin.value(value)
    
    def off(self):
        value = 1 if self.active_low else 0
        self.led_pin.value(value)