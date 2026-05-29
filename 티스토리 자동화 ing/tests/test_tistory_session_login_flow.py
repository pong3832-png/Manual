import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from tistory_automation import main as main_mod


class FakeTistoryLoginDriver:
    def __init__(self):
        self.current_url = ""
        self.visited_urls = []

    def get(self, url):
        self.visited_urls.append(url)
        if "manage/newpost" in url:
            self.current_url = "https://accounts.kakao.com/login"
        else:
            self.current_url = url

    def find_elements(self, by, value):
        return []


class FakeTistoryAutoRecoverDriver:
    def __init__(self, auto_redirect_after_reads=4):
        self._current_url = ""
        self.visited_urls = []
        self.current_url_reads = 0
        self.auto_redirect_after_reads = auto_redirect_after_reads
        self.window_handles = ["main"]
        self.switch_to = self

    @property
    def current_url(self):
        if "accounts.kakao.com" in self._current_url:
            self.current_url_reads += 1
            if self.current_url_reads >= self.auto_redirect_after_reads:
                self._current_url = main_mod.TISTORY_NEW_POST_URL
        return self._current_url

    @current_url.setter
    def current_url(self, value):
        self._current_url = value

    def window(self, handle):
        return None

    def get(self, url):
        self.visited_urls.append(url)
        if "manage/newpost" in url:
            self._current_url = "https://accounts.kakao.com/login"
        else:
            self._current_url = url

    def find_elements(self, by, value):
        if "manage/newpost" in self.current_url and "daniever2217.tistory.com" in self.current_url:
            return [object()]
        return []

    def find_element(self, by, value):
        if "manage/newpost" in self.current_url and "daniever2217.tistory.com" in self.current_url:
            return object()
        raise Exception("not found")


