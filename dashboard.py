#------------------------------------
# add an activity for today: curl http://localhost:5000/activityTracker -d "activity=python"
# add an activity on a specific day: curl http://localhost:5000/activityTracker -d "activity=python" -d "date=2019-05-1"
#------------------------------------
# get daily activity list: curl http://localhost:5000/activityTracker -d "display=day"
# get monthy activity list: curl http://localhost:5000/activityTracker -d "display=month"
#------------------------------------
from functionPackages.misc import *
from functionPackages.charts import *
from functionPackages.dateTime import *

import sqlite3
import datetime
import sys, os
from package import *
from flask import Flask, request, url_for, redirect
from flask import send_from_directory
from flask_restful import reqparse, abort, Api, Resource
from flask import render_template, make_response
from werkzeug import secure_filename
import requests
import json
import os
from random import randint


app = Flask(__name__, template_folder='template', static_url_path='/static')
api = Api(app)

parser = reqparse.RequestParser()
for item in ['tracker_type', 'value', 'oldValue', 'display', 'date', 'done', 'action',
             'type', 'name', 'cardProj', 'cardTask', 'currentList', 'notes',
             'destList', 'priority', 'Theme', 'counter', 'password', 'planner',
             'entry', 'notebook', 'chapter', 'rename', 'color']:
    parser.add_argument(item)

conn, c = createDB("journal.db")
backupDatabase(conn)
generateDBTables(c)


