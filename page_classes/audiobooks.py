from flask_restful import Resource
from flask import render_template, make_response

from functionPackages.misc import *

logger = logging.getLogger(__name__)


class Audiobooks(Resource):
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
        path = "static/audiobooks/"
        try:
            audiobooks, metadata = get_audiobooks(path)
        except Exception as err:
            logger.error(err)
            audiobooks = metadata = {}
        print(metadata["Malmo Queer Stories Archive"])
        logger.info("---- page prepared in  %s seconds ---" % (time.time() - start_time))
        return make_response(
            render_template('audiobooks.html', audiobooks=audiobooks, metadata=metadata,
                            pageTheme=page_theme), 200, headers)

    def post(self):
        if not session.get("name"):
            return "user is not logged in", 401

        args = self.parser.parse_args()
        value = json.loads(args['value'])
        metadata_file_path = "static/audiobooks/" + value["author"] + "/" + value["book"] + "/metadata.json"
        with open(metadata_file_path, "r") as metadataFile:
            data = json.load(metadataFile)
            data["chapter " + value["chapter"]]["timestamp"] = \
                value.get("timestamp", data["chapter " + value["chapter"]]["timestamp"])
            data["chapter " + value["chapter"]]["progress"] = \
                value.get("progress", data["chapter " + value["chapter"]]["progress"])
            data["chapter " + value["chapter"]]["notes"] = \
                value.get("notes", data["chapter " + value["chapter"]].get("notes", ""))
        metadataFile.close()
        with open(metadata_file_path, "w") as metadataFile:
            json.dump(data, metadataFile)
        metadataFile.close()
        return "Done", 200
