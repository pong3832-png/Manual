import os
import sys
import subprocess

def build():
    print("="*50)
    print("Premium_GUI.exe build start")
    print("="*50)

    # 1. customtkinter 경로 찾기
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
    print(f"Found customtkinter at: {ctk_path}")

    # 2. PyInstaller 커맨드 구성 (noconsole, onefile, customtkinter 폴더 추가, GUI.py 스크립트 추가)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    separator = ';' if sys.platform == 'win32' else ':'

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed", # 검은 콘솔창 숨김
        "--name", "Premium_Neighbor_Bot",
        f"--add-data={ctk_path}{separator}customtkinter/",
        f"--add-data={os.path.join(base_dir, 'GUI.py')}{separator}.",
        os.path.join(base_dir, "Premium_GUI.py")
    ]

    print("Running PyInstaller...")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    
    for line in iter(process.stdout.readline, ''):
        print(line, end="")
        
    process.wait()
    
    if process.returncode == 0:
        print("="*50)
        print("Build Success!!")
        print(f"File created at: {os.path.join(base_dir, 'dist', 'Premium_Neighbor_Bot.exe')}")
        print("="*50)
    else:
        print("Build failed. See logs above.")

if __name__ == "__main__":
    build()
