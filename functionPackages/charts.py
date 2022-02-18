import datetime
from dateutil.relativedelta import relativedelta
from functionPackages.misc import get_months_beginning, get_months_end, is_number
import os
import time
import logging
from functionPackages.dateTime import convert_time_to24


logger = logging.getLogger(__name__)
temporary_data = {}


def get_travel_destinations(db_cursor, lock):

    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM travelTracker""")
    travels = db_cursor.fetchall()
    lock.release()

    all_travels = []
    for item in travels:
        all_travels.append({'name': item[0], 'coords': [item[1], item[2]], })
    return all_travels


def generate_weight_chart_data(page_month: int, page_year: int, number_of_days: int, db_cursor, lock):
    last_months_beginning = datetime.datetime.strptime(f"{page_year}-{page_month}-01", '%Y-%m-%d') - \
                            relativedelta(months=+1)
    last_months_end = datetime.datetime.strptime(f"{page_year}-{page_month}-01", '%Y-%m-%d') - \
                      datetime.timedelta(days=1)

    last_months_weights = []
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM weightTracker WHERE date >= ? and date <= ?  """,
                      (last_months_beginning.date(), last_months_end.date(),))
    last_months_weights += db_cursor.fetchall()
    lock.release()

    months_weights = []

    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM weightTracker WHERE date >= ? and date <= ?  """,
                      (get_months_beginning(page_month, page_year).date(),
                       get_months_end(page_month, page_year).date(),))
    months_weights += db_cursor.fetchall()
    lock.release()

    start_weight = "nan"
    if len(last_months_weights) > 0:
        start_weight = float(sorted(last_months_weights, key=lambda x: int(x[1].split("-")[2]))[0][0])
    else:
        if len(months_weights) > 0:
            start_weight = float(sorted(months_weights, key=lambda x: int(x[1].split("-")[2]))[0][0])

    chart_weights = []
    for i in range(1, number_of_days + 1):
        current_month = int(str(datetime.date.today()).split("-")[1])
        weight = "nan"
        for item in months_weights:
            if int(item[1].split("-")[2]) == i:
                weight = float(item[0])
        # fix the beginning of the month by extending the first value to beginning
        if (i == 1) and (weight == 'nan'):
            weight = start_weight
        # fix the end of the month by extending the last value to the end...
        # do not do it for current month
        if (i == number_of_days) and (weight == 'nan') and current_month != page_month:
            recorded_days = [x for x in chart_weights if (x != 'nan')]
            if len(recorded_days) > 0:
                weight = recorded_days[-1]
        chart_weights.append(weight)
    return chart_weights


def weight_func(res, weight):
    weight_list = [float(x[0]) for x in res if is_number(x[0])]
    if len(weight_list) > 0:
        weight.append(float(sum(weight_list))/len(weight_list))
    else:
        weight.append("nan")
    return weight


def bo_func(res, bo):
    bo_list = [float(x[0]) for x in res if is_number(x[0])]
    if len(bo_list) > 0:
        bo.append(float(sum(bo_list)) / len(bo_list))
    else:
        bo.append("nan")
    return bo


def wh_func(res, year_wh):
    year_wh.append(sum([float(x[0]) for x in res if is_number(x[0])]))
    return year_wh


def sleep_func(res, year_sleep):
    year_sleep.append(sum([float(x[0]) for x in res if is_number(x[0])]))
    return year_sleep


def step_func(res, year_step):
    year_step.append(sum([float(x[0]) for x in res if is_number(x[0])]))
    return year_step


def hydration_func(res, year_hydration):
    year_hydration.append(sum([float(x[0]) for x in res if is_number(x[0])]))
    return year_hydration


def mood_func(res, year_moods):
    res = [x[0] for x in res]
    month_val = res.count("great")*4.5 + res.count("good")*3.5 + res.count("ok")*2.5 + res.count("bad")*1.5 + \
                res.count("awful")*0.5
    if len(res) > 0:
        mood_val = month_val/float(len(res))
        year_moods.append(mood_val)
    else:
        year_moods.append("nan")
    return year_moods


def run_func(res, year_runs):
    year_runs.append(sum([float(x[0]) for x in res if is_number(x[0])]))
    return year_runs


def gen_year_chart_data(page_year: int, table_name: str, calc_func, db_cursor, lock):
    start_time = time.time()
    ret_list = []
    global temporary_data
    temporary_data["chart_year_data"] = temporary_data.get("chart_year_data", {})
    temporary_data["chart_year_data"][table_name] = temporary_data["chart_year_data"].get(table_name, {page_year: []})
    i = 0
    while (i+7) < 364:
        try:
            recorded_data = temporary_data["chart_year_data"][table_name][page_year][(i / 7) + 1]
            if len(recorded_data) == 0:
                raise ValueError("re-calculate...")
            ret_list += recorded_data[len(ret_list): len(ret_list)+6]
        except Exception as err:
            logger.error(err)
            week_beg = datetime.datetime.strptime(f"{page_year}-01-01", '%Y-%m-%d') + datetime.timedelta(days=i)
            week_end = datetime.datetime.strptime(f"{page_year}-01-01", '%Y-%m-%d') + datetime.timedelta(days=i + 6)
            lock.acquire(True)
            db_cursor.execute("SELECT * FROM " + table_name + " WHERE date >= ? and date <= ?  ",
                              (week_beg.date(), week_end.date(),))
            ret_list = calc_func(db_cursor.fetchall(), ret_list)
            lock.release()
        i += 7

    week_end = datetime.datetime.strptime(f"{page_year}-01-01", '%Y-%m-%d') + datetime.timedelta(days=364)
    lock.acquire(True)
    db_cursor.execute("SELECT * FROM " + table_name + " WHERE date >= ? and date <= ?  ",
                      (week_end.date(), get_months_end(i, page_year).date(),))
    ret_list = calc_func(db_cursor.fetchall(), ret_list)
    lock.release()
    temporary_data["chart_year_data"][table_name][page_year] = ret_list[:]
    execution_time = (time.time() - start_time)
    logger.info('{0: <20}'.format(table_name) + " time: " + str(execution_time))
    return ret_list


def generate_hr_chart_data(page_month: int, page_year: int, number_of_days: int, db_cursor, lock):
    months_hr = []

    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM HRTracker WHERE date >= ? and date <= ?  """,
                      (get_months_beginning(page_month, page_year).date(),
                       get_months_end(page_month, page_year).date(),))
    months_hr += db_cursor.fetchall()
    lock.release()

    chart_hr_min = []
    chart_hr_max = []
    for i in range(1, number_of_days + 1):
        hr_min = "nan"
        hr_max = "nan"
        for item in months_hr:
            if int(item[2].split("-")[2]) == i:
                hr_min, hr_max = float(item[0]), float(item[1])
        chart_hr_min.append(hr_min)
        chart_hr_max.append(hr_max)
    return chart_hr_min, chart_hr_max


