all: upload-source play-remote
pyinstall:
	pyinstaller ./run_app.py -F -n "robotcontrol"

test:
	PYTHONPATH=. pytest

clean:
	rm -rf build/ dist/

upload-source:
	rsync -av --delete . deck@steamdeck.local:/home/deck/devkit-game/RobotControl

play-remote:
	ssh deck@steamdeck.local -t "bash -c \"cd /home/deck/devkit-game/RobotControl; DISPLAY=:0 python ./run_app.py -- devel\""