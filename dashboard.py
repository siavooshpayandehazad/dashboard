from functionPackages.ha_package import *
from functionPackages.misc import *
from functionPackages.charts import *
from functionPackages.dateTime import *

import sqlite3
import datetime
import sys
from package import *
from flask import Flask, request, url_for, redirect
from flask import send_from_directory
from flask_restful import reqparse, abort, Api, Resource
from flask import render_template, make_response
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from werkzeug import secure_filename
import requests
import json
import os
from random import randint
import logging
from logging.handlers import RotatingFileHandler
from flask_mail import Mail,  Message
import time
from threading import Lock


app = Flask(__name__, template_folder='template', static_url_path='/static')
api = Api(app)
mail = Mail()

try:
    os.mkdir("./logs")
except:
    pass
logfile = "logs/log.log"
log = logging.getLogger(__name__)
logging.basicConfig(filename = logfile,
                    level = logging.INFO,
                    format = '%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
handler = RotatingFileHandler(logfile, maxBytes=1024, backupCount=1)
log.addHandler(handler)

parser = reqparse.RequestParser()
for item in ['tracker_type', 'value', 'oldValue', 'date', 'action', 'type', 'planner']:
    parser.add_argument(item)

lock= Lock()

conn, c = createDB("journal.db")
conn_ha, c_ha = createDB("ha.db")
backupDatabase(conn)
generateDBTables(c, conn, lock)
generate_ha_DBTables(c_ha, conn_ha, lock)
setupSettingTable(c, conn, lock)



class dash(Resource):
    def get(self):
        start_time = time.time()
        args = parser.parse_args()
        try:
            pageTheme = fetchSettingParamFromDB(c, "Theme", lock)
            activityList = fetchSettingParamFromDB(c, "activityList", lock).replace(" ", "").split(",")
        except:
            pageTheme = "Dark"
            logger.info("could not fetch page theme! replacing with default values")
        if args['date'] is not None:
            pageYear, pageMonth, pageDay = args['date'].split("-")
        else:
            pageMonth = str(datetime.date.today().month).zfill(2)
            pageYear = str(datetime.date.today().year)

        headers      = {'Content-Type': 'text/html'}
        pageTitle    = "DashBoard"

        titleDate    = monthsOfTheYear[int(pageMonth)-1]+"-"+pageYear
        numberOfDays = numberOfDaysInMonth(int(pageMonth), int(pageYear))
        monthsBeginningWeekDay = datetime.datetime.strptime(f"{pageYear}-{pageMonth}-01", '%Y-%m-%d').weekday()
        # moodTrackerDays is a list that contains a bunch of Nones for the days of the week that are in the
        # previous month. this is used for the moodtracker in order to add the empty spaces in the beginning of the month.
        moodTrackerDays = [None for i in range(0, monthsBeginningWeekDay)] + list(range(1, numberOfDays+1))
        # list of current month's moods and activities.
        monthsActivities, monthsActivitiesPlanned, monthsMoods = collectMonthsData(int(pageMonth), int(pageYear), c, lock)
        # highlights the current day in the activity tracker page!
        highlight    = shouldHighlight(pageYear, pageMonth)
        counterValue = fetchSettingParamFromDB(c, "counter", lock)

        ChartData = getChartData(pageMonth, pageYear, numberOfDays, c, lock)

        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('index.html', name= pageTitle , titleDate = titleDate,
                                             PageYear = int(pageYear), PageMonth = int(pageMonth),
                                             today = datetime.date.today().day, moods = monthsMoods,
                                             # charts info
                                             ChartMonthDays = ChartData["ChartMonthDays"], ChartYearMonths = monthsOfTheYear,
                                             ChartData = ChartData, HideLine = "false",
                                             # ----------------------
                                             activities = monthsActivities, monthsActivitiesPlanned = monthsActivitiesPlanned,
                                             activityList = activityList, days=moodTrackerDays, highlight = highlight,
                                             pageTheme = pageTheme, counterValue = counterValue),200,headers)

    def post(self):
        activityList = fetchSettingParamFromDB(c, "activityList", lock).replace(" ", "").split(",")
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
            if args['value'] == "countup":
                counterVal = int(fetchSettingParamFromDB(c, "counter", lock)) + 1
            elif args['value'] == "reset":    # reset the counter
                counterVal = 0
            updateSettingParam(c, conn, "counter", counterVal, lock)

        todaysDate = parseDate(args['date'])
        deleteDay = False
        if (len(args['value'].strip()) == 0) :
            deleteDay = True
        if args['tracker_type'] in ['sleep', 'running', 'pace', 'step', 'weight', 'work', 'hydration']:
            return addTrackerItemToTable(args['value'].lower(), "", [], args['tracker_type']+"Tracker", todaysDate, deleteDay, True, c, conn, lock)
        if args['tracker_type'] in ['HR', 'BP']:
            return addTrackerItemToTable(args['value'].split(","), "", [], args['tracker_type']+"Tracker", todaysDate, deleteDay, True, c, conn, lock)
        if args['tracker_type'] == 'blood oxygen':
            return addTrackerItemToTable(args['value'].lower(), "", [], "oxygenTracker", todaysDate, deleteDay, True, c, conn, lock)
        if args['tracker_type'] == 'saving':
            return addsSavingItemToTable(args['value'].lower(), todaysDate, c, conn, lock)
        if args['tracker_type'] == 'mortgage':
            return addsMortgageItemToTable(args['value'].lower(), todaysDate, c, conn, lock)
        if args['tracker_type'] == 'mood':
            return addTrackerItemToTable(args['value'].lower(), "mood_name", moodList, "moodTracker", todaysDate, False, False, c, conn, lock)
        if args['tracker_type'] == "activity":
            delete = True if args['action']=="delete" else False
            if args['planner'] == "True":
                return addTrackerItemToTable(args['value'].lower(), "activity_name", activityList, "activityPlanner", todaysDate, delete, False, c, conn, lock)
            else:
                return addTrackerItemToTable(args['value'].lower(), "activity_name", activityList, "activityTracker", todaysDate, delete, False, c, conn, lock)
        if args['tracker_type'] == "travel":
            values = args['value'].split(",")
            addTravelItem(values[0], values[1], values[2], c, conn, lock)
        return "Done", 200


