from steamdeck_robotcontrol.__main__ import run

if __name__ == '__main__':
    import os
    import sys
    import re
    if 'devel' in sys.argv:
        # When developing, the process is that the program code is uploaded to the Deck with rsync,
        # then run as a Xorg program (nb: the Plasma desktop uses Wayland usually)
        # So the DISPLAY is :0,
        os.environ['DISPLAY'] = ':0'
        # and the XAUTHORITY is stored in /run/user/1000 and is a UUID.
        xauthority_candidates = []
        xauth_origin = '/run/user/1000/'
        for file in os.listdir(xauth_origin):
            if re.match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', file):
                xauthority_candidates.append(os.path.join(xauth_origin, file))
        # The old XAUTHORITY files are not cleaned up, so we need to find the latest one.
        print(xauthority_candidates)
        xauth = max(xauthority_candidates, key=lambda x: os.stat(x).st_mtime)
        os.environ['XAUTHORITY'] = xauth
    run()