import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_GOLF_PATH = PROJECT_ROOT / "golf" / "main_golf.py"

spec = importlib.util.spec_from_file_location("main_golf_mod", MAIN_GOLF_PATH)
main_golf = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = main_golf
spec.loader.exec_module(main_golf)


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

    @property
    def current_url(self):
        if "accounts.kakao.com" in self._current_url:
            self.current_url_reads += 1
            if self.current_url_reads >= self.auto_redirect_after_reads:
                self._current_url = main_golf.TISTORY_NEW_POST_URL
        return self._current_url

    @current_url.setter
    def current_url(self, value):
        self._current_url = value

    def get(self, url):
        self.visited_urls.append(url)
        if "manage/newpost" in url:
            self._current_url = "https://accounts.kakao.com/login"
        else:
            self._current_url = url

    def find_elements(self, by, value):
        if "manage/newpost" in self.current_url and "jxbooklove.tistory.com" in self.current_url:
            return [object()]
        return []

    def find_element(self, by, value):
        if "manage/newpost" in self.current_url and "jxbooklove.tistory.com" in self.current_url:
            return object()
        raise Exception("not found")


class FakeEditorReadyDriver:
    def __init__(self):
        self.current_url = main_golf.TISTORY_NEW_POST_URL
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
        self._newpost_visits = 0

    def get(self, url):
        self.visited_urls.append(url)
        if "manage/newpost" in url:
            self._newpost_visits += 1
            if self._newpost_visits == 1:
                self.current_url = "https://accounts.kakao.com/login"
            else:
                self.current_url = main_golf.TISTORY_NEW_POST_URL
            return
        if url == main_golf.TISTORY_URL:
            self.current_url = "https://www.tistory.com/"
            return
        self.current_url = url

    def find_elements(self, by, value):
        if value == main_golf.TISTORY_TITLE_XPATH and "manage/newpost" in self.current_url:
            return [object()]
        return []

    def find_element(self, by, value):
        if value == main_golf.TISTORY_TITLE_XPATH and "manage/newpost" in self.current_url:
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


