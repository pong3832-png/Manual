from pathlib import Path

path = Path("main_golf.py")
text = path.read_text(encoding="utf-8")

broken = '''    print("[오류] 이미지 base64 변환 최종 실패 — 이미지 없이 계속합니다.")
    return ""

    except Exception as e:
        print(f"[경고] 이미지 Base64 다운로드 오류: {e}")
        return ""
'''

fixed = '''    print("[오류] 이미지 base64 변환 최종 실패 — 이미지 없이 계속합니다.")
    return ""
'''

if broken not in text:
    print("[ERROR] 제거 대상 코드 블록을 찾지 못했습니다.")
    raise SystemExit(1)

path.write_text(text.replace(broken, fixed), encoding="utf-8")
print("[OK] 잘못 남은 except 블록 제거 완료")
