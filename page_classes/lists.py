from flask_restful import Resource
from flask import render_template, make_response, request
from functionPackages.misc import *

logger = logging.getLogger(__name__)


class Lists(Resource):
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
        lists = {}

        self.lock.acquire(True)
        self.c.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("lists",))
        list_names = [x.strip() for x in self.c.fetchall()[0][1].split(",")]
        self.lock.release()

        self.lock.acquire(True)
        for listName in list_names:
            self.c.execute("""SELECT * FROM lists WHERE type = ? """, (listName,))
            data = self.c.fetchall()
            lists[listName] = sorted(sorted([(name, done, note) for name, done, list_type, note in data]),
                                     key=lambda x: x[1])
        self.lock.release()

        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('lists.html', lists=lists, readList=lists["book"],
                                             animeList=lists["anime"], movieList=lists["movie"],
                                             bucketList=lists["bucketList"],
                                             toLearnList=lists["toLearn"],
                                             pageTheme=page_theme), 200, headers)

    def post(self):
        if not session.get("name"):
            return "user is not logged in", 401
        args = self.parser.parse_args()
        if args['action'] == "create list":
            list_name = eval(args['value'])["listName"]
            self.lock.acquire(True)
            self.c.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("lists",))
            list_names = [x.strip() for x in self.c.fetchall()[0][1].split(",")] + [list_name]
            self.c.execute("UPDATE settings SET value = ? WHERE parameter = ?", (",".join(list_names), "lists",))
            self.conn.commit()
            self.lock.release()
            return "Done", 200

        if args['action'] == "delete list":
            list_name = eval(args['value'])["listName"]
            self.lock.acquire(True)
            self.c.execute("""SELECT * FROM settings WHERE parameter = ?  """, ("lists",))
            list_names = [x.strip() for x in self.c.fetchall()[0][1].split(",")]
            list_names.remove(list_name)
            self.c.execute("UPDATE settings SET value = ? WHERE parameter = ?", (",".join(list_names), 'lists',))
            self.c.execute("""DELETE from lists where type = ? """, (list_name,))
            self.conn.commit()
            self.lock.release()
            return "Done", 200

        self.lock.acquire(True)
        if args['action'] == "delete":
            value_dict = eval((args['value']))
            logger.info(f"deleted {value_dict['name'].lower()} from {value_dict['type']}")
            self.c.execute("""DELETE from lists where name = ? and type = ?  """,
                           (value_dict["name"].lower(), value_dict["type"]))
        else:
            value_dict = eval((args['value']))
            logger.info(f"added {value_dict['name'].lower()} to {value_dict['type']} as {value_dict['done']} ")
            self.c.execute("""DELETE from lists where name = ? and type = ? """,
                           (value_dict["name"].lower(), value_dict["type"]))
            self.c.execute("""INSERT INTO lists VALUES(?, ?, ?, ?)""",
                           (value_dict["name"].lower(), value_dict["done"], value_dict["type"], value_dict["notes"]))
        self.conn.commit()
        self.lock.release()
        return "Done", 200
