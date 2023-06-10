from steamdeck_robotcontrol.__main__ import run

if __name__ == '__main__':
    import os
    os.environ['DISPLAY'] = ':0'
    os.environ['XAUTHORITY']='/run/user/1000/c552cc44-9a87-493a-a40f-06f20b1b9efd'
    run()