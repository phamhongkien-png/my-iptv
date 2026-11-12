
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_FILE = ROOT / "config" / "fixtures.json"
STREAMS_FILE = ROOT / "config" / "streams.json"
OUTPUT_FILE = ROOT / "Iptv_selected.m3u"

API_URL = "https://v3.football.api-sports.io/fixtures"
TIMEZONE = "Asia/Ho_Chi_Minh"

# API-Football league IDs
LEAGUES = {
    39: "Premier League",
    2: "Champions League",
    140: "La Liga",
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1",
    340: "V.League 1"
}

LIVE_STATUSES = {
    "1H", "HT", "2H", "ET", "BT", "P", "LIVE"
}

UPCOMING_STATUSES = {"NS", "TBD"}

FINISHED_STATUSES = {
    "FT", "AET", "PEN", "CANC", "ABD", "AWD", "WO"
}


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )



def api_request(api_key):
    now = datetime.now(ZoneInfo(TIMEZONE))
    date_from = now.date()
    date_to = (now + timedelta(days=7)).date()

    all_fixtures = []

    for league_id, league_name in LEAGUES.items():
        params = urllib.parse.urlencode({
            "league": league_id,
            "season": now.year,
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "timezone": TIMEZONE
        })

        request = urllib.request.Request(
            f"{API_URL}?{params}",
            headers={
                "x-apisports-key": api_key,
                "User-Agent": "my-iptv-personal-bot"
            }
        )

        print(f"Fetching {league_name}...")

        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        errors = result.get("errors")

        if errors:
            raise RuntimeError(
                f"API error for {league_name}: {errors}"
            )

        fixtures = result.get("response", [])
        all_fixtures.extend(fixtures)

        print(f"{league_name}: {len(fixtures)} matches")

    return all_fixtures


def valid_url(url):
    if not isinstance(url, str):
        return False

    parsed = urllib.parse.urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def main():
    api_key = os.environ.get("API_FOOTBALL_KEY")

    if not api_key:
        raise RuntimeError("Missing API_FOOTBALL_KEY secret")

    print("Fetching football fixtures...")
    api_fixtures = api_request(api_key)

    try:
        streams_data = load_json(STREAMS_FILE)
    except FileNotFoundError:
        streams_data = {"streams": []}

    stream_map = {
        str(item["match_id"]): item["url"].strip()
        for item in streams_data.get("streams", [])
        if item.get("match_id") and valid_url(item.get("url"))
    }

    fixtures = []
    playable = []

    for item in api_fixtures:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        status = fixture.get("status", {}).get("short", "")

        league_id = league.get("id")

        if league_id not in LEAGUES:
            continue

        if status in FINISHED_STATUSES:
            continue

        if status not in LIVE_STATUSES | UPCOMING_STATUSES:
            continue

        fixture_id = str(fixture.get("id"))
        kickoff = fixture.get("date")

        home = teams.get("home", {}).get("name", "Unknown")
        away = teams.get("away", {}).get("name", "Unknown")

        match = {
            "id": fixture_id,
            "sport": "Football",
            "league_id": league_id,
            "league": LEAGUES[league_id],
            "home": home,
            "away": away,
            "start_time": kickoff,
            "status": status,
            "elapsed": fixture.get("status", {}).get("elapsed")
        }

        fixtures.append(match)

        stream_url = stream_map.get(fixture_id)

        if not stream_url:
            continue

        if not valid_url(stream_url):
            continue

        group = "LIVE" if status in LIVE_STATUSES else "Sap dien ra"

        title = f"{home} vs {away}"
        logo = teams.get("home", {}).get("logo", "")

        extinf = (
            f'#EXTINF:-1 tvg-id="{fixture_id}" '
            f'tvg-logo="{logo}" group-title="{group}",{title}'
        )

        playable.append((kickoff or "", extinf, stream_url))

    fixtures.sort(key=lambda x: x.get("start_time", ""))
    playable.sort(key=lambda x: x[0])

    save_json(FIXTURES_FILE, {"matches": fixtures})

    playlist = ["#EXTM3U"]

    for _, extinf, url in playable:
        playlist.append(extinf)
        playlist.append(url)

    OUTPUT_FILE.write_text(
        "\n".join(playlist) + "\n",
        encoding="utf-8"
    )

    print(f"Fixtures found: {len(fixtures)}")
    print(f"Playable matches: {len(playable)}")
    print("Playlist updated successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        sys.exit(1)
