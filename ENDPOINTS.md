# My Festival API — endpoint-dokumentti

**Tekijä:** Miku Haveri
**Julkinen osoite:** https://festival-api-festival-mikuhave.2.rahtiapp.fi
**GitHub:** https://github.com/haverimiku/CSC
**Tarkistimen tulos:** `20/20 checks passed`

---

## 1. Endpointit

| Metodi | Polku | Onnistuu | Virheet |
|---|---|---|---|
| GET | `/api/artists` | 200 | – |
| GET | `/api/days` | 200 | – |
| GET | `/api/stages` | 200 | – |
| GET | `/api/artists/{id}/events` | 200 | 404 |
| GET | `/api/timetable?day=YYYY-MM-DD` | 200 | 400 |
| POST | `/api/events` | 201 | 400 |
| DELETE | `/api/events/{id}` | 204 | 404 |

## 2. Esimerkit

### GET /api/artists

```bash
curl https://festival-api-festival-mikuhave.2.rahtiapp.fi/api/artists
```
```json
[{"artist_id": 9, "country": "NOR", "name": "Arctic Rhythm"}, {"artist_id": 2, "country": "FIN", "name": "Aurora Pulse"}, …]
```

### GET /api/artists/{id}/events
```bash
curl https://festival-api-festival-mikuhave.2.rahtiapp.fi/api/artists/1/events
```
```json
[{"day": "2027-07-16", "event_id": 1, "stage": "Northern Main Stage", "starts": "2027-07-16 16:00"}]
```
Tuntematon id → `404` `{"error": "artist 999999 not found"}`

### GET /api/timetable?day=YYYY-MM-DD
```bash
curl "https://festival-api-festival-mikuhave.2.rahtiapp.fi/api/timetable?day=2027-07-17"
```
```json
[{"artist": "Shadow Avenue", "date": "2027-07-17", "ends": "2027-07-17 16:45", "stage": "Forest Stage", "starts": "2027-07-17 16:00"},
 {"artist": "The Northern Lights", "date": "2027-07-17", "ends": "2027-07-17 17:00", "stage": "Northern Main Stage", "starts": "2027-07-17 16:00"}, …]
```
Virheellinen päivämäärä (`?day=not-a-date`) → `400` `{"error": "day must be a valid date in format YYYY-MM-DD"}`

### POST /api/events
```bash
curl -X POST https://festival-api-festival-mikuhave.2.rahtiapp.fi/api/events \
     -H "Content-Type: application/json" \
     -d '{"artist_id": 1, "stage_id": 2, "day_id": 1, "start_dt": "2027-07-16 20:00:00"}'
```
```json
{"artist_id": 1, "day_id": 1, "duration_min": 45, "end_dt": "2027-07-16 20:45:00", "event_id": 16,
 "event_type": "PERFORMANCE", "stage_id": 2, "start_dt": "2027-07-16 20:00:00"}
```
Puuttuva kenttä → `400` `{"error": "missing fields: stage_id, day_id, start_dt"}` ·
Olematon artist_id → `400` `{"error": "artist_id, stage_id or day_id does not exist"}`

### DELETE /api/events/{id}
```bash
curl -X DELETE https://festival-api-festival-mikuhave.2.rahtiapp.fi/api/events/16
```
Onnistuu → `204` (tyhjä runko) · Tuntematon id → `404` `{"error": "event 16 not found"}`

## 3. Julkaisu Rahtiin

Loin Rahdin web-konsolissa projektin ja toin sovelluksen GitHub-reposta linkillä.
Rahti rakensi siitä kontti-imagen, jossa on Python, Flask, gunicorn ja SQLite-kanta. Valmiista imagesta Rahti käynnisti Deploymentin, joka ajaa sovellusta portissa 8080. Osoitteen löysin topology näkymän "routes" alta.
Haasteita oli csc käyttöliittymän kanssa. Epäselkeä navigointi ja painikkeet piilossa, mutta kyllä kaikki löytyi kun tarpeeksi penkoi.

## 4. Tietoturva

Ennen oikeaa tuotantokäyttöä rajapinta tarvitsisi tunnistautumisen
ainakin POST- ja DELETE-kutsuille, koska nyt kuka tahansa voi muokata ohjelmaa. Lisäksi tarvittaisiin pyyntöjen rajoitus ja lokien seuranta. SQL-injektio on estetty, koska kaikki käyttäjän syötteet välitetään kyselyihin `?`-parametreina
eikä SQL-merkkijonoja koskaan koota syötteestä. Syötteet myös validoidaan ennen kantaan menoa:
päivämäärä ja `start_dt` tarkistetaan `datetime.strptime`:llä ja id:iden pitää olla kokonaislukuja,
joten esim. `?day=2027-07-16' OR 1=1--` palauttaa 400.
