from typing import Any, Generator
import pygame
from steamdeck_robotcontrol import persistence
from steamdeck_robotcontrol.screen import CallAnother, ContinueExecution, ExitProgram, ReturnToCaller, ScreenRunResult
from steamdeck_robotcontrol.screens.menu import VerticalMenuScreen
from steamdeck_robotcontrol.screens.text_input import TextInputScreen
from .. import screen


class GeneratorScreen(screen.Screen):
    """
    Chains together many Screens using a generator function,
    allowing for an imperative-style control flow.
    """
    def __init__(self, generator: Generator[ScreenRunResult, Any, Any]):
        self.generator = generator
        self.what_to_return_next_frame = next(self.generator)
        print("Generator initial response:", self.what_to_return_next_frame)
    
    def run_frame(self, display: pygame.Surface) -> ScreenRunResult:
        super().run_frame(display)
        display.fill((255,0,255))  # magenta; if this is shown for more than a single frame, then there is an error in the generator's logic
        print("Frame yielding:", self.what_to_return_next_frame)
        return self.what_to_return_next_frame
        # Note that this gets called twice.

    def should_render_frame(self) -> bool:
        return True

    def handle_event(self, event: pygame.event.Event) -> bool:
        return False

    def receive_data(self, returning_screen, returned_data: Any):
        # This is the only reason for us to "render" frames
        # Pass the data into the generator
        try:
            print("Sending", returned_data, 'to generator')
            self.what_to_return_next_frame = self.generator.send(returned_data)
            print("Generator responded with", self.what_to_return_next_frame)

            # The generator is now waiting for a response from a called function 
        except StopIteration as e:  # Generator has returned
            if isinstance(e.value, ContinueExecution):
                # We cannot continue execution when the generator has returned
                self.what_to_return_next_frame = ReturnToCaller(None)
            elif isinstance(e.value, ScreenRunResult):
                # Return the final ScreenRunResult, if it's not one that would continue this screen
                # NOTE: if this is CallAnother, it will be stuck in an infinite loop of calling that screen
                self.what_to_return_next_frame = e.value
            else:
                # Return the value itself
                self.what_to_return_next_frame = ReturnToCaller(e.value)
    