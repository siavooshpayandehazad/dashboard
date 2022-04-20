from functionPackages.ha_package import generate_ha_db_tables
from functionPackages.misc import *

import datetime
from flask import Flask, request, url_for, redirect
from flask import send_from_directory
from flask_restful import reqparse, Api
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from werkzeug.utils import secure_filename
import os
from random import randint
import logging
from logging.handlers import RotatingFileHandler
from flask_mail import Mail
from threading import Lock

from page_classes.home import Dash
from page_classes.journal import Journal
from page_classes.settings import Settings
from page_classes.org import Org
from page_classes.gallery import Gallery
from page_classes.lists import Lists
from page_classes.notes import Notes
from page_classes.home_automation import HomeAutomation
from page_classes.server import Server
from page_classes.audiobooks import Audiobooks
from page_classes.learning import Learning

app = Flask(__name__, template_folder='template', static_url_path='/static')
api = Api(app)
mail = Mail()
login = Login()

try:
    os.mkdir("./logs")
except Exception as error:
    print(error)

logfile = "logs/log.log"
logger = logging.getLogger(__name__)
logging.basicConfig(filename=logfile,
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : [%(filename)s:%(lineno)d] %(message)s')
handler = RotatingFileHandler(logfile, maxBytes=1024, backupCount=1)
logger.addHandler(handler)

parser = reqparse.RequestParser()
for item in ['tracker_type', 'value', 'oldValue', 'date', 'action', 'type', 'planner']:
    parser.add_argument(item)

lock = Lock()

conn, c = create_db("journal.db")
conn_ha, c_ha = create_db("ha.db")
backup_database(conn)
generate_db_tables(c, conn, lock)
generate_ha_db_tables(c_ha, conn_ha, lock)
setup_setting_table(c, conn, lock)


@app.route("/downloadDB/")
def download_db():
    return send_from_directory(directory=".", filename="journal.db", as_attachment="True",
                               attachment_filename="sqlite_database.db")


@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        upload_date = request.form['date']
        year = upload_date.split("-")[0]
        folder_name = upload_date
        if not os.path.isdir("./static/photos/" + year):
            os.mkdir("./static/photos/" + year)
        if not os.path.isdir("./static/photos/" + year + "/" + folder_name):
            os.mkdir("./static/photos/" + year + "/" + folder_name)
        f = request.files['file']
        file_name = f.filename
        while os.path.isfile("./static/photos/" + year + "/" + folder_name + "/" + file_name):
            file_name = str(randint(1, 100000)) + "_" + f.filename
        f.save(os.path.join("./static/photos/" + year + "/" + folder_name, secure_filename(file_name)))
        return redirect(url_for('journal') + "?date=" + upload_date, 200)


@app.route('/notesUploader', methods=['GET', 'POST'])
def upload_file_notes():
    if request.method == 'POST':
        notebook_label = request.form['notebookLabel']
        if not os.path.isdir("./static/photos/notebookPhotos/"):
            os.mkdir("./static/photos/notebookPhotos/")
        if not os.path.isdir("./static/photos/notebookPhotos/" + notebook_label):
            os.mkdir("./static/photos/notebookPhotos/" + notebook_label)
        f = request.files['file']
        file_name = f.filename
        while os.path.isfile("./static/photos/notebookPhotos/" + notebook_label + "/" + file_name):
            file_name = str(randint(1, 100)) + "_" + f.filename
        f.save(os.path.join("./static/photos/notebookPhotos/" + notebook_label, secure_filename(file_name)))
        return redirect(url_for('notes'), 200)


@app.route('/shutdown', methods=['POST'])
def shutdown_server():
    if request.method == 'POST':
        logger.info("shutdown request received...")
        send_mail("Server:: shutting down", "shut down command received.", app, mail, c, lock)
        login.logout()
        shutdown_req = request.environ.get('werkzeug.server.shutdown')
        if shutdown_req is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        shutdown_req()
        logger.info("closing the DB connection...")
        conn.close()
        logger.info("shutting down the server...")
        scheduler.shutdown()
        return "server is shutting down..."


def send_cal_notification():
    if fetch_setting_param_from_db(c, "EnableEventNotifications", lock) == "false":
        return
    with app.app_context():
        today_date = str(datetime.date.today())
        day, month, year = separate_day_month_year(today_date)
        lock.acquire(True)
        c.execute("""SELECT * FROM calendar WHERE date >= ? and date <= ?  """,
                  (get_months_beginning(month, year).date(),
                   get_months_end(month, year).date(),))
        cal_events = c.fetchall()
        lock.release()
        notifications_to_be_sent = []
        for event in cal_events:
            if event[0] == today_date:
                if event[1] != "None":
                    time_split = event[1].split(":")
                    now = datetime.datetime.now()
                    new_datetime = datetime.datetime.now().replace(hour=int(time_split[0]), minute=int(time_split[1]))
                    diff = new_datetime - now
                    minutes_diff = int(diff.total_seconds() / 60)
                    if (minutes_diff == 30) or (minutes_diff == 15):
                        notifications_to_be_sent.append(event)
        for notification in notifications_to_be_sent:
            body = "Event time: " + notification[1] + " - " + notification[2] + "\n" + \
                   "Event: " + notification[3] + "\n" + \
                   "Description: " + notification[5] + "\n"
            send_mail("Upcoming event: " + notification[3], body, app, mail, c, lock)


def send_daily_digest():
    if fetch_setting_param_from_db(c, "EnableDailyDigest", lock) == "false":
        return
    with app.app_context():
        today_date = str(datetime.date.today())
        lock.acquire(True)
        c.execute("""SELECT * FROM calendar WHERE date = ? """,
                  (today_date,))
        cal_events = c.fetchall()
        c.execute("""SELECT * FROM todoList WHERE date = ? """,
                  (today_date,))
        todos = c.fetchall()
        lock.release()
        body = "Here is your daily digest for:   " + today_date + "\n"
        body += "\n\nCalendar events:\n"
        for event in cal_events:
            body += "\t* Event: " + event[3] + "\n" + \
                    "\t         Event time: " + event[1] + " - " + event[2] + "\n" + \
                    "\t         Description: " + event[5] + "\n"
        body += "\n\nTODOs events:\n"
        for todo in todos:
            body += "\t* Todo: " + todo[0] + "\n"
            body += "\t       Status: " + ("Done" if todo[2] == "true" else "Not Done") + "\n"
        send_mail("Daily Digest for: " + today_date, body, app, mail, c, lock)


scheduler = BackgroundScheduler()
scheduler.add_job(func=send_cal_notification, trigger="interval", seconds=60)
scheduler.add_job(func=send_daily_digest, trigger=CronTrigger.from_crontab('0 6 * * *'))
scheduler.start()

resource_class_args = {"conn": conn, "c": c, "lock": lock, "parser": parser, "conn_ha": conn_ha,
                       "c_ha": c_ha, "login": login}

api.add_resource(Dash, '/', resource_class_kwargs=resource_class_args)
api.add_resource(Journal, '/journal', resource_class_kwargs=resource_class_args)
api.add_resource(Org, '/org', resource_class_kwargs=resource_class_args)
api.add_resource(Settings, '/settings', resource_class_kwargs=resource_class_args)
api.add_resource(Lists, '/lists', resource_class_kwargs=resource_class_args)
api.add_resource(Notes, '/notes', resource_class_kwargs=resource_class_args)
api.add_resource(Gallery, '/gallery', resource_class_kwargs=resource_class_args)
api.add_resource(Learning, '/learning', resource_class_kwargs=resource_class_args)
api.add_resource(Server, '/server', resource_class_kwargs=resource_class_args)
api.add_resource(Audiobooks, '/audiobooks', resource_class_kwargs=resource_class_args)
api.add_resource(HomeAutomation, '/homeAutomation', resource_class_kwargs=resource_class_args)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)

conn.close()