class TistorySessionLoginFlowTests(unittest.TestCase):
    def test_scheduled_tistory_flow_fails_fast_when_saved_session_requires_login(self):
        original_handle_alert = main_mod._handle_tistory_editor_alert
        original_dismiss_popup = main_mod._dismiss_tistory_continue_draft_popup_with_escape
        original_random_sleep = main_mod.random_sleep
        original_recovery_seconds = getattr(main_mod, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS", None)

        driver = FakeTistoryLoginDriver()

        try:
            main_mod._handle_tistory_editor_alert = lambda *_args, **_kwargs: None
            main_mod._dismiss_tistory_continue_draft_popup_with_escape = lambda *_args, **_kwargs: False
            main_mod.random_sleep = lambda *_args, **_kwargs: None
            main_mod.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = 0

            with self.assertRaisesRegex(RuntimeError, "티스토리 저장 세션.*다시 저장"):
                main_mod.login_and_open_tistory_editor(driver, allow_manual_login=False)

            self.assertNotIn(main_mod.TISTORY_URL, driver.visited_urls)
        finally:
            main_mod._handle_tistory_editor_alert = original_handle_alert
            main_mod._dismiss_tistory_continue_draft_popup_with_escape = original_dismiss_popup
            main_mod.random_sleep = original_random_sleep
            if original_recovery_seconds is None:
                delattr(main_mod, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS")
            else:
                main_mod.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = original_recovery_seconds

    def test_scheduled_tistory_flow_allows_saved_session_auto_redirect(self):
        original_handle_alert = main_mod._handle_tistory_editor_alert
        original_dismiss_popup = main_mod._dismiss_tistory_continue_draft_popup_with_escape
        original_random_sleep = main_mod.random_sleep
        original_sleep = main_mod.time.sleep
        original_recovery_seconds = getattr(main_mod, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS", None)

        driver = FakeTistoryAutoRecoverDriver(auto_redirect_after_reads=4)

        try:
            main_mod._handle_tistory_editor_alert = lambda *_args, **_kwargs: None
            main_mod._dismiss_tistory_continue_draft_popup_with_escape = lambda *_args, **_kwargs: False
            main_mod.random_sleep = lambda *_args, **_kwargs: None
            main_mod.time.sleep = lambda *_args, **_kwargs: None
            main_mod.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = 5

            main_mod.login_and_open_tistory_editor(driver, allow_manual_login=False)

            self.assertNotIn(main_mod.TISTORY_URL, driver.visited_urls)
            self.assertIn(main_mod.TISTORY_NEW_POST_URL, driver.visited_urls)
        finally:
            main_mod._handle_tistory_editor_alert = original_handle_alert
            main_mod._dismiss_tistory_continue_draft_popup_with_escape = original_dismiss_popup
            main_mod.random_sleep = original_random_sleep
            main_mod.time.sleep = original_sleep
            if original_recovery_seconds is None:
                delattr(main_mod, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS")
            else:
                main_mod.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = original_recovery_seconds


class CoupangApiProductSelectionTests(unittest.TestCase):
    def _patch_coupang_selection_context(self, seed_rows, enrich_func, supplemental_func=None):
        topic = {"query": "제습기 확인", "keyword": "제습기", "category": "가전", "match_terms": ["제습기"]}
        return (
            topic,
            patch.object(main_mod, "COUPANG_API_ENABLED", True),
            patch.object(main_mod, "COUPANG_ACCESS_KEY", "test-access"),
            patch.object(main_mod, "COUPANG_SECRET_KEY", "test-secret"),
            patch.object(main_mod, "_load_used_coupang_url_keys", return_value=set()),
            patch.object(main_mod, "_ordered_available_product_rows", return_value=seed_rows),
            patch.object(
                main_mod,
                "_topic_api_supplemental_seed_rows",
                side_effect=supplemental_func or (lambda _topic: []),
            ),
            patch.object(main_mod, "enrich_products_with_coupang_links", side_effect=enrich_func),
        )

    def test_performance_topic_stops_api_lookup_after_two_products(self):
        seed_rows = [
            {"상품명": "제습기 첫번째", "키워드": "제습기"},
            {"상품명": "제습기 두번째", "키워드": "제습기"},
            {"상품명": "제습기 세번째", "키워드": "제습기"},
        ]
        calls = []
        supplemental_called = []

        def fake_enrich(products, **_kwargs):
            calls.append(products[0]["상품명"])
            product_id = len(calls)
            return [
                {
                    **products[0],
                    "쿠팡링크": f"https://www.coupang.com/vp/products/{product_id}",
                    "API매칭방식": "keyword",
                }
            ]

        topic, *patches = self._patch_coupang_selection_context(
            seed_rows,
            fake_enrich,
            supplemental_func=lambda _topic: supplemental_called.append(True) or [],
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            selected_seed_products, selected_api_products = main_mod.prepare_coupang_api_products(
                count=3,
                performance_topic=topic,
            )

        self.assertEqual(2, len(selected_seed_products))
        self.assertEqual(2, len(selected_api_products))
        self.assertEqual(["제습기 첫번째", "제습기 두번째"], calls)
        self.assertEqual([], supplemental_called)

    def test_api_lookup_failure_skips_candidate_and_continues(self):
        seed_rows = [
            {"상품명": "제습기 실패 후보", "키워드": "제습기"},
            {"상품명": "제습기 첫번째", "키워드": "제습기"},
            {"상품명": "제습기 두번째", "키워드": "제습기"},
        ]
        calls = []

        def fake_enrich(products, **_kwargs):
            calls.append(products[0]["상품명"])
            if products[0]["상품명"] == "제습기 실패 후보":
                raise RuntimeError("temporary api failure")
            product_id = len(calls)
            return [
                {
                    **products[0],
                    "쿠팡링크": f"https://www.coupang.com/vp/products/{product_id}",
                    "API매칭방식": "keyword",
                }
            ]

        topic, *patches = self._patch_coupang_selection_context(seed_rows, fake_enrich)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            selected_seed_products, selected_api_products = main_mod.prepare_coupang_api_products(
                count=3,
                performance_topic=topic,
            )

        self.assertEqual(2, len(selected_seed_products))
        self.assertEqual(2, len(selected_api_products))
        self.assertEqual(["제습기 실패 후보", "제습기 첫번째", "제습기 두번째"], calls)


if __name__ == "__main__":
    unittest.main()
