import logging
import sqlite3
from typing import Union

from convert.helper import parse_jid_string
from convert.message_type_mapping import convert_iphone_message_type_to_android


def import_iphone_database_to_android_database(
        android_sqlite_db_connection: sqlite3.Connection,
        iphone_sqlite_db_connection: sqlite3.Connection,
        result_sqlite_db_connection: sqlite3.Connection):
    with result_sqlite_db_connection, iphone_sqlite_db_connection, android_sqlite_db_connection:
        cur = iphone_sqlite_db_connection.cursor()
        cur.execute("SELECT "
                    "Z_PK, Z_ENT, Z_OPT, ZARCHIVED, ZCONTACTABID, ZFLAGS, ZHIDDEN, "  # 6 
                    "ZIDENTITYVERIFICATIONEPOCH, ZIDENTITYVERIFICATIONSTATE, ZMESSAGECOUNTER, "  # 9
                    "ZREMOVED, ZSESSIONTYPE, ZSPOTLIGHTSTATUS, ZUNREADCOUNT, ZGROUPINFO, "  # 14
                    "ZLASTMESSAGE, ZPROPERTIES, ZLASTMESSAGEDATE, ZLOCATIONSHARINGENDDATE, "
                    "ZCONTACTIDENTIFIER, ZCONTACTJID, ZETAG, ZLASTMESSAGETEXT, ZPARTNERNAME, ZSAVEDINPUT FROM ZWACHATSESSION WHERE ZHIDDEN = 0")
        rows = cur.fetchall()
        logging.info("fetched {} chat rows from iphone db".format(len(rows)))
        for iphone_chat_row in rows:
            logging.debug("importing chat for {}".format(iphone_chat_row[20]))
            sender_jid = get_android_jid_for_contact(android_sqlite_db_connection, iphone_chat_row[20])
            existing_chat_row = _android_get_chat_by_jid(android_sqlite_db_connection, sender_jid)
            if not existing_chat_row:
                logging.debug("chat doesn't exist in android db. inserting...")
                result_cur = result_sqlite_db_connection.cursor()
                result_cur.execute("INSERT INTO chat ("
                                   "jid_row_id, hidden, subject, created_timestamp, display_message_row_id, last_message_row_id, "
                                   "last_read_message_row_id, last_read_receipt_sent_message_row_id, last_important_message_row_id, "
                                   "archived, sort_timestamp, mod_tag, gen, spam_detection, unseen_earliest_message_received_time, "
                                   "unseen_message_count, unseen_missed_calls_count, unseen_row_count, plaintext_disabled, "
                                   "vcard_ui_dismissed, change_number_notified_message_row_id, show_group_description, ephemeral_expiration, "
                                   "last_read_ephemeral_message_row_id, ephemeral_setting_timestamp, ephemeral_disappearing_messages_initiator, "
                                   "unseen_important_message_count, group_type, last_message_reaction_row_id, last_seen_message_reaction_row_id, "
                                   "unseen_message_reaction_count, growth_lock_level, growth_lock_expiration_ts, last_read_message_sort_id, "
                                   "display_message_sort_id, last_message_sort_id, last_read_receipt_sent_message_sort_id, "
                                   "has_new_community_admin_dialog_been_acknowledged, history_sync_progress) VALUES "
                                   "(?, 0, null, ?, ?, ?, ?, ?, 1, ?, ?, 0, null, 1, ?, ?, 0, ?, 1, 0, 1, 0, 0, null, 0, 0, 0, 0, 0, 0, 0, null, null, ?, ?, ?, ?, 0, 0)",
                                   (
                                       sender_jid,  # jid_row_id
                                       int((978307200 + int(iphone_chat_row[17])) * 1000),  # created_timestamp
                                       0,  # display_message_row_id -- last message id
                                       0,  # last_message_row_id --> last message id
                                       0,  # last_read_message_row_id --> last message id
                                       0,  # last_read_receipt_sent_message_row_id --> last message id
                                       int(iphone_chat_row[3]),  # archived
                                       0,  # sort_timestamp, last message timestamp
                                       0,
                                       # unseen_earliest_message_received_time -> last message timestamp if unread_count > 1
                                       int(iphone_chat_row[13]),  # unseen_message_count
                                       int(iphone_chat_row[13]),  # unseen_row_count

                                       0,  # last_read_message_sort_id  --> last message id
                                       0,  # display_message_sort_id  --> last message id
                                       0,  # last_message_sort_id --> last message id
                                       0,  # last_read_receipt_sent_message_sort_id  --> last message id

                                   ))
                chat_id = result_cur.lastrowid
            else:
                chat_id = existing_chat_row[0]
                if int(iphone_chat_row[6]) == 0 and int(existing_chat_row[1]) == 1:
                    logging.warning("CHAT belong to JID {} was hidden in android, unhiddening...".format(iphone_chat_row[20]))
                result_cur.execute("UPDATE chat SET hidden = 0 WHERE _id = ? ", (chat_id,))

            insert_chats_ret = _import_message_database_using_chat_row(
                iphone_sqlite_db_connection,
                result_sqlite_db_connection,
                int(iphone_chat_row[0]),
                sender_jid,
                chat_id
            )

            result_cur.execute("UPDATE chat SET display_message_row_id = ?, last_message_row_id = ?, "
                               "last_read_message_row_id = ?,  last_read_receipt_sent_message_row_id = ?, "
                               "sort_timestamp = ?,  last_read_message_sort_id = ?, display_message_sort_id = ?, "
                               "last_message_sort_id = ?, last_read_receipt_sent_message_sort_id = ? WHERE _id = ?", (
                                   int(insert_chats_ret["last_message_id"]),
                                   int(insert_chats_ret["last_message_id"]),
                                   int(insert_chats_ret["last_message_id"]),
                                   int(insert_chats_ret["last_message_id"]),
                                   int(insert_chats_ret["last_message_timestamp"]),
                                   int(insert_chats_ret["last_message_id"]),
                                   int(insert_chats_ret["last_message_id"]),
                                   int(insert_chats_ret["last_message_id"]),
                                   int(insert_chats_ret["last_message_id"]),
                                   chat_id
                               ))

            result_sqlite_db_connection.commit()
    pass


def _android_get_chat_by_jid(android_sqlite_db_connection: sqlite3.Connection, jid_id: int):
    cur = android_sqlite_db_connection.cursor()
    cur.execute("SELECT _id, hidden FROM chat WHERE jid_row_id = ?", (jid_id,))
    row = cur.fetchone()
    if row:
        return row
    return None


def _import_message_database_using_chat_row(iphone_sqlite_db_connection: sqlite3.Connection,
                                            result_sqlite_db_connection: sqlite3.Connection,
                                            iphone_chat_id: int,
                                            sender_jid: int,
                                            android_chat_id: int) -> dict:
    """
    Inserts the relevant messages into android message database using a chat row
    returns last_message_id
    :param iphone_sqlite_db_connection: iphone db connection
    :param result_sqlite_db_connection: result db connection
    :param sender_jid: jid of the sender, silly doc!
    :param android_chat_id: I don't have to explain this!
    """

    logging.debug("Importing messages for chat id {}".format(android_chat_id))
    cur = iphone_sqlite_db_connection.cursor()
    cur.execute("SELECT "
                "Z_PK, Z_ENT, Z_OPT, ZCHILDMESSAGESDELIVEREDCOUNT, ZCHILDMESSAGESPLAYEDCOUNT, "  # 4
                "ZCHILDMESSAGESREADCOUNT, ZDATAITEMVERSION, ZDOCID, ZENCRETRYCOUNT, ZFILTEREDRECIPIENTCOUNT, ZFLAGS, "  # 10
                "ZGROUPEVENTTYPE, ZISFROMME, ZMESSAGEERRORSTATUS, ZMESSAGESTATUS, ZMESSAGETYPE, ZSORT, "  # 16
                "ZSPOTLIGHTSTATUS, ZSTARRED, ZCHATSESSION, ZGROUPMEMBER, ZLASTSESSION, ZMEDIAITEM, ZMESSAGEINFO, "  # 23
                "ZPARENTMESSAGE, ZMESSAGEDATE, ZSENTDATE, ZFROMJID, ZMEDIASECTIONID, ZPHASH, ZPUSHNAME, ZSTANZAID, ZTEXT, ZTOJID"
                " FROM ZWAMESSAGE WHERE ZCHATSESSION = ? ORDER BY ZMESSAGEDATE ASC", (iphone_chat_id,))
    rows = cur.fetchall()
    last_message_id = None
    last_message_timestamp = None
    logging.debug("found {} messages".format(len(rows)))
    for iphone_message_row in rows:
        result_cur = result_sqlite_db_connection.cursor()
        msg_timestamp = int((978307200 + iphone_message_row[25]) * 1000)
        from_me = int(iphone_message_row[12]) == 1
        duplicated_row = _get_duplicated_record(result_sqlite_db_connection, android_chat_id, from_me,
                                                iphone_message_row[31], sender_jid)
        msg_type = convert_iphone_message_type_to_android(int(iphone_message_row[15]))
        if msg_type == -1:
            logging.debug("unknown msg_type : {} , skipping".format(iphone_message_row[15]))
            continue
        if duplicated_row:
            logging.warning("WEIRD: YOU ALREADY HAVE MESSAGE FROM {} WITH TEXT: {} IN ANDROID DB. SKIPPING".format(
                iphone_message_row[33] if from_me else iphone_message_row[27],
                duplicated_row["text"]
            ))
            last_message_id = duplicated_row["id"]
            last_message_timestamp = msg_timestamp
            continue
        result_cur.execute("INSERT INTO message ("
                           "chat_row_id, from_me, key_id, sender_jid_row_id, status, broadcast, recipient_count, "
                           "participant_hash, origination_flags, origin, timestamp, received_timestamp, "
                           "receipt_server_timestamp, message_type, text_data, starred, lookup_tables, "
                           "message_add_on_flags"
                           ") VALUES ( ?, ?, ?, ?, ?, 0, 0, null, 0, 0, ?, ?, ?, ?, ?, ?, 0, 0)",
                           (
                               android_chat_id,
                               1 if from_me else 0,
                               iphone_message_row[31],  # ZSTANZAID for key_id
                               sender_jid,
                               _get_android_message_status(from_me,
                                                           int(iphone_message_row[14])),
                               msg_timestamp,  # timestamp
                               msg_timestamp if not from_me else 0,  # received_timestamp
                               msg_timestamp if from_me else -1,  # receipt server timestamp
                               0,  # message_type @TODO: do the media migration
                               iphone_message_row[32] if msg_type == 0 else "A Media file was here",  # text_data
                               int(iphone_message_row[18]) if iphone_message_row[18] else 0
                           ))
        last_message_id = result_cur.lastrowid
        last_message_timestamp = msg_timestamp
        logging.debug("Inserted message #{} @{}".format(last_message_id, last_message_timestamp))
        result_cur.execute(" UPDATE message SET sort_id = ? WHERE _id = ?", (last_message_id, last_message_id))
        result_sqlite_db_connection.commit()
    return {
        "last_message_id": last_message_id,
        "last_message_timestamp": last_message_timestamp
    }


