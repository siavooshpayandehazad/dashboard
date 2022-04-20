from flask_restful import Resource
from flask import render_template, make_response
from pathlib import Path
from functionPackages.misc import *

logger = logging.getLogger(__name__)


class Settings(Resource):
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
        activity_list = fetch_setting_param_from_db(self.c, "activityList", self.lock)
        audiobooks_path = fetch_setting_param_from_db(self.c, "audiobooksPath", self.lock)

        mail_username = fetch_setting_param_from_db(self.c, "MAIL_USERNAME", self.lock)
        mail_server = fetch_setting_param_from_db(self.c, "MAIL_SERVER", self.lock)
        mail_port = fetch_setting_param_from_db(self.c, "MAIL_PORT", self.lock)
        mail_ssl = fetch_setting_param_from_db(self.c, "MAIL_USE_SSL", self.lock)
        recipient_email = fetch_setting_param_from_db(self.c, "MAIL_RECIPIENT", self.lock)
        enable_daily_digest = fetch_setting_param_from_db(self.c, "EnableDailyDigest", self.lock)
        enable_event_notifications = fetch_setting_param_from_db(self.c, "EnableEventNotifications", self.lock)
        email_setting = {"MAIL_USERNAME": mail_username,
                         "MAIL_SERVER": mail_server,
                         "MAIL_PORT": mail_port,
                         "MAIL_USE_SSL": mail_ssl,
                         "MAIL_PASSWORD": "mail pass",
                         "MAIL_RECIPIENT": recipient_email,
                         "EnableEventNotifications": enable_event_notifications,
                         "EnableDailyDigest": enable_daily_digest
                         }
        return make_response(render_template('settings.html', activityList=activity_list,
                                             audiobooksPath=audiobooks_path, pageTheme=page_theme,
                                             email_setting=email_setting,
                                             loggedIn=str(self.login.is_logged_in)), 200, headers)

    def post(self):
        if not self.login.is_logged_in:
            return "user is not logged in", 401

        args = self.parser.parse_args()
        if args['type'] == "Theme":
            page_theme = args['value']
            update_setting_param(self.c, self.conn, "Theme", page_theme, self.lock)
        if args['type'] == "activityList":
            activity_list = args['value']
            update_setting_param(self.c, self.conn, "activityList", activity_list, self.lock)
        if args['type'] == "password":
            pass_dict = eval((args['value']))
            hashed_password = fetch_setting_param_from_db(self.c, "password", self.lock)
            if (hashed_password == "None") or verify_password(hashed_password, pass_dict["currntpwd"]):
                update_setting_param(self.c, self.conn, "password", hash_password(pass_dict["newpwd"]), self.lock)
                return "succeeded", 200
            return "failed", 200
        if args['type'] == "audiobooksPath":
            update_setting_param(self.c, self.conn, "audiobooksPath", args['value'], self.lock)
            source = Path(args['value'])
            destination = Path("./static/audiobooks/").resolve()
            os.symlink(source, destination)
            return "succeeded", 200
        if args['type'] == "mailSetting":
            value_dict = eval((args['value']))
            for setting_item in value_dict:
                if setting_item != "MAIL_PASSWORD":
                    update_setting_param(self.c, self.conn, setting_item, value_dict[setting_item], self.lock)
                else:
                    if value_dict[setting_item] != "mailpass":
                        update_setting_param(self.c, self.conn, setting_item, value_dict[setting_item], self.lock)
            return "succeeded", 200
        if args['type'] == "EnableDailyDigest":
            update_setting_param(self.c, self.conn, "EnableDailyDigest", args['value'], self.lock)
            return "succeeded", 200
        if args['type'] == "EnableEventNotifications":
            update_setting_param(self.c, self.conn, "EnableEventNotifications", args['value'], self.lock)
            return "succeeded", 200
        return "Done", 200
