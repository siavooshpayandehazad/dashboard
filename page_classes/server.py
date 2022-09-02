from flask_restful import Resource
from flask import render_template, make_response

from functionPackages.charts import generate_cpu_stat_monthly, generate_cpu_stat
from functionPackages.misc import *
from package import chart_months

logger = logging.getLogger(__name__)


class Server(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conn = kwargs["conn"]
        self.c = kwargs["c"]
        self.lock = kwargs["lock"]
        self.parser = kwargs["parser"]

    def get(self):
        headers = {'Content-Type': 'text/html'}
        page_theme = fetch_setting_param_from_db(self.c, "Theme", self.lock)
        if not session.get("name"):
            return make_response(render_template('login.html', pageTheme=page_theme), 200, headers)
        start_time = time.time()
        args = self.parser.parse_args()
        if args['date'] is not None:
            year, month, day = args['date'].split("-")
            today_date = "-".join([day, month, year[-2:]])
        else:
            today = datetime.date.today()
            day, month, year = today.day, today.month, today.year
            today_date = today.strftime('%d-%m-%y')

        cpu_temps, cpu_temps_times, cpu_usage, cpu_usage_times, disc_space, up_time = \
            generate_cpu_stat(today_date, str(year))
        cpu_temps_yearly, cpu_usage_yearly = generate_cpu_stat_monthly(str(year))
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('server.html', pageTheme=page_theme,
                                             cpuTemps=cpu_temps, cpuTempsTimes=cpu_temps_times,
                                             cpuUsage=cpu_usage, cpuUsageTimes=cpu_usage_times,
                                             cpuUsageYearly=cpu_usage_yearly, cpuTempsYearly=cpu_temps_yearly,
                                             upTime=up_time, HideLine="true", chart_months=chart_months,
                                             discSpace=disc_space, year=int(year), month=int(month), day=int(day),
                                             PageYear=1999, PageMonth=10), 200, headers)

    @staticmethod
    def post():
        if not session.get("name"):
            return "user is not logged in", 401
        return "Nothing to be posted!", 200
