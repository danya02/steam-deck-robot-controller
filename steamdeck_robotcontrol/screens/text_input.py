from typing import Any
import pygame

from steamdeck_robotcontrol.screen import ContinueExecution, ReturnToCaller, ScreenRunResult
from .. import screen

class TextInputScreen(screen.Screen):
    """Asks for some text from the user and returns it once Enter is hit."""
    def __init__(self, prompt='', prefill='', allow_cancelling=False):
        super().__init__()
        self.prompt = prompt
        self.text = prefill
        self.am_returning_now = False
        self.allow_cancelling = allow_cancelling
        pygame.font.init()
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), 36)
        self.did_flip_fullscreen = False


    def run_frame(self, display: pygame.Surface) -> ScreenRunResult:
        super().run_frame(display)
        if self.am_returning_now:
            if self.did_flip_fullscreen:
                pygame.display.toggle_fullscreen()
            return ReturnToCaller(self.text)
        
        # On Steam Deck's desktop mode, the keyboard will not appear above fullscreen programs.
        # So we need to make sure we aren't in full screen for this.
        if pygame.display.is_fullscreen():
            self.did_flip_fullscreen = True
            pygame.display.toggle_fullscreen()
        
        display.fill('black')
        disp = display.get_rect()

        prompt_line = self.font.render(self.prompt, True, 'white')
        prompt_pos = prompt_line.get_rect()
        prompt_pos.center = disp.center
        prompt_pos.top = disp.top + int(prompt_pos.height*1.5)
        display.blit(prompt_line, prompt_pos)

        answer_box = pygame.Rect(0, 0, int(disp.width*0.75), int(prompt_pos.height*1.25))
        answer_box.center = prompt_pos.center
        answer_box.centery += 120
        pygame.draw.rect(display, 'white', answer_box, width=4)

        answer_line = self.font.render(self.text, True, 'white')
        answer_pos = answer_line.get_rect()
        answer_pos.center = answer_box.center

        display.blit(answer_line, answer_pos)


        keyboard_line = self.font.render(f"To show keyboard, press STEAM+X buttons. Enter to confirm{', B button to cancel' if self.allow_cancelling else ''}.", True, 'white')
        keyboard_pos = keyboard_line.get_rect()
        keyboard_pos.bottom = disp.bottom - 100  # This ensures it is below the keyboard, but above the taskbar (if there is one)
        display.blit(keyboard_line, keyboard_pos)

        return ContinueExecution.value

    def receive_data(self, returning_screen, returned_data: Any):
        return super().receive_data(returning_screen, returned_data)

    def should_render_frame(self) -> bool:
        return self.time_since_last_rendered > 1

    
    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            elif event.key == pygame.K_RETURN:
                self.am_returning_now = True
                return True
        elif event.type == pygame.TEXTINPUT:
               self.text += event.text
               return True
        elif event.type == pygame.JOYBUTTONDOWN:
            if self.allow_cancelling and event.button == 1:
                self.text = None
                self.am_returning_now = True
                return True
        return False