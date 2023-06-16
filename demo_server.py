import cv2
import websockets.sync.server
import time
import struct


camera = cv2.VideoCapture(0)  # init the camera

def handler(socket: websockets.sync.server.ServerConnection):
    old_setpoints = None
    while True:
        try:
            try:
                while 1:  # loop until timeout error
                    cmd = socket.recv(timeout=0)
                    match cmd[0:1]:
                        case b"S":
                            setpoints = struct.unpack(">hhhh", cmd[1:])
                            if setpoints != old_setpoints:
                                old_setpoints = setpoints
                                print("New setpoints:", setpoints)
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
            break

server = websockets.sync.server.serve(handler, host='0.0.0.0', port=5555)
server.serve_forever()