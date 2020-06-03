import os, datetime
import sqlite3
import hashlib, binascii
from typing import Any
import re
from dateutil.relativedelta import relativedelta

def getTodaysLogs(dbCursur, todaysDate):
    dbCursur.execute("""SELECT * FROM logTracker WHERE date = ? """, (todaysDate,))
    logValue = dbCursur.fetchall()
    if len(logValue)>0:
        todaysLog = logValue[0][0].replace("\n","<br>")
        todaysLogText = logValue[0][0]
    else:
        todaysLog = "<hr><b>work related</b><br><br>"
        todaysLogText = "<hr><b>work related</b>\n\n"
    return todaysLog, todaysLogText


def allPotosInDir(photoDir, year, date):
    todayPhotos = []
    if os.path.isdir(photoDir):
        for file in os.listdir(photoDir):
            if file.endswith(".jpg") or file.endswith(".JPG"):
                todayPhotos.append(str(year)+"/"+date+"/"+file)
    todayPhotos.sort()
    return todayPhotos


def parseDate(dateVal):
    if dateVal is None:
        return str(datetime.date.today())
    else:
        if not checkIfDateValid(dateVal):
            raise ValueError("date format not valid, should be YYYY-MM-DD")
        return dateVal


def addTrackerItemToTable(item: str, itemName: str, itemList, tableName: str,
                          date: str, delete: bool, deleteDay: bool, dbCursur,
                          dbConnection):
    if itemList and (item not in itemList):
        return item+" not found", 400
    dbCursur.execute("SELECT * FROM "+tableName+" WHERE date = ?", (date,))
    if tableName == "workHourTracker":
        fetchedData = dbCursur.fetchall()
        if len(fetchedData)>0:
            item = float(fetchedData[0][0])+float(item)
    if tableName == "moodTracker":     # trying to remove old mood from the table
        for oldItem, todaysDate in dbCursur.fetchall():
            dbCursur.execute("DELETE from "+tableName+" where date = ? and "+itemName+" = ?", (date, oldItem))
    else:
        if deleteDay:
            dbCursur.execute("DELETE from "+tableName+" where date = ?", (date,))
        else:
            dbCursur.execute("DELETE from "+tableName+" where date = ? and "+itemName+" = ?", (date, item))
    if not delete:
        if tableName == "HRTracker":
            dbCursur.execute("INSERT INTO "+tableName+" VALUES(?, ?, ?)", (item[0], item[1], date))
        else:
            dbCursur.execute("INSERT INTO "+tableName+" VALUES(?, ?)", (item, date))
        print(f"{tableName}:: added {item} for date: {date}")
    else:
        print(f"{tableName}:: removed {item} from date: {date}")
    dbConnection.commit()
    return "Done", 200

def addsSavingItemToTable(item: str, date: str, dbCursur, dbConnection):
    month = "-".join(date.split("-")[0:2])
    dbCursur.execute("SELECT * FROM savingTracker WHERE month = ?", (month,))
    fetchedData = dbCursur.fetchall()

    if len(fetchedData)>0:
        item = float(fetchedData[0][0])+float(item)
    else:
        # get last months value
        currentMonth = int(date.split("-")[1])
        currentYear = int(date.split("-")[0])
        counter = 12
        lastMonthFetch = []
        while((len(lastMonthFetch)==0)):
            if currentMonth != 1:
                MonthVal = currentMonth-1
                YearVal = currentYear
            else:
                MonthVal = 12
                YearVal = currentYear -1

            lastMonthVal = str(YearVal)+"-"+str(MonthVal).zfill(2)
            dbCursur.execute("SELECT * FROM savingTracker WHERE month = ?", (lastMonthVal,))
            lastMonthFetch = dbCursur.fetchall()
            currentMonth = MonthVal
            currentYear = YearVal
            counter -= 1
            if counter <= 0:
                break;
        if len(lastMonthFetch)>0:
            lastMonthVal = float(lastMonthFetch[0][0])
        else:
            lastMonthVal = 0
        item = float(lastMonthVal)+float(item)

    dbCursur.execute("DELETE from savingTracker where month = ?", (month,))
    dbCursur.execute("INSERT INTO savingTracker VALUES(?, ?)", (item, month))
    dbConnection.commit()
    return "Done", 200

