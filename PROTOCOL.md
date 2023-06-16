# Wire protocol reference

This app acts as a client to a server that is running on the robot.
The client connects to the server to send it commands, and to receive video and telemetry.

The client connects to the server using Websocket protocol which is responsible for delivering each message in full.

The following messages are defined:

## Client to server

### Wheel pair setpoints

This message sets the new values for the setpoints of the port and starboard wheel controller.
This is an advanced method: for normal use, consider using one of the other methods for setting the desired position.

The first byte is the ASCII letter `S`.
After that, 4 instances of 2 bytes are sent:
these are the new setpoints for the wheel controllers.
The wheels are provided in the order: port front, starboard front, starboard back, port back.


## Server to client
### Video frame

A single frame captured by the robot's camera, as well as info on when it was taken.

The first byte is the ASCII letter `F`.
The next 8 bytes are the timestamp of when the frame was captured, in IEEE754 "double precision" in big-endian order.
The next 4 bytes are an unsigned integer indicating how many bytes of picture data are included.
After that, that many bytes of JPEG-encoded data.

