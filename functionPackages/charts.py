import datetime
from dateutil.relativedelta import relativedelta
from functionPackages.misc import getMonthsBeginning, getMonthsEnd, numberOfDaysInMonth, is_number
import os
import json
from package import temporary_data
import time
from flask import current_app as app
import logging
from functionPackages.dateTime import convertTimeTo24


logger = logging.getLogger(__name__)


def getTravelDests(dbCursur, lock):

    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM travelTracker""")
    travels = dbCursur.fetchall()
    lock.release()

    allTravels = []
    for item in travels:
        allTravels.append({'name': item[0], 'coords': [item[1], item[2]],})
    return allTravels


def generateWeightChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur, lock):
    lastMonthsBeginning = datetime.datetime.strptime(f"{pageYear}-{pageMonth}-01", '%Y-%m-%d')-relativedelta(months=+1)
    lastMonthsEnd = datetime.datetime.strptime(f"{pageYear}-{pageMonth}-01", '%Y-%m-%d')-datetime.timedelta(days=1)

    lastMonthsWeights = []
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM weightTracker WHERE date >= ? and date <= ?  """,
              (lastMonthsBeginning.date(), lastMonthsEnd.date(),))
    lastMonthsWeights += dbCursur.fetchall()
    lock.release()

    monthsWeights = []

    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM weightTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsWeights += dbCursur.fetchall()
    lock.release()

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


def hydrationFunc(res, yearHydration):
    yearHydration.append(sum([float(x[0]) for x in res if is_number(x[0])]))
    return yearHydration


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


def genYearChartData(pageYear: int, pageMonth: int, tableName: str, calcFunc, dbCursur, lock):
    startTime = time.time()
    retList = []
    global temporary_data
    temporary_data["chart_year_data"] = temporary_data.get("chart_year_data", {})
    temporary_data["chart_year_data"][tableName] = temporary_data["chart_year_data"].get(tableName, {pageYear: []})
    now = datetime.datetime.now()

    i = 0
    while (i+7<364):
        try:
            recorded_data = temporary_data["chart_year_data"][tableName][pageYear][(i/7)+1]
            if len(recorded_data) == 0:
                raise ValueError("re-calculate...")
            retList += recorded_data[len(retList): len(retList)+6]
        except Exception as err:
            weekBeg = datetime.datetime.strptime(f"{pageYear}-01-01", '%Y-%m-%d')+datetime.timedelta(days=i)
            weekEnd = datetime.datetime.strptime(f"{pageYear}-01-01", '%Y-%m-%d')+datetime.timedelta(days=i+6)
            lock.acquire(True)
            dbCursur.execute("SELECT * FROM " + tableName + " WHERE date >= ? and date <= ?  ",
                             (weekBeg.date(), weekEnd.date(),))
            retList = calcFunc(dbCursur.fetchall(), retList)
            lock.release()
        i += 7

    weekBeg = datetime.datetime.strptime(f"{pageYear}-01-01", '%Y-%m-%d')+datetime.timedelta(days=i)
    weekEnd = datetime.datetime.strptime(f"{pageYear}-01-01", '%Y-%m-%d')+datetime.timedelta(days=364)
    lock.acquire(True)
    dbCursur.execute("SELECT * FROM " + tableName + " WHERE date >= ? and date <= ?  ",
                     (weekEnd.date(), getMonthsEnd(i, pageYear).date(),))
    retList = calcFunc(dbCursur.fetchall(), retList)
    lock.release()
    temporary_data["chart_year_data"][tableName][pageYear] = retList[:]
    executionTime = (time.time() - startTime)
    logger.info('{0: <20}'.format(tableName)+ " time: " + str(executionTime))
    return retList


def generateHRChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur, lock):
    monthsHR = []

    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM HRTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsHR += dbCursur.fetchall()
    lock.release()

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



