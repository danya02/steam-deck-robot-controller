import cv2
import websockets.sync.server
import time
import struct
import threading


import serial
p = serial.Serial('/dev/ttyACM0', 115200)

camera = cv2.VideoCapture(0)  # init the camera
conn_lock = threading.Lock()
emergency_stop_when_started = 0.0

INPUT_SCALE = 10
MIN_SIDE_VAL = 50


def wheel_controller_read():
    while 1:
        print(p.readline())

threading.Thread(target=wheel_controller_read, daemon=True).start()

current_setpoints = [0,0,0,0]

def write_setpoints(sp):
  #print("Writing", current_setpoints)
  last_setpoints = current_setpoints
  spf, ssf, ssb, spb = current_setpoints
  #print(f'pf{spf} sf{ssf} sb{ssb} pb{spb}\r\n')
  p.write(f'pf{spf} sf{ssf} sb{ssb} pb{spb}\r\n'.encode())
  #p.write('?\r\n'.encode())
  p.flush()

p.write(b'\x03')
p.write('\r\n'.encode())
p.write(b'\x04')
p.write('\r\n'.encode())
p.flush()

def write_thread():
    last_setpoints = None
    p.write(b'\x03')
    p.write('\r\n'.encode())
    p.write(b'\x04')
    p.write('\r\n'.encode())
    p.flush()
    while 1:
      write_setpoints(current_setpoints)
      time.sleep(0.01)


def report_loop():
    while 1:
        time.sleep(1)
        p.write(b'?\r\n')
        p.flush()

threading.Thread(target=report_loop, daemon=True).start()


def handler(socket: websockets.sync.server.ServerConnection):
    global emergency_stop_when_started
    global current_setpoints
    if conn_lock.locked():
        socket.close(code=1008,  # closing due to message that violates policy
                     reason="Another client is connected")
    conn_lock.acquire()
    old_setpoints = None
    try:
        while True:
            try:
                while 1:  # loop until timeout error
                    cmd = socket.recv(timeout=0)
                    if cmd[0:1] == b"S":
                            if time.time() - emergency_stop_when_started < 2:
                                print("Ignoring setpoint command due to emergency stop")
                                break
                            setpoints = list(struct.unpack(">hhhh", cmd[1:]))
                            if setpoints != old_setpoints:
                                old_setpoints = setpoints
                                #print("New setpoints:", setpoints)
                    if cmd[0:1] == b"T":
                            if time.time() - emergency_stop_when_started < 2:
                                print("Ignoring setpoint command due to emergency stop")
                                break
                            # Offsets: port to forward, port to left, starboard to forward, starboard to right
                            opf,opl,osf,osr = struct.unpack(">hhhh", cmd[1:])
                            #print("Offsets:")
                            #print("Port to forward:", opf)
                            #print("Port to left:", opl)
                            #print("Starboard to forward:", osf)
                            #print("Starboard to right:", osr)
                            
                            # Need to transform the coordinates from pair offsets into setpoints.
                            #spf, ssf, ssb, spb = current_setpoints
                            spf, ssf, ssb, spb = 0,0,0,0

                            if abs(opl) < MIN_SIDE_VAL and abs(osr) < MIN_SIDE_VAL:
                                # Forward-back motion: add this component to both wheels on side
                                spf += opf
                                spb += opf
                                ssf += osf
                                ssb += osf
                            else:
                                # Left-right motion: one wheel needs this component subtracted, the other added
                                # (TODO: check which one on real robot)
                                spf += opl
                                spb -= opl
                                ssf += osr
                                ssb -= osr

                            # port front, starboard front, starboard back, port back
                            setpoints = [spf, ssf, ssb, spb]

                            for i in range(len(setpoints)):
                                setpoints[i] *= INPUT_SCALE

                            if setpoints != old_setpoints:
                                old_setpoints = setpoints
                                current_setpoints = setpoints
                                write_setpoints(setpoints)

                    elif cmd[0:1] == b"!":
                            # Emergency stop:
                            emergency_stop_when_started = time.time()
                            # TODO: set setpoints to wheel positions
                            p.write(b'!\r\n')
                            p.flush()

                    else:
                            print("Unknown command:", repr(cmd))
            except TimeoutError:
                pass
            try:
              grabbed, frame = camera.read()  # grab the current frame
              when = time.time()
              frame = cv2.resize(frame, (640, 480))  # resize the frame
              encoded, buffer = cv2.imencode('.jpg', frame)
              to_send = bytearray(b'F????????????')
              when_size_enc = struct.pack_into(">dI", to_send, 1, when, len(buffer))
              to_send.extend(buffer)
              socket.send(to_send)
            except: pass


    except KeyboardInterrupt:
        camera.release()
        cv2.destroyAllWindows()
    finally:
        conn_lock.release()
        p.write(b'\x03')
        p.write('\r\n'.encode())
        p.write(b'\x04')
        p.write('\r\n'.encode())
        p.flush()

server = websockets.sync.server.serve(handler, host='0.0.0.0', port=5555)
server.serve_forever()
