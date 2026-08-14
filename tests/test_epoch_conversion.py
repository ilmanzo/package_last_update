import unittest
from datetime import datetime
from last_update import convert_to_epoch


class TestEpochParsing(unittest.TestCase):

    def test_date_with_year(self):
        self.assertEqual(1671231600, convert_to_epoch('Dec 17 2022'))

    def test_date_without_year(self):
        now = datetime(2026, 8, 14, 12, 0)
        ref = int(datetime(2026, 1, 22, 15, 35).timestamp())
        self.assertEqual(ref, convert_to_epoch('Jan 22 15:35', now=now))

    def test_yearless_date_in_future_rolls_back(self):
        # a change dated 'Dec 15' seen in January belongs to the previous year
        now = datetime(2026, 1, 10, 9, 0)
        ref = int(datetime(2025, 12, 15, 10, 44).timestamp())
        self.assertEqual(ref, convert_to_epoch('Dec 15 10:44', now=now))

    def test_invalid_date(self):
        self.assertIsNone(convert_to_epoch('foobar'))


if __name__ == '__main__':
    unittest.main()
