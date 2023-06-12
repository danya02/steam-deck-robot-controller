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

    The generator is expected to yield a ScreenRunResult every time, indicating what to do on the next frame.
    When the generator returns, the value it returned is used as a ReturnToCaller value.
    """
    def __init__(self, generator: Generator[ScreenRunResult, Any, Any]):
        self.generator = generator
        self.receive_data(None, None)  # to start the generator
        print("Generator initial response:", self.what_to_return_next_frame)
    
    def run_frame(self, display: pygame.Surface) -> ScreenRunResult:
        super().run_frame(display)
        display.fill((255,0,255))  # magenta; if this is shown for more than a single frame, then there is an error in the generator's logic
        print("Frame yielding:", self.what_to_return_next_frame)
        return self.what_to_return_next_frame

    def should_render_frame(self) -> bool:
        return True

    def handle_event(self, event: pygame.event.Event) -> bool:
        return False

    def receive_data(self, returning_screen, returned_data: Any):
        # This is the only reason for us to "render" frames
        # Pass the data into the generator
        try:
            print("Sending", returned_data, 'to generator')
            what_to_call = self.generator.send(returned_data)
            self.what_to_return_next_frame = CallAnother(what_to_call)
            print("Generator responded with", what_to_call)

            # The generator is now waiting for a response from a called function 
        except StopIteration as e:  # Generator has returned
            if isinstance(e.value, ScreenRunResult):
                # Return the final ScreenRunResult, if it's not one that would continue this screen
                # NOTE: if this is CallAnother, it will be stuck in an infinite loop of calling that screen
                self.what_to_return_next_frame = e.value
            else:
                # Return the value itself
                self.what_to_return_next_frame = ReturnToCaller(e.value)

# Magic constants used for communicating with a rendering generator
RENDERING_OPPORTUNITY = 'rendering opportunity'
WANT_TO_RENDER = 'want to render'
IGNORE_OPPORTUNITY = 'ignore opportunity'
SUPPORTS_RENDERING = 'supports rendering'

# These are internal constants for communicating inside the class
NOTHING = 'nothing'
SEND_DISPLAY = 'send display'
RETURN_STORED_VALUE = 'return stored value'

def if_stopped_return(fn):
    """
    This decorator catches StopIteration and assigns the value inside it to the variable to return.
    That way, when the generator quits, we'll be able to catch its final response.
    """
    def wrapped(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except StopIteration as e:
            self.bail_with = ReturnToCaller(e.value)
            return True  # because a likely place for this to happen is in should_render_frame or handle_event
    return wrapped

class RenderingGeneratorScreen(screen.Screen):
    """
    Allows a generator to imperatively render to the display, in addition to tying together other Screens.
    """

    def __init__(self, generator: Generator[ScreenRunResult, Any, Any]):
        self.generator = generator
        self.queued_events = []
        self.on_render_do = NOTHING
        self.stored_run_result = ...
        self.bail_with = None

        # On the first iteration, we cannot send anything into the generator.
        # Also, the generator will not be able to do anything,
        # since on the rendering opportunity its response will be overwritten.
        # So, we'll simply sync up here.
        if self.generator.send(None) is not SUPPORTS_RENDERING:
            raise ValueError("Generator provided did not say it supports rendering")
        # Now the generator is waiting on data from the yield SUPPORTS_RENDERING, but that is ignored there.
        self.generator.send(None)

    @if_stopped_return
    def run_frame(self, display: pygame.Surface) -> ScreenRunResult:
        if self.bail_with:
            return self.bail_with

        super().run_frame(display)
        if self.on_render_do is NOTHING:
            print("run_frame called when on_render_do is NOTHING -- this is a bug!")
            return ...
        elif self.on_render_do is SEND_DISPLAY:
            # This means that the generator is ready to run the frame manually
            # We'll send it the display, and it'll yield a ScreenRunResult
            # After that, it'll enter the generic state again.
            try:
                resp = self.generator.send(display)
                
                return resp
            finally:
                self.on_render_do = NOTHING
        elif self.on_render_do is RETURN_STORED_VALUE:
            try:
                return self.stored_run_result
            finally:
                self.stored_run_result = ...
                self.on_render_do = NOTHING

    @if_stopped_return
    def default_state_response_handle(self, resp) -> bool:
        # Inspect the response from a generator in the default state,
        # and prepare for rendering a frame if needed.
        if isinstance(resp, screen.Screen):
            # One option is that the generator wants to call a screen, and this is it.
            self.stored_run_result = CallAnother(resp)
            self.on_render_do = RETURN_STORED_VALUE
            return True
        elif resp is WANT_TO_RENDER:
            # Another option is that it wants to render something,
            # in which case we'll need to pass it the display on the next iteration.
            self.on_render_do = SEND_DISPLAY
            return True
        elif resp is IGNORE_OPPORTUNITY:
            return False
        else:
            print(f"Unexpected return value from the generator: {resp}. Is the generator out of sync?")
            return False

    @if_stopped_return
    def should_render_frame(self) -> bool:
        if self.bail_with: return True  # while bailing, return that value as soon as possible

        # We need to ask the generator whether it wants to render now, considering the events it received.
        # It will yield WANT_TO_RENDER if it does, meaning it's waiting for the display.
        # Also: this should only happen when this is the active Screen;
        # so we do not need to keep track if the generator is waiting on data.

        # We first send the rendering opportunity data, and ignore the response.
        resp = self.generator.send( (RENDERING_OPPORTUNITY, self.queued_events) )
        self.queued_events.clear()

        # Then, the generator will ignore the data, and we'll get a response.
        #resp = self.generator.send(DNC)

        return self.default_state_response_handle(resp)

    @if_stopped_return
    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.bail_with: return True  # while bailing, return that value as soon as possible

        # This is called for every event that happened this frame.
        # Before the rendering actually happens, more events can come in.
        # So we store them in a list, and then we'll send the entire list.
        self.queued_events.append(event)
        return False  # we don't actually know if we want to render it or not.

    @if_stopped_return
    def receive_data(self, returning_screen, returned_data: Any):
        # This should only get called if we have returned a CallAnother immediately before it.
        # So, the generator should be ready to receive the data from it.
        resp = self.generator.send(returned_data)
        # Immediately after this, run_frame will be called unconditionally.
        # This means that this is an opportunity for the generator to render something, or call another Screen.
        self.default_state_response_handle(resp)
