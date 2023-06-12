import cv2
import zmq
import numpy as np

context = zmq.Context()
footage_socket = context.socket(zmq.SUB)
footage_socket.connect('tcp://localhost:5555')
footage_socket.setsockopt_string(zmq.SUBSCRIBE, '')

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