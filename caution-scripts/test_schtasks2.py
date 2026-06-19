import subprocess
import sys

python_exe = sys.executable.replace("python.exe", "pythonw.exe")
main_golf_path = r"C:\Users\itwill\자동화 공부\티스토리 자동화 ing\golf\main_golf.py"

task_run_cmd = f'"{python_exe}" "{main_golf_path}" --post-type golf --scheduled --publish'
cmd = [
    "schtasks", "/Create", "/TN", "TestPythonW", "/SC", "ONCE", "/SD", "2026/04/29", "/ST", "12:00",
    "/TR", task_run_cmd, "/F"
]
proc = subprocess.run(cmd, capture_output=True, text=True)
print("OUT:", proc.stdout)
print("ERR:", proc.stderr)
