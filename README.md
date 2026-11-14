# 🇪🇺 Clubs français en Coupes d'Europe — Flux ICS (hors Rennes)

Flux `.ics` mis à jour automatiquement une fois par semaine (lundi à 6h UTC) via GitHub Actions et servi sur GitHub Pages.

## Abonnement Google Agenda

1. Ouvrir **Google Agenda** → **Autres agendas (+)** → **À partir de l'URL** (`https://calendar.google.com/calendar/u/0/r/settings/addbyurl`).
2. Coller l'URL du flux :
   `https://pierre-lebihan.github.io/clubs-fr-europe-ics/calendar.ics`
3. Cliquer sur **Ajouter l'agenda**.

## Ce que contient le flux

- **Sources :** flux officiels Fixtur.es pour la Ligue des Champions (`[CL]`), la Ligue Europa (`[EL]`) et la Ligue Conférence (`[Conf]`).
- **Filtrage :** uniquement les matchs impliquant un club français (découverts dynamiquement depuis les flux Ligue 1 & Ligue 2 de Fixtur.es + liste de secours).
- **Exclusions :** `Stade Rennais` est explicitement exclu pour éviter les doublons avec un calendrier dédié au club.

## Développement local

```bash
python3 -m unittest discover -s tests -v
python3 scripts/generate_ics.py
```