class journal(Resource):
    def get(self):
        start_time = time.time()
        args = parser.parse_args()
        pageTheme = fetchSettingParamFromDB(c, "Theme", lock)
        headers = {'Content-Type': 'text/html'}
        todaysDate = parseDate(args['date'])
        day, month, year = sparateDayMonthYear(todaysDate)
        photoDir=os.getcwd()+"/static/photos/"+str(year)+"/"+todaysDate
        photoDir2=os.getcwd()+"/static/photos/"+str(year)
        daysWithPhotos = allDaysWithPhotos(photoDir2, year, month)
        todayPhotos =  allPotosInDir(photoDir, year, todaysDate)
        todaysLog, todaysLogText = getTodaysLogs(c, todaysDate, lock)
        numberOfDays = numberOfDaysInMonth(int(month), int(year))
        monthsBeginning = getMonthsBeginning(month, year).weekday()

        lock.acquire(True)
        c.execute("""SELECT * FROM logTracker WHERE date >= ? and date <= ? """, (getMonthsBeginning(month, year).date(), getMonthsEnd(month, year).date(), ))
        logged_days = [int(x[1].split("-")[2]) for x in c.fetchall()]
        lock.release()

        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('journal.html', numberOfDays = numberOfDays,
                             day = day, month = month, year=year, monthsBeginning=monthsBeginning,
                             log = todaysLog, todaysLogText = todaysLogText, todayPhotos= todayPhotos,
                             logged_days = logged_days, daysWithPhotos = daysWithPhotos, pageTheme=pageTheme),
                             200,headers)

    def post(self):
        args = parser.parse_args()
        if args['type'] == 'log':
            todaysDate = parseDate(args['date'])
            log = args['value'].lower()

            lock.acquire(True)
            c.execute("""SELECT * FROM logTracker WHERE date = ? """, (todaysDate, ))
            if len(c.fetchall()) > 0:
                c.execute("""DELETE from logTracker where date = ?""", (todaysDate, ))
            c.execute("""INSERT INTO logTracker VALUES(?, ?)""", (log, todaysDate))
            conn.commit()
            lock.release()

            logger.info(f"added log for date: {todaysDate}")
        if args['type'] == "photo":
            if args['action'] == "delete":
                file = "./static"+args['value'].split("/static")[1]
                if os.path.isfile(file):
                    os.remove(file)
                    parentDir = "./static"+"/".join(args['value'].split("/static")[1].split("/")[:-1])
                    logger.info("parent Directory:", parentDir)
                    if len(os.listdir(parentDir))==0:
                        os.rmdir(parentDir)
                else:
                    return "File Doesnt Exist!", 400
        if args['type'] == "tag":
            if args['action'] == "delete":
                value_dict = eval(args['value'])
                tags = value_dict["tag"]
                fileName = "./static/photos/"+value_dict["fileName"]
                if os.path.isfile(fileName):
                    remove_tag_from_picture(fileName, tags)
            else:
                value_dict = eval(args['value'])
                tags = value_dict["tag"]
                fileName = "./static/photos/"+value_dict["fileName"]
                if os.path.isfile(fileName):
                    add_tag_to_picture(fileName, tags)
        return "Done", 200


