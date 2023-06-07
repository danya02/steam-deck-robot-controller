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
    def __init__(self, display: pygame.Surface):
        """
        A reference to the current app display is needed.
        """
        self.display = display

    @abstractmethod
    def run_frame(self) -> ScreenRunResult:
        """
        Perform all the processing needed for the execution of this frame.
        Return a value indicating what should happen to this Screen on the next frame.
        """
        return ContinueExecution.value

    @abstractmethod
    async def should_render_frame(self) -> bool:
        """
        This coroutine returns True if it would like to update the contents of the screen.
        It does not return, or returns False, if it does not want to do it on this loop.
        """
        return False

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Accept a Pygame event and update internal state based on it.

        Return True if we would like to `run_frame` now, or False otherwise.
        The normal `should_render_frame` also applies, even if this returns True.
        """


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