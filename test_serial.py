import serial
import threading
a = serial.Serial('/dev/ttyACM0', 115200)

def readloop():
    while 1:
        print(a.readline())

threading.Thread(target=readloop, daemon=True).start()

while 1:
    c = input()
    c += "\r\n"
    a.write(c.encode())
    a.flush()
