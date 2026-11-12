
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

FIXTURES_FILE = ROOT / "config" / "fixtures.json"
STREAMS_FILE = ROOT / "config" / "streams.json"
OUTPUT_FILE = ROOT / "Iptv_selected.m3u"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def valid_stream_url(url):
    if not isinstance(url, str):
        return False

    parsed = urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def main():
    fixtures = load_json(FIXTURES_FILE)
    streams_data = load_json(STREAMS_FILE)

    matches = fixtures.get("matches", [])
    streams = streams_data.get("streams", [])

    stream_map = {
        item["match_id"]: item["url"]
        for item in streams
        if item.get("match_id") and valid_stream_url(item.get("url"))
    }

    now = datetime.now(timezone.utc)
    output = ["#EXTM3U"]
    count = 0

    for match in matches:
        match_id = match.get("id")
        start = datetime.fromisoformat(
            match["start_time"].replace("Z", "+00:00")
        )
        end = datetime.fromisoformat(
            match["end_time"].replace("Z", "+00:00")
        )

        if end <= now:
            continue

        url = stream_map.get(match_id)

        # M3U cần URL phát thực tế.
        # Trận chưa có link sẽ không được đưa vào playlist.
        if not url:
            continue

        if start <= now < end:
            group = "LIVE"
        else:
            group = "Sap dien ra"

        home = match.get("home", "Unknown")
        away = match.get("away", "Unknown")
        title = f"{home} vs {away}"

        output.append(
            f'#EXTINF:-1 group-title="{group}",{title}'
        )
        output.append(url)
        count += 1

    OUTPUT_FILE.write_text(
        "\n".join(output) + "\n",
        encoding="utf-8"
    )

    print(f"Playlist updated: {count} playable matches")


if __name__ == "__main__":
    main()
