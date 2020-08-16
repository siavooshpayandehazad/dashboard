import datetime
import pytest
import sys
sys.path.insert(1, '../')
sys.path.insert(1, '../functionPackages')
print(sys.path)
from functionPackages.misc import *
from functionPackages.charts import *
from functionPackages.dateTime import *
from package import *

db_connection, db_cursor = None, None

def setup_module(module):
    global db_connection, db_cursor
    db_connection, db_cursor =  createDB("test.db")


def teardown_module(module):
    global db_connection
    db_connection.close()


def test_generateDBTables():
    generateDBTables(db_cursor)
    #check if tables exist
    for tableName in ["activityTracker", "moodTracker", "logTracker", "todoList", "scrumBoard", "settings", "lists"]:
        db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tableName, ))
        assert len(db_cursor.fetchall())>0


@pytest.mark.parametrize('activity, colName, tableName, date, list, delete, deleteDay', [
                         ("reading", "activity_name", "activityTracker", str(datetime.date.today()), activityList, False, False),
                         ("bad", "mood_name", "moodTracker", str(datetime.date.today()), moodList, False, False)
])
def test_addTrackerItemToTable(activity, colName, tableName, date, list, delete, deleteDay):
    addTrackerItemToTable(activity, colName, list, tableName, date, delete, deleteDay, db_cursor, db_connection)
    db_cursor.execute("SELECT * FROM "+tableName+" WHERE date = ?", (date,))
    assert (activity, date) in db_cursor.fetchall()


def test_shouldHighlight():
    thisYear = datetime.date.today().year
    thisMonth = datetime.date.today().month
    assert shouldHighlight(str(thisYear), str(thisMonth).zfill(2)) == True
    assert shouldHighlight(str(thisYear-1), str(thisMonth).zfill(2)) == False
    assert shouldHighlight(str(thisYear+1), str(thisMonth).zfill(2)) == False


@pytest.mark.parametrize('date, result',
                         [ ("2020-02-32", (29, 2, 2020)),  #leap year!
                           ("2020-10-02", (2, 10, 2020))
                          ])
def test_sparateDayMonthYear(date, result):
    # check basic functionality
    assert type(sparateDayMonthYear(date)) is tuple
    assert sparateDayMonthYear(date) == result


def test_sparateDayMonthYear_exception():
    with pytest.raises(ValueError):
        sparateDayMonthYear("2020-m0-02")
        sparateDayMonthYear("2020_10-02")


def test_checkIfDateValid():
    assert checkIfDateValid("2020-m0-02") is False
    assert checkIfDateValid("2020-10-02") is True


def test_getThirtyDaysFromNow():
    assert type(getThirtyDaysFromNow(2,10,2020)) is datetime.datetime
    assert getThirtyDaysFromNow(2,10,2020) == datetime.datetime.strptime("2020-11-01", '%Y-%m-%d')


def test_hashPassword():
    assert type(hashPassword("password")) is str
    assert len(hashPassword("password"))==(64+128)


def test_verifyPassword():
    assert type(verifyPassword(hashPassword("password"), "password")) is bool
    assert verifyPassword(hashPassword("password"), "password") == True
    assert verifyPassword(hashPassword("password"), "not password") == False
