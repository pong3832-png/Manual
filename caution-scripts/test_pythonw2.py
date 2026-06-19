import sys
import traceback

with open("test_crash.log", "w") as f:
    f.write(f"stdout is {sys.stdout}\n")
    try:
        print("hello")
        f.write("print success\n")
    except Exception as e:
        f.write(f"print failed: {e}\n")
        f.write(traceback.format_exc())
