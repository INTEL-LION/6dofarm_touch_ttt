import shutil
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from session_bag import SessionBagRecorder, list_bag_directories, sanitize_bag_name, unique_bag_directory


class SessionBagTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(".test_bags")
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.root.exists():
            shutil.rmtree(self.root)

    def test_records_servo_steps_and_writes_analysis(self):
        root = self.root
        recorder = SessionBagRecorder(root)
        paths = recorder.start(f"test_bag_{uuid.uuid4().hex}")
        recorder.record_robot_steps(
            4,
            [
                {
                    "name": "cell hover holding",
                    "angles": [90, 80, 70, 60, 50, 90],
                    "speed_percent": 50,
                    "dry_run": True,
                },
                {
                    "name": "cell release",
                    "angles": [90, 80, 70, 60, 50, 40],
                    "speed_percent": 100,
                    "dry_run": True,
                },
            ],
            "OK",
        )
        recorder.stop()

        self.assertTrue(paths.events_jsonl.exists())
        self.assertTrue(paths.servo_csv.exists())
        self.assertTrue(paths.analysis_html.exists())
        csv_text = paths.servo_csv.read_text(encoding="utf-8")
        self.assertIn("cell hover holding", csv_text)
        self.assertIn("50", csv_text)
        html_text = paths.analysis_html.read_text(encoding="utf-8")
        self.assertIn("v1.3 Bag Analysis", html_text)
        self.assertIn("yellow band = 50% speed", html_text)

    def test_bag_names_are_sanitized_and_unique(self):
        root = self.root
        self.assertEqual(sanitize_bag_name(" test:bag/01 "), "test_bag_01")
        first = unique_bag_directory(root, "named bag")
        first.mkdir(parents=True)
        second = unique_bag_directory(root, "named bag")
        self.assertEqual(second.name, "named_bag_2")

    def test_lists_existing_bag_directories(self):
        root = self.root
        bag = unique_bag_directory(root, "listed bag")
        bag.mkdir(parents=True)
        (bag / "servo_steps.csv").write_text("step,cell\n", encoding="utf-8")
        self.assertIn(bag, list_bag_directories(root))


if __name__ == "__main__":
    unittest.main()
