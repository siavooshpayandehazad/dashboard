from flask_restful import Resource
from flask import render_template, make_response

from functionPackages.charts import *
from functionPackages.misc import *
from functionPackages.dateTime import *
from package import *

logger = logging.getLogger(__name__)


class Dash(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conn = kwargs["conn"]
        self.c = kwargs["c"]
        self.lock = kwargs["lock"]
        self.parser = kwargs["parser"]

    def get(self):
        start_time = time.time()
        args = self.parser.parse_args()
        try:
            page_theme = fetch_setting_param_from_db(self.c, "Theme", self.lock)
        except Exception as err:
            logger.error(err)
            page_theme = "Dark"
            logger.info("could not fetch page theme! replacing with default values")
        activity_list = fetch_setting_param_from_db(self.c, "activityList", self.lock).replace(" ", "").split(",")
        if args['date'] is not None:
            page_year, page_month, page_day = args['date'].split("-")
        else:
            page_month = str(datetime.date.today().month).zfill(2)
            page_year = str(datetime.date.today().year)

        headers = {'Content-Type': 'text/html'}
        page_title = "DashBoard"

        title_date = weeks_of_the_year[int(page_month) - 1] + "-" + page_year
        number_of_days = number_of_days_in_month(int(page_month), int(page_year))
        months_beginning_week_day = datetime.datetime.strptime(f"{page_year}-{page_month}-01", '%Y-%m-%d').weekday()
        # moodTrackerDays is a list that contains a bunch of Nones for the days of the week that are in the
        # previous month. this is used for the mood-tracker in order to add the empty spaces in the beginning of the
        # month.
        mood_tracker_days = [None for _ in range(0, months_beginning_week_day)] + list(range(1, number_of_days + 1))
        # list of current month's moods and activities.
        months_activities, months_activities_planned, months_moods = collect_months_data(int(page_month),
                                                                                         int(page_year), self.c,
                                                                                         self.lock)

        years_activities = collect_yearly_activities(int(page_year), self.c, self.lock)
        # highlights the current day in the activity tracker page!
        highlight = should_highlight(page_year, page_month)
        counter_value = fetch_setting_param_from_db(self.c, "counter", self.lock)

        chart_data = get_chart_data(page_month, page_year, number_of_days, self.c, self.lock)

        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('index.html', name=page_title, titleDate=title_date,
                                             PageYear=int(page_year), PageMonth=int(page_month),
                                             today=datetime.date.today().day, moods=months_moods,
                                             # charts info
                                             ChartMonthDays=chart_data["ChartMonthDays"],
                                             ChartYearMonths=weeks_of_the_year,
                                             ChartData=chart_data, HideLine="false",
                                             # ----------------------
                                             activities=months_activities,
                                             monthsActivitiesPlanned=months_activities_planned,
                                             activityList=activity_list, days=mood_tracker_days, highlight=highlight,
                                             yearsActivities=years_activities,
                                             pageTheme=page_theme, counterValue=counter_value), 200, headers)

    def post(self):
        activity_list = fetch_setting_param_from_db(self.c, "activityList", self.lock).replace(" ", "").split(",")
        args = self.parser.parse_args()
        if args['type'] == "password":
            password = fetch_setting_param_from_db(self.c, "password", self.lock)
            if password == "None":
                return "success", 200
            else:
                if not verify_password(password, args['value']):
                    return "failed", 200
                else:
                    return "success", 200

        if args['type'] == "counter":
            counter_value = int(fetch_setting_param_from_db(self.c, "counter", self.lock))
            if args['value'] == "countup":
                counter_value += 1
            elif args['value'] == "reset":  # reset the counter
                counter_value = 0
            update_setting_param(self.c, self.conn, "counter", counter_value, self.lock)

        today_date = parse_date(args['date'])
        delete = False
        if len(args['value'].strip()) == 0:
            delete = True
        if args['tracker_type'] in ['sleep', 'running', 'pace', 'step', 'weight', 'work', 'hydration']:
            return add_tracker_item_to_table(args['value'].lower(), [], args['tracker_type'] + "Tracker",
                                             today_date, delete, self.c, self.conn, self.lock)
        if args['tracker_type'] in ['HR', 'BP']:
            values = args['value'].split(",")
            add_tracker_item_to_table(values[0], [], args['tracker_type'] + "_Min",
                                      today_date, delete, self.c, self.conn, self.lock)
            add_tracker_item_to_table(values[1], [], args['tracker_type'] + "_Max",
                                      today_date, delete, self.c, self.conn, self.lock)
            return "Done", 200

        if args['tracker_type'] == 'blood oxygen':
            return add_tracker_item_to_table(args['value'].lower(), [], "oxygenTracker", today_date,
                                             delete, self.c, self.conn, self.lock)
        if args['tracker_type'] == 'saving':
            return add_saving_item_to_table(args['value'].lower(), today_date, self.c, self.conn, self.lock)
        if args['tracker_type'] == 'mortgage':
            return add_mortgage_item_to_table(args['value'].lower(), today_date, self.c, self.conn, self.lock)
        if args['tracker_type'] == 'mood':
            return add_tracker_item_to_table(args['value'].lower(), moodList, "moodTracker",
                                             today_date, False, self.c, self.conn, self.lock)
        if args['tracker_type'] == "activity":
            delete = True if args['action'] == "delete" else False
            if args['planner'] == "True":
                return add_tracker_item_to_table(args['value'].lower(), activity_list,
                                                 "activityPlanner", today_date, delete, self.c, self.conn, self.lock)
            else:
                return add_tracker_item_to_table(args['value'].lower(), activity_list,
                                                 "activityTracker", today_date, delete, self.c, self.conn, self.lock)
        if args['tracker_type'] == "travel":
            values = args['value'].split(",")
            add_travel_item(values[0], values[1], values[2], self.c, self.conn, self.lock)
        return "Done", 200
