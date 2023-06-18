import time
from typing import Any, List, Tuple
import pygame

from steamdeck_robotcontrol.screen import ContinueExecution, ReturnToCaller, ScreenRunResult
from .. import screen

TYPEMATIC_DELAY = 0.5  # When a direction is being held down, this is how long until typematic triggers
TYPEMATIC_RATE = 0.1  # When typematic is triggered, this is how often it will tick
TYPEMATIC_RATE_GAIN = 0.01  # When typematic is running, the delay will decrease by this factor every second.

class VerticalMenuScreen(screen.Screen):
    """Shows several rows, one below the other, and returns which was selected."""
    def __init__(self, items: List[Tuple[Any, str]], default_item=None, allow_cancelling=False):
        super().__init__()
        self.items = items
        pygame.font.init()
        font = pygame.font.SysFont(pygame.font.get_default_font(), 36)
        self.vspace = 12
        self.text_lines = []
        self.selected_item = None
        if default_item is not None:
            for i, (key, _) in enumerate(self.items):
                if default_item == key:
                    self.selected_item = i
                    break
            else: # no break
                raise ValueError(f"The default_argument must be the internal representation of one of the items: for example, default_item==items[0][0]; provided is: {default_item}")
        self.highlight_index = 0
        self.allow_cancelling = allow_cancelling
        for _, label in self.items:
            self.text_lines.append( (
                font.render(label, True, 'white'),
                [font.render(label, True, 'red'), font.render(label, True, 'green'), font.render(label, True, 'blue')]
            ))
        self.am_returning_now = False

        self.typematic_source = None
        self.typematic_direction = None
        self.typematic_initial_press_at = None
        self.typematic_last_typed_at = None


    def run_frame(self, display: pygame.Surface) -> ScreenRunResult:
        super().run_frame(display)
        if self.am_returning_now:
            if self.selected_item is not None:
                return ReturnToCaller(self.items[self.selected_item][0])
            else:
                return ReturnToCaller(None)

        display.fill('black')
        disp = display.get_rect()

        label_rects: List[pygame.Rect] = []
        for normal, _selected in self.text_lines:
            label_rects.append(normal.get_rect())
        
        # Vertical arrange: the first item is at the top of the screen, and the next one is below the bottom with a space
        latest_rect = None
        for rect in label_rects:
            rect.centerx = disp.centerx
            if not latest_rect:
                rect.top = 0
            else:
                rect.top = latest_rect.bottom + self.vspace
            latest_rect = rect
        
        # Now shift it so that the rects together have a vertical center of the screen

        grouped_rect = latest_rect.copy()
        grouped_rect.unionall_ip(label_rects)
        y_error = grouped_rect.centery - disp.centery
        for rect in label_rects:
            rect.centery -= y_error

        # Now shift it so that the selected item (if there is one) is at the center of the screen
        if self.selected_item is not None:
            highlighted_item = label_rects[self.selected_item]
            y_error = highlighted_item.centery - disp.centery
            for rect in label_rects:
                rect.centery -= y_error

        # Now draw the rects.
        for i, label_data in enumerate(zip(self.text_lines, label_rects)):
            label, rect = label_data
            label_deselected, labels_selected = label
            if self.selected_item == i:
                self.highlight_index = (self.highlight_index + 1) % len(labels_selected)
                current_label = labels_selected[self.highlight_index]
            else:
                current_label = label_deselected
            
            display.blit(current_label, rect)
            

        return ContinueExecution.value

    def receive_data(self, returning_screen, returned_data: Any):
        return super().receive_data(returning_screen, returned_data)

    def should_render_frame(self) -> bool:
        # Typematic processing
        if self.typematic_direction:
            # If typematic is ready, check whether we passed the first threshold
            running_for = time.perf_counter() - self.typematic_initial_press_at
            if running_for > TYPEMATIC_DELAY:
                # Now we need to start typing
                if self.typematic_last_typed_at is None:
                    self.selected_item = (self.selected_item + self.typematic_direction) % len(self.items)
                    self.typematic_last_typed_at = time.perf_counter()
                    return True
                else:
                    if (time.perf_counter() - self.typematic_last_typed_at) > (TYPEMATIC_RATE - (TYPEMATIC_RATE_GAIN * running_for)):
                        self.selected_item = (self.selected_item + self.typematic_direction) % len(self.items)
                        self.typematic_last_typed_at = time.perf_counter()
                        return True

        return self.time_since_last_rendered > 0.333

    
    def handle_event(self, event: pygame.event.Event) -> bool:
        desired_change = 0
        change_source = None  # 1 for hat, 2 for axis
        match event.type:
            case pygame.JOYHATMOTION:
                # there is only one hat, so its motion corresponds directly
                desired_change = -event.value[1]
                change_source = 1
                #print(event)
            case pygame.JOYBUTTONDOWN:
                # If A button is pressed, and item is selected, then we're returning.
                if event.button == 0 and self.selected_item is not None:
                    self.am_returning_now = True
                    return True

                # If B button is pressed, and we are allowed to return with no item, then returning.
                if event.button == 1 and self.allow_cancelling:
                    self.selected_item = None
                    self.am_returning_now = True
                    return True
            case pygame.JOYAXISMOTION:
                if event.axis == 1:  # left joystick, up-down axis (up is negative)
                    if abs(event.value)>0.8:
                        desired_change = (1 if event.value > 0 else -1)
                        change_source = 2
                    else:
                        desired_change = 0
                        change_source = 2
            #case _: pass

        if change_source:
            # First check whether typematic is currently running or preparing for this source
            if self.typematic_source == change_source:
                # If typematic is running, and the change is zero (or opposite to typematic), then stop typematic
                # then execute the desired change
                if desired_change == 0 or desired_change != self.typematic_direction:
                    #print("RESET")
                    self.typematic_direction = None
                    self.typematic_last_typed_at = None
                    self.typematic_initial_press_at = None
                    self.typematic_source = None
                elif desired_change == self.typematic_direction:
                    # If this matches the typematic direction, then let typematic keep running,
                    # and do not execute the change as normal
                    #print("KEEP RUNNING", self.typematic_direction)
                    return False
                
            elif change_source != self.typematic_source and desired_change == 0:
                # If the other source does not want any change, then it should be ignored
                return False
            else:
                # Typematic is not running: prepare to start it
                # And also continue to execute select
                # (also, if the new event is from a different source)
                self.typematic_direction = desired_change
                self.typematic_initial_press_at = time.perf_counter()
                self.typematic_source = change_source
                self.typematic_last_typed_at = None
                #print("START", self.typematic_direction)


            if self.selected_item is None:
                # If nothing was selected, select the first item.
                self.selected_item = (0 if desired_change>0 else len(self.items)-1)
            else:
                # Select an adjacent item, wrapping
                self.selected_item = (self.selected_item + desired_change) % len(self.items)
            return True
        else:
            return False

