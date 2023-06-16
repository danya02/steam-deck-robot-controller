import math
import struct
import time
from typing import Any
import cv2
import numpy as np
import pygame
import threading
import websockets.sync.client
import websockets.exceptions

from steamdeck_robotcontrol.screen import ContinueExecution, ReturnToCaller, ScreenRunResult
from steamdeck_robotcontrol.screens.generator_screen import IGNORE_OPPORTUNITY, RENDERING_OPPORTUNITY, SUPPORTS_RENDERING, WANT_TO_RENDER
from .. import screen


def robot_control_wrapper(server_addr):
    """Generator-style wrapper responsible for (re)opening the connection."""
    # The first thing I'll receive is an indication of a rendering opportunity, and some events.
    yield SUPPORTS_RENDERING
    # Then, I'll send an ignored value, which would have been my first indication of what to do.
    opportunity, events = yield None

    connected_once = False

    while True:
        # Now they're waiting for me to say what I want to do.
        # I want to render now, and they'll give me the display.
        display = yield WANT_TO_RENDER

        # I will render the "Connecting" text to the screen.
        display.fill('black')
        font = pygame.font.SysFont(pygame.font.get_default_font(), 48)
        text = font.render(f"{'Rec' if connected_once else 'C'}onnecting to {server_addr} (press B to give up)...", True, 'white')
        display.blit(text, (0,0))  # TODO: position
        last_rendered_at = time.perf_counter()

        # Now I'm done rendering, and I'm going to start connecting.
        connection_result = [None, None]
        def connect():
            try:
                socket = websockets.sync.client.connect(f"ws://{server_addr}")
                connection_result[0] = socket  # Instead of return, must use this
            except Exception as e:
                connection_result[1] = e
        connection_thread = threading.Thread(target=connect, daemon=True)
        connection_thread.start()

        # I will tell the caller that I'm done rendering, and would now like to continue running
        opportunity, events = yield ContinueExecution.value

        # Now comes an event loop
        i = 100
        while connection_thread.is_alive():
            for event in events:
                if event.type == pygame.JOYBUTTONDOWN and event.button == 1:
                    # The B button was pressed, which means we're aborting the connection.
                    return None

            # I'll yield whether I want to continue, or render.
            # I'll render if it's more than 1 second since I did last time.
            if time.perf_counter() - last_rendered_at > 1:
                display = yield WANT_TO_RENDER
                display.fill('black')
                display.blit(text, (i, 100))  # to see if it's working, we move the text
                i += 10
                last_rendered_at = time.perf_counter()
                opportunity, events = yield ContinueExecution.value
            else:
                # Otherwise, I don't care about this rendering opportunity.
                opportunity, events = yield IGNORE_OPPORTUNITY

        # If the second value is there, then it means that there was an error connecting.
        # Show the error, and give the option to retry
        if connection_result[1]:
            # This is something to render
            display = yield WANT_TO_RENDER
            display.fill('black')
            errors = []
            errors.append( font.render(f"Error while connecting to {server_addr}:", True, 'white') )
            errors.append( font.render(repr(connection_result[1]), True, 'white') )
            errors.append( font.render("Press A to retry or B to give up", True, 'white') )
            rect = pygame.Rect(0,0,0,0)
            for error in errors:
                error_rect = error.get_rect()
                error_rect.top = rect.bottom
                error_rect.left = rect.left
                display.blit(error, error_rect)
                rect = error_rect
            
            # Now sit in a loop, accepting events until either button is pressed.
            opportunity, events = yield ContinueExecution.value
            last_rendered_at = time.perf_counter()
            what_to_do = None
            print(what_to_do)
            while not what_to_do:
                for e in events:
                    if e.type == pygame.JOYBUTTONDOWN:
                        if e.button == 0: what_to_do = 'retry'
                        elif e.button == 1: what_to_do = 'abort'
                
                # Occasionally we need to take the render opportunity, but not render anything new.
                # This is so that the display keeps up to date.
                if time.perf_counter() - last_rendered_at > 1:
                    display = yield WANT_TO_RENDER
                    opportunity, events = yield ContinueExecution.value
                else:
                    opportunity, events = yield IGNORE_OPPORTUNITY

            # We need to acquire some new events now, after the event with the button press.
            opportunity, events = yield IGNORE_OPPORTUNITY
            if what_to_do == 'retry':
                what_to_do = None  # idk how exactly, but this does not get reset at the start of the loop
                # Continue to the start of the loop implicitly
            else: return None



        else:
            # With the connection established, we can make a RobotControlScreen out of it
            # Yield it, and wait for a response
            connected_once = True
            reason = yield RobotControlScreen(connection_result[0])
            # The response will tell us how the control session died.
            # If it was a disconnection, we should try to reconnect.
            if reason == 'conn':
                continue
            else:
                return None



