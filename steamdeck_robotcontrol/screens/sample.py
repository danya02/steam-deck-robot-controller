from typing import Any
import pygame

from steamdeck_robotcontrol.screen import ScreenRunResult
from .. import screen
import random


class SampleScreen(screen.Screen):
    """
    This screen is a simple example for screens.
    """

    def __init__(self, display):
        self.square = pygame.Rect(0, 0, 100, 100)
        self.going_down = True
        self.going_right = True
        self.frames_remaining = random.randint(500, 1000)
        super().__init__(display)

    def run_frame(self) -> ScreenRunResult:
        super().run_frame()
        self.display.fill("black")
        self.display.fill("white", self.square)
        self.square.centerx += 10 if self.going_right else -10
        self.square.centery += 10 if self.going_down else -10
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

    def should_render_frame(self) -> bool:
        return self.time_since_last_rendered > 1
    
    def receive_data(self, returning_screen, returned_data: Any):
        return super().receive_data(returning_screen, returned_data)


class EventLogScreen(screen.Screen):
    """This screen shows a list of events that have been passed to it."""

    def __init__(self, display):
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), 24)
        self.log = []
        super().__init__(display)

    def run_frame(self) -> ScreenRunResult:
        super().run_frame()
        self.display.fill("black")
        if not self.log:
            self.log.append("EMPTY")

        srect = self.display.get_rect()
        items_shown = []
        for v in reversed(self.log):
            line = self.font.render(v, True, "white")
            lrect = line.get_rect()
            if not items_shown:
                lrect.bottom = srect.bottom
            else:
                lrect.bottom = items_shown[-1][1].top
            if lrect.top < 0:
                break
            items_shown.append((line, lrect))

        self.log = self.log[-len(items_shown) :]

        for item, pos in items_shown:
            self.display.blit(item, pos)

        return screen.ContinueExecution.value

    def handle_event(self, event: pygame.event.Event) -> bool:
        self.log.append(str(event))
        return True

    def should_render_frame(self) -> bool:
        return self.time_since_last_rendered > 1

    def receive_data(self, returning_screen, returned_data: Any):
        return super().receive_data(returning_screen, returned_data)