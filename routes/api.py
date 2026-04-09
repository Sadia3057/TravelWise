from flask import Blueprint, request, jsonify, session, g
from functools import wraps
import urllib.request, urllib.parse, json as _json, sqlite3, os
from app import get_db as _orig_get_db
from app.ai_engine import (get_recommendations, generate_itinerary,
                           analyze_sentiment, DESTINATIONS, get_dest_coords)
from app.nlp_chatbot import nlp_chatbot_reply

# ── Robust get_db: WAL mode + 30s timeout prevents "database is locked" ───────
def get_db():
    """Return a per-request SQLite connection with WAL journal and 30s timeout."""
    if "db" not in g:
        try:
            db = _orig_get_db()   # use app's existing connection if available
            # Enable WAL mode (allows concurrent reads + one writer)
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA busy_timeout=30000")   # wait up to 30s if locked
            g.db = db
        except Exception:
            # Fallback: open fresh connection with timeout
            import sys, pathlib
            base  = pathlib.Path(__file__).resolve().parent.parent
            db_path = str(base / "travel.db")
            conn = sqlite3.connect(db_path, timeout=30,
                                   check_same_thread=False,
                                   isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            g.db = conn
    return g.db

api_bp = Blueprint("api", __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"status":"error","message":"Not authenticated"}), 401
        return f(*args, **kwargs)
    return decorated

# ── City name → OpenWeatherMap searchable name ───────────────────────────────
# Some destination names in our DB don't match OWM city names exactly
CITY_NAME_MAP = {
    "Kerala Backwaters":  "Alleppey",
    "Andaman Islands":    "Port Blair",
    "Rann of Kutch":      "Bhuj",
    "Gir National Park":  "Junagadh",
    "Valley of Flowers":  "Chamoli",
    "Bandhavgarh":        "Umaria",
    "Ranthambore":        "Sawai Madhopur",
    "Kaziranga":          "Jorhat",
    "Chilika Lake":       "Puri",
    "Sundarbans":         "Kolkata",
    "Konkan Coast":       "Ratnagiri",
    "Mathura Vrindavan":  "Mathura",
    "Spiti Valley":       "Kaza",
    "Leh Ladakh":         "Leh",
    "Ziro Valley":        "Ziro",
    "Majuli":             "Jorhat",
    "Dawki":              "Shillong",
    "Lachung":            "Gangtok",
    "Araku Valley":       "Visakhapatnam",
    "Mahabalipuram":      "Chennai",
    "Bhedaghat":          "Jabalpur",
    "Chitrakote Falls":   "Jagdalpur",
    "Netarhat":           "Ranchi",
    "Kedarnath":          "Rudraprayag",
    "Auli":               "Joshimath",
    "Cherrapunjee":       "Shillong",
}

def get_owm_city(destination_name):
    """Return the best city name to search on OpenWeatherMap."""
    return CITY_NAME_MAP.get(destination_name, destination_name)

@api_bp.route("/recommend", methods=["POST"])
@login_required
def recommend():
    data = request.get_json()
    try:
        results = get_recommendations(
            from_loc=data.get("from_location",""),
            dest_area=data.get("to_location",""),
            budget=float(data.get("budget",10000)),
            trip_type=data.get("trip_type","Solo"),
            num_days=int(data.get("num_days",3)),
            transport=data.get("transport","Train"),
            season=data.get("season","Winter"),
            interests=data.get("interests", []),
            people=int(data.get("people", 1))
        )
        return jsonify({"status":"success","results":results})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"status":"error","message":str(e)}),500

@api_bp.route("/itinerary", methods=["POST"])
@login_required
def itinerary():
    data = request.get_json()
    try:
        destination  = data.get("destination", "Goa")
        num_days     = int(data.get("num_days", 3))
        trip_type    = data.get("trip_type", "Solo")
        from_location= data.get("from_location", "")
        budget       = float(data.get("budget", 10000))
        transport    = data.get("transport", "Train")
        season       = data.get("season", "Winter")

        plan = generate_itinerary(
            destination=destination,
            num_days=num_days,
            trip_type=trip_type
        )

        # Add lat/lng for Leaflet.js map
        lat, lng = get_dest_coords(plan["destination"])
        plan["lat"] = lat
        plan["lng"] = lng

        # Save trip to DB only here (not on /recommend search)
        try:
            db = get_db()
            db.execute(
                "INSERT INTO trips (user_id,from_location,destination,"
                "trip_type,budget,num_days,transport,season) VALUES (?,?,?,?,?,?,?,?)",
                (session["user_id"], from_location, destination,
                 trip_type, budget, num_days, transport, season)
            )
            db.commit()
        except Exception as db_err:
            # Log DB error but still return itinerary — don't block the user
            print(f"[WARN] Trip save failed: {db_err}")

        return jsonify({"status":"success","itinerary":plan})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"status":"error","message":str(e)}), 500

