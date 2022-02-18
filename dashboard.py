from functionPackages.ha_package import *
from functionPackages.misc import *
from functionPackages.charts import *
from functionPackages.dateTime import *

from pathlib import Path
import datetime
from package import *
from flask import Flask, request, url_for, redirect
from flask import send_from_directory
from flask_restful import reqparse, Api, Resource
from flask import render_template, make_response
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from werkzeug import secure_filename
import json
import os
from random import randint
import logging
from logging.handlers import RotatingFileHandler
from flask_mail import Mail
import time
from threading import Lock

app = Flask(__name__, template_folder='template', static_url_path='/static')
api = Api(app)
mail = Mail()

try:
    os.mkdir("./logs")
except Exception as error:
    print(error)

logfile = "logs/log.log"
log = logging.getLogger(__name__)
logging.basicConfig(filename=logfile,
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
handler = RotatingFileHandler(logfile, maxBytes=1024, backupCount=1)
log.addHandler(handler)

parser = reqparse.RequestParser()
for item in ['tracker_type', 'value', 'oldValue', 'date', 'action', 'type', 'planner']:
    parser.add_argument(item)

lock = Lock()

conn, c = createDB("journal.db")
conn_ha, c_ha = createDB("ha.db")
backupDatabase(conn)
generateDBTables(c, conn, lock)
generate_ha_DBTables(c_ha, conn_ha, lock)
setupSettingTable(c, conn, lock)


class Dash(Resource):
    @staticmethod
    def get():
        start_time = time.time()
        args = parser.parse_args()
        try:
            page_theme = fetchSettingParamFromDB(c, "Theme", lock)
        except Exception as err:
            log.error(err)
            page_theme = "Dark"
            logger.info("could not fetch page theme! replacing with default values")
        activity_list = fetchSettingParamFromDB(c, "activityList", lock).replace(" ", "").split(",")
        if args['date'] is not None:
            page_year, page_month, page_day = args['date'].split("-")
        else:
            page_month = str(datetime.date.today().month).zfill(2)
            page_year = str(datetime.date.today().year)

        headers = {'Content-Type': 'text/html'}
        page_title = "DashBoard"

        title_date = weeks_of_the_year[int(page_month) - 1] + "-" + page_year
        number_of_days = number_of_days_in_month(int(page_month), int(page_year))
        months_beginning_week_day = datetime.datetime.strptime(f"{page_year}-{page_month}-01", '%Y-%m-%d').weekday()
        # moodTrackerDays is a list that contains a bunch of Nones for the days of the week that are in the
        # previous month. this is used for the mood-tracker in order to add the empty spaces in the beginning of the
        # month.
        mood_tracker_days = [None for _ in range(0, months_beginning_week_day)] + list(range(1, number_of_days + 1))
        # list of current month's moods and activities.
        months_activities, months_activities_planned, months_moods = collectMonthsData(int(page_month), int(page_year),
                                                                                       c, lock)
        years_activities = collect_yearly_activities(int(page_year), c, lock)
        # highlights the current day in the activity tracker page!
        highlight = shouldHighlight(page_year, page_month)
        counter_value = fetchSettingParamFromDB(c, "counter", lock)

        chart_data = get_chart_data(page_month, page_year, number_of_days, c, lock)

        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('index.html', name=page_title, titleDate=title_date,
                                             PageYear=int(page_year), PageMonth=int(page_month),
                                             today=datetime.date.today().day, moods=months_moods,
                                             # charts info
                                             ChartMonthDays=chart_data["ChartMonthDays"],
                                             ChartYearMonths=weeks_of_the_year,
                                             ChartData=chart_data, HideLine="false",
                                             # ----------------------
                                             activities=months_activities,
                                             monthsActivitiesPlanned=months_activities_planned,
                                             activityList=activity_list, days=mood_tracker_days, highlight=highlight,
                                             yearsActivities=years_activities,
                                             pageTheme=page_theme, counterValue=counter_value), 200, headers)

    @staticmethod
    def post():
        activity_list = fetchSettingParamFromDB(c, "activityList", lock).replace(" ", "").split(",")
        args = parser.parse_args()
        if args['type'] == "password":
            password = fetchSettingParamFromDB(c, "password", lock)
            if password == "None":
                return "success", 200
            else:
                if not verifyPassword(password, args['value']):
                    return "failed", 200
                else:
                    return "success", 200

        if args['type'] == "counter":
            counter_value = int(fetchSettingParamFromDB(c, "counter", lock))
            if args['value'] == "countup":
                counter_value += 1
            elif args['value'] == "reset":  # reset the counter
                counter_value = 0
            updateSettingParam(c, conn, "counter", counter_value, lock)

        today_date = parse_date(args['date'])
        delete_day = False
        if len(args['value'].strip()) == 0:
            delete_day = True
        if args['tracker_type'] in ['sleep', 'running', 'pace', 'step', 'weight', 'work', 'hydration']:
            return addTrackerItemToTable(args['value'].lower(), "", [], args['tracker_type'] + "Tracker", today_date,
                                         delete_day, True, c, conn, lock)
        if args['tracker_type'] in ['HR', 'BP']:
            return addTrackerItemToTable(args['value'].split(","), "", [], args['tracker_type'] + "Tracker", today_date,
                                         delete_day, True, c, conn, lock)
        if args['tracker_type'] == 'blood oxygen':
            return addTrackerItemToTable(args['value'].lower(), "", [], "oxygenTracker", today_date, delete_day, True,
                                         c, conn, lock)
        if args['tracker_type'] == 'saving':
            return addsSavingItemToTable(args['value'].lower(), today_date, c, conn, lock)
        if args['tracker_type'] == 'mortgage':
            return addsMortgageItemToTable(args['value'].lower(), today_date, c, conn, lock)
        if args['tracker_type'] == 'mood':
            return addTrackerItemToTable(args['value'].lower(), "mood_name", moodList, "moodTracker", today_date, False,
                                         False, c, conn, lock)
        if args['tracker_type'] == "activity":
            delete = True if args['action'] == "delete" else False
            if args['planner'] == "True":
                return addTrackerItemToTable(args['value'].lower(), "activity_name", activity_list, "activityPlanner",
                                             today_date, delete, False, c, conn, lock)
            else:
                return addTrackerItemToTable(args['value'].lower(), "activity_name", activity_list, "activityTracker",
                                             today_date, delete, False, c, conn, lock)
        if args['tracker_type'] == "travel":
            values = args['value'].split(",")
            addTravelItem(values[0], values[1], values[2], c, conn, lock)
        return "Done", 200


