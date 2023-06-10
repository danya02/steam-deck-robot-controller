import time
from typing import Any
import pygame
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ScreenRunResult:
    """
    Represents what a Screen wants to happen on the next frame of its execution.
    """


class Screen(ABC):
    """
    Represents a full-screen environment of the application, like an Android Activity.

    Is responsible for its own handling of the input events and for drawing to the screen.
    """

    def __init__(self):
        """
        A reference to the current app display is needed.
        """
        self.last_rendered_at = 0

    @abstractmethod
    def run_frame(self, display: pygame.Surface) -> ScreenRunResult:
        """
        Perform all the processing needed for the execution and rendering of this frame, rendering it on the provided surface.
        Return a value indicating what should happen to this Screen on the next frame.
        """
        self.last_rendered_at = time.perf_counter()
        return ContinueExecution.value

    @abstractmethod
    def should_render_frame(self) -> bool:
        """
        This method returns whether the screen would like to get rendered now.
        It is called on every render opportunity.
        """
        return False

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Accept a Pygame event and update internal state based on it.

        Return True if we would like to `run_frame` now, or False otherwise.
        The normal `should_render_frame` also applies, even if this returns True.
        """
        return False
    
    def receive_data(self, returning_screen, returned_data: Any):
        """
        When a screen that was called with CallAnother emits a ReturnToCaller,
        this method is called.
        Immediately after that, run_frame is called again.

        Use this to receive and react to data from sub windows.
        """
        pass

    @property
    def time_since_last_rendered(self) -> float:
        return time.perf_counter() - self.last_rendered_at


@dataclass
class ContinueExecution(ScreenRunResult):
    """
    Indicates that the Screen wants to continue to be on the screen.
    """


ContinueExecution.value = ContinueExecution()


@dataclass
class ExitProgram(ScreenRunResult):
    """
    Indicates that the screen wants the program to be shut down.
    """


ExitProgram.value = ExitProgram()


@dataclass
class CallAnother(ScreenRunResult):
    """
    Indicates that this screen wants another screen to start being the one currently displayed.

    The parent screen is responsible for initializing the child screen being passed here.
    The parent screen will be kept around in a stack.
    """

    screen: Screen


@dataclass
class ReturnToCaller(ScreenRunResult):
    """
    Indicates that the screen wants to return control to the screen that called it, possibly returning some data.
    """

    data: Any
