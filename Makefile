all: test pyinstall
pyinstall:
	pyinstaller ./run_app.py -F -n "robotcontrol"

test:
	PYTHONPATH=. pytest

clean:
	rm -rf build/ dist/