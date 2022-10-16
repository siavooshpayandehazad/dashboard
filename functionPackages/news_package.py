import feedparser
import multiprocessing


def generate_news_db_tables(db_cursor, db_connection, lock):
    try:
        lock.acquire(True)
        db_cursor.execute("""CREATE TABLE if not exists rss(rss_name text, rss_link text)""")
        db_cursor.execute("""CREATE TABLE if not exists podcasts(podcast_name text, podcast_link text)""")
        db_cursor.execute("""CREATE TABLE if not exists twitters(twitter_name text, twitter_link text)""")
        db_connection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def get_news_rss_data(db_cursor, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM rss """)
    rss_data = [tuple(x) for x in db_cursor.fetchall()]
    lock.release()
    return rss_data


def get_news_podcast_data(db_cursor, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM podcasts """)
    rss_data = [tuple(x) for x in db_cursor.fetchall()]
    lock.release()
    return rss_data


def add_rss_data(rss_name, rss_link, db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""INSERT INTO rss VALUES(?, ?)""", (rss_name, rss_link))
    db_connection.commit()
    lock.release()
    return None


def add_podcast_data(podcast_name, podcast_link, db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""INSERT INTO podcasts VALUES(?, ?)""", (podcast_name, podcast_link))
    db_connection.commit()
    lock.release()
    return None


def delete_podcast_data(podcast_name, db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""DELETE from podcasts where podcast_name = ?""",
                      (podcast_name, ))
    db_connection.commit()
    lock.release()


def get_twitter_data(db_cursor, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM twitters """)
    twitter_data = [tuple(x) for x in db_cursor.fetchall()]
    lock.release()
    return twitter_data


def add_twitter_data(twitter_name, twitter_link, db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""INSERT INTO twitters VALUES(?, ?)""", (twitter_name, twitter_link))
    db_connection.commit()
    lock.release()
    return None


def delete_twitter_data(twitter_name, db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""DELETE from twitters where twitter_name = ?""",
                      (twitter_name, ))
    db_connection.commit()
    lock.release()


def parse_feed(pod):
    podcast_feed = feedparser.parse(pod[1])
    entry = podcast_feed.entries[0]
    try:
        published = entry["published"]
        title = entry["title"]
    except KeyError:
        published = ""
        title = ""
    for item in entry["links"]:
        if item.get("type", None) == "audio/mpeg":
            try:
                image = entry["image"]["href"]
            except KeyError:
                image = ""
            return [pod[0], image, item["href"], published, title]


def get_podcasts(db_connection, lock):
    podcasts = get_news_podcast_data(db_connection, lock)
    pool = multiprocessing.Pool(processes=len(podcasts))
    inputs = podcasts
    podcast_links = pool.map(parse_feed, inputs)
    return podcast_links