class org(Resource):
    def get(self):
        start_time = time.time()
        pageTheme = fetchSettingParamFromDB(c, "Theme", lock)

        headers = {'Content-Type': 'text/html'}
        args = parser.parse_args()
        todaysDate = parseDate(args['date'])
        day, month, year = sparateDayMonthYear(todaysDate)
        monthsBeginning = getMonthsBeginning(month, year)
        weekDay = datetime.datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d').weekday()
        numberOfDays = numberOfDaysInMonth(int(month), int(year))
        monthsBeginningWeekDay = monthsBeginning.weekday()

        all_due_events, thisMonthsEvents, todayTodos =  getTodos(todaysDate, c, lock)
        scrumBoardLists, ChartDoneTasks, ChartMonthDays, ChartthisMonthTasks = getScrumTasks(todaysDate, c, lock)

        calDate = getCalEvents(todaysDate, c, lock)
        calMonth = getCalEventsMonth(todaysDate, c, lock)
        #---------------------------
        headerDates = []
        dayVal= datetime.datetime.strptime(todaysDate, '%Y-%m-%d')-datetime.timedelta(days=weekDay) # weekstart
        for i in range(1, 8):
            headerDates.append(str(dayVal.date()).split("-")[2])
            dayVal = datetime.datetime.strptime(str(dayVal.date()), '%Y-%m-%d')+datetime.timedelta(days=1)
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('org.html', day = day, month = month, year=year, weekDay = daysOfTheWeek[weekDay],
                                             monthsBeginning=monthsBeginningWeekDay, todayTodos=todayTodos, overDue = all_due_events,
                                             numberOfDays=numberOfDays, thisMonthsEvents = thisMonthsEvents, calDate = calDate, calMonth = calMonth,
                                             headerDates = headerDates,
                                             Backlog = scrumBoardLists["backlog"], ScrumTodo=scrumBoardLists["todo"],
                                             inProgress=scrumBoardLists["in progress"], done=scrumBoardLists["done"],
                                             ChartMonthDays = ChartMonthDays, ChartDoneTasks=ChartDoneTasks,
                                             ChartthisMonthTasks= ChartthisMonthTasks, pageTheme=pageTheme),200,headers)

    def post(self):
        args = parser.parse_args()
        if args['type'] == 'todo':
            if args['action'] == "search":
                value_dict = eval((args['value']))
                search_result = []
                search_term = value_dict["search_term"].strip().lower()
                if search_term  != "":
                    search_term = "%"+search_term+"%"
                    lock.acquire(True)
                    c.execute("""SELECT * FROM todoList WHERE task like ? """, (search_term,))
                    search_result = sorted(c.fetchall(), key=lambda tup: tup[1], reverse = True)
                    lock.release()
                return search_result, 200
            else:
                dateVal = parseDate(args['date'])
                value_dict = eval((args['value']))
                lock.acquire(True)
                c.execute("""DELETE from todoList where date = ? and task = ?""", (dateVal, value_dict['value'].lower()))
                if args['action'] == "delete":
                    logger.info(f"removed todo {value_dict['value'].lower()} from todoList for date: {dateVal}")
                else:
                    c.execute("""INSERT INTO todoList VALUES(?, ?, ?, ?)""", (value_dict['value'].lower(), dateVal, value_dict['done'], value_dict['color']))
                    logger.info(f"added todo {value_dict['value'].lower()} to todoList for date: {dateVal} as {value_dict['done']}")
                conn.commit()
                lock.release()

        elif args['type'] == 'calendar':
            if args["action"] == "create":
                date = args['date']
                values = json.loads(args['value'])
                lock.acquire(True)
                c.execute("""INSERT INTO calendar VALUES(?, ?, ?, ?, ?, ?)""", (date, values["startTime"], values["stopTime"], values["name"], values["color"], values["details"]))
                conn.commit()
                lock.release()
            elif args["action"] == "delete":
                date = args['date']
                values = json.loads(args['value'])
                lock.acquire(True)
                c.execute("""DELETE from calendar where date = ? and startTime = ? and endTime = ?  and eventName = ? """, (date, values["startTime"], values["stopTime"], values["name"]))
                conn.commit()
                lock.release()
            elif args["action"] == "edit":
                date = args['date']
                lock.acquire(True)
                values = json.loads(args['oldValue'])
                c.execute("""DELETE from calendar where date = ? and startTime = ? and endTime = ?  and eventName = ? """, (values["date"], values["startTime"], values["stopTime"], values["name"]))
                values = json.loads(args['value'])
                c.execute("""INSERT INTO calendar VALUES(?, ?, ?, ?, ?, ?)""", (values["date"], values["startTime"], values["stopTime"], values["name"], values["color"], values["details"]))
                conn.commit()
                lock.release()

        elif args['type'] == "scrum":
            scrum_dict = eval((args['value']))
            proj = scrum_dict['cardProj']
            task = scrum_dict['cardTask']
            if scrum_dict.get('currentList', None) is not None:
                currentList = scrum_dict['currentList']
                if scrum_dict.get('action', "") == "delete":
                    deleteScrumTask(proj, task, c, conn, lock)
                else:
                    destList = scrum_dict.get('destList', "")
                    lock.acquire(True)
                    c.execute("""SELECT * FROM scrumBoard WHERE project = ? and task = ? and stage = ? """, (proj, task, currentList))
                    tasks = c.fetchall()
                    lock.release()
                    if len(tasks)>0:
                        priority = tasks[0][-2]
                    else:
                        priority = scrum_dict.get('priority', "")
                    if destList == "done":
                        deleteScrumTask(proj, task, c, conn, lock)
                        addScrumTask(proj, task, destList, priority, str(datetime.date.today()), c, conn, lock)
                    elif destList == "archive":
                        lock.acquire(True)
                        c.execute("""SELECT * FROM scrumBoard WHERE project = ? and task = ? """, (proj, task))
                        date = c.fetchall()[0][-1]
                        lock.release()
                        deleteScrumTask(proj, task, c, conn, lock)
                        addScrumTask(proj, task, destList, priority, str(date), c, conn, lock)
                    else:
                        deleteScrumTask(proj, task, c, conn, lock)
                        addScrumTask(proj, task, destList, priority, " ", c, conn, lock)
                    conn.commit()
            else:   # its a new card!
                priority = scrum_dict['priority']
                addScrumTask(proj, task, "backlog", priority, " ", c, conn, lock)
        return "Done", 200