def generate_bp_chart_data(page_month: int, page_year: int, number_of_days: int, db_cursor, lock):
    months_bp = []

    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM BPTracker WHERE date >= ? and date <= ?  """,
                      (get_months_beginning(page_month, page_year).date(),
                       get_months_end(page_month, page_year).date(),))
    months_bp += db_cursor.fetchall()
    lock.release()

    chart_bp_min = []
    chart_bp_max = []
    for i in range(1, number_of_days + 1):
        bp_min = "nan"
        bp_max = "nan"
        for item in months_bp:
            if int(item[2].split("-")[2]) == i:
                bp_min, bp_max = float(item[0]), float(item[1])
        chart_bp_min.append(bp_min)
        chart_bp_max.append(bp_max)
    return chart_bp_min, chart_bp_max


def generate_year_double_chart_data(page_year: int, tracker_name: str, db_cursor, lock):
    start_time = time.time()
    td_min_avg = []     # Table Data average Min
    td_max_avg = []     # Table Data average Max
    i = 0
    while (i+7) < 364:
        week_beg = datetime.datetime.strptime(f"{page_year}-01-01", '%Y-%m-%d') + datetime.timedelta(days=i)
        week_end = datetime.datetime.strptime(f"{page_year}-01-01", '%Y-%m-%d') + datetime.timedelta(days=i + 6)
        lock.acquire(True)
        db_cursor.execute("SELECT * FROM " + tracker_name + " WHERE date >= ? and date <= ?  ",
                          (week_beg.date(), week_end.date(),))
        res = db_cursor.fetchall()
        lock.release()

        td_min = [float(x[0]) for x in res if is_number(x[0])]
        td_max = [float(x[1]) for x in res if is_number(x[1])]
        if len(td_min) > 0:
            td_min_avg.append(float(sum(td_min))/len(td_min))
        else:
            td_min_avg.append("nan")
        if len(td_max) > 0:
            td_max_avg.append(float(sum(td_max))/len(td_max))
        else:
            td_max_avg.append("nan")
        i += 7

    week_beg = datetime.datetime.strptime(f"{page_year}-01-01", '%Y-%m-%d') + datetime.timedelta(days=i)
    week_end = datetime.datetime.strptime(f"{page_year}-01-01", '%Y-%m-%d') + datetime.timedelta(days=364)
    lock.acquire(True)
    db_cursor.execute("SELECT * FROM " + tracker_name + " WHERE date >= ? and date <= ?  ",
                      (week_beg.date(), week_end.date(),))
    res = db_cursor.fetchall()
    lock.release()

    td_min = [float(x[0]) for x in res if is_number(x[0])]
    td_max = [float(x[1]) for x in res if is_number(x[1])]
    if len(td_min) > 0:
        td_min_avg.append(float(sum(td_min))/len(td_min))
    else:
        td_min_avg.append("nan")
    if len(td_max) > 0:
        td_max_avg.append(float(sum(td_max))/len(td_max))
    else:
        td_max_avg.append("nan")

    execution_time = (time.time() - start_time)
    logger.info('{0: <20}'.format(tracker_name) + " time: " + str(execution_time))
    return td_min_avg, td_max_avg


def generate_saving_tracker_chart_data(page_year: int, db_cursor, lock):
    years_savings = []
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM savingTracker WHERE month >= ? and month <= ?  """,
                      (str(page_year) + "-" + "01", str(page_year) + "-" + "12"))
    years_savings += db_cursor.fetchall()
    lock.release()

    saving_tracker_data = []
    for i in range(1, 13):
        savings_val = "nan"
        for item in years_savings:
            if int(item[1].split("-")[1]) == i:
                savings_val = float(item[0])
        saving_tracker_data.append(savings_val)
    return saving_tracker_data