class Journal(Resource):
    @staticmethod
    def get():
        start_time = time.time()
        args = parser.parse_args()
        page_theme = fetchSettingParamFromDB(c, "Theme", lock)
        headers = {'Content-Type': 'text/html'}
        today_date = parse_date(args['date'])
        day, month, year = separate_day_month_year(today_date)
        photo_dir = os.getcwd() + "/static/photos/" + str(year) + "/" + today_date
        photo_dir2 = os.getcwd() + "/static/photos/" + str(year)
        days_with_photos = allDaysWithPhotos(photo_dir2, year, month)
        today_photos = allPotosInDir(photo_dir, year, today_date)
        today_log, today_log_text = getTodaysLogs(c, today_date, lock)
        number_of_days = number_of_days_in_month(int(month), int(year))
        months_beginning = get_months_beginning(month, year).weekday()

        lock.acquire(True)
        c.execute("""SELECT * FROM logTracker WHERE date >= ? and date <= ? """,
                  (get_months_beginning(month, year).date(), get_months_end(month, year).date(),))
        logged_days = [int(x[1].split("-")[2]) for x in c.fetchall()]
        lock.release()

        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('journal.html', numberOfDays=number_of_days,
                                             day=day, month=month, year=year, monthsBeginning=months_beginning,
                                             log=today_log, todaysLogText=today_log_text, todayPhotos=today_photos,
                                             logged_days=logged_days, daysWithPhotos=days_with_photos,
                                             pageTheme=page_theme),
                             200, headers)

    @staticmethod
    def post():
        args = parser.parse_args()
        if args['type'] == 'log':
            today_date = parse_date(args['date'])
            log_entry = args['value'].lower()

            lock.acquire(True)
            c.execute("""SELECT * FROM logTracker WHERE date = ? """, (today_date,))
            if len(c.fetchall()) > 0:
                c.execute("""DELETE from logTracker where date = ?""", (today_date,))
            c.execute("""INSERT INTO logTracker VALUES(?, ?)""", (log_entry, today_date))
            conn.commit()
            lock.release()

            logger.info(f"added log for date: {today_date}")
        if args['type'] == "photo":
            if args['action'] == "delete":
                file = "./static" + args['value'].split("/static")[1]
                if os.path.isfile(file):
                    os.remove(file)
                    parent_dir = "./static" + "/".join(args['value'].split("/static")[1].split("/")[:-1])
                    logger.info("parent Directory:", parent_dir)
                    if len(os.listdir(parent_dir)) == 0:
                        os.rmdir(parent_dir)
                else:
                    return "File Doesnt Exist!", 400
        if args['type'] == "tag":
            if args['action'] == "delete":
                value_dict = eval(args['value'])
                tags = value_dict["tag"]
                file_name = "./static/photos/" + value_dict["fileName"]
                if os.path.isfile(file_name):
                    remove_tag_from_picture(file_name, tags)
            else:
                value_dict = eval(args['value'])
                tags = value_dict["tag"]
                file_name = "./static/photos/" + value_dict["fileName"]
                if os.path.isfile(file_name):
                    add_tag_to_picture(file_name, tags)
        return "Done", 200


