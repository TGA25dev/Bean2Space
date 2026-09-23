import time

print("Press Ctrl+C within 5 seconds to enter maintenance mode")

try:
    time.sleep(5)
    
except KeyboardInterrupt:
    print("Maintenance mode")
else:
    import software.main