def generateBPChartData(pageMonth: int, pageYear: int, numberOfDays: int, dbCursur, lock):
    monthsBP = []

    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM BPTracker WHERE date >= ? and date <= ?  """,
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsBP += dbCursur.fetchall()
    lock.release()

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


def generateYearDoubleChartData(pageYear: int, numberOfDays: int, trackerName: str,  dbCursur, lock):
    startTime = time.time()
    TD_Min_Avg = [] # Table Data average Min
    TD_Max_Avg = [] # Table Data average Max
    i = 0
    while (i+7<364):
        weekBeg = datetime.datetime.strptime(f"{pageYear}-01-01", '%Y-%m-%d')+datetime.timedelta(days=i)
        weekEnd = datetime.datetime.strptime(f"{pageYear}-01-01", '%Y-%m-%d')+datetime.timedelta(days=i+6)
        lock.acquire(True)
        dbCursur.execute("SELECT * FROM "+trackerName+" WHERE date >= ? and date <= ?  ",
            (weekBeg.date(), weekEnd.date(),))
        res = dbCursur.fetchall()
        lock.release()

        TD_Min = [float(x[0]) for x in res if is_number(x[0])]
        TD_Max = [float(x[1]) for x in res if is_number(x[1])]
        if len(TD_Min)>0:
            TD_Min_Avg.append(float(sum(TD_Min))/len(TD_Min))
        else:
            TD_Min_Avg.append("nan")
        if len(TD_Max)>0:
            TD_Max_Avg.append(float(sum(TD_Max))/len(TD_Max))
        else:
            TD_Max_Avg.append("nan")
        i += 7

    weekBeg = datetime.datetime.strptime(f"{pageYear}-01-01", '%Y-%m-%d')+datetime.timedelta(days=i)
    weekEnd = datetime.datetime.strptime(f"{pageYear}-01-01", '%Y-%m-%d')+datetime.timedelta(days=364)
    lock.acquire(True)
    dbCursur.execute("SELECT * FROM "+trackerName+" WHERE date >= ? and date <= ?  ",
        (weekBeg.date(), weekEnd.date(),))
    res = dbCursur.fetchall()
    lock.release()

    TD_Min = [float(x[0]) for x in res if is_number(x[0])]
    TD_Max = [float(x[1]) for x in res if is_number(x[1])]
    if len(TD_Min)>0:
        TD_Min_Avg.append(float(sum(TD_Min))/len(TD_Min))
    else:
        TD_Min_Avg.append("nan")
    if len(TD_Max)>0:
        TD_Max_Avg.append(float(sum(TD_Max))/len(TD_Max))
    else:
        TD_Max_Avg.append("nan")

    executionTime = (time.time() - startTime)
    logger.info('{0: <20}'.format(trackerName)+ " time: " + str(executionTime))
    return TD_Min_Avg, TD_Max_Avg


def generateSavingTrackerChartData(pageYear: int, dbCursur, lock):
    yearsSavings = []
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM savingTracker WHERE month >= ? and month <= ?  """,
              (pageYear+"-"+"01", pageYear+"-"+"12"))
    yearsSavings += dbCursur.fetchall()
    lock.release()

    savingTrackerData=[]
    for i in range(1, 13):
        savingsVal = "nan"
        for item in yearsSavings:
            if int(item[1].split("-")[1]) == i:
                savingsVal = float(item[0])
        savingTrackerData.append(savingsVal)
    return savingTrackerData



def generateMortgageTrackerChartData(pageYear: int, dbCursur, lock):
    yearsSavings = []
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM mortgageTracker WHERE month >= ? and month <= ?  """,
              (pageYear+"-"+"01", pageYear+"-"+"12"))
    yearsSavings += dbCursur.fetchall()
    lock.release()

    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM mortgageTracker """)
    data = dbCursur.fetchall()
    try:
        maxVal = max([float(x[0]) for x in data])
        minVal = min([float(x[0]) for x in data])
        paid = maxVal - minVal
    except Exception as err:
        paid = 0
    lock.release()

    mortgageTrackerData=[]
    for i in range(1, 13):
        mortgageVal = "nan"
        for item in yearsSavings:
            if int(item[1].split("-")[1]) == i:
                mortgageVal = float(item[0])
        mortgageTrackerData.append(mortgageVal)

    return mortgageTrackerData, paid



def generateMonthlyChartData(pageMonth: int, pageYear: int, tabelName:str, numberOfDays: int, dbCursur, lock):
    monthsVals = []
    lock.acquire(True)
    dbCursur.execute("SELECT * FROM "+tabelName+" WHERE date >= ? and date <= ?  ",
              (getMonthsBeginning(pageMonth, pageYear).date(), getMonthsEnd(pageMonth, pageYear).date(),))
    monthsVals += dbCursur.fetchall()
    lock.release()

    monthsData=[]
    for i in range(1, numberOfDays+1):
        _value = "nan"
        for item in monthsVals:
            if int(item[1].split("-")[2]) == i:
                try:
                    _value = float(item[0])
                except:
                    _value = "nan"
        monthsData.append(_value)
    return monthsData


