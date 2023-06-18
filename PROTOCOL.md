# Wire protocol reference

This app acts as a client to a server that is running on the robot.
The client connects to the server to send it commands, and to receive video and telemetry.

The client connects to the server using Websocket protocol which is responsible for delivering each message in full.

The following messages are defined:

## Client to server

### Wheel setpoints

This message sets the direct new values for the setpoints of the port and starboard wheel controller.
This is an advanced method: for normal use, consider using one of the other methods for setting the desired position.

The first byte is the ASCII letter `S`.
After that, 4 instances of 2 bytes are sent:
these are the new setpoints for the wheel controllers as 16-bit signed values.
The wheels are provided in the order: port front, starboard front, starboard back, port back.

### Wheel pair offset setpoints

This message sets the desired setpoints for the translation of the port and starboard wheel pairs.

A pair of mecanum wheels can move forward and back (by turning both the wheels in sync), as well as left or right (by turning the wheels outward or inward).
This message sets the desired position on the X-Y plane for both the pairs of wheels on the robot.
This is sufficient to move and rotate the entire robot.
However, the two pairs can come into disagreement, and the controllers may attempt to fight between each other to reach their desired target.

The first byte is the ASCII letter `T`.
After that, 4 16-bit signed values follow:
the first two are the offset for the port side, the second two are for the starboard side.

The first within each pair is a forward-back offset, where values towards the front of the robot are positive.
The second within each pair is a left-right offset, where values **in the direction away from the robot** are positive, and **towards the symmetry axis of the robot** are negative.


### Emergency stop

This message is intended to prevent the robot from moving as quickly as possible, for example when the robot is doing something unsafe.
Also: when the client disconnects from the server, the server should interpret it as having this message sent to it.

When the message is received, the robot should command the motor controllers to stop the motors (if possible).
Then, it should reset the setpoints for the motor controllers to match the current wheel positions, so that the controllers would not move the wheels.
Finally, for at least two seconds, the server must ignore any setpoint commands sent to it.
This timer is reset if another emergency stop message is received within this interval.

The first and only byte of the message is the ASCII letter `!`.


## Server to client
### Video frame

A single frame captured by the robot's camera, as well as info on when it was taken.

The first byte is the ASCII letter `F`.
The next 8 bytes are the timestamp of when the frame was captured, in IEEE754 "double precision" in big-endian order.
The next 4 bytes are an unsigned integer indicating how many bytes of picture data are included.
After that, that many bytes of JPEG-encoded data.

