#!/usr/bin/env python3
"""Unit tests for the European French clubs ICS generator."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import generate_ics as gen  # noqa: E402


SAMPLE_ICS = (
    "BEGIN:VCALENDAR\r\n"
    "VERSION:2.0\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:psg-1@maak-agenda.nl\r\n"
    "DTSTART:20261125T200000Z\r\n"
    "DTEND:20261125T214500Z\r\n"
    "SUMMARY:Borussia Dortmund - Paris Saint-Germain [CL]\r\n"
    "DESCRIPTION:Line one\r\n"
    "  continued\r\n"
    "END:VEVENT\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:dinamo-brest-1@maak-agenda.nl\r\n"
    "DTSTART:20261125T174500Z\r\n"
    "DTEND:20261125T193000Z\r\n"
    "SUMMARY:Dinamo Brest - FC Astana [CL]\r\n"
    "END:VEVENT\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:rennes-1@maak-agenda.nl\r\n"
    "DTSTART:20261126T200000Z\r\n"
    "DTEND:20261126T214500Z\r\n"
    "SUMMARY:N.E.C. - Stade Rennais [EL]\r\n"
    "END:VEVENT\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:rennes-vs-ol@maak-agenda.nl\r\n"
    "DTSTART:20270311T200000Z\r\n"
    "DTEND:20270311T214500Z\r\n"
    "SUMMARY:Olympique Lyonnais - Stade Rennais [EL]\r\n"
    "END:VEVENT\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:monaco-postponed@maak-agenda.nl\r\n"
    "DTSTART:20261126T174500Z\r\n"
    "DTEND:20261126T193000Z\r\n"
    "SUMMARY:⚠️ Postponed: Heart of Midlothian - AS Monaco [Conf]\r\n"
    "END:VEVENT\r\n"
    "END:VCALENDAR\r\n"
)


class GenerateIcsTests(unittest.TestCase):
    def test_extract_teams_from_summary(self) -> None:
        self.assertEqual(
            gen.extract_teams_from_summary("Liverpool - Lens [CL]"),
            ("Liverpool", "Lens"),
        )
        self.assertEqual(
            gen.extract_teams_from_summary("Borussia Dortmund - Paris Saint-Germain [CL] (2-1)"),
            ("Borussia Dortmund", "Paris Saint-Germain"),
        )
        self.assertEqual(
            gen.extract_teams_from_summary("⚠️ Postponed: Heart of Midlothian - AS Monaco [Conf]"),
            ("Heart of Midlothian", "AS Monaco"),
        )
        self.assertIsNone(gen.extract_teams_from_summary("... - ... [CL]"))

    def test_filter_excludes_rennes_and_false_positives(self) -> None:
        clubs = set(gen.SEED_FRENCH_CLUBS) - gen.EXCLUDED_CLUBS
        events = gen.filter_european_events([SAMPLE_ICS, SAMPLE_ICS], clubs)
        uids = [gen.extract_field(ev, "UID") for ev in events]

        # Chronological order, deduplicated, Rennes & Dinamo Brest excluded.
        self.assertEqual(
            uids,
            ["psg-1@maak-agenda.nl", "monaco-postponed@maak-agenda.nl"],
        )

    def test_build_vcalendar_uses_crlf_and_folds_long_lines(self) -> None:
        clubs = set(gen.SEED_FRENCH_CLUBS) - gen.EXCLUDED_CLUBS
        events = gen.filter_european_events([SAMPLE_ICS], clubs)
        ics = gen.build_vcalendar(events)

        self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(ics.endswith("END:VCALENDAR\r\n"))
        for physical_line in ics.split("\r\n"):
            self.assertLessEqual(len(physical_line.encode("utf-8")), 75)


if __name__ == "__main__":
    unittest.main()
