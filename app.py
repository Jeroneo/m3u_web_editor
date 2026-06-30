from flask import Flask, render_template, request, jsonify
import requests
import json
import os

from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)


STORAGE_FILE = "selected_channels.json"

EXPORT_PATH = (
    r"./my_playlist.m3u"
)


# Create storage file
if not os.path.exists(STORAGE_FILE):

    with open(STORAGE_FILE, "w") as f:
        json.dump([], f)



def load_selected():

    with open(STORAGE_FILE, "r") as f:
        return json.load(f)



def save_selected(data):

    with open(STORAGE_FILE, "w") as f:
        json.dump(
            data,
            f,
            indent=4
        )



def generate_m3u():

    print("Generating playlist...")


    try:

        playlist = requests.get(
            "https://iptv-org.github.io/iptv/index.m3u"
        ).text


        selected = load_selected()


        lines = playlist.splitlines()


        output = "#EXTM3U\n"


        for i in range(len(lines)-1):

            if lines[i].startswith("#EXTINF"):

                url = lines[i+1].strip()


                if url in selected:

                    output += (
                        lines[i]
                        + "\n"
                        + url
                        + "\n"
                    )



        with open(
            EXPORT_PATH,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(output)



        print(
            "Generated",
            len(selected),
            "channels"
        )


    except Exception as e:

        print(
            "Generation error:",
            e
        )





scheduler = BackgroundScheduler()


scheduler.add_job(
    generate_m3u,
    trigger="interval",
    days=1
)


scheduler.start()





@app.route("/")
def index():

    return render_template(
        "index.html"
    )





@app.route(
    "/api/channels",
    methods=["GET"]
)
def get_channels():

    return jsonify(
        load_selected()
    )





@app.route(
    "/api/channels",
    methods=["POST"]
)
def save_channels():

    data = request.json

    save_selected(data)


    print(
        "Saved",
        len(data),
        "channels"
    )


    return jsonify(
        {
            "status":"success"
        }
    )





@app.route(
    "/api/generate",
    methods=["POST"]
)
def force_generate():

    generate_m3u()

    return jsonify(
        {
            "status":"success"
        }
    )





if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )