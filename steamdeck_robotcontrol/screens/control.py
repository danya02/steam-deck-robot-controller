import asyncio
from typing import Any
import pygame

from steamdeck_robotcontrol.screen import ContinueExecution, ReturnToCaller, ScreenRunResult
from .. import screen

class RobotControlScreen(screen.Screen):
    """Maintains a connection to the robot and sends it joystick positions."""
    def __init__(self, server=''):
        super().__init__()
        self.server = server
        self.connection = None
        self.left_joystick_position = [0, 0]
        self.right_joystick_position = [0, 0]
        self.events_without_render = 0
        


    def run_frame(self, display: pygame.Surface) -> ScreenRunResult:
        super().run_frame(display)
        display.fill('black')

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

