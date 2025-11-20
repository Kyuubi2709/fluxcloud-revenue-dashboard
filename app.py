from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import os
import threading
import time
import json

BASE_DIR = os.path.dirname(__file__)
CACHE_FILE = os.path.join(BASE_DIR, "cache", "stats.json")

app = Flask(__name__, static_folder="static", template_folder="templates")

# Secret key for session
app.secret_key = "fluxcloud_dashboard_secret"

# Hardcoded login
LOGIN_USER = "fluxcloud"
LOGIN_PASS = "fluxcloud123"


# ---------------------------
# AUTH
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "")
        pw = request.form.get("password", "")

        if user == LOGIN_USER and pw == LOGIN_PASS:
            session["logged_in"] = True
            return redirect(url_for("home"))

        return render_template("login.html", error="Invalid login")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------
# CACHE-BASED /stats
# ---------------------------
@app.route("/stats")
def stats():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if not os.path.exists(CACHE_FILE):
        from update_cache import update_cache
        update_cache()

    try:
        with open(CACHE_FILE, "r") as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify({"error": "Cache unavailable"}), 500


# ---------------------------
# MANUAL REFRESH
# ---------------------------
@app.route("/refresh", methods=["POST"])
def refresh():
    if not session.get("logged_in"):
        return jsonify({"status": "unauthorized"}), 403

    last_refresh_file = os.path.join(BASE_DIR, "cache", "last_refresh.txt")
    now = time.time()
    cooldown = 60 * 15  # 15 minutes

    if os.path.exists(last_refresh_file):
        last_refresh = float(open(last_refresh_file).read().strip())
        if now - last_refresh < cooldown:
            remaining = int(cooldown - (now - last_refresh))
            return jsonify({"status": "cooldown", "message": f"Try again in {remaining}s"})

    os.makedirs(os.path.dirname(last_refresh_file), exist_ok=True)
    with open(last_refresh_file, "w") as f:
        f.write(str(now))

    def background():
        from update_cache import update_cache
        update_cache()

    threading.Thread(target=background, daemon=True).start()
    return jsonify({"status": "ok", "message": "Refresh started"})


# ---------------------------
# HOME
# ---------------------------
@app.route("/")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
