import sys
import threading
import queue
import time
import os
import io
import builtins
import customtkinter as ctk

# --- Ferrari Design Tokens ---
FERRARI_RED = "#DA291C"
RED_HOVER = "#B01E0A"
ABSOLUTE_BLACK = "#000000"
DARK_SURFACE = "#303030"
PURE_WHITE = "#FFFFFF"
MID_GRAY = "#8F8F8F"
SILVER_GRAY = "#969696"
BORDER_GRAY = "#CCCCCC"
RADIUS = 2 # Razor-sharp engineering precision

# CustomTkinter 기본 설정: 페라리의 시네마틱 다크 느낌을 극대화
ctk.set_appearance_mode("dark")

class StdoutRedirector(io.StringIO):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def write(self, s):
        # 파이썬 input의 프롬프트 문구 제거
        if any(x in s for x in ['네이버 로그인 ID를 입력하세요', '비밀번호를 입력하세요', '검색할 키워드를 입력하세요', '신청할까요?']):
            return
        if s.strip() or s == '\n':
            self.log_queue.put(s)
            
    def flush(self):
        pass

class PremiumAutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NAVER NEIGHBOR AUTO-BOT | FERRARI EDITION")
        self.geometry("600x750")
        self.resizable(False, False)
        
        # Absolute Black 바탕 적용
        self.configure(fg_color=ABSOLUTE_BLACK)
        
        self.log_queue = queue.Queue()

        # --- 상단 타이틀 (Header) ---
        self.title_label = ctk.CTkLabel(
            self, 
            text="NAVER NEIGHBOR AUTO-BOT", 
            font=ctk.CTkFont(family="Helvetica", size=24, weight="bold"),
            text_color=PURE_WHITE
        )
        self.title_label.pack(pady=(30, 5))
        
        # Subtitle (Body-Font uppercase 레이블 톤)
        self.subtitle_label = ctk.CTkLabel(
            self, 
            text="A U T O M A T I C   C O N N E C T I O N   S Y S T E M", 
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color=MID_GRAY
        )
        self.subtitle_label.pack(pady=(0, 30))

        # --- 메인 프레임 (입력 구역) ---
        self.main_frame = ctk.CTkFrame(self, fg_color=ABSOLUTE_BLACK)
        self.main_frame.pack(pady=10, padx=40, fill="both", expand=True)

        # 항목들 (모두 대문자형 레이블)
        def create_entry(parent, label_text, placeholder, show=None):
            lbl = ctk.CTkLabel(
                parent, 
                text=label_text, 
                font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"),
                text_color=MID_GRAY
            )
            lbl.pack(anchor="w", pady=(5, 2))
            
            ent = ctk.CTkEntry(
                parent, 
                placeholder_text=placeholder,
                show=show,
                width=520, 
                height=44, 
                fg_color=ABSOLUTE_BLACK,
                text_color=PURE_WHITE,
                placeholder_text_color=SILVER_GRAY,
                border_color=BORDER_GRAY,
                border_width=1,
                corner_radius=RADIUS
            )
            ent.pack(pady=(0, 20))
            return ent

        self.id_entry = create_entry(self.main_frame, "NAVER ID", "Enter your Naver ID")
        self.pw_entry = create_entry(self.main_frame, "PASSWORD", "Enter your Password", show="●")
        self.kw_entry = create_entry(self.main_frame, "SEARCH KEYWORD", "e.g. 재테크, 일상, 맛집")
        self.count_entry = create_entry(self.main_frame, "TARGET COUNT", "e.g. 50")

        # --- 강력한 실행 버튼 (Ferrari Red) ---
        self.start_button = ctk.CTkButton(
            self.main_frame, 
            text="🚀 START AUTOMATION", 
            font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
            height=44,
            fg_color=FERRARI_RED,
            hover_color=RED_HOVER,
            text_color=PURE_WHITE,
            corner_radius=RADIUS,
            command=self.start_automation
        )
        self.start_button.pack(fill="x", pady=(10, 0))

        # --- 콘솔 로그 출력창 ---
        self.console_label = ctk.CTkLabel(
            self.main_frame, 
            text="SYSTEM LOGS", 
            font=ctk.CTkFont(family="Helvetica", size=11, weight="bold"),
            text_color=MID_GRAY
        )
        self.console_label.pack(anchor="w", pady=(30, 5))

        self.console = ctk.CTkTextbox(
            self.main_frame, 
            width=520, 
            height=160, 
            state="disabled", 
            fg_color=DARK_SURFACE, 
            text_color=PURE_WHITE,
            border_color=BORDER_GRAY,
            border_width=1,
            corner_radius=RADIUS
        )
        self.console.pack(fill="x")

        self.check_queue()

    def write_log(self, text):
        self.console.configure(state="normal")
        self.console.insert("end", text)
        self.console.see("end")
        self.console.configure(state="disabled")

    def check_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.write_log(msg)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_queue)

    def start_automation(self):
        v_id = self.id_entry.get().strip()
        v_pw = self.pw_entry.get().strip()
        kw = self.kw_entry.get().strip()
        count = self.count_entry.get().strip()

        if not all([v_id, v_pw, kw, count]):
            self.write_log("[SYSTEM] ⚠️ ALL FIELDS ARE REQUIRED!\n")
            return
        
        if not count.isdigit():
            self.write_log("[SYSTEM] ⚠️ TARGET COUNT MUST BE A NUMBER!\n")
            return

        self.start_button.configure(state="disabled", text="EXECUTING...")
        self.write_log("[SYSTEM] ✨ LAUNCHING NAVER AUTOMATION SYSTEM...\n")
        
        thread = threading.Thread(target=self.run_embedded_script, args=(v_id, v_pw, kw, count), daemon=True)
        thread.start()

    def run_embedded_script(self, v_id, v_pw, kw, count):
        script_name = "GUI.py"
        
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        script_path = os.path.join(base_dir, script_name)

        if not os.path.exists(script_path):
            self.log_queue.put(f"[SYSTEM] ❌ FILE NOT FOUND: {script_name} ({script_path})\n")
            self.after(0, lambda: self.start_button.configure(state="normal", text="🚀 RE-START AUTOMATION"))
            return

        out_redirector = StdoutRedirector(self.log_queue)
        original_stdout = sys.stdout
        original_input = builtins.input

        input_list = [v_id, v_pw, kw, count]
        input_iter = iter(input_list)

        def mock_input(prompt=""):
            try:
                return next(input_iter)
            except StopIteration:
                return ""

        sys.stdout = out_redirector
        builtins.input = mock_input

        try:
            with open(script_path, "r", encoding="utf-8") as f:
                code_obj = compile(f.read(), script_path, 'exec')
            exec_globals = {"__name__": "__main__", "__file__": script_path}
            exec(code_obj, exec_globals)
            self.log_queue.put(f"\n[SYSTEM] ✅ ALL TASKS COMPLETED SUCCESSFULLY.\n")
        except Exception as e:
            self.log_queue.put(f"\n[SYSTEM] ❌ ERROR ENCOUNTERED: {e}\n")
        finally:
            sys.stdout = original_stdout
            builtins.input = original_input
            self.after(0, lambda: self.start_button.configure(state="normal", text="🚀 RE-START AUTOMATION"))

if __name__ == "__main__":
    app = PremiumAutomationApp()
    app.mainloop()
