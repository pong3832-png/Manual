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


class FakeEditorReadyDriver:
    def __init__(self):
        self.current_url = main_mod.TISTORY_NEW_POST_URL
        self.scripts = []

    def find_elements(self, by, value):
        return [object()]

    def execute_script(self, script):
        self.scripts.append(script)
        if script.startswith("return "):
            return False
        return None


class FakeManualLoginHomeDriver:
    def __init__(self):
        self.current_url = ""
        self.visited_urls = []
        self.window_handles = ["main"]
        self.switch_to = self
        self._newpost_visits = 0

    def window(self, handle):
        return None

    def get(self, url):
        self.visited_urls.append(url)
        if "manage/newpost" in url:
            self._newpost_visits += 1
            if self._newpost_visits == 1:
                self.current_url = "https://accounts.kakao.com/login"
            else:
                self.current_url = main_mod.TISTORY_NEW_POST_URL
            return
        if url == main_mod.TISTORY_URL:
            self.current_url = "https://www.tistory.com/"
            return
        self.current_url = url

    def find_elements(self, by, value):
        if value == main_mod.TISTORY_TITLE_XPATH and "manage/newpost" in self.current_url:
            return [object()]
        return []

    def find_element(self, by, value):
        if value == main_mod.TISTORY_TITLE_XPATH and "manage/newpost" in self.current_url:
            return object()
        raise Exception("not found")


class FakeActionChains:
    sent_keys = []

    def __init__(self, driver):
        self.driver = driver

    def send_keys(self, key):
        self.sent_keys.append(key)
        return self

    def perform(self):
        return None


class FakeAlert:
    def __init__(self, text):
        self.text = text
        self.accepted = False
        self.dismissed = False

    def accept(self):
        self.accepted = True

    def dismiss(self):
        self.dismissed = True


class FakeAlertDriver:
    def __init__(self, text):
        self.alert = FakeAlert(text)
        self.switch_to = self


class FakeSaveSessionDriver:
    def __init__(self):
        self.visited_urls = []

    def get(self, url):
        self.visited_urls.append(url)


class FakeSessionMarker:
    def __init__(self):
        self.text = ""
        self.unlinked = False

    def exists(self):
        return True

    def unlink(self):
        self.unlinked = True

    def write_text(self, text, encoding="utf-8"):
        self.text = text


