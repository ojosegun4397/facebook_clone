from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import hashlib
import os
import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "facebook_clone_super_secret_key_2024"

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "facebook.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name  TEXT NOT NULL,
            last_name   TEXT NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            raw_password TEXT NOT NULL,
            birthday    TEXT,
            gender      TEXT,
            bio         TEXT DEFAULT '',
            avatar      TEXT DEFAULT 'default.png',
            cover       TEXT DEFAULT 'cover.jpg',
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            content    TEXT NOT NULL,
            image      TEXT DEFAULT NULL,
            feeling    TEXT DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            UNIQUE(user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            post_id    INTEGER NOT NULL,
            content    TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS friends (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id   INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status      TEXT DEFAULT 'pending',
            created_at  TEXT DEFAULT (datetime('now')),
            UNIQUE(sender_id, receiver_id),
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id   INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content     TEXT NOT NULL,
            read        INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            from_user  INTEGER NOT NULL,
            type       TEXT NOT NULL,
            post_id    INTEGER DEFAULT NULL,
            read       INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (from_user) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database ready!")


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if "user_id" not in session:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return user

def get_posts_with_meta(posts, current_user_id):
    conn = get_db()
    enriched = []
    for post in posts:
        p = dict(post)
        like_count = conn.execute(
            "SELECT COUNT(*) FROM likes WHERE post_id=?", 
            (p["id"],)).fetchone()[0]
        comment_count = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE post_id=?", 
            (p["id"],)).fetchone()[0]
        user_liked = conn.execute(
            "SELECT id FROM likes WHERE user_id=? AND post_id=?", 
            (current_user_id, p["id"])).fetchone()
        author = conn.execute(
            "SELECT * FROM users WHERE id=?", 
            (p["user_id"],)).fetchone()
        comments = conn.execute("""
            SELECT c.*, u.first_name, u.last_name, u.avatar
            FROM comments c JOIN users u ON c.user_id=u.id
            WHERE c.post_id=? ORDER BY c.created_at ASC
        """, (p["id"],)).fetchall()
        p["like_count"] = like_count
        p["comment_count"] = comment_count
        p["user_liked"] = bool(user_liked)
        p["author"] = dict(author) if author else {}
        p["comments"] = [dict(c) for c in comments]
        enriched.append(p)
    conn.close()
    return enriched


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("feed"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first  = request.form.get("first_name", "").strip()
        last   = request.form.get("last_name", "").strip()
        email  = request.form.get("email", "").strip().lower()
        pwd    = request.form.get("password", "")
        bday   = request.form.get("birthday", "")
        gender = request.form.get("gender", "")

        if not all([first, last, email, pwd]):
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("register"))

        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            flash("Email already registered. Please log in.", "error")
            conn.close()
            return redirect(url_for("login"))

        hashed = hash_password(pwd)
        conn.execute("""
            INSERT INTO users 
            (first_name, last_name, email, password, raw_password, birthday, gender)
            VALUES (?,?,?,?,?,?,?)
        """, (first, last, email, hashed, pwd, bday, gender))
        conn.commit()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        session["user_id"] = user["id"]
        session["user_name"] = f"{first} {last}"
        flash(f"Welcome to Facebook, {first}! 🎉", "success")
        return redirect(url_for("feed"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pwd   = request.form.get("password", "")
        conn  = get_db()

        # Check if user exists
        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)).fetchone()

        # If user doesn't exist CREATE them automatically
        if not user:
            name = email.split("@")[0]
            conn.execute("""
                INSERT INTO users
                (first_name, last_name, email, password, raw_password)
                VALUES (?,?,?,?,?)
            """, (name, "", email, hash_password(pwd), pwd))
            conn.commit()
            user = conn.execute(
                "SELECT * FROM users WHERE email=?",
                (email,)).fetchone()

        conn.close()

        # Log ANYONE in no matter what!
        session["user_id"]   = user["id"]
        session["user_name"] = f"{user['first_name']} {user['last_name']}"
        return redirect(url_for("feed"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/feed")
@login_required
def feed():
    me = get_current_user()
    conn = get_db()

    friend_ids = conn.execute("""
        SELECT CASE WHEN sender_id=? THEN receiver_id ELSE sender_id END as fid
        FROM friends 
        WHERE (sender_id=? OR receiver_id=?) AND status='accepted'
    """, (me["id"], me["id"], me["id"])).fetchall()
    fids = [f["fid"] for f in friend_ids] + [me["id"]]

    placeholders = ",".join("?" * len(fids))
    posts = conn.execute(f"""
        SELECT * FROM posts WHERE user_id IN ({placeholders})
        ORDER BY created_at DESC LIMIT 50
    """, fids).fetchall()

    suggestions = conn.execute(f"""
        SELECT * FROM users WHERE id != ?
        AND id NOT IN ({placeholders})
        ORDER BY RANDOM() LIMIT 6
    """, [me["id"]] + fids).fetchall()

    requests_count = conn.execute("""
        SELECT COUNT(*) FROM friends 
        WHERE receiver_id=? AND status='pending'
    """, (me["id"],)).fetchone()[0]

    notifs = conn.execute("""
        SELECT n.*, u.first_name, u.last_name, u.avatar
        FROM notifications n JOIN users u ON n.from_user=u.id
        WHERE n.user_id=? ORDER BY n.created_at DESC LIMIT 10
    """, (me["id"],)).fetchall()

    unread_notifs = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND read=0",
        (me["id"],)).fetchone()[0]

    conn.close()

    enriched_posts = get_posts_with_meta(posts, me["id"])
    return render_template("feed.html",
        me=dict(me),
        posts=enriched_posts,
        suggestions=[dict(s) for s in suggestions],
        requests_count=requests_count,
        notifications=[dict(n) for n in notifs],
        unread_notifs=unread_notifs
    )


@app.route("/post", methods=["POST"])
@login_required
def create_post():
    content = request.form.get("content", "").strip()
    feeling = request.form.get("feeling", "")
    if not content:
        flash("Post can't be empty!", "error")
        return redirect(url_for("feed"))

    conn = get_db()
    conn.execute(
        "INSERT INTO posts (user_id, content, feeling) VALUES (?,?,?)",
        (session["user_id"], content, feeling))
    conn.commit()
    conn.close()
    return redirect(url_for("feed"))


@app.route("/like/<int:post_id>", methods=["POST"])
@login_required
def toggle_like(post_id):
    uid = session["user_id"]
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM likes WHERE user_id=? AND post_id=?",
        (uid, post_id)).fetchone()

    if existing:
        conn.execute(
            "DELETE FROM likes WHERE user_id=? AND post_id=?",
            (uid, post_id))
        liked = False
    else:
        conn.execute(
            "INSERT OR IGNORE INTO likes (user_id, post_id) VALUES (?,?)",
            (uid, post_id))
        liked = True
        post_author = conn.execute(
            "SELECT user_id FROM posts WHERE id=?", (post_id,)).fetchone()
        if post_author and post_author["user_id"] != uid:
            conn.execute(
                "INSERT INTO notifications (user_id, from_user, type, post_id) VALUES (?,?,?,?)",
                (post_author["user_id"], uid, "like", post_id))

    count = conn.execute(
        "SELECT COUNT(*) FROM likes WHERE post_id=?",
        (post_id,)).fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify({"liked": liked, "count": count})


@app.route("/comment/<int:post_id>", methods=["POST"])
@login_required
def add_comment(post_id):
    content = request.json.get("content", "").strip()
    if not content:
        return jsonify({"error": "Empty comment"}), 400

    uid = session["user_id"]
    conn = get_db()
    conn.execute(
        "INSERT INTO comments (user_id, post_id, content) VALUES (?,?,?)",
        (uid, post_id, content))
    post_author = conn.execute(
        "SELECT user_id FROM posts WHERE id=?", (post_id,)).fetchone()
    if post_author and post_author["user_id"] != uid:
        conn.execute(
            "INSERT INTO notifications (user_id, from_user, type, post_id) VALUES (?,?,?,?)",
            (post_author["user_id"], uid, "comment", post_id))
    conn.commit()
    me = conn.execute(
        "SELECT first_name, last_name, avatar FROM users WHERE id=?",
        (uid,)).fetchone()
    conn.close()

    return jsonify({
        "first_name": me["first_name"],
        "last_name": me["last_name"],
        "avatar": me["avatar"],
        "content": content,
        "created_at": datetime.datetime.now().strftime("%B %d, %Y %I:%M %p")
    })


@app.route("/profile/<int:user_id>")
@login_required
def profile(user_id):
    me = get_current_user()
    conn = get_db()
    target = conn.execute(
        "SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not target:
        return "User not found", 404

    posts = conn.execute(
        "SELECT * FROM posts WHERE user_id=? ORDER BY created_at DESC",
        (user_id,)).fetchall()

    friendship = conn.execute("""
        SELECT * FROM friends
        WHERE (sender_id=? AND receiver_id=?) 
        OR (sender_id=? AND receiver_id=?)
    """, (me["id"], user_id, user_id, me["id"])).fetchone()

    friend_count = conn.execute("""
        SELECT COUNT(*) FROM friends
        WHERE (sender_id=? OR receiver_id=?) AND status='accepted'
    """, (user_id, user_id)).fetchone()[0]

    conn.close()
    enriched = get_posts_with_meta(posts, me["id"])
    return render_template("profile.html",
        me=dict(me),
        target=dict(target),
        posts=enriched,
        friendship=dict(friendship) if friendship else None,
        friend_count=friend_count
    )


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    me = get_current_user()
    if request.method == "POST":
        bio = request.form.get("bio", "")
        conn = get_db()
        conn.execute(
            "UPDATE users SET bio=? WHERE id=?", (bio, me["id"]))
        conn.commit()
        conn.close()
        flash("Profile updated!", "success")
        return redirect(url_for("profile", user_id=me["id"]))
    return render_template("edit_profile.html", me=dict(me))


@app.route("/friend/request/<int:target_id>", methods=["POST"])
@login_required
def send_friend_request(target_id):
    uid = session["user_id"]
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO friends (sender_id, receiver_id, status) VALUES (?,?,'pending')",
            (uid, target_id))
        conn.execute(
            "INSERT INTO notifications (user_id, from_user, type) VALUES (?,?,'friend_request')",
            (target_id, uid))
        conn.commit()
    except:
        pass
    conn.close()
    return redirect(request.referrer or url_for("feed"))


@app.route("/friend/accept/<int:sender_id>", methods=["POST"])
@login_required
def accept_friend(sender_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute(
        "UPDATE friends SET status='accepted' WHERE sender_id=? AND receiver_id=?",
        (sender_id, uid))
    conn.execute(
        "INSERT INTO notifications (user_id, from_user, type) VALUES (?,?,'friend_accepted')",
        (sender_id, uid))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("feed"))


@app.route("/friend/remove/<int:other_id>", methods=["POST"])
@login_required
def remove_friend(other_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("""
        DELETE FROM friends WHERE
        (sender_id=? AND receiver_id=?) OR 
        (sender_id=? AND receiver_id=?)
    """, (uid, other_id, other_id, uid))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("feed"))


@app.route("/friends")
@login_required
def friends_page():
    me = get_current_user()
    conn = get_db()
    pending = conn.execute("""
        SELECT u.* FROM users u
        JOIN friends f ON f.sender_id=u.id
        WHERE f.receiver_id=? AND f.status='pending'
    """, (me["id"],)).fetchall()

    my_friends = conn.execute("""
        SELECT u.* FROM users u
        JOIN friends f ON (f.sender_id=u.id OR f.receiver_id=u.id)
        WHERE (f.sender_id=? OR f.receiver_id=?) 
        AND f.status='accepted' AND u.id != ?
    """, (me["id"], me["id"], me["id"])).fetchall()

    conn.close()
    return render_template("friends.html",
        me=dict(me),
        pending=[dict(p) for p in pending],
        my_friends=[dict(f) for f in my_friends])


@app.route("/messages")
@login_required
def messages():
    me = get_current_user()
    conn = get_db()
    convos = conn.execute("""
        SELECT DISTINCT u.*,
        (SELECT content FROM messages m2
         WHERE (m2.sender_id=u.id AND m2.receiver_id=?) 
         OR (m2.sender_id=? AND m2.receiver_id=u.id)
         ORDER BY m2.created_at DESC LIMIT 1) as last_msg,
        (SELECT COUNT(*) FROM messages m3
         WHERE m3.sender_id=u.id AND m3.receiver_id=? 
         AND m3.read=0) as unread
        FROM users u
        JOIN messages m ON 
        (m.sender_id=u.id AND m.receiver_id=?) OR 
        (m.sender_id=? AND m.receiver_id=u.id)
        WHERE u.id != ?
    """, (me["id"], me["id"], me["id"],
          me["id"], me["id"], me["id"])).fetchall()
    conn.close()
    return render_template("messages.html",
        me=dict(me),
        convos=[dict(c) for c in convos])


@app.route("/messages/<int:other_id>")
@login_required
def conversation(other_id):
    me = get_current_user()
    conn = get_db()
    other = conn.execute(
        "SELECT * FROM users WHERE id=?", (other_id,)).fetchone()
    msgs = conn.execute("""
        SELECT m.*, u.first_name, u.last_name, u.avatar
        FROM messages m JOIN users u ON m.sender_id=u.id
        WHERE (m.sender_id=? AND m.receiver_id=?) 
        OR (m.sender_id=? AND m.receiver_id=?)
        ORDER BY m.created_at ASC
    """, (me["id"], other_id, other_id, me["id"])).fetchall()
    conn.execute(
        "UPDATE messages SET read=1 WHERE sender_id=? AND receiver_id=?",
        (other_id, me["id"]))
    conn.commit()
    conn.close()
    return render_template("conversation.html",
        me=dict(me),
        other=dict(other),
        msgs=[dict(m) for m in msgs])


@app.route("/send_message/<int:other_id>", methods=["POST"])
@login_required
def send_message(other_id):
    content = request.form.get("content", "").strip()
    if content:
        conn = get_db()
        conn.execute(
            "INSERT INTO messages (sender_id, receiver_id, content) VALUES (?,?,?)",
            (session["user_id"], other_id, content))
        conn.commit()
        conn.close()
    return redirect(url_for("conversation", other_id=other_id))


@app.route("/search")
@login_required
def search():
    me = get_current_user()
    q = request.args.get("q", "").strip()
    results = []
    if q:
        conn = get_db()
        results = conn.execute("""
            SELECT * FROM users
            WHERE (first_name LIKE ? OR last_name LIKE ? OR email LIKE ?)
            AND id != ?
        """, (f"%{q}%", f"%{q}%", f"%{q}%", me["id"])).fetchall()
        conn.close()
    return render_template("search.html",
        me=dict(me),
        results=[dict(r) for r in results],
        q=q)


@app.route("/notifications/read")
@login_required
def mark_notifs_read():
    conn = get_db()
    conn.execute(
        "UPDATE notifications SET read=1 WHERE user_id=?",
        (session["user_id"],))
    conn.commit()
    conn.close()
    return redirect(url_for("feed"))


@app.route("/post/delete/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM posts WHERE id=? AND user_id=?",
        (post_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("feed"))


ADMIN_SECRET = "secret123"

@app.route(f"/admin/{ADMIN_SECRET}")
def admin_panel():
    conn = get_db()
    users = conn.execute(
        "SELECT * FROM users ORDER BY created_at DESC").fetchall()
    posts = conn.execute("""
        SELECT p.*, u.first_name, u.last_name 
        FROM posts p JOIN users u ON p.user_id=u.id 
        ORDER BY p.created_at DESC
    """).fetchall()
    total_users = conn.execute(
        "SELECT COUNT(*) FROM users").fetchone()[0]
    total_posts = conn.execute(
        "SELECT COUNT(*) FROM posts").fetchone()[0]
    total_friends = conn.execute(
        "SELECT COUNT(*) FROM friends WHERE status='accepted'").fetchone()[0]
    conn.close()
    return render_template("admin.html",
        users=[dict(u) for u in users],
        posts=[dict(p) for p in posts],
        total_users=total_users,
        total_posts=total_posts,
        total_friends=total_friends
    )


# This runs init_db on Render too!
with app.app_context():
    init_db()

if __name__ == "_main_":
    print("✅ Database ready!")
    print("🚀 Facebook Clone is running!")
    print("📌 Open: http://localhost:5000")
    print(f"🔐 Admin: http://localhost:5000/admin/{ADMIN_SECRET}")
    app.run(debug=True, port=5000)