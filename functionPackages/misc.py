import os, datetime
import sqlite3
import hashlib, binascii
from typing import Any
from functionPackages.dateTime import *
from collections import Counter
from datetime import date
from pyexiv2 import ImageMetadata, exif
import json

import logging

logger = logging.getLogger(__name__)


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
                            except Exception as e:
                                logger.error(e)
                                logger.error("something is wrong with" + str(f.name))
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


def getFlashCards(dbCursur, lock):
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM flashcards""")
    flashCards = dbCursur.fetchall()
    lock.release()
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


def addFlashCards(setName, side1, side2, lastTimeReviewed, dbCursur, dbConnection, lock):
    lock.acquire(True)
    dbCursur.execute("""INSERT INTO flashcards VALUES(?, ?, ?, ?, ?)""", (setName, side1, side2, 1, lastTimeReviewed))
    dbConnection.commit()
    lock.release()


def deleteFlashCards(setName, side1, side2, dbCursur, dbConnection, lock):
    logger.info(f"deleting card {side1} and {side2} from set {setName}")
    lock.acquire(True)
    dbCursur.execute("""DELETE from flashcards where setName = ? and side1 = ? and side2 = ?""", (setName, side1, side2,))
    dbConnection.commit()
    lock.release()


def changeFlashCards(setName, side1, side2, lastTimeReviewed, increament, dbCursur, dbConnection, lock):
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM flashcards WHERE setName = ? and side1 = ? and side2 = ?""", (setName, side1, side2,))
    val = dbCursur.fetchall()
    lock.release()
    value = int(val[0][3])
    if increament:
        value += 1
        logger.info("increase the reviewInDays to" + str(value))
    else:
        if value == 1:
            return
        value -= 1
        logger.info("increase the reviewInDays to" + str(value))
    lock.acquire(True)
    dbCursur.execute("""DELETE from flashcards where setName = ? and side1 = ? and side2 = ?""", (setName, side1, side2,))
    dbCursur.execute("""INSERT INTO flashcards VALUES(?, ?, ?, ?, ?)""", (setName, side1, side2, value, lastTimeReviewed))
    dbConnection.commit()
    lock.release()


def addTravelItem(name, latitude, longitude, dbCursur, dbConnection, lock):
    lock.acquire(True)
    dbCursur.execute("""INSERT INTO travelTracker VALUES(?, ?, ?)""", (name, latitude, longitude))
    dbConnection.commit()
    lock.release()


def getCalEvents(todaysDate, dbCursur, lock):
    dt = datetime.datetime.strptime(todaysDate, '%Y-%m-%d')
    weeksBeginning = dt - datetime.timedelta(days=dt.weekday())
    weeksEnd = weeksBeginning + datetime.timedelta(days=6)
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM calendar WHERE date >= ? and date <= ?  """,
              (str(weeksBeginning.date()),
               str(weeksEnd.date()),))
    weeklyCalEvents = dbCursur.fetchall()
    lock.release()
    calList = []
    for item in weeklyCalEvents:
        try:
            d1 =  datetime.datetime.strptime(item[0], '%Y-%m-%d')
            delta = d1 - weeksBeginning
            calList.append([delta.days, item[1], item[2], item[3], 1,1, item[4], item[5]])
        except Exception as e:
            logger.error(e)
    return calList


def getCalEventsMonth(todaysDate, dbCursur, lock):
    day, month, year = sparateDayMonthYear(todaysDate)
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM calendar WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(month, year).date(),
               getMonthsEnd(month, year).date(),))
    weeklyCalEvents = dbCursur.fetchall()
    lock.release()
    calList = []
    for item in weeklyCalEvents:
        try:
            calList.append([item[0], item[1], item[2], item[3], 1,1, item[4], item[5]])
        except Exception as e:
            logger.error(e)
    return calList


def getTodaysLogs(dbCursur, todaysDate, lock):
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM logTracker WHERE date = ? """, (todaysDate,))
    logValue = dbCursur.fetchall()
    lock.release()
    if len(logValue)>0:
        todaysLog = logValue[0][0].replace("\n","<br>")
        todaysLogText = logValue[0][0]
    else:
        todaysLog = ""
        todaysLogText = ""
    return todaysLog, todaysLogText