class settings(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme", lock)
        activityList = fetchSettingParamFromDB(c, "activityList", lock)

        mailUsername = fetchSettingParamFromDB(c, "MAIL_USERNAME", lock)
        mailpass = len(fetchSettingParamFromDB(c, "MAIL_PASSWORD", lock))*"*"
        mailServer = fetchSettingParamFromDB(c, "MAIL_SERVER", lock)
        mailPort = fetchSettingParamFromDB(c, "MAIL_PORT", lock)
        mailSSL = fetchSettingParamFromDB(c, "MAIL_USE_SSL", lock)
        recipientEmail = fetchSettingParamFromDB(c, "MAIL_RECIPIENT", lock)
        email_setting = {"MAIL_USERNAME": mailUsername,
                         "MAIL_SERVER": mailServer,
                         "MAIL_PORT": mailPort,
                         "MAIL_USE_SSL": mailSSL,
                         "MAIL_PASSWORD": "mailpass",
                         "MAIL_RECIPIENT": recipientEmail
                         }
        return make_response(render_template('settings.html', activityList=activityList,
                                             pageTheme=pageTheme, email_setting=email_setting),200,headers)

    def post(self):
        args = parser.parse_args()
        if args['type'] == "Theme":
            pageTheme = args['value']
            updateSettingParam(c, conn, "Theme", pageTheme, lock)
        if args['type'] == "activityList":
            activityList = args['value']
            updateSettingParam(c, conn, "activityList", activityList, lock)
        if args['type'] == "password":
            pass_dict = eval((args['value']))
            hashed_password = fetchSettingParamFromDB(c, "password")
            if (hashed_password == "None") or verifyPassword(hashed_password, pass_dict["currntpwd"]):
                updateSettingParam(c, conn, "password", hashPassword(pass_dict["newpwd"], lock))
                return "succeded", 200
            return "failed", 200
        if args['type'] == "mailSetting":
            value_dict = eval((args['value']))
            for item in value_dict:
                if item != "MAIL_PASSWORD":
                    updateSettingParam(c, conn, item, value_dict[item], lock)
                else:
                    if value_dict[item] != "mailpass":
                        updateSettingParam(c, conn, item, value_dict[item], lock)
            return "succeded", 200
        return "Done", 200


class gallery(Resource):
    def get(self):
        start_time = time.time()
        args = parser.parse_args()
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme", lock)
        todaysDate = parseDate(args['date'])
        day, month, year = sparateDayMonthYear(todaysDate)
        numberOfDays = numberOfDaysInMonth(int(month), int(year))
        monthsBeginning = getMonthsBeginning(month, year).weekday()
        monthsPhotos=[]
        for dayNumber in range(1, numberOfDays+1):
            date= str(year)+"-"+str(month).zfill(2)+"-"+str(dayNumber).zfill(2)
            photoDir=os.getcwd()+"/static/photos/"+str(year)+"/"+date
            todaysPhotos=allPotosInDir(photoDir, year, date)
            monthsPhotos.append(todaysPhotos)
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('gallery.html', day=day, month=month, year=year,
                                             numberOfDays=numberOfDays, monthsBeginning=monthsBeginning,
                                             monthsPhotos=monthsPhotos,
                                             pageTheme=pageTheme),200,headers)

    def post(self):
        return "Done", 200


