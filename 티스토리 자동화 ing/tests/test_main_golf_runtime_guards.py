import importlib.util
import sys
import unittest
from pathlib import Path


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


class MainGolfRuntimeGuardTests(unittest.TestCase):
    def test_scheduled_tistory_flow_fails_fast_when_saved_session_requires_login(self):
        original_handle_alert = main_golf._handle_tistory_editor_alert
        original_random_sleep = main_golf.random_sleep
        original_recovery_seconds = getattr(main_golf, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS", None)

        driver = FakeTistoryLoginDriver()

        try:
            main_golf._handle_tistory_editor_alert = lambda *_args, **_kwargs: None
            main_golf.random_sleep = lambda *_args, **_kwargs: None
            main_golf.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = 0

            with self.assertRaisesRegex(RuntimeError, "티스토리 저장 세션.*다시 저장"):
                main_golf.login_and_open_tistory_editor(driver, allow_manual_login=False)

            self.assertNotIn(main_golf.TISTORY_URL, driver.visited_urls)
        finally:
            main_golf._handle_tistory_editor_alert = original_handle_alert
            main_golf.random_sleep = original_random_sleep
            if original_recovery_seconds is None:
                delattr(main_golf, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS")
            else:
                main_golf.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = original_recovery_seconds

    def test_scheduled_tistory_flow_allows_saved_session_auto_redirect(self):
        original_handle_alert = main_golf._handle_tistory_editor_alert
        original_random_sleep = main_golf.random_sleep
        original_sleep = main_golf.time.sleep
        original_recovery_seconds = getattr(main_golf, "TISTORY_SAVED_SESSION_RECOVERY_SECONDS", None)

        driver = FakeTistoryAutoRecoverDriver(auto_redirect_after_reads=4)

        try:
            main_golf._handle_tistory_editor_alert = lambda *_args, **_kwargs: None
            main_golf.random_sleep = lambda *_args, **_kwargs: None
            main_golf.time.sleep = lambda *_args, **_kwargs: None
            main_golf.TISTORY_SAVED_SESSION_RECOVERY_SECONDS = 5

            main_golf.login_and_open_tistory_editor(driver, allow_manual_login=False)

            self.assertNotIn(main_golf.TISTORY_URL, driver.visited_urls)
            self.assertIn(main_golf.TISTORY_NEW_POST_URL, driver.visited_urls)
        finally:
            main_golf._handle_tistory_editor_alert = original_handle_alert
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


if __name__ == "__main__":
    unittest.main()
