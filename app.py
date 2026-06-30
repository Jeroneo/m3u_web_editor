from flask import Flask, render_template, request, jsonify
import requests
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

STORAGE_FILE = "selected_channels.json"
EXPORT_PATH = r"./my_playlist.m3u"

STREAMS_URL = "https://iptv-org.github.io/api/streams.json"
CHANNELS_URL = "https://iptv-org.github.io/api/channels.json"
FEEDS_URL = "https://iptv-org.github.io/api/feeds.json"
LANGUAGES_URL = "https://iptv-org.github.io/api/languages.json"

# Create storage file
if not os.path.exists(STORAGE_FILE):
    with open(STORAGE_FILE, "w") as f:
        json.dump([], f)


def load_selected():
    with open(STORAGE_FILE, "r") as f:
        return json.load(f)


def save_selected(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=4)


def build_channel_index():
    """
    Joins streams.json + channels.json + feeds.json + languages.json
    so URLs and language info stay consistent.
    """
    streams = requests.get(STREAMS_URL).json()
    channels = requests.get(CHANNELS_URL).json()
    feeds = requests.get(FEEDS_URL).json()
    languages = requests.get(LANGUAGES_URL).json()

    channel_by_id = {ch["id"]: ch for ch in channels}
    language_name_by_code = {lang["code"]: lang["name"] for lang in languages}

    feed_by_channel_and_id = {}
    first_feed_languages_by_channel = {}

    for feed in feeds:
        feed_by_channel_and_id[(feed["channel"], feed["id"])] = feed
        if feed["channel"] not in first_feed_languages_by_channel:
            first_feed_languages_by_channel[feed["channel"]] = feed.get("languages", [])

    indexed = []
    for stream in streams:
        url = stream.get("url")
        channel_id = stream.get("channel")

        if not url or not channel_id:
            continue

        channel_info = channel_by_id.get(channel_id)
        if not channel_info:
            continue

        categories = channel_info.get("categories") or []
        category = categories[0] if categories else "Uncategorized"

        feed_key = (channel_id, stream.get("feed") or "")
        feed = feed_by_channel_and_id.get(feed_key)

        language_codes = (
            (feed.get("languages") if feed else None)
            or first_feed_languages_by_channel.get(channel_id)
            or []
        )

        language_names = [language_name_by_code.get(code, code) for code in language_codes]
        name = stream.get("title") or channel_info.get("name")

        indexed.append({
            "url": url,
            "name": name,
            "category": category,
            "languages": language_names
        })

    return indexed


def generate_m3u():
    print("Generating playlist...")
    try:
        channels = build_channel_index()
        selected = load_selected()
        selected_set = set(selected)

        output = "#EXTM3U\n"
        for channel in channels:
            if channel["url"] not in selected_set:
                continue

            lang_attr = ",".join(channel["languages"])
            extinf = (
                '#EXTINF:-1 group-title="{category}" tvg-language="{lang}",{name}'
                .format(
                    category=channel["category"],
                    lang=lang_attr,
                    name=channel["name"]
                )
            )
            output += extinf + "\n" + channel["url"] + "\n"

        with open(EXPORT_PATH, "w", encoding="utf-8") as f:
            f.write(output)

        print(f"Generated {len(selected)} channels")

    except Exception as e:
        print(f"Generation error: {e}")


# Scheduler setup
scheduler = BackgroundScheduler()
scheduler.add_job(generate_m3u, trigger="interval", days=1)
scheduler.start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/channels", methods=["GET"])
def get_channels():
    return jsonify(load_selected())


@app.route("/api/channels", methods=["POST"])
def save_channels():
    data = request.json
    save_selected(data)
    print(f"Saved {len(data)} channels")
    return jsonify({"status": "success"})


@app.route("/api/generate", methods=["POST"])
def force_generate():
    generate_m3u()
    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)