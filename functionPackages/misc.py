import os
import sqlite3
import hashlib
import binascii
from functionPackages.dateTime import *
from pyexiv2 import ImageMetadata
import json
from package import tracker_settings, temporary_data
import requests
import logging

logger = logging.getLogger(__name__)


def get_audiobooks(path):
    audiobooks = {}
    for a in os.scandir(path):
        if a.is_dir():
            author = a.name
            books = {}
            for b in os.scandir(a):
                if b.is_dir():
                    chapters = []
                    for chapter in os.scandir(b):
                        if ".mp3" in chapter.name:
                            chapters.append(chapter.name)
                    books[b.name] = sorted(chapters)
            audiobooks[author] = books
    metadata = {}
    for a in os.scandir(path):
        if a.is_dir():
            author = a.name
            books = {}
            for b in os.scandir(a):
                if b.is_dir():
                    for f in os.scandir(b):
                        if ".json" in f.name:
                            try:
                                f = open(f, 'r')
                                data = json.load(f)
                                books[b.name] = data
                            except Exception as e:
                                logger.error(e)
                                logger.error("something is wrong with" + str(f.name))
                            break
                    # if book metadate doesn't exist add it
                    if b.name not in books.keys():
                        books[b.name] = {}
                        for i in range(len(audiobooks[author][b.name])):
                            books[b.name]["chapter "+str(i+1)] = {
                                "timestamp": 0,
                                "progress": "0.0"
                            }
                        path = os.path.realpath(b)+"/metadata.json"
                        f = open(path, 'w+')
                        json.dump(books[b.name], f)
                        f.close()
            metadata[author] = books
    return audiobooks, metadata


def get_flash_cards(db_cursor, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM flashcards""")
    flash_cards = db_cursor.fetchall()
    lock.release()
    to_review = []
    set_names = set()
    for item in flash_cards:
        date = datetime.datetime.strptime(item[3], '%Y-%m-%d').date()
        today_date = datetime.date.today()
        delta = today_date - date
        if delta.days >= 0:
            to_review.append(item)
        set_names.add(item[0])
    return set_names, to_review


def add_flash_cards(set_name: str, side1: str, side2: str, last_time_reviewed: str, db_cursor, db_connection, lock):
    logger.info(f"Adding card {side1} and {side2} to set {set_name}")
    lock.acquire(True)
    db_cursor.execute("""INSERT INTO flashcards VALUES(?, ?, ?, ?)""",
                      (set_name, side1, side2, last_time_reviewed))
    db_connection.commit()
    lock.release()


def delete_flash_cards(set_name: str, side1: str, side2: str, db_cursor, db_connection, lock):
    logger.info(f"deleting card {side1} and {side2} from set {set_name}")
    lock.acquire(True)
    db_cursor.execute("""DELETE from flashcards where setName = ? and side1 = ? and side2 = ?""",
                      (set_name, side1, side2,))
    db_connection.commit()
    lock.release()


def change_flash_cards(set_name: str, side1: str, side2: str, last_time_reviewed: str, db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""DELETE from flashcards where setName = ? and side1 = ? and side2 = ?""",
                      (set_name, side1, side2,))
    db_cursor.execute("""INSERT INTO flashcards VALUES(?, ?, ?, ?)""",
                      (set_name, side1, side2, last_time_reviewed))
    db_connection.commit()
    lock.release()


def add_travel_item(name: str, latitude: str, longitude: str, db_cursor, db_connection, lock) -> None:
    lock.acquire(True)
    db_cursor.execute("""INSERT INTO travelTracker VALUES(?, ?, ?)""", (name, latitude, longitude))
    db_connection.commit()
    lock.release()
    return None


def get_cal_events_week(today_date: str, db_cursor, lock) -> list:
    dt = datetime.datetime.strptime(today_date, '%Y-%m-%d')
    weeks_beginning = dt - datetime.timedelta(days=dt.weekday())
    weeks_end = weeks_beginning + datetime.timedelta(days=6)
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM calendar WHERE date >= ? and date <= ?  """,
                      (str(weeks_beginning.date()),
                       str(weeks_end.date()),))
    weekly_cal_events = db_cursor.fetchall()
    lock.release()
    cal_list = []
    for item in weekly_cal_events:
        try:
            d1 = datetime.datetime.strptime(item[0], '%Y-%m-%d')
            delta = d1 - weeks_beginning
            cal_list.append([delta.days, item[1], item[2], item[3], 1, 1, item[4], item[5]])
        except Exception as e:
            logger.error(e)
    return cal_list


def get_cal_events_month(today_date: str, db_cursor, lock) -> list:
    day, month, year = separate_day_month_year(today_date)
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM calendar WHERE date >= ? and date <= ?  """,
                      (get_months_beginning(month, year).date(), get_months_end(month, year).date(),))
    weekly_cal_events = db_cursor.fetchall()
    lock.release()
    cal_list = []
    for item in weekly_cal_events:
        try:
            cal_list.append([item[0], item[1], item[2], item[3], 1, 1, item[4], item[5]])
        except Exception as e:
            logger.error(e)
    cal_list = sorted(cal_list, key=lambda x: x[1])
    cal_list = sorted(cal_list, key=lambda x: (x[1] != "None"))
    cal_list = sorted(cal_list, key=lambda x: x[0])
    return cal_list