class Org(Resource):
    @staticmethod
    def get():
        start_time = time.time()
        page_theme = fetchSettingParamFromDB(c, "Theme", lock)

        headers = {'Content-Type': 'text/html'}
        args = parser.parse_args()
        today_date = parse_date(args['date'])
        day, month, year = separate_day_month_year(today_date)
        months_beginning = get_months_beginning(month, year)
        week_day = datetime.datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d').weekday()
        number_of_days = number_of_days_in_month(int(month), int(year))
        months_beginning_week_day = months_beginning.weekday()

        all_due_events, this_months_events, today_todos = getTodos(today_date, c, lock)
        scrum_board_lists, chart_done_tasks, chart_month_days, chart_this_month_tasks = \
            getScrumTasks(today_date, c, lock)

        cal_date = getCalEvents(today_date, c, lock)
        cal_month = getCalEventsMonth(today_date, c, lock)
        # ---------------------------
        header_dates = []
        day_val = datetime.datetime.strptime(today_date, '%Y-%m-%d') - datetime.timedelta(days=week_day)  # week's start
        for i in range(1, 8):
            header_dates.append(str(day_val.date()).split("-")[2])
            day_val = datetime.datetime.strptime(str(day_val.date()), '%Y-%m-%d') + datetime.timedelta(days=1)
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(
            render_template('org.html', day=day, month=month, year=year, weekDay=days_of_the_week[week_day],
                            monthsBeginning=months_beginning_week_day, todayTodos=today_todos, overDue=all_due_events,
                            numberOfDays=number_of_days, thisMonthsEvents=this_months_events, calDate=cal_date,
                            calMonth=cal_month, headerDates=header_dates,
                            Backlog=scrum_board_lists["backlog"], ScrumTodo=scrum_board_lists["todo"],
                            inProgress=scrum_board_lists["in progress"], done=scrum_board_lists["done"],
                            ChartMonthDays=chart_month_days, ChartDoneTasks=chart_done_tasks,
                            ChartthisMonthTasks=chart_this_month_tasks, pageTheme=page_theme), 200, headers)

    @staticmethod
    def post():
        args = parser.parse_args()
        if args['type'] == 'todo':
            if args['action'] == "search":
                value_dict = eval((args['value']))
                search_result = []
                search_term = value_dict["search_term"].strip().lower()
                if search_term != "":
                    search_term = "%" + search_term + "%"
                    lock.acquire(True)
                    c.execute("""SELECT * FROM todoList WHERE task like ? """, (search_term,))
                    search_result = sorted(c.fetchall(), key=lambda tup: tup[1], reverse=True)
                    lock.release()
                return search_result, 200
            else:
                date_val = parse_date(args['date'])
                value_dict = eval((args['value']))
                lock.acquire(True)
                c.execute("""DELETE from todoList where date = ? and task = ?""",
                          (date_val, value_dict['value'].lower()))
                if args['action'] == "delete":
                    logger.info(f"removed todo {value_dict['value'].lower()} from todoList for date: {date_val}")
                else:
                    c.execute("""INSERT INTO todoList VALUES(?, ?, ?, ?)""",
                              (value_dict['value'].lower(), date_val, value_dict['done'], value_dict['color']))
                    logger.info(
                        f"added todo {value_dict['value'].lower()} to todoList for date: {date_val} as "
                        f"{value_dict['done']}")
                conn.commit()
                lock.release()

        elif args['type'] == 'calendar':
            if args["action"] == "create":
                date_value = args['date']
                values = json.loads(args['value'])
                lock.acquire(True)
                c.execute("""INSERT INTO calendar VALUES(?, ?, ?, ?, ?, ?)""", (
                    date_value, values["startTime"], values["stopTime"], values["name"], values["color"],
                    values["details"]))
                conn.commit()
                lock.release()
            elif args["action"] == "delete":
                date_value = args['date']
                values = json.loads(args['value'])
                lock.acquire(True)
                c.execute(
                    """DELETE from calendar where date = ? and startTime = ? and endTime = ?  and eventName = ? """,
                    (date_value, values["startTime"], values["stopTime"], values["name"]))
                conn.commit()
                lock.release()
            elif args["action"] == "edit":
                lock.acquire(True)
                values = json.loads(args['oldValue'])
                new_values = json.loads(args['value'])
                c.execute(
                    """DELETE from calendar where date = ? and startTime = ? and endTime = ?  and eventName = ? """,
                    (values["date"], values["startTime"], values["stopTime"], values["name"]))
                c.execute("""INSERT INTO calendar VALUES(?, ?, ?, ?, ?, ?)""", (
                    new_values["date"], new_values["startTime"], new_values["stopTime"], new_values["name"],
                    new_values["color"], new_values["details"]))
                conn.commit()
                lock.release()
        elif args['type'] == "scrum":
            scrum_dict = eval((args['value']))
            proj = scrum_dict['cardProj']
            task = scrum_dict['cardTask']
            if scrum_dict.get('currentList', None) is not None:
                current_list = scrum_dict['currentList']
                if scrum_dict.get('action', "") == "delete":
                    deleteScrumTask(proj, task, c, conn, lock)
                else:
                    destination_list = scrum_dict.get('destList', "")
                    lock.acquire(True)
                    c.execute("""SELECT * FROM scrumBoard WHERE project = ? and task = ? and stage = ? """,
                              (proj, task, current_list))
                    tasks = c.fetchall()
                    lock.release()
                    if len(tasks) > 0:
                        priority = tasks[0][-2]
                    else:
                        priority = scrum_dict.get('priority', "")
                    if destination_list == "done":
                        deleteScrumTask(proj, task, c, conn, lock)
                        addScrumTask(proj, task, destination_list, priority, str(datetime.date.today()), c, conn, lock)
                    elif destination_list == "archive":
                        lock.acquire(True)
                        c.execute("""SELECT * FROM scrumBoard WHERE project = ? and task = ? """, (proj, task))
                        date_value = c.fetchall()[0][-1]
                        lock.release()
                        deleteScrumTask(proj, task, c, conn, lock)
                        addScrumTask(proj, task, destination_list, priority, str(date_value), c, conn, lock)
                    else:
                        deleteScrumTask(proj, task, c, conn, lock)
                        addScrumTask(proj, task, destination_list, priority, " ", c, conn, lock)
                    conn.commit()
            else:  # it is a new card!
                priority = scrum_dict['priority']
                addScrumTask(proj, task, "backlog", priority, " ", c, conn, lock)
        return "Done", 200


