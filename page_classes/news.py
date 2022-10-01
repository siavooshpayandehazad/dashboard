import datetime

from flask_restful import Resource
from flask import render_template, make_response, request
import feedparser
from functionPackages.misc import *
import time
logger = logging.getLogger(__name__)


class News(Resource):
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
        weather_dict = get_today_weather_information(self.c, self.lock)
        news_rss = [("Democracy now!", "//rss.bloople.net/?url=https%3A%2F%2Fwww.democracynow.org%2Fdemocracynow.rss&detail=50&limit=5&showtitle=false&type=js"),
                    ("Pink News", "//rss.bloople.net/?url=https%3A%2F%2Fwww.pinknews.co.uk%2Ffeed%2F&detail=50&limit=5&showtitle=false&type=js"),
                    ("truthout","//rss.bloople.net/?url=https%3A%2F%2Ftruthout.org%2Flatest%2Ffeed%2F&detail=50&limit=6&showtitle=false&type=js"),
                    ("Inside Higher-Ed","//rss.bloople.net/?url=https%3A%2F%2Fwww.insidehighered.com%2Fnews%2Ffeed&detail=50&limit=5&showtitle=false&striphtml=true&type=js")]

        today = datetime.datetime.today()
        time_stamp = f"{today.date()}:{today.hour}"
        if temporary_data.get("podcasts", {}).get("date", None) != time_stamp:
            news_feed = feedparser.parse("https://www.democracynow.org/podcast-video.xml")
            entry = news_feed.entries[0]
            news_show_date = "-".join(entry["published"].split((" "))[1:4])
            news_show_link = entry["media_content"][0]["url"]

            podcast_links = []
            podcast_feed = feedparser.parse("http://dissidentisland.org/rss")
            entry = podcast_feed.entries[0]
            podcast_links.append(["Dissident Island Radio",
                                  entry["image"]["href"],
                                  entry["links"][1]["href"]])

            podcast_feed = feedparser.parse("https://archive.org/services/collection-rss.php?collection=thefinalstrawradio")
            entry = podcast_feed.entries[0]
            podcast_links.append(["The Final Straw Radio",
                                  entry["summary_detail"]["value"].split("\"")[1],
                                  entry["links"][-1]["href"]])

            temporary_data["podcasts"] = {"podcast_links": podcast_links,
                                          "news_show_link": news_show_link,
                                          "news_show_date": news_show_date,
                                          "date": time_stamp}
        else:
            podcast_links = temporary_data["podcasts"]["podcast_links"]
            news_show_link = temporary_data["podcasts"]["news_show_link"]
            news_show_date = temporary_data["podcasts"]["news_show_date"]

        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('news.html', pageTheme=page_theme, news_rss=news_rss,
                                             weather_dict=weather_dict,
                                             news_show_link=news_show_link,
                                             news_show_date=news_show_date,
                                             podcast_links=podcast_links), 200, headers)

    @staticmethod
    def post():
        if not session.get("name"):
            return "user is not logged in", 401
        return "Done", 200
