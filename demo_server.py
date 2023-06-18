import cv2
import websockets.sync.server
import time
import struct
import threading


camera = cv2.VideoCapture(0)  # init the camera
conn_lock = threading.Lock()
emergency_stop_when_started = 0.0


def handler(socket: websockets.sync.server.ServerConnection):
    global emergency_stop_when_started
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
                    match cmd[0:1]:
                        case b"S":
                            if time.time() - emergency_stop_when_started < 2:
                                print("Ignoring setpoint command due to emergency stop")
                                break
                            setpoints = list(struct.unpack(">hhhh", cmd[1:]))
                            if setpoints != old_setpoints:
                                old_setpoints = setpoints
                                print("New setpoints:", setpoints)
                        case b"T":
                            if time.time() - emergency_stop_when_started < 2:
                                print("Ignoring setpoint command due to emergency stop")
                                break
                            # Offsets: port to forward, port to left, starboard to forward, starboard to right
                            opf,opl,osf,osr = struct.unpack(">hhhh", cmd[1:])
                            print("Offsets:")
                            print("Port to forward:", opf)
                            print("Port to left:", opl)
                            print("Starboard to forward:", osf)
                            print("Starboard to right:", osr)
                            
                            # Need to transform the coordinates from pair offsets into setpoints.
                            spf = 0
                            spb = 0
                            ssf = 0
                            ssb = 0

                            # Forward-back motion: add this component to both wheels on side
                            spf += opf
                            spb += opf
                            ssf += osf
                            ssb += osf

                            # Left-right motion: one wheel needs this component subtracted, the other added
                            # (TODO: check which one on real robot)

                            spf += opl
                            spb -= opl

                            ssf += osr
                            ssb -= osr

                            # port front, starboard front, starboard back, port back
                            setpoints = [spf, ssf, ssb, spb]
                            if setpoints != old_setpoints:
                                old_setpoints = setpoints
                                print("New setpoints:", setpoints)
                        case b"!":
                            # Emergency stop:
                            emergency_stop_when_started = time.time()
                            # TODO: set setpoints to wheel positions

                        case what:
                            print("Unknown command:", repr(what))
            except TimeoutError:
                pass

            grabbed, frame = camera.read()  # grab the current frame
            when = time.time()
            frame = cv2.resize(frame, (640, 480))  # resize the frame
            encoded, buffer = cv2.imencode('.jpg', frame)
            to_send = bytearray(b'F????????????')
            when_size_enc = struct.pack_into(">dI", to_send, 1, when, len(buffer))
            to_send.extend(buffer)
            socket.send(to_send)


    except KeyboardInterrupt:
        camera.release()
        cv2.destroyAllWindows()
    finally:
        conn_lock.release()

server = websockets.sync.server.serve(handler, host='0.0.0.0', port=5555)
server.serve_forever()