class Settings(Resource):
    @staticmethod
    def get():
        headers = {'Content-Type': 'text/html'}
        page_theme = fetchSettingParamFromDB(c, "Theme", lock)
        activity_list = fetchSettingParamFromDB(c, "activityList", lock)
        audiobooks_path = fetchSettingParamFromDB(c, "audiobooksPath", lock)

        mail_username = fetchSettingParamFromDB(c, "MAIL_USERNAME", lock)
        mail_server = fetchSettingParamFromDB(c, "MAIL_SERVER", lock)
        mail_port = fetchSettingParamFromDB(c, "MAIL_PORT", lock)
        mail_ssl = fetchSettingParamFromDB(c, "MAIL_USE_SSL", lock)
        recipient_email = fetchSettingParamFromDB(c, "MAIL_RECIPIENT", lock)
        enable_daily_digest = fetchSettingParamFromDB(c, "EnableDailyDigest", lock)
        enable_event_notifications = fetchSettingParamFromDB(c, "EnableEventNotifications", lock)
        email_setting = {"MAIL_USERNAME": mail_username,
                         "MAIL_SERVER": mail_server,
                         "MAIL_PORT": mail_port,
                         "MAIL_USE_SSL": mail_ssl,
                         "MAIL_PASSWORD": "mail pass",
                         "MAIL_RECIPIENT": recipient_email,
                         "EnableEventNotifications": enable_event_notifications,
                         "EnableDailyDigest": enable_daily_digest
                         }
        return make_response(render_template('settings.html', activityList=activity_list,
                                             audiobooksPath=audiobooks_path, pageTheme=page_theme,
                                             email_setting=email_setting), 200, headers)

    @staticmethod
    def post():
        args = parser.parse_args()
        if args['type'] == "Theme":
            page_theme = args['value']
            updateSettingParam(c, conn, "Theme", page_theme, lock)
        if args['type'] == "activityList":
            activity_list = args['value']
            updateSettingParam(c, conn, "activityList", activity_list, lock)
        if args['type'] == "password":
            pass_dict = eval((args['value']))
            hashed_password = fetchSettingParamFromDB(c, "password", lock)
            if (hashed_password == "None") or verifyPassword(hashed_password, pass_dict["currntpwd"]):
                updateSettingParam(c, conn, "password", hashPassword(pass_dict["newpwd"]), lock)
                return "succeeded", 200
            return "failed", 200
        if args['type'] == "audiobooksPath":
            updateSettingParam(c, conn, "audiobooksPath", args['value'], lock)
            source = Path(args['value'])
            destination = Path("./static/audiobooks/").resolve()
            os.symlink(source, destination)
            return "succeeded", 200
        if args['type'] == "mailSetting":
            value_dict = eval((args['value']))
            for setting_item in value_dict:
                if setting_item != "MAIL_PASSWORD":
                    updateSettingParam(c, conn, setting_item, value_dict[setting_item], lock)
                else:
                    if value_dict[setting_item] != "mailpass":
                        updateSettingParam(c, conn, setting_item, value_dict[setting_item], lock)
            return "succeeded", 200
        if args['type'] == "EnableDailyDigest":
            updateSettingParam(c, conn, "EnableDailyDigest", args['value'], lock)
            return "succeeded", 200
        if args['type'] == "EnableEventNotifications":
            updateSettingParam(c, conn, "EnableEventNotifications", args['value'], lock)
            return "succeeded", 200
        return "Done", 200


