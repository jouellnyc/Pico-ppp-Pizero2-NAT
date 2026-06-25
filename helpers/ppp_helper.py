#ppp_helper

import time
import machine
import network

# 1. Hardware Initialization
uart = machine.UART(1, baudrate=115200, tx=machine.Pin(4), rx=machine.Pin(5), rxbuf=2048)
ppp = network.PPP(uart)

# 2. Activate and Trigger Connection
print("Triggering PPP connection...")
try:
    ppp.connect()
except OSError as e:
    # If it returns 114 (EALREADY), it means the connection is already negotiating
    if e.args[0] != 114:
        raise e

# 3. Connection Validation Loop
timeout = 15  # Max seconds to wait for a link
start_time = time.time()

print("Waiting for network interface to assign IP...")
while not ppp.isconnected():
    if (time.time() - start_time) > timeout:
        raise RuntimeError("PPP Link Negotiation Timeout - Check Pi daemon logs")
    
    print(".", end="")
    time.sleep_ms(500)

print("\nLink established successfully!")
print("Network Config:", ppp.ifconfig())
