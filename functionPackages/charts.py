import datetime
from dateutil.relativedelta import relativedelta
from functionPackages.misc import getMonthsBeginning, getMonthsEnd

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

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


def generateYearWeightChartData(pageYear: int, numberOfDays: int, dbCursur):
    weight = []
    for i in range(1, 13):
        dbCursur.execute("""SELECT * FROM weightTracker WHERE date >= ? and date <= ?  """,
                (getMonthsBeginning(i, pageYear).date(), getMonthsEnd(i, pageYear).date(),))
        res = dbCursur.fetchall()
        weightList = [float(x[0]) for x in res if is_number(x[0])]
        if len(weightList)>0:
            weight.append(float(sum(weightList))/len(weightList))
        else:
            weight.append("nan")
    return weight


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

def generateYearHRChartData(pageYear: int, numberOfDays: int, dbCursur):
    HR_Min_Avg = []
    HR_Max_Avg = []
    for i in range(1, 13):
        dbCursur.execute("""SELECT * FROM HRTracker WHERE date >= ? and date <= ?  """,
                (getMonthsBeginning(i, pageYear).date(), getMonthsEnd(i, pageYear).date(),))
        res = dbCursur.fetchall()
        HR_Min = [float(x[0]) for x in res if is_number(x[0])]
        HR_Max = [float(x[1]) for x in res if is_number(x[1])]
        if len(HR_Min)>0:
            HR_Min_Avg.append(float(sum(HR_Min))/len(HR_Min))
        else:
            HR_Min_Avg.append("nan")
        if len(HR_Max)>0:
            HR_Max_Avg.append(float(sum(HR_Max))/len(HR_Max))
        else:
            HR_Max_Avg.append("nan")
    return HR_Min_Avg, HR_Max_Avg


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

def generateYearWHChartData(pageYear: int, numberOfDays: int, dbCursur):
    yearSleep = []
    for i in range(1, 13):
        dbCursur.execute("""SELECT * FROM workHourTracker WHERE date >= ? and date <= ?  """,
                (getMonthsBeginning(i, pageYear).date(), getMonthsEnd(i, pageYear).date(),))
        yearSleep.append(sum([float(x[0]) for x in dbCursur.fetchall() if is_number(x[0])]))
    return yearSleep

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

def generateYearSleepChartData(pageYear: int, numberOfDays: int, dbCursur):
    yearSleep = []
    for i in range(1, 13):
        dbCursur.execute("""SELECT * FROM sleepTracker WHERE date >= ? and date <= ?  """,
                (getMonthsBeginning(i, pageYear).date(), getMonthsEnd(i, pageYear).date(),))
        yearSleep.append(sum([float(x[0]) for x in dbCursur.fetchall() if is_number(x[0])]))
    return yearSleep

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

def generateYearStepChartData(pageYear: int, numberOfDays: int, dbCursur):
    yearSteps = []
    for i in range(1, 13):
        dbCursur.execute("""SELECT * FROM stepTracker WHERE date >= ? and date <= ?  """,
                (getMonthsBeginning(i, pageYear).date(), getMonthsEnd(i, pageYear).date(),))
        yearSteps.append(sum([int(x[0]) for x in dbCursur.fetchall() if is_number(x[0])]))
    return yearSteps

def generateYearRunChartData(pageYear: int, numberOfDays: int, dbCursur):
    yearRuns = []
    for i in range(1, 13):
        dbCursur.execute("""SELECT * FROM runningTracker WHERE date >= ? and date <= ?  """,
                (getMonthsBeginning(i, pageYear).date(), getMonthsEnd(i, pageYear).date(),))
        yearRuns.append(sum([float(x[0]) for x in dbCursur.fetchall() if is_number(x[0])]))
    return yearRuns

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
                pace_value = "nan"
                try:
                    if float(item[0])>0:
                       pace_value = float(item[0])
                except:
                    pace_value = "nan"
        paceTrackerData.append(pace_value)
    return paceTrackerData

def generateYearMoodChartData(pageYear: int, numberOfDays: int, dbCursur):
    yearMoods = []
    for i in range(1, 13):
        dbCursur.execute("""SELECT * FROM moodTracker WHERE date >= ? and date <= ?  """,
                (getMonthsBeginning(i, pageYear).date(), getMonthsEnd(i, pageYear).date(),))
        res = [x[0] for x in dbCursur.fetchall()]
        MonthVal = res.count("great")*4.5 + res.count("good")*3.5 + res.count("ok")*2.5 + res.count("bad")*1.5 + res.count("awful")*0.5

        if len(res) > 0:
            moodVal = MonthVal/float(len(res))
            yearMoods.append(moodVal)
        else:
            yearMoods.append("nan")
    return yearMoods