def allPotosInDir(photoDir, year, date):
    todayPhotos = {}
    if os.path.isdir(photoDir):
        for file in os.listdir(photoDir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                tags = []
                try:
                    fileName = "./static/photos/"+str(year)+"/"+date+"/"+file
                    metadata = ImageMetadata(fileName)
                    metadata.read()
                    if 'Exif.Photo.UserComment' in metadata:
                        userdata=json.loads(metadata['Exif.Photo.UserComment'].value)
                        if userdata["tags"] != None:
                            tags = list(userdata["tags"])
                except Exception as e:
                    logger.error(e)
                todayPhotos[str(year)+"/"+date+"/"+file] = tags
            if file.lower().endswith(('.mp4')):
                todayPhotos[str(year)+"/"+date+"/"+file] = []
    return todayPhotos


def allDaysWithPhotos(photoDir, year, month):
    daysWithPhotos = []
    if os.path.isdir(photoDir):
        daysWithPhotos = [int(x.split("-")[2]) for x in os.listdir(photoDir) if str(year)+"-"+'%02d' % (month) in x ]
    return sorted(daysWithPhotos)


def addTrackerItemToTable(item: str, itemName: str, itemList, tableName: str,
                          date: str, delete: bool, deleteDay: bool, dbCursur,
                          dbConnection, lock):
    if itemList and (item not in itemList):
        return item + " not found", 400

    lock.acquire(True)
    dbCursur.execute("SELECT * FROM " + tableName + " WHERE date = ?", (date,))
    fetchedData = dbCursur.fetchall()

    if tableName == "workTracker":
        if (len(fetchedData)>0) and (delete == False):
            logger.info(f"@{datetime.datetime.now()} :: adding {item} time to todays work hours")
            item = float(fetchedData[0][0])+float(item)

    if tableName == "moodTracker":     # trying to remove old mood from the table
        for oldItem, todaysDate in fetchedData:
            dbCursur.execute("DELETE from "+tableName+" where date = ? and "+itemName+" = ?", (date, oldItem))
            dbConnection.commit()
    else:   # all other trackers
        if deleteDay:
            dbCursur.execute("DELETE from "+tableName+" where date = ?", (date,))
        else: # try removing the tracker
            dbCursur.execute("DELETE from "+tableName+" where date = ? and "+itemName+" = ?", (date, item))

    if not delete:
        if tableName in ["HRTracker", "BPTracker"]:
            dbCursur.execute("INSERT INTO "+tableName+" VALUES(?, ?, ?)", (item[0], item[1], date))
        else:
            dbCursur.execute("INSERT INTO "+tableName+" VALUES(?, ?)", (item, date))
        logger.info(f"{tableName}:: added {item} for date: {date}")
    else:
        logger.info(f"{tableName}:: removed {item} from date: {date}")
    dbConnection.commit()
    lock.release()
    return "Done", 200


def addsSavingItemToTable(item: str, date: str, dbCursur, dbConnection, lock):
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
    lock.acquire(True)
    dbCursur.execute("DELETE from savingTracker where month = ?", (month,))
    dbCursur.execute("INSERT INTO savingTracker VALUES(?, ?)", (item, month))
    dbConnection.commit()
    lock.release()
    return "Done", 200


def addsMortgageItemToTable(item: str, date: str, dbCursur, dbConnection, lock):
    month = "-".join(date.split("-")[0:2])
    lock.acquire(True)
    dbCursur.execute("SELECT * FROM mortgageTracker WHERE month = ?", (month,))
    fetchedData = dbCursur.fetchall()
    lock.release()
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
            lock.acquire(True)
            dbCursur.execute("SELECT * FROM mortgageTracker WHERE month = ?", (lastMonthVal,))
            lastMonthFetch = dbCursur.fetchall()
            lock.release()
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
    lock.acquire(True)
    dbCursur.execute("DELETE from mortgageTracker where month = ?", (month,))
    dbCursur.execute("INSERT INTO mortgageTracker VALUES(?, ?)", (item, month))
    dbConnection.commit()
    lock.release()
    return "Done", 200


def collectMonthsData(pageMonth: int, pageYear: int, dbCursur, lock):
    activities = []
    activitiesPlannes = []
    moods = []
    lock.acquire(True)
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
    lock.release()
    return activities, activitiesPlannes, moods


def createDB(DBName):
    DBConnection  =  sqlite3.connect(DBName,  check_same_thread=False)
    DBCursor = DBConnection.cursor()
    return DBConnection, DBCursor


def generateDBTables(DBCursor, dbConnection, lock):
    lock.acquire(True)
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
    DBCursor.execute("""CREATE TABLE if not exists mortgageTracker (
             mortgage text, month text)""")
    DBCursor.execute("""CREATE TABLE if not exists weightTracker (
             weight text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists workTracker (
             work_hour text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists stepTracker (
             steps text, date text)""")
    DBCursor.execute("""CREATE TABLE if not exists hydrationTracker (
             hydration text, date text)""")
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
    dbConnection.commit()
    lock.release()


def setupSettingTable(dbCursur, dbConnection, lock):
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("Theme",))
    try:
        parameter = dbCursur.fetchall()[0][1]
    except:
        dbCursur.execute("""INSERT INTO settings VALUES(?, ?)""", ("Theme", "Dark"))

    dbCursur.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("counter",))
    try:
        parameter = dbCursur.fetchall()[0][1]
    except:
        dbCursur.execute("""INSERT INTO settings VALUES(?, ?)""", ("counter", "0"))

    for item in ["activityList", "activityList", "MAIL_SERVER", "MAIL_PORT", "MAIL_USE_SSL",
                 "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_RECIPIENT", "audiobooksPath"]:
        dbCursur.execute("""SELECT * FROM settings WHERE parameter = ?  """, (item,))
        try:
            parameter = dbCursur.fetchall()[0][1]
        except:
            dbCursur.execute("""INSERT INTO settings VALUES(?, ?)""", (item, "None"))

    dbConnection.commit()
    lock.release()


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
        logger.info("backup successful")
    except sqlite3.Error as error:
        logger.error("Error while taking backup: " +  str(error))
    finally:
        if(backupCon):
            backupCon.close()


