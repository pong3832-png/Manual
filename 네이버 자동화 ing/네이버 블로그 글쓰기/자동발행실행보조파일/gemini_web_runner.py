import os
import runpy


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.abspath(os.path.join(BASE_DIR, os.pardir, "\uc81c\ubbf8\ub098\uc774\uc6f9.py"))

runpy.run_path(TARGET, run_name="__main__")
