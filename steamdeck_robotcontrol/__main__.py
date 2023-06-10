import threading
import time
import traceback
import pygame
from .screens import RobotControlScreen
from .screen import *
import asyncio

#entrypoint = lambda disp: screens.TextInputScreen(disp, "Type whatever")
#entrypoint = screens.SampleScreen
entrypoint = RobotControlScreen

display_to_transfer = None

def run_render(screen_stack):
    global current_screen
    result = current_screen.run_frame()
    pygame.display.flip()

    match result:
        case ContinueExecution():
            return
        case ExitProgram():
            raise SystemExit
        case CallAnother(other_screen):
            screen_stack.append(current_screen)
            current_screen = other_screen
        case ReturnToCaller(data):
            old_screen = current_screen
            if screen_stack:
                current_screen = screen_stack.pop()
                current_screen.receive_data(old_screen, data)
                current_screen.run_frame()
                run_render(screen_stack)
            else:
                print(f"Screen {old_screen} returned without a caller on the stack with data: {data}")
                raise SystemExit
        case what:
            raise RuntimeError(f"Unknown run frame result: {what}")



async def main():
    pygame.init()
    is_running = True
    display = pygame.display.set_mode((1280, 800))
    #if not pygame.display.is_fullscreen():
    #    pygame.display.toggle_fullscreen()

    joysticks = [
        pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())
    ]

    
    global current_screen
    current_screen = entrypoint(display)
    screen_stack = []

    clock = pygame.time.Clock()
    try:
        while True:
            clock.tick(60)
            should_render = False
            for event in pygame.event.get():
                should_render |= current_screen.handle_event(event)
            should_render |= current_screen.should_render_frame()

            if should_render:
                run_render(screen_stack)
            
    except:
        traceback.print_exc()

    finally:
        pygame.quit()


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