class Gallery(Resource):
    @staticmethod
    def get():
        start_time = time.time()
        args = parser.parse_args()
        headers = {'Content-Type': 'text/html'}
        page_theme = fetchSettingParamFromDB(c, "Theme", lock)
        today_date = parse_date(args['date'])
        day, month, year = separate_day_month_year(today_date)
        number_of_days = number_of_days_in_month(int(month), int(year))
        months_beginning = get_months_beginning(month, year).weekday()
        months_photos = []
        for day_number in range(1, number_of_days + 1):
            date_value = str(year) + "-" + str(month).zfill(2) + "-" + str(day_number).zfill(2)
            photo_dir = os.getcwd() + "/static/photos/" + str(year) + "/" + date_value
            today_photos = allPotosInDir(photo_dir, year, date_value)
            months_photos.append(today_photos)
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('gallery.html', day=day, month=month, year=year,
                                             numberOfDays=number_of_days, monthsBeginning=months_beginning,
                                             monthsPhotos=months_photos,
                                             pageTheme=page_theme), 200, headers)

    @staticmethod
    def post():
        return "Done", 200


class Lists(Resource):
    @staticmethod
    def get():
        start_time = time.time()
        headers = {'Content-Type': 'text/html'}
        page_theme = fetchSettingParamFromDB(c, "Theme", lock)
        lists = {}

        lock.acquire(True)
        c.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("lists",))
        list_names = [x.strip() for x in c.fetchall()[0][1].split(",")]
        lock.release()

        lock.acquire(True)
        for listName in list_names:
            c.execute("""SELECT * FROM lists WHERE type = ? """, (listName,))
            data = c.fetchall()
            lists[listName] = sorted(sorted([(name, done, note) for name, done, list_type, note in data]),
                                     key=lambda x: x[1])
        lock.release()

        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('lists.html', lists=lists, readList=lists["book"],
                                             animeList=lists["anime"], movieList=lists["movie"],
                                             bucketList=lists["bucketList"],
                                             toLearnList=lists["toLearn"],
                                             pageTheme=page_theme), 200, headers)

    @staticmethod
    def post():
        args = parser.parse_args()
        if args['action'] == "create list":
            list_name = eval(args['value'])["listName"]
            lock.acquire(True)
            c.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("lists",))
            list_names = [x.strip() for x in c.fetchall()[0][1].split(",")] + [list_name]
            c.execute("UPDATE settings SET value = ? WHERE parameter = ?", (",".join(list_names), "lists",))
            conn.commit()
            lock.release()
            return "Done", 200

        if args['action'] == "delete list":
            list_name = eval(args['value'])["listName"]
            lock.acquire(True)
            c.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("lists",))
            list_names = [x.strip() for x in c.fetchall()[0][1].split(",")]
            list_names.remove(list_name)
            c.execute("UPDATE settings SET value = ? WHERE parameter = ?", (",".join(list_names), 'lists',))
            c.execute("""DELETE from lists where type = ? """, (list_name,))
            conn.commit()
            lock.release()
            return "Done", 200

        lock.acquire(True)
        if args['action'] == "delete":
            value_dict = eval((args['value']))
            logger.info(f"deleted {value_dict['name'].lower()} from {value_dict['type']}")
            c.execute("""DELETE from lists where name = ? and type = ?  """,
                      (value_dict["name"].lower(), value_dict["type"]))
        else:
            value_dict = eval((args['value']))
            logger.info(f"added {value_dict['name'].lower()} to {value_dict['type']} as {value_dict['done']} ")
            c.execute("""DELETE from lists where name = ? and type = ? """,
                      (value_dict["name"].lower(), value_dict["type"]))
            c.execute("""INSERT INTO lists VALUES(?, ?, ?, ?)""",
                      (value_dict["name"].lower(), value_dict["done"], value_dict["type"], value_dict["notes"]))
        conn.commit()
        lock.release()
        return "Done", 200


