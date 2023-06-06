import pygame
from . import screens
from .screen import *

entrypoint = screens.SampleScreen

def run():
    pygame.init()
    display = pygame.display.set_mode((1280, 800))
    current_screen = entrypoint(display)
    is_running = True
    clock = pygame.time.Clock()

    while is_running:
        clock.tick(30)

        result = current_screen.run_frame()
        pygame.display.flip()

        match result:
            case ContinueExecution(): continue
            case ExitProgram(): is_running = False
            case what: raise RuntimeError(f"Unknown run frame result: {what}")

    pygame.quit()

if __name__ == '__main__':
    run()