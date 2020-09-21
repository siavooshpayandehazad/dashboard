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

app = Flask(__name__, template_folder='template', static_url_path='/static')
api = Api(app)

parser = reqparse.RequestParser()
for item in ['tracker_type', 'value', 'oldValue', 'display', 'date', 'done', 'action',
             'type', 'name', 'cardProj', 'cardTask', 'currentList',
             'destList', 'priority', 'Theme', 'counter', 'password', 'planner',
             'entry', 'notebook', 'chapter', 'rename']:
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
            pageYear, pageMonth = args['date'].split("-")
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
        YearsSavings     = generateSavingTrackerChartData(pageYear, c)
        monthsPaces      = generatePaceChartData(int(pageMonth), int(pageYear), numberOfDays, c)
        ChartMonthDays   = [str(i) for i in range(1, numberOfDays+1)]
        # ----------------------------------------------
        return make_response(render_template('index.html', name= pageTitle , titleDate = titleDate,
                                             PageYear = int(pageYear), PageMonth = int(pageMonth),
                                             today = datetime.date.today().day, moods = monthsMoods,
                                             # charts info
                                             ChartMonthDays = ChartMonthDays, ChartYearMonths = monthsOfTheYear,
                                             monthsWeights = chartWeights, monthsSleepTimes = monthsSleepTimes,
                                             monthsSteps = monthsSteps, HR_Min = HR_Min, HR_Max = HR_Max,
                                             monthsRuns = monthsRuns, monthsPaces = monthsPaces,
                                             monthsWorkHours = monthsWorkHours, YearsSavings = YearsSavings,
                                             # ----------------------
                                             activities = monthsActivities, monthsActivitiesPlanned = monthsActivitiesPlanned,
                                             activityList = activityList, days=moodTrackerDays, highlight = highlight,
                                             pageTheme = pageTheme, counterValue = counterValue),200,headers)

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
        if args['tracker_type'] == 'weight':
            return addTrackerItemToTable(args['value'].lower(), "weight", [], "weightTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'sleep':
            return addTrackerItemToTable(args['value'].lower(), "", [], "sleepTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'running':
            return addTrackerItemToTable(args['value'].lower(), "", [], "runningTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'pace':
            return addTrackerItemToTable(args['value'].lower(), "", [], "paceTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'steps':
            return addTrackerItemToTable(args['value'].lower(), "", [], "stepTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'WorkHours':
            return addTrackerItemToTable(args['value'].lower(), "work_hour", [], "workHourTracker", todaysDate, False, True, c, conn)
        if args['tracker_type'] == 'saving':
            return addsSavingItemToTable(args['value'].lower(), todaysDate, c, conn)
        if args['tracker_type'] == 'mood':
            return addTrackerItemToTable(args['value'].lower(), "mood_name", moodList, "moodTracker", todaysDate, False, False, c, conn)
        if args['tracker_type'] == "activity":
            delete = True if args['action']=="delete" else False;
            if args['planner'] == "True":
                return addTrackerItemToTable(args['value'].lower(), "activity_name", activityList, "activityPlanner", todaysDate, delete, False, c, conn)
            else:
                return addTrackerItemToTable(args['value'].lower(), "activity_name", activityList, "activityTracker", todaysDate, delete, False, c, conn)
        return "Done", 200


class journal(Resource):
    def get(self):
        args = parser.parse_args()
        pageTheme = fetchSettingParamFromDB(c, "Theme")
        headers = {'Content-Type': 'text/html'}
        todaysDate = parseDate(args['date'])
        day, month, year = sparateDayMonthYear(todaysDate)
        photoDir=os.getcwd()+"/static/photos/"+str(year)+"/"+todaysDate
        todayPhotos =  allPotosInDir(photoDir, year, todaysDate)
        todaysLog, todaysLogText = getTodaysLogs(c, todaysDate)
        numberOfDays = numberOfDaysInMonth(int(month), int(year))
        monthsBeginning = getMonthsBeginning(month, year).weekday()

        c.execute("""SELECT * FROM logTracker WHERE date >= ? and date <= ? """, (getMonthsBeginning(month, year).date(), getMonthsEnd(month, year).date(), ))
        logged_days = [int(x[1].split("-")[2]) for x in c.fetchall()]

        return make_response(render_template('journal.html', numberOfDays = numberOfDays,
                             day = day, month = month, year=year, monthsBeginning=monthsBeginning,
                             log = todaysLog, todaysLogText = todaysLogText, todayPhotos= todayPhotos,
                             logged_days = logged_days, pageTheme=pageTheme),
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
        all_due_events=[]
        todaysDate = parseDate(args['date'])
        if todaysDate == str(datetime.date.today()):
            c.execute("""SELECT * FROM todoList WHERE date < ? and done = 'false' """, (datetime.date.today(),))
            all_due_events = sorted(c.fetchall(), key=lambda tup: tup[1])

        day, month, year = sparateDayMonthYear(todaysDate)
        weekDay = datetime.datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d').weekday()
        numberOfDays = numberOfDaysInMonth(int(month), int(year))
        c.execute("""SELECT * FROM todoList WHERE date >= ? and date < ? and done = 'false' """, (getNextDay(todaysDate), getThirtyDaysFromNow(day, month, year)))
        thisMonthsEvents = sorted(c.fetchall(), key=lambda tup: tup[1])

        c.execute("""SELECT * FROM todoList WHERE date = ? """, (todaysDate,))
        todayTodos = c.fetchall()

        monthsBeginning = getMonthsBeginning(month, year)
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
        #---------------------------
        headerDates = []
        dayVal= datetime.datetime.strptime(todaysDate, '%Y-%m-%d')-datetime.timedelta(days=weekDay) # weekstart
        for i in range(1, 8):
            headerDates.append(str(dayVal.date()).split("-")[2])
            dayVal = datetime.datetime.strptime(str(dayVal.date()), '%Y-%m-%d')+datetime.timedelta(days=1)

        return make_response(render_template('org.html', day = day, month = month, year=year, weekDay = daysOfTheWeek[weekDay],
                                             monthsBeginning=monthsBeginningWeekDay, todayTodos=todayTodos, overDue = all_due_events,
                                             numberOfDays=numberOfDays, thisMonthsEvents = thisMonthsEvents, calDate = calDate,
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
                c.execute("""INSERT INTO todoList VALUES(?, ?, ?)""", (todo, todaysDate, args['done']))
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
                print( args["action"] )
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


class lists(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme")
        lists = {}
        for listName in ["book", "movie", "anime", "bucketList", "toLearnList"]:
            c.execute("""SELECT * FROM lists WHERE type = ? """, (listName, ))
            lists[listName] = sorted(sorted([(name, done) for name, done, type in c.fetchall()]), key=lambda x: x[1])
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
            c.execute("""INSERT INTO lists VALUES(?, ?, ?)""", (args["name"].lower(), args["done"], args["type"]))
        conn.commit()
        return "Done", 200


class notes(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme")
        Notebooks = fetchNotebooks(c)
        return make_response(render_template('notes.html', pageTheme=pageTheme, Notebooks=Notebooks),200,headers)

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
                    c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (parsjson["newName"], x[1], x[2]))
                conn.commit()
                for x in allNotes:
                    c.execute("""DELETE from Notes where Notebook = ? and Chapter = ? and content = ? """, (parsjson["oldName"], x[1], x[2]))
                conn.commit()
                return "nothing here!", 200
            if (parsjson["type"] == "chapterName") and(parsjson["oldName"] != parsjson["newName"]):
                c.execute("""SELECT * FROM Notes WHERE Notebook = ? and Chapter = ? """, (parsjson["noteBookName"], parsjson["oldName"],))
                allNotes = c.fetchall()
                for x in allNotes:
                    c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (x[0], parsjson["newName"], x[2]))
                    c.execute("""DELETE from Notes where Notebook = ? and Chapter = ? and content = ? """, (x[0], parsjson["oldName"], x[2]))
                conn.commit()
                return "nothing here!", 200
        else:
            c.execute("""DELETE from Notes where Notebook = ? and Chapter = ?  """, (args["notebook"], args["chapter"]))
            c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (args["notebook"], args["chapter"], args['entry']))
        conn.commit()
        return "nothing here!", 200


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
        f.save(os.path.join("./static/photos/"+year+"/"+folderName, secure_filename(f.filename)))
        return redirect(url_for('journal'), 200)


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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

conn.close()
