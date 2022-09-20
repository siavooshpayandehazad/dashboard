from flask_restful import Resource
from flask import render_template, make_response

from functionPackages.charts import generate_finance_charts
from functionPackages.finance_package import add_data_to_finance_db
from functionPackages.misc import *

logger = logging.getLogger(__name__)


class Finances(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conn = kwargs["conn"]
        self.c = kwargs["c"]
        self.conn_finance = kwargs["conn_finance"]
        self.c_finance = kwargs["c_finance"]
        self.lock = kwargs["lock"]
        self.parser = kwargs["parser"]

    def get(self):
        headers = {'Content-Type': 'text/html'}
        page_theme = fetch_setting_param_from_db(self.c, "Theme", self.lock)
        if not session.get("name"):
            return make_response(render_template('login.html', pageTheme=page_theme), 200, headers)
        args = self.parser.parse_args()
        if args['date'] is not None:
            page_year, page_month, page_day = args['date'].split("-")
        else:
            page_month = str(datetime.date.today().month).zfill(2)
            page_year = str(datetime.date.today().year)

        number_of_days = number_of_days_in_month(int(page_month), int(page_year))
        chart_data = generate_finance_charts(int(page_month), int(page_year), number_of_days,
                                             self.c, self.c_finance, self.lock)
        spending_data, break_down_values, break_down_titles = generate_month_spending_data(int(page_month),
                                                                                           int(page_year),
                                                                                           self.c_finance,
                                                                                           self.lock)
        return make_response(render_template('finances.html', ChartData=chart_data,
                                             PageYear=page_year, PageMonth=page_month,
                                             HideLine="false", today=datetime.date.today().day,
                                             SpendingData=spending_data, breakDownValues=break_down_values,
                                             breakDownTitles=break_down_titles,
                                             pageTheme=page_theme), 200, headers)

    def post(self):
        if not session.get("name"):
            return "user is not logged in", 401

        args = self.parser.parse_args()
        today_date = parse_date(args['date'])
        if args['tracker_type'] == 'saving':
            return add_saving_item_to_table(args['value'].lower(), today_date, self.c, self.conn, self.lock)

        if args['tracker_type'] == 'mortgage':
            return add_mortgage_item_to_table(args['value'].lower(), today_date, self.c, self.conn, self.lock)

        if args['tracker_type'] == 'spending':
            item_value = [x.strip() for x in args['value'].lower().split(",")]
            add_data_to_finance_db(self.c_finance, self.conn_finance, today_date, item_value[0].strip(),
                                   item_value[1].strip(), item_value[2].strip(), self.lock)

        if args['action'] == "update":
            old_vals = eval(args['oldValue'])
            old_date = old_vals["date"].strip()
            old_name = old_vals["name"].strip()
            old_cost = old_vals["cost"].strip()
            old_type = old_vals["type"].strip()

            new_vals = eval(args['value'])
            new_date = new_vals["date"].strip()
            new_name = new_vals["name"].strip()
            new_cost = new_vals["cost"].strip()
            new_type = new_vals["type"].strip()

            self.lock.acquire(True)
            self.c_finance.execute("UPDATE finance "
                                   "SET date = ? , name = ? , cost = ? , type = ? "
                                   "WHERE date = ? AND name = ? AND cost = ? AND type = ?",
                                   (new_date, new_name, new_cost, new_type, old_date, old_name, old_cost, old_type))
            self.conn_finance.commit()
            self.lock.release()

        if args['action'] == "delete":
            vals = eval(args['value'])
            date = vals["date"].strip()
            name = vals["name"].strip()
            cost = vals["cost"].strip()
            type = vals["type"].strip()
            self.lock.acquire(True)
            self.c_finance.execute("""DELETE from finance WHERE date = ? AND name = ? AND cost = ? AND type = ?""",
                                   (date, name, cost, type))
            self.conn_finance.commit()
            self.lock.release()
        return "Done", 200
