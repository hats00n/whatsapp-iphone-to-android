import logging
import os
import shutil
import sqlite3
import sys
import unittest

from convert.iphone_to_android import get_android_jid_for_contact, import_iphone_database_to_android_database

_ANDROID_DB_NAME = "msgstore.db"
_IPHONE_DB_BANE = "Chatstorage.sqlite"
_RESULT_DB_NAME = "result_msgstore.db"


class IPhoneToAndroidTestCases(unittest.TestCase):
    test_android_sqlite_file = None
    test_android_sqlite_connection = None
    test_iphone_sqlite_file = None
    test_iphone_sqlite_connection = None
    test_result_sqlite_file = None
    test_result_sqlite_connection = None

    def setUp(self) -> None:
        # copy empty databases to current dire
        self.test_android_sqlite_file = "test_{}".format(_ANDROID_DB_NAME)
        self.test_iphone_sqlite_file = "test_{}".format(_IPHONE_DB_BANE)
        self.test_result_sqlite_file = "test_{}".format(_RESULT_DB_NAME)
        shutil.copy("../../assets/empty/{}".format(_ANDROID_DB_NAME), "./{}".format(self.test_android_sqlite_file))
        shutil.copy("../../assets/empty/{}".format(_IPHONE_DB_BANE), "./{}".format(self.test_iphone_sqlite_file))
        shutil.copy("../../assets/empty/{}".format(_ANDROID_DB_NAME), "./{}".format(self.test_result_sqlite_file))
        self.test_android_sqlite_connection = sqlite3.connect(self.test_android_sqlite_file)
        self.test_iphone_sqlite_connection = sqlite3.connect(self.test_iphone_sqlite_file)
        self.test_result_sqlite_connection = sqlite3.connect(self.test_result_sqlite_file)
        super().setUp()

    def test_get_jid_for_non_existing_contact(self):
        non_existing_jid_string = "989332566719@s.whatsapp.com"
        before_jid_table_count = self._get_table_count(self.test_android_sqlite_connection, "jid")
        get_android_jid_for_contact(self.test_android_sqlite_connection, non_existing_jid_string)
        after_jid_table_count = self._get_table_count(self.test_android_sqlite_connection, "jid")
        self.assertEqual(before_jid_table_count + 1, after_jid_table_count)

    def test_get_jid_for_existing_contact(self):
        non_existing_jid_string = "989332566719@s.whatsapp.com"
        before_jid_table_count = self._get_table_count(self.test_android_sqlite_connection, "jid")
        get_android_jid_for_contact(self.test_android_sqlite_connection, non_existing_jid_string)
        after_jid_table_count = self._get_table_count(self.test_android_sqlite_connection, "jid")
        self.assertEqual(before_jid_table_count + 1, after_jid_table_count)

        # querying it again , and it shouldn't change the count
        get_android_jid_for_contact(self.test_android_sqlite_connection, non_existing_jid_string)
        after_second_query_jid_table_count = self._get_table_count(self.test_android_sqlite_connection, "jid")
        self.assertEqual(after_second_query_jid_table_count, after_jid_table_count)

    def test_simple_import(self):
        before_android_message_count = self._get_table_count(self.test_result_sqlite_connection, "message")
        iphone_message_count = self._get_table_count(self.test_iphone_sqlite_connection, "ZWAMESSAGE")
        import_iphone_database_to_android_database(self.test_android_sqlite_connection,
                                                   self.test_iphone_sqlite_connection,
                                                   self.test_result_sqlite_connection)
        shutil.copy(self.test_result_sqlite_file, "../../assets/result/")
        print(before_android_message_count, iphone_message_count)
        self.assertEqual(self._get_table_count(self.test_result_sqlite_connection, "message"),
                         before_android_message_count + iphone_message_count)

    @staticmethod
    def _get_table_count(connection: sqlite3.Connection, table_name: str) -> int:
        cur = connection.cursor()
        cur.execute("SELECT COUNT(*) from {}".format(table_name))
        res = cur.fetchone()
        return int(res[0])

    def tearDown(self) -> None:
        self.test_android_sqlite_connection.close()
        self.test_iphone_sqlite_connection.close()
        self.test_result_sqlite_connection.close()
        self._remove_all_temp_files()
        super().tearDown()

    def _remove_all_temp_files(self):
        try:
            os.remove("{}".format(self.test_android_sqlite_file))
        except FileNotFoundError:
            pass
        try:
            os.remove("{}-wal".format(self.test_android_sqlite_file))
        except FileNotFoundError:
            pass
        try:
            os.remove("{}-shm".format(self.test_android_sqlite_file))
        except FileNotFoundError:
            pass
        try:
            os.remove("{}".format(self.test_iphone_sqlite_file))
        except FileNotFoundError:
            pass
        try:
            os.remove("{}-wal".format(self.test_iphone_sqlite_file))
        except FileNotFoundError:
            pass
        try:
            os.remove("{}-shm".format(self.test_iphone_sqlite_file))
        except FileNotFoundError:
            pass
        try:
            os.remove("{}".format(self.test_result_sqlite_file))
        except FileNotFoundError:
            pass
        try:
            os.remove("{}-wal".format(self.test_result_sqlite_file))
        except FileNotFoundError:
            pass
        try:
            os.remove("{}-shm".format(self.test_result_sqlite_file))
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    unittest.main()