class dash(Resource):
    def get(self):
        args = parser.parse_args()
        try:
            pageTheme = fetchSettingParamFromDB(c, "Theme")
        except:
            pageTheme = "Dark"
            setupSettingTable(c, conn)
            print("could not fetch page theme! replacing with default values")
        if args['date'] is not None:
            pageYear, pageMonth, pageDay = args['date'].split("-")
        else:
            pageMonth = str(datetime.date.today().month).zfill(2)
            pageYear = str(datetime.date.today().year)

        headers      = {'Content-Type': 'text/html'}
        pageTitle    = "DashBoard "
        titleDate    = monthsOfTheYear[int(pageMonth)-1]+"-"+pageYear
        numberOfDays = numberOfDaysInMonth(int(pageMonth), int(pageYear))
        monthsBeginningWeekDay = datetime.datetime.strptime(f"{pageYear}-{pageMonth}-01", '%Y-%m-%d').weekday()
        # moodTrackerDays is a list that contains a bunch of Nones for the days of the week that are in the
        # previous month. this is used for the moodtracker in order to add the empty spaces in the beginning of the month.
        moodTrackerDays = [None for i in range(0, monthsBeginningWeekDay)] + list(range(1, numberOfDays+1))
        # list of current month's moods and activities.
        monthsActivities, monthsActivitiesPlanned, monthsMoods = collectMonthsData(int(pageMonth), int(pageYear), c)
        # highlights the current day in the activity tracker page!
        highlight    = shouldHighlight(pageYear, pageMonth)
        counterValue = fetchSettingParamFromDB(c, "counter")
        # gather chart information ----------------------
        chartWeights     = generateWeightChartData(int(pageMonth), int(pageYear), numberOfDays, c)
        monthsWorkHours  = generateWorkTrakcerChartData(int(pageMonth), int(pageYear), numberOfDays, c)
        monthsSleepTimes = generateSleepChartData(int(pageMonth), int(pageYear), numberOfDays, c)
        monthsSteps      = generateStepChartData(int(pageMonth), int(pageYear), numberOfDays, c)
        monthsRuns       = generateRunningChartData(int(pageMonth), int(pageYear), numberOfDays, c)
        HR_Min, HR_Max   = generateHRChartData(int(pageMonth), int(pageYear), numberOfDays, c)
        BP_Min, BP_Max   = generateBPChartData(int(pageMonth), int(pageYear), numberOfDays, c)
        BO               = generateYearOxygenChartData(int(pageMonth), int(pageYear), numberOfDays, c)
        YearsSavings     = generateSavingTrackerChartData(pageYear, c)
        monthsPaces      = generatePaceChartData(int(pageMonth), int(pageYear), numberOfDays, c)
        ChartMonthDays   = [str(i) for i in range(1, numberOfDays+1)]
        travels          = getTravelDests(c)
        print(BO)
        # ----------------------------------------------
        yearRuns = generateYearRunChartData(int(pageYear), numberOfDays, c)
        yearSteps = generateYearStepChartData(int(pageYear), numberOfDays, c)
        yearSleep = generateYearSleepChartData(int(pageYear), numberOfDays, c)
        yearWeight = generateYearWeightChartData(int(pageYear), numberOfDays, c)
        yearWH = generateYearWHChartData(int(pageYear), numberOfDays, c)
        yearHR_Min, yearHR_Max = generateYearHRChartData(int(pageYear), numberOfDays, c)
        yearMood = generateYearMoodChartData(int(pageYear), numberOfDays, c)
        return make_response(render_template('index.html', name= pageTitle , titleDate = titleDate,
                                             PageYear = int(pageYear), PageMonth = int(pageMonth),
                                             today = datetime.date.today().day, moods = monthsMoods,
                                             # charts info
                                             ChartMonthDays = ChartMonthDays, ChartYearMonths = monthsOfTheYear,
                                             monthsWeights = chartWeights, monthsSleepTimes = monthsSleepTimes,
                                             monthsSteps = monthsSteps, HR_Min = HR_Min, HR_Max = HR_Max,
                                             BP_Min = BP_Min, BP_Max = BP_Max, BO = BO,
                                             monthsRuns = monthsRuns, monthsPaces = monthsPaces,
                                             monthsWorkHours = monthsWorkHours, YearsSavings = YearsSavings,
                                             yearSteps = yearSteps, yearSleep = yearSleep, yearWH = yearWH,
                                             yearHR_Min = yearHR_Min, yearHR_Max = yearHR_Max, yearMood = yearMood,
                                             yearWeight = yearWeight, yearRuns = yearRuns,
                                             # ----------------------
                                             activities = monthsActivities, monthsActivitiesPlanned = monthsActivitiesPlanned,
                                             activityList = activityList, days=moodTrackerDays, highlight = highlight,
                                             pageTheme = pageTheme, counterValue = counterValue, travels = travels),200,headers)

    def post(self):
        args = parser.parse_args()
        if args['password'] is not None:
            password = fetchSettingParamFromDB(c, "password")
            if password == "None":
                return "success", 200
            else:
                if not verifyPassword(password, args['password']):
                    return "failed", 200
                else:
                    return "success", 200

        if args['counter'] is not None:
            if args['counter'] == "countup":
                counterVal = int(fetchSettingParamFromDB(c, "counter")) + 1
            elif args['counter'] == "reset":    # reset the counter
                counterVal = 0
            updateSettingParam(c, conn, "counter", counterVal)

        todaysDate = parseDate(args['date'])
        if args['tracker_type'] == 'HR':
            return addTrackerItemToTable(args['value'].split(","), "", [], "HRTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'BP':
            return addTrackerItemToTable(args['value'].split(","), "", [], "BPTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'weight':
            return addTrackerItemToTable(args['value'].lower(), "weight", [], "weightTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'blood oxygen':
            return addTrackerItemToTable(args['value'].lower(), "oxygen", [], "oxygenTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'sleep':
            return addTrackerItemToTable(args['value'].lower(), "", [], "sleepTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'running':
            return addTrackerItemToTable(args['value'].lower(), "", [], "runningTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'pace':
            return addTrackerItemToTable(args['value'].lower(), "", [], "paceTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'step':
            return addTrackerItemToTable(args['value'].lower(), "", [], "stepTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'work hours':
            return addTrackerItemToTable(args['value'].lower(), "work_hour", [], "workHourTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'saving':
            return addsSavingItemToTable(args['value'].lower(), todaysDate, c, conn)
        if args['tracker_type'] == 'mood':
            return addTrackerItemToTable(args['value'].lower(), "mood_name", moodList, "moodTracker", todaysDate, False, False, c, conn)
        if args['tracker_type'] == "activity":
            delete = True if args['action']=="delete" else False
            if args['planner'] == "True":
                return addTrackerItemToTable(args['value'].lower(), "activity_name", activityList, "activityPlanner", todaysDate, delete, False, c, conn)
            else:
                return addTrackerItemToTable(args['value'].lower(), "activity_name", activityList, "activityTracker", todaysDate, delete, False, c, conn)
        if args['tracker_type'] == "travel":
            values = args['value'].split(",")
            addTravelItem(values[0], values[1], values[2], c, conn)
        return "Done", 200


class journal(Resource):
    def get(self):
        args = parser.parse_args()
        pageTheme = fetchSettingParamFromDB(c, "Theme")
        headers = {'Content-Type': 'text/html'}
        todaysDate = parseDate(args['date'])
        day, month, year = sparateDayMonthYear(todaysDate)
        photoDir=os.getcwd()+"/static/photos/"+str(year)+"/"+todaysDate
        photoDir2=os.getcwd()+"/static/photos/"+str(year)
        daysWithPhotos = allDaysWithPotos(photoDir2, year, month)
        todayPhotos =  allPotosInDir(photoDir, year, todaysDate)
        todaysLog, todaysLogText = getTodaysLogs(c, todaysDate)
        numberOfDays = numberOfDaysInMonth(int(month), int(year))
        monthsBeginning = getMonthsBeginning(month, year).weekday()
        c.execute("""SELECT * FROM logTracker WHERE date >= ? and date <= ? """, (getMonthsBeginning(month, year).date(), getMonthsEnd(month, year).date(), ))
        logged_days = [int(x[1].split("-")[2]) for x in c.fetchall()]

        return make_response(render_template('journal.html', numberOfDays = numberOfDays,
                             day = day, month = month, year=year, monthsBeginning=monthsBeginning,
                             log = todaysLog, todaysLogText = todaysLogText, todayPhotos= todayPhotos,
                             logged_days = logged_days, daysWithPhotos = daysWithPhotos, pageTheme=pageTheme),
                             200,headers)

    def post(self):
        args = parser.parse_args()
        if args['entry'] == 'log':
            todaysDate = parseDate(args['date'])
            log = args['value'].lower()
            c.execute("""SELECT * FROM logTracker WHERE date = ? """, (todaysDate, ))
            if len(c.fetchall()) > 0:
                c.execute("""DELETE from logTracker where date = ?""", (todaysDate, ))
            c.execute("""INSERT INTO logTracker VALUES(?, ?)""", (log, todaysDate))
            conn.commit()
            print(f"added log for date: {todaysDate}")
        return "Done", 200


class org(Resource):
    def get(self):
        pageTheme = fetchSettingParamFromDB(c, "Theme")

        headers = {'Content-Type': 'text/html'}
        args = parser.parse_args()
        todaysDate = parseDate(args['date'])
        day, month, year = sparateDayMonthYear(todaysDate)
        monthsBeginning = getMonthsBeginning(month, year)

        c.execute("""SELECT * FROM todoList WHERE date < ? and done = 'false' """, (todaysDate,))
        all_due_events = sorted(c.fetchall(), key=lambda tup: tup[1])

        c.execute("""SELECT * FROM todoList WHERE date < ? and date >= ? and done = 'true'""", (todaysDate, monthsBeginning))
        all_due_events += sorted(c.fetchall(), key=lambda tup: tup[1])

        weekDay = datetime.datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d').weekday()
        numberOfDays = numberOfDaysInMonth(int(month), int(year))
        c.execute("""SELECT * FROM todoList WHERE date >= ? and date < ? """, (getNextDay(todaysDate), getThirtyDaysFromNow(day, month, year)))
        thisMonthsEvents = sorted(c.fetchall(), key=lambda tup: tup[1])

        c.execute("""SELECT * FROM todoList WHERE date = ? """, (todaysDate,))
        todayTodos = c.fetchall()


        monthsBeginningWeekDay = monthsBeginning.weekday()
        scrumBoardLists = {}
        for stage in ["backlog", "todo", "in progress", "done"]:
            c.execute("""SELECT * FROM scrumBoard WHERE stage = ? """, (stage, ))
            # sort based on priority
            scrumBoardLists[stage] = sorted([(task, proj, priority) for task, proj, stage, priority, done_date in c.fetchall()], key = lambda x: x[2])

        # find all the tasks done during this month's period!
        monthsEnd = getMonthsEnd(month, year)
        c.execute("""SELECT * FROM scrumBoard WHERE done_date >= ? and done_date <= ? """, (monthsBeginning.date(),  monthsEnd.date()))
        doneTasks = sorted([int(done_date.split("-")[2]) for proj, task,  stage, priority, done_date in c.fetchall()])
        current_done = 0
        ChartDoneTasks=[]
        for i in range(1, numberOfDays+1):
            current_done += doneTasks.count(i)
            ChartDoneTasks.append(current_done)
        ChartMonthDays = [str(i) for i in range(1, numberOfDays+1)]
        if todaysDate == str(datetime.date.today()):
            thisMonthTasksNum = len(scrumBoardLists["done"])+len(scrumBoardLists["in progress"])+len(scrumBoardLists["todo"])
        else:
            thisMonthTasksNum = ChartDoneTasks[-1]
        ChartthisMonthTasks = [thisMonthTasksNum for i in range(numberOfDays)]

        calDate = getCalEvents(todaysDate, c)
        calMonth = getCalEventsMonth(month, year, c)
        #---------------------------
        headerDates = []
        dayVal= datetime.datetime.strptime(todaysDate, '%Y-%m-%d')-datetime.timedelta(days=weekDay) # weekstart
        for i in range(1, 8):
            headerDates.append(str(dayVal.date()).split("-")[2])
            dayVal = datetime.datetime.strptime(str(dayVal.date()), '%Y-%m-%d')+datetime.timedelta(days=1)

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
        if args['entry'] == 'todo':
            todaysDate = parseDate(args['date'])
            todo = args['value'].lower()
            c.execute("""DELETE from todoList where date = ? and task = ?""", (todaysDate, todo))
            if args['action'] == "delete":
                print(f"removed todo {todo} from todoList for date: {todaysDate} as {args['done']}")
            else:
                c.execute("""INSERT INTO todoList VALUES(?, ?, ?, ?)""", (todo, todaysDate, args['done'], args['color']))
                print(f"added todo {todo} to todoList for date: {todaysDate} as {args['done']}")
            conn.commit()

        elif args['entry'] == 'calendar':
            if args["action"] == "create":
                date = args['date']
                values = json.loads(args['value'])

                c.execute("""INSERT INTO calendar VALUES(?, ?, ?, ?, ?, ?)""", (date, values["startTime"], values["stopTime"], values["name"], values["color"], values["details"]))
                conn.commit()
            elif args["action"] == "delete":
                date = args['date']
                values = json.loads(args['value'])
                c.execute("""DELETE from calendar where date = ? and startTime = ? and endTime = ?  and eventName = ? """, (date, values["startTime"], values["stopTime"], values["name"]))
                conn.commit()
            elif args["action"] == "edit":
                date = args['date']
                values = json.loads(args['oldValue'])
                c.execute("""DELETE from calendar where date = ? and startTime = ? and endTime = ?  and eventName = ? """, (values["date"], values["startTime"], values["stopTime"], values["name"]))
                values = json.loads(args['value'])
                c.execute("""INSERT INTO calendar VALUES(?, ?, ?, ?, ?, ?)""", (values["date"], values["startTime"], values["stopTime"], values["name"], values["color"], values["details"]))
                conn.commit()

        elif args['cardProj'] is not None:
            proj = args['cardProj']
            task = args['cardTask']
            if args['currentList'] is not None:
                currentList = args['currentList']
                if args['action'] == "delete":
                    print("deleting card:", task)
                    c.execute("""DELETE from scrumBoard where project = ? and task = ? and stage = ?""", (proj, task, currentList))
                    conn.commit()
                else:
                    destList = args['destList']
                    c.execute("""SELECT * FROM scrumBoard WHERE project = ? and task = ? and stage = ? """, (proj, task, currentList))
                    tasks = c.fetchall()
                    if len(tasks)>0:
                        priority = tasks[0][-2]
                    else:
                        priority = args['priority']

                    if destList == "done":
                        c.execute("""DELETE from scrumBoard where project = ? and task = ? """, (proj, task))
                        c.execute("""INSERT INTO scrumBoard VALUES(?, ?, ?, ?, ?)""", (proj, task, destList, priority, str(datetime.date.today())))
                    elif destList == "archive":
                        c.execute("""SELECT * FROM scrumBoard WHERE project = ? and task = ? """, (proj, task))
                        date = c.fetchall()[0][-1]
                        c.execute("""DELETE from scrumBoard where project = ? and task = ? """, (proj, task))
                        c.execute("""INSERT INTO scrumBoard VALUES(?, ?, ?, ?, ?)""", (proj, task, destList, priority, str(date)))
                    else:
                        c.execute("""DELETE from scrumBoard where project = ? and task = ? """, (proj, task))
                        c.execute("""INSERT INTO scrumBoard VALUES(?, ?, ?, ?, ?)""", (proj, task, destList, priority, " "))
                    conn.commit()
            else:   # its a new card!
                priority = args['priority']
                c.execute("""INSERT INTO scrumBoard VALUES(?, ?, ?, ?, ?)""", (proj, task, "backlog", priority, " "))
                conn.commit()
        return "Done", 200


class settings(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme")
        return make_response(render_template('settings.html', activityList=activityList,
                                             pageTheme=pageTheme),200,headers)

    def post(self):
        args = parser.parse_args()
        if args['Theme'] is not None:
            pageTheme = args['Theme']
            updateSettingParam(c, conn, "Theme", pageTheme)
        if args['password'] is not None:
            pass_dict = eval((args['password']))
            hashed_password = fetchSettingParamFromDB(c, "password")
            if (hashed_password == "None") or verifyPassword(hashed_password, pass_dict["currntpwd"]):
                updateSettingParam(c, conn, "password", hashPassword(pass_dict["newpwd"]))
                return "succeded", 200
            return "failed", 200
        return "Done", 200


class gallery(Resource):
    def get(self):
        args = parser.parse_args()
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme")
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
            print(date, monthsPhotos)
        return make_response(render_template('gallery.html', day=day, month=month, year=year,
                                             numberOfDays=numberOfDays, monthsBeginning=monthsBeginning,
                                             monthsPhotos=monthsPhotos,
                                             pageTheme=pageTheme),200,headers)

    def post(self):
        return "Done", 200

class lists(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme")
        lists = {}
        for listName in ["book", "movie", "anime", "bucketList", "toLearnList"]:
            c.execute("""SELECT * FROM lists WHERE type = ? """, (listName, ))
            lists[listName] = sorted(sorted([(name, done, note) for name, done, type, note in c.fetchall()]), key=lambda x: x[1])
        return make_response(render_template('lists.html', readList = lists["book"],
                                             animeList=lists["anime"], movieList = lists["movie"],
                                             bucketList=lists["bucketList"],
                                             toLearnList=lists["toLearnList"],
                                             pageTheme=pageTheme),200,headers)

    def post(self):
        args = parser.parse_args()
        if args['action'] == "delete":
            print(f"deleted {args['name'].lower()} from {args['type']}")
            c.execute("""DELETE from lists where name = ? and type = ?  """, (args["name"].lower(), args["type"]))
        else:
            print(f"added {args['name'].lower()} to {args['type']} as {args['done']} ")
            c.execute("""DELETE from lists where name = ? and type = ? """, (args["name"].lower(), args["type"]))
            c.execute("""INSERT INTO lists VALUES(?, ?, ?, ?)""", (args["name"].lower(), args["done"], args["type"], args["notes"]))
        conn.commit()
        return "Done", 200


class notes(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme")
        Notebooks = fetchNotebooks(c)
        photoDir=os.getcwd()+"/static/photos/notebookPhotos"
        photos = {}
        for root, dirs, files in os.walk(photoDir):
            if len(root.split("notebookPhotos/"))>1:
                for filename in files:
                    notebookName = root.split("notebookPhotos/")[1]
                    if (".jpg" in filename) or (".png" in filename):
                        photos[notebookName] = photos.get(notebookName, [])+[filename]
        return make_response(render_template('notes.html', pageTheme=pageTheme, Notebooks=Notebooks, photos=photos),200,headers)

    def post(self):
        args = parser.parse_args()
        if  args['action'] == "delete":
            if (args['chapter']):
                print(f"deleting the chapter {args['chapter']} from notebook: {args['notebook']}")
                c.execute("""DELETE from Notes where Notebook = ? and  Chapter = ? """, (args["notebook"],args['chapter'],))
            else:
                print(f"deleting the notebook: {args['notebook']}")
                c.execute("""DELETE from Notes where Notebook = ? """, (args["notebook"],))
        elif args['rename'] is not None:
            parsjson = json.loads(args['rename'])
            if (parsjson["type"] == "noteBookName") and(parsjson["oldName"] != parsjson["newName"]):
                c.execute("""SELECT * FROM Notes WHERE Notebook = ?""", (parsjson["oldName"],))
                allNotes = c.fetchall()
                for x in allNotes:
                    content = x[2]
                    # rename the folder that holds the files inside the references of it...
                    while ("static/photos/notebookPhotos/"+parsjson["oldName"]+"/" in content):
                        content = content.replace("static/photos/notebookPhotos/"+parsjson["oldName"]+"/", "static/photos/notebookPhotos/"+parsjson["newName"]+"/")
                    c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (parsjson["newName"], x[1], content))
                conn.commit()
                for x in allNotes:
                    c.execute("""DELETE from Notes where Notebook = ? and Chapter = ? and content = ? """, (parsjson["oldName"], x[1], x[2]))
                conn.commit()
                # rename the folder that holds the files
                if os.path.isdir("./static/photos/notebookPhotos/"+parsjson["oldName"]):
                    os.rename("./static/photos/notebookPhotos/"+parsjson["oldName"], "./static/photos/notebookPhotos/"+parsjson["newName"])
                return "all good!", 200
            if (parsjson["type"] == "chapterName") and(parsjson["oldName"] != parsjson["newName"]):
                c.execute("""SELECT * FROM Notes WHERE Notebook = ? and Chapter = ? """, (parsjson["noteBookName"], parsjson["oldName"],))
                allNotes = c.fetchall()
                for x in allNotes:
                    c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (x[0], parsjson["newName"], x[2]))
                    c.execute("""DELETE from Notes where Notebook = ? and Chapter = ? and content = ? """, (x[0], parsjson["oldName"], x[2]))
                conn.commit()
                return "all good!", 200
        else:
            c.execute("""DELETE from Notes where Notebook = ? and Chapter = ?  """, (args["notebook"], args["chapter"]))
            c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (args["notebook"], args["chapter"], args['entry']))
        conn.commit()
        return "nothing here!", 200


class learning(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme")
        setNames, maxDaysNumbers, cnts, flashCards = getFlashCards(c)
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
        if args["entry"] == "flashCards":
            if args["action"] == "create":
                values =  json.loads(args['value'])
                setName = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                lastTimeReviewed =  str(datetime.date.today())
                addFlashCards(setName, side1, side2, lastTimeReviewed, c, conn)
            elif args["action"] == "delete":
                values =  json.loads(args['value'])
                setName = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                deleteFlashCards(setName, side1, side2, c, conn)
            else:
                values =  json.loads(args['value'])
                setName = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                lastTimeReviewed =  str(datetime.date.today())
                if args["action"] == "true":
                    changeFlashCards(setName, side1, side2, lastTimeReviewed, True, c, conn)
                else:
                    changeFlashCards(setName, side1, side2, lastTimeReviewed, False, c, conn)
        return "Done", 200

class server(Resource):
    def get(self):
        args = parser.parse_args()
        if args['date'] is not None:
            year, month, day = args['date'].split("-")
            todaysDate = "-".join([day,month,year[-2:]])
        else:
            today = datetime.date.today()
            day, month, year = today.day, today.month, today.year
            todaysDate = today.strftime('%d-%m-%y')

        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme")

        cpuTemps = []
        cpuTempsTimes = []

        cpuUsage = []
        cpuUsageTimes = []

        try:
            with open('serverScripts/reports/cpuReports/cpuUsageData_'+str(todaysDate)+'.txt', 'r') as reader2:
                line2 = reader2.readline()
                while (line2 != ""):
                    lineSplit = line2.split(" ")
                    cpuUsage.append(float(lineSplit[2]))
                    cpuUsageTimes.append(lineSplit[0])
                    line2 = reader2.readline()
        except:
            print("something went wrong!")
        try:
            with open('serverScripts/reports/cpuReports/cpuTempData_'+str(todaysDate)+'.txt', 'r') as reader2:
                line2 = reader2.readline()
                while (line2 != ""):
                    lineSplit = line2.split(" ")
                    cpuTemps.append(float(lineSplit[0])/1000)
                    cpuTempsTimes.append(lineSplit[2])
                    line2 = reader2.readline()
        except:
            print("something went wrong!")

        discSpace1 = int(os.popen('df -h | grep "/dev/root"').read().split()[4][:-1])
        discSpace2 = int(os.popen('df -h | grep "/dev/sda1"').read().split()[4][:-1])
        discSpace3Temp = os.popen('free -m | grep "Mem"').read().split()
        discSpace3 = (float(discSpace3Temp[2])/float(discSpace3Temp[1]))*100
        discSpace4Temp = os.popen('free -m | grep "Swap"').read().split()
        discSpace4 = (float(discSpace4Temp[2])/float(discSpace4Temp[1]))*100
        discSpace = {"/dev/root" : [discSpace1, 100-discSpace1],
                     "/dev/sda1": [discSpace2, 100-discSpace2],
                     "Mem": [discSpace3, 100-discSpace3],
                     "Swap": [discSpace4, 100-discSpace4]}

        upTimeString = " ".join(os.popen('uptime -s').read().split())
        bootTime = datetime.datetime.strptime(upTimeString, '%Y-%m-%d %H:%M:%S')
        upTime = datetime.datetime.now() - bootTime
        upTime = int(upTime.total_seconds()/3600)

        return make_response(render_template('server.html', pageTheme=pageTheme,
                             cpuTemps=cpuTemps, cpuTempsTimes=cpuTempsTimes,
                             cpuUsage=cpuUsage, cpuUsageTimes=cpuUsageTimes,
                             upTime=upTime,
                             discSpace=discSpace, year=int(year), month=int(month), day=int(day),
                             PageYear = 1999, PageMonth = 10),200,headers)


class audiobooks(Resource):
    def get(self):
        args = parser.parse_args()
        if args['date'] is not None:
            year, month, day = args['date'].split("-")
            todaysDate = "-".join([day,month,year[-2:]])
        else:
            today = datetime.date.today()
            day, month, year = today.day, today.month, today.year
            todaysDate = today.strftime('%d-%m-%y')

        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme")

        path = "static/audiobooks/"
        audiobooks, metadata = getAudiobooks(path)
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
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme")

        tempData = {}
        tempData["room_1"] = {}
        with open('homeAutomation/room_1/temp/2021-03-24.txt', 'r') as reader2:
            tempData["room_1"]["time"] = []
            tempData["room_1"]["temp"] = []
            line2 = reader2.readline()
            while (line2 != ""):
                lineSplit = line2.split(" -> ")
                tempData["room_1"]["time"].append(str(lineSplit[0]).strip())
                tempData["room_1"]["temp"].append(float(lineSplit[1]))
                line2 = reader2.readline()
        reader2.close()

        return make_response(render_template('homeAutomation.html', tempData=tempData,
                             PageYear = 1999, PageMonth = 10, pageTheme=pageTheme ),200,headers)

    def post(self):
        args = parser.parse_args()
        value = json.loads(args['value'])
        print(value['date'], value['hour'], value['temp'])
        directory="homeAutomation/room_"+value['room']+"/temp"
        if not os.path.exists(directory):
            os.makedirs(directory)
        f = open("homeAutomation/room_"+value['room']+"/temp/"+value['date']+".txt", "a")
        f.write(value['hour']+" -> "+value['temp']+"\n")
        f.close()
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
        print("shutdown request recieved...")
        shutdownReq = request.environ.get('werkzeug.server.shutdown')
        if shutdownReq is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        shutdownReq()
        print("closing the DB connection...")
        conn.close()
        print("shutting down the server...")
        return "server is shutting down..."


api.add_resource(dash, '/home')
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
