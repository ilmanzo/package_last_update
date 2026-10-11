import unittest
from unittest.mock import patch

from sample_outdated import iter_stale_candidates


class TestIterStaleCandidates(unittest.TestCase):
    @patch("sample_outdated.in_age_window")
    @patch("sample_outdated.list_packages")
    def test_yields_only_in_window(self, list_packages, in_age_window):
        list_packages.return_value = ["a", "b", "c", "d", "e"]
        # a,c,e in window; b,d outside (too fresh or too old)
        in_age_window.side_effect = lambda osc, proj, pkg, oldest, newest: pkg in ("a", "c", "e")
        result = list(iter_stale_candidates(["osc"], "openSUSE:Factory", 60, 730))
        self.assertEqual({"a", "c", "e"}, set(result))
        self.assertEqual(3, len(result))

    @patch("sample_outdated.in_age_window")
    @patch("sample_outdated.list_packages")
    def test_none_in_window(self, list_packages, in_age_window):
        list_packages.return_value = ["a", "b"]
        in_age_window.return_value = False
        result = list(iter_stale_candidates(["osc"], "openSUSE:Factory", 60, 730))
        self.assertEqual([], result)


if __name__ == "__main__":
    unittest.main()
