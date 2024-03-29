from flask_restful import Resource
from flask import render_template, make_response, request
from functionPackages.misc import *
from package import days_of_the_week


class Org(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conn = kwargs["conn"]
        self.c = kwargs["c"]
        self.lock = kwargs["lock"]
        self.parser = kwargs["parser"]
        self.logger = logging.getLogger(__name__)

    def get(self):
        headers = {'Content-Type': 'text/html'}
        page_theme = fetch_setting_param_from_db(self.c, "Theme", self.lock)
        if not session.get("name"):
            return make_response(render_template('login.html', pageTheme=page_theme), 200, headers)
        start_time = time.time()
        args = self.parser.parse_args()
        today_date = parse_date(args['date'])
        day, month, year = separate_day_month_year(today_date)
        months_beginning = get_months_beginning(month, year)
        week_day = datetime.datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d').weekday()
        number_of_days = number_of_days_in_month(int(month), int(year))
        months_beginning_week_day = months_beginning.weekday()

        all_due_events, this_months_events, today_todos = get_todos(today_date, self.c, self.lock)
        scrum_board_lists, chart_done_tasks, chart_month_days, chart_this_month_tasks = \
            get_scrum_tasks(today_date, self.c, self.lock)

        cal_date = get_cal_events_week(today_date, self.c, self.lock)
        cal_month = get_cal_events_month(today_date, self.c, self.lock)

        vacations = get_all_vacations(today_date, self.c, self.lock)
        this_year_vacations, vacations_from_last_year = get_number_of_vacation_days(today_date, self.c, self.lock)
        # ---------------------------
        header_dates = []
        day_val = datetime.datetime.strptime(today_date, '%Y-%m-%d') - datetime.timedelta(days=week_day)  # week's start
        for i in range(1, 8):
            header_dates.append(str(day_val.date()).split("-")[2])
            day_val = datetime.datetime.strptime(str(day_val.date()), '%Y-%m-%d') + datetime.timedelta(days=1)
        self.logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        calendars = fetch_setting_param_from_db(self.c, "calendars", self.lock).replace(" ", "").split(",")
        return make_response(
            render_template('org.html', day=day, month=month, year=year, weekDay=days_of_the_week[week_day],
                            monthsBeginning=months_beginning_week_day, todayTodos=today_todos, overDue=all_due_events,
                            numberOfDays=number_of_days, thisMonthsEvents=this_months_events, calDate=cal_date,
                            calMonth=cal_month, headerDates=header_dates, vacations=vacations, calendars=calendars,
                            vacationsFromLastYear=vacations_from_last_year, thisYearVacations=this_year_vacations,
                            Backlog=scrum_board_lists["backlog"], ScrumTodo=scrum_board_lists["todo"],
                            inProgress=scrum_board_lists["in progress"], done=scrum_board_lists["done"],
                            ChartMonthDays=chart_month_days, ChartDoneTasks=chart_done_tasks,
                            ChartthisMonthTasks=chart_this_month_tasks, pageTheme=page_theme), 200, headers)

    def post(self):
        if not session.get("name"):
            return "user is not logged in", 401
        if request.form.get("type") == "calendar":
            if request.form["action"] == "create":
                date_value = request.form.get("date")
                task_id = get_unique_id(self.c, self.lock)
                if task_id is False:
                    return "failed to generate unique id", 400
                self.lock.acquire(True)
                self.c.execute("""INSERT INTO calendar VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                    date_value, request.form["startTime"], request.form["stopTime"], request.form["name"],
                    request.form["color"], request.form["details"], request.form["calName"], task_id,
                    request.form["location"]))
                self.conn.commit()
                self.lock.release()
                self.logger.info(f"created task {request.form['name']} for date {date_value}")
                upload_cal_attachments(task_id, request.files.getlist('files[]'))
                task_files = get_all_cal_events_files(task_id)
                return json.dumps({"taskID": task_id, "files": task_files}), 200
            elif request.form["action"] == "edit":
                self.lock.acquire(True)
                self.c.execute("UPDATE calendar SET date = ?, startTime = ?, endTime = ?, eventName = ?, \
                                    color = ?, details = ?, calendarName = ?, location = ? WHERE taskID = ?",
                               (request.form["date"], request.form["startTime"], request.form["stopTime"],
                                request.form["name"], request.form["color"], request.form["details"],
                                request.form["calName"], request.form["location"], request.form["taskID"],))
                self.conn.commit()
                self.lock.release()
                task_id = request.form["taskID"]
                delete_all_attachments(task_id)
                upload_cal_attachments(task_id, request.files.getlist('files[]'))
                self.logger.info(f"updated task {task_id}")
                task_files = get_all_cal_events_files(task_id)
                return json.dumps({"taskID": task_id, "files": task_files}), 200
            elif request.form["action"] == "delete":
                try:
                    date_value = request.form['date']
                    task_id = request.form["taskID"]
                except KeyError:
                    return "failed to extract values", 400
                self.lock.acquire(True)
                self.c.execute("""DELETE from calendar where taskID = ?""", (task_id, ))
                self.conn.commit()
                self.lock.release()
                delete_all_attachments(task_id)
                self.logger.info(f"deleted task {request.form['taskID']} from date {date_value}")
        else:
            args = self.parser.parse_args()
            if args['type'] == 'createCal':
                calendars = fetch_setting_param_from_db(self.c, "calendars", self.lock).split(",")
                value_dict = eval(args['value'])
                calendars.append(value_dict['name'])
                update_setting_param(self.c, self.conn, "calendars",
                                     str(calendars)[1:-1].replace("\'", "").replace(" ", ""), self.lock)
                return "done", 200
            elif args['type'] == 'deleteCal':
                calendars = fetch_setting_param_from_db(self.c, "calendars", self.lock).split(",")
                value_dict = eval(args['value'])
                calendars.remove(value_dict['name'])
                update_setting_param(self.c, self.conn, "calendars",
                                     str(calendars)[1:-1].replace("\'", "").replace(" ", ""), self.lock)
            elif args['type'] == 'vacation':
                value_dict = eval(args['value'])
                if value_dict["name"] == "thisYearVacs":
                    update_vacation_days(args['date'], "yearsVacation", value_dict["value"],
                                         self.c, self.conn, self.lock)
                elif value_dict["name"] == "lastYearVacs":
                    update_vacation_days(args['date'], "vacationFromLastYear", value_dict["value"],
                                         self.c, self.conn, self.lock)
                return "done", 200
            elif args['type'] == 'todo':
                if args['action'] == "search":
                    value_dict = eval((args['value']))
                    search_result = []
                    search_term = value_dict["search_term"].strip().lower()
                    if search_term != "":
                        search_term = "%" + search_term + "%"
                        self.lock.acquire(True)
                        self.c.execute("""SELECT * FROM todoList WHERE task like ? """, (search_term,))
                        search_result = sorted(self.c.fetchall(), key=lambda tup: tup[1], reverse=True)
                        self.lock.release()
                    return search_result, 200
                else:
                    date_val = parse_date(args['date'])
                    value_dict = eval((args['value']))
                    self.lock.acquire(True)
                    self.c.execute("""DELETE from todoList where date = ? and task = ?""",
                                   (date_val, value_dict['value'].lower()))
                    if args['action'] == "delete":
                        self.logger.info(f"removed todo {value_dict['value'].lower()} from todoList for date: {date_val}")
                    else:
                        # TODO: change to UPDATE
                        self.c.execute("""INSERT INTO todoList VALUES(?, ?, ?, ?)""",
                                       (value_dict['value'].lower(), date_val, value_dict['done'], value_dict['color']))
                        self.logger.info(
                            f"added todo {value_dict['value'].lower()} to todoList for date: {date_val} as "
                            f"{value_dict['done']}")
                    self.conn.commit()
                    self.lock.release()
            elif args['type'] == "scrum":
                scrum_dict = eval((args['value']))
                proj = scrum_dict['cardProj']
                task = scrum_dict['cardTask']
                if scrum_dict.get('currentList', None) is not None:
                    current_list = scrum_dict['currentList']
                    if scrum_dict.get('action', "") == "delete":
                        delete_scrum_task(proj, task, self.c, self.conn, self.lock)
                    else:
                        destination_list = scrum_dict.get('destList', "")
                        self.lock.acquire(True)
                        self.c.execute("""SELECT * FROM scrumBoard WHERE project = ? and task = ? and stage = ? """,
                                       (proj, task, current_list))
                        tasks = self.c.fetchall()
                        self.lock.release()
                        if len(tasks) > 0:
                            priority = tasks[0][-2]
                        else:
                            priority = scrum_dict.get('priority', "")
                        if destination_list == "done":
                            delete_scrum_task(proj, task, self.c, self.conn, self.lock)
                            add_scrum_task(proj, task, destination_list, priority, str(datetime.date.today()),
                                           self.c, self.conn, self.lock)
                        elif destination_list == "archive":
                            self.lock.acquire(True)
                            self.c.execute("""SELECT * FROM scrumBoard WHERE project = ? and task = ? """, (proj, task))
                            date_value = self.c.fetchall()[0][-1]
                            self.lock.release()
                            # TODO: change to UPDATE
                            delete_scrum_task(proj, task, self.c, self.conn, self.lock)
                            add_scrum_task(proj, task, destination_list, priority, str(date_value), self.c, self.conn,
                                           self.lock)
                        else:
                            delete_scrum_task(proj, task, self.c, self.conn, self.lock)
                            add_scrum_task(proj, task, destination_list, priority, " ", self.c, self.conn, self.lock)
                        self.conn.commit()
                else:  # it is a new card!
                    priority = scrum_dict['priority']
                    add_scrum_task(proj, task, "backlog", priority, " ", self.c, self.conn, self.lock)
            else:
                print(f"unknown type {args['type']}")
        return "Done", 200
