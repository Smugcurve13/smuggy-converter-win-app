import tempfile
import unittest
from pathlib import Path
from unittest import mock

import logs


class LogExportTests(unittest.TestCase):
    def test_export_copies_only_current_log_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "smuggyconverter.log"
            source.write_text("exact log contents\n", encoding="utf-8")
            destination = Path(tmp) / "exported.log"

            with mock.patch.object(logs, "file", source):
                result = logs.export_log(destination)

            self.assertEqual(result, destination)
            self.assertEqual(destination.read_text(encoding="utf-8"), "exact log contents\n")

    def test_default_export_name_is_a_log_file(self):
        self.assertTrue(logs.default_log_path().endswith(".log"))


if __name__ == "__main__":
    unittest.main()
