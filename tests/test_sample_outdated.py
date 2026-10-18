import io
import unittest
from unittest.mock import patch

from sample_outdated import iter_stale_candidates, main, parse_args


class TestParseArgs(unittest.TestCase):
    def test_default_count_is_20(self):
        args = parse_args([])
        self.assertEqual(args.count, 20)

    def test_custom_count(self):
        args = parse_args(["-n", "5"])
        self.assertEqual(args.count, 5)


class TestMain(unittest.TestCase):
    @patch("sample_outdated.has_pending_request", return_value=False)
    @patch("sample_outdated.check_package")
    @patch("sample_outdated.iter_stale_candidates")
    @patch("sample_outdated.cli_tools_installed", return_value=True)
    def test_streams_found_packages_and_stops_at_count(
        self, mock_cli, mock_candidates, mock_check, mock_has_pending
    ):
        mock_candidates.return_value = ["pkg1", "pkg2", "pkg3"]
        mock_check.side_effect = [
            {"version": "1.0", "upstream_version": "2.0", "upstream_newer": True},
            {"version": "2.0", "upstream_version": "3.0", "upstream_newer": True},
            {"version": "3.0", "upstream_version": "4.0", "upstream_newer": True},
        ]
        out = io.StringIO()
        err = io.StringIO()
        with patch("sys.stdout", out), patch("sys.stderr", err):
            ret = main(["-n", "2"])

        self.assertEqual(ret, 0)
        self.assertEqual(mock_check.call_count, 2)
        stdout_val = out.getvalue()
        self.assertEqual(stdout_val, "pkg1: 1.0 -> 2.0\npkg2: 2.0 -> 3.0\n")

    @patch("sample_outdated.iter_stale_candidates", return_value=[])
    @patch("sample_outdated.cli_tools_installed", return_value=True)
    def test_no_outdated_candidates(self, mock_cli, mock_candidates):
        out = io.StringIO()
        err = io.StringIO()
        with patch("sys.stdout", out), patch("sys.stderr", err):
            ret = main(["-n", "5"])

        self.assertEqual(ret, 0)
        self.assertIn("No outdated candidates found.", out.getvalue())


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