def generate_weather_monthly(dbCursur, year: int, lock):
    # extract the year data
    returnData = {}
    for month in range(1, 13):
        lock.acquire(True)
        dbCursur.execute("SELECT * FROM weatherStation WHERE date >= ? and date <= ?  ",
                (getMonthsBeginning(month, year).date(), getMonthsEnd(month, year).date(),))
        monthly_Data = dbCursur.fetchall()
        lock.release()
        tempData = {}
        for item in monthly_Data:
            room = int(item[0])
            tempData[room] = tempData.get(room, {"temp":[], "pressure":[], "humidity": []})
            tempData[room]["temp"].append(float(item[3].strip()))
            tempData[room]["humidity"].append(float(item[4].strip()))
            tempData[room]["pressure"].append(float(item[5].strip())/1000)

        for item in tempData.keys():
            room = item
            returnData[room] = returnData.get(room,{"months": [],
                                                    "temp":{"min": [], "max": [],"avg": []},
                                                    "pressure":{"min": [], "max": [],"avg": []},
                                                    "humidity":{"min": [], "max": [],"avg": []}})
            returnData[room]["months"].append(month)
            for parameter in ["temp", "pressure", "humidity"]:
                tempDataCleanList = [x for x in tempData[room][parameter] if x != 0]
                if len(tempDataCleanList)>0:
                    returnData[room][parameter]["min"].append(min(tempDataCleanList))
                    returnData[room][parameter]["max"].append(max(tempDataCleanList))
                    returnData[room][parameter]["avg"].append(sum(tempDataCleanList)/len(tempDataCleanList))
                else:
                    returnData[room][parameter]["min"].append("nan")
                    returnData[room][parameter]["max"].append("nan")
                    returnData[room][parameter]["avg"].append("nan")
    for month in range(1, 13):
        for room in returnData.keys():
            if month not in returnData[room]["months"]:
                for parameter in ["temp", "pressure", "humidity"]:
                    returnData[room][parameter]["min"] = returnData[room][parameter]["min"][:month-1] + ["nan"] + returnData[room][parameter]["min"][month-1:]
                    returnData[room][parameter]["max"] = returnData[room][parameter]["max"][:month-1] + ["nan"] + returnData[room][parameter]["max"][month-1:]
                    returnData[room][parameter]["avg"] = returnData[room][parameter]["avg"][:month-1] + ["nan"] + returnData[room][parameter]["avg"][month-1:]

    return returnData


def genenrate_weather_daily(dbCursur, todaysDate, lock):
    daily_data = {}
    lock.acquire(True)
    dbCursur.execute("SELECT * FROM weatherStation WHERE date = ? ", (todaysDate,))
    todayVals = dbCursur.fetchall()
    lock.release()
    for item in todayVals:
        room = int(item[0])
        daily_data[room] = daily_data.get(room, {"time": [], "temp":[], "pressure":[], "humidity": []})
        daily_data[room]["time"].append(item[2].strip()[:-3])
        daily_data[room]["temp"].append(item[3].strip())
        daily_data[room]["humidity"].append(item[4].strip())
        daily_data[room]["pressure"].append(float(item[5].strip())/1000)

    lock.acquire(True)
    dbCursur.execute("SELECT * FROM settings")
    res = dbCursur.fetchall()
    description = {}
    for item in res:
        description[str(item[0])] = item[1]
    for item in todayVals:
        room = str(item[0])
        if room not in description.keys():
            description[room] = "room_"+room
    lock.release()

    return daily_data, description


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
                # convert to 24hr format if its 12hr format
                if ("PM" in lineSplit) or ("AM" in lineSplit):
                    lineSplit[0] = convertTimeTo24(lineSplit[0]+" "+lineSplit[1])
                    del lineSplit[1]
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
    except:
        discSpace1 = 0

    try:
        discSpace2 = int(os.popen('df -h | grep "/dev/sda1"').read().split()[4][:-1])
    except:
        discSpace2 = 0

    try:
        discSpace3Temp = os.popen('free -m | grep "Mem"').read().split()
        discSpace3 = (float(discSpace3Temp[2])/float(discSpace3Temp[1]))*100
    except:
        discSpace3 = 0

    try:
        discSpace4Temp = os.popen('free -m | grep "Swap"').read().split()
        discSpace4 = (float(discSpace4Temp[2])/float(discSpace4Temp[1]))*100
    except:
        discSpace4 = 0

    try:
        upTimeString = " ".join(os.popen('uptime -s').read().split())
        bootTime = datetime.datetime.strptime(upTimeString, '%Y-%m-%d %H:%M:%S')
        upTime = datetime.datetime.now() - bootTime
        upTime = int(upTime.total_seconds()/3600)
    except Exception as e:
        upTime = 0

    discSpace = {"/dev/root" : [discSpace1, 100-discSpace1],
                 "/dev/sda1": [discSpace2, 100-discSpace2],
                 "Mem": [discSpace3, 100-discSpace3],
                 "Swap": [discSpace4, 100-discSpace4]}
    return cpuTemps, cpuTempsTimes, cpuUsage, cpuUsageTimes, discSpace, upTime