def _get_duplicated_record(android_sqlite_db_connection: sqlite3.Connection, chat_row_id: int, from_me: bool,
                           key_id: str, sender_jid_row_id: int):
    cur = android_sqlite_db_connection.cursor()
    res = cur.execute(
        "SELECT _id, text_data FROM message WHERE chat_row_id = ? and from_me = ? and key_id = ? and sender_jid_row_id = ? ",
        (chat_row_id, 1 if from_me else 0, key_id, sender_jid_row_id))
    row = res.fetchone()
    if row:
        return {
            'id': int(row[0]),
            'text': row[1]
        }
    return None


def _get_android_message_status(from_me: bool, iphone_status: int) -> int:
    if from_me:
        if iphone_status in [5,
                             13]:  # 5-> delivered_but_not_read, 13-> delivered_and_read @TODO sent but not delivered status should be added here 
            return iphone_status
        elif iphone_status == 6:  # don't know what the f** is that , but i saw that in my db!
            return 6
        else:
            return 5  # set to delivered_but_not_read in case you don't know
    else:
        return 0


def get_android_jid_for_contact(android_sqlite_db_connection: sqlite3.Connection, jid_string: str) -> int:
    cur = android_sqlite_db_connection.cursor()
    cur.execute("SELECT * FROM jid WHERE raw_string = ? ", (jid_string,))
    parsed_jid_string = parse_jid_string(jid_string)
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO jid (user, server, agent, device, type, raw_string) VALUES (?, ?, 0, 0, 0, ?)",
                    (parsed_jid_string["user"], parsed_jid_string["server"], jid_string))

        android_sqlite_db_connection.commit()
        return cur.lastrowid

    # _id column
    return int(row[0])
