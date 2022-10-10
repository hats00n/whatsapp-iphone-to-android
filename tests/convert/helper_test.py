import unittest

from convert.helper import parse_jid_string


class HelperTest(unittest.TestCase):
    def test_parse_jid_string_wrong_format(self):
        test_jid = "12312312@s.whatsapp.com@bullshit"
        with self.assertRaises(ValueError):
            parse_jid_string(test_jid)

    def test_parse_jid_string(self):
        test_jid = "12312312@g.whatsapp.com"
        ret = parse_jid_string(test_jid)
        self.assertEqual("12312312", ret["user"])
        self.assertEqual("g.whatsapp.com", ret["server"])


if __name__ == '__main__':
    unittest.main()