class TistorySessionLoginFlowTests(unittest.TestCase):
    def test_tistory_login_only_preserves_existing_session_directory(self):
        original_reset = main_mod._reset_browser_session_dir
        original_create_driver = main_mod.create_driver
        original_login = main_mod.login_and_open_tistory_editor
        original_quit = main_mod.quit_driver
        original_has_session = main_mod._has_saved_tistory_session
        original_marker = main_mod.TISTORY_SESSION_MARKER
        reset_calls = []
        driver = FakeSaveSessionDriver()

        try:
            main_mod._reset_browser_session_dir = lambda path: reset_calls.append(path)
            main_mod.create_driver = lambda *_args, **_kwargs: driver
            main_mod.login_and_open_tistory_editor = lambda *_args, **_kwargs: None
            main_mod.quit_driver = lambda *_args, **_kwargs: None
            main_mod._has_saved_tistory_session = lambda: True
            main_mod.TISTORY_SESSION_MARKER = FakeSessionMarker()

            with patch("builtins.input", return_value=""):
                main_mod._save_tistory_session_once(attempt=1)

            self.assertEqual([], reset_calls)
        finally:
            main_mod._reset_browser_session_dir = original_reset
            main_mod.create_driver = original_create_driver
            main_mod.login_and_open_tistory_editor = original_login
            main_mod.quit_driver = original_quit
            main_mod._has_saved_tistory_session = original_has_session
            main_mod.TISTORY_SESSION_MARKER = original_marker

    def test_main_tistory_new_post_url_is_direct_editor_url(self):
        self.assertEqual(
            "https://daniever2217.tistory.com/manage/newpost/",
            main_mod.TISTORY_NEW_POST_URL,
        )

    def test_tistory_editor_entry_alert_defaults_to_dismiss(self):
        original_wait = main_mod.WebDriverWait
        driver = FakeAlertDriver("작성 중인 글이 있습니다.")

        class ImmediateAlertWait:
            def __init__(self, *_args, **_kwargs):
                pass

            def until(self, _condition):
                return True

        try:
            main_mod.WebDriverWait = ImmediateAlertWait

            main_mod._handle_tistory_editor_alert(driver)

            self.assertTrue(driver.alert.dismissed)
            self.assertFalse(driver.alert.accepted)
        finally:
            main_mod.WebDriverWait = original_wait

    def test_manual_login_home_redirects_directly_to_new_post_url(self):
        original_handle_alert = main_mod._handle_tistory_editor_alert
        original_dismiss_popup = main_mod._dismiss_tistory_continue_draft_popup_with_escape
        original_random_sleep = main_mod.random_sleep
        original_sleep = main_mod.time.sleep
        driver = FakeManualLoginHomeDriver()

        try:
            main_mod._handle_tistory_editor_alert = lambda *_args, **_kwargs: None
            main_mod._dismiss_tistory_continue_draft_popup_with_escape = lambda *_args, **_kwargs: False
            main_mod.random_sleep = lambda *_args, **_kwargs: None
            main_mod.time.sleep = lambda *_args, **_kwargs: None

            main_mod.login_and_open_tistory_editor(driver, allow_manual_login=True)

            self.assertGreaterEqual(driver.visited_urls.count(main_mod.TISTORY_NEW_POST_URL), 2)
            self.assertEqual(main_mod.TISTORY_NEW_POST_URL, driver.current_url)
        finally:
            main_mod._handle_tistory_editor_alert = original_handle_alert
            main_mod._dismiss_tistory_continue_draft_popup_with_escape = original_dismiss_popup
            main_mod.random_sleep = original_random_sleep
            main_mod.time.sleep = original_sleep

    def test_scheduled_full_flow_checks_tistory_before_chatgpt_driver(self):
        original_preflight = getattr(main_mod, "_ensure_tistory_saved_session_ready_for_scheduled_run", None)
        original_create_driver = main_mod.create_driver

        try:
            main_mod._ensure_tistory_saved_session_ready_for_scheduled_run = lambda: (_ for _ in ()).throw(
                RuntimeError("preflight stopped")
            )
            main_mod.create_driver = lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("ChatGPT driver should not start before Tistory preflight")
            )

            with self.assertRaisesRegex(RuntimeError, "preflight stopped"):
                main_mod.run_full_flow(
                    publish=False,
                    post_type="daily",
                    keep_browser_on_error=False,
                )
        finally:
            if original_preflight is None:
                try:
                    delattr(main_mod, "_ensure_tistory_saved_session_ready_for_scheduled_run")
                except AttributeError:
                    pass
            else:
                main_mod._ensure_tistory_saved_session_ready_for_scheduled_run = original_preflight
            main_mod.create_driver = original_create_driver

    def test_scheduled_tistory_preflight_raises_when_saved_session_requires_login(self):
        original_create_driver = main_mod.create_driver
        original_quit_driver = main_mod.quit_driver
        original_handle_alert = main_mod._handle_tistory_editor_alert
        original_dismiss_popup = main_mod._dismiss_tistory_continue_draft_popup_with_escape
        original_random_sleep = main_mod.random_sleep
        original_recovery_seconds = getattr(main_mod, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS", None)
        original_has_session = main_mod._has_saved_tistory_session
        quit_calls = []
        driver = FakeTistoryLoginDriver()

        try:
            main_mod.create_driver = lambda *_args, **_kwargs: driver
            main_mod.quit_driver = lambda quit_driver, keep_browser=False: quit_calls.append((quit_driver, keep_browser))
            main_mod._handle_tistory_editor_alert = lambda *_args, **_kwargs: None
            main_mod._dismiss_tistory_continue_draft_popup_with_escape = lambda *_args, **_kwargs: False
            main_mod.random_sleep = lambda *_args, **_kwargs: None
            main_mod._has_saved_tistory_session = lambda: True
            main_mod.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = 0

            with self.assertRaisesRegex(RuntimeError, "티스토리 저장 세션.*다시 저장"):
                main_mod._ensure_tistory_saved_session_ready_for_scheduled_run()

            self.assertEqual([(driver, False)], quit_calls)
        finally:
            main_mod.create_driver = original_create_driver
            main_mod.quit_driver = original_quit_driver
            main_mod._handle_tistory_editor_alert = original_handle_alert
            main_mod._dismiss_tistory_continue_draft_popup_with_escape = original_dismiss_popup
            main_mod.random_sleep = original_random_sleep
            main_mod._has_saved_tistory_session = original_has_session
            if original_recovery_seconds is None:
                delattr(main_mod, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS")
            else:
                main_mod.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = original_recovery_seconds

    def test_continue_draft_popup_cleanup_waits_two_seconds_before_escape(self):
        original_action_chains = main_mod.ActionChains
        original_sleep = main_mod.time.sleep
        original_random_sleep = main_mod.random_sleep
        sleep_calls = []
        driver = FakeEditorReadyDriver()
        FakeActionChains.sent_keys = []

        try:
            main_mod.ActionChains = FakeActionChains
            main_mod.time.sleep = lambda seconds: sleep_calls.append(seconds)
            main_mod.random_sleep = lambda *_args, **_kwargs: None

            dismissed = main_mod._dismiss_tistory_continue_draft_popup_with_escape(driver)

            self.assertTrue(dismissed)
            self.assertEqual([2.0], sleep_calls)
            self.assertEqual([main_mod.Keys.ESCAPE], FakeActionChains.sent_keys)
        finally:
            main_mod.ActionChains = original_action_chains
            main_mod.time.sleep = original_sleep
            main_mod.random_sleep = original_random_sleep

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

    def test_api_rate_limit_failure_stops_lookup_immediately(self):
        seed_rows = [
            {"상품명": "제습기 첫번째", "키워드": "제습기"},
            {"상품명": "제습기 두번째", "키워드": "제습기"},
        ]
        calls = []
        supplemental_called = []

        def fake_enrich(products, **_kwargs):
            calls.append(products[0]["상품명"])
            raise RuntimeError("쿠팡 API 오류: 검색 API의 시간당 사용 횟수 를 초과했습니다.")

        topic, *patches = self._patch_coupang_selection_context(
            seed_rows,
            fake_enrich,
            supplemental_func=lambda _topic: supplemental_called.append(True) or [{"상품명": "보강 후보"}],
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            with self.assertRaisesRegex(RuntimeError, "시간당 사용 횟수"):
                main_mod.prepare_coupang_api_products(
                    count=3,
                    performance_topic=topic,
                )

        self.assertEqual(["제습기 첫번째"], calls)
        self.assertEqual([], supplemental_called)


if __name__ == "__main__":
    unittest.main()