def get_today_logs(db_cursor, today_date: str, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM tracker WHERE date = ? """, (today_date,))
    log_value = db_cursor.fetchall()[0][14]
    lock.release()
    if len(log_value) > 0:
        today_log = log_value.replace("\n", "<br>")
        today_log_text = log_value
    else:
        today_log = ""
        today_log_text = ""
    return today_log, today_log_text


def all_photos_in_dir(photo_dir: str, year: str, date: str) -> dict:
    today_photos = {}
    if os.path.isdir(photo_dir):
        for file in os.listdir(photo_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                tags = []
                try:
                    file_name = "./static/photos/"+year+"/"+date+"/"+file
                    metadata = ImageMetadata(file_name)
                    metadata.read()
                    if 'Exif.Photo.UserComment' in metadata:
                        userdata = json.loads(metadata['Exif.Photo.UserComment'].value)
                        if userdata["tags"] is not None:
                            tags = list(userdata["tags"])
                except Exception as e:
                    logger.error(e)
                today_photos[year+"/"+date+"/"+file] = tags
            if file.lower().endswith('.mp4'):
                today_photos[year+"/"+date+"/"+file] = []
    return today_photos


def all_days_with_photos(photo_dir: str, year: str, month: str) -> list:
    days_with_photos = []
    if os.path.isdir(photo_dir):
        days_with_photos = [int(x.split("-")[2]) for x in os.listdir(photo_dir) if year + "-" +
                            '%02d' % int(month) in x]
    return sorted(days_with_photos)


def add_tracker_item_to_table(item: str, item_list: list, table_name: str,
                              date: str, delete: bool, db_cursor,  db_connection, lock):

    if item_list and (item not in item_list):
        return item + " not found", 400

    # invalidate the temporary_data for the whole year
    year = int(date.split("-")[0])
    temporary_data.pop(year, None)

    lock.acquire(True)
    db_cursor.execute("SELECT * FROM tracker WHERE date = ?", (date,))
    fetched_data = db_cursor.fetchall()
    if len(fetched_data) == 0:
        db_cursor.execute("INSERT INTO tracker VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (date, "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan",
                           "nan", "nan", "nan", "nan"))
        db_connection.commit()
    lock.release()

    index = tracker_settings[table_name]["index"]
    label = tracker_settings[table_name]["label"]
    accumulate = tracker_settings[table_name]["accumulate"]

    lock.acquire(True)
    db_cursor.execute("SELECT * FROM tracker WHERE date = ?", (date,))
    fetched_data = db_cursor.fetchall()
    if table_name in ["activityTracker", "activityPlanner"]:
        if fetched_data[0][index] in ["nan", "None"]:
            init_set = []
        else:
            init_set = eval(fetched_data[0][index])
        if delete:
            if (len(init_set) > 0) and (item in init_set):
                init_set.remove(item)
                item = str(init_set)
            else:
                lock.release()
                return "Done", 200
        else:
            item = str(init_set+[item])
    else:
        if delete:
            item = "nan"
        else:
            if accumulate and (fetched_data[0][index] != "nan"):
                item = float(fetched_data[0][index]) + float(item)

    logger.info(f"@{datetime.datetime.now()} :: adding {item} to {date}'s {label}")

    db_cursor.execute("UPDATE tracker SET " + label + " = ? WHERE date = ?", (item, date,))
    db_connection.commit()
    lock.release()
    return "Done", 200


def add_saving_item_to_table(item: str, date: str, db_cursor, db_connection, lock):
    # invalidate the temporary_data for the whole year
    year = int(date.split("-")[0])
    temporary_data.pop(year, None)

    month = "-".join(date.split("-")[0:2])
    db_cursor.execute("SELECT * FROM savingTracker WHERE month = ?", (month,))
    fetched_data = db_cursor.fetchall()

    if len(fetched_data) > 0:
        item = float(fetched_data[0][0])+float(item)
    else:
        # get last month's value
        current_month = int(date.split("-")[1])
        current_year = int(date.split("-")[0])
        counter = 12
        last_month_fetch = []
        while len(last_month_fetch) == 0:
            if current_month != 1:
                month_val = current_month - 1
                year_val = current_year
            else:
                month_val = 12
                year_val = current_year - 1

            last_month_val = str(year_val)+"-"+str(month_val).zfill(2)
            db_cursor.execute("SELECT * FROM savingTracker WHERE month = ?", (last_month_val,))
            last_month_fetch = db_cursor.fetchall()
            current_month = month_val
            current_year = year_val
            counter -= 1
            if counter <= 0:
                break
        if len(last_month_fetch) > 0:
            last_month_val = float(last_month_fetch[0][0])
        else:
            last_month_val = 0
        item = float(last_month_val)+float(item)
    lock.acquire(True)
    db_cursor.execute("SELECT * FROM savingTracker WHERE month = ?", (month,))
    current_month_fetch = db_cursor.fetchall()
    if len(current_month_fetch) == 0:

        db_cursor.execute("INSERT INTO savingTracker VALUES(?, ?)", (item, month))
    else:
        db_cursor.execute("UPDATE savingTracker SET saving = ? WHERE month = ?", (item, month,))

    db_connection.commit()
    lock.release()
    return "Done", 200


def add_mortgage_item_to_table(item: str, date: str, db_cursor, db_connection, lock):
    month = "-".join(date.split("-")[0:2])

    # invalidate the temporary_data for the whole year
    year = int(date.split("-")[0])
    temporary_data.pop(year, None)

    lock.acquire(True)
    db_cursor.execute("SELECT * FROM mortgageTracker WHERE month = ?", (month,))
    fetched_data = db_cursor.fetchall()
    lock.release()
    if len(fetched_data) > 0:
        item = float(fetched_data[0][0])+float(item)
    else:
        # get last month's value
        current_month = int(date.split("-")[1])
        current_year = int(date.split("-")[0])
        counter = 12
        last_month_fetch = []
        while len(last_month_fetch) == 0:
            if current_month != 1:
                month_val = current_month - 1
                year_val = current_year
            else:
                month_val = 12
                year_val = current_year - 1

            last_month_val = str(year_val)+"-"+str(month_val).zfill(2)
            lock.acquire(True)
            db_cursor.execute("SELECT * FROM mortgageTracker WHERE month = ?", (last_month_val,))
            last_month_fetch = db_cursor.fetchall()
            lock.release()
            current_month = month_val
            current_year = year_val
            counter -= 1
            if counter <= 0:
                break
        if len(last_month_fetch) > 0:
            last_month_val = float(last_month_fetch[0][0])
        else:
            last_month_val = 0
        item = float(last_month_val)+float(item)
    lock.acquire(True)
    db_cursor.execute("SELECT * FROM mortgageTracker WHERE month = ?", (month,))
    current_month_fetch = db_cursor.fetchall()
    if len(current_month_fetch) == 0:

        db_cursor.execute("INSERT INTO mortgageTracker VALUES(?, ?)", (item, month))
    else:
        db_cursor.execute("UPDATE mortgageTracker SET mortgage = ? WHERE month = ?", (item, month,))
    db_connection.commit()
    lock.release()
    return "Done", 200


def collect_months_data(page_month: int, page_year: int, db_cursor, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM tracker WHERE date >= ? and date <= ?  """,
                      (get_months_beginning(page_month, page_year).date(),
                       get_months_end(page_month, page_year).date(),))
    index = tracker_settings["activityTracker"]["index"]
    activities = [(x[0], x[index]) for x in db_cursor.fetchall()]

    db_cursor.execute("""SELECT * FROM tracker WHERE date >= ? and date <= ?  """,
                      (get_months_beginning(page_month, page_year).date(),
                       get_months_end(page_month, page_year).date(),))
    index = tracker_settings["activityPlanner"]["index"]
    activities_planned = [(x[0], x[index]) for x in db_cursor.fetchall()]

    db_cursor.execute("""SELECT * FROM tracker WHERE date >= ? and date <= ?  """,
                      (get_months_beginning(page_month, page_year).date(),
                       get_months_end(page_month, page_year).date(),))
    index = tracker_settings["moodTracker"]["index"]
    moods = [(x[0], x[index]) for x in db_cursor.fetchall()]
    lock.release()
    return activities, activities_planned, moods


