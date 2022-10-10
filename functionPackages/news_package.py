
def generate_news_db_tables(db_cursor, db_connection, lock):
    try:
        lock.acquire(True)
        db_cursor.execute("""CREATE TABLE if not exists rss(rss_name text, rss_link text)""")
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


def add_rss_data(rss_name, rss_link, db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""INSERT INTO rss VALUES(?, ?)""", (rss_name, rss_link))
    db_connection.commit()
    lock.release()
    return None
