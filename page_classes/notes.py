from flask_restful import Resource
from flask import render_template, make_response
import time
from functionPackages.misc import *

logger = logging.getLogger(__name__)


class Notes(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conn = kwargs["conn"]
        self.c = kwargs["c"]
        self.lock = kwargs["lock"]
        self.parser = kwargs["parser"]

    def get(self):
        start_time = time.time()
        headers = {'Content-Type': 'text/html'}
        page_theme = fetch_setting_param_from_db(self.c, "Theme", self.lock)
        notebooks = fetch_notebooks(self.c, self.lock)
        photo_dir = os.getcwd() + "/static/photos/notebookPhotos"
        photos = {}
        for root, dirs, files in os.walk(photo_dir):
            if len(root.split("notebookPhotos/")) > 1:
                for filename in files:
                    notebook_name = root.split("notebookPhotos/")[1]
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.mp4')):
                        photos[notebook_name] = photos.get(notebook_name, []) + [filename]
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(render_template('notes.html', pageTheme=page_theme, Notebooks=notebooks, photos=photos),
                             200, headers)

    def post(self):
        args = self.parser.parse_args()
        value_dict = eval((args['value']))
        if args['action'] == "delete":
            self.lock.acquire(True)
            if value_dict.get("chapter", None) is not None:
                logger.info(f"deleting the chapter {value_dict['chapter']} from notebook: {value_dict['notebook']}")
                self.c.execute("""DELETE from Notes where Notebook = ? and  Chapter = ? """,
                               (value_dict["notebook"], value_dict["chapter"],))
            else:
                logger.info(f"deleting the notebook: {value_dict['notebook']}")
                self.c.execute("""DELETE from Notes where Notebook = ? """, (value_dict["notebook"],))
            self.conn.commit()
            self.lock.release()
        elif args['action'] == "rename":
            parsed_json = json.loads(args['value'])
            if (parsed_json["type"] == "noteBookName") and (parsed_json["oldName"] != parsed_json["newName"]):
                self.lock.acquire(True)
                self.c.execute("""SELECT * FROM Notes WHERE Notebook = ?""", (parsed_json["oldName"],))
                all_notes = self.c.fetchall()
                self.lock.release()

                self.lock.acquire(True)
                for x in all_notes:
                    content = x[2]
                    # rename the folder that holds the files inside the references of it...
                    while "static/photos/notebookPhotos/" + parsed_json["oldName"] + "/" in content:
                        content = content.replace("static/photos/notebookPhotos/" + parsed_json["oldName"] + "/",
                                                  "static/photos/notebookPhotos/" + parsed_json["newName"] + "/")
                    self.c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (parsed_json["newName"], x[1], content))
                self.conn.commit()
                self.lock.release()

                self.lock.acquire(True)
                for x in all_notes:
                    self.c.execute("""DELETE from Notes where Notebook = ? and Chapter = ? and content = ? """,
                                   (parsed_json["oldName"], x[1], x[2]))
                self.conn.commit()
                self.lock.release()

                # rename the folder that holds the files
                if os.path.isdir("./static/photos/notebookPhotos/" + parsed_json["oldName"]):
                    os.rename("./static/photos/notebookPhotos/" + parsed_json["oldName"],
                              "./static/photos/notebookPhotos/" + parsed_json["newName"])
                return "all good!", 200

            if (parsed_json["type"] == "chapterName") and (parsed_json["oldName"] != parsed_json["newName"]):
                self.lock.acquire(True)
                self.c.execute("""SELECT * FROM Notes WHERE Notebook = ? and Chapter = ? """,
                               (parsed_json["noteBookName"], parsed_json["oldName"],))
                all_notes = self.c.fetchall()
                for x in all_notes:
                    self.c.execute("""INSERT into Notes VALUES(?, ?, ?)  """, (x[0], parsed_json["newName"], x[2]))
                    self.c.execute("""DELETE from Notes where Notebook = ? and Chapter = ? and content = ? """,
                                   (x[0], parsed_json["oldName"], x[2]))
                self.conn.commit()
                self.lock.release()
                return "all good!", 200
        else:
            self.lock.acquire(True)
            self.c.execute("""DELETE from Notes where Notebook = ? and Chapter = ?  """,
                           (value_dict["notebook"], value_dict["chapter"]))
            self.c.execute("""INSERT into Notes VALUES(?, ?, ?)  """,
                           (value_dict["notebook"], value_dict["chapter"], value_dict['entry']))
            self.conn.commit()
            self.lock.release()
        return "nothing here!", 200
