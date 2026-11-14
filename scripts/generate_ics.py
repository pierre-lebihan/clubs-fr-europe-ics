#!/usr/bin/env python3
"""Generate a filtered ICS calendar for French football clubs in UEFA competitions."""

from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

COMPETITION_FEEDS: tuple[tuple[str, str], ...] = (
    ("CL", "https://ics.fixtur.es/v2/league/champions-league.ics"),
    ("EL", "https://ics.fixtur.es/v2/league/europa-league.ics"),
    ("Conf", "https://ics.fixtur.es/v2/league/uefa-conference-league.ics"),
)

FRENCH_LEAGUE_FEEDS: tuple[str, ...] = (
    "https://ics.fixtur.es/v2/league/ligue-1.ics",
    "https://ics.fixtur.es/v2/league/ligue-2.ics",
)

# Canonical Fixtur.es names for French clubs (used as fallback & union with live Ligue 1/2 feeds).
SEED_FRENCH_CLUBS: frozenset[str] = frozenset(
    {
        "AS Monaco",
        "AS Nancy",
        "Amiens",
        "Angers SCO",
        "Annecy",
        "Auxerre",
        "Bastia",
        "Boulogne",
        "Clermont",
        "Concarneau",
        "Dijon FCO",
        "Dunkerque",
        "EA Guingamp",
        "Estac Troyes",
        "FC Metz",
        "FC Nantes",
        "Gazelec FC Ajaccio",
        "Girondins Bordeaux",
        "Grenoble Foot 38",
        "Laval",
        "Le Havre",
        "Le Mans",
        "Lens",
        "Lille",
        "Lorient",
        "Martigues",
        "Montpellier",
        "Nîmes Olympique",
        "OGC Nice",
        "Olympique Lyonnais",
        "Olympique Marseille",
        "Paris FC",
        "Paris Saint-Germain",
        "Pau",
        "Quevilly",
        "RC Strasbourg",
        "Red Star",
        "Rodez",
        "SM Caen",
        "Saint-Etienne",
        "Sochaux",
        "Stade Brestois 29",
        "Stade Rennais",
        "Stade de Reims",
        "Toulouse",
        "Valenciennes",
    }
)

EXCLUDED_CLUBS: frozenset[str] = frozenset({"Stade Rennais"})

CALENDAR_NAME = "🇪🇺 Clubs FR (hors Rennes)"
CALENDAR_DESCRIPTION = (
    "Matchs des clubs français en Coupes d'Europe "
    "(Ligue des Champions, Ligue Europa, Ligue Conférence), hors Stade Rennais."
)


