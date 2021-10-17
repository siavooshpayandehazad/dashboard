import datetime
from dateutil.relativedelta import relativedelta
from functionPackages.misc import getMonthsBeginning, getMonthsEnd, numberOfDaysInMonth
import os
import json

from flask import current_app as app
import logging

logger = logging.getLogger(__name__)

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


def weightFunc(res, weight):
    weightList = [float(x[0]) for x in res if is_number(x[0])]
    if len(weightList)>0:
        weight.append(float(sum(weightList))/len(weightList))
    else:
        weight.append("nan")
    return weight


def BOFunc(res, BO):
    BOList = [float(x[0]) for x in res if is_number(x[0])]
    if len(BOList)>0:
        BO.append(float(sum(BOList))/len(BOList))
    else:
        BO.append("nan")
    return BO


def WHFunc(res, yearWH):
    yearWH.append(sum([float(x[0]) for x in res if is_number(x[0])]))
    return yearWH


def sleepFunc(res, yearSleep):
    yearSleep.append(sum([float(x[0]) for x in res if is_number(x[0])]))
    return yearSleep


def stepFunc(res, yearStep):
    yearStep.append(sum([float(x[0]) for x in res if is_number(x[0])]))
    return yearStep


def moodFunc(res, yearMoods):
    res = [x[0] for x in res]
    MonthVal = res.count("great")*4.5 + res.count("good")*3.5 + res.count("ok")*2.5 + res.count("bad")*1.5 + res.count("awful")*0.5
    if len(res) > 0:
        moodVal = MonthVal/float(len(res))
        yearMoods.append(moodVal)
    else:
        yearMoods.append("nan")
    return yearMoods


def runFunc(res, yearRuns):
    yearRuns.append(sum([float(x[0]) for x in res if is_number(x[0])]))
    return yearRuns


def genYearChartData(pageYear: int, tableName: str, calcFunc, dbCursur):
    retList = []
    for i in range(1, 13):
        monthsBeginning = str(getMonthsBeginning(i, pageYear).date())
        for j in range(0, 3):
            weekBeginning = datetime.datetime.strptime(monthsBeginning, '%Y-%m-%d')+datetime.timedelta(days=7*j)
            weekEnd = weekBeginning+datetime.timedelta(days=7)
            dbCursur.execute("SELECT * FROM " + tableName + " WHERE date >= ? and date < ?  ",
                (weekBeginning.date(), weekEnd.date(),))
            retList = calcFunc(dbCursur.fetchall(), retList)
        dbCursur.execute("SELECT * FROM " + tableName + " WHERE date >= ? and date <= ?  ",
            (weekEnd.date(), getMonthsEnd(i, pageYear).date(),))
        retList = calcFunc(dbCursur.fetchall(), retList)
    return retList


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
        monthsBeginning = str(getMonthsBeginning(i, pageYear).date())
        for j in range(0, 3):
            weekBeginning = datetime.datetime.strptime(monthsBeginning, '%Y-%m-%d')+datetime.timedelta(days=7*j)
            weekEnd = weekBeginning+datetime.timedelta(days=7)
            dbCursur.execute("""SELECT * FROM HRTracker WHERE date >= ? and date < ?  """,
                (weekBeginning.date(), weekEnd.date(),))
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
        dbCursur.execute("""SELECT * FROM HRTracker WHERE date >= ? and date <= ?  """,
            (weekEnd.date(), getMonthsEnd(i, pageYear).date(),))
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


def generateBPChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsBP = []
    dbCursur.execute("""SELECT * FROM BPTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsBP += dbCursur.fetchall()
    chartBP_Min=[]
    chartBP_Max=[]
    for i in range(1, numberOfDays+1):
        bp_min = "nan"
        bp_max = "nan"
        for item in monthsBP:
            if int(item[2].split("-")[2]) == i:
                bp_min, bp_max = float(item[0]), float(item[1])
        chartBP_Min.append(bp_min)
        chartBP_Max.append(bp_max)
    return chartBP_Min, chartBP_Max


def generateYearBPChartData(pageYear: int, numberOfDays: int, dbCursur):
    BP_Min_Avg = []
    BP_Max_Avg = []
    for i in range(1, 13):
        monthsBeginning = str(getMonthsBeginning(i, pageYear).date())
        aggregateDays = round(numberOfDaysInMonth(int(i), int(pageYear))/4)
        for j in range(0, 3):
            weekBeginning = datetime.datetime.strptime(monthsBeginning, '%Y-%m-%d')+datetime.timedelta(days=7*j)
            weekEnd = weekBeginning+datetime.timedelta(days=7)
            dbCursur.execute("""SELECT * FROM BPTracker WHERE date >= ? and date < ?  """,
                (weekBeginning.date(), weekEnd.date(),))
            res = dbCursur.fetchall()
            BP_Min = [float(x[0]) for x in res if is_number(x[0])]
            BP_Max = [float(x[1]) for x in res if is_number(x[1])]
            if len(BP_Min)>0:
                BP_Min_Avg.append(float(sum(BP_Min))/len(BP_Min))
            else:
                BP_Min_Avg.append("nan")
            if len(BP_Max)>0:
                BP_Max_Avg.append(float(sum(BP_Max))/len(BP_Max))
            else:
                BP_Max_Avg.append("nan")
        dbCursur.execute("""SELECT * FROM BPTracker WHERE date >= ? and date <= ?  """,
            (weekEnd.date(), getMonthsEnd(i, pageYear).date(),))
        res = dbCursur.fetchall()
        BP_Min = [float(x[0]) for x in res if is_number(x[0])]
        BP_Max = [float(x[1]) for x in res if is_number(x[1])]
        if len(BP_Min)>0:
            BP_Min_Avg.append(float(sum(BP_Min))/len(BP_Min))
        else:
            BP_Min_Avg.append("nan")
        if len(BP_Max)>0:
            BP_Max_Avg.append(float(sum(BP_Max))/len(BP_Max))
        else:
            BP_Max_Avg.append("nan")
    return BP_Min_Avg, BP_Max_Avg


def generateOxygenChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsBO = []
    dbCursur.execute("""SELECT * FROM oxygenTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsBO += dbCursur.fetchall()

    BOTrackerData=[]

    for i in range(1, numberOfDays+1):
        BO = "nan"     # set to zero in order to avoid failing when adding value
        for item in monthsBO:
            if int(item[1].split("-")[2]) == i:
                BO = float(item[0])
        BOTrackerData.append(BO)
    return BOTrackerData


def generateWorkTrakcerChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur):
    monthsWorkHours = []
    dbCursur.execute("""SELECT * FROM workTracker WHERE date >= ? and date <= ?  """,
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
                pace_value = "nan"
                try:
                    if float(item[0])>0:
                       pace_value = float(item[0])
                except:
                    pace_value = "nan"
        paceTrackerData.append(pace_value)
    return paceTrackerData


def generate_weather_monthly(ha_directory: str, year):
    # extract the year data
    yearData = {}
    for room in os.listdir(ha_directory):
        if os.path.isdir(ha_directory+"/"+room):
            yearData[room] = yearData.get(room, {})
            for year_folder in os.listdir(ha_directory+"/"+room):
                if int(year_folder) == int(year):
                    for file in os.listdir(ha_directory+"/"+room+"/"+year_folder):
                        # f = open('homeAutomation/room_1/'+file, 'r')
                        f_month = int(file.replace(".txt", "").split("-")[1])
                        yearData[room][f_month] = yearData[room].get(f_month, {"time":[], "temp":[], "humidity":[], "pressure":[]})
                        f = open("homeAutomation/"+room+"/"+year_folder+"/"+file, 'r')
                        line2 = f.readline()
                        while (line2 != ""):
                            value = json.loads(line2)
                            yearData[room][f_month]["time"].append(value["time"])
                            yearData[room][f_month]["temp"].append(value["temp"])
                            yearData[room][f_month]["humidity"].append(value["humidity"])
                            yearData[room][f_month]["pressure"].append(float(value["pressure"])/1000.0)
                            line2 = f.readline()
                        f.close()
    # calculate min max for each month
    monthly_Data = {}
    for room in yearData:
        monthly_Data[room] = monthly_Data.get(room, {})
        for monthVal in range(1, 13):
            for item in ["temp", "humidity", "pressure"]:
                monthly_Data[room][item] = monthly_Data[room].get(item, {"min":[], "max":[]})
                if monthVal in yearData[room]:
                    monthly_Data[room][item]["min"].append(min(yearData[room][monthVal][item]))
                    monthly_Data[room][item]["max"].append(max(yearData[room][monthVal][item]))
                else:
                    monthly_Data[room][item]["min"].append("NaN")
                    monthly_Data[room][item]["max"].append("NaN")

    return monthly_Data


def genenrate_weather_daily(ha_directory:str, todaysDate):
    daily_data = {}
    for room in os.listdir(ha_directory):
        if os.path.isdir(ha_directory+"/"+room):
            daily_data[room] = daily_data.get(room, {"time": [], "temp":[], "humidity":[], "pressure": []})
            try:
                f = open("homeAutomation/"+room+"/"+todaysDate.split("-")[0]+"/"+todaysDate+'.txt', 'r')
                line2 = f.readline()
                while (line2 != ""):
                    value = json.loads(line2)
                    daily_data["room_1"]["time"].append(value["time"])
                    daily_data["room_1"]["temp"].append(value["temp"])
                    daily_data["room_1"]["humidity"].append(value["humidity"])
                    daily_data["room_1"]["pressure"].append(float(value["pressure"])/1000.0)
                    line2 = f.readline()
                f.close()
            except Exception as e:
                daily_data["room_1"] = {"time": [0], "temp":[0], "humidity":[0], "pressure": [0]}
                logger.error(e)
                try:
                    f.close()
                except:
                    pass
    return daily_data


def generate_cpu_stat(todaysDate, year):
    server_report_dir='serverScripts/reports/cpuReports/'+str(year)
    cpuTemps = []
    cpuTempsTimes = []

    cpuUsage = []
    cpuUsageTimes = []
    try:
        with open(server_report_dir+'/cpuUsageData_'+str(todaysDate)+'.txt', 'r') as reader2:
            line2 = reader2.readline()
            while (line2 != ""):
                lineSplit = line2.split(" ")
                cpuUsage.append(float(lineSplit[2]))
                cpuUsageTimes.append(lineSplit[0])
                line2 = reader2.readline()
        reader2.close()
    except Exception as e:
        logger.error(e)
        try:
            reader2.close()
        except:
            pass
    try:
        with open(server_report_dir+'/cpuTempData_'+str(todaysDate)+'.txt', 'r') as reader2:
            line2 = reader2.readline()
            while (line2 != ""):
                lineSplit = line2.split(" ")
                cpuTemps.append(float(lineSplit[0])/1000)
                cpuTempsTimes.append(lineSplit[2])
                line2 = reader2.readline()
        reader2.close()
    except Exception as e:
        logger.error(e)
        try:
            reader2.close()
        except:
            pass

    try:
        discSpace1 = int(os.popen('df -h | grep "/dev/root"').read().split()[4][:-1])
        discSpace2 = int(os.popen('df -h | grep "/dev/sda1"').read().split()[4][:-1])
        discSpace3Temp = os.popen('free -m | grep "Mem"').read().split()
        discSpace3 = (float(discSpace3Temp[2])/float(discSpace3Temp[1]))*100
        discSpace4Temp = os.popen('free -m | grep "Swap"').read().split()
        discSpace4 = (float(discSpace4Temp[2])/float(discSpace4Temp[1]))*100
        discSpace = {"/dev/root" : [discSpace1, 100-discSpace1],
                     "/dev/sda1": [discSpace2, 100-discSpace2],
                     "Mem": [discSpace3, 100-discSpace3],
                     "Swap": [discSpace4, 100-discSpace4]}
        upTimeString = " ".join(os.popen('uptime -s').read().split())
        bootTime = datetime.datetime.strptime(upTimeString, '%Y-%m-%d %H:%M:%S')
        upTime = datetime.datetime.now() - bootTime
        upTime = int(upTime.total_seconds()/3600)
    except:
            discSpace = {"/dev/root" : [0, 100], "/dev/sda1": [0, 100],
                         "Mem": [0, 100], "Swap": [0, 100]}
            upTime = 0

    return cpuTemps, cpuTempsTimes, cpuUsage, cpuUsageTimes, discSpace, upTime


def generate_cpu_stat_yearly(year: str):
    server_report_dir='serverScripts/reports/cpuReports/'+str(year)
    cpuTemps = {}
    cpuUsage = {}

    for file in os.listdir(server_report_dir):
        file_year = file.split(".")[0].split("-")[2]
        file_month = int(file.split(".")[0].split("-")[1])
        try:
            with open(server_report_dir+"/"+file, 'r') as reader2:
                line2 = reader2.readline()
                while (line2 != ""):
                    lineSplit = line2.strip().split(" ")
                    if "cpuUsageData" in file:
                        cpuUsage[file_month] = cpuUsage.get(file_month, [])
                        cpuUsage[file_month].append(float(lineSplit[2]))
                    else:
                        cpuTemps[file_month] = cpuTemps.get(file_month, [])
                        cpuTemps[file_month].append(float(lineSplit[0])/1000)
                    line2 = reader2.readline()
            reader2.close()
        except Exception as e:
            logger.error(file, e)
            logger.error("line:", line2)
            try:
                reader2.close()
            except:
                pass
    cpuUsageYearly={"min":[], "max":[]}
    cpuTempsYearly={"min":[], "max":[]}
    for i in range(1, 13):
        if i in cpuUsage:
            cpuUsageYearly["min"].append(min(cpuUsage[i]))
            cpuUsageYearly["max"].append(max(cpuUsage[i]))
        else:
            cpuUsageYearly["min"].append("nan")
            cpuUsageYearly["max"].append("nan")
        if i in cpuTemps:
            cpuTempsYearly["min"].append(min(cpuTemps[i]))
            cpuTempsYearly["max"].append(max(cpuTemps[i]))
        else:
            cpuTempsYearly["min"].append("nan")
            cpuTempsYearly["max"].append("nan")
    return cpuTempsYearly, cpuUsageYearly
