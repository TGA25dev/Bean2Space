from machine import Pin

class BuzzerManager:
    def __init__(self, pin_number=2):
        self.buzzer_pin = Pin(pin_number, Pin.OUT)

    def on(self):
        self.buzzer_pin.value(1)  #buzzer ON
    
    def off(self):
        self.buzzer_pin.value(0)  #buzzer OFF