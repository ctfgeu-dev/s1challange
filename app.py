from flask import Flask, request, redirect, url_for, render_template, session, jsonify, abort
import base64
import os
import hashlib

app = Flask(__name__)
app.secret_key = "s3cr3t_k3y_ctf_2024"

# --- User store (intentionally flawed logic) ---
USERS = {
    "admin": hashlib.md5(b"superSecure!99").hexdigest(),  # md5: a3f1c2d77e9b04e8a1234abcd5678ef0 (fake)
    "guest": hashlib.md5(b"guest").hexdigest(),
}

def check_login(username, password):
    """
    Checks credentials. Has a subtle logic flaw:
    If the username exists AND the md5 of the password matches - OR -
    if the password field is literally the stored hash string, it passes.
    This simulates a type-confusion / double-hash bypass.
    """
    if username in USERS:
        pw_hash = hashlib.md5(password.encode()).hexdigest()
        stored = USERS[username]
        # BUG: also accepts the raw hash string as a valid password (hash == hash of hash is never true,
        # but comparing password directly to stored hash is a logic flaw)
        if pw_hash == stored or password == stored:
            return True
    return False


@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if check_login(username, password):
            session["user"] = username
            session["role"] = "admin" if username == "admin" else "guest"
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid credentials."

    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"])


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -----------------------------------------------
# LAYER 2: Hidden API endpoint (discovered via HTML comment hint)
# The comment hints at /api/status — that returns a base64-encoded path
# -----------------------------------------------
@app.route("/api/status")
def api_status():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # Encoded hint: points to /api/secret/retrieve
    hint_raw = "/api/secret/retrieve"
    encoded_hint = base64.b64encode(hint_raw.encode()).decode()

    return jsonify({
        "status": "operational",
        "version": "1.0.4",
        "build": "prod-2024",
        "debug_ref": encoded_hint   # <-- player must decode this
    })


# -----------------------------------------------
# LAYER 3: File retrieval endpoint
# Reads secret/data.txt and returns its content (encoded flag)
# -----------------------------------------------
@app.route("/api/secret/retrieve")
def secret_retrieve():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    secret_path = os.path.join(os.path.dirname(__file__), "secret", "data.txt")

    if not os.path.exists(secret_path):
        return jsonify({"error": "File not found"}), 404

    with open(secret_path, "r") as f:
        raw = f.read().strip()

    # The file contains a double-encoded flag. We return it as-is.
    # Player must decode it themselves.
    return jsonify({
        "classification": "TOP SECRET",
        "payload": raw,
        "encoding": "see comment in /dashboard source"
    })


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)