@api_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    data    = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"status": "error", "message": "Empty message"}), 400
    result = nlp_chatbot_reply(message, DESTINATIONS)
    return jsonify({"status": "success", **result})

@api_bp.route("/delete_trip/<int:trip_id>", methods=["DELETE"])
@login_required
def delete_trip(trip_id):
    db = get_db()
    trip = db.execute("SELECT id FROM trips WHERE id=? AND user_id=?",
                      (trip_id, session["user_id"])).fetchone()
    if not trip:
        return jsonify({"status":"error","message":"Trip not found"}), 404
    db.execute("DELETE FROM trips WHERE id=? AND user_id=?", (trip_id, session["user_id"]))
    db.commit()
    return jsonify({"status":"success","message":"Trip deleted"})

@api_bp.route("/sentiment", methods=["POST"])
@login_required
def sentiment():
    data = request.get_json()
    result = analyze_sentiment(data.get("review",""))
    return jsonify({"status":"success","sentiment":result})

# ── Weather (proxy — keeps API key server-side) ───────────────────────────────
def _load_api_key():
    """Force-reload config.py every time so key changes take effect immediately."""
    import importlib, sys
    if 'config' in sys.modules:
        del sys.modules['config']
    try:
        import os
        return os.getenv("OPENWEATHER_API_KEY", "").strip()
    except Exception:
        return ""

def _fetch_weather(city_query, api_key):
    """Call OpenWeatherMap API. Returns parsed dict or raises exception."""
    url = (f"https://api.openweathermap.org/data/2.5/weather"
           f"?q={urllib.parse.quote(city_query)},IN"
           f"&appid={api_key}&units=metric")
    req = urllib.request.Request(url, headers={"User-Agent": "TravelWise/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return _json.loads(r.read())

@api_bp.route("/weather/<path:city>", methods=["GET"])
@login_required
def weather(city):
    owm_key = _load_api_key()
    if not owm_key or owm_key == "your_key_here":
        return jsonify({"status": "success", "weather": {
            "city": city, "temp": 28, "feels_like": 30,
            "description": "Partly Cloudy", "humidity": 62,
            "wind": 14, "icon": "02d", "mock": True,
        }})

    # Try primary city name, then fallback mapped name
    primary = get_owm_city(city)   # mapped name (e.g. Kerala Backwaters → Alleppey)
    fallback = city                # original name

    for attempt, query in enumerate([primary, fallback]):
        try:
            d = _fetch_weather(query, owm_key)
            return jsonify({"status": "success", "weather": {
                "city":        city,
                "owm_city":    d["name"],
                "temp":        round(d["main"]["temp"]),
                "feels_like":  round(d["main"]["feels_like"]),
                "description": d["weather"][0]["description"].title(),
                "humidity":    d["main"]["humidity"],
                "wind":        round(d["wind"]["speed"] * 3.6),
                "icon":        d["weather"][0]["icon"],
                "mock":        False,
            }})
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return jsonify({"status": "error",
                    "message": "Invalid API key. Check config.py — paste key directly, no quotes issues."}), 500
            if e.code == 404 and attempt == 0:
                continue   # try fallback name
            try:
                err_body = _json.loads(e.read())
                msg = err_body.get("message", str(e))
            except Exception:
                msg = str(e)
            return jsonify({"status": "error", "message": f"OWM {e.code}: {msg}"}), 500
        except Exception as e:
            if attempt == 0:
                continue
            return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "error", "message": f"City '{city}' not found"}), 500

