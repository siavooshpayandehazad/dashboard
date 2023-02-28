from flask_restful import Resource
from flask import render_template, make_response, request

from functionPackages.charts import generate_e_consumption_tracker_chart_data, generate_weather_monthly, \
    generate_weather_daily
from functionPackages.ha_package import *
from functionPackages.misc import *
from package import chart_months

logger = logging.getLogger(__name__)


class HomeAutomation(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conn = kwargs["conn"]
        self.c = kwargs["c"]
        self.lock = kwargs["lock"]
        self.parser = kwargs["parser"]
        self.conn_ha = kwargs["conn_ha"]
        self.c_ha = kwargs["c_ha"]

    def get(self):
        page_theme = fetch_setting_param_from_db(self.c, "Theme", self.lock)
        headers = {'Content-Type': 'text/html'}
        if not session.get("name"):
            return make_response(render_template('login.html', pageTheme=page_theme), 200, headers)

        start_time = time.time()
        args = self.parser.parse_args()
        if args['date'] is not None:
            year, month, day = args['date'].split("-")
            today_date = "-".join([year, month, day])
        else:
            today = datetime.date.today()
            day, month, year = today.day, today.month, today.year
            today_date = today.strftime('%Y-%m-%d')

        my_annual_consumption = generate_e_consumption_tracker_chart_data(str(year), self.c_ha, self.lock)
        monthly_data = generate_weather_monthly(self.c_ha, int(year), self.lock)
        daily_data, description = generate_weather_daily(self.c_ha, today_date, self.lock)
        prep_data = get_prep_data(self.c_ha, self.lock)
        lights = get_light_vals(self.c_ha, self.lock)
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('homeAutomation.html', daily_data=daily_data,
                                             monthly_Data=monthly_data, chart_months=chart_months,
                                             prep_data=prep_data, lights=lights,
                                             myAnnualConsumption=my_annual_consumption, description=description,
                                             pageTheme=page_theme, HideLine="true",
                                             PageYear=int(year), PageMonth=int(month), day=int(day)), 200, headers)

    def post(self):

        if request.form.get("action") == "change light":
            add_val_to_light(request.form['light_id'], request.form['val_id'], request.form["value"],
                             self.c_ha, self.conn_ha, self.lock)
            return "Done", 200

        if request.form.get("action") == "switch light":
            switch_light(request.form['light_id'], request.form['state'], self.c_ha, self.conn_ha, self.lock)
            return "Done", 200

        args = self.parser.parse_args()
        value = json.loads(args['value'])

        if args['action'] == "addPrepItem":
            id_number = str(time.time()).replace(".", "")
            add_prep_data(id_number, value["item_name"].lower(), value["item_type"].lower(), value["quantity"], value["expiry_date"],
                          self.c_ha, self.conn_ha, self.lock)
            return id_number, 200

        if args['action'] == "deletePrepItem":
            delete_prep_data(value["id_number"], self.c_ha, self.conn_ha, self.lock)
            return "Done", 200

        if args['action'] == "rename":
            rename_room(str(value['roomNumber']), str(value['newValue']), self.c_ha, self.conn_ha, self.lock)
            return "Done", 200

        if args['tracker_type'] == "eConsumption":
            add_econsumption_data(args['date'], args['value'], self.c_ha, self.conn_ha, self.lock)
            return "Done", 200
        else:
            value["temp"] = value.get("temp", "0")
            value["humidity"] = value.get("humidity", "0")
            value["pressure"] = value.get("pressure", "0")
            value["moisture"] = value.get("moisture", "0")
            add_data_to_ha_db(self.c_ha, self.conn_ha, value['room'], value['date'], value['hour'], value["temp"],
                              value["humidity"], value["pressure"], value["moisture"], self.lock)
            return "Done", 200