class lists(Resource):
    def get(self):
        start_time = time.time()
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme", lock)
        lists = {}

        lock.acquire(True)
        c.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("lists",))
        listNmes = [x.strip() for x in c.fetchall()[0][1].split(",")]
        lock.release()

        lock.acquire(True)
        for listName in listNmes:
            c.execute("""SELECT * FROM lists WHERE type = ? """, (listName, ))
            data =  c.fetchall()
            lists[listName] = sorted(sorted([(name, done, note) for name, done, type, note in data]), key=lambda x: x[1])
        lock.release()

        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('lists.html', lists = lists, readList = lists["book"],
                                             animeList=lists["anime"], movieList = lists["movie"],
                                             bucketList=lists["bucketList"],
                                             toLearnList=lists["toLearn"],
                                             pageTheme=pageTheme),200,headers)

    def post(self):
        args = parser.parse_args()
        if args['action'] == "create list":
            listName = eval(args['value'])["listName"]
            lock.acquire(True)
            c.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("lists",))
            listNames = [x.strip() for x in c.fetchall()[0][1].split(",")] + [listName]
            c.execute("""DELETE from settings where parameter = ? """, ("lists", ))
            c.execute("""INSERT INTO settings VALUES(?, ?)""", ("lists", ",".join(listNames)))
            conn.commit()
            lock.release()
            return "Done", 200

        if args['action'] == "delete list":
            listName = eval(args['value'])["listName"]
            lock.acquire(True)
            c.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("lists",))
            listNames = [x.strip() for x in c.fetchall()[0][1].split(",")]
            listNames.remove(listName)
            c.execute("""DELETE from settings where parameter = ? """, ("lists", ))
            c.execute("""INSERT INTO settings VALUES(?, ?)""", ("lists", ",".join(listNames)))
            c.execute("""DELETE from lists where type = ? """, (listName, ))
            conn.commit()
            lock.release()
            return "Done", 200

        lock.acquire(True)
        if args['action'] == "delete":
            value_dict = eval((args['value']))
            logger.info(f"deleted {value_dict['name'].lower()} from {value_dict['type']}")
            c.execute("""DELETE from lists where name = ? and type = ?  """, (value_dict["name"].lower(), value_dict["type"]))
        else:
            value_dict = eval((args['value']))
            logger.info(f"added {value_dict['name'].lower()} to {value_dict['type']} as {value_dict['done']} ")
            c.execute("""DELETE from lists where name = ? and type = ? """, (value_dict["name"].lower(), value_dict["type"]))
            c.execute("""INSERT INTO lists VALUES(?, ?, ?, ?)""", (value_dict["name"].lower(), value_dict["done"], value_dict["type"], value_dict["notes"]))
        conn.commit()
        lock.release()
        return "Done", 200