def generate_cpu_stat_monthly(year: str):
    server_report_dir='serverScripts/reports/cpuReports/'+str(year)
    cpuTemps = {}
    cpuUsage = {}

    now = datetime.datetime.now()
    temporary_data["yearly_cpu_usage"] = temporary_data.get("yearly_cpu_usage", {})
    temporary_data["yearly_cpu_temp"] = temporary_data.get("yearly_cpu_temp", {})
    temporary_data["yearly_cpu_usage"][year] = temporary_data["yearly_cpu_usage"].get(year, {"min":["nan" for _ in range(1, 13)], "max":["nan" for _ in range(1, 13)]})
    temporary_data["yearly_cpu_temp"][year] = temporary_data["yearly_cpu_temp"].get(year, {"min":["nan" for _ in range(1, 13)], "max":["nan" for _ in range(1, 13)]})

    file_month_counter_cpu=[0 for _ in range(1, 13)]
    file_month_counter_temp=[0 for _ in range(1, 13)]
    for file in os.listdir(server_report_dir):
        file_year = file.split(".")[0].split("-")[2]
        file_month = int(file.split(".")[0].split("-")[1])
        if file_year == str(year)[2:]:
            if(temporary_data["yearly_cpu_usage"][year]["min"][file_month-1]=="nan") or (int(file_month) == int(now.month)):
                try:
                    with open(server_report_dir+"/"+file, 'r') as reader2:
                        line2 = reader2.readline()
                        while (line2 != ""):
                            lineSplit = line2.strip().split(" ")
                            if "cpuUsageData" in file:
                                # convert to 24hr format if its 12hr format
                                if ("PM" in lineSplit) or ("AM" in lineSplit):
                                    lineSplit[0] = convertTimeTo24(lineSplit[0]+" "+lineSplit[1])
                                    del lineSplit[1]
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
    cpuUsageYearly={"min":["nan" for _ in range(1, 13)], "max":["nan" for _ in range(1, 13)]}
    cpuTempsYearly={"min":["nan" for _ in range(1, 13)], "max":["nan" for _ in range(1, 13)]}
    for i in range(1, 13):
        if(temporary_data["yearly_cpu_usage"][year]["min"][i-1]=="nan") or (i == now.month):
            if i in cpuUsage:
                temporary_data["yearly_cpu_usage"][year]["min"][i-1] = min(cpuUsage[i])
                temporary_data["yearly_cpu_usage"][year]["max"][i-1] = max(cpuUsage[i])
            if i in cpuTemps:
                temporary_data["yearly_cpu_temp"][year]["min"][i-1] = min(cpuTemps[i])
                temporary_data["yearly_cpu_temp"][year]["max"][i-1] = max(cpuTemps[i])
    cpuUsageYearly["min"] = temporary_data["yearly_cpu_usage"][year]["min"][:]
    cpuUsageYearly["max"] = temporary_data["yearly_cpu_usage"][year]["max"][:]
    cpuTempsYearly["min"] = temporary_data["yearly_cpu_temp"][year]["min"][:]
    cpuTempsYearly["max"] = temporary_data["yearly_cpu_temp"][year]["max"][:]
    return cpuTempsYearly, cpuUsageYearly



