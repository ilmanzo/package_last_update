import unittest
from datetime import datetime
from last_update import convert_to_epoch

class TestEpochParsing(unittest.TestCase):

    def test_date_with_year(self):
        self.assertEqual(1671231600, convert_to_epoch('Dec 17 2022'))

    def test_date_without_year(self):
        current_year = datetime.today().year
        ref_date = int(datetime(current_year, 1, 22, 15, 35).timestamp())
        self.assertEqual(ref_date, convert_to_epoch('Jan 22 15:35'))

    def test_invalid_date(self):
        self.assertIsNone(convert_to_epoch('foobar'))

if __name__ == '__main__':
    unittest.main()