def fetchSettingParamFromDB(DBCursor, param, lock):
    lock.acquire(True)
    DBCursor.execute("""SELECT * FROM settings WHERE parameter = ?  """, (param,))
    try:
        parameter = DBCursor.fetchall()[0][1]
    except:
        raise ValueError(f"parameter {param} is missing in DB!")
    lock.release()
    return parameter


def fetchNotebooks(dbCursur, lock):
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM Notes """)
    noteBooksContent = dbCursur.fetchall()
    lock.release()
    noteBooks = {}
    for item in noteBooksContent:
        chapters = noteBooks.get(item[0], {})
        chapters[item[1]] = item[2]
        noteBooks[item[0]] = chapters
    return noteBooks


def updateSettingParam(DBCursor, DBConnection, param, value, lock):
    try:
        lock.acquire(True)
        DBCursor.execute("UPDATE settings SET value = ? WHERE parameter = ?", (value, param,))
        DBConnection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


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


def getTodos(todaysDate, dbCursur, lock):
    day, month, year = sparateDayMonthYear(todaysDate)
    monthsBeginning = getMonthsBeginning(month, year)
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM todoList WHERE date < ? and done = 'false' """, (todaysDate,))
    all_due_events = sorted(dbCursur.fetchall(), key=lambda tup: tup[1])

    dbCursur.execute("""SELECT * FROM todoList WHERE date < ? and date >= ? and done = 'true'""", (todaysDate, monthsBeginning.date()))
    all_due_events += sorted(dbCursur.fetchall(), key=lambda tup: tup[1])

    dbCursur.execute("""SELECT * FROM todoList WHERE date >= ? and date < ? """, (getNextDay(todaysDate), getThirtyDaysFromNow(day, month, year)))
    thisMonthsEvents = sorted(dbCursur.fetchall(), key=lambda tup: tup[1])

    dbCursur.execute("""SELECT * FROM todoList WHERE date = ? """, (todaysDate,))
    todayTodos = dbCursur.fetchall()
    lock.release()
    return all_due_events, thisMonthsEvents, todayTodos


