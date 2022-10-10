import logging
import os
import shutil
import sqlite3
import subprocess
import sys

from iOSbackup import iOSbackup
from termcolor import colored
from git import Repo

from convert.iphone_to_android import import_iphone_database_to_android_database
from log_format import CustomFormatter

TMP_PATH = "./tmp/"
ASSETS_PATH = "./assets/"
ANDROID_REPO_CLONE_PATH = "./lib/android/"


def initialize_logger():
    logger = logging.getLogger()
    logger.level = logging.DEBUG
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(CustomFormatter())
    logger.addHandler(stream_handler)


def initialize_directories():

    try:
        shutil.rmtree(TMP_PATH)
    except FileNotFoundError:
        pass
    os.mkdir(TMP_PATH)

    try:
        shutil.rmtree("{}extracted".format(ANDROID_REPO_CLONE_PATH))
    except FileNotFoundError:
        pass



def initialize_repositories():
    github_link = "https://github.com/hats00n/whatsapp_db_extractor"
    logging.info("Going to clone {} for android backup".format(github_link))
    if not os.path.isdir(ANDROID_REPO_CLONE_PATH):
        Repo.clone_from(github_link, ANDROID_REPO_CLONE_PATH)
    logging.info("Clone done!")


def iphone_backup():
    device_list = iOSbackup.getDeviceList()
    if not device_list:
        raise Exception("Could not find any iphone backup in the system. Read readme to know how to get one!")

    def device_name_formatter(device_dict: dict) -> str:
        return "{name}({type})".format(
            name=device_dict["name"],
            type=device_dict["type"])

    selected_device = device_list[0]
    if len(device_list) > 1:
        while True:
            print("Select one of your following backups to import from:")
            for idx, device in enumerate(device_list):
                print("{} - {}".format(idx + 1, device_name_formatter(device)))
            selected = int(input(":")) - 1
            if selected < 0 or selected >= len(device_list):
                continue
            selected_device = device_list[selected]
            break

    logging.info("Device Selected: {}".format(device_name_formatter(selected_device)))
    i_backup = iOSbackup(udid=selected_device["udid"])
    for id in [s for s in list(i_backup.manifest['Applications'].keys()) if "whatsapp" in s]:
        for prefix in ["AppDomain", "AppDomainGroup", "AppDomainPlugin"]:
            i_backup.getFolderDecryptedCopy(includeDomains=prefix + '-' + id, targetFolder=TMP_PATH)

    shutil.copy("{}{}".format(TMP_PATH, "AppDomainGroup-group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite"),
                ASSETS_PATH)
    logging.info("ChatStorage.sqlite copied to {}".format(ASSETS_PATH))


def android_backup():
    os.system("cd {};{} wa_kdbe.py --tar-only".format(ANDROID_REPO_CLONE_PATH, sys.executable))
    if not os.path.isfile("{}extracted/user.tar".format(ANDROID_REPO_CLONE_PATH)):
        raise Exception("Android backup process was not successful.")

    os.system("cd {}extracted; tar -xf user.tar".format(ANDROID_REPO_CLONE_PATH))

    android_db_path = "{}extracted/apps/com.whatsapp/db/msgstore.db".format(ANDROID_REPO_CLONE_PATH)
    if not os.path.isfile(android_db_path):
        raise Exception("{} not Exists!".format(android_db_path))

    shutil.copy(android_db_path, ASSETS_PATH)
    pass


def do_convert():
    android_connection = sqlite3.connect("{}msgstore.db".format(ASSETS_PATH))
    iphone_connection = sqlite3.connect("{}ChatStorage.sqlite".format(ASSETS_PATH))

    result_path = "{}result/".format(ASSETS_PATH)
    if os.path.isdir(result_path):
        shutil.rmtree(result_path)
    os.makedirs(result_path)

    shutil.copy("{}msgstore.db".format(ASSETS_PATH), "{}msgstore.db".format(result_path))
    result_connection = sqlite3.connect("{}msgstore.db".format(result_path))
    import_iphone_database_to_android_database(android_connection, iphone_connection, result_connection)
    logging.info("conversion done!")


def restore_modified_db():
    result_path = "{}result/".format(ASSETS_PATH)
    old_archive_base_path = "{}extracted/".format(ANDROID_REPO_CLONE_PATH)
    new_android_db_file_path = "{}msgstore.db".format(result_path)
    old_android_path = "{}apps/com.whatsapp/db/".format(old_archive_base_path)
    old_android_db_path = "{}msgstore.db".format(old_android_path)
    if not os.path.isfile(new_android_db_file_path):
        raise Exception("Expected merged android db file at {} is not there".format(new_android_db_file_path))

    if not os.path.isfile(old_android_db_path):
        raise Exception("Expected old android db file at {} is not there".format(new_android_db_file_path))

    shutil.copy(new_android_db_file_path, old_android_db_path)
    cmd = "cd {}; rm msgstore.db-shm msgstore.db-wal".format(old_android_path)
    logging.info("running {}".format(cmd))
    proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    logging.debug(out)
    logging.debug(err)

    # Create a new tar file, Important note: https://github.com/nelenkov/android-backup-extractor/pull/38/files
    cmd = "cd {}; tar tf user.tar | grep -F \"com.whatsapp\" > package.list".format(old_archive_base_path, TMP_PATH)
    logging.info("running {}".format(cmd))
    proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    logging.debug(out)
    logging.debug(err)

    cmd = "cd {}; tar cf restore.tar -T package.list".format(old_archive_base_path)
    logging.info("running {}".format(cmd))
    proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    logging.debug(out)
    logging.debug(err)

    if not os.path.isfile("{}restore.tar".format(old_archive_base_path)):
        raise Exception("Could not repack restore.tar")

    os.system("cd {};{} wa_kdbe.py --restore --restore-path=extracted/restore.tar".format(ANDROID_REPO_CLONE_PATH, sys.executable))

    logging.info("Done!")


if __name__ == "__main__":
    initialize_logger()
    initialize_directories()
    initialize_repositories()

    print(colored("Before starting make sure you do the following:", 'green'))
    print("1. {}".format(colored("BACKUP YOUR MESSAGES SOMEWHERE, BOTH ON ANDROID AND iOS", 'green')))
    print("2. {}".format(colored("ACTIVATE THE WHATSAPP ON ANDROID [iPHONE WILL DISCONNECT]", 'red')))
    print("3. {}".format(colored("Make an backup from iPhone using the method explained in the readme", 'green')))
    answer = input(colored("Press y to continue:"))
    if answer.strip().lower() != 'y':
        exit(0)

    iphone_backup()
    android_backup()
    do_convert()
    restore_modified_db()

# # clone iOSBackup repo into lib
# 
# android_connection = sqlite3.connect("./assets/msgstore.db")
# iphone_connection = sqlite3.connect("./assets/ChatStorage.sqlite")
# try:
#     os.removedirs("./assets/result")
# except Exception as e:
#     pass
# os.makedirs("./assets/result")
# 
# shutil.copy("./assets/msgstore.db", "./assets/result/msgstore.db",)
# result_connection = sqlite3.connect("assets/result/msgstore.db")
# 
# convert.iphone_to_android.import_iphone_database_to_android_database(android_connection, iphone_connection, result_connection)
# 
# logging.info("done!")
