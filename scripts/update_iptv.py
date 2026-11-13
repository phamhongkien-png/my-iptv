
def main():
    api_key = os.environ.get("SPORTSTATS_API_KEY")

    if not api_key:
        raise RuntimeError("Missing SPORTSTATS_API_KEY GitHub Secret")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "my-iptv-personal-bot"
    }

    # ==========================================
    # 1. CHECK SOCCER LEAGUE CATALOGUE
    # ==========================================

    print("\n========== SOCCER LEAGUES ==========")

    request = urllib.request.Request(
        LEAGUES_URL,
        headers=headers
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        soccer_catalogue = json.loads(
            response.read().decode("utf-8")
        )

    if not soccer_catalogue.get("success"):
        raise RuntimeError(
            f"Soccer league catalogue error: {soccer_catalogue}"
        )

    soccer_leagues = soccer_catalogue.get("data", [])

    print(f"Total soccer leagues: {len(soccer_leagues)}")

    print("\n----- RAW FIRST 3 SOCCER LEAGUES -----")
    print(json.dumps(
        soccer_leagues[:3],
        ensure_ascii=False,
        indent=2
    ))

    keywords = [
        "premier league",
        "champions league",
        "la liga",
        "v.league",
        "vietnam"
    ]

    print("\n----- TARGET SOCCER LEAGUES -----")

    for league in soccer_leagues:
        league_text = json.dumps(
            league,
            ensure_ascii=False
        ).lower()

        if any(word in league_text for word in keywords):
            print(json.dumps(
                league,
                ensure_ascii=False
            ))

    # ==========================================
    # 2. CHECK VOLLEYBALL LEAGUE CATALOGUE
    # ==========================================

    print("\n========== VOLLEYBALL LEAGUES ==========")

    request = urllib.request.Request(
        VOLLEYBALL_LEAGUES_URL,
        headers=headers
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        volleyball_catalogue = json.loads(
            response.read().decode("utf-8")
        )

    if not volleyball_catalogue.get("success"):
        raise RuntimeError(
            f"Volleyball league catalogue error: {volleyball_catalogue}"
        )

    volleyball_leagues = volleyball_catalogue.get("data", [])

    print(f"Total volleyball leagues: {len(volleyball_leagues)}")

    print("\n----- RAW FIRST 3 VOLLEYBALL LEAGUES -----")
    print(json.dumps(
        volleyball_leagues[:3],
        ensure_ascii=False,
        indent=2
    ))

    volleyball_keywords = [
        "nations league",
        "asian championship",
        "asian games",
        "avc champions league",
        "vietnam"
    ]

    print("\n----- TARGET VOLLEYBALL LEAGUES -----")

    for league in volleyball_leagues:
        league_text = json.dumps(
            league,
            ensure_ascii=False
        ).lower()

        if any(word in league_text for word in volleyball_keywords):
            print(json.dumps(
                league,
                ensure_ascii=False
            ))

    print("\n========== END CATALOGUE DIAGNOSTIC ==========")
if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        sys.exit(1)