class MainGolfRuntimeGuardTests(unittest.TestCase):
    def test_tistory_login_only_preserves_existing_session_directory(self):
        original_reset = main_golf._reset_browser_session_dir
        original_create_driver = main_golf.create_driver
        original_login = main_golf.login_and_open_tistory_editor
        original_quit = main_golf.quit_driver
        original_has_session = main_golf._has_saved_tistory_session
        original_marker = main_golf.TISTORY_SESSION_MARKER
        reset_calls = []
        driver = FakeSaveSessionDriver()

        try:
            main_golf._reset_browser_session_dir = lambda path: reset_calls.append(path)
            main_golf.create_driver = lambda *_args, **_kwargs: driver
            main_golf.login_and_open_tistory_editor = lambda *_args, **_kwargs: None
            main_golf.quit_driver = lambda *_args, **_kwargs: None
            main_golf._has_saved_tistory_session = lambda: True
            main_golf.TISTORY_SESSION_MARKER = FakeSessionMarker()

            with patch("builtins.input", return_value=""):
                main_golf._save_tistory_session_once(attempt=1)

            self.assertEqual([], reset_calls)
        finally:
            main_golf._reset_browser_session_dir = original_reset
            main_golf.create_driver = original_create_driver
            main_golf.login_and_open_tistory_editor = original_login
            main_golf.quit_driver = original_quit
            main_golf._has_saved_tistory_session = original_has_session
            main_golf.TISTORY_SESSION_MARKER = original_marker

    def test_golf_uses_separate_tistory_session_directory(self):
        self.assertEqual("tistory_golf", main_golf.TISTORY_SESSION_DIR.name)

    def test_golf_tistory_new_post_url_is_direct_editor_url(self):
        self.assertEqual(
            "https://jxbooklove.tistory.com/manage/newpost/",
            main_golf.TISTORY_NEW_POST_URL,
        )

    def test_tistory_editor_entry_alert_defaults_to_dismiss(self):
        original_wait = main_golf.WebDriverWait
        driver = FakeAlertDriver("작성 중인 글이 있습니다.")

        class ImmediateAlertWait:
            def __init__(self, *_args, **_kwargs):
                pass

            def until(self, _condition):
                return True

        try:
            main_golf.WebDriverWait = ImmediateAlertWait

            main_golf._handle_tistory_editor_alert(driver)

            self.assertTrue(driver.alert.dismissed)
            self.assertFalse(driver.alert.accepted)
        finally:
            main_golf.WebDriverWait = original_wait

    def test_manual_login_home_redirects_directly_to_new_post_url(self):
        original_handle_alert = main_golf._handle_tistory_editor_alert
        original_dismiss_popup = main_golf._dismiss_tistory_continue_draft_popup_with_escape
        original_random_sleep = main_golf.random_sleep
        original_sleep = main_golf.time.sleep
        driver = FakeManualLoginHomeDriver()

        try:
            main_golf._handle_tistory_editor_alert = lambda *_args, **_kwargs: None
            main_golf._dismiss_tistory_continue_draft_popup_with_escape = lambda *_args, **_kwargs: False
            main_golf.random_sleep = lambda *_args, **_kwargs: None
            main_golf.time.sleep = lambda *_args, **_kwargs: None

            main_golf.login_and_open_tistory_editor(driver, allow_manual_login=True)

            self.assertGreaterEqual(driver.visited_urls.count(main_golf.TISTORY_NEW_POST_URL), 2)
            self.assertEqual(main_golf.TISTORY_NEW_POST_URL, driver.current_url)
        finally:
            main_golf._handle_tistory_editor_alert = original_handle_alert
            main_golf._dismiss_tistory_continue_draft_popup_with_escape = original_dismiss_popup
            main_golf.random_sleep = original_random_sleep
            main_golf.time.sleep = original_sleep

    def test_scheduled_full_flow_checks_tistory_before_chatgpt_driver(self):
        original_preflight = getattr(main_golf, "_ensure_tistory_saved_session_ready_for_scheduled_run", None)
        original_create_driver = main_golf.create_driver

        try:
            main_golf._ensure_tistory_saved_session_ready_for_scheduled_run = lambda: (_ for _ in ()).throw(
                RuntimeError("preflight stopped")
            )
            main_golf.create_driver = lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("ChatGPT driver should not start before Tistory preflight")
            )

            with self.assertRaisesRegex(RuntimeError, "preflight stopped"):
                main_golf.run_full_flow(
                    publish=False,
                    post_type="golf",
                    keep_browser_on_error=False,
                )
        finally:
            if original_preflight is None:
                try:
                    delattr(main_golf, "_ensure_tistory_saved_session_ready_for_scheduled_run")
                except AttributeError:
                    pass
            else:
                main_golf._ensure_tistory_saved_session_ready_for_scheduled_run = original_preflight
            main_golf.create_driver = original_create_driver

    def test_scheduled_tistory_preflight_raises_when_saved_session_requires_login(self):
        original_create_driver = main_golf.create_driver
        original_quit_driver = main_golf.quit_driver
        original_handle_alert = main_golf._handle_tistory_editor_alert
        original_dismiss_popup = main_golf._dismiss_tistory_continue_draft_popup_with_escape
        original_random_sleep = main_golf.random_sleep
        original_recovery_seconds = getattr(main_golf, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS", None)
        original_has_session = main_golf._has_saved_tistory_session
        quit_calls = []
        driver = FakeTistoryLoginDriver()

        try:
            main_golf.create_driver = lambda *_args, **_kwargs: driver
            main_golf.quit_driver = lambda quit_driver, keep_browser=False: quit_calls.append((quit_driver, keep_browser))
            main_golf._handle_tistory_editor_alert = lambda *_args, **_kwargs: None
            main_golf._dismiss_tistory_continue_draft_popup_with_escape = lambda *_args, **_kwargs: False
            main_golf.random_sleep = lambda *_args, **_kwargs: None
            main_golf._has_saved_tistory_session = lambda: True
            main_golf.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = 0

            with self.assertRaisesRegex(RuntimeError, "티스토리 저장 세션.*다시 저장"):
                main_golf._ensure_tistory_saved_session_ready_for_scheduled_run()

            self.assertEqual([(driver, False)], quit_calls)
        finally:
            main_golf.create_driver = original_create_driver
            main_golf.quit_driver = original_quit_driver
            main_golf._handle_tistory_editor_alert = original_handle_alert
            main_golf._dismiss_tistory_continue_draft_popup_with_escape = original_dismiss_popup
            main_golf.random_sleep = original_random_sleep
            main_golf._has_saved_tistory_session = original_has_session
            if original_recovery_seconds is None:
                delattr(main_golf, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS")
            else:
                main_golf.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = original_recovery_seconds

    def test_continue_draft_popup_cleanup_waits_two_seconds_before_escape(self):
        original_action_chains = main_golf.ActionChains
        original_sleep = main_golf.time.sleep
        original_random_sleep = main_golf.random_sleep
        sleep_calls = []
        driver = FakeEditorReadyDriver()
        FakeActionChains.sent_keys = []

        try:
            main_golf.ActionChains = FakeActionChains
            main_golf.time.sleep = lambda seconds: sleep_calls.append(seconds)
            main_golf.random_sleep = lambda *_args, **_kwargs: None

            dismissed = main_golf._dismiss_tistory_continue_draft_popup_with_escape(driver)

            self.assertTrue(dismissed)
            self.assertEqual([2.0], sleep_calls)
            self.assertEqual([main_golf.Keys.ESCAPE], FakeActionChains.sent_keys)
        finally:
            main_golf.ActionChains = original_action_chains
            main_golf.time.sleep = original_sleep
            main_golf.random_sleep = original_random_sleep

    def test_golf_validation_allows_price_uncertainty_warning(self):
        html_body = (
            "<p>"
            "\ud655\uc815 \uac00\uaca9\uc774 \uc544\ub2c8\ub77c "
            "\uc608\uc0c1 \ubc94\uc704\ub85c \ubcf4\uace0 \uc608\uc57d\ucc98\uc5d0\uc11c "
            "\ub2e4\uc2dc \ud655\uc778\ud574\uc57c \ud569\ub2c8\ub2e4."
            "</p>"
        )

        main_golf.validate_golf_generated_content(html_body)

    def test_golf_validation_rejects_fixed_price_claim(self):
        html_body = "<p>\ud655\uc815 \uac00\uaca9: 7500000VND</p>"

        with self.assertRaisesRegex(ValueError, "\ud655\uc815 \uac00\uaca9"):
            main_golf.validate_golf_generated_content(html_body)

    def test_scheduled_tistory_flow_fails_fast_when_saved_session_requires_login(self):
        original_handle_alert = main_golf._handle_tistory_editor_alert
        original_dismiss_popup = main_golf._dismiss_tistory_continue_draft_popup_with_escape
        original_random_sleep = main_golf.random_sleep
        original_recovery_seconds = getattr(main_golf, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS", None)

        driver = FakeTistoryLoginDriver()

        try:
            main_golf._handle_tistory_editor_alert = lambda *_args, **_kwargs: None
            main_golf._dismiss_tistory_continue_draft_popup_with_escape = lambda *_args, **_kwargs: False
            main_golf.random_sleep = lambda *_args, **_kwargs: None
            main_golf.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = 0

            with self.assertRaisesRegex(RuntimeError, "티스토리 저장 세션.*다시 저장"):
                main_golf.login_and_open_tistory_editor(driver, allow_manual_login=False)

            self.assertNotIn(main_golf.TISTORY_URL, driver.visited_urls)
        finally:
            main_golf._handle_tistory_editor_alert = original_handle_alert
            main_golf._dismiss_tistory_continue_draft_popup_with_escape = original_dismiss_popup
            main_golf.random_sleep = original_random_sleep
            if original_recovery_seconds is None:
                delattr(main_golf, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS")
            else:
                main_golf.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = original_recovery_seconds

    def test_scheduled_tistory_flow_allows_saved_session_auto_redirect(self):
        original_handle_alert = main_golf._handle_tistory_editor_alert
        original_dismiss_popup = main_golf._dismiss_tistory_continue_draft_popup_with_escape
        original_random_sleep = main_golf.random_sleep
        original_sleep = main_golf.time.sleep
        original_recovery_seconds = getattr(main_golf, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS", None)

        driver = FakeTistoryAutoRecoverDriver(auto_redirect_after_reads=4)

        try:
            main_golf._handle_tistory_editor_alert = lambda *_args, **_kwargs: None
            main_golf._dismiss_tistory_continue_draft_popup_with_escape = lambda *_args, **_kwargs: False
            main_golf.random_sleep = lambda *_args, **_kwargs: None
            main_golf.time.sleep = lambda *_args, **_kwargs: None
            main_golf.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = 5

            main_golf.login_and_open_tistory_editor(driver, allow_manual_login=False)

            self.assertNotIn(main_golf.TISTORY_URL, driver.visited_urls)
            self.assertIn(main_golf.TISTORY_NEW_POST_URL, driver.visited_urls)
        finally:
            main_golf._handle_tistory_editor_alert = original_handle_alert
            main_golf._dismiss_tistory_continue_draft_popup_with_escape = original_dismiss_popup
            main_golf.random_sleep = original_random_sleep
            main_golf.time.sleep = original_sleep
            if original_recovery_seconds is None:
                delattr(main_golf, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS")
            else:
                main_golf.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = original_recovery_seconds

    def test_chromedriver_candidates_prefer_current_chrome_major(self):
        current_major = main_golf._get_installed_chrome_major()
        if not current_major:
            self.skipTest("installed Chrome major version not detected")

        candidates = main_golf._candidate_chromedriver_paths()
        matching = [path for path in candidates if f"\\{current_major}." in str(path)]
        if not matching:
            self.skipTest(f"no cached ChromeDriver for Chrome {current_major}")

        self.assertIn(f"\\{current_major}.", str(candidates[0]))


class MainGolfHealthProductSelectionTests(unittest.TestCase):
    def test_health_api_rate_limit_failure_raises_clear_stop_message(self):
        seed_rows = [
            {"상품명": "단백질 첫번째", "키워드": "단백질"},
            {"상품명": "단백질 두번째", "키워드": "단백질"},
        ]
        calls = []

        def fake_enrich(products, **_kwargs):
            calls.append(products[0]["상품명"])
            raise RuntimeError("쿠팡 API 오류: 검색 API의 시간당 사용 횟수 를 초과했습니다.")

        with (
            patch.object(main_golf, "COUPANG_API_ENABLED", True),
            patch.object(main_golf, "COUPANG_ACCESS_KEY", "test-access"),
            patch.object(main_golf, "COUPANG_SECRET_KEY", "test-secret"),
            patch.object(main_golf, "HEALTH_PRODUCT_SELECTION_SCAN_LIMIT", 2),
            patch.object(main_golf, "HEALTH_PRODUCT_ENRICH_BATCH_SIZE", 1),
            patch.object(main_golf, "_health_product_db_path", return_value=Path("health.csv")),
            patch.object(main_golf, "select_products", return_value=seed_rows),
            patch.object(main_golf, "_load_used_coupang_url_keys", return_value=set()),
            patch.object(main_golf, "enrich_products_with_coupang_links", side_effect=fake_enrich),
        ):
            with self.assertRaisesRegex(RuntimeError, "시간당 사용 횟수 제한.*추가 API 조회를 중단"):
                main_golf.prepare_health_coupang_products(count=1)

        self.assertEqual(["단백질 첫번째"], calls)


if __name__ == "__main__":
    unittest.main()
