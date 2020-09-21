import os, datetime
import sqlite3
import hashlib, binascii
from typing import Any
from functionPackages.dateTime import *

from datetime import date


def getCalEvents(todaysDate, dbCursur):
    dt = datetime.datetime.strptime(todaysDate, '%Y-%m-%d')
    weeksBeginning = dt - datetime.timedelta(days=dt.weekday())
    weeksEnd = weeksBeginning + datetime.timedelta(days=6)
    dbCursur.execute("""SELECT * FROM calendar WHERE date >= ? and date <= ?  """,
              (str(weeksBeginning.date()),
               str(weeksEnd.date()),))
    weeklyCalEvents = dbCursur.fetchall()
    calList = []
    for item in weeklyCalEvents:
        d1 =  datetime.datetime.strptime(item[0], '%Y-%m-%d')
        delta = d1 - weeksBeginning
        calList.append([delta.days, item[1], item[2], item[3], 1,1, item[4], item[5]])
    return calList


def getTodaysLogs(dbCursur, todaysDate):
    dbCursur.execute("""SELECT * FROM logTracker WHERE date = ? """, (todaysDate,))
    logValue = dbCursur.fetchall()
    if len(logValue)>0:
        todaysLog = logValue[0][0].replace("\n","<br>")
        todaysLogText = logValue[0][0]
    else:
        todaysLog = " "
        todaysLogText = " "
    return todaysLog, todaysLogText


def allPotosInDir(photoDir, year, date):
    todayPhotos = []
    if os.path.isdir(photoDir):
        for file in os.listdir(photoDir):
            if file.endswith(".jpg") or file.endswith(".JPG"):
                todayPhotos.append(str(year)+"/"+date+"/"+file)
    todayPhotos.sort()
    return todayPhotos


def addTrackerItemToTable(item: str, itemName: str, itemList, tableName: str,
                          date: str, delete: bool, deleteDay: bool, dbCursur,
                          dbConnection):
    if itemList and (item not in itemList):
        return item + " not found", 400

    dbCursur.execute("SELECT * FROM " + tableName + " WHERE date = ?", (date,))
    fetchedData = dbCursur.fetchall()

    if tableName == "workHourTracker":
        print(f"@{datetime.datetime.now()} :: adding {item} time to todays work hours")
        if len(fetchedData)>0:
            item = float(fetchedData[0][0])+float(item)
    if tableName == "moodTracker":     # trying to remove old mood from the table
        for oldItem, todaysDate in fetchedData:
            dbCursur.execute("DELETE from "+tableName+" where date = ? and "+itemName+" = ?", (date, oldItem))
            dbConnection.commit()
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


def createDB(DBName):
    DBConnection  =  sqlite3.connect(DBName,  check_same_thread=False)
    DBCursor = DBConnection.cursor()
    return DBConnection, DBCursor


def generateDBTables(DBCursor):
    DBCursor.execute("""CREATE TABLE if not exists calendar (
             date text, startTime text, endTime text, eventName text, color text, details text)""")
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
    DBCursor.execute("""CREATE TABLE if not exists stepTracker (
             steps text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists runningTracker (
             run text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists paceTracker (
             pace text, date text)""")
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


def setupSettingTable(dbCursur, dbConnection):
    c.execute("""INSERT INTO settings VALUES(?, ?)""", ("Theme", "Dark"))
    c.execute("""INSERT INTO settings VALUES(?, ?)""", ("counter", "0"))
    c.execute("""INSERT INTO settings VALUES(?, ?)""", ("password", "None"))
    dbConnection.commit()


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