def generateEConsumptionTrackerChartData(pageYear: str, dbCursur, lock):
    yearsConsumption = []
    lock.acquire(True)
    dbCursur.execute("""SELECT * FROM econsumption WHERE date >= ? and date <= ?  """,
              (pageYear+"-"+"01"+"-"+"01", pageYear+"-"+"12"+"-"+"30"))
    yearsConsumption += dbCursur.fetchall()
    lock.release()

    ConsumptionTrackerData=[]
    for i in range(1, 13):
        ConsumptionVal = "nan"
        for item in yearsConsumption:
            if int(item[0].split("-")[1]) == i:
                ConsumptionVal = float(item[1])
        ConsumptionTrackerData.append(ConsumptionVal)
    return ConsumptionTrackerData



def getChartData(pageMonth, pageYear, numberOfDays, c, lock):
    # gather chart information ----------------------
    ChartData = {}
    ChartData["monthsWeights"]    = generateWeightChartData(int(pageMonth),      int(pageYear), numberOfDays, c, lock)
    ChartData["monthsPaces"]      = generateMonthlyChartData(int(pageMonth), int(pageYear), "paceTracker", numberOfDays, c, lock)
    ChartData["BO"]               = generateMonthlyChartData(int(pageMonth), int(pageYear), "oxygenTracker", numberOfDays, c, lock)
    ChartData["monthsWorkHours"]  = generateMonthlyChartData(int(pageMonth), int(pageYear), "workTracker", numberOfDays, c, lock)
    ChartData["monthsSleepTimes"] = generateMonthlyChartData(int(pageMonth), int(pageYear), "sleepTracker", numberOfDays, c, lock)
    ChartData["monthsSteps"]      = generateMonthlyChartData(int(pageMonth), int(pageYear), "stepTracker", numberOfDays, c, lock)
    ChartData["monthsHydration"]  = generateMonthlyChartData(int(pageMonth), int(pageYear), "hydrationTracker", numberOfDays, c, lock)
    ChartData["monthsRuns"]       = generateMonthlyChartData(int(pageMonth), int(pageYear), "runningTracker",numberOfDays, c, lock)
    ChartData["YearsSavings"]     = generateSavingTrackerChartData(pageYear, c, lock)
    ChartData["YearsMortgages"], ChartData["MortgagePaid"]   = generateMortgageTrackerChartData(pageYear, c, lock)
    ChartData["ChartMonthDays"]   = [str(i) for i in range(1, numberOfDays+1)]
    ChartData["travels"]          = getTravelDests(c, lock)
    ChartData["HR_Min"], ChartData["HR_Max"] = generateHRChartData(int(pageMonth),          int(pageYear), numberOfDays, c, lock)
    ChartData["BP_Min"], ChartData["BP_Max"] = generateBPChartData(int(pageMonth),          int(pageYear), numberOfDays, c, lock)
    # ----------------------------------------------
    ChartData["yearRuns"]   = genYearChartData(int(pageYear), int(pageMonth), "runningTracker",  runFunc,    c, lock)
    ChartData["yearSteps"]  = genYearChartData(int(pageYear), int(pageMonth), "stepTracker",     stepFunc,   c, lock)
    ChartData["yearSleep"]  = genYearChartData(int(pageYear), int(pageMonth), "sleepTracker",    sleepFunc,  c, lock)
    ChartData["yearHydr"]   = genYearChartData(int(pageYear), int(pageMonth), "hydrationTracker",hydrationFunc,  c, lock)
    ChartData["yearWeight"] = genYearChartData(int(pageYear), int(pageMonth), "weightTracker",   weightFunc, c, lock)
    ChartData["yearBO"]     = genYearChartData(int(pageYear), int(pageMonth), "oxygenTracker",   BOFunc,     c, lock)
    ChartData["yearWH"]     = genYearChartData(int(pageYear), int(pageMonth), "workTracker",     WHFunc,     c, lock)
    ChartData["yearMood"]   = genYearChartData(int(pageYear), int(pageMonth), "moodTracker",     moodFunc,   c, lock)
    ChartData["yearHR_Min"], ChartData["yearHR_Max"] = generateYearDoubleChartData(int(pageYear), numberOfDays, "HRTracker",  c, lock)
    ChartData["yearBP_Min"], ChartData["yearBP_Max"] = generateYearDoubleChartData(int(pageYear), numberOfDays, "BPTracker",  c, lock)

    return ChartData
