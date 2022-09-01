from flask_restful import Resource
from flask import render_template, make_response, request
from functionPackages.misc import *

logger = logging.getLogger(__name__)


class Learning(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conn = kwargs["conn"]
        self.c = kwargs["c"]
        self.conn_learning = kwargs["conn_learning"]
        self.c_learning = kwargs["c_learning"]
        self.lock = kwargs["lock"]
        self.parser = kwargs["parser"]
        self.login = kwargs["login"]

    def get(self):
        headers = {'Content-Type': 'text/html'}
        page_theme = fetch_setting_param_from_db(self.c, "Theme", self.lock)
        req_session_id = request.headers.get("Cookie", "session=1;").split("=")[-1].split(";")[0]
        if (not self.login.is_user_logged_in()) or (req_session_id != self.login.session_id):
            return make_response(render_template('login.html', pageTheme=page_theme), 200, headers)

        set_names, flash_cards = get_flash_cards(self.c_learning, self.lock)
        return make_response(render_template('learning.html', pageTheme=page_theme, setNames=set_names,
                                             flashCards=flash_cards,
                                             loggedIn=str(self.login.is_logged_in)), 200, headers)

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
                add_flash_cards(set_name, side1, side2, last_time_reviewed, self.c_learning,
                                self.conn_learning, self.lock)
            elif args["action"] == "delete":
                values = json.loads(args['value'])
                set_name = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                delete_flash_cards(set_name, side1, side2, self.c_learning, self.conn_learning, self.lock)
            else:
                values = json.loads(args['value'])
                set_name = values["setName"]
                side1 = values["side1"]
                side2 = values["side2"]
                if args["action"] == "true":
                    last_time_reviewed = str(datetime.date.today())
                    change_flash_cards(set_name, side1, side2, last_time_reviewed, self.c_learning,
                                       self.conn_learning, self.lock)
        return "Done", 200
