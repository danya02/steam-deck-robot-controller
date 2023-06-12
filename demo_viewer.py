import cv2
import numpy as np
import websockets.sync.client

footage_socket = websockets.sync.client.connect("ws://localhost:5555")

while True:
    try:
        frame = footage_socket.recv()
        npimg = np.fromstring(frame, dtype=np.uint8)
        source = cv2.imdecode(npimg, 1)
        cv2.imshow("Stream", source)
        cv2.waitKey(1)

    except KeyboardInterrupt:
        cv2.destroyAllWindows()
        break