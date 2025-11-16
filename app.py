
import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEAGUES_DIR = os.path.join(BASE_DIR, "data", "leagues")
os.makedirs(LEAGUES_DIR, exist_ok=True)


def slugify_league(name: str) -> str:
    return (
        name.lower()
        .strip()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
    )


def load_league_rows(league_name: str):
    slug = slugify_league(league_name)
    path = os.path.join(LEAGUES_DIR, f"{slug}.csv")
    if not os.path.exists(path):
        return []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        return list(reader)


def normalize_name(name: str) -> str:
    return (
        name.lower()
        .replace("-", " ")
        .replace(".", "")
        .replace(" fc", "")
        .replace(" sc", "")
        .replace(" ac", "")
        .replace(" cf", "")
        .replace(" u19", "")
        .replace(" u20", "")
        .strip()
    )


def find_team_row(rows, team_name: str, team_col: str):
    target = normalize_name(team_name)
    best = None
    for row in rows:
        row_team = row.get(team_col, "")
        if normalize_name(row_team) == target:
            best = row
            break
    return best


def detect_team_column(fieldnames):
    if not fieldnames:
        return None
    lowered = {c.lower(): c for c in fieldnames}
    candidates = ["team", "teams", "nome", "name", "club", "clube", "equipe", "squad", "team_name", "club_name"]
    for key in candidates:
        for lf, orig in lowered.items():
            if key in lf:
                return orig
    return fieldnames[0]


def parse_form(row):
    form_str = (row.get("form") or "").strip()
    if not form_str:
        return []
    parts = [p.strip().upper() for p in form_str.split(",") if p.strip()]
    return parts[:5]


def to_float(row, key, default=0.0):
    try:
        return float(row.get(key, default) or default)
    except (ValueError, TypeError):
        return default


def build_match_object(league_name, home_row, away_row):
    home_form = parse_form(home_row)
    away_form = parse_form(away_row)

    home_win = to_float(home_row, "win_prob", 40.0)
    draw = to_float(home_row, "draw_prob", 25.0)
    away_win = to_float(home_row, "lose_prob", 35.0)

    goals = {
        "over15": to_float(home_row, "over15", 70.0),
        "over25": to_float(home_row, "over25", 60.0),
        "btts": to_float(home_row, "btts", 65.0),
        "away_over15": to_float(away_row, "over15", 65.0),
        "away_over25": to_float(away_row, "over25", 55.0),
        "away_btts": to_float(away_row, "btts", 60.0),
    }

    corners = {
        "home_over85": to_float(home_row, "corners_over85", 68.0),
        "home_over95": to_float(home_row, "corners_over95", 60.0),
        "away_over85": to_float(away_row, "corners_over85", 62.0),
        "away_over95": to_float(away_row, "corners_over95", 55.0),
    }

    shots = {
        "home_for": to_float(home_row, "shots_for", 5.0),
        "home_against": to_float(home_row, "shots_against", 3.0),
        "away_for": to_float(away_row, "shots_for", 4.0),
        "away_against": to_float(away_row, "shots_against", 4.0),
    }

    cards = {
        "home_for": to_float(home_row, "cards_for", 2.0),
        "home_against": to_float(home_row, "cards_against", 2.0),
        "away_for": to_float(away_row, "cards_for", 2.0),
        "away_against": to_float(away_row, "cards_against", 2.0),
    }

    ht_goals_pct = to_float(home_row, "ht_goals_scored_pct", 0.0)
    trigger_corners = ht_goals_pct >= 70.0

    home_rpg = to_float(home_row, "rpg", 1.5)
    away_rpg = to_float(away_row, "rpg", 1.2)

    if abs(home_rpg - away_rpg) > 0.15 and home_rpg > away_rpg:
        recommendation = "Melhor aposta: 1 (mandante)."
    elif abs(home_rpg - away_rpg) > 0.15 and away_rpg > home_rpg:
        recommendation = "Melhor aposta: 2 (visitante)."
    else:
        recommendation = "Cenário equilibrado: aposta conservadora X1 ou X2."

    prompt_lines = []

    prompt_lines.append(
        f"O {home_row.get('team', home_row.get('nome', 'time da casa'))} vem com força RPG {home_rpg:.2f}, "
        f"enquanto o {away_row.get('team', away_row.get('nome', 'time visitante'))} apresenta RPG {away_rpg:.2f}."
    )

    if home_form:
        prompt_lines.append(
            f"Jogando em casa, o {home_row.get('team', 'mandante')} vive boa fase "
            f"nos últimos jogos: {'-'.join(home_form)}."
        )

    if goals['over25'] >= 65 or goals['away_over25'] >= 65:
        prompt_lines.append("Tendência de gols elevada, com forte cenário para Over 2.5 gols.")
    elif goals['over15'] >= 70:
        prompt_lines.append("Cenário sólido para Over 1.5 gols na partida.")

    if cards["home_for"] + cards["away_for"] >= 4:
        prompt_lines.append("Partida com perfil mais pegado, sugerindo boa chance de cartões.")

    if trigger_corners:
        prompt_lines.append(
            "[GATILHO ⚠] Mandante ≥ 70% gols no HT → pressão alta no 1º tempo. "
            "Boa oportunidade para Over 1.5 escanteios do time mandante."
        )

    prompt_text = " ".join(prompt_lines)

    match = {
        "league": league_name,
        "home": {
            "name": home_row.get("team", home_row.get("nome", "Time Casa")),
            "position": home_row.get("position", "-"),
            "rpg": home_rpg,
            "form": home_form,
            "logo_url": home_row.get("logo_url", ""),
        },
        "away": {
            "name": away_row.get("team", away_row.get("nome", "Time Fora")),
            "position": away_row.get("position", "-"),
            "rpg": away_rpg,
            "form": away_form,
            "logo_url": away_row.get("logo_url", ""),
        },
        "probabilities": {
            "home_win": home_win,
            "draw": draw,
            "away_win": away_win,
        },
        "goals": goals,
        "corners": corners,
        "shots": shots,
        "cards": cards,
        "trigger_corners": trigger_corners,
        "recommendation": recommendation,
        "prompt": prompt_text,
        "h2h_history": [],
    }

    return match


