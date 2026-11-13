
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FIXTURES_FILE = ROOT / "config" / "fixtures.json"
STREAMS_FILE = ROOT / "config" / "streams.json"
OUTPUT_FILE = ROOT / "Iptv_selected.m3u"

API_URL = "https://api.sportstatsapi.com/api/v1/soccer/matches"

# Match league names returned by SportStatsAPI.
LEAGUES = {
    "premier league": "Premier League",
    "uefa champions league": "Champions League",
    "champions league": "Champions League",
    "la liga": "La Liga",
    "serie a": "Serie A",
    "bundesliga": "Bundesliga",
    "ligue 1": "Ligue 1",
    "v.league 1": "V-League"
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


def fetch_matches(api_key):
    today = datetime.now(timezone.utc).date()
    last_day = today + timedelta(days=7)

    params = urllib.parse.urlencode({
        "date_from": today.isoformat(),
        "date_to": last_day.isoformat(),
        "limit": 100,
        "order": "asc"
    })

    request = urllib.request.Request(
        f"{API_URL}?{params}",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "my-iptv-personal-bot"
        }
    )

    print("Connecting to SportStatsAPI...")

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if not result.get("success"):
        raise RuntimeError(
            f"SportStatsAPI error: {result.get('error', result)}"
        )

    meta = result.get("meta", {})

    if meta.get("has_more"):
        print(
            "WARNING: API returned more than 100 matches. "
            "Some matches may not be included."
        )

    return result.get("data", [])


def valid_url(url):
    if not isinstance(url, str):
        return False

    parsed = urllib.parse.urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def get_match_status(match):
    code = str(match.get("status_code") or "").lower()
    status = str(match.get("status") or "").upper()

    finished = {
        "finished", "ft", "aet", "pen",
        "cancelled", "canceled", "postponed"
    }

    live_codes = {
        "live", "1h", "ht", "2h", "et", "bt", "p"
    }

    if code in finished or status in {"FT", "AET", "PEN"}:
        return "FINISHED"

    if code == "live" or status in live_codes:
        return "LIVE"

    if status.isdigit() or "+" in status:
        return "LIVE"

    if code in {"scheduled", "not_started", "upcoming"}:
        return "UPCOMING"

    if status in {"NS", "TBD"}:
        return "UPCOMING"

    return "UNKNOWN"


def main():
    api_key = os.environ.get("SPORTSTATS_API_KEY")

    if not api_key:
        raise RuntimeError("Missing SPORTSTATS_API_KEY GitHub Secret")

    raw_matches = fetch_matches(api_key)

    print("----- API DATA DIAGNOSTIC -----")
    print(f"Total received: {len(raw_matches)}")

    league_names = sorted({
        str(m.get("league_name", "UNKNOWN"))
        for m in raw_matches
    })

    print("LEAGUES RETURNED BY API:")
    for name in league_names:
        print(f"- {name}")

    print("SAMPLE MATCHES:")
    for match in raw_matches[:5]:
        print({
            "league_name": match.get("league_name"),
            "status": match.get("status"),
            "status_code": match.get("status_code"),
            "start_at": match.get("start_at"),
            "home": match.get("home_team"),
            "away": match.get("away_team")
        })

    print("----- END DIAGNOSTIC -----")

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

    for match in raw_matches:
        league_name = str(match.get("league_name") or "").strip()
        league_key = league_name.lower()

        if league_key not in LEAGUES:
            continue

        match_status = get_match_status(match)

        if match_status not in {"LIVE", "UPCOMING"}:
            continue

        match_id = match.get("match_id") or match.get("id")

        home = match.get("home_team") or {}
        away = match.get("away_team") or {}

        home_name = home.get("display_name") or home.get("name") or "Unknown"
        away_name = away.get("display_name") or away.get("name") or "Unknown"

        start_at = match.get("start_at") or match.get("start_date")

        fixture = {
            "id": str(match_id),
            "sport": "Football",
            "league": LEAGUES[league_key],
            "source_league": league_name,
            "home": home_name,
            "away": away_name,
            "start_time": start_at,
            "status": match_status,
            "score_home": home.get("score"),
            "score_away": away.get("score")
        }

        fixtures.append(fixture)

        stream_url = stream_map.get(str(match_id))

        if not stream_url:
            continue

        group = "LIVE" if match_status == "LIVE" else "Sap dien ra"

        title = f"{home_name} vs {away_name}"

        extinf = (
            f'#EXTINF:-1 tvg-id="{match_id}" '
            f'group-title="{group}",{title}'
        )

        playable.append((str(start_at or ""), extinf, stream_url))

    fixtures.sort(key=lambda x: x.get("start_time") or "")
    playable.sort(key=lambda x: x[0])

    save_json(FIXTURES_FILE, {"matches": fixtures})

    playlist = [
        "#EXTM3U",
        "# Data: Stadiro / SportStatsAPI - https://sportstatsapi.com/"
    ]

    for _, extinf, url in playable:
        playlist.append(extinf)
        playlist.append(url)

    OUTPUT_FILE.write_text(
        "\n".join(playlist) + "\n",
        encoding="utf-8"
    )

    live_count = sum(
        1 for item in fixtures if item["status"] == "LIVE"
    )
    upcoming_count = sum(
        1 for item in fixtures if item["status"] == "UPCOMING"
    )

    print(f"Matches received: {len(raw_matches)}")
    print(f"Selected fixtures: {len(fixtures)}")
    print(f"Live matches: {live_count}")
    print(f"Upcoming matches: {upcoming_count}")
    print(f"Playable matches: {len(playable)}")
    print("Playlist updated successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        sys.exit(1)