def generate_mortgage_tracker_chart_data(page_year: int, db_cursor, lock):
    years_savings = []
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM mortgageTracker WHERE month >= ? and month <= ?  """,
                      (str(page_year) + "-" + "01", str(page_year) + "-" + "12"))
    years_savings += db_cursor.fetchall()
    lock.release()

    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM mortgageTracker """)
    data = db_cursor.fetchall()
    try:
        max_val = max([float(x[0]) for x in data])
        min_val = min([float(x[0]) for x in data])
        paid = max_val - min_val
    except Exception as err:
        logger.error(err)
        paid = 0
    lock.release()

    mortgage_tracker_data = []
    for i in range(1, 13):
        mortgage_val = "nan"
        for item in years_savings:
            if int(item[1].split("-")[1]) == i:
                mortgage_val = float(item[0])
        mortgage_tracker_data.append(mortgage_val)

    return mortgage_tracker_data, paid


def generate_monthly_chart_data(page_month: int, page_year: int, tabel_name: str, number_of_days: int, db_cursor, lock):
    months_vals = []
    lock.acquire(True)
    db_cursor.execute("SELECT * FROM " + tabel_name + " WHERE date >= ? and date <= ?  ",
                      (get_months_beginning(page_month, page_year).date(),
                       get_months_end(page_month, page_year).date(),))
    months_vals += db_cursor.fetchall()
    lock.release()

    months_data = []
    for i in range(1, number_of_days + 1):
        _value = "nan"
        for item in months_vals:
            if int(item[1].split("-")[2]) == i:
                try:
                    _value = float(item[0])
                except Exception as err:
                    logger.error(err)
                    _value = "nan"
        months_data.append(_value)
    return months_data