class Notes(Resource):
    @staticmethod
    def get():
        start_time = time.time()
        headers = {'Content-Type': 'text/html'}
        page_theme = fetchSettingParamFromDB(c, "Theme", lock)
        notebooks = fetchNotebooks(c, lock)
        photo_dir = os.getcwd() + "/static/photos/notebookPhotos"
        photos = {}
        for root, dirs, files in os.walk(photo_dir):
            if len(root.split("notebookPhotos/")) > 1:
                for filename in files:
                    notebook_name = root.split("notebookPhotos/")[1]
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.mp4')):
                        photos[notebook_name] = photos.get(notebook_name, []) + [filename]
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('notes.html', pageTheme=page_theme, Notebooks=notebooks, photos=photos),
                             200, headers)

    @staticmethod
    def post():
        args = parser.parse_args()
        value_dict = eval((args['value']))
        if args['action'] == "delete":
            lock.acquire(True)
            if value_dict.get("chapter", None) is not None:
                logger.info(f"deleting the chapter {value_dict['chapter']} from notebook: {value_dict['notebook']}")
                c.execute("""DELETE from Notes where Notebook = ? and  Chapter = ? """,
                          (value_dict["notebook"], value_dict["chapter"],))
            else:
                logger.info(f"deleting the notebook: {value_dict['notebook']}")
                c.execute("""DELETE from Notes where Notebook = ? """, (value_dict["notebook"],))
            conn.commit()
            lock.release()
        elif args['action'] == "rename":
            parsed_json = json.loads(args['value'])
            if (parsed_json["type"] == "noteBookName") and (parsed_json["oldName"] != parsed_json["newName"]):
                lock.acquire(True)
                c.execute("""SELECT * FROM Notes WHERE Notebook = ?""", (parsed_json["oldName"],))
                all_notes = c.fetchall()
                lock.release()

                lock.acquire(True)
                for x in all_notes:
                    content = x[2]
                    # rename the folder that holds the files inside the references of it...
                    while "static/photos/notebookPhotos/" + parsed_json["oldName"] + "/" in content:
                        content = content.replace("static/photos/notebookPhotos/" + parsed_json["oldName"] + "/",
                                                  "static/photos/notebookPhotos/" + parsed_json["newName"] + "/")
                    c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (parsed_json["newName"], x[1], content))
                conn.commit()
                lock.release()

                lock.acquire(True)
                for x in all_notes:
                    c.execute("""DELETE from Notes where Notebook = ? and Chapter = ? and content = ? """,
                              (parsed_json["oldName"], x[1], x[2]))
                conn.commit()
                lock.release()

                # rename the folder that holds the files
                if os.path.isdir("./static/photos/notebookPhotos/" + parsed_json["oldName"]):
                    os.rename("./static/photos/notebookPhotos/" + parsed_json["oldName"],
                              "./static/photos/notebookPhotos/" + parsed_json["newName"])
                return "all good!", 200

            if (parsed_json["type"] == "chapterName") and (parsed_json["oldName"] != parsed_json["newName"]):
                lock.acquire(True)
                c.execute("""SELECT * FROM Notes WHERE Notebook = ? and Chapter = ? """,
                          (parsed_json["noteBookName"], parsed_json["oldName"],))
                all_notes = c.fetchall()
                for x in all_notes:
                    c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (x[0], parsed_json["newName"], x[2]))
                    c.execute("""DELETE from Notes where Notebook = ? and Chapter = ? and content = ? """,
                              (x[0], parsed_json["oldName"], x[2]))
                conn.commit()
                lock.release()
                return "all good!", 200
        else:
            lock.acquire(True)
            c.execute("""DELETE from Notes where Notebook = ? and Chapter = ?  """,
                      (value_dict["notebook"], value_dict["chapter"]))
            c.execute("""INSERT into Notes VALUES(?, ?, ?)  """,
                      (value_dict["notebook"], value_dict["chapter"], value_dict['entry']))
            conn.commit()
            lock.release()
        return "nothing here!", 200


class Learning(Resource):
    @staticmethod
    def get():
        headers = {'Content-Type': 'text/html'}
        page_theme = fetchSettingParamFromDB(c, "Theme", lock)
        set_names, max_days_numbers, cnts, flash_cards = getFlashCards(c, lock)
        max_days_numbers = list(range(1, max_days_numbers + 1))
        counters = []
        for i in max_days_numbers:
            if i in cnts.keys():
                counters.append(cnts[i])
            else:
                counters.append(0)
        return make_response(render_template('learning.html', pageTheme=page_theme, setNames=set_names,
                                             flashCards=flash_cards, maxDaysNumbers=max_days_numbers,
                                             countes=counters), 200, headers)

    @staticmethod
    def post():
        args = parser.parse_args()
        if args["type"] == "flashCards":
            if args["action"] == "create":
                values = json.loads(args['value'])
                set_name = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                last_time_reviewed = str(datetime.date.today())
                addFlashCards(set_name, side1, side2, last_time_reviewed, c, conn, lock)
            elif args["action"] == "delete":
                values = json.loads(args['value'])
                set_name = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                deleteFlashCards(set_name, side1, side2, c, conn, lock)
            else:
                values = json.loads(args['value'])
                set_name = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                last_time_reviewed = str(datetime.date.today())
                if args["action"] == "true":
                    changeFlashCards(set_name, side1, side2, last_time_reviewed, True, c, conn, lock)
                else:
                    changeFlashCards(set_name, side1, side2, last_time_reviewed, False, c, conn, lock)
        return "Done", 200


