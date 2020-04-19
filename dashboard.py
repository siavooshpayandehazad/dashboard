#------------------------------------
# add an activity for today: curl http://localhost:5000/activityTracker -d "activity=python"
# add an activity on a specific day: curl http://localhost:5000/activityTracker -d "activity=python" -d "date=2019-05-1"
#------------------------------------
# get daily activity list: curl http://localhost:5000/activityTracker -d "display=day"
# get monthy activity list: curl http://localhost:5000/activityTracker -d "display=month"
#------------------------------------
from functionPackage import *

import sqlite3
import datetime
import sys, os
from package import *
from flask import Flask
from flask import send_from_directory
from flask_restful import reqparse, abort, Api, Resource
from flask import render_template, make_response
import requests

app = Flask(__name__, template_folder='template', static_url_path='/static')
api = Api(app)

parser = reqparse.RequestParser()
for item in ['activity', 'display', 'date', 'log', 'mood', 'todo', 'done',
             'type', 'name', 'delete', 'cardProj', 'cardTask', 'currentList',
             'destList', 'priority', 'Theme', 'counter', 'password']:
    parser.add_argument(item)

conn  =  sqlite3.connect("journal.db",  check_same_thread=False)
# making a backup of the database...
backupDatabase(conn)

c = conn.cursor()
generateDBTables(c)

class dash(Resource):
    def get(self):
        args = parser.parse_args()
        try:
            pageTheme = fetchSettingParamFromDB(c, "Theme")
        except:
            pageTheme = "Dark"
            c.execute("""INSERT INTO settings VALUES(?, ?)""", ("Theme", "Dark"))
            c.execute("""INSERT INTO settings VALUES(?, ?)""", ("counter", "0"))
            c.execute("""INSERT INTO settings VALUES(?, ?)""", ("password", "None"))
            print("could not fetch page theme! replacing with default values")

        if args['date'] is not None:
            pageMonth = args['date'].split("-")[1]
            pageYear = args['date'].split("-")[0]
        else:
            pageMonth = str(datetime.date.today().month).zfill(2)
            pageYear = str(datetime.date.today().year)

        headers = {'Content-Type': 'text/html'}
        pageTitle = "DashBoard "
        titleDate = monthsOfTheYear[int(pageMonth)-1]+"-"+pageYear

        # this is a list that contains a bunch of Nones for the days of the week that are in the
        # previous month. this is used for the moodtracker in order to add the empty spaces in the beginning of the month.
        monthsBeginningWeekDay = datetime.datetime.strptime(f"{pageYear}-{pageMonth}-01", '%Y-%m-%d').weekday()
        moodTrackerDays = [None for i in range(0, monthsBeginningWeekDay)] + list(range(1, numberOfDaysInMonth(pageMonth)+1))

        # list of current month's moods and activities.
        monthsActivities = []
        monthsMoods = []
        for i in range(0, 32):
            dayOfMonth = pageYear+"-"+pageMonth+"-"+str(i).zfill(2)
            c.execute("""SELECT * FROM activityTracker WHERE date = ? """, (dayOfMonth,))
            monthsActivities+=c.fetchall()
            c.execute("""SELECT * FROM moodTracker WHERE date = ? """, (dayOfMonth,))
            monthsMoods+=c.fetchall()

        # highlights the current day in the activity tracker page!
        highlight = shouldHighlight(pageYear, pageMonth)
        counterValue = fetchSettingParamFromDB(c, "counter")

        return make_response(render_template('index.html', name= pageTitle , titleDate = titleDate,
                                             PageYear = int(pageYear), PageMonth=int(pageMonth),
                                             today = datetime.date.today().day, moods = monthsMoods,
                                             activities = monthsActivities, activityList =activityList,
                                             days=moodTrackerDays, highlight=highlight, pageTheme=pageTheme,
                                             counterValue=counterValue),200,headers)

    def post(self):
        args = parser.parse_args()
        if args['password'] is not None:
            password = fetchSettingParamFromDB(c, "password")
            if password == "None":
                return "success", 200
            else:
                if not verifyPassword(password, args['password']):
                    print("login failed!")
                    return "failed", 200
                else:
                    print("login succeded!")
                    return "success", 200

        if args['counter'] is not None:
            if args['counter'] == "countup":
                counterVal = int(fetchSettingParamFromDB(c, "counter")) + 1
            elif args['counter'] == "reset":    # reset the counter
                counterVal = 0
            c.execute("""DELETE from settings where parameter = ? """, ("counter", ))
            c.execute("""INSERT INTO settings VALUES(?, ?)""", ("counter", counterVal))
            conn.commit()

        if args['date'] is None:
            todaysDate = str(datetime.date.today())
        else:
            todaysDate = args['date']
            if not checkIfDateValid(todaysDate):  # check for cases like: 2019-05-2
                return "date format not valid, should be YYYY-MM-DD", 400

        if args['mood'] is not None:
            mood = args['mood'].lower()
            if mood not in moodList:
                return "mood not found", 400

            c.execute("""SELECT * FROM moodTracker WHERE date = ?""", (todaysDate,))
            for oldMood, todaysDate in c.fetchall():
                c.execute("""DELETE from moodTracker where date = ? and mood_name = ?""", (todaysDate, oldMood))
            c.execute("""INSERT INTO moodTracker VALUES(?, ?)""", (mood, todaysDate))
            conn.commit()
            print(f"added mood {mood} for date: {todaysDate}")

        if args['activity'] is not None:
            activity = args['activity'].lower()
            if activity not in activityList:
                return "activity not found", 400
            c.execute("""SELECT * FROM activityTracker WHERE date = ? and activity_name = ?""", (todaysDate, activity))
            if (args['activity'], todaysDate) not in c.fetchall():
                c.execute("""INSERT INTO activityTracker VALUES(?, ?)""", (activity, todaysDate))
                conn.commit()
                print(f"added activity {activity} for date: {todaysDate}")
        return "Done", 200