def generate_weather_monthly(db_cursor, year: int, lock):
    # extract the year data
    return_data = {}
    for month in range(1, 13):
        lock.acquire(True)
        db_cursor.execute("SELECT * FROM weatherStation WHERE date >= ? and date <= ?  ",
                          (get_months_beginning(month, year).date(), get_months_end(month, year).date(),))
        monthly_data = db_cursor.fetchall()
        lock.release()
        temp_data = {}
        for item in monthly_data:
            room = int(item[0])
            temp_data[room] = temp_data.get(room, {"temp": [], "pressure": [], "humidity": []})
            temp_data[room]["temp"].append(float(item[3].strip()))
            temp_data[room]["humidity"].append(float(item[4].strip()))
            temp_data[room]["pressure"].append(float(item[5].strip())/1000)

        for item in temp_data.keys():
            room = item
            return_data[room] = return_data.get(room, {"months": [],
                                                       "temp": {"min": [], "max": [], "avg": []},
                                                       "pressure": {"min": [], "max": [], "avg": []},
                                                       "humidity": {"min": [], "max": [], "avg": []}})
            return_data[room]["months"].append(month)
            for parameter in ["temp", "pressure", "humidity"]:
                temp_data_clean_list = [x for x in temp_data[room][parameter] if x != 0]
                if len(temp_data_clean_list) > 0:
                    return_data[room][parameter]["min"].append(min(temp_data_clean_list))
                    return_data[room][parameter]["max"].append(max(temp_data_clean_list))
                    return_data[room][parameter]["avg"].append(sum(temp_data_clean_list)/len(temp_data_clean_list))
                else:
                    return_data[room][parameter]["min"].append("nan")
                    return_data[room][parameter]["max"].append("nan")
                    return_data[room][parameter]["avg"].append("nan")
    for month in range(1, 13):
        for room in return_data.keys():
            if month not in return_data[room]["months"]:
                for parameter in ["temp", "pressure", "humidity"]:
                    return_data[room][parameter]["min"] = return_data[room][parameter]["min"][:month-1] + ["nan"] + \
                                                          return_data[room][parameter]["min"][month-1:]
                    return_data[room][parameter]["max"] = return_data[room][parameter]["max"][:month-1] + ["nan"] + \
                                                          return_data[room][parameter]["max"][month-1:]
                    return_data[room][parameter]["avg"] = return_data[room][parameter]["avg"][:month-1] + ["nan"] + \
                                                          return_data[room][parameter]["avg"][month-1:]

    return return_data


def generate_weather_daily(db_cursor, today_date, lock):
    daily_data = {}
    lock.acquire(True)
    db_cursor.execute("SELECT * FROM weatherStation WHERE date = ? ", (today_date,))
    today_vals = db_cursor.fetchall()
    lock.release()
    for item in today_vals:
        room = int(item[0])
        daily_data[room] = daily_data.get(room, {"time": [], "temp": [], "pressure": [], "humidity": []})
        daily_data[room]["time"].append(item[2].strip()[:-3])
        daily_data[room]["temp"].append(item[3].strip())
        daily_data[room]["humidity"].append(item[4].strip())
        daily_data[room]["pressure"].append(float(item[5].strip())/1000)

    lock.acquire(True)
    db_cursor.execute("SELECT * FROM settings")
    res = db_cursor.fetchall()
    description = {}
    for item in res:
        description[str(item[0])] = item[1]
    for item in today_vals:
        room = str(item[0])
        if room not in description.keys():
            description[room] = "room_"+room
    lock.release()

    return daily_data, description


def generate_cpu_stat(today_date, year):
    server_report_dir = 'serverScripts/reports/cpuReports/'+str(year)
    cpu_temps = []
    cpu_temps_times = []

    cpu_usage = []
    cpu_usage_times = []
    try:
        with open(server_report_dir + '/cpuUsageData_' + str(today_date) + '.txt', 'r') as reader2:
            line2 = reader2.readline()
            while line2 != "":
                line_split = line2.split(" ")
                # convert to 24hr format if its 12hr format
                if ("PM" in line_split) or ("AM" in line_split):
                    line_split[0] = convert_time_to24(line_split[0] + " " + line_split[1])
                    del line_split[1]
                cpu_usage.append(float(line_split[2]))
                cpu_usage_times.append(line_split[0])
                line2 = reader2.readline()
        reader2.close()
    except Exception as e:
        logger.error(e)
        try:
            reader2.close()
        except Exception as err:
            logger.error(err)
            pass
    try:
        with open(server_report_dir + '/cpuTempData_' + str(today_date) + '.txt', 'r') as reader2:
            line2 = reader2.readline()
            while line2 != "":
                line_split = line2.split(" ")
                cpu_temps.append(float(line_split[0])/1000)
                cpu_temps_times.append(line_split[2])
                line2 = reader2.readline()
        reader2.close()
    except Exception as e:
        logger.error(e)
        try:
            reader2.close()
        except Exception as err:
            logger.error(err)
    try:
        disc_space1 = int(os.popen('df -h | grep "/dev/root"').read().split()[4][:-1])
    except Exception as err:
        logger.error(err)
        disc_space1 = 0

    try:
        disc_space2 = int(os.popen('df -h | grep "/dev/sda1"').read().split()[4][:-1])
    except Exception as err:
        logger.error(err)
        disc_space2 = 0

    try:
        disc_space3_temp = os.popen('free -m | grep "Mem"').read().split()
        disc_space3 = (float(disc_space3_temp[2])/float(disc_space3_temp[1]))*100
    except Exception as err:
        logger.error(err)
        disc_space3 = 0

    try:
        disc_space4_temp = os.popen('free -m | grep "Swap"').read().split()
        disc_space4 = (float(disc_space4_temp[2])/float(disc_space4_temp[1]))*100
    except Exception as err:
        logger.error(err)
        disc_space4 = 0

    try:
        up_time_string = " ".join(os.popen('uptime -s').read().split())
        boot_time = datetime.datetime.strptime(up_time_string, '%Y-%m-%d %H:%M:%S')
        up_time = datetime.datetime.now() - boot_time
        up_time = int(up_time.total_seconds()/3600)
    except Exception as err:
        logger.error(err)
        up_time = 0

    disc_space = {"/dev/root": [disc_space1, 100-disc_space1],
                  "/dev/sda1": [disc_space2, 100-disc_space2],
                  "Mem": [disc_space3, 100-disc_space3],
                  "Swap": [disc_space4, 100-disc_space4]}
    return cpu_temps, cpu_temps_times, cpu_usage, cpu_usage_times, disc_space, up_time


