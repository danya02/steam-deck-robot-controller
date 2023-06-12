from typing import Any
import pygame
from steamdeck_robotcontrol import persistence
from steamdeck_robotcontrol.screen import CallAnother, ContinueExecution, ExitProgram, ScreenRunResult
from steamdeck_robotcontrol.screens.control import robot_control_wrapper
from steamdeck_robotcontrol.screens.generator_screen import RenderingGeneratorScreen
from steamdeck_robotcontrol.screens.menu import VerticalMenuScreen
from steamdeck_robotcontrol.screens.text_input import TextInputScreen
from .. import screen

def main_menu():
    db = persistence.get_database('servers_config')
    while 1:
        items = []
        for index, server in enumerate(db.get_or_create('servers', [])):
            items.append( (index, f'View server "{server["name"]}"') )
        
        items.append( ('add', 'Add a new server...') )
        items.append( ('exit', 'Exit program') )
        response = yield VerticalMenuScreen(items)
        match response:
            case 'exit':
                return None
            case 'add':
                name = yield TextInputScreen("What should the new server be called?", prefill="New Server", allow_cancelling=True)
                if not name: continue
                address = yield TextInputScreen(f'What should the address for server "{name}" be?', allow_cancelling=True)
                if not address: continue
                db['servers'] += [{'name': name, 'address': address}]
            case idx:
                # Selected index of server
                yield from server_submenu(db, idx)

def server_submenu(db, server_idx):
    response = '???'
    while response and response != 'back':
        server = db['servers'][server_idx]
        menu = [
            ('conn', 'Connect to this server'),
            ('edit_name', f'Name: {server["name"]} (edit?)'),
            ('edit_addr', f'Address: {server["address"]} (edit?)'),
            ('back', 'Return to server list')
        ]
        response = yield VerticalMenuScreen(menu, default_item='conn', allow_cancelling=True)
        match response:
            case 'conn': yield RenderingGeneratorScreen(robot_control_wrapper(server['address']))
            case 'edit_name':
                new_name = yield TextInputScreen("What should the new name for this server be?", server['name'], allow_cancelling=True)
                if new_name:
                    server['name'] = new_name
                    db['servers'][server_idx] = server
            case 'edit_addr':
                new_addr = yield TextInputScreen("What should the new address for this server be?", server['address'], allow_cancelling=True)
                if new_addr:
                    server['address'] = new_addr
                    db['servers'][server_idx] = server