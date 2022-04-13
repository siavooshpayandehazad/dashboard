from flask_restful import Resource
from flask import render_template, make_response
import time
from functionPackages.misc import *
from package import days_of_the_week

logger = logging.getLogger(__name__)


class Org(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conn = kwargs["conn"]
        self.c = kwargs["c"]
        self.lock = kwargs["lock"]
        self.parser = kwargs["parser"]

    def get(self):
        start_time = time.time()
        page_theme = fetch_setting_param_from_db(self.c, "Theme", self.lock)

        headers = {'Content-Type': 'text/html'}
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

        cal_date = get_cal_events(today_date, self.c, self.lock)
        cal_month = get_cal_events_month(today_date, self.c, self.lock)
        # ---------------------------
        header_dates = []
        day_val = datetime.datetime.strptime(today_date, '%Y-%m-%d') - datetime.timedelta(days=week_day)  # week's start
        for i in range(1, 8):
            header_dates.append(str(day_val.date()).split("-")[2])
            day_val = datetime.datetime.strptime(str(day_val.date()), '%Y-%m-%d') + datetime.timedelta(days=1)
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(
            render_template('org.html', day=day, month=month, year=year, weekDay=days_of_the_week[week_day],
                            monthsBeginning=months_beginning_week_day, todayTodos=today_todos, overDue=all_due_events,
                            numberOfDays=number_of_days, thisMonthsEvents=this_months_events, calDate=cal_date,
                            calMonth=cal_month, headerDates=header_dates,
                            Backlog=scrum_board_lists["backlog"], ScrumTodo=scrum_board_lists["todo"],
                            inProgress=scrum_board_lists["in progress"], done=scrum_board_lists["done"],
                            ChartMonthDays=chart_month_days, ChartDoneTasks=chart_done_tasks,
                            ChartthisMonthTasks=chart_this_month_tasks, pageTheme=page_theme), 200, headers)

    def post(self):
        args = self.parser.parse_args()
        if args['type'] == 'todo':
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
                    logger.info(f"removed todo {value_dict['value'].lower()} from todoList for date: {date_val}")
                else:
                    self.c.execute("""INSERT INTO todoList VALUES(?, ?, ?, ?)""",
                                   (value_dict['value'].lower(), date_val, value_dict['done'], value_dict['color']))
                    logger.info(
                        f"added todo {value_dict['value'].lower()} to todoList for date: {date_val} as "
                        f"{value_dict['done']}")
                self.conn.commit()
                self.lock.release()

        elif args['type'] == 'calendar':
            if args["action"] == "create":
                date_value = args['date']
                values = json.loads(args['value'])
                self.lock.acquire(True)
                self.c.execute("""INSERT INTO calendar VALUES(?, ?, ?, ?, ?, ?)""", (
                    date_value, values["startTime"], values["stopTime"], values["name"], values["color"],
                    values["details"]))
                self.conn.commit()
                self.lock.release()
            elif args["action"] == "delete":
                date_value = args['date']
                values = json.loads(args['value'])
                self.lock.acquire(True)
                self.c.execute(
                    """DELETE from calendar where date = ? and startTime = ? and endTime = ?  and eventName = ? """,
                    (date_value, values["startTime"], values["stopTime"], values["name"]))
                self.conn.commit()
                self.lock.release()
            elif args["action"] == "edit":
                self.lock.acquire(True)
                values = json.loads(args['oldValue'])
                new_values = json.loads(args['value'])
                self.c.execute(
                    """DELETE from calendar where date = ? and startTime = ? and endTime = ?  and eventName = ? """,
                    (values["date"], values["startTime"], values["stopTime"], values["name"]))
                self.c.execute("""INSERT INTO calendar VALUES(?, ?, ?, ?, ?, ?)""", (
                    new_values["date"], new_values["startTime"], new_values["stopTime"], new_values["name"],
                    new_values["color"], new_values["details"]))
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
        return "Done", 200