class journal(Resource):
    def get(self):
        args = parser.parse_args()
        pageTheme = fetchSettingParamFromDB(c, "Theme")

        headers = {'Content-Type': 'text/html'}
        if args['date'] is not None:
            todaysDate = args['date']
        else:
            todaysDate = str(datetime.date.today())

        day, month, year = sparateDayMonthYear(todaysDate)
        photoDir=os.getcwd()+"/static/photos/"+str(year)+"/"+todaysDate
        todayPhotos =  allPotosInDir(photoDir, year, todaysDate)
        todaysLog, todaysLogText = getTodaysLogs(c, todaysDate)
        numberOfDays = numberOfDaysInMonth(month)
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
        todaysDate = str(datetime.date.today())
        if args['log'] is not None:
            if args['date'] is None:
                todaysDate = str(datetime.date.today())
            else:
                todaysDate = args['date']
                if len(todaysDate.split("-")[2]) == 1:  # check for cases like: 2019-05-2
                    return "date format not valid, should be YYYY-MM-DD", 404
            log = args['log'].lower()
            c.execute("""SELECT * FROM logTracker WHERE date = ? """, (todaysDate, ))
            if len(c.fetchall()) > 0:
                c.execute("""DELETE from logTracker where date = ?""", (todaysDate, ))
            c.execute("""INSERT INTO logTracker VALUES(?, ?)""", (log, todaysDate))
            conn.commit()
            print(f"added log for date: {todaysDate}")
        return "Done", 200