def generate_cpu_stat_monthly(year: str):
    server_report_dir = 'serverScripts/reports/cpuReports/'+str(year)
    cpu_temps = {}
    cpu_usage = {}

    now = datetime.datetime.now()
    temporary_data["yearly_cpu_usage"] = temporary_data.get("yearly_cpu_usage", {})
    temporary_data["yearly_cpu_temp"] = temporary_data.get("yearly_cpu_temp", {})
    temporary_data["yearly_cpu_usage"][year] = temporary_data["yearly_cpu_usage"].get(year, {"min": ["nan" for _ in range(1, 13)], "max": ["nan" for _ in range(1, 13)]})
    temporary_data["yearly_cpu_temp"][year] = temporary_data["yearly_cpu_temp"].get(year, {"min": ["nan" for _ in range(1, 13)], "max": ["nan" for _ in range(1, 13)]})

    for file in os.listdir(server_report_dir):
        file_year = file.split(".")[0].split("-")[2]
        file_month = int(file.split(".")[0].split("-")[1])
        if file_year == str(year)[2:]:
            if(temporary_data["yearly_cpu_usage"][year]["min"][file_month-1] == "nan") or \
                    (int(file_month) == int(now.month)):
                try:
                    with open(server_report_dir+"/"+file, 'r') as reader2:
                        line2 = reader2.readline()
                        while line2 != "":
                            line_split = line2.strip().split(" ")
                            if "cpuUsageData" in file:
                                # convert to 24hr format if its 12hr format
                                if ("PM" in line_split) or ("AM" in line_split):
                                    line_split[0] = convert_time_to24(line_split[0] + " " + line_split[1])
                                    del line_split[1]
                                cpu_usage[file_month] = cpu_usage.get(file_month, [])
                                cpu_usage[file_month].append(float(line_split[2]))
                            else:
                                cpu_temps[file_month] = cpu_temps.get(file_month, [])
                                cpu_temps[file_month].append(float(line_split[0])/1000)
                            line2 = reader2.readline()
                    reader2.close()
                except Exception as e:
                    logger.error(file, e)
                    logger.error("line:", line2)
                    try:
                        reader2.close()
                    except Exception as err:
                        logger.error(err)
    cpu_usage_yearly = {"min": ["nan" for _ in range(1, 13)], "max": ["nan" for _ in range(1, 13)]}
    cpu_temps_yearly = {"min": ["nan" for _ in range(1, 13)], "max": ["nan" for _ in range(1, 13)]}
    for i in range(1, 13):
        if(temporary_data["yearly_cpu_usage"][year]["min"][i-1] == "nan") or (i == now.month):
            if i in cpu_usage:
                temporary_data["yearly_cpu_usage"][year]["min"][i-1] = min(cpu_usage[i])
                temporary_data["yearly_cpu_usage"][year]["max"][i-1] = max(cpu_usage[i])
            if i in cpu_temps:
                temporary_data["yearly_cpu_temp"][year]["min"][i-1] = min(cpu_temps[i])
                temporary_data["yearly_cpu_temp"][year]["max"][i-1] = max(cpu_temps[i])
    cpu_usage_yearly["min"] = temporary_data["yearly_cpu_usage"][year]["min"][:]
    cpu_usage_yearly["max"] = temporary_data["yearly_cpu_usage"][year]["max"][:]
    cpu_temps_yearly["min"] = temporary_data["yearly_cpu_temp"][year]["min"][:]
    cpu_temps_yearly["max"] = temporary_data["yearly_cpu_temp"][year]["max"][:]
    return cpu_temps_yearly, cpu_usage_yearly


