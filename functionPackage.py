import os, datetime
import sqlite3
import hashlib, binascii
from typing import Any
import re


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


def addTrackerItemToTable(item: str, itemName: str, itemList,
                          tableName: str, date: str, dbCursur, dbConnection):
    if item not in itemList:
        return item+" not found", 400
    dbCursur.execute("SELECT * FROM "+tableName+" WHERE date = ?", (date,))
    if itemName == "mood_name":     # trying to remove old mood from the table
        for oldItem, todaysDate in dbCursur.fetchall():
            dbCursur.execute("DELETE from "+tableName+" where date = ? and "+itemName+" = ?", (date, oldItem))
    dbCursur.execute("INSERT INTO "+tableName+" VALUES(?, ?)", (item, date))
    dbConnection.commit()
    print(f"{tableName}:: added {item} for date: {date}")
    return "Done", 200


def collectMonthsActivityAndMood(pageMonth: int, pageYear: int, dbCursur):
    activities = []
    moods = []
    dbCursur.execute("""SELECT * FROM activityTracker WHERE date >= ? and date < ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(),
               getMonthsEnd(pageMonth, pageYear).date(),))
    activities += dbCursur.fetchall()
    dbCursur.execute("""SELECT * FROM moodTracker WHERE date >= ? and date < ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(),
               getMonthsEnd(pageMonth, pageYear).date(),))
    moods += dbCursur.fetchall()
    return activities, moods


def createDB(DBName):
    DBConnection  =  sqlite3.connect(DBName,  check_same_thread=False)
    DBCursor = DBConnection.cursor()
    return DBConnection, DBCursor


def generateDBTables(DBCursor):
    DBCursor.execute("""CREATE TABLE if not exists activityTracker (
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