def collect_yearly_activities(page_year: int, db_cursor, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM tracker WHERE date >= ? and date <= ?  """,
                      (get_months_beginning(1, page_year).date(),
                       get_months_end(12, page_year).date(),))
    index = tracker_settings["activityTracker"]["index"]
    activities = {x[0]: x[index] for x in db_cursor.fetchall()}
    lock.release()

    activity_list = [x.replace(" ", "") for x in
                     fetch_setting_param_from_db(db_cursor, "activityList", lock).split(",")]
    return_dict = {}
    for month in range(1, 13):
        for day in range(1, number_of_days_in_month(month, page_year) + 1):
            for activity in activity_list:
                date = str(datetime.datetime.strptime(f"{page_year}-{month}-{day}", '%Y-%m-%d').date())
                return_dict[activity] = return_dict.get(activity, [])
                if activity in activities.get(date, []):
                    return_dict[activity].append(1)
                else:
                    return_dict[activity].append(0)

    return return_dict


def create_db(db_name):
    db_connection = sqlite3.connect(db_name, check_same_thread=False)
    db_cursor = db_connection.cursor()
    return db_connection, db_cursor


def generate_db_tables_learning(db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""CREATE TABLE if not exists flashcards (
                 setName text, side1 text, side2 text, lastTimeReviewed text)""")
    db_connection.commit()
    lock.release()


def generate_db_tables(db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""CREATE TABLE if not exists tracker (
                 date text, 
                 work_hour text,
                 HR_Min text, HR_Max text, BP_Min text, BP_Max text, BO text,
                 sleepTime text, weight text, steps text, hydration text, 
                 run text, pace text,
                 mood_name text, log text,
                 activity_tracker_name text, 
                 activity_planner_name text
                 )""")

    db_cursor.execute("""CREATE TABLE if not exists calendar (
             date text, startTime text, endTime text, eventName text, color text, details text)""")

    db_cursor.execute("""CREATE TABLE if not exists travelTracker (
             Destination text, latitude text, longitude text)""")

    db_cursor.execute("""CREATE TABLE if not exists savingTracker (
                 saving text, month text)""")
    db_cursor.execute("""CREATE TABLE if not exists mortgageTracker (
                 mortgage text, month text)""")

    db_cursor.execute("""CREATE TABLE if not exists todoList (
             task text, date text, done text, color, text)""")
    db_cursor.execute("""CREATE TABLE if not exists scrumBoard (
             project text, task text, stage text, priority text, done_date text)""")
    db_cursor.execute("""CREATE TABLE if not exists settings (
             parameter text, value text)""")
    db_cursor.execute("""CREATE TABLE if not exists lists (
             name text, done text, type text, note text)""")
    db_cursor.execute("""CREATE TABLE if not exists Notes (
             Notebook text, Chapter text, Content text)""")
    db_connection.commit()
    lock.release()


def setup_setting_table(db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("Theme",))
    try:
        db_cursor.fetchall()[0][1]
    except IndexError:
        db_cursor.execute("""INSERT INTO settings VALUES(?, ?)""", ("Theme", "Dark"))

    db_cursor.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("counter",))
    try:
        db_cursor.fetchall()[0][1]
    except IndexError:
        db_cursor.execute("""INSERT INTO settings VALUES(?, ?)""", ("counter", "0"))

    for item in ["activityList", "activityList", "MAIL_SERVER", "MAIL_PORT", "MAIL_USE_SSL",
                 "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_RECIPIENT", "audiobooksPath"]:
        db_cursor.execute("""SELECT * FROM settings WHERE parameter = ?  """, (item,))
        try:
            db_cursor.fetchall()[0][1]
        except IndexError:
            db_cursor.execute("""INSERT INTO settings VALUES(?, ?)""", (item, "None"))

    for item in ["EnableDailyDigest", "EnableEventNotifications"]:
        db_cursor.execute("""SELECT * FROM settings WHERE parameter = ?  """, (item,))
        try:
            db_cursor.fetchall()[0][1]
        except IndexError:
            db_cursor.execute("""INSERT INTO settings VALUES(?, ?)""", (item, "false"))

    db_cursor.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("latitude",))
    try:
        db_cursor.fetchall()[0][1]
    except IndexError:
        db_cursor.execute("""INSERT INTO settings VALUES(?, ?)""", ("latitude", "ex. 52.523430"))

    db_cursor.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("longitude",))
    try:
        db_cursor.fetchall()[0][1]
    except IndexError:
        db_cursor.execute("""INSERT INTO settings VALUES(?, ?)""", ("longitude", "ex. 13.411440"))

    db_connection.commit()
    lock.release()


def should_highlight(page_year: str, page_month: str) -> bool:
    """
    returns True if the pageYear and pageMonth are the same as the current month
    and year. returns False otherwise.
    """
    if (page_year != str(datetime.date.today().year)) or (page_month != str(datetime.date.today().month).zfill(2)):
        return False
    return True


def progress(status, remaining, total):
    print(f'Copied {total-remaining} of {total} pages...')


def backup_database(conn):
    try:
        if not os.path.exists('backups'):
            os.mkdir('backups')
        backup_con = sqlite3.connect('backups/journal_backup_'+str(datetime.date.today())+'.db')
        with backup_con:
            conn.backup(backup_con, pages=1, progress=progress)
        logger.info("backup successful")
    except sqlite3.Error as error:
        logger.error("Error while taking backup: " + str(error))
    else:
        if backup_con:
            backup_con.close()


def fetch_setting_param_from_db(db_cursor, param, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM settings WHERE parameter = ?  """, (param,))
    try:
        parameter = db_cursor.fetchall()[0][1]
    except Exception as err:
        logger.error(err)
        raise ValueError(f"parameter {param} is missing in DB!")
    lock.release()
    return parameter


