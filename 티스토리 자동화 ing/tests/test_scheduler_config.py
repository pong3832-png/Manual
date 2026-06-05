import datetime as dt
import sys
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from tistory_automation import scheduler


class SchedulerPostMixTests(unittest.TestCase):
    def test_build_schedule_items_can_create_twelve_daily_drafts_without_coupang(self):
        target_date = dt.date.today() + dt.timedelta(days=1)

        items = scheduler.build_schedule_items(
            target_date,
            daily_posts=12,
            coupang_posts=0,
        )

        self.assertEqual(len(items), 12)
        self.assertEqual({item["post_type"] for item in items}, {"daily"})
        self.assertEqual([item["index"] for item in items], list(range(1, 13)))

    def test_refresh_task_preserves_daily_only_counts(self):
        commands = []

        with (
            mock.patch.object(scheduler, "delete_task_if_exists"),
            mock.patch.object(scheduler.getpass, "getuser", return_value="itwill"),
            mock.patch.object(scheduler, "run_command", side_effect=lambda command: commands.append(command)),
        ):
            scheduler.register_refresh_task(
                "00:05",
                draft=True,
                daily_posts=12,
                coupang_posts=0,
            )

        self.assertEqual(len(commands), 1)
        task_command = commands[0][commands[0].index("/TR") + 1]
        self.assertIn("-DailyPosts 12", task_command)
        self.assertIn("-CoupangPosts 0", task_command)
        self.assertIn("-Draft", task_command)


if __name__ == "__main__":
    unittest.main()
