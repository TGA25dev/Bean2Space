import esp32 #type: ignore

def read_internal_temp():
    """
    Reads the internal MCU temperature directly in Celsius
    
    args:
        None
    returns:
        float: The internal temperature of the board in Celsius
    """
    temp = esp32.mcu_temperature()
    return temp

def check_internal_temp(threshold:float) -> tuple[bool, float]:
    """
    Checks if the internal temperature exceeds a given threshold
    
    args:
        threshold (float): The temperature threshold in Celsius
    returns:
        tuple(bool, float):True if the internal temperature exceeds the threshold, False otherwise, and the current temperature
    """

    current_temp = read_internal_temp()
    return (current_temp > threshold), current_temp