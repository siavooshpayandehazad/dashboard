from flask_restful import Resource
from flask import render_template, make_response
from functionPackages.misc import *

logger = logging.getLogger(__name__)


class Learning(Resource):
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
        set_names, max_days_numbers, cnts, flash_cards = get_flash_cards(self.c, self.lock)
        max_days_numbers = list(range(1, max_days_numbers + 1))
        counters = []
        for i in max_days_numbers:
            if i in cnts.keys():
                counters.append(cnts[i])
            else:
                counters.append(0)
        return make_response(render_template('learning.html', pageTheme=page_theme, setNames=set_names,
                                             flashCards=flash_cards, maxDaysNumbers=max_days_numbers,
                                             countes=counters, loggedIn=str(self.login.is_logged_in)), 200, headers)

    def post(self):
        if not self.login.is_logged_in:
            return "user is not logged in", 401
        args = self.parser.parse_args()
        if args["type"] == "flashCards":
            if args["action"] == "create":
                values = json.loads(args['value'])
                set_name = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                last_time_reviewed = str(datetime.date.today())
                add_flash_cards(set_name, side1, side2, last_time_reviewed, self.c, self.conn, self.lock)
            elif args["action"] == "delete":
                values = json.loads(args['value'])
                set_name = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                delete_flash_cards(set_name, side1, side2, self.c, self.conn, self.lock)
            else:
                values = json.loads(args['value'])
                set_name = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                last_time_reviewed = str(datetime.date.today())
                if args["action"] == "true":
                    change_flash_cards(set_name, side1, side2, last_time_reviewed, True, self.c, self.conn, self.lock)
                else:
                    change_flash_cards(set_name, side1, side2, last_time_reviewed, False, self.c, self.conn, self.lock)
        return "Done", 200