def generate_e_consumption_tracker_chart_data(page_year: str, db_cursor, lock):
    years_consumption = []
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM econsumption WHERE date >= ? and date <= ?  """,
                      (page_year + "-" + "01" + "-" + "01", page_year + "-" + "12" + "-" + "30"))
    years_consumption += db_cursor.fetchall()
    lock.release()

    consumption_tracker_data = []
    for i in range(1, 13):
        consumption_val = "nan"
        for item in years_consumption:
            if int(item[0].split("-")[1]) == i:
                consumption_val = float(item[1])
        consumption_tracker_data.append(consumption_val)
    return consumption_tracker_data


def get_chart_data(page_month, page_year, number_of_days, c, lock):
    # gather chart information ----------------------
    chart_data = dict()
    chart_data["monthsWeights"] = \
        generate_weight_chart_data(int(page_month), int(page_year), number_of_days, c, lock)
    chart_data["monthsPaces"] = \
        generate_monthly_chart_data(int(page_month), int(page_year), "paceTracker", number_of_days, c, lock)
    chart_data["BO"] = \
        generate_monthly_chart_data(int(page_month), int(page_year), "oxygenTracker", number_of_days, c, lock)
    chart_data["monthsWorkHours"] = \
        generate_monthly_chart_data(int(page_month), int(page_year), "workTracker", number_of_days, c, lock)
    chart_data["monthsSleepTimes"] = \
        generate_monthly_chart_data(int(page_month), int(page_year), "sleepTracker", number_of_days, c, lock)
    chart_data["monthsSteps"] = \
        generate_monthly_chart_data(int(page_month), int(page_year), "stepTracker", number_of_days, c, lock)
    chart_data["monthsHydration"] = \
        generate_monthly_chart_data(int(page_month), int(page_year), "hydrationTracker", number_of_days, c, lock)
    chart_data["monthsRuns"] = \
        generate_monthly_chart_data(int(page_month), int(page_year), "runningTracker", number_of_days, c, lock)
    chart_data["YearsSavings"] = generate_saving_tracker_chart_data(page_year, c, lock)
    chart_data["YearsMortgages"], chart_data["MortgagePaid"] = generate_mortgage_tracker_chart_data(page_year, c, lock)
    chart_data["ChartMonthDays"] = [str(i) for i in range(1, number_of_days + 1)]
    chart_data["travels"] = get_travel_destinations(c, lock)
    chart_data["HR_Min"], chart_data["HR_Max"] = \
        generate_hr_chart_data(int(page_month), int(page_year), number_of_days, c, lock)
    chart_data["BP_Min"], chart_data["BP_Max"] = \
        generate_bp_chart_data(int(page_month), int(page_year), number_of_days, c, lock)
    # ----------------------------------------------
    chart_data["yearRuns"] = gen_year_chart_data(int(page_year), "runningTracker", run_func, c, lock)
    chart_data["yearSteps"] = gen_year_chart_data(int(page_year), "stepTracker", step_func, c, lock)
    chart_data["yearSleep"] = gen_year_chart_data(int(page_year), "sleepTracker", sleep_func, c, lock)
    chart_data["yearHydr"] = gen_year_chart_data(int(page_year), "hydrationTracker", hydration_func, c, lock)
    chart_data["yearWeight"] = gen_year_chart_data(int(page_year), "weightTracker", weight_func, c, lock)
    chart_data["yearBO"] = gen_year_chart_data(int(page_year), "oxygenTracker", bo_func, c, lock)
    chart_data["yearWH"] = gen_year_chart_data(int(page_year), "workTracker", wh_func, c, lock)
    chart_data["yearMood"] = gen_year_chart_data(int(page_year), "moodTracker", mood_func, c, lock)
    chart_data["yearHR_Min"], chart_data["yearHR_Max"] = \
        generate_year_double_chart_data(int(page_year), "HRTracker", c, lock)
    chart_data["yearBP_Min"], chart_data["yearBP_Max"] = \
        generate_year_double_chart_data(int(page_year), "BPTracker", c, lock)

    return chart_data