class notes(Resource):
    def get(self):
        start_time = time.time()
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme", lock)
        Notebooks = fetchNotebooks(c, lock)
        photoDir=os.getcwd()+"/static/photos/notebookPhotos"
        photos = {}
        for root, dirs, files in os.walk(photoDir):
            if len(root.split("notebookPhotos/"))>1:
                for filename in files:
                    notebookName = root.split("notebookPhotos/")[1]
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.mp4')):
                        photos[notebookName] = photos.get(notebookName, [])+[filename]
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('notes.html', pageTheme=pageTheme, Notebooks=Notebooks, photos=photos),200,headers)

    def post(self):
        args = parser.parse_args()
        value_dict = eval((args['value']))
        if  args['action'] == "delete":
            lock.acquire(True)
            if value_dict.get("chapter", None) != None:
                logger.info(f"deleting the chapter {value_dict['chapter']} from notebook: {value_dict['notebook']}")
                c.execute("""DELETE from Notes where Notebook = ? and  Chapter = ? """, (value_dict["notebook"],value_dict["chapter"],))
            else:
                logger.info(f"deleting the notebook: {value_dict['notebook']}")
                c.execute("""DELETE from Notes where Notebook = ? """, (value_dict["notebook"],))
            conn.commit()
            lock.release()
        elif args['action'] == "rename":
            parsjson = json.loads(args['value'])
            if (parsjson["type"] == "noteBookName") and(parsjson["oldName"] != parsjson["newName"]):
                lock.acquire(True)
                c.execute("""SELECT * FROM Notes WHERE Notebook = ?""", (parsjson["oldName"],))
                allNotes = c.fetchall()
                lock.release()

                lock.acquire(True)
                for x in allNotes:
                    content = x[2]
                    # rename the folder that holds the files inside the references of it...
                    while ("static/photos/notebookPhotos/"+parsjson["oldName"]+"/" in content):
                        content = content.replace("static/photos/notebookPhotos/"+parsjson["oldName"]+"/", "static/photos/notebookPhotos/"+parsjson["newName"]+"/")
                    c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (parsjson["newName"], x[1], content))
                conn.commit()
                lock.release()

                lock.acquire(True)
                for x in allNotes:
                    c.execute("""DELETE from Notes where Notebook = ? and Chapter = ? and content = ? """, (parsjson["oldName"], x[1], x[2]))
                conn.commit()
                lock.release()

                # rename the folder that holds the files
                if os.path.isdir("./static/photos/notebookPhotos/"+parsjson["oldName"]):
                    os.rename("./static/photos/notebookPhotos/"+parsjson["oldName"], "./static/photos/notebookPhotos/"+parsjson["newName"])
                return "all good!", 200

            if (parsjson["type"] == "chapterName") and(parsjson["oldName"] != parsjson["newName"]):
                lock.acquire(True)
                c.execute("""SELECT * FROM Notes WHERE Notebook = ? and Chapter = ? """, (parsjson["noteBookName"], parsjson["oldName"],))
                allNotes = c.fetchall()
                for x in allNotes:
                    c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (x[0], parsjson["newName"], x[2]))
                    c.execute("""DELETE from Notes where Notebook = ? and Chapter = ? and content = ? """, (x[0], parsjson["oldName"], x[2]))
                conn.commit()
                lock.release()
                return "all good!", 200
        else:
            lock.acquire(True)
            c.execute("""DELETE from Notes where Notebook = ? and Chapter = ?  """, (value_dict["notebook"], value_dict["chapter"]))
            c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (value_dict["notebook"], value_dict["chapter"], value_dict['entry']))
            conn.commit()
            lock.release()
        return "nothing here!", 200


class learning(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme", lock)
        setNames, maxDaysNumbers, cnts, flashCards = getFlashCards(c, lock)
        maxDaysNumbers = list(range(1,maxDaysNumbers+1))
        countes = []
        for i in maxDaysNumbers:
            if i in cnts.keys():
                countes.append(cnts[i])
            else:
                countes.append(0)
        return make_response(render_template('learning.html', pageTheme=pageTheme,
                             setNames=setNames, flashCards=flashCards, maxDaysNumbers = maxDaysNumbers, countes=countes),200,headers)

    def post(self):
        args = parser.parse_args()
        if args["type"] == "flashCards":
            if args["action"] == "create":
                values =  json.loads(args['value'])
                setName = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                lastTimeReviewed =  str(datetime.date.today())
                addFlashCards(setName, side1, side2, lastTimeReviewed, c, conn, lock)
            elif args["action"] == "delete":
                values =  json.loads(args['value'])
                setName = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                deleteFlashCards(setName, side1, side2, c, conn, lock)
            else:
                values =  json.loads(args['value'])
                setName = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                lastTimeReviewed =  str(datetime.date.today())
                if args["action"] == "true":
                    changeFlashCards(setName, side1, side2, lastTimeReviewed, True, c, conn, lock)
                else:
                    changeFlashCards(setName, side1, side2, lastTimeReviewed, False, c, conn, lock)
        return "Done", 200


class server(Resource):
    def get(self):
        start_time = time.time()
        args = parser.parse_args()
        if args['date'] is not None:
            year, month, day = args['date'].split("-")
            todaysDate = "-".join([day,month,year[-2:]])
        else:
            today = datetime.date.today()
            day, month, year = today.day, today.month, today.year
            todaysDate = today.strftime('%d-%m-%y')

        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme", lock)

        cpuTemps, cpuTempsTimes, cpuUsage, cpuUsageTimes, discSpace, upTime = generate_cpu_stat(todaysDate, year)
        cpuTempsYearly, cpuUsageYearly = generate_cpu_stat_monthly(year)
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('server.html', pageTheme=pageTheme,
                             cpuTemps=cpuTemps, cpuTempsTimes=cpuTempsTimes,
                             cpuUsage=cpuUsage, cpuUsageTimes=cpuUsageTimes,
                             cpuUsageYearly=cpuUsageYearly, cpuTempsYearly=cpuTempsYearly,
                             upTime=upTime, HideLine = "true", chart_months=chart_months,
                             discSpace=discSpace, year=int(year), month=int(month), day=int(day),
                             PageYear = 1999, PageMonth = 10),200,headers)

    def post(self):
        return "Nothing to be posted!", 200


