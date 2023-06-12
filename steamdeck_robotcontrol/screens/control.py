import time
from typing import Any
import pygame
import threading

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
        connection_result = [None]
        def connect():
            time.sleep(10)  # TODO: connection code here
            connection_result[0] = 'OK'  # Instead of return, must use this
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

        # With the connection established, we can make a RobotControlScreen out of it
        # Yield it, and wait for a response
        connected_once = True
        resp = yield RobotControlScreen(connection=connection_result[0])
        # The response will tell us how the control session died.
        # If it was a disconnection, we should try to reconnect.
        if resp:
            continue
        else:
            return None




class RobotControlScreen(screen.Screen):
    """Maintains a connection to the robot and sends it joystick positions."""
    def __init__(self, connection=''):
        super().__init__()
        self.server = connection
        self.connection = None
        self.left_joystick_position = [0, 0]
        self.right_joystick_position = [0, 0]
        self.events_without_render = 0
        self.closing = False
        


    def run_frame(self, display: pygame.Surface) -> ScreenRunResult:
        super().run_frame(display)
        display.fill('black')
        if self.closing:
            return ReturnToCaller(True)

        disp = display.get_rect()
        left_joystick_circle = pygame.Rect(0, 0, 250, 250)
        left_joystick_circle.centery = disp.centery
        left_joystick_circle.centerx = int(disp.centerx / 2)
        pygame.draw.circle(display, 'white', left_joystick_circle.center, left_joystick_circle.width/2, 4)
        pygame.draw.line(display, 'white', (left_joystick_circle.centerx, left_joystick_circle.top), (left_joystick_circle.centerx, left_joystick_circle.bottom), 2)
        pygame.draw.line(display, 'white', (left_joystick_circle.left, left_joystick_circle.centery), (left_joystick_circle.right, left_joystick_circle.centery), 2)
        
        right_joystick_circle = left_joystick_circle.copy()
        right_joystick_circle.centerx = int(3 * disp.centerx / 2)
        pygame.draw.circle(display, 'white', right_joystick_circle.center, right_joystick_circle.width/2, 4)
        pygame.draw.line(display, 'white', (right_joystick_circle.centerx, right_joystick_circle.top), (right_joystick_circle.centerx, right_joystick_circle.bottom), 2)
        pygame.draw.line(display, 'white', (right_joystick_circle.left, right_joystick_circle.centery), (right_joystick_circle.right, right_joystick_circle.centery), 2)

        # Draw joystick positions
        left_joystick_pos = pygame.Rect(0,0,50,50)
        left_joystick_pos.centerx = left_joystick_circle.centerx + (self.left_joystick_position[0] * left_joystick_circle.width / 2)
        left_joystick_pos.centery = left_joystick_circle.centery + (self.left_joystick_position[1] * left_joystick_circle.height / 2)

        right_joystick_pos = pygame.Rect(0,0,50,50)
        right_joystick_pos.centerx = right_joystick_circle.centerx + (self.right_joystick_position[0] * right_joystick_circle.width / 2)
        right_joystick_pos.centery = right_joystick_circle.centery + (self.right_joystick_position[1] * right_joystick_circle.height / 2)

        pygame.draw.circle(display, (0, 128, 255), left_joystick_pos.center, left_joystick_pos.width/2)
        pygame.draw.circle(display, 'red', right_joystick_pos.center, right_joystick_pos.width/2)

        return ContinueExecution.value

    def receive_data(self, returning_screen, returned_data: Any):
        return super().receive_data(returning_screen, returned_data)

    def should_render_frame(self) -> bool:
        return self.time_since_last_rendered > 1
    
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.JOYBUTTONDOWN:
            self.closing = True
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

