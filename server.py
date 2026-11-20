
import os
import getpass
import requests
import time
import sqlite3

from datetime import datetime, timezone
from pypresence import Presence
from flask import Flask, jsonify, send_from_directory, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
DATABASE = os.path.join(BASE_DIR, "community.db")

API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()

# DISCORD RPC
DISCORD_CLIENT_ID = "1573419528660979752"
rpc = None

# COMMUNITY
COMMUNITY_TOPICS = [
    "Music",
    "Gaming",
    "Entertainment",
    "Technology",
    "Other"
]


# DATABASE
def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL DEFAULT 'Guest',
                content TEXT NOT NULL,
                topic TEXT NOT NULL DEFAULT 'Other',
                created_at TEXT NOT NULL
            )
        """)

    print("Community database ready!")


# DISCORD RPC
def start_discord_rpc():
    global rpc

    try:
        print("\nConnecting to Discord RPC...")

        rpc = Presence(DISCORD_CLIENT_ID)
        rpc.connect()

        rpc.update(
            details="Using YT2007",
            state="Browsing classic YouTube",
            start=int(time.time())
        )

        print("Discord RPC connected!")

    except Exception as error:
        rpc = None
        print(f"Discord RPC unavailable: {error}")
        print("The server will continue normally.")


def stop_discord_rpc():
    global rpc

    if rpc:
        try:
            rpc.close()
            print("Discord RPC disconnected.")
        except Exception:
            pass


def configure():
    global API_KEY

    print("=" * 45)
    print("       YouTube Backend")
    print("=" * 45)

    if not API_KEY:
        print("\nQual API você deseja configurar?")
        print("1. YouTube Data API v3")

        choice = input("\nEscolha ou cole sua API Key: ").strip()

        if choice == "1":
            API_KEY = getpass.getpass(
                "\nCole sua API Key: "
            ).strip()

        elif choice.startswith("AIza"):
            API_KEY = choice

        else:
            print("Opção inválida.")
            raise SystemExit(1)

    if not API_KEY:
        print("API Key não informada.")
        raise SystemExit(1)

    print("\nOnde deseja hospedar?")
    print("1. Localhost")
    print("2. Rede local")

    host_choice = input("\nEscolha: ").strip()

    host = "0.0.0.0" if host_choice == "2" else "127.0.0.1"

    port_input = input("Porta [5000]: ").strip()
    port = int(port_input) if port_input else 5000

    return host, port


def youtube_request(endpoint, **params):
    params["key"] = API_KEY

    try:
        response = requests.get(
            f"{YOUTUBE_API}/{endpoint}",
            params=params,
            timeout=20
        )

        data = response.json()

        if not response.ok:
            return {
                "error": data.get("error", {}).get(
                    "message", "YouTube API error"
                )
            }, response.status_code

        return data, 200

    except requests.RequestException:
        return {"error": "Connection failed"}, 502


# VIDEOS
@app.route("/api/videos")
def videos():
    query = request.args.get("q", "").strip()
    channel_id = request.args.get("channelId", "").strip()

    params = {
        "part": "snippet",
        "type": "video",
        "maxResults": 20
    }

    if channel_id:
        params["channelId"] = channel_id
        params["order"] = "date"

        if query:
            params["q"] = query

    else:
        params["order"] = "relevance" if query else "viewCount"
        params["q"] = query or "popular videos"

    data, status = youtube_request("search", **params)
    return jsonify(data), status


# VIDEO DETAILS
@app.route("/api/video/<video_id>")
def video(video_id):
    data, status = youtube_request(
        "videos",
        part="snippet,statistics,contentDetails",
        id=video_id
    )

    return jsonify(data), status


# RELATED VIDEOS
@app.route("/api/related/<video_id>")
def related(video_id):
    data, status = youtube_request(
        "search",
        part="snippet",
        type="video",
        relatedToVideoId=video_id,
        maxResults=10
    )

    return jsonify(data), status


# CHANNEL LIST
@app.route("/api/channels")
def channels():
    query = request.args.get("q", "").strip()

    params = {
        "part": "snippet",
        "type": "channel",
        "maxResults": 20
    }

    if query:
        params["q"] = query

    data, status = youtube_request("search", **params)
    return jsonify(data), status


# CHANNEL DETAILS
@app.route("/api/channel/<channel_id>")
def channel(channel_id):
    data, status = youtube_request(
        "channels",
        part="snippet,statistics,contentDetails",
        id=channel_id
    )

    return jsonify(data), status


# COMMUNITY - GET POSTS
@app.route("/api/posts", methods=["GET"])
def get_posts():
    topic = request.args.get("topic", "").strip()

    try:
        with get_db() as db:
            if topic and topic != "All":
                posts = db.execute(
                    """
                    SELECT * FROM posts
                    WHERE topic = ?
                    ORDER BY id DESC
                    LIMIT 100
                    """,
                    (topic,)
                ).fetchall()
            else:
                posts = db.execute(
                    """
                    SELECT * FROM posts
                    ORDER BY id DESC
                    LIMIT 100
                    """
                ).fetchall()

        return jsonify({
            "items": [dict(post) for post in posts]
        })

    except sqlite3.Error as error:
        print("Database error:", error)
        return jsonify({"error": "Could not load posts"}), 500


# COMMUNITY - CREATE POST
@app.route("/api/posts", methods=["POST"])
def create_post():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request"}), 400

    content = data.get("content", "")
    topic = data.get("topic", "Other")

    if not isinstance(content, str):
        return jsonify({"error": "Invalid post content"}), 400

    content = content.strip()

    if not content:
        return jsonify({"error": "Post cannot be empty"}), 400

    if len(content) > 1000:
        return jsonify({"error": "Post is too long"}), 400

    if not isinstance(topic, str) or topic not in COMMUNITY_TOPICS:
        topic = "Other"

    created_at = datetime.now(timezone.utc).isoformat()

    try:
        with get_db() as db:
            cursor = db.execute(
                """
                INSERT INTO posts (author, content, topic, created_at)
                VALUES (?, ?, ?, ?)
                """,
                ("Guest", content, topic, created_at)
            )

            post_id = cursor.lastrowid

            post = db.execute(
                "SELECT * FROM posts WHERE id = ?",
                (post_id,)
            ).fetchone()

        return jsonify({
            "success": True,
            "post": dict(post)
        }), 201

    except sqlite3.Error as error:
        print("Database error:", error)
        return jsonify({"error": "Could not save post"}), 500


# HOME
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


# STATIC FILES
@app.route("/<path:path>")
def files(path):
    return send_from_directory(BASE_DIR, path)


if __name__ == "__main__":
    HOST, PORT = configure()

    init_database()

    print("\nBackend iniciado!")
    print(f"http://127.0.0.1:{PORT}")

    start_discord_rpc()

    try:
        app.run(
            host=HOST,
            port=PORT,
            debug=False
        )
    finally:
        stop_discord_rpc()
