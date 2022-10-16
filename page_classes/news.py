import datetime

from flask_restful import Resource
from flask import render_template, make_response, request, redirect, url_for
import feedparser
from functionPackages.misc import *
from functionPackages.news_package import *
import time
logger = logging.getLogger(__name__)


class News(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conn = kwargs["conn"]
        self.c = kwargs["c"]
        self.lock = kwargs["lock"]
        self.parser = kwargs["parser"]
        self.conn_news = kwargs["conn_news"]
        self.c_news = kwargs["c_news"]

    def get(self):
        headers = {'Content-Type': 'text/html'}
        page_theme = fetch_setting_param_from_db(self.c, "Theme", self.lock)
        if not session.get("name"):
            return make_response(render_template('login.html', pageTheme=page_theme), 200, headers)
        start_time = time.time()
        weather_dict = get_today_weather_information(self.c, self.lock)
        news_rss = get_news_rss_data(self.c_news, self.lock)
        today = datetime.datetime.today()
        time_stamp = f"{today.date()}:{today.hour}"
        if temporary_data.get("podcasts", {}).get("date", None) != time_stamp:
            news_feed = feedparser.parse("https://www.democracynow.org/podcast-video.xml")
            entry = news_feed.entries[0]
            news_show_date = "-".join(entry["published"].split((" "))[1:4])
            news_show_link = entry["media_content"][0]["url"]

            podcast_links = get_podcasts(self.c_news, self.lock)
            temporary_data["podcasts"] = {"podcast_links": podcast_links,
                                          "news_show_link": news_show_link,
                                          "news_show_date": news_show_date,
                                          "date": time_stamp}
        else:
            podcast_links = temporary_data["podcasts"]["podcast_links"]
            news_show_link = temporary_data["podcasts"]["news_show_link"]
            news_show_date = temporary_data["podcasts"]["news_show_date"]
        twitter_items = get_twitter_data(self.c_news, self.lock)

        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('news.html', pageTheme=page_theme, news_rss=news_rss,
                                             weather_dict=weather_dict,
                                             news_show_link=news_show_link,
                                             news_show_date=news_show_date,
                                             twitter_items=twitter_items,
                                             podcast_links=podcast_links), 200, headers)

    def post(self):
        if not session.get("name"):
            return "user is not logged in", 401
        if request.form["action"] == "add RSS":
            add_rss_data(request.form["rss-title"], request.form["rss-link"], self.c_news, self.conn_news, self.lock)
            return redirect(url_for('news'))
        if request.form["action"] == "add podcast":
            temporary_data["podcasts"] = {}
            add_podcast_data(request.form["podcast-title"], request.form["podcast-link"], self.c_news, self.conn_news, self.lock)
            return redirect(url_for('news'))
        if request.form["action"] == "delete podcast":
            temporary_data["podcasts"] = {}
            delete_podcast_data(request.form["name"], self.c_news, self.conn_news, self.lock)
            return "Done", 200
        if request.form["action"] == "add twitter":
            temporary_data["podcasts"] = {}
            add_twitter_data(request.form["twitter-title"], request.form["twitter-link"], self.c_news, self.conn_news, self.lock)
            return redirect(url_for('news'))
        if request.form["action"] == "delete twitter":
            delete_twitter_data(request.form["name"], self.c_news, self.conn_news, self.lock)
            return "Done", 200
