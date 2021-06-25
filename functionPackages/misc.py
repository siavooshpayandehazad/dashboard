import os, datetime
import sqlite3
import hashlib, binascii
from typing import Any
from functionPackages.dateTime import *
from collections import Counter
from datetime import date
import json

def getAudiobooks(path):
    audiobooks = {}
    for a in os.scandir(path):
        if a.is_dir():
            author = a.name
            books = {}
            for b in os.scandir(a):
                if b.is_dir():
                    chapters= []
                    for chapter in os.scandir(b):
                        if ".mp3" in chapter.name:
                            chapters.append(chapter.name)
                    books[b.name]=sorted(chapters)
            audiobooks[author]=books
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
                                f = open(f,'r')
                                data = json.load(f)
                                books[b.name]=data
                            except:
                                print("something is wrong with", f.name)
                            break
                    # if book metadate doesnt exist add it
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
            metadata[author]=books
    return audiobooks, metadata

def getFlashCards(dbCursur):
    dbCursur.execute("""SELECT * FROM flashcards""")
    flashCards = dbCursur.fetchall()
    toReview = []
    setNames = set()
    maxDaysNumbers = 0
    cnts = Counter()
    for item in flashCards:
        date = (datetime.datetime.strptime(item[4], '%Y-%m-%d')+datetime.timedelta(days=int(item[3]))).date()
        todaysDate = datetime.date.today()
        delta = todaysDate - date
        if delta.days >= 0:
            toReview.append(item)
        setNames.add(item[0])
        maxDaysNumbers = max(maxDaysNumbers, int(item[3]))
        cnts[int(item[3])] += 1
    return setNames, maxDaysNumbers, cnts, toReview

def addFlashCards(setName, side1, side2, lastTimeReviewed, dbCursur, dbConnection):
    dbCursur.execute("""INSERT INTO flashcards VALUES(?, ?, ?, ?, ?)""", (setName, side1, side2, 1, lastTimeReviewed))
    dbConnection.commit()

def deleteFlashCards(setName, side1, side2, dbCursur, dbConnection):
    print(f"deleting card {side1} and {side2} from set {setName}")
    dbCursur.execute("""DELETE from flashcards where setName = ? and side1 = ? and side2 = ?""", (setName, side1, side2,))
    dbConnection.commit()

def changeFlashCards(setName, side1, side2, lastTimeReviewed, increament, dbCursur, dbConnection):
    dbCursur.execute("""SELECT * FROM flashcards WHERE setName = ? and side1 = ? and side2 = ?""", (setName, side1, side2,))
    val = dbCursur.fetchall()
    value = int(val[0][3])
    if increament:
        value += 1
        print("increase the reviewInDays to", value)
    else:
        if value == 1:
            return
        value -= 1
        print("increase the reviewInDays to", value)
    dbCursur.execute("""DELETE from flashcards where setName = ? and side1 = ? and side2 = ?""", (setName, side1, side2,))
    dbCursur.execute("""INSERT INTO flashcards VALUES(?, ?, ?, ?, ?)""", (setName, side1, side2, value, lastTimeReviewed))
    dbConnection.commit()

def getTravelDests(dbCursur):
    dbCursur.execute("""SELECT * FROM travelTracker""")
    travels = dbCursur.fetchall()
    allTravels = []
    for item in travels:
        allTravels.append({'name': item[0], 'coords': [item[1], item[2]],})
    return allTravels

def addTravelItem(name, latitude, longitude, dbCursur, dbConnection):
    dbCursur.execute("""INSERT INTO travelTracker VALUES(?, ?, ?)""", (name, latitude, longitude))
    dbConnection.commit()

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
        try:
            d1 =  datetime.datetime.strptime(item[0], '%Y-%m-%d')
            delta = d1 - weeksBeginning
            calList.append([delta.days, item[1], item[2], item[3], 1,1, item[4], item[5]])
        except:
            print("something went wrong here!")
    return calList

def getCalEventsMonth(pageMonth, pageYear, dbCursur):
    dbCursur.execute("""SELECT * FROM calendar WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(),
               getMonthsEnd(pageMonth, pageYear).date(),))
    weeklyCalEvents = dbCursur.fetchall()
    calList = []
    for item in weeklyCalEvents:
        try:
            calList.append([item[0], item[1], item[2], item[3], 1,1, item[4], item[5]])
        except:
            print("something went wrong here!")
    return calList

def getTodaysLogs(dbCursur, todaysDate):
    dbCursur.execute("""SELECT * FROM logTracker WHERE date = ? """, (todaysDate,))
    logValue = dbCursur.fetchall()
    if len(logValue)>0:
        todaysLog = logValue[0][0].replace("\n","<br>")
        todaysLogText = logValue[0][0]
    else:
        todaysLog = ""
        todaysLogText = ""
    return todaysLog, todaysLogText


def allPotosInDir(photoDir, year, date):
    todayPhotos = []
    if os.path.isdir(photoDir):
        for file in os.listdir(photoDir):
            if file.endswith(".jpg") or file.endswith(".JPG") or file.endswith(".png"):
                todayPhotos.append(str(year)+"/"+date+"/"+file)
    todayPhotos.sort()
    return todayPhotos

def allDaysWithPotos(photoDir, year, month):
    daysWithPhotos = []
    if os.path.isdir(photoDir):
        daysWithPhotos = [int(x.split("-")[2]) for x in os.listdir(photoDir) if str(year)+"-"+'%02d' % (month) in x ]
    return sorted(daysWithPhotos)

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
        if tableName in ["HRTracker", "BPTracker"]:
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
    DBCursor.execute("""CREATE TABLE if not exists flashcards (
             setName text, side1 text, side2 text, reviewInDays text, lastTimeReviewed text)""")
    DBCursor.execute("""CREATE TABLE if not exists travelTracker (
             Destination text, latitude text, longitude text)""")
    DBCursor.execute("""CREATE TABLE if not exists HRTracker (
             HR_Min text, HR_Max text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists BPTracker (
             BP_Min text, BP_Max text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists oxygenTracker (
             BO text, date text)""")
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
             task text, date text, done text, color, text)""")
    DBCursor.execute("""CREATE TABLE if not exists scrumBoard (
             project text, task text, stage text, priority text, done_date text)""")
    DBCursor.execute("""CREATE TABLE if not exists settings (
             parameter text, value text)""")
    DBCursor.execute("""CREATE TABLE if not exists lists (
             name text, done text, type text, note text)""")
    DBCursor.execute("""CREATE TABLE if not exists Notes (
             Notebook text, Chapter text, Content text)""")


def setupSettingTable(dbCursur, dbConnection):
    dbCursur.execute("""INSERT INTO settings VALUES(?, ?)""", ("Theme", "Dark"))
    dbCursur.execute("""INSERT INTO settings VALUES(?, ?)""", ("counter", "0"))
    dbCursur.execute("""INSERT INTO settings VALUES(?, ?)""", ("password", "None"))
    dbCursur.execute("""INSERT INTO settings VALUES(?, ?)""", ("activityList", "None"))
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