class todoList(Resource):
    def get(self):
        pageTheme = fetchSettingParamFromDB(c, "Theme")

        headers = {'Content-Type': 'text/html'}
        args = parser.parse_args()
        if args['date'] is not None:
            todaysDate = args['date']
            tomorrowsDate = todaysDate # TODO: fix this!
            all_due_events=[]
        else:
            todaysDate = str(datetime.date.today())
            tomorrowsDate = str(datetime.date.today()+datetime.timedelta(days=1))
        if todaysDate == str(datetime.date.today()):
            c.execute("""SELECT * FROM todoList WHERE date < ? and done = 'false' """, (datetime.date.today(),))
            all_due_events = sorted(c.fetchall(), key=lambda tup: tup[1])

        day, month, year = sparateDayMonthYear(todaysDate)
        weekDay = datetime.datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d').weekday()
        numberOfDays = numberOfDaysInMonth(month)

        c.execute("""SELECT * FROM todoList WHERE date >= ? and date < ? and done = 'false' """, ( tomorrowsDate, getThirtyDaysFromNow(day, month, year) ) )
        thisMonthsEvents = sorted(c.fetchall(), key=lambda tup: tup[1])

        c.execute("""SELECT * FROM todoList WHERE date = ? """, (todaysDate,))
        todayTodos = c.fetchall()

        monthsBeginning = datetime.datetime.strptime(f"{year}-{month}-01", '%Y-%m-%d')
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
        return make_response(render_template('todo.html', day = day, month = month, year=year, weekDay = daysOfTheWeek[weekDay],
                                             monthsBeginning=monthsBeginningWeekDay, todayTodos=todayTodos, overDue = all_due_events,
                                             numberOfDays=numberOfDays, thisMonthsEvents = thisMonthsEvents,
                                             Backlog = scrumBoardLists["backlog"], ScrumTodo=scrumBoardLists["todo"],
                                             inProgress=scrumBoardLists["in progress"], done=scrumBoardLists["done"],
                                             ChartMonthDays = ChartMonthDays, ChartDoneTasks=ChartDoneTasks,
                                             ChartthisMonthTasks= ChartthisMonthTasks, pageTheme=pageTheme),200,headers)

    def post(self):
        args = parser.parse_args()

        if args['todo'] is not None:
            if args['date'] is None:
                todaysDate = str(datetime.date.today())
            else:
                todaysDate = args['date']
                if checkIfDateValid(todaysDate):
                    return "date format not valid, should be YYYY-MM-DD", 404
            todo = args['todo'].lower()

            c.execute("""DELETE from todoList where date = ? and task = ?""", (todaysDate, todo))
            if args['delete'] is None:
                c.execute("""INSERT INTO todoList VALUES(?, ?, ?)""", (todo, todaysDate, args['done']))
                print(f"added todo {todo} to todoList for date: {todaysDate} as {args['done']}")
            else:
                print(f"removed todo {todo} from todoList for date: {todaysDate} as {args['done']}")
            conn.commit()
        elif args['cardProj'] is not None:
            proj = args['cardProj']
            task = args['cardTask']
            if args['currentList'] is not None:
                currentList = args['currentList']
                if args['delete'] is not None:
                    print("deleting card:", task)
                    c.execute("""DELETE from scrumBoard where project = ? and task = ? and stage = ?""", (proj, task, currentList))
                    conn.commit()
                else:
                    destList = args['destList']
                    c.execute("""SELECT * FROM scrumBoard WHERE project = ? and task = ? and stage = ? """, (proj, task, currentList))
                    tasks = c.fetchall()
                    if len(tasks)>0:
                        priority = tasks[0][-2]

                    if destList == "done":
                        c.execute("""DELETE from scrumBoard where project = ? and task = ? and stage = ?""", (proj, task, currentList))
                        c.execute("""INSERT INTO scrumBoard VALUES(?, ?, ?, ?, ?)""", (proj, task, destList, priority, str(datetime.date.today())))
                    elif destList == "archive":
                        c.execute("""SELECT * FROM scrumBoard WHERE project = ? and task = ? and stage = ? """, (proj, task, currentList))
                        date = c.fetchall()[0][-1]
                        c.execute("""DELETE from scrumBoard where project = ? and task = ? and stage = ?""", (proj, task, currentList))
                        c.execute("""INSERT INTO scrumBoard VALUES(?, ?, ?, ?, ?)""", (proj, task, destList, priority, str(date)))
                    else:
                        c.execute("""DELETE from scrumBoard where project = ? and task = ? and stage = ?""", (proj, task, currentList))
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
        return make_response(render_template('settings.html', activityList=activityList, pageTheme=pageTheme),200,headers)

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
        return "nothing here!", 200

class Lists(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        pageTheme = fetchSettingParamFromDB(c, "Theme")
        lists = {}
        for listName in ["book", "movie", "anime", "bucketList"]:
            c.execute("""SELECT * FROM lists WHERE type = ? """, (listName, ))
            lists[listName] = sorted(sorted([(name, done) for name, done, type in c.fetchall()]), key=lambda x: x[1])
        return make_response(render_template('lists.html', readList = lists["book"],
                                             animeList=lists["anime"], movieList = lists["movie"],
                                             bucketList=lists["bucketList"],
                                             pageTheme=pageTheme),200,headers)

    def post(self):
        args = parser.parse_args()
        if args['delete'] == '1':
            c.execute("""DELETE from lists where name = ? and type = ?  """, (args["name"].lower(), args["type"]))
        else:
            c.execute("""DELETE from lists where name = ? and type = ? """, (args["name"].lower(), args["type"]))
            c.execute("""INSERT INTO lists VALUES(?, ?, ?)""", (args["name"].lower(), args["done"], args["type"]))
        conn.commit()
        return "nothing here!", 200


@app.route("/downloadDB/")
def downloadDB():
    return send_from_directory(directory=".", filename="journal.db", as_attachment="True", attachment_filename="sqlite_database.db")

api.add_resource(dash, '/home')
api.add_resource(journal, '/journal')
api.add_resource(todoList, '/todoList')
api.add_resource(settings, '/settings')
api.add_resource(Lists, '/Lists')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

conn.close()
