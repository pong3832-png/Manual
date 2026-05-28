import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from tistory_automation import main as main_mod


class FakeResponseElement:
    def __init__(self, text: str):
        self.text = text


class ChatGptResponseWaitTests(unittest.TestCase):
    def test_wait_for_text_uses_latest_non_empty_candidate_when_tail_is_blank(self):
        original_get_response_elements = main_mod._get_response_elements
        original_is_chatgpt_busy = main_mod._is_chatgpt_busy
        original_wait_until_ready = main_mod._wait_until_chatgpt_ready
        original_sleep = main_mod.time.sleep

        try:
            main_mod._get_response_elements = lambda driver: [
                FakeResponseElement("old response"),
                FakeResponseElement('{"title":"나고야 숙소 위치 선택","tags":"#나고야 #사카에"}'),
                FakeResponseElement(""),
            ]
            main_mod._is_chatgpt_busy = lambda driver: False
            main_mod._wait_until_chatgpt_ready = lambda *args, **kwargs: None
            main_mod.time.sleep = lambda seconds: None

            text = main_mod._wait_for_text(
                object(),
                previous_count=1,
                timeout=0.05,
                stable_seconds=0.0,
            )

            self.assertEqual(
                text,
                '{"title":"나고야 숙소 위치 선택","tags":"#나고야 #사카에"}',
            )
        finally:
            main_mod._get_response_elements = original_get_response_elements
            main_mod._is_chatgpt_busy = original_is_chatgpt_busy
            main_mod._wait_until_chatgpt_ready = original_wait_until_ready
            main_mod.time.sleep = original_sleep


if __name__ == "__main__":
    unittest.main()