def fetch_notebooks(db_cursor, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM Notes """)
    note_books_content = db_cursor.fetchall()
    lock.release()
    note_books = {}
    for item in note_books_content:
        chapters = note_books.get(item[0], {})
        chapters[item[1]] = item[2]
        note_books[item[0]] = chapters
    return note_books


def update_setting_param(db_cursor, db_connection, param, value, lock):
    try:
        lock.acquire(True)
        db_cursor.execute("UPDATE settings SET value = ? WHERE parameter = ?", (value, param,))
        db_connection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def hash_password(password: str) -> str:
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwd_hash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                   salt, 100000)
    pwd_hash = binascii.hexlify(pwd_hash)
    return (salt + pwd_hash).decode('ascii')


def verify_password(stored_password: str, provided_password: str) -> bool:
    salt = stored_password[:64]
    stored_password = stored_password[64:]
    pwd_hash = hashlib.pbkdf2_hmac('sha512',
                                   provided_password.encode('utf-8'),
                                   salt.encode('ascii'),
                                   100000)
    pwd_hash = binascii.hexlify(pwd_hash).decode('ascii')
    return pwd_hash == stored_password


def get_todos(today_date: str, db_cursor, lock):
    day, month, year = separate_day_month_year(today_date)
    months_beginning = get_months_beginning(month, year)
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM todoList WHERE date < ? and done = 'false' """, (today_date,))
    all_due_events = sorted(db_cursor.fetchall(), key=lambda tup: tup[1])

    db_cursor.execute("""SELECT * FROM todoList WHERE date < ? and date >= ? and done = 'true'""",
                      (today_date, months_beginning.date()))
    all_due_events += sorted(db_cursor.fetchall(), key=lambda tup: tup[1])

    db_cursor.execute("""SELECT * FROM todoList WHERE date >= ? and date < ? """,
                      (get_next_day(today_date), get_thirty_days_from_now(day, month, year)))
    this_months_events = sorted(db_cursor.fetchall(), key=lambda tup: tup[1])

    db_cursor.execute("""SELECT * FROM todoList WHERE date = ? """, (today_date,))
    today_todos = db_cursor.fetchall()
    lock.release()
    return all_due_events, this_months_events, today_todos


