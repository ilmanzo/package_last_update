import unittest
from unittest.mock import patch, MagicMock

import last_update
from last_update import is_numeric, filter_repo, is_newer_on_repology, anitya_upstream


class TestIsNumeric(unittest.TestCase):
    def test_numeric(self):
        self.assertTrue(is_numeric("1.2.3"))
        self.assertTrue(is_numeric("9"))

    def test_non_numeric(self):
        self.assertFalse(is_numeric("_VERSION_"))
        self.assertFalse(is_numeric("v1.2"))
        self.assertFalse(is_numeric(""))


class TestFilterRepo(unittest.TestCase):
    def test_keeps_only_newer(self):
        items = [{"version": "1.0"}, {"version": "2.0"}, {"version": "1.5"}]
        result = filter_repo(items, "1.2")
        self.assertEqual([{"version": "2.0"}, {"version": "1.5"}], result)

    def test_none_newer(self):
        items = [{"version": "1.0"}, {"version": "0.9"}]
        self.assertEqual([], filter_repo(items, "1.2"))

    def test_unparseable_reference_returns_all(self):
        items = [{"version": "1.0"}]
        self.assertEqual(items, filter_repo(items, "not-a-version"))


def _mock_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


class TestIsNewerOnRepology(unittest.TestCase):
    @patch("last_update.requests.Session")
    def test_counts_newer_numeric(self, session_cls):
        session_cls.return_value.get.return_value = _mock_response([
            {"status": "newest", "version": "2.0"},
            {"status": "newest", "version": "1.5"},
            {"status": "newest", "version": "1.0"},   # older, filtered out
            {"status": "outdated", "version": "3.0"},  # wrong status
        ])
        count, newest = is_newer_on_repology("foo", "1.2")
        self.assertEqual(2, count)
        self.assertEqual("2.0", newest)

    @patch("last_update.requests.Session")
    def test_no_newer(self, session_cls):
        session_cls.return_value.get.return_value = _mock_response([
            {"status": "newest", "version": "1.2"},   # equal to ref
        ])
        self.assertEqual((0, None), is_newer_on_repology("foo", "1.2"))

    @patch("last_update.requests.Session")
    def test_connection_error(self, session_cls):
        session_cls.return_value.get.side_effect = \
            last_update.requests.exceptions.ConnectionError("boom")
        self.assertEqual((-1, None), is_newer_on_repology("foo", "1.2"))

    @patch("last_update.requests.Session")
    def test_http_error_is_caught(self, session_cls):
        resp = MagicMock()
        resp.raise_for_status.side_effect = \
            last_update.requests.exceptions.HTTPError("429")
        session_cls.return_value.get.return_value = resp
        self.assertEqual((-1, None), is_newer_on_repology("foo", "1.2"))


class TestAnityaUpstream(unittest.TestCase):
    @patch("last_update.requests.Session")
    def test_prefers_stable_version(self, session_cls):
        session_cls.return_value.get.return_value = _mock_response({
            "items": [{"version": "1.15", "stable_version": "1.14"}],
        })
        self.assertEqual("1.14", anitya_upstream("gzip"))

    @patch("last_update.requests.Session")
    def test_falls_back_to_version(self, session_cls):
        session_cls.return_value.get.return_value = _mock_response({
            "items": [{"version": "1.14", "stable_version": None}],
        })
        self.assertEqual("1.14", anitya_upstream("gzip"))

    @patch("last_update.requests.Session")
    def test_not_tracked(self, session_cls):
        session_cls.return_value.get.return_value = _mock_response({"items": []})
        self.assertIsNone(anitya_upstream("nope"))

    @patch("last_update.requests.Session")
    def test_error_returns_none(self, session_cls):
        session_cls.return_value.get.side_effect = \
            last_update.requests.exceptions.ConnectionError("boom")
        self.assertIsNone(anitya_upstream("gzip"))


if __name__ == "__main__":
    unittest.main()