def fetch_text(url: str, timeout: int = 20) -> str:
    """Download UTF-8 text content from an HTTP(S) URL."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "clubs-fr-europe-ics/1.0 (+https://github.com/pierre-lebihan)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def unfold_ics(raw_ics: str) -> str:
    """Unfold RFC 5545 folded lines (CRLF/LF followed by space or tab)."""
    normalized = raw_ics.replace("\r\n", "\n")
    return re.sub(r"\n[ \t]", "", normalized)


def parse_vevents(raw_ics: str) -> list[str]:
    """Extract unfolded VEVENT blocks from a raw ICS string."""
    unfolded = unfold_ics(raw_ics)
    return re.findall(r"BEGIN:VEVENT\n.*?\nEND:VEVENT", unfolded, flags=re.S)


def extract_teams_from_summary(summary: str) -> tuple[str, str] | None:
    """Parse (home, away) team names from a Fixtur.es SUMMARY line."""
    clean = summary.strip()
    clean = re.sub(r"^⚠️\s*(?:Postponed|Suspended|Cancelled):\s*", "", clean)
    clean = re.sub(r"\s*\[(?:CL|EL|Conf)\]", "", clean)
    clean = re.sub(r"\s*\(\d+\s*-\s*\d+\)\s*$", "", clean)
    parts = clean.split(" - ")
    if len(parts) != 2:
        return None
    home, away = parts[0].strip(), parts[1].strip()
    if not home or not away or home == "..." or away == "...":
        return None
    return home, away


def extract_field(vevent: str, name: str) -> str:
    """Return the value of the first matching ICS property in a VEVENT block."""
    match = re.search(rf"^{re.escape(name)}(?:;[^:]*)?:(.*)$", vevent, flags=re.M)
    return match.group(1).strip() if match else ""


def discover_french_clubs() -> set[str]:
    """Build the set of French club names from live Ligue 1/2 ICS feeds + static seed."""
    clubs = set(SEED_FRENCH_CLUBS)
    for url in FRENCH_LEAGUE_FEEDS:
        try:
            raw = fetch_text(url)
        except Exception as exc:  # pragma: no cover - network fallback
            print(f"Warning: failed to fetch {url}: {exc}", file=sys.stderr)
            continue
        for vevent in parse_vevents(raw):
            teams = extract_teams_from_summary(extract_field(vevent, "SUMMARY"))
            if teams:
                clubs.update(teams)
    return clubs - EXCLUDED_CLUBS


def filter_european_events(
    feeds_content: list[str],
    french_clubs: set[str],
    excluded_clubs: frozenset[str] = EXCLUDED_CLUBS,
) -> list[str]:
    """Return deduplicated, chronologically sorted VEVENTs involving French clubs."""
    seen_uids: dict[str, tuple[str, str]] = {}
    for raw_ics in feeds_content:
        for vevent in parse_vevents(raw_ics):
            teams = extract_teams_from_summary(extract_field(vevent, "SUMMARY"))
            if not teams:
                continue
            home, away = teams
            if home in excluded_clubs or away in excluded_clubs:
                continue
            if home not in french_clubs and away not in french_clubs:
                continue
            uid = extract_field(vevent, "UID")
            dtstart = extract_field(vevent, "DTSTART")
            if not uid or not dtstart:
                continue
            seen_uids[uid] = (dtstart, vevent)

    return [ev for _, ev in sorted(seen_uids.values(), key=lambda item: (item[0], extract_field(item[1], "UID")))]


def fold_ics_line(line: str, max_octets: int = 75) -> str:
    """Fold a single ICS line to at most max_octets UTF-8 bytes per physical line."""
    encoded = line.encode("utf-8")
    if len(encoded) <= max_octets:
        return line

    chunks: list[str] = []
    current = ""
    current_bytes = 0
    limit = max_octets

    for ch in line:
        ch_bytes = len(ch.encode("utf-8"))
        if current_bytes + ch_bytes > limit:
            chunks.append(current)
            current = " " + ch
            current_bytes = 1 + ch_bytes
            limit = max_octets
        else:
            current += ch
            current_bytes += ch_bytes

    if current:
        chunks.append(current)
    return "\r\n".join(chunks)


def build_vcalendar(vevents: list[str]) -> str:
    """Serialize filtered VEVENT blocks into a complete RFC 5545 VCALENDAR string."""
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//pierre-lebihan//clubs-fr-europe-ics//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{CALENDAR_NAME}",
        f"NAME:{CALENDAR_NAME}",
        f"X-WR-CALDESC:{CALENDAR_DESCRIPTION}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]
    lines = [fold_ics_line(line) for line in header]
    for vevent in vevents:
        for line in vevent.split("\n"):
            lines.append(fold_ics_line(line))
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> int:
    """Fetch feeds, filter French clubs (excluding Rennes), and write docs/calendar.ics."""
    french_clubs = discover_french_clubs()
    feeds_content: list[str] = []
    for code, url in COMPETITION_FEEDS:
        print(f"Fetching {code}: {url}")
        feeds_content.append(fetch_text(url))

    events = filter_european_events(feeds_content, french_clubs)
    ics_output = build_vcalendar(events)

    out_path = Path(__file__).resolve().parent.parent / "docs" / "calendar.ics"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(ics_output.encode("utf-8"))
    print(f"Wrote {len(events)} events to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