class RobotControlScreen(screen.Screen):
    """Maintains a connection to the robot and sends it joystick positions."""
    def __init__(self, websocket: websockets.sync.client.ClientConnection):
        super().__init__()
        self.socket = websocket
        self.connection = None

        self.left_joystick_position = [0, 0]
        self.right_joystick_position = [0, 0]
        self.port_wheel_pair_position = [0.0,0.0]
        self.starboard_wheel_pair_position = [0.0,0.0]
        
        self.last_integration_time = time.perf_counter()
        self.top_speed = 100


        self.events_without_render = 0
        self.closing = False
        self.closing_reason = None

        self.latest_video_frame = pygame.Surface((800, 600))
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), 24)
        self.latest_video_frame.fill((255,0,255))
        self.latest_video_frame_latency = 0.0
        self.latest_video_frame_presented = False
        self.latest_video_frame_latencies = [0]
        self.video_recv_thread = threading.Thread(target=self.video_recv_thread_worker, daemon=True)
        self.video_recv_thread.start()

        self.video_is_fullscreen = False

    def video_recv_thread_worker(self):
        try:
            while not self.closing:
                try:
                    msg = self.socket.recv()
                except websockets.exceptions.ConnectionClosed:
                    self.closing = True
                    self.closing_reason = 'conn'
                if msg[0] == ord('F'):  # video frame
                    when_captured, byte_size = struct.unpack_from(">dI", buffer=msg, offset=1)
                    npimg = np.frombuffer(msg[13:], dtype=np.uint8)
                    cv2img = cv2.imdecode(npimg, 1)
                    pygame_img = pygame.image.frombuffer(cv2img.tostring(), cv2img.shape[1::-1], "BGR")
                    self.latest_video_frame = pygame_img
                    self.latest_video_frame_latency = time.time() - when_captured
                    self.latest_video_frame_latencies.append(self.latest_video_frame_latency)
                    while len(self.latest_video_frame_latencies) > 1280:  # Horizontal chart can fit 1280 pixels
                        self.latest_video_frame_latencies.pop(0)
                    self.latest_video_frame_presented = True
        finally:
        # Finalize by closing the socket
            self.socket.close()


    def run_frame(self, display: pygame.Surface) -> ScreenRunResult:
        super().run_frame(display)
        display.fill('black')
        if self.closing:
            return ReturnToCaller(self.closing_reason)

        disp = display.get_rect()

        if self.video_is_fullscreen:
            img = self.latest_video_frame
            factor = min(disp.width / img.get_width(), disp.height / img.get_height())
            img = pygame.transform.scale_by(img, factor)
            img_rect = img.get_rect()
            img_rect.center = disp.center
            display.blit(img, img_rect)
            return ContinueExecution.value


        left_joystick_circle = pygame.Rect(0, 0, 100, 100)
        left_joystick_circle.centery = disp.centery
        left_joystick_circle.left = disp.left + 25
        pygame.draw.circle(display, 'white', left_joystick_circle.center, left_joystick_circle.width/2, 4)
        pygame.draw.line(display, 'white', (left_joystick_circle.centerx, left_joystick_circle.top), (left_joystick_circle.centerx, left_joystick_circle.bottom), 2)
        pygame.draw.line(display, 'white', (left_joystick_circle.left, left_joystick_circle.centery), (left_joystick_circle.right, left_joystick_circle.centery), 2)
        
        right_joystick_circle = left_joystick_circle.copy()
        right_joystick_circle.right = disp.right - 25
        pygame.draw.circle(display, 'white', right_joystick_circle.center, right_joystick_circle.width/2, 4)
        pygame.draw.line(display, 'white', (right_joystick_circle.centerx, right_joystick_circle.top), (right_joystick_circle.centerx, right_joystick_circle.bottom), 2)
        pygame.draw.line(display, 'white', (right_joystick_circle.left, right_joystick_circle.centery), (right_joystick_circle.right, right_joystick_circle.centery), 2)

        # Draw joystick positions
        left_joystick_pos = pygame.Rect(0,0,25,25)
        left_joystick_pos.centerx = left_joystick_circle.centerx + (self.left_joystick_position[0] * left_joystick_circle.width / 2)
        left_joystick_pos.centery = left_joystick_circle.centery + (self.left_joystick_position[1] * left_joystick_circle.height / 2)

        right_joystick_pos = left_joystick_pos.copy()
        right_joystick_pos.centerx = right_joystick_circle.centerx + (self.right_joystick_position[0] * right_joystick_circle.width / 2)
        right_joystick_pos.centery = right_joystick_circle.centery + (self.right_joystick_position[1] * right_joystick_circle.height / 2)

        pygame.draw.circle(display, (0, 128, 255), left_joystick_pos.center, left_joystick_pos.width/2)
        pygame.draw.circle(display, 'red', right_joystick_pos.center, right_joystick_pos.width/2)

        # In the middle of the screen, draw the frame
        frame_rect = self.latest_video_frame.get_rect()
        frame_rect.center = disp.center
        display.blit(self.latest_video_frame, frame_rect)
        self.latest_video_frame_presented = True

        # In a corner of the screen, draw the delay between now and the latest frame
        delay_text = self.font.render(f"Frame recv: {round(1000*self.latest_video_frame_latency, 2)} ms ago", True, 'white')
        delay_rect = delay_text.get_rect()
        display.blit(delay_text, delay_rect)

        # On bottom of screen, draw a chart of the latencies
        chart_rect = pygame.Rect(0, 0, disp.width, 200)
        chart_rect.bottom = disp.bottom
        lines = 10
        min_value = min(self.latest_video_frame_latencies)
        max_value = max(self.latest_video_frame_latencies)

        # First draw the points (or bars?)
        for idx, sample in enumerate(self.latest_video_frame_latencies):
            height_frac = (sample - min_value) / ((max_value - min_value) or 1)
            screen_position = chart_rect.bottom - int(chart_rect.height * height_frac)
            if height_frac < 0.5:
                color = (int(255 * height_frac), 255, 0)
            else:
                color = (255, int(255 * (1-height_frac)), 0)
            #display.set_at((idx, screen_position), color)
            pygame.draw.line(display, color, (idx, chart_rect.bottom), (idx, screen_position)) 
        # Then, draw lines and their labels
        for line in range(lines):
            screen_position = chart_rect.bottom - int((chart_rect.bottom - chart_rect.top) * line / lines)
            pygame.draw.line(display, 'grey', (chart_rect.left, screen_position), (chart_rect.right, screen_position), 2)
            value = min_value + (max_value - min_value) * line / lines
            value = str(round(value * 1000, 2)) + 'ms'
            label = self.font.render(value, True, 'grey')
            label_rect = label.get_rect()
            label_rect.bottom = screen_position
            label_rect.right = disp.right
            display.blit(label, label_rect)


        return ContinueExecution.value

    def receive_data(self, returning_screen, returned_data: Any):
        return super().receive_data(returning_screen, returned_data)

    @property
    def port_wheel_pair_position_rounded(self):
        return [round(self.port_wheel_pair_position[0]), round(self.port_wheel_pair_position[1])]
    
    @property
    def starboard_wheel_pair_position_rounded(self):
        return [round(self.starboard_wheel_pair_position[0]), round(self.starboard_wheel_pair_position[1])]
    

    def should_render_frame(self) -> bool:
        # Run integration for the two axes
        deltaT = time.perf_counter() - self.last_integration_time

        old_port_wheel = self.port_wheel_pair_position_rounded
        old_starboard_wheel = self.starboard_wheel_pair_position_rounded

        # Deadzone: if the joystick distance from the center is below a threshold,
        # do not use it in integration
        left_distance = math.sqrt(sum([i**2 for i in self.left_joystick_position]))
        if left_distance >= 0.1:
            self.port_wheel_pair_position[0] += self.left_joystick_position[0] * self.top_speed * deltaT
            self.port_wheel_pair_position[1] += self.left_joystick_position[1] * self.top_speed * deltaT

        right_distance = math.sqrt(sum([i**2 for i in self.right_joystick_position]))
        if right_distance >= 0.1:
            self.starboard_wheel_pair_position[0] += self.right_joystick_position[0] * self.top_speed * deltaT
            self.starboard_wheel_pair_position[1] += self.right_joystick_position[1] * self.top_speed * deltaT

        self.last_integration_time = time.perf_counter()
        # Send the new value if the integration had exceeded a single point of difference.
        if self.port_wheel_pair_position_rounded != old_port_wheel or self.starboard_wheel_pair_position_rounded != old_starboard_wheel:
            cmd = bytearray(b"S")
            pf, pb = self.port_wheel_pair_position_rounded
            sf, sb = self.starboard_wheel_pair_position_rounded
            cmd.extend(struct.pack(">hhhh", pf, sf, sb, pb))
            self.socket.send(cmd)
            print("Sent", self.port_wheel_pair_position_rounded, self.starboard_wheel_pair_position_rounded)


        return self.time_since_last_rendered > 1 or not self.latest_video_frame_presented
    
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.JOYBUTTONDOWN:
            print(event.button)
            if event.button == 5:  # Right shoulder button
                self.video_is_fullscreen = True
            elif event.button == 6:  # Left menu button / start button
                self.closing = True
                self.closing_reason = 'user'
        elif event.type == pygame.JOYBUTTONUP:
            if event.button == 5:
                self.video_is_fullscreen = False
        if event.type == pygame.JOYAXISMOTION:
            match event.axis:
                case 0:
                    self.left_joystick_position[0] = event.value
                case 1:
                    self.left_joystick_position[1] = event.value
                case 3:
                    self.right_joystick_position[0] = event.value
                case 4:
                    self.right_joystick_position[1] = event.value
                case _:
                    return False
        #print(self.left_joystick_position, self.right_joystick_position)
        self.events_without_render += 1
        if self.events_without_render > 10:
            self.events_without_render = 0
            return True
        return False

