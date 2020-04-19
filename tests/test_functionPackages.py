import datetime

import sys
sys.path.insert(1, '../')

from functionPackage import *


def test_shouldHighlight():
    thisYear = datetime.date.today().year
    thisMonth = datetime.date.today().month
    assert shouldHighlight(str(thisYear), str(thisMonth).zfill(2)) == True
    assert shouldHighlight(str(thisYear-1), str(thisMonth).zfill(2)) == False
    assert shouldHighlight(str(thisYear+1), str(thisMonth).zfill(2)) == False
