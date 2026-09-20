from machine import Pin

class BuzzerManager:
    def __init__(self, pin_number=4, disabled=False):
        self.buzzer_pin = Pin(pin_number, Pin.OUT)
        self.disabled = disabled

    def on(self):
        if not self.disabled:
            self.buzzer_pin.value(1)  #buzzer ON
    
    def off(self):
        if not self.disabled:
            self.buzzer_pin.value(0)  #buzzer OFF