class Server(Resource):
    @staticmethod
    def get():
        start_time = time.time()
        args = parser.parse_args()
        if args['date'] is not None:
            year, month, day = args['date'].split("-")
            today_date = "-".join([day, month, year[-2:]])
        else:
            today = datetime.date.today()
            day, month, year = today.day, today.month, today.year
            today_date = today.strftime('%d-%m-%y')

        headers = {'Content-Type': 'text/html'}
        page_theme = fetchSettingParamFromDB(c, "Theme", lock)

        cpu_temps, cpu_temps_times, cpu_usage, cpu_usage_times, disc_space, up_time = \
            generate_cpu_stat(today_date, year)
        cpu_temps_yearly, cpu_usage_yearly = generate_cpu_stat_monthly(year)
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('server.html', pageTheme=page_theme,
                                             cpuTemps=cpu_temps, cpuTempsTimes=cpu_temps_times,
                                             cpuUsage=cpu_usage, cpuUsageTimes=cpu_usage_times,
                                             cpuUsageYearly=cpu_usage_yearly, cpuTempsYearly=cpu_temps_yearly,
                                             upTime=up_time, HideLine="true", chart_months=chart_months,
                                             discSpace=disc_space, year=int(year), month=int(month), day=int(day),
                                             PageYear=1999, PageMonth=10), 200, headers)

    @staticmethod
    def post():
        return "Nothing to be posted!", 200


class Audiobooks(Resource):
    @staticmethod
    def get():
        start_time = time.time()
        headers = {'Content-Type': 'text/html'}
        page_theme = fetchSettingParamFromDB(c, "Theme", lock)
        path = "static/audiobooks/"
        try:
            audiobooks, metadata = getAudiobooks(path)
        except Exception as err:
            log.error(err)
            audiobooks = metadata = {}
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(
            render_template('audiobooks.html', audiobooks=audiobooks, metadata=metadata, pageTheme=page_theme), 200,
            headers)

    @staticmethod
    def post():
        args = parser.parse_args()
        value = json.loads(args['value'])
        metadata_file_path = "static/audiobooks/" + value["author"] + "/" + value["book"] + "/metadata.json"
        with open(metadata_file_path, "r") as metadataFile:
            data = json.load(metadataFile)
            data["chapter " + value["chapter"]]["timestamp"] = value["timestamp"]
            data["chapter " + value["chapter"]]["progress"] = value["progress"]
        metadataFile.close()
        with open(metadata_file_path, "w") as metadataFile:
            json.dump(data, metadataFile)
        metadataFile.close()
        return "Done", 200


class HomeAutomation(Resource):
    @staticmethod
    def get():
        start_time = time.time()
        args = parser.parse_args()
        if args['date'] is not None:
            year, month, day = args['date'].split("-")
            today_date = "-".join([year, month, day])
        else:
            today = datetime.date.today()
            day, month, year = today.day, today.month, today.year
            today_date = today.strftime('%Y-%m-%d')
        headers = {'Content-Type': 'text/html'}
        page_theme = fetchSettingParamFromDB(c, "Theme", lock)

        my_annual_consumption = generate_e_consumption_tracker_chart_data(str(year), c_ha, lock)
        monthly_data = generate_weather_monthly(c_ha, int(year), lock)
        daily_data, description = generate_weather_daily(c_ha, today_date, lock)
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('homeAutomation.html', daily_data=daily_data,
                                             monthly_Data=monthly_data, chart_months=chart_months,
                                             myAnnualConsumption=my_annual_consumption, description=description,
                                             pageTheme=page_theme, HideLine="true",
                                             PageYear=int(year), PageMonth=int(month), day=int(day), ), 200, headers)

    @staticmethod
    def post():
        args = parser.parse_args()
        value = json.loads(args['value'])
        if args['action'] == "rename":
            rename_room(str(value['roomNumber']), str(value['newValue']), c_ha, conn_ha, lock)
            return "Done", 200

        if args['tracker_type'] == "eConsumption":
            add_econsumption_data(args['date'], args['value'], c_ha, conn_ha, lock)
            return "Done", 200
        else:
            directory = "homeAutomation"
            if not os.path.exists(directory):
                os.makedirs(directory)
            directory = "homeAutomation/room_" + value['room']
            if not os.path.exists(directory):
                os.makedirs(directory)
            add_data_to_ha_DB(c_ha, conn_ha, value['room'], value['date'], value['hour'], value["temp"],
                              value["humidity"], value["pressure"], lock)
            return "Done", 200


@app.route("/downloadDB/")
def download_db():
    return send_from_directory(directory=".", filename="journal.db", as_attachment="True",
                               attachment_filename="sqlite_database.db")


@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        upload_date = request.form['date']
        year = upload_date.split("-")[0]
        folder_name = upload_date
        if not os.path.isdir("./static/photos/" + year):
            os.mkdir("./static/photos/" + year)
        if not os.path.isdir("./static/photos/" + year + "/" + folder_name):
            os.mkdir("./static/photos/" + year + "/" + folder_name)
        f = request.files['file']
        file_name = f.filename
        while os.path.isfile("./static/photos/" + year + "/" + folder_name + "/" + file_name):
            file_name = str(randint(1, 100000)) + "_" + f.filename
        f.save(os.path.join("./static/photos/" + year + "/" + folder_name, secure_filename(file_name)))
        return redirect(url_for('journal') + "?date=" + upload_date, 200)


