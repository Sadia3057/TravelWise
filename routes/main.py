from flask import Blueprint, render_template, redirect, url_for, session
from functools import wraps
from app import get_db

main_bp = Blueprint("main", __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    trips = db.execute(
        "SELECT * FROM trips WHERE user_id=? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()
    # Wrap for template compatibility
    class User:
        username = session.get("username","")
    return render_template("dashboard.html", trips=trips, current_user=User())

@main_bp.route("/planner")
@login_required
def planner():
    return render_template("planner.html")

@main_bp.route("/itinerary")
@login_required
def itinerary():
    return render_template("itinerary.html")

@main_bp.route("/chatbot")
@login_required
def chatbot():
    return render_template("chatbot.html")