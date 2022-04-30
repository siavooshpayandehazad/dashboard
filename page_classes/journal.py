from flask_restful import Resource
from flask import render_template, make_response

from functionPackages.charts import *
from functionPackages.misc import *
from functionPackages.dateTime import *

logger = logging.getLogger(__name__)


class Journal(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conn = kwargs["conn"]
        self.c = kwargs["c"]
        self.lock = kwargs["lock"]
        self.parser = kwargs["parser"]
        self.login = kwargs["login"]

    def get(self):
        start_time = time.time()
        args = self.parser.parse_args()
        page_theme = fetch_setting_param_from_db(self.c, "Theme", self.lock)
        headers = {'Content-Type': 'text/html'}
        today_date = parse_date(args['date'])
        day, month, year = separate_day_month_year(today_date)
        photo_dir = os.getcwd() + "/static/photos/" + str(year) + "/" + today_date
        photo_dir2 = os.getcwd() + "/static/photos/" + str(year)
        days_with_photos = all_days_with_photos(photo_dir2, str(year), str(month))
        today_photos = all_photos_in_dir(photo_dir, str(year), today_date)
        today_log, today_log_text = get_today_logs(self.c, today_date, self.lock)
        number_of_days = number_of_days_in_month(int(month), int(year))
        months_beginning = get_months_beginning(month, year).weekday()

        self.lock.acquire(True)
        self.c.execute("""SELECT * FROM tracker WHERE date >= ? and date <= ? """,
                       (get_months_beginning(month, year).date(), get_months_end(month, year).date(),))

        logged_days = [int(x[0].split("-")[2]) for x in self.c.fetchall() if x[14] != "nan"]
        self.lock.release()

        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('journal.html', numberOfDays=number_of_days,
                                             day=day, month=month, year=year, monthsBeginning=months_beginning,
                                             log=today_log, todaysLogText=today_log_text, todayPhotos=today_photos,
                                             logged_days=logged_days, daysWithPhotos=days_with_photos,
                                             pageTheme=page_theme, loggedIn=str(self.login.is_logged_in)),
                             200, headers)

    def post(self):
        if not self.login.is_logged_in:
            return "user is not logged in", 401
        args = self.parser.parse_args()
        if args['type'] == 'log':
            today_date = parse_date(args['date'])
            log_entry = args['value'].lower()

            self.lock.acquire(True)
            self.c.execute("""SELECT * FROM tracker WHERE date = ? """, (today_date,))
            if len(self.c.fetchall()) == 0:
                self.c.execute("INSERT INTO tracker VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (today_date, "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan", "nan",
                                "nan", "nan", "nan", "nan", "nan"))
            self.c.execute("UPDATE tracker SET log = ? WHERE date = ?", (log_entry, today_date,))
            self.conn.commit()
            self.lock.release()

            logger.info(f"added log for date: {today_date}")
        if args['type'] == "photo":
            if args['action'] == "delete":
                file = "./static" + args['value'].split("/static")[1]
                if os.path.isfile(file):
                    os.remove(file)
                    parent_dir = "./static" + "/".join(args['value'].split("/static")[1].split("/")[:-1])
                    logger.info("parent Directory:", parent_dir)
                    if len(os.listdir(parent_dir)) == 0:
                        os.rmdir(parent_dir)
                else:
                    return "File Doesnt Exist!", 400
        if args['type'] == "tag":
            if args['action'] == "delete":
                value_dict = eval(args['value'])
                tags = value_dict["tag"]
                file_name = "./static/photos/" + value_dict["fileName"]
                if os.path.isfile(file_name):
                    remove_tag_from_picture(file_name, tags)
            else:
                value_dict = eval(args['value'])
                tags = value_dict["tag"]
                file_name = "./static/photos/" + value_dict["fileName"]
                if os.path.isfile(file_name):
                    add_tag_to_picture(file_name, tags)
        return "Done", 200