def collectMonthsData(pageMonth: int, pageYear: int, dbCursur):
    activities = []
    activitiesPlannes = []
    moods = []
    dbCursur.execute("""SELECT * FROM activityTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(),
               getMonthsEnd(pageMonth, pageYear).date(),))
    activities += dbCursur.fetchall()
    dbCursur.execute("""SELECT * FROM activityPlanner WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(),
               getMonthsEnd(pageMonth, pageYear).date(),))
    activitiesPlannes += dbCursur.fetchall()
    dbCursur.execute("""SELECT * FROM moodTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(),
               getMonthsEnd(pageMonth, pageYear).date(),))
    moods += dbCursur.fetchall()
    return activities, activitiesPlannes, moods


def generateWeightChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    lastMonthsBeginning = datetime.datetime.strptime(f"{pageYear}-{pageMonth}-01", '%Y-%m-%d')-relativedelta(months=+1)
    lastMonthsEnd = datetime.datetime.strptime(f"{pageYear}-{pageMonth}-01", '%Y-%m-%d')-datetime.timedelta(days=1)

    lastMonthsWeights = []
    dbCursur.execute("""SELECT * FROM weightTracker WHERE date >= ? and date <= ?  """,
              (lastMonthsBeginning.date(), lastMonthsEnd.date(),))
    lastMonthsWeights += dbCursur.fetchall()

    monthsWeights = []
    dbCursur.execute("""SELECT * FROM weightTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsWeights += dbCursur.fetchall()

    start_weight = "nan"
    if len(lastMonthsWeights)>0:
        start_weight = float(sorted(lastMonthsWeights, key = lambda x: int(x[1].split("-")[2]))[0][0])
    else:
        if len(monthsWeights)>0:
            start_weight = float(sorted(monthsWeights, key = lambda x: int(x[1].split("-")[2]))[0][0])


    chartWeights=[]
    for i in range(1, numberOfDays+1):
        currentMonth = int(str(datetime.date.today()).split("-")[1])
        weight = "nan"
        for item in monthsWeights:
            if int(item[1].split("-")[2]) == i:
                weight = float(item[0])
        # fix the beginning of the month by extending the first value to beginning
        if (i == 1) and (weight == 'nan'):
            weight = start_weight
        # fix the end of the month by extending the last value to the end...
        # do not do it for current month
        if (i == numberOfDays) and (weight == 'nan') and currentMonth != pageMonth:
            recordedDays = [x for x in chartWeights if (x != 'nan') ]
            if len(recordedDays)>0:
                weight = recordedDays[-1]
        chartWeights.append(weight)
    return chartWeights


def generateHRChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsHR = []
    dbCursur.execute("""SELECT * FROM HRTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsHR += dbCursur.fetchall()

    chartHR_Min=[]
    chartHR_Max=[]
    for i in range(1, numberOfDays+1):
        hr_min = "nan"
        hr_max = "nan"
        for item in monthsHR:
            if int(item[2].split("-")[2]) == i:
                hr_min, hr_max = float(item[0]), float(item[1])
        chartHR_Min.append(hr_min)
        chartHR_Max.append(hr_max)
    return chartHR_Min, chartHR_Max

def generateWorkTrakcerChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsWorkHours = []
    dbCursur.execute("""SELECT * FROM workHourTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsWorkHours += dbCursur.fetchall()

    workTrackerData=[]

    for i in range(1, numberOfDays+1):
        work_hour = "0"
        for item in monthsWorkHours:
            if int(item[1].split("-")[2]) == i:
                work_hour = float(item[0])
        workTrackerData.append(work_hour)
    return workTrackerData

def generateSavingTrackerChartData(pageYear: int, dbCursur):
    yearsSavings = []
    dbCursur.execute("""SELECT * FROM savingTracker WHERE month >= ? and month <= ?  """,
              (pageYear+"-"+"01", pageYear+"-"+"12"))
    yearsSavings += dbCursur.fetchall()

    savingTrackerData=[]
    for i in range(1, 13):
        savingsVal = "nan"
        for item in yearsSavings:
            if int(item[1].split("-")[1]) == i:
                savingsVal = float(item[0])
        savingTrackerData.append(savingsVal)
    return savingTrackerData

def generateSleepChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsSleepHours = []
    dbCursur.execute("""SELECT * FROM sleepTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsSleepHours += dbCursur.fetchall()

    sleepTrackerData=[]

    for i in range(1, numberOfDays+1):
        sleep_hour = "nan"
        for item in monthsSleepHours:
            if int(item[1].split("-")[2]) == i:
                sleep_hour = float(item[0])
        sleepTrackerData.append(sleep_hour)
    return sleepTrackerData

def createDB(DBName):
    DBConnection  =  sqlite3.connect(DBName,  check_same_thread=False)
    DBCursor = DBConnection.cursor()
    return DBConnection, DBCursor


def generateDBTables(DBCursor):
    DBCursor.execute("""CREATE TABLE if not exists HRTracker (
             HR_Min text, HR_Max text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists sleepTracker (
             sleepTime text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists savingTracker (
             saving text, month text)""")
    DBCursor.execute("""CREATE TABLE if not exists weightTracker (
             weight text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists workHourTracker (
             work_hour text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists activityTracker (
             activity_name text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists activityPlanner (
             activity_name text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists moodTracker (
             mood_name text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists logTracker (
             log text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists todoList (
             task text, date text, done text)""")
    DBCursor.execute("""CREATE TABLE if not exists scrumBoard (
             project text, task text, stage text, priority text, done_date text)""")
    DBCursor.execute("""CREATE TABLE if not exists settings (
             parameter text, value text)""")
    DBCursor.execute("""CREATE TABLE if not exists lists (
             name text, done text, type text)""")
    DBCursor.execute("""CREATE TABLE if not exists Notes (
             Notebook text, Chapter text, Content text)""")

def sparateDayMonthYear(todaysDate:str) -> tuple:
    if not checkIfDateValid(todaysDate):
        raise ValueError("Wrong date format is passed!")
    year, month, day = [int(m) for m in todaysDate.split("-")]
    day = min(day, numberOfDaysInMonth(month, year))
    return day, month, year


def setupSettingTable(dbCursur, dbConnection):
    c.execute("""INSERT INTO settings VALUES(?, ?)""", ("Theme", "Dark"))
    c.execute("""INSERT INTO settings VALUES(?, ?)""", ("counter", "0"))
    c.execute("""INSERT INTO settings VALUES(?, ?)""", ("password", "None"))
    conn.commit()


def getMonthsBeginning(month: int, year: int) -> datetime:
    return  datetime.datetime.strptime(f"{year}-{month}-01", '%Y-%m-%d')


def getMonthsEnd(month: int, year: int) -> datetime:
    return  getNextMonthsBeginning(month, year)-datetime.timedelta(days=1)

def getNextDay(currentDay: str) -> str:
    return str((datetime.datetime.strptime(currentDay, '%Y-%m-%d')+datetime.timedelta(days=1)).date())

def getNextMonthsBeginning(month: int, year: int) -> datetime:
    if month < 12:
        return datetime.datetime.strptime(f"{year}-{month+1}-01", '%Y-%m-%d')
    else:
        return datetime.datetime.strptime(f"{year+1}-01-01", '%Y-%m-%d')


def getThirtyDaysFromNow(day: int, month: int, year: int) -> datetime:
    """
    returns a datetime object, thirty days in future of the input value
    """
    if month < 12:
        return datetime.datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')+datetime.timedelta(days=30)
    else:
        return datetime.datetime.strptime(f"{year+1}-{month}-{day}", '%Y-%m-%d')


def numberOfDaysInMonth(month: int, year: int) -> int:
    numberOfDays = int(getMonthsEnd(month, year).day)
    return numberOfDays


def checkIfDateValid(date: str) -> bool:
    """
    check format of the date
    """
    checkFormat = re.compile(r'\d\d\d\d-\d\d-\d\d')
    if checkFormat.match(date) is None:
        return False
    return True


def shouldHighlight(pageYear:str, pageMonth:str) -> bool:
    """
    returns True if the pageYear and pageMonth are the same as the current month
    and year. returns False otherwise.
    """
    if (pageYear != str(datetime.date.today().year)) or (pageMonth != str(datetime.date.today().month).zfill(2)):
        return False
    return True


def progress(status, remaining, total):
    print(f'Copied {total-remaining} of {total} pages...')


def backupDatabase(conn):
    try:
        if not os.path.exists('backups'):
            os.mkdir('backups')
        backupCon = sqlite3.connect('backups/journal_backup_'+str(datetime.date.today())+'.db')
        with backupCon:
            conn.backup(backupCon, pages=1, progress=progress)
        print("backup successful")
    except sqlite3.Error as error:
        print("Error while taking backup: ", error)
    finally:
        if(backupCon):
            backupCon.close()


def fetchSettingParamFromDB(DBCursor, param):
    DBCursor.execute("""SELECT * FROM settings WHERE parameter = ?  """, (param,))
    try:
        parameter = DBCursor.fetchall()[0][1]
    except:
        raise ValueError(f"parameter {param} is missing in DB!")
    return parameter


def fetchNotebooks(dbCursur):
    dbCursur.execute("""SELECT * FROM Notes """)
    noteBooksContent = dbCursur.fetchall()
    noteBooks = {}
    for item in noteBooksContent:
        chapters = noteBooks.get(item[0], {})
        chapters[item[1]] = item[2]
        noteBooks[item[0]] = chapters
    return noteBooks

def updateSettingParam(DBCursor, DBConnection, param, value):
    DBCursor.execute("""DELETE from settings where parameter = ? """, (param, ))
    DBCursor.execute("""INSERT INTO settings VALUES(?, ?)""", (param, value))
    DBConnection.commit()
    return None


def hashPassword(password:str) -> any:
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


def verifyPassword(stored_password: str, provided_password: str) -> bool:
    salt = stored_password[:64]
    stored_password = stored_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha512',
                                  provided_password.encode('utf-8'),
                                  salt.encode('ascii'),
                                  100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == stored_password