def get_daily_tips():
    return [
        {
            "icon": "🔥",
            "title": "Over 1.5 gols",
            "subtitle": "Jogo com forte tendência ofensiva",
            "description": "Ambas as equipes chegam com médias altas de gols marcados.",
            "tag": "Alta confiança",
            "confidence": 82,
        },
        {
            "icon": "✅",
            "title": "Casa vence",
            "subtitle": "Mandante em grande fase",
            "description": "Sequência positiva em casa + vantagem de RPG.",
            "tag": "Favorito",
            "confidence": 78,
        },
    ]


def get_multiple_bets():
    return [
        {
            "title": "Favorito + Over 1.5",
            "subtitle": "Casa vence & +1.5 gols",
            "description": "Time mandante dominante e partida com boa média de gols.",
            "tag": "Combo seguro",
            "confidence": 75,
        },
        {
            "title": "Dupla chance + BTTS",
            "subtitle": "X2 & Ambas marcam",
            "description": "Visitante consistente e defesas vulneráveis.",
            "tag": "Risco moderado",
            "confidence": 70,
        },
    ]


@app.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html",
        daily_tips=get_daily_tips(),
        multiple_bets=get_multiple_bets(),
        match=None,
        selected_league="",
        selected_home="",
        selected_away="",
    )


@app.route("/analisar", methods=["POST"])
def analisar():
    league = request.form.get("league", "").strip()
    home_team = request.form.get("home_team", "").strip()
    away_team = request.form.get("away_team", "").strip()

    rows = load_league_rows(league)
    if not rows:
        flash("Nenhum CSV encontrado para essa liga. Verifique o nome ou importe a liga.")
        return redirect(url_for("index"))

    fieldnames = rows[0].keys()
    team_col = detect_team_column(fieldnames)

    home_row = find_team_row(rows, home_team, team_col)
    away_row = find_team_row(rows, away_team, team_col)

    if not home_row or not away_row:
        flash("Não foi possível encontrar um dos times no CSV da liga.")
        return redirect(url_for("index"))

    match = build_match_object(league, home_row, away_row)

    return render_template(
        "index.html",
        daily_tips=get_daily_tips(),
        multiple_bets=get_multiple_bets(),
        match=match,
        selected_league=league,
        selected_home=home_team,
        selected_away=away_team,
    )


@app.route("/importar_liga", methods=["POST"])
def importar_liga():
    league_name = request.form.get("league_name", "").strip()
    file = request.files.get("file")

    if not league_name or not file:
        flash("Informe o nome da liga e selecione o arquivo CSV.")
        return redirect(url_for("index"))

    slug = slugify_league(league_name)
    path = os.path.join(LEAGUES_DIR, f"{slug}.csv")
    file.save(path)
    flash(f"Liga '{league_name}' importada com sucesso!")
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
