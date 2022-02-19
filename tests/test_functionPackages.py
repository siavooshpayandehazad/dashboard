import datetime
import pytest
import sys
sys.path.insert(1, '.')
sys.path.insert(1, 'functionPackages')
print(sys.path)
from functionPackages.misc import *
from functionPackages.charts import *
from functionPackages.dateTime import *
from package import *

db_connection, db_cursor = None, None
activityList = None


def setup_module(module):
    global db_connection, db_cursor
    db_connection, db_cursor =  create_db("test.db")


def teardown_module(module):
    global db_connection
    db_connection.close()


def test_generateDBTables():
    generate_db_tables(db_cursor, db_connection)
    #check if tables exist
    for tableName in ["activityTracker", "moodTracker", "logTracker", "todoList", "scrumBoard", "settings", "lists"]:
        db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tableName, ))
        assert len(db_cursor.fetchall())>0


@pytest.mark.parametrize('activity, colName, tableName, date, list, delete, deleteDay', [
                         ("reading", "activity_name", "activityTracker", str(datetime.date.today()), [], False, False),
                         ("bad", "mood_name", "moodTracker", str(datetime.date.today()), moodList, False, False)
])
def test_addTrackerItemToTable(activity, colName, tableName, date, list, delete, deleteDay):
    add_tracker_item_to_table(activity, colName, list, tableName, date, delete, deleteDay, db_cursor, db_connection)
    db_cursor.execute("SELECT * FROM "+tableName+" WHERE date = ?", (date,))
    assert (activity, date) in db_cursor.fetchall()


def test_shouldHighlight():
    thisYear = datetime.date.today().year
    thisMonth = datetime.date.today().month
    assert should_highlight(str(thisYear), str(thisMonth).zfill(2)) == True
    assert should_highlight(str(thisYear - 1), str(thisMonth).zfill(2)) == False
    assert should_highlight(str(thisYear + 1), str(thisMonth).zfill(2)) == False


@pytest.mark.parametrize('date, result',
                         [ ("2020-02-32", (29, 2, 2020)),  #leap year!
                           ("2020-10-02", (2, 10, 2020))
                          ])
def test_sparateDayMonthYear(date, result):
    # check basic functionality
    assert type(separate_day_month_year(date)) is tuple
    assert separate_day_month_year(date) == result


def test_sparateDayMonthYear_exception():
    with pytest.raises(ValueError):
        separate_day_month_year("2020-m0-02")
        separate_day_month_year("2020_10-02")


def test_checkIfDateValid():
    assert check_if_date_valid("2020-m0-02") is False
    assert check_if_date_valid("2020-10-02") is True


def test_getThirtyDaysFromNow():
    assert type(get_thirty_days_from_now(2, 10, 2020)) is datetime.datetime
    assert get_thirty_days_from_now(2, 10, 2020) == datetime.datetime.strptime("2020-11-01", '%Y-%m-%d')


def test_hashPassword():
    assert type(hash_password("password")) is str
    assert len(hash_password("password")) == (64 + 128)


def test_verifyPassword():
    assert type(verify_password(hash_password("password"), "password")) is bool
    assert verify_password(hash_password("password"), "password") == True
    assert verify_password(hash_password("password"), "not password") == False
