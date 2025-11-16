
import os
import csv
import time
from typing import Dict, Any, Optional

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEAGUES_DIR = os.path.join(BASE_DIR, "data", "leagues")
os.makedirs(LEAGUES_DIR, exist_ok=True)

SOFASCORE_BASE = os.environ.get("SOFASCORE_BASE_URL", "https://api.sofascore.com/api/v1")


def _build_proxies_list():
    proxies = []
    p1 = os.environ.get("PROXY_PRIMARY")
    p2 = os.environ.get("PROXY_SECONDARY")

    if p1:
        proxies.append({"http": p1, "https": p1})
    if p2:
        proxies.append({"http": p2, "https": p2})

    return proxies


def sofascore_get(url: str) -> Optional[Dict[str, Any]]:
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (H2H Predictor Bot)",
        "Accept": "application/json, text/plain, */*",
    }

    proxies_list = _build_proxies_list()
    attempts = [None] + proxies_list

    for proxy_cfg in attempts:
        try:
            kwargs = {"headers": headers, "timeout": 15}
            if proxy_cfg:
                kwargs["proxies"] = proxy_cfg

            resp = session.get(url, **kwargs)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"[SofaScore] HTTP {resp.status_code} para {url}")
        except Exception as e:
            print(f"[SofaScore] Erro com proxy {proxy_cfg}: {e}")

        time.sleep(1)

    print(f"[SofaScore] Falha geral ao acessar {url}")
    return None


def _safe_avg(stat_block: Dict[str, Any]) -> float:
    if not isinstance(stat_block, dict):
        return 0.0

    total = (
        stat_block.get("total")
        or stat_block.get("goals")
        or stat_block.get("value")
        or 0
    )
    matches = (
        stat_block.get("matches")
        or stat_block.get("appearances")
        or stat_block.get("played")
        or 0
    )
    try:
        total = float(total)
        matches = float(matches)
    except (ValueError, TypeError):
        return 0.0

    if matches <= 0:
        return 0.0
    return total / matches


def normalize_name(name: str) -> str:
    return (
        str(name)
        .lower()
        .replace("-", " ")
        .replace(".", "")
        .replace(" fc", "")
        .replace(" sc", "")
        .replace(" ac", "")
        .replace(" cf", "")
        .replace(" u19", "")
        .replace(" u20", "")
        .replace(" u21", "")
        .replace(" u23", "")
        .replace("junior", "")
        .replace("sub ", "")
        .strip()
    )


def detect_team_column(fieldnames):
    if not fieldnames:
        return None
    lowered = {c.lower(): c for c in fieldnames}
    candidates = ["team", "teams", "nome", "name", "club", "clube", "equipe", "squad", "team_name", "club_name"]
    for key in candidates:
        for lf, orig in lowered.items():
            if key in lf:
                return orig
    return list(fieldnames)[0]


def carregar_times_liga(league_id: int, season_id: int):
    url = f"{SOFASCORE_BASE}/unique-tournament/{league_id}/season/{season_id}/standings/total"
    data = sofascore_get(url)
    if not data:
        return {}

    teams_map = {}
    standings = data.get("standings") or data.get("standingsTable") or []
    if isinstance(standings, list):
        groups = standings
    else:
        groups = standings.get("tables") or []

    for group in groups:
        rows = group.get("rows") or []
        for row in rows:
            team = row.get("team") or {}
            team_id = team.get("id")
            name = team.get("name")
            if not team_id or not name:
                continue
            key = normalize_name(name)
            teams_map[key] = int(team_id)

    return teams_map