@app.route('/notesUploader', methods=['GET', 'POST'])
def upload_file_notes():
    if request.method == 'POST':
        notebook_label = request.form['notebookLabel']
        if not os.path.isdir("./static/photos/notebookPhotos/"):
            os.mkdir("./static/photos/notebookPhotos/")
        if not os.path.isdir("./static/photos/notebookPhotos/" + notebook_label):
            os.mkdir("./static/photos/notebookPhotos/" + notebook_label)
        f = request.files['file']
        file_name = f.filename
        while os.path.isfile("./static/photos/notebookPhotos/" + notebook_label + "/" + file_name):
            file_name = str(randint(1, 100)) + "_" + f.filename
        f.save(os.path.join("./static/photos/notebookPhotos/" + notebook_label, secure_filename(file_name)))
        return redirect(url_for('notes'), 200)


@app.route('/shutdown', methods=['POST'])
def shutdown_server():
    if request.method == 'POST':
        logger.info("shutdown request received...")
        send_mail("Server:: shutting down", "shut down command received.", app, mail, c, lock)
        shutdown_req = request.environ.get('werkzeug.server.shutdown')
        if shutdown_req is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        shutdown_req()
        logger.info("closing the DB connection...")
        conn.close()
        logger.info("shutting down the server...")
        scheduler.shutdown()
        return "server is shutting down..."


def send_cal_notification():
    if fetchSettingParamFromDB(c, "EnableEventNotifications", lock) == "false":
        return
    with app.app_context():
        today_date = str(datetime.date.today())
        day, month, year = separate_day_month_year(today_date)
        lock.acquire(True)
        c.execute("""SELECT * FROM calendar WHERE date >= ? and date <= ?  """,
                  (get_months_beginning(month, year).date(),
                   get_months_end(month, year).date(),))
        cal_events = c.fetchall()
        lock.release()
        notifications_to_be_sent = []
        for event in cal_events:
            if event[0] == today_date:
                if event[1] != "None":
                    time_split = event[1].split(":")
                    now = datetime.datetime.now()
                    new_datetime = datetime.datetime.now().replace(hour=int(time_split[0]), minute=int(time_split[1]))
                    diff = new_datetime - now
                    minutes_diff = int(diff.total_seconds() / 60)
                    if (minutes_diff == 30) or (minutes_diff == 15):
                        notifications_to_be_sent.append(event)
        for notification in notifications_to_be_sent:
            body = "Event time: " + notification[1] + " - " + notification[2] + "\n" + \
                   "Event: " + notification[3] + "\n" + \
                   "Description: " + notification[5] + "\n"
            send_mail("Upcoming event: " + notification[3], body, app, mail, c, lock)


def send_daily_digest():
    if fetchSettingParamFromDB(c, "EnableDailyDigest", lock) == "false":
        return
    with app.app_context():
        today_date = str(datetime.date.today())
        lock.acquire(True)
        c.execute("""SELECT * FROM calendar WHERE date = ? """,
                  (today_date,))
        cal_events = c.fetchall()
        c.execute("""SELECT * FROM todoList WHERE date = ? """,
                  (today_date,))
        todos = c.fetchall()
        lock.release()
        body = "Here is your daily digest for:   " + today_date + "\n"
        body += "\n\nCalendar events:\n"
        for event in cal_events:
            body += "\t* Event: " + event[3] + "\n" + \
                    "\t         Event time: " + event[1] + " - " + event[2] + "\n" + \
                    "\t         Description: " + event[5] + "\n"
        body += "\n\nTODOs events:\n"
        for todo in todos:
            body += "\t* Todo: " + todo[0] + "\n"
            body += "\t       Status: " + ("Done" if todo[2] == "true" else "Not Done") + "\n"
        send_mail("Daily Digest for: " + today_date, body, app, mail, c, lock)


scheduler = BackgroundScheduler()
scheduler.add_job(func=send_cal_notification, trigger="interval", seconds=60)
scheduler.add_job(func=send_daily_digest, trigger=CronTrigger.from_crontab('0 6 * * *'))
scheduler.start()

api.add_resource(Dash, '/')
api.add_resource(Journal, '/journal')
api.add_resource(Org, '/org')
api.add_resource(Settings, '/settings')
api.add_resource(Lists, '/lists')
api.add_resource(Notes, '/notes')
api.add_resource(Gallery, '/gallery')
api.add_resource(Learning, '/learning')
api.add_resource(Server, '/server')
api.add_resource(Audiobooks, '/audiobooks')
api.add_resource(HomeAutomation, '/homeAutomation')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

conn.close()
