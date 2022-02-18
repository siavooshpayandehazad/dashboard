import datetime
import re

def convert_time_to24(time12:str) -> str:
    """
    takes 'hh:MM:SS AM' or 'hh:MM:SS PM' and returns
    'HH:MM:SS' in 24 hour format.
    convertTimeTo24('12:XX:XX AM') will return 00:XX:XX
    convertTimeTo24('12:XX:XX AM') will return 12:XX:XX
    """
    if time12[-2:] == "AM" and time12[:2] == "12":
        return "00" + time12[2:-2]
    elif time12[-2:] == "AM":
        return time12[:-2]
    elif time12[-2:] == "PM" and time12[:2] == "12":
        return time12[:-2]
    else:
        return str(int(time12[:2]) + 12) + time12[2:8]


def sparateDayMonthYear(todaysDate:str) -> tuple:
    if not checkIfDateValid(todaysDate):
        raise ValueError("Wrong date format is passed!")
    year, month, day = [int(m) for m in todaysDate.split("-")]
    day = min(day, numberOfDaysInMonth(month, year))
    return day, month, year


def parseDate(dateVal):
    if dateVal is None:
        return str(datetime.date.today())
    else:
        if not checkIfDateValid(dateVal):
            raise ValueError("date format not valid, should be YYYY-MM-DD")
        return dateVal


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
