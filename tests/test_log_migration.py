import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logs


class LogMigrationTests(unittest.TestCase):
    def test_migrates_latest_five_converter_text_logs_removes_all_converter_text_logs_and_preserves_unrelated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            current = folder / "smuggyconverter.log"
            current.write_text("current\n", encoding="utf-8")
            legacy = []
            for index in range(6):
                path = folder / f"smuggyconverter.log.2026-10-0{index + 1}.txt"
                path.write_text(f"legacy-{index}\n", encoding="utf-8")
                os.utime(path, (index + 1, index + 1))
                legacy.append(path)
            unrelated = folder / "support-note.txt"
            unrelated.write_text("leave me\n", encoding="utf-8")

            merged = logs.migrate_legacy_text_logs(folder, current)

            self.assertEqual(merged, legacy[-5:])
            self.assertEqual(current.read_text(encoding="utf-8"), "current\nlegacy-1\nlegacy-2\nlegacy-3\nlegacy-4\nlegacy-5\n")
            self.assertFalse(legacy[0].exists())
            self.assertTrue(unrelated.exists())


if __name__ == "__main__":
    unittest.main()