class audiobooks(Resource):
    def get(self):
        start_time = time.time()
        args = parser.parse_args()
        if args['date'] is not None:
            year, month, day = args['date'].split("-")
            todaysDate = "-".join([day,month,year[-2:]])
        else:
            today = datetime.date.today()
            day, month, year = today.day, today.month, today.year
            todaysDate = today.strftime('%d-%m-%y')

        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme", lock)

        path = "static/audiobooks/"
        try:
            audiobooks, metadata = getAudiobooks(path)
        except:
            audiobooks = metadata = {}
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('audiobooks.html', audiobooks=audiobooks, metadata=metadata, pageTheme=pageTheme ),200,headers)

    def post(self):
        args = parser.parse_args()
        value = json.loads(args['value'])
        metadataFilePath = "static/audiobooks/"+value["author"]+"/"+value["book"]+"/metadata.json"
        with open(metadataFilePath, "r") as metadataFile:
            data = json.load(metadataFile)
            data["chapter "+value["chapter"]]["timestamp"] = value["timestamp"]
            data["chapter "+value["chapter"]]["progress"] = value["progress"]
        metadataFile.close()
        with open(metadataFilePath, "w") as metadataFile:
            json.dump(data, metadataFile)
        metadataFile.close()
        return "Done", 200


class homeAutomation(Resource):
    def get(self):
        start_time = time.time()
        args = parser.parse_args()
        if args['date'] is not None:
            year, month, day = args['date'].split("-")
            todaysDate = "-".join([year, month, day])
        else:
            today = datetime.date.today()
            day, month, year = today.day, today.month, today.year
            todaysDate = today.strftime('%Y-%m-%d')
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme", lock)

        ha_directory="homeAutomation"
        myAnnualConsumption = generateEConsumptionTrackerChartData(str(year), c_ha, lock)
        monthly_data = generate_weather_monthly(c_ha, int(year), lock)
        daily_data, description = genenrate_weather_daily(c_ha, todaysDate, lock)
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('homeAutomation.html', daily_data=daily_data,
                             monthly_Data = monthly_data, chart_months=chart_months,
                             myAnnualConsumption=myAnnualConsumption, description = description,
                             pageTheme=pageTheme, HideLine = "true",
                             PageYear=int(year), PageMonth=int(month), day=int(day),),200,headers)

    def post(self):
        args = parser.parse_args()
        value = json.loads(args['value'])
        if args['action'] == "rename":
            rename_room(str(value['roomNumber']), str(value['newValue']), c_ha, conn_ha, lock)
            return "Done", 200

        if args['tracker_type'] == "eConsumption":
            add_econsumption_data(args['date'], args['value'], c_ha, conn_ha, lock)
            return "Done", 200
        else:
            directory="homeAutomation"
            if not os.path.exists(directory):
                os.makedirs(directory)
            directory="homeAutomation/room_"+value['room']
            if not os.path.exists(directory):
                os.makedirs(directory)
            year = value['date'].split("-")[0]
            add_data_to_ha_DB(c_ha, conn_ha, value['room'], value['date'], value['hour'], value["temp"], value["humidity"], value["pressure"], lock)
            return "Done", 200


@app.route("/downloadDB/")
def downloadDB():
    return send_from_directory(directory=".", filename="journal.db", as_attachment="True", attachment_filename="sqlite_database.db")


@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        date  = request.form['date']
        year = date.split("-")[0]
        folderName = date
        if not os.path.isdir("./static/photos/"+year):
            os.mkdir("./static/photos/"+year)
        if not os.path.isdir("./static/photos/"+year+"/"+folderName):
            os.mkdir("./static/photos/"+year+"/"+folderName)
        f = request.files['file']
        fileName = f.filename
        while os.path.isfile("./static/photos/"+year+"/"+folderName+"/"+fileName):
            fileName = str(randint(1, 100000)) + "_" + f.filename
        f.save(os.path.join("./static/photos/"+year+"/"+folderName, secure_filename(fileName)))
        return redirect(url_for('journal'), 200)


