from typing import Any
import pygame

from steamdeck_robotcontrol.screen import ContinueExecution, ReturnToCaller, ScreenRunResult
from .. import screen

class TextInputScreen(screen.Screen):
    """Asks for some text from the user and returns it once Enter is hit."""
    def __init__(self, display: pygame.Surface, prompt=''):
        super().__init__(display)
        self.prompt = prompt
        self.text = ''
        self.am_returning_now = False
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), 36)


    def run_frame(self) -> ScreenRunResult:
        super().run_frame()
        if self.am_returning_now:
            return ReturnToCaller(self.text)
        
        self.display.fill('black')
        disp = self.display.get_rect()

        prompt_line = self.font.render(self.prompt, True, 'white')
        prompt_pos = prompt_line.get_rect()
        prompt_pos.center = disp.center
        prompt_pos.top = disp.top + int(prompt_pos.height*1.5)
        self.display.blit(prompt_line, prompt_pos)

        answer_box = pygame.Rect(0, 0, int(disp.width*0.75), int(prompt_pos.height*1.25))
        answer_box.center = prompt_pos.center
        answer_box.centery += 120
        pygame.draw.rect(self.display, 'white', answer_box, width=4)

        answer_line = self.font.render(self.text, True, 'white')
        answer_pos = answer_line.get_rect()
        answer_pos.center = answer_box.center

        self.display.blit(answer_line, answer_pos)
        return ContinueExecution.value

    def receive_data(self, returning_screen, returned_data: Any):
        return super().receive_data(returning_screen, returned_data)

    async def should_render_frame(self) -> bool:
        await asyncio.sleep(1)
        return True
    
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.am_returning_now = True
        elif event.type == pygame.TEXTINPUT:
               self.text += event.text

