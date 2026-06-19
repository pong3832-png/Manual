import os
import runpy


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.abspath(os.path.join(BASE_DIR, os.pardir, "\uc2a4\ucf00\uc904\ub7ec.py"))

runpy.run_path(TARGET, run_name="__main__")
