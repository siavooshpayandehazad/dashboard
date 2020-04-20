import datetime
import pytest
import sys
sys.path.insert(1, '../')

from functionPackage import *


def test_shouldHighlight():
    thisYear = datetime.date.today().year
    thisMonth = datetime.date.today().month
    assert shouldHighlight(str(thisYear), str(thisMonth).zfill(2)) == True
    assert shouldHighlight(str(thisYear-1), str(thisMonth).zfill(2)) == False
    assert shouldHighlight(str(thisYear+1), str(thisMonth).zfill(2)) == False


def test_sparateDayMonthYear():
    # check basic functionality
    assert type(sparateDayMonthYear("2020-10-02")) is tuple
    assert sparateDayMonthYear("2020-10-02") == (2, 10, 2020)
    assert sparateDayMonthYear("2020-02-32") == (29, 2, 2020) #leap year!
    # check exception handling
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