def get_scrum_tasks(today_date: str, db_cursor, lock):
    day, month, year = separate_day_month_year(today_date)
    months_beginning = get_months_beginning(month, year)
    number_of_days = number_of_days_in_month(int(month), int(year))
    months_end = get_months_end(month, year)
    scrum_board_lists = {}
    for stage in ["backlog", "todo", "in progress", "done"]:
        lock.acquire(True)
        db_cursor.execute("""SELECT * FROM scrumBoard WHERE stage = ? """, (stage,))
        # sort based on priority
        scrum_board_lists[stage] = sorted([(task, proj, priority) for task, proj, stage, priority, done_date in
                                           db_cursor.fetchall()], key=lambda x: x[2])
        lock.release()

    # find all the tasks done during this month's period!
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM scrumBoard WHERE done_date >= ? and done_date <= ? """,
                      (months_beginning.date(), months_end.date()))
    done_tasks = sorted([int(done_date.split("-")[2]) for proj, task, stage, priority, done_date in
                         db_cursor.fetchall()])
    lock.release()
    current_done = 0
    chart_done_tasks = []
    for i in range(1, number_of_days+1):
        current_done += done_tasks.count(i)
        chart_done_tasks.append(current_done)
    chart_month_days = [str(i) for i in range(1, number_of_days+1)]
    if today_date == str(datetime.date.today()):
        this_month_tasks_num = len(scrum_board_lists["done"]) + len(scrum_board_lists["in progress"]) + \
                               len(scrum_board_lists["todo"])
    else:
        this_month_tasks_num = chart_done_tasks[-1]
    chart_this_month_tasks = [this_month_tasks_num for _ in range(number_of_days)]
    return scrum_board_lists, chart_done_tasks, chart_month_days, chart_this_month_tasks


def delete_scrum_task(proj: str, task: str, db_cursor, db_connection, lock):
    try:
        logger.info("deleting card:" + task)
        lock.acquire(True)
        db_cursor.execute("""DELETE from scrumBoard where project = ? and task = ?""", (proj, task))
        db_connection.commit()
        lock.release()
        return True
    except Exception as err:
        print(f"delete_scrum_task failed with error: {err}")
        return False


def add_scrum_task(proj: str, task: str, list_name: str, priority: str, date: str, db_cursor, db_connection, lock):
    try:
        lock.acquire(True)
        db_cursor.execute("""INSERT INTO scrumBoard VALUES(?, ?, ?, ?, ?)""", (proj, task, list_name, priority, date))
        db_connection.commit()
        lock.release()
        return True
    except Exception as err:
        print(f"add_scrum_task failed with error: {err}")
        return False


def send_mail(msg_subject: str, msg_content: str, flask_app, mail_instance, db_cursor, lock):
    server_email = fetch_setting_param_from_db(db_cursor, "MAIL_USERNAME", lock)
    app_password = fetch_setting_param_from_db(db_cursor, "MAIL_PASSWORD", lock)
    mail_server = fetch_setting_param_from_db(db_cursor, "MAIL_SERVER", lock)
    mail_port = fetch_setting_param_from_db(db_cursor, "MAIL_PORT", lock)
    mail_ssl = fetch_setting_param_from_db(db_cursor, "MAIL_USE_SSL", lock)
    recipient_email = fetch_setting_param_from_db(db_cursor, "MAIL_RECIPIENT", lock)
    logger.info("sending email to: " + recipient_email)
    if (server_email != "None") and (app_password != "None") and (recipient_email != "None"):
        flask_app.config.update(
            MAIL_SERVER=str(mail_server),
            MAIL_PORT=int(mail_port),
            MAIL_USE_SSL=bool(mail_ssl),
            MAIL_USERNAME=server_email,
            MAIL_PASSWORD=app_password
        )
        mail_instance.init_app(flask_app)
        mail_instance.send_message(
            msg_subject,
            sender=str(server_email),
            recipients=[str(recipient_email)],
            body=msg_content
        )
    logger.info("email sent!")
    return 'Mail sent'


def add_tag_to_picture(filename: str, tag: str):
    metadata = ImageMetadata(filename)
    metadata.read()
    current_tags = []
    if 'Exif.Photo.UserComment' in metadata:
        userdata = json.loads(metadata['Exif.Photo.UserComment'].value)
        if userdata["tags"] is not None:
            current_tags = list(userdata["tags"])
    tags = [tag] + current_tags
    metadata = ImageMetadata(filename)
    metadata.read()
    userdata = {'tags': tags}
    metadata['Exif.Photo.UserComment'] = json.dumps(userdata)
    metadata.write()
    return True


def remove_tag_from_picture(filename: str, tag: str):
    metadata = ImageMetadata(filename)
    metadata.read()
    if 'Exif.Photo.UserComment' not in metadata:
        print("Exif.Photo.UserComment does not exist in metadata")
        return False
    userdata = json.loads(metadata['Exif.Photo.UserComment'].value)
    current_tags = [] if userdata["tags"] is not None else list(userdata["tags"])
    if len(current_tags) > 0:
        current_tags.remove(tag)
    metadata = ImageMetadata(filename)
    metadata.read()
    userdata = {'tags': current_tags}
    metadata['Exif.Photo.UserComment'] = json.dumps(userdata)
    metadata.write()
    return True


def clean_db(table_name: str, db_connection, db_cursor, lock):

    lock.acquire(True)
    db_cursor.execute("SELECT * FROM "+table_name)
    fetched_data = db_cursor.fetchall()

    tracker_dictionary = {}

    for item in fetched_data:
        date = item[1]
        value = item[0]
        old_value = tracker_dictionary.get(str(date), [])
        tracker_dictionary[date] = old_value + [value]

    for key in tracker_dictionary:
        date = key
        value = tracker_dictionary[key]

        db_cursor.execute("SELECT * FROM tracker WHERE date = ?", (date,))
        fetched_data = db_cursor.fetchall()
        if len(fetched_data) == 0:
            db_cursor.execute("INSERT INTO tracker VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                              (date, "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan",
                               "nan", "nan", "nan", "nan"))
            db_connection.commit()

        db_cursor.execute("UPDATE tracker SET " + "activity_planner_name" + " = ? WHERE date = ?", (str(value), date,))
        db_connection.commit()
    lock.release()


class Login:
    def __init__(self):
        print("initializing user login...")
        self.is_logged_in = False

    def verify_user(self, db_pw, user_pw):
        if (db_pw == "None") or verify_password(db_pw, user_pw):
            self.is_logged_in = True
            print("login successful!")
            return True
        print("login attempt failed!")
        self.is_logged_in = False
        return False

    def logout(self):
        print("user is logged out!")
        self.is_logged_in = False


def get_today_weather_information(db_connection, lock) -> dict:
    if temporary_data.get("weather_info", {"date": None}).get("date", None) == datetime.date.today():
        # weather info already exists
        return temporary_data["weather_info"]
    else:
        latitude = fetch_setting_param_from_db(db_connection, "latitude", lock)
        longitude = fetch_setting_param_from_db(db_connection, "longitude", lock)
        app_id = fetch_setting_param_from_db(db_connection, "weather_appid", lock)
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": app_id,
            "units": "metric"
        }

        response = requests.get(url="https://api.openweathermap.org/data/2.5/onecall", params=params)
        response.raise_for_status()
        json_resp = response.json()["current"]
        sunrise = datetime.datetime.fromtimestamp(json_resp["sunrise"]).time()
        sunset = datetime.datetime.fromtimestamp(json_resp["sunset"]).time()
        temp = json_resp["temp"]
        feels_like = json_resp["feels_like"]
        pressure = json_resp["pressure"]
        humidity = json_resp["humidity"]
        uvi = json_resp["uvi"]
        wind_speed = json_resp["wind_speed"]

        temporary_data["weather_info"] = {"date": datetime.date.today(),
                                          "temp": temp, "feels_like": feels_like,
                                          "pressure": pressure, "humidity": humidity,
                                          "uvi": uvi, "wind_speed": wind_speed,
                                          "sunset": sunset, "sunrise": sunrise}
    return temporary_data["weather_info"]


def generate_month_spending_data(page_month, page_year, db_cursor, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM finance WHERE date >= ? and date <= ?  """,
                      (get_months_beginning(page_month, page_year).date(),
                       get_months_end(page_month, page_year).date(),))
    months_vals = db_cursor.fetchall()
    lock.release()
    return months_vals