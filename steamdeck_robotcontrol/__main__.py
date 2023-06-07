import pygame
from . import screens
from .screen import *
import asyncio

entrypoint = screens.SampleScreen

display_to_transfer = None

def pygame_event_loop(asyncio_loop: asyncio.AbstractEventLoop, event_queue: asyncio.Queue):
    while True:
        event = pygame.event.wait()
        asyncio.run_coroutine_threadsafe(event_queue.put(event), asyncio_loop)

async def main():
    pygame.init()
    is_running = True
    display = pygame.display.set_mode((1280,800))


    # Initialize the Pygame event loop task
    loop = asyncio.get_event_loop()
    event_queue = asyncio.Queue()
    pygame_task = loop.run_in_executor(None, pygame_event_loop, loop, event_queue)

    current_screen = entrypoint(display)
    latest_should_render_task = asyncio.create_task(current_screen.should_render_frame())
    should_render = False

    try:
        while is_running:
            # Wait for the first to happen: 
            done, _pending = await asyncio.wait([
                asyncio.Task(event_queue.get()), # either an event comes in through the event queue,
                latest_should_render_task, # or the screen wants to get rendered,
            ], return_when=asyncio.FIRST_COMPLETED)
            if latest_should_render_task in done:
                # This means that the should render task is the one that returned
                if latest_should_render_task.result():
                    should_render = True
                # Restart the task for the next loop
                latest_should_render_task = asyncio.create_task(current_screen.should_render_frame())
            else:
                # This means that the event queue has a new item
                ev_queue_task = done.pop()  # should be the single item
                event = ev_queue_task.result()
                if current_screen.handle_event(event):
                    should_render = True
            
            # Now we know whether to render now
            if should_render:
                result = current_screen.run_frame()
                pygame.display.flip()
                should_render = False

                match result:
                    case ContinueExecution(): continue
                    case ExitProgram(): is_running = False
                    case what: raise RuntimeError(f"Unknown run frame result: {what}")

    finally:
        pygame_task.cancel()
        pygame.quit()



def run():
    asyncio.run(main())


if __name__ == '__main__':
    run()