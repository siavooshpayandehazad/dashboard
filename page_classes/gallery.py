from flask_restful import Resource
from flask import render_template, make_response, request
from functionPackages.misc import *

logger = logging.getLogger(__name__)


class Gallery(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conn = kwargs["conn"]
        self.c = kwargs["c"]
        self.lock = kwargs["lock"]
        self.parser = kwargs["parser"]
        self.login = kwargs["login"]

    def get(self):
        headers = {'Content-Type': 'text/html'}
        page_theme = fetch_setting_param_from_db(self.c, "Theme", self.lock)
        req_session_id = request.headers.get("Cookie", "session=1;").split("=")[-1].split(";")[0]
        if (not self.login.is_user_logged_in()) or (req_session_id != self.login.session_id):
            return make_response(render_template('login.html', pageTheme=page_theme), 200, headers)
        start_time = time.time()
        args = self.parser.parse_args()
        today_date = parse_date(args['date'])
        day, month, year = separate_day_month_year(today_date)
        number_of_days = number_of_days_in_month(int(month), int(year))
        months_beginning = get_months_beginning(month, year).weekday()
        months_photos = []
        for day_number in range(1, number_of_days + 1):
            date_value = str(year) + "-" + str(month).zfill(2) + "-" + str(day_number).zfill(2)
            photo_dir = os.getcwd() + "/static/photos/" + str(year) + "/" + date_value
            today_photos = all_photos_in_dir(photo_dir, str(year), date_value)
            months_photos.append(today_photos)
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('gallery.html', day=day, month=month, year=year,
                                             numberOfDays=number_of_days, monthsBeginning=months_beginning,
                                             monthsPhotos=months_photos,
                                             pageTheme=page_theme, loggedIn=str(self.login.is_logged_in)), 200, headers)

    def post(self):
        if not self.login.is_logged_in:
            return "user is not logged in", 401
        return "Done", 200