def buscar_estatisticas_sofascore(row: Dict[str, Any]) -> Dict[str, float]:
    team_id = row.get("sofascore_team_id") or row.get("team_id")
    season_id = row.get("sofascore_season_id") or row.get("season_id")

    if not team_id or not season_id:
        return {}

    try:
        team_id_int = int(str(team_id).strip())
        season_id_int = int(str(season_id).strip())
    except ValueError:
        print(f"[Update] IDs inválidos no CSV: team_id={team_id}, season_id={season_id}")
        return {}

    url = f"{SOFASCORE_BASE}/team/{team_id_int}/statistics/season/{season_id_int}"
    data = sofascore_get(url)
    if not data:
        return {}

    stats = (
        data.get("statistics")
        or data.get("teamStatistics")
        or data.get("data")
        or {}
    )

    overall = stats.get("overall") if isinstance(stats, dict) else {}
    if not isinstance(overall, dict) or not overall:
        overall = stats if isinstance(stats, dict) else {}

    corners_block = overall.get("corners") or {}
    avg_corners = _safe_avg(corners_block)

    shots_on_block = overall.get("shotsOnTarget") or {}
    shots_off_block = overall.get("shotsOffTarget") or {}
    avg_shots_on = _safe_avg(shots_on_block)
    avg_shots_off = _safe_avg(shots_off_block)
    avg_shots_total = avg_shots_on + avg_shots_off

    yellow_block = overall.get("yellowCards") or {}
    red_block = overall.get("redCards") or {}
    avg_yellow = _safe_avg(yellow_block)
    avg_red = _safe_avg(red_block)
    avg_cards_total = avg_yellow + avg_red

    goals_scored_block = overall.get("goalsScored") or {}
    try:
        total_goals_scored = float(goals_scored_block.get("total") or 0)
    except (ValueError, TypeError):
        total_goals_scored = 0.0

    periods = goals_scored_block.get("periods") if isinstance(goals_scored_block, dict) else {}
    first_half_goals = 0.0
    if isinstance(periods, dict):
        first_half_goals = float(
            periods.get("first")
            or periods.get("firstHalf")
            or 0
        )

    if total_goals_scored > 0:
        ht_goals_pct = (first_half_goals / total_goals_scored) * 100.0
    else:
        ht_goals_pct = 0.0

    if avg_corners >= 10:
        corners_over85 = 75.0
        corners_over95 = 65.0
    elif avg_corners >= 9:
        corners_over85 = 68.0
        corners_over95 = 58.0
    elif avg_corners >= 8:
        corners_over85 = 60.0
        corners_over95 = 50.0
    else:
        corners_over85 = 50.0
        corners_over95 = 42.0

    return {
        "corners_over85": round(corners_over85, 1),
        "corners_over95": round(corners_over95, 1),
        "shots_for": round(avg_shots_total, 2),
        "shots_against": float(row.get("shots_against") or 0),
        "cards_for": round(avg_cards_total, 2),
        "cards_against": float(row.get("cards_against") or 0),
        "ht_goals_scored_pct": round(ht_goals_pct, 1),
    }


def atualizar_csvs_via_sofascore():
    print("🔍 Atualizando CSVs na pasta leagues/...")

    for filename in os.listdir(LEAGUES_DIR):
        if not filename.endswith(".csv"):
            continue

        path = os.path.join(LEAGUES_DIR, filename)
        print(f"📄 Atualizando {filename}...")

        linhas = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            fieldnames = reader.fieldnames or []
            for row in reader:
                linhas.append(row)

        if not linhas:
            print(f"⚠ CSV {filename} vazio, pulando.")
            continue

        league_id = None
        season_id = None
        if "sofascore_league_id" in fieldnames:
            league_id = linhas[0].get("sofascore_league_id")
        if "sofascore_season_id" in fieldnames:
            season_id = linhas[0].get("sofascore_season_id")

        league_team_map = {}
        if league_id and season_id:
            try:
                league_team_map = carregar_times_liga(int(league_id), int(season_id))
            except ValueError:
                print(f"[Update] Liga/season ID inválidos em {filename}")

        team_col = detect_team_column(fieldnames)

        if league_team_map:
            for row in linhas:
                name = row.get(team_col)
                if not name:
                    continue
                key = normalize_name(name)
                team_id = league_team_map.get(key)
                if team_id and not row.get("sofascore_team_id"):
                    row["sofascore_team_id"] = team_id
                if season_id and not row.get("sofascore_season_id"):
                    row["sofascore_season_id"] = season_id

        novas_colunas = [
            "sofascore_team_id",
            "sofascore_season_id",
            "corners_over85",
            "corners_over95",
            "shots_for",
            "shots_against",
            "cards_for",
            "cards_against",
            "ht_goals_scored_pct",
        ]

        for col in novas_colunas:
            if col not in fieldnames:
                fieldnames.append(col)

        for row in linhas:
            stats = buscar_estatisticas_sofascore(row)
            if not stats:
                continue
            for k, v in stats.items():
                row[k] = v

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(linhas)

        print(f"✅ {filename} atualizado.")

    print("✅ Finalizado ciclo de atualização de todos os CSVs.")


if __name__ == "__main__":
    atualizar_csvs_via_sofascore()