# ── Weather debug endpoint — shows exactly what's happening ───────────────────
@api_bp.route("/weather_debug", methods=["GET"])
@login_required
def weather_debug():
    owm_key = _load_api_key()
    info = {
        "owm_key_set":    owm_key != "your_key_here" and bool(owm_key),
        "owm_key_prefix": owm_key[:6] + "..." if len(owm_key) > 6 else "(empty)",
    }
    if not info["owm_key_set"]:
        info["status"] = "No API key — still showing demo weather"
        return jsonify(info)
    # Test with a known city
    try:
        d = _fetch_weather("Mumbai", owm_key)
        info["status"] = "SUCCESS — API key is working!"
        info["test_city"] = d["name"]
        info["test_temp"] = f"{round(d['main']['temp'])}°C"
    except urllib.error.HTTPError as e:
        info["status"] = f"HTTP ERROR {e.code}"
        try: info["detail"] = _json.loads(e.read()).get("message","")
        except Exception: pass
        if e.code == 401:
            info["fix"] = "Your API key is invalid or not yet activated. New keys take ~10 min."
    except Exception as e:
        info["status"] = f"NETWORK ERROR: {e}"
    return jsonify(info)

# ── Reviews ───────────────────────────────────────────────────────────────────

@api_bp.route("/send_itinerary_email", methods=["POST"])
@login_required
def send_itinerary_email():
    import smtplib, ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import sys, importlib

    data      = request.get_json()
    recipient = data.get("email", "").strip()
    itin      = data.get("itinerary", {})

    if not recipient or "@" not in recipient:
        return jsonify({"status": "error", "message": "Invalid email address."}), 400
    if not itin:
        return jsonify({"status": "error", "message": "No itinerary data provided."}), 400

    # Load SMTP credentials from config.py
    try:
        if "config" in sys.modules:
            del sys.modules["config"]
        import os
        smtp_email = os.getenv("SMTP_EMAIL", "").strip()
        smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    except Exception as e:
        return jsonify({"status": "error", "message": "Email not configured. Add SMTP_EMAIL and SMTP_PASSWORD to config.py"}), 500

    if not smtp_email or not smtp_password:
        return jsonify({"status": "error", "message": "SMTP credentials missing in config.py"}), 500

    # Build HTML email body using string concatenation (avoids emoji encoding issues)
    destination = itin.get("destination", "Your Destination")
    num_days    = itin.get("num_days", 0)
    trip_type   = itin.get("trip_type", "")
    days        = itin.get("days", [])

    html  = "<html><body style='font-family:Arial,sans-serif;max-width:700px;margin:0 auto;'>"
    html += "<div style='background:#1a6b6b;padding:24px;border-radius:8px 8px 0 0;'>"
    html += "<h1 style='color:#fff;margin:0;font-size:24px;'>TravelWise</h1>"
    html += "<p style='color:rgba(255,255,255,0.8);margin:4px 0 0;'>Your personalised travel itinerary</p>"
    html += "</div>"
    html += "<div style='background:#f0f4f8;padding:24px;'>"
    html += "<h2 style='color:#1F4E79;margin:0 0 4px;'>" + destination + "</h2>"
    html += "<p style='color:#718096;margin:0;'>" + str(num_days) + "-day " + trip_type + " trip</p>"
    html += "</div>"
    html += "<div style='padding:24px;'>"

    for day in days:
        html += "<div style='margin-bottom:24px;border-left:4px solid #1a6b6b;padding-left:16px;'>"
        html += "<h3 style='color:#1a6b6b;margin:0 0 12px;'>" + day.get("title", "") + "</h3>"
        html += "<table style='width:100%;border-collapse:collapse;'>"
        for item in day.get("schedule", []):
            activity = item.get("activity", "")
            time_val = item.get("time", "")
            itype    = item.get("type", "")
            color    = {"sightseeing":"#2E75B6","food":"#C62828","activity":"#276749",
                       "travel":"#975A16","leisure":"#553C9A"}.get(itype, "#333")
            html += "<tr style='border-bottom:1px solid #f0f4f8;'>"
            html += "<td style='padding:8px 12px 8px 0;color:#718096;font-size:13px;white-space:nowrap;width:80px;'>" + time_val + "</td>"
            html += "<td style='padding:8px 0;font-size:14px;color:#1a202c;'>" + activity
            html += " <span style='font-size:11px;color:" + color + ";background:#f0f4f8;padding:2px 6px;border-radius:10px;margin-left:6px;'>" + itype + "</span>"
            html += "</td></tr>"
        html += "</table></div>"

    html += "</div>"
    html += "<div style='background:#1F4E79;padding:16px 24px;border-radius:0 0 8px 8px;text-align:center;'>"
    html += "<p style='color:rgba(255,255,255,0.7);margin:0;font-size:13px;'>Generated by TravelWise - Smart Travel Planning for India</p>"
    html += "</div>"
    html += "</body></html>"

    try:
        msg             = MIMEMultipart("alternative")
        msg["Subject"]  = "Your " + str(num_days) + "-Day " + destination + " Itinerary - TravelWise"
        msg["From"]     = smtp_email
        msg["To"]       = recipient
        msg.attach(MIMEText(html, "html"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, recipient, msg.as_string())

        return jsonify({"status": "success", "message": "Itinerary sent to " + recipient})

    except smtplib.SMTPAuthenticationError:
        return jsonify({"status": "error",
                        "message": "Gmail authentication failed. Check SMTP_EMAIL and SMTP_PASSWORD in config.py. Make sure you are using a Gmail App Password, not your regular password."}), 500
    except smtplib.SMTPException as e:
        return jsonify({"status": "error", "message": "SMTP error: " + str(e)}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to send email: " + str(e)}), 500


@api_bp.route("/reviews/<destination>", methods=["GET"])
@login_required
def get_reviews(destination):
    db   = get_db()
    rows = db.execute(
        "SELECT r.id, r.review_text, r.rating, r.sentiment, r.created_at, "
        "u.username, r.user_id "
        "FROM reviews r JOIN users u ON r.user_id=u.id "
        "WHERE r.destination=? ORDER BY r.created_at DESC LIMIT 50",
        (destination,)
    ).fetchall()
    reviews = [dict(r) for r in rows]

    if reviews:
        avg_rating = round(sum(r["rating"] for r in reviews) / len(reviews), 1)
        pos  = sum(1 for r in reviews if r["sentiment"] == "Positive")
        neg  = sum(1 for r in reviews if r["sentiment"] == "Negative")
        neu  = sum(1 for r in reviews if r["sentiment"] == "Neutral")
        total = len(reviews)

        # Overall sentiment label based on majority
        if pos >= neg and pos >= neu:
            overall = "Positive"
        elif neg >= pos and neg >= neu:
            overall = "Negative"
        else:
            overall = "Neutral"

        summary = {
            "avg_rating":    avg_rating,
            "total":         total,
            "positive_pct":  round(pos / total * 100),
            "negative_pct":  round(neg / total * 100),
            "neutral_pct":   round(neu / total * 100),
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count":  neu,
            "overall_sentiment": overall,
        }
    else:
        summary = {
            "avg_rating": 0, "total": 0,
            "positive_pct": 0, "negative_pct": 0, "neutral_pct": 0,
            "positive_count": 0, "negative_count": 0, "neutral_count": 0,
            "overall_sentiment": "Neutral",
        }
    return jsonify({"status": "success", "reviews": reviews,
                    "summary": summary, "current_user_id": session["user_id"]})

@api_bp.route("/reviews", methods=["POST"])
@login_required
def submit_review():
    data        = request.get_json()
    destination = data.get("destination", "").strip()
    review_text = data.get("review_text", "").strip()
    rating      = float(data.get("rating", 3))
    if not destination or not review_text:
        return jsonify({"status": "error", "message": "Missing fields"}), 400
    sentiment_result = analyze_sentiment(review_text)
    db = get_db()
    db.execute(
        "INSERT INTO reviews (destination, user_id, review_text, rating, sentiment) VALUES (?,?,?,?,?)",
        (destination, session["user_id"], review_text, rating, sentiment_result["label"])
    )
    db.commit()
    return jsonify({"status": "success", "sentiment": sentiment_result})

@api_bp.route("/reviews/<int:review_id>", methods=["DELETE"])
@login_required
def delete_review(review_id):
    db  = get_db()
    row = db.execute("SELECT id FROM reviews WHERE id=? AND user_id=?",
                     (review_id, session["user_id"])).fetchone()
    if not row:
        return jsonify({"status": "error", "message": "Review not found or not yours"}), 404
    db.execute("DELETE FROM reviews WHERE id=?", (review_id,))
    db.commit()
    return jsonify({"status": "success", "message": "Review deleted"})