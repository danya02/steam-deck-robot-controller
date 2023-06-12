import cv2
import websockets.sync.server


camera = cv2.VideoCapture(0)  # init the camera

def handler(socket):
    while True:
        try:
            grabbed, frame = camera.read()  # grab the current frame
            frame = cv2.resize(frame, (640, 480))  # resize the frame
            encoded, buffer = cv2.imencode('.jpg', frame)
            socket.send(bytes(buffer))

        except KeyboardInterrupt:
            camera.release()
            cv2.destroyAllWindows()
            break

server = websockets.sync.server.serve(handler, host='0.0.0.0', port=5555)
server.serve_forever()