@app.route('/notesUploader', methods = ['GET', 'POST'])
def upload_file_notes():
    if request.method == 'POST':
        notebookLabel  = request.form['notebookLabel']
        if not os.path.isdir("./static/photos/notebookPhotos/"):
            os.mkdir("./static/photos/notebookPhotos/")
        if not os.path.isdir("./static/photos/notebookPhotos/"+notebookLabel):
            os.mkdir("./static/photos/notebookPhotos/"+notebookLabel)
        f = request.files['file']
        fileName = f.filename
        while os.path.isfile("./static/photos/notebookPhotos/"+notebookLabel+"/"+fileName):
            fileName = str(randint(1, 100)) + "_" + f.filename
        f.save(os.path.join("./static/photos/notebookPhotos/"+notebookLabel, secure_filename(fileName)))
        return redirect(url_for('notes'), 200)


@app.route('/shutdown', methods = ['POST'])
def shutdown_server():
    if request.method == 'POST':
        logger.info("shutdown request recieved...")
        send_mail("Server:: shutting down", "shut down command received.", app, mail, c, lock)
        shutdownReq = request.environ.get('werkzeug.server.shutdown')
        if shutdownReq is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        shutdownReq()
        logger.info("closing the DB connection...")
        conn.close()
        logger.info("shutting down the server...")
        scheduler.shutdown()
        return "server is shutting down..."


def sendCalNotification():
    with app.app_context():
        todaysDate = str(datetime.date.today())
        day, month, year = sparateDayMonthYear(todaysDate)
        lock.acquire(True)
        c.execute("""SELECT * FROM calendar WHERE date >= ? and date <= ?  """,
                  (getMonthsBeginning(month, year).date(),
                   getMonthsEnd(month, year).date(),))
        calEvents = c.fetchall()
        lock.release()
        notificationsToBeSent = []
        for item in calEvents:
            if item[0]==todaysDate:
                if item[1] != "None":
                    timeSplit = item[1].split(":")
                    now = datetime.datetime.now()
                    newdatetime = datetime.datetime.now().replace(hour=int(timeSplit[0]), minute=int(timeSplit[1]))
                    diff = newdatetime-now
                    minutesDiff = int(diff.total_seconds()/60)
                    if (minutesDiff == 30) or (minutesDiff == 15):
                        notificationsToBeSent.append(item)
        for item in notificationsToBeSent:
            body = "Event time: "+item[1]+" - "+item[2]+"\n"+ \
                   "Event: "+item[3]+"\n"+ \
                   "Description: "+item[5]+"\n"
            send_mail("Upcomming event: "+item[3], body, app, mail, c)


def sendDailyDigest():
    with app.app_context():
        todaysDate = str(datetime.date.today())
        day, month, year = sparateDayMonthYear(todaysDate)
        lock.acquire(True)
        c.execute("""SELECT * FROM calendar WHERE date = ? """,
                  (todaysDate,))
        calEvents = c.fetchall()
        c.execute("""SELECT * FROM todoList WHERE date = ? """,
                  (todaysDate,))
        todos = c.fetchall()
        lock.release()
        body = "Here is your daily digest for:   "+ todaysDate + "\n"
        body += "\n\nCalendar events:\n"
        for item in calEvents:
            body += "\t* Event: " + item[3] + "\n" + \
                    "\t         Event time: " + item[1] + " - " + item[2] + "\n" + \
                    "\t         Description: "+item[5]+"\n"
        body += "\n\nTODOs events:\n"
        for item in todos:
            body += "\t* Todo: " + item[0] + "\n"
            body += "\t       Status: "+ ("Done" if item[2] == "true" else "Not Done") + "\n"
        send_mail("Daily Digest for: "+todaysDate, body, app, mail, c)


scheduler = BackgroundScheduler()
scheduler.add_job(func=sendCalNotification, trigger="interval", seconds=60)
scheduler.add_job(func=sendDailyDigest, trigger=CronTrigger.from_crontab('0 6 * * *'))
scheduler.start()


api.add_resource(dash, '/')
api.add_resource(journal, '/journal')
api.add_resource(org, '/org')
api.add_resource(settings, '/settings')
api.add_resource(lists, '/lists')
api.add_resource(notes, '/notes')
api.add_resource(gallery, '/gallery')
api.add_resource(learning, '/learning')
api.add_resource(server, '/server')
api.add_resource(audiobooks, '/audiobooks')
api.add_resource(homeAutomation, '/homeAutomation')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

conn.close()
