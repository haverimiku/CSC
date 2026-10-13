"""My Festival REST API — M10 starter (CSC Rahti).

FI: Tämä on M10-tehtävän lähtöpohja. GET /api/artists on valmiina mallina;
    toteuta loput TODO-kohdat. Aja paikallisesti:  python app.py
    ja testaa:  python test_endpoints.py http://localhost:8080
EN: This is the M10 starter. GET /api/artists is done as an example;
    implement the remaining TODOs. Run locally:  python app.py
    and test:  python test_endpoints.py http://localhost:8080
"""
import os
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, jsonify, request

app = Flask(__name__)

# FI: Kanta kulkee kontin mukana. Polun voi vaihtaa ympäristömuuttujalla.
# EN: The database ships inside the container. Override the path with an env var.
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "myfestival.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")  # M8: sqlite3 ei valvo FK:ita oletuksena / FKs are off by default
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def health():
    """FI: Rahti ja selain näkevät, että sovellus on pystyssä.
    EN: Lets Rahti and your browser see the app is up."""
    return jsonify(status="ok", endpoints=["/api/artists", "/api/days", "/api/stages",
                                           "/api/artists/<id>/events", "/api/timetable?day=YYYY-MM-DD",
                                           "POST /api/events", "DELETE /api/events/<id>"])


@app.get("/api/artists")
def get_artists():
    conn = get_db()
    rows = conn.execute("SELECT artist_id, name, country FROM Artist ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/days")
def get_days():
    """FI: Apuendpoint: festivaalipäivät (tarkistin hakee tästä day_id:n).
    EN: Helper endpoint: festival days (the checker reads day_id from here)."""
    conn = get_db()
    rows = conn.execute("SELECT day_id, date FROM Day ORDER BY date").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/stages")
def get_stages():
    """FI: Apuendpoint: lavat. EN: Helper endpoint: stages."""
    conn = get_db()
    rows = conn.execute("SELECT stage_id, name FROM Stage ORDER BY stage_id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/artists/<int:artist_id>/events")
def get_artist_events(artist_id):
    """FI: Artistin esiintymiset: event_id, day, stage, starts. Tuntematon id → 404."""
    conn = get_db()
    # FI: Tarkista artisti erikseen: artisti ilman esiintymisiä → 200 ja [], ei 404.
    artist = conn.execute("SELECT 1 FROM Artist WHERE artist_id = ?", (artist_id,)).fetchone()
    if artist is None:
        conn.close()
        return jsonify(error=f"artist {artist_id} not found"), 404
    rows = conn.execute("""
        SELECT e.event_id, d.date AS day, s.name AS stage, e.start_dt AS starts
        FROM Event e
        JOIN Day d        ON d.day_id = e.day_id
        JOIN Stage s      ON s.stage_id = e.stage_id
        JOIN EventType et ON et.event_type_id = e.event_type_id
        WHERE e.artist_id = ? AND et.code = 'PERFORMANCE'
        ORDER BY e.start_dt
    """, (artist_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/timetable")
def get_timetable():
    day = request.args.get("day")  # FI: kyselyparametri ?day=2025-07-05
    """FI: Rivit {date, stage, artist, starts, ends} aikajärjestyksessä. Ilman parametria koko ohjelma,
    virheellinen päivämäärä → 400."""
    if day is not None:
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            return jsonify(error="day must be a valid date in format YYYY-MM-DD"), 400
    sql = """
        SELECT d.date, s.name AS stage, a.name AS artist, e.start_dt AS starts, e.end_dt AS ends
        FROM Event e
        JOIN Day d        ON d.day_id = e.day_id
        JOIN Stage s      ON s.stage_id = e.stage_id
        JOIN Artist a     ON a.artist_id = e.artist_id
        JOIN EventType et ON et.event_type_id = e.event_type_id
        WHERE et.code = 'PERFORMANCE'
    """
    params = []
    if day is not None:
        sql += " AND d.date = ?"
        params.append(day)
    sql += " ORDER BY e.start_dt, s.name"
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.post("/api/events")
def create_event():
    """FI: Lisää esiintyminen. Puuttuva/virheellinen kenttä tai olematon viite → 400, onnistuminen → 201."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="request body must be a JSON object"), 400

    required = ("artist_id", "stage_id", "day_id", "start_dt")
    missing = [f for f in required if body.get(f) in (None, "")]
    if missing:
        return jsonify(error=f"missing fields: {', '.join(missing)}"), 400
    for f in ("artist_id", "stage_id", "day_id"):
        if not isinstance(body[f], int) or isinstance(body[f], bool):
            return jsonify(error=f"{f} must be an integer"), 400

    # FI: Kannassa on sekä muotoa 'YYYY-MM-DD HH:MM' että 'YYYY-MM-DD HH:MM:SS'.
    start_dt = body["start_dt"]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            start = datetime.strptime(str(start_dt), fmt)
            break
        except ValueError:
            continue
    else:
        return jsonify(error="start_dt must be in format YYYY-MM-DD HH:MM[:SS]"), 400

    duration_min = 45
    end_dt = (start + timedelta(minutes=duration_min)).strftime(fmt)

    conn = get_db()
    try:
        day = conn.execute("SELECT date FROM Day WHERE day_id = ?", (body["day_id"],)).fetchone()
        if day is not None and day["date"] != start.strftime("%Y-%m-%d"):
            return jsonify(error=f"start_dt must be on day {day['date']} (day_id {body['day_id']})"), 400
        cur = conn.execute("""
            INSERT INTO Event (event_type_id, day_id, stage_id, artist_id, start_dt, end_dt, duration_min)
            VALUES ((SELECT event_type_id FROM EventType WHERE code = 'PERFORMANCE'), ?, ?, ?, ?, ?, ?)
        """, (body["day_id"], body["stage_id"], body["artist_id"], start_dt, end_dt, duration_min))
        conn.commit()
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e):
            msg = "this stage already has an event starting at that time on that day"
        elif "FOREIGN KEY" in str(e):
            msg = "artist_id, stage_id or day_id does not exist"
        else:
            msg = f"invalid event: {e}"
        return jsonify(error=msg), 400
    finally:
        conn.close()

    return jsonify(event_id=cur.lastrowid, artist_id=body["artist_id"], stage_id=body["stage_id"],
                   day_id=body["day_id"], event_type="PERFORMANCE", start_dt=start_dt,
                   end_dt=end_dt, duration_min=duration_min), 201


@app.delete("/api/events/<int:event_id>")
def delete_event(event_id):
    """FI: Poista esiintyminen. Onnistuminen → 204 (tyhjä runko), tuntematon id → 404."""
    conn = get_db()
    cur = conn.execute("DELETE FROM Event WHERE event_id = ?", (event_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify(error=f"event {event_id} not found"), 404
    return "", 204


if __name__ == "__main__":
    # FI: Paikallinen kehityspalvelin. Rahdissa sovellusta ajaa gunicorn (ks. Dockerfile).
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
