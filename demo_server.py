import cv2
import zmq

context = zmq.Context()
footage_socket = context.socket(zmq.PUB)
footage_socket.bind('tcp://*:5555')

camera = cv2.VideoCapture(0)  # init the camera

while True:
    try:
        grabbed, frame = camera.read()  # grab the current frame
        frame = cv2.resize(frame, (640, 480))  # resize the frame
        encoded, buffer = cv2.imencode('.jpg', frame)
        footage_socket.send(buffer)

    except KeyboardInterrupt:
        camera.release()
        cv2.destroyAllWindows()
        break