import asyncio
import pygame

from steamdeck_robotcontrol.screen import ScreenRunResult
from .. import screen
import random

class SampleScreen(screen.Screen):
    """
    This screen is a simple example for screens.
    """
    def __init__(self, display):
        self.square = pygame.Rect(0,0,100,100)
        self.going_down = True
        self.going_right = True
        self.frames_remaining = random.randint(500, 1000)
        super().__init__(display)

    def run_frame(self) -> ScreenRunResult:
        self.display.fill('black')
        self.display.fill('white', self.square)
        self.square.centerx += (10 if self.going_right else -10)
        self.square.centery += (10 if self.going_down else -10)
        if self.square.right > self.display.get_width():
            self.going_right = False
        elif self.square.left < 0:
            self.going_right = True
        
        if self.square.bottom > self.display.get_height():
            self.going_down = False
        elif self.square.top < 0:
            self.going_down = True
        
        self.frames_remaining -= 1
        if self.frames_remaining <= 0:
            return screen.ExitProgram.value
        
        return screen.ContinueExecution.value
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        return True
    
    async def should_render_frame(self) -> bool:
        await asyncio.sleep(1)
        return True
