import datetime
from dateutil.relativedelta import relativedelta
from functionPackages.misc import getMonthsBeginning, getMonthsEnd

def generateWeightChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    lastMonthsBeginning = datetime.datetime.strptime(f"{pageYear}-{pageMonth}-01", '%Y-%m-%d')-relativedelta(months=+1)
    lastMonthsEnd = datetime.datetime.strptime(f"{pageYear}-{pageMonth}-01", '%Y-%m-%d')-datetime.timedelta(days=1)

    lastMonthsWeights = []
    dbCursur.execute("""SELECT * FROM weightTracker WHERE date >= ? and date <= ?  """,
              (lastMonthsBeginning.date(), lastMonthsEnd.date(),))
    lastMonthsWeights += dbCursur.fetchall()

    monthsWeights = []
    dbCursur.execute("""SELECT * FROM weightTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsWeights += dbCursur.fetchall()

    start_weight = "nan"
    if len(lastMonthsWeights)>0:
        start_weight = float(sorted(lastMonthsWeights, key = lambda x: int(x[1].split("-")[2]))[0][0])
    else:
        if len(monthsWeights)>0:
            start_weight = float(sorted(monthsWeights, key = lambda x: int(x[1].split("-")[2]))[0][0])


    chartWeights=[]
    for i in range(1, numberOfDays+1):
        currentMonth = int(str(datetime.date.today()).split("-")[1])
        weight = "nan"
        for item in monthsWeights:
            if int(item[1].split("-")[2]) == i:
                weight = float(item[0])
        # fix the beginning of the month by extending the first value to beginning
        if (i == 1) and (weight == 'nan'):
            weight = start_weight
        # fix the end of the month by extending the last value to the end...
        # do not do it for current month
        if (i == numberOfDays) and (weight == 'nan') and currentMonth != pageMonth:
            recordedDays = [x for x in chartWeights if (x != 'nan') ]
            if len(recordedDays)>0:
                weight = recordedDays[-1]
        chartWeights.append(weight)
    return chartWeights


def generateHRChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsHR = []
    dbCursur.execute("""SELECT * FROM HRTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsHR += dbCursur.fetchall()

    chartHR_Min=[]
    chartHR_Max=[]
    for i in range(1, numberOfDays+1):
        hr_min = "nan"
        hr_max = "nan"
        for item in monthsHR:
            if int(item[2].split("-")[2]) == i:
                hr_min, hr_max = float(item[0]), float(item[1])
        chartHR_Min.append(hr_min)
        chartHR_Max.append(hr_max)
    return chartHR_Min, chartHR_Max


def generateWorkTrakcerChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsWorkHours = []
    dbCursur.execute("""SELECT * FROM workHourTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsWorkHours += dbCursur.fetchall()

    workTrackerData=[]

    for i in range(1, numberOfDays+1):
        work_hour = "0"     # set to zero in order to avoid failing when adding value
        for item in monthsWorkHours:
            if int(item[1].split("-")[2]) == i:
                work_hour = float(item[0])
        workTrackerData.append(work_hour)
    return workTrackerData

def generateSavingTrackerChartData(pageYear: int, dbCursur):
    yearsSavings = []
    dbCursur.execute("""SELECT * FROM savingTracker WHERE month >= ? and month <= ?  """,
              (pageYear+"-"+"01", pageYear+"-"+"12"))
    yearsSavings += dbCursur.fetchall()

    savingTrackerData=[]
    for i in range(1, 13):
        savingsVal = "nan"
        for item in yearsSavings:
            if int(item[1].split("-")[1]) == i:
                savingsVal = float(item[0])
        savingTrackerData.append(savingsVal)
    return savingTrackerData

def generateSleepChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsSleepHours = []
    dbCursur.execute("""SELECT * FROM sleepTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsSleepHours += dbCursur.fetchall()

    sleepTrackerData=[]

    for i in range(1, numberOfDays+1):
        sleep_hour = "nan"
        for item in monthsSleepHours:
            if int(item[1].split("-")[2]) == i:
                try:
                    sleep_hour = float(item[0])
                except:
                    sleep_hour = "nan"
        sleepTrackerData.append(sleep_hour)
    return sleepTrackerData

def generateStepChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsSteps = []
    dbCursur.execute("""SELECT * FROM stepTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsSteps += dbCursur.fetchall()

    stepsTrackerData=[]

    for i in range(1, numberOfDays+1):
        step_value = "nan"
        for item in monthsSteps:
            if int(item[1].split("-")[2]) == i and item[0].isnumeric():
                try:
                    step_value = float(item[0])
                except:
                    step_value = "nan"
        stepsTrackerData.append(step_value)
    return stepsTrackerData

def generateRunningChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsRuns = []
    dbCursur.execute("""SELECT * FROM runningTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsRuns += dbCursur.fetchall()
    runningTrackerData=[]

    for i in range(1, numberOfDays+1):
        run_value = "nan"
        for item in monthsRuns:
            if int(item[1].split("-")[2]) == i:
                try:
                    run_value = float(item[0])
                except:
                    run_value = "nan"
        runningTrackerData.append(run_value)
    return runningTrackerData

def generatePaceChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsPaces = []
    dbCursur.execute("""SELECT * FROM paceTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsPaces += dbCursur.fetchall()
    paceTrackerData=[]

    for i in range(1, numberOfDays+1):
        pace_value = "nan"
        for item in monthsPaces:
            if int(item[1].split("-")[2]) == i:
                try:
                    pace_value = float(item[0])
                except:
                    pace_value = "nan"
        paceTrackerData.append(pace_value)
    return paceTrackerData
