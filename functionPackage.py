import os, datetime
import sqlite3
import hashlib, binascii
from typing import Any
import re


def getTodaysLogs(db_c, todaysDate):
    db_c.execute("""SELECT * FROM logTracker WHERE date = ? """, (todaysDate,))
    logValue = db_c.fetchall()
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


def addTrackerItemToTable(item: str, itemName: str, itemList, tableName: str, date: str):
    if item not in itemList:
        return item+" not found", 400
    c.execute("SELECT * FROM "+tableName+" WHERE date = ?", (date,))
    for oldItem, todaysDate in c.fetchall():
        c.execute("DELETE from "+tableName+" where date = ? and "+itemName+" = ?", (date, oldItem))
    c.execute("INSERT INTO "+tableName+" VALUES(?, ?)", (item, date))
    conn.commit()
    print(f"{tableName}:: added {item} for date: {date}")
    return "Done", 200


def generateDBTables(db_conn_handel):
    db_conn_handel.execute("""CREATE TABLE if not exists activityTracker (
             activity_name text, date text)""")

    db_conn_handel.execute("""CREATE TABLE if not exists moodTracker (
             mood_name text, date text)""")

    db_conn_handel.execute("""CREATE TABLE if not exists logTracker (
             log text, date text)""")

    db_conn_handel.execute("""CREATE TABLE if not exists todoList (
             task text, date text, done text)""")

    db_conn_handel.execute("""CREATE TABLE if not exists scrumBoard (
             project text, task text, stage text, priority text, done_date text)""")

    db_conn_handel.execute("""CREATE TABLE if not exists settings (
             parameter text, value text)""")

    db_conn_handel.execute("""CREATE TABLE if not exists lists (
             name text, done text, type text)""")


def sparateDayMonthYear(todaysDate:str) -> tuple:
    if not checkIfDateValid(todaysDate):
        raise ValueError("Wrong date format is passed!")
    day = int(todaysDate.split("-")[2])
    month = int(todaysDate.split("-")[1])
    year = int(todaysDate.split("-")[0])
    if day>numberOfDaysInMonth(year, month):
        day = numberOfDaysInMonth(year, month)
    return day, month, year


def getMonthsBeginning(month, year):
    return  datetime.datetime.strptime(f"{year}-{month}-01", '%Y-%m-%d')


def getMonthsEnd(month, year):
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


def numberOfDaysInMonth(year: str, month: str) -> int:
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
    highlight = True
    if (pageYear != str(datetime.date.today().year)) or (pageMonth != str(datetime.date.today().month).zfill(2)):
        highlight = False
    return highlight


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


def fetchSettingParamFromDB(cursor, param):
    cursor.execute("""SELECT * FROM settings WHERE parameter = ?  """, (param,))
    try:
        parameter = cursor.fetchall()[0][1]
    except:
        raise ValueError(f"parameter {param} is missing in DB!")
    return parameter


def updateSettingParam(cursor, connection, param, value):
    cursor.execute("""DELETE from settings where parameter = ? """, (param, ))
    cursor.execute("""INSERT INTO settings VALUES(?, ?)""", (param, value))
    connection.commit()
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