def getScrumTasks(todaysDate, dbCursur, lock):
    day, month, year = sparateDayMonthYear(todaysDate)
    monthsBeginning = getMonthsBeginning(month, year)
    numberOfDays = numberOfDaysInMonth(int(month), int(year))
    monthsEnd = getMonthsEnd(month, year)

    scrumBoardLists = {}
    for stage in ["backlog", "todo", "in progress", "done"]:
        lock.acquire(True)
        dbCursur.execute("""SELECT * FROM scrumBoard WHERE stage = ? """, (stage, ))
        # sort based on priority
        scrumBoardLists[stage] = sorted([(task, proj, priority) for task, proj, stage, priority, done_date in dbCursur.fetchall()], key = lambda x: x[2])
        lock.release()

    # find all the tasks done during this month's period!
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM scrumBoard WHERE done_date >= ? and done_date <= ? """, (monthsBeginning.date(),  monthsEnd.date()))
    doneTasks = sorted([int(done_date.split("-")[2]) for proj, task,  stage, priority, done_date in dbCursur.fetchall()])
    lock.release()
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
    return scrumBoardLists, ChartDoneTasks, ChartMonthDays, ChartthisMonthTasks


def deleteScrumTask(proj, task, dbCursur, dbConnection, lock):
    try:
        logger.info("deleting card:" + str(task))
        lock.acquire(True)
        dbCursur.execute("""DELETE from scrumBoard where project = ? and task = ?""", (proj, task))
        dbConnection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def addScrumTask(proj, task, list, priority, date, dbCursur, dbConnection, lock):
    try:
        lock.acquire(True)
        dbCursur.execute("""INSERT INTO scrumBoard VALUES(?, ?, ?, ?, ?)""", (proj, task, list, priority, date))
        dbConnection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def send_mail(msg_subject, msg_content, flask_app, mailInstance, dbCursur, lock):
    serverEmail = fetchSettingParamFromDB(dbCursur, "MAIL_USERNAME", lock)
    appPassword = fetchSettingParamFromDB(dbCursur, "MAIL_PASSWORD", lock)
    mailServer = fetchSettingParamFromDB(dbCursur, "MAIL_SERVER", lock)
    mailPort = fetchSettingParamFromDB(dbCursur, "MAIL_PORT", lock)
    mailSSL = fetchSettingParamFromDB(dbCursur, "MAIL_USE_SSL", lock)
    recipientEmail = fetchSettingParamFromDB(dbCursur, "MAIL_RECIPIENT", lock)
    logger.info("sending email to: " + recipientEmail)
    if (serverEmail != "None") and (appPassword != "None") and (recipientEmail != "None"):
        flask_app.config.update(
            MAIL_SERVER = str(mailServer),
            MAIL_PORT = int(mailPort),
            MAIL_USE_SSL = bool(mailSSL),
            MAIL_USERNAME = serverEmail,
            MAIL_PASSWORD = appPassword
        )
        mailInstance.init_app(flask_app)
        msg = mailInstance.send_message(
            msg_subject,
            sender=str(serverEmail),
            recipients=[str(recipientEmail)],
            body=msg_content
        )
    logger.info("email sent!")
    return 'Mail sent'


def add_tag_to_picture(filename, tag):
    metadata = ImageMetadata(filename)
    metadata.read()
    currentTags = []
    if 'Exif.Photo.UserComment' in metadata:
        userdata=json.loads(metadata['Exif.Photo.UserComment'].value)
        if userdata["tags"] != None:
            currentTags = list(userdata["tags"])
    tags = [tag] + currentTags
    metadata = ImageMetadata(filename)
    metadata.read()
    userdata={'tags':tags}
    metadata['Exif.Photo.UserComment']=json.dumps(userdata)
    metadata.write()
    return True


def remove_tag_from_picture(filename, tag):
    metadata = ImageMetadata(filename)
    metadata.read()
    currentTags = []
    if 'Exif.Photo.UserComment' in metadata:
        userdata=json.loads(metadata['Exif.Photo.UserComment'].value)
        if userdata["tags"] != None:
            currentTags = list(userdata["tags"])
    currentTags = [] if userdata["tags"] == None else list(userdata["tags"])
    if len(currentTags)>0:
        currentTags.remove(tag)
    metadata = ImageMetadata(filename)
    metadata.read()
    userdata={'tags':currentTags}
    metadata['Exif.Photo.UserComment']=json.dumps(userdata)
    metadata.write()
    return True
