"""
app.py
------
"Where Should I Serve?" — missionary field placement tool.

Starts with a short questionnaire to understand the user's background and
calling, then recommends the top 5 countries with the highest need for
missionaries that best match the user's profile.

Run with:
    python app.py

Then open http://127.0.0.1:8050 in your browser.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc

from src.clean import load_and_clean, load_countries

# ── App init ──────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Where Should I Serve?",
    suppress_callback_exceptions=True,
)

# ── Load data at startup ──────────────────────────────────────────────────────
print("Loading people group data...")
DF = load_and_clean()
print("Loading country-level data...")
COUNTRIES_DF = load_countries()   # one row per country; empty DF if unavailable
print("Data loaded.\n")

# ── Static option lists ───────────────────────────────────────────────────────
REGIONS   = sorted(DF["RegionName"].dropna().unique())
RELIGIONS = sorted(DF["PrimaryReligion"].dropna().unique())

# Languages spoken by at least 5 groups (keeps the list manageable)
_lang_counts = DF["PrimaryLanguageName"].value_counts()
LANGUAGES = sorted(_lang_counts[_lang_counts >= 5].index.tolist())

RELIGION_COLORS = {
    "Islam":           "#E05A2B",
    "Hinduism":        "#E8A020",
    "Buddhism":        "#5B8DD9",
    "Ethnic Religions":"#7CB87A",
    "Christianity":    "#5271C4",
    "Non-Religious":   "#9E9E9E",
    "Other/Small":     "#B06BB0",
    "Unknown":         "#CCCCCC",
}

BIBLE_STATUS_LABELS = {
    0: "No scripture",
    1: "No scripture",
    2: "Portions only",
    3: "New Testament",
    4: "Bible portions",
    5: "Complete Bible",
}

RANK_COLORS    = ["#C9A84C", "#8A9BA8", "#CD7F32", "#5B8DD9", "#7CB87A"]
# Light pastel backgrounds paired with dark text — all exceed WCAG AA (4.5:1)
RANK_BADGE_BG  = ["#FDF3D6", "#E8EDF1", "#FAE8D1", "#DCE9F8", "#DCEEDD"]

# Maps user-facing continent labels to the JP RegionName values they cover.
# "Africa, North and Middle East" is kept as its own MENA bucket so users
# can exclude it independently of sub-Saharan Africa.
CONTINENT_TO_REGIONS = {
    "Africa (Sub-Saharan)":       ["Africa, East and Southern",
                                   "Africa, West and Central"],
    "Middle East & North Africa": ["Africa, North and Middle East"],
    "Asia":                       ["Asia, Central", "Asia, South",
                                   "Asia, Southeast"],
    "Americas":                   ["America, Latin",
                                   "America, North and Caribbean"],
    "Europe":                     ["Europe, Eastern and Eurasia",
                                   "Europe, Western"],
    "Oceania / Pacific":          ["Australia and Pacific"],
}

# ── Scoring / recommendation engine ──────────────────────────────────────────
def score_countries(regions, religions, languages, frontier_focus,
                    exclude_continents=None):
    """
    Return the top-5 country records ranked by missionary need weighted by
    how closely the user's preferences match that country.

    Need score (0–1):
        40% unreached population share
        35% gospel gap  (1 – avg evangelical %)
        25% frontier density

    Preference multipliers applied on top:
        2.0× — region is in user's selected regions
        1.8× — country has groups matching user's chosen religions
        1.5× — country has groups speaking one of the user's languages

    exclude_continents removes every JP region mapped to the selected
    continents before any scoring takes place.

    Returns a list of dicts (one per top-5 country).
    """
    dff = DF.copy()

    if exclude_continents:
        excluded_regions = [
            region
            for continent in exclude_continents
            for region in CONTINENT_TO_REGIONS.get(continent, [])
        ]
        dff = dff[~dff["RegionName"].isin(excluded_regions)]

    if frontier_focus == "frontier":
        dff = dff[dff["Frontier"] == True]
    elif frontier_focus == "unreached":
        dff = dff[dff["LeastReached"] == True]
    # "any" keeps all groups

    if dff.empty:
        return []

    def _agg(g):
        pop_total = g["Population"].sum()
        avg_evang = (
            (g["PercentEvangelical"] * g["Population"]).sum() / pop_total
            if pop_total > 0 else 0.0
        )
        country_urls = g["CountryURL"].dropna() if "CountryURL" in g.columns else pd.Series([], dtype=str)
        return pd.Series({
            "RegionName":    g["RegionName"].mode().iloc[0] if len(g) > 0 else "",
            "NumGroups":     len(g),
            "NumFrontier":   int(g["Frontier"].sum()),
            "TotalPop":      int(pop_total),
            "AvgEvangelical": float(avg_evang),
            "Religions":     g["PrimaryReligion"].value_counts().index[:5].tolist(),
            "Languages":     g["PrimaryLanguageName"].value_counts().index[:5].tolist(),
            "CountryURL":    country_urls.iloc[0] if len(country_urls) > 0 else "",
            "TopGroups":     (
                g.nlargest(3, "Population")
                 [["PeopNameInCountry", "PrimaryReligion", "Population"]]
                 .to_dict("records")
            ),
        })

    agg = dff.groupby("Ctry").apply(_agg).reset_index()

    # Need components (each 0–1)
    max_pop      = agg["TotalPop"].max() or 1
    max_frontier = agg["NumFrontier"].max() or 1
    pop_norm        = agg["TotalPop"] / max_pop
    gospel_gap      = 1.0 - (agg["AvgEvangelical"] / 100).clip(0, 1)
    frontier_density = agg["NumFrontier"] / max_frontier

    agg["need_score"] = (
        0.40 * pop_norm +
        0.35 * gospel_gap +
        0.25 * frontier_density
    )

    # Preference multipliers
    agg["multiplier"]    = 1.0
    agg["match_reasons"] = [[] for _ in range(len(agg))]

    if regions:
        mask = agg["RegionName"].isin(regions)
        agg.loc[mask, "multiplier"] *= 2.0
        for idx in agg.index[mask]:
            agg.at[idx, "match_reasons"].append(
                f"Region: {agg.at[idx, 'RegionName']}"
            )

    if religions:
        mask = agg["Religions"].apply(
            lambda r_list: any(r in religions for r in r_list)
        )
        agg.loc[mask, "multiplier"] *= 1.8
        for idx in agg.index[mask]:
            matched = [r for r in agg.at[idx, "Religions"] if r in religions]
            agg.at[idx, "match_reasons"].append(
                "Religion: " + ", ".join(matched[:2])
            )

    if languages:
        mask = agg["Languages"].apply(
            lambda l_list: any(l in languages for l in l_list)
        )
        agg.loc[mask, "multiplier"] *= 1.5
        for idx in agg.index[mask]:
            matched = [l for l in agg.at[idx, "Languages"] if l in languages]
            agg.at[idx, "match_reasons"].append(
                "Language: " + ", ".join(matched[:2])
            )

    agg["final_score"] = agg["need_score"] * agg["multiplier"]
    top5 = agg.nlargest(5, "final_score")
    return top5.to_dict("records")


# ── Shared header ─────────────────────────────────────────────────────────────
def _header(subtitle):
    return dbc.Row(dbc.Col(html.Div(
        style={"backgroundColor": "#1A2B45", "padding": "18px 32px", "marginBottom": "32px"},
        children=[
            html.H4("Where Should I Serve?",
                    style={"color": "#FFFFFF", "margin": 0, "fontWeight": "500"}),
            html.P(subtitle,
                   style={"color": "#A0AEC0", "margin": "4px 0 0", "fontSize": "13px"}),
        ],
    )))


# ── Page 1: Questionnaire ─────────────────────────────────────────────────────
def make_questionnaire_layout(init_regions=None, init_languages=None,
                               init_religions=None, init_frontier="unreached",
                               init_exclude_continents=None):
    card_style = {
        "border": "none",
        "borderRadius": "12px",
        "boxShadow": "0 2px 12px rgba(0,0,0,0.08)",
        "marginBottom": "16px",
        "padding": "24px 32px",
    }
    label_style = {"fontWeight": "600", "color": "#1A2B45", "marginBottom": "4px"}
    hint_style  = {"fontSize": "12px", "color": "#718096", "marginBottom": "12px"}

    return dbc.Container(
        fluid=True,
        style={"backgroundColor": "#F0F4F8", "minHeight": "100vh", "padding": "0"},
        children=[
            _header("Answer a few questions to find your best mission field match"),
            dbc.Row(justify="center", children=[
                dbc.Col(width=10, lg=7, children=[

                    # Intro blurb
                    dbc.Card(style=card_style, children=[
                        html.P(
                            "This tool draws on data from over 17,000 people groups across "
                            "250+ countries to match you with mission fields where your "
                            "background and calling can have the most impact.",
                            style={"fontSize": "14px", "color": "#4A5568", "marginBottom": "4px"},
                        ),
                        html.P(
                            "All questions are optional — great matches are still possible "
                            "with limited input.",
                            style={"fontSize": "13px", "color": "#718096",
                                   "marginBottom": "0", "fontStyle": "italic"},
                        ),
                    ]),

                    # Q1 — Regions
                    dbc.Card(style=card_style, children=[
                        html.H6("1. Which regions of the world interest you?",
                                style=label_style),
                        html.P("Select any that feel like a calling — leave blank to consider all regions.",
                               style=hint_style),
                        dcc.Dropdown(
                            id="q-regions",
                            options=[{"label": r, "value": r} for r in REGIONS],
                            value=init_regions,
                            multi=True,
                            placeholder="Select regions...",
                            style={"fontSize": "13px"},
                        ),
                    ]),

                    # Q2 — Languages
                    dbc.Card(style=card_style, children=[
                        html.H6("2. What languages do you speak?",
                                style=label_style),
                        html.P("Speaking a local language creates deeper ministry relationships.",
                               style=hint_style),
                        dcc.Dropdown(
                            id="q-languages",
                            options=[{"label": l, "value": l} for l in LANGUAGES],
                            value=init_languages,
                            multi=True,
                            placeholder="Select languages (besides English)...",
                            style={"fontSize": "13px"},
                        ),
                    ]),

                    # Q3 — Religions
                    dbc.Card(style=card_style, children=[
                        html.H6("3. Which religious communities do you feel called to reach?",
                                style=label_style),
                        html.P("Helps us prioritise countries where those communities are most present.",
                               style=hint_style),
                        dcc.Dropdown(
                            id="q-religions",
                            options=[{"label": r, "value": r} for r in RELIGIONS],
                            value=init_religions,
                            multi=True,
                            placeholder="Select religious communities...",
                            style={"fontSize": "13px"},
                        ),
                    ]),

                    # Q4 — Mission focus
                    dbc.Card(style=card_style, children=[
                        html.H6("4. What is your calling priority?", style=label_style),
                        html.P(
                            "Frontier groups (< 0.1% evangelical) have the fewest gospel "
                            "resources of any people on earth.",
                            style=hint_style,
                        ),
                        dbc.RadioItems(
                            id="q-frontier",
                            options=[
                                {"label": "Frontier groups — the least reached of the least reached",
                                 "value": "frontier"},
                                {"label": "Unreached groups broadly — any group under 2% evangelical",
                                 "value": "unreached"},
                                {"label": "Open to any — show me the highest overall need",
                                 "value": "any"},
                            ],
                            value=init_frontier,
                            style={"fontSize": "13px"},
                        ),
                    ]),

                    # Q5 — Continent exclusions
                    dbc.Card(style={**card_style, "marginBottom": "24px"}, children=[
                        html.H6("5. Are there any continents you do not want to serve in?",
                                style=label_style),
                        html.P(
                            "Countries in these regions will be removed from your results entirely.",
                            style=hint_style,
                        ),
                        dcc.Dropdown(
                            id="q-exclude-continents",
                            options=[{"label": c, "value": c}
                                     for c in CONTINENT_TO_REGIONS],
                            value=init_exclude_continents,
                            multi=True,
                            placeholder="Select continents to exclude (or leave blank)...",
                            style={"fontSize": "13px"},
                        ),
                    ]),

                    # Submit
                    dbc.Row(justify="end", children=[
                        dbc.Col(width="auto", children=[
                            dbc.Button(
                                "Find my top mission fields →",
                                id="submit-btn",
                                size="lg",
                                style={
                                    "backgroundColor": "#1A2B45",
                                    "border": "none",
                                    "borderRadius": "8px",
                                    "padding": "12px 28px",
                                    "fontSize": "14px",
                                    "fontWeight": "500",
                                },
                            ),
                        ]),
                    ]),
                    html.Div(style={"height": "48px"}),
                ]),
            ]),
        ],
    )


# ── Page 2: Results ───────────────────────────────────────────────────────────
def make_results_layout(top5, prefs):
    rank_labels = ["#1 Match", "#2 Match", "#3 Match", "#4 Match", "#5 Match"]

    cards = []
    for i, rec in enumerate(top5):
        color  = RANK_COLORS[i]
        religions_str = ", ".join(rec.get("Religions", [])[:3]) or "Varies"
        languages_str = ", ".join(rec.get("Languages", [])[:3]) or "Varies"
        reasons       = rec.get("match_reasons", [])

        group_rows = [
            html.Tr([
                html.Td(g["PeopNameInCountry"],
                        style={"fontSize": "12px", "paddingBottom": "4px",
                               "paddingRight": "12px"}),
                html.Td(g["PrimaryReligion"],
                        style={"fontSize": "12px", "color": "#718096",
                               "paddingBottom": "4px", "paddingRight": "12px"}),
                html.Td(f"{int(g['Population']):,}",
                        style={"fontSize": "12px", "color": "#718096",
                               "paddingBottom": "4px", "textAlign": "right"}),
            ])
            for g in rec.get("TopGroups", [])
        ]

        _badge = {
            "display": "inline-block",
            "backgroundColor": "#DCE9F8",
            "color": "#1A2B45",
            "fontWeight": "500",
            "fontSize": "11px",
            "padding": "2px 8px",
            "borderRadius": "4px",
            "marginRight": "4px",
            "marginBottom": "4px",
        }
        reason_badges = [
            html.Span(r, style=_badge)
            for r in reasons
        ] if reasons else [
            html.Span("Matched on overall need",
                      style={"fontSize": "11px", "color": "#718096", "fontStyle": "italic"})
        ]

        cards.append(dbc.Card(
            style={"border": "none", "borderRadius": "12px",
                   "boxShadow": "0 2px 12px rgba(0,0,0,0.08)",
                   "marginBottom": "16px", "overflow": "hidden"},
            children=[
                html.Div(style={"backgroundColor": color, "height": "4px"}),
                dbc.CardBody(style={"padding": "20px 24px"}, children=[

                    # Title row
                    dbc.Row([
                        dbc.Col([
                            html.Span(rank_labels[i], style={
                                "display": "inline-block",
                                "backgroundColor": RANK_BADGE_BG[i],
                                "color": "#1A2B45",
                                "fontWeight": "600",
                                "fontSize": "11px",
                                "padding": "2px 8px",
                                "borderRadius": "4px",
                                "marginBottom": "6px",
                            }),
                            html.H5(
                                html.A(
                                    rec["Ctry"],
                                    href=rec.get("CountryURL") or "#",
                                    target="_blank",
                                    style={"color": "#1A2B45", "textDecoration": "none",
                                           "borderBottom": "1px solid #CBD5E0"},
                                ),
                                style={"fontWeight": "600", "marginBottom": "2px"},
                            ),
                            html.P(rec.get("RegionName", ""),
                                   style={"fontSize": "12px", "color": "#718096",
                                          "marginBottom": "10px"}),
                            html.Div(reason_badges),
                        ], width=8),
                        dbc.Col([
                            html.P(f"{rec['TotalPop']:,}",
                                   style={"fontSize": "22px", "fontWeight": "600",
                                          "color": "#1A2B45", "margin": "0",
                                          "textAlign": "right"}),
                            html.P("unreached population",
                                   style={"fontSize": "11px", "color": "#718096",
                                          "margin": "0", "textAlign": "right"}),
                        ], width=4,
                           style={"display": "flex", "flexDirection": "column",
                                  "alignItems": "flex-end", "justifyContent": "center"}),
                    ]),

                    # Stats strip
                    html.Hr(style={"margin": "12px 0"}),
                    dbc.Row(style={"marginBottom": "12px"}, children=[
                        dbc.Col([
                            html.P(f"{rec['NumGroups']:,}",
                                   style={"fontSize": "16px", "fontWeight": "600",
                                          "color": "#1A2B45", "margin": "0"}),
                            html.P("unreached groups",
                                   style={"fontSize": "11px", "color": "#718096", "margin": "0"}),
                        ], width=3),
                        dbc.Col([
                            html.P(f"{rec['NumFrontier']:,}",
                                   style={"fontSize": "16px", "fontWeight": "600",
                                          "color": "#E05A2B", "margin": "0"}),
                            html.P("frontier groups",
                                   style={"fontSize": "11px", "color": "#718096", "margin": "0"}),
                        ], width=3),
                        dbc.Col([
                            html.P(f"{rec['AvgEvangelical']:.2f}%",
                                   style={"fontSize": "16px", "fontWeight": "600",
                                          "color": "#1A2B45", "margin": "0"}),
                            html.P("avg. evangelical",
                                   style={"fontSize": "11px", "color": "#718096", "margin": "0"}),
                        ], width=3),
                        dbc.Col([
                            html.P(f"{len(rec.get('Religions', []))}",
                                   style={"fontSize": "16px", "fontWeight": "600",
                                          "color": "#1A2B45", "margin": "0"}),
                            html.P("major religions",
                                   style={"fontSize": "11px", "color": "#718096", "margin": "0"}),
                        ], width=3),
                    ]),

                    # Religions + languages
                    dbc.Row(style={"marginBottom": "12px"}, children=[
                        dbc.Col([
                            html.P("Primary religions:",
                                   style={"fontSize": "11px", "color": "#718096",
                                          "marginBottom": "2px", "fontWeight": "500"}),
                            html.P(religions_str,
                                   style={"fontSize": "12px", "color": "#2D3748", "margin": "0"}),
                        ], width=6),
                        dbc.Col([
                            html.P("Key languages:",
                                   style={"fontSize": "11px", "color": "#718096",
                                          "marginBottom": "2px", "fontWeight": "500"}),
                            html.P(languages_str,
                                   style={"fontSize": "12px", "color": "#2D3748", "margin": "0"}),
                        ], width=6),
                    ]),

                    # Expandable people groups
                    html.Details([
                        html.Summary("Largest unreached people groups",
                                     style={"fontSize": "12px", "color": "#3182CE",
                                            "cursor": "pointer", "fontWeight": "500"}),
                        html.Table(
                            style={"width": "100%", "marginTop": "8px"},
                            children=[
                                html.Thead(html.Tr([
                                    html.Th("People Group",
                                            style={"fontSize": "11px", "color": "#718096",
                                                   "fontWeight": "500", "paddingBottom": "4px"}),
                                    html.Th("Religion",
                                            style={"fontSize": "11px", "color": "#718096",
                                                   "fontWeight": "500", "paddingBottom": "4px"}),
                                    html.Th("Population",
                                            style={"fontSize": "11px", "color": "#718096",
                                                   "fontWeight": "500", "paddingBottom": "4px",
                                                   "textAlign": "right"}),
                                ])),
                                html.Tbody(group_rows),
                            ],
                        ),
                    ]) if group_rows else html.Span(),
                ]),
            ],
        ))

    # Build prefs summary string
    parts = []
    if prefs.get("regions"):
        parts.append("Regions: " + ", ".join(prefs["regions"]))
    if prefs.get("religions"):
        parts.append("Religions: " + ", ".join(prefs["religions"]))
    if prefs.get("languages"):
        parts.append("Languages: " + ", ".join(prefs["languages"]))
    focus_map = {"frontier": "Frontier focus", "unreached": "Unreached broadly", "any": "Open to all"}
    parts.append(focus_map.get(prefs.get("frontier_focus", "unreached"), ""))
    if prefs.get("exclude_continents"):
        parts.append("Excluding: " + ", ".join(prefs["exclude_continents"]))
    summary = " · ".join(p for p in parts if p)

    return dbc.Container(
        fluid=True,
        style={"backgroundColor": "#F0F4F8", "minHeight": "100vh", "padding": "0"},
        children=[
            _header("Your top mission field matches"),
            dbc.Row(justify="center", children=[
                dbc.Col(width=10, lg=7, children=[

                    # Prefs summary + back button
                    dbc.Row(style={"marginBottom": "20px"}, children=[
                        dbc.Col([
                            html.P(f"Based on: {summary}" if summary else "Based on: Open to all",
                                   style={"fontSize": "12px", "color": "#718096", "margin": "0"}),
                        ]),
                        dbc.Col(width="auto", children=[
                            dbc.Button("← Adjust preferences",
                                       id="back-to-questionnaire",
                                       color="light", size="sm",
                                       style={"fontSize": "12px"}),
                        ]),
                    ]),

                    # Country cards
                    html.Div(cards),

                    # Link to advanced explorer
                    dbc.Card(
                        style={"border": "1px dashed #CBD5E0", "borderRadius": "12px",
                               "backgroundColor": "transparent",
                               "marginTop": "8px", "marginBottom": "48px"},
                        children=[dbc.CardBody(
                            style={"padding": "16px 24px", "textAlign": "center"},
                            children=[
                                html.P("Want to explore all unreached people groups in depth?",
                                       style={"fontSize": "13px", "color": "#4A5568",
                                              "marginBottom": "8px"}),
                                dbc.Button("Open advanced explorer →",
                                           id="go-to-dashboard",
                                           color="secondary", outline=True, size="sm",
                                           style={"fontSize": "13px"}),
                            ],
                        )],
                    ),
                ]),
            ]),
        ],
    )


# ── Page 3: Advanced dashboard ────────────────────────────────────────────────
def make_dashboard_layout():
    region_opts   = [{"label": "All regions", "value": "ALL"}] + [
        {"label": r, "value": r} for r in REGIONS]
    religion_opts = [{"label": "All religions", "value": "ALL"}] + [
        {"label": r, "value": r} for r in RELIGIONS]

    return dbc.Container(
        fluid=True,
        style={"backgroundColor": "#F8F9FA", "minHeight": "100vh", "padding": "0"},
        children=[

            # Header
            dbc.Row(dbc.Col(html.Div(
                style={"backgroundColor": "#1A2B45", "padding": "18px 32px",
                       "marginBottom": "24px"},
                children=[dbc.Row([
                    dbc.Col([
                        html.H4("Unreached People Groups Explorer",
                                style={"color": "#FFFFFF", "margin": 0, "fontWeight": "500"}),
                        html.P("A research tool for missionaries — powered by Joshua Project data",
                               style={"color": "#A0AEC0", "margin": "4px 0 0",
                                      "fontSize": "13px"}),
                    ]),
                    dbc.Col(width="auto",
                            style={"display": "flex", "alignItems": "center"},
                            children=[
                        dbc.Button("← Back to my matches",
                                   id="dashboard-back-btn",
                                   color="light", outline=True, size="sm",
                                   style={"fontSize": "12px", "color": "#A0AEC0",
                                          "borderColor": "#4A5568"}),
                    ]),
                ])],
            ))),

            # Controls
            dbc.Row(style={"padding": "0 24px", "marginBottom": "20px"}, children=[
                dbc.Col(width=4, children=[
                    html.Label("World region",
                               style={"fontSize": "12px", "fontWeight": "500",
                                      "color": "#4A5568", "marginBottom": "4px"}),
                    dcc.Dropdown(id="region-filter", options=region_opts,
                                 value="ALL", clearable=False,
                                 style={"fontSize": "13px"}),
                ]),
                dbc.Col(width=4, children=[
                    html.Label("Primary religion",
                               style={"fontSize": "12px", "fontWeight": "500",
                                      "color": "#4A5568", "marginBottom": "4px"}),
                    dcc.Dropdown(id="religion-filter", options=religion_opts,
                                 value="ALL", clearable=False,
                                 style={"fontSize": "13px"}),
                ]),
                dbc.Col(width=4, children=[
                    html.Label("Frontier groups only",
                               style={"fontSize": "12px", "fontWeight": "500",
                                      "color": "#4A5568", "marginBottom": "8px"}),
                    dbc.Switch(id="frontier-toggle", value=False, label="",
                               style={"marginTop": "4px"}),
                ]),
            ]),

            # Stats bar
            dbc.Row(id="stats-bar",
                    style={"padding": "0 24px", "marginBottom": "20px"}),

            # Choropleth + scatter
            dbc.Row(style={"padding": "0 24px", "marginBottom": "20px"}, children=[
                dbc.Col(width=7, children=[
                    dbc.Card(style={"border": "1px solid #E2E8F0", "borderRadius": "8px"},
                             children=[
                        dbc.CardHeader("Evangelical presence by country",
                                       style={"fontSize": "13px", "fontWeight": "500",
                                              "backgroundColor": "#FFFFFF",
                                              "borderBottom": "1px solid #E2E8F0"}),
                        dbc.CardBody(dcc.Graph(id="choropleth-map",
                                               style={"height": "380px"}),
                                     style={"padding": "8px"}),
                    ]),
                ]),
                dbc.Col(width=5, children=[
                    dbc.Card(style={"border": "1px solid #E2E8F0", "borderRadius": "8px"},
                             children=[
                        dbc.CardHeader("Population vs. % Evangelical (click a dot to inspect)",
                                       style={"fontSize": "13px", "fontWeight": "500",
                                              "backgroundColor": "#FFFFFF",
                                              "borderBottom": "1px solid #E2E8F0"}),
                        dbc.CardBody(dcc.Graph(id="scatter-plot",
                                               style={"height": "380px"}),
                                     style={"padding": "8px"}),
                    ]),
                ]),
            ]),

            # Bar chart + detail panel
            dbc.Row(style={"padding": "0 24px", "marginBottom": "32px"}, children=[
                dbc.Col(width=7, children=[
                    dbc.Card(style={"border": "1px solid #E2E8F0", "borderRadius": "8px"},
                             children=[
                        dbc.CardHeader("Religious makeup of countries on the map",
                                       style={"fontSize": "13px", "fontWeight": "500",
                                              "backgroundColor": "#FFFFFF",
                                              "borderBottom": "1px solid #E2E8F0"}),
                        dbc.CardBody(dcc.Graph(id="region-bar",
                                               style={"height": "300px"}),
                                     style={"padding": "8px"}),
                    ]),
                ]),
                dbc.Col(width=5, children=[
                    dbc.Card(id="detail-panel",
                             style={"border": "1px solid #E2E8F0", "borderRadius": "8px",
                                    "height": "100%"},
                             children=[
                        dbc.CardHeader("People group detail",
                                       style={"fontSize": "13px", "fontWeight": "500",
                                              "backgroundColor": "#FFFFFF",
                                              "borderBottom": "1px solid #E2E8F0"}),
                        dbc.CardBody(id="detail-content", style={"padding": "16px"},
                                     children=[html.P(
                                         "Click any dot on the scatter plot to see details.",
                                         style={"fontSize": "13px", "color": "#718096",
                                                "fontStyle": "italic"},
                                     )]),
                    ]),
                ]),
            ]),

            # Export
            dbc.Row(style={"padding": "0 24px", "marginBottom": "32px"}, children=[
                dbc.Col([
                    dbc.Button("Export current results as CSV",
                               id="export-btn", color="secondary",
                               outline=True, size="sm",
                               style={"fontSize": "13px"}),
                    dcc.Download(id="download-csv"),
                    html.Span(" Exports all people groups matching current filters",
                              style={"fontSize": "12px", "color": "#718096",
                                     "marginLeft": "12px"}),
                ]),
            ]),

            dcc.Store(id="filtered-indices"),

            # Country detail modal (opened by clicking the choropleth)
            dbc.Modal(
                id="country-modal",
                size="lg",
                is_open=False,
                scrollable=True,
                children=[
                    dbc.ModalHeader(dbc.ModalTitle(id="country-modal-title"),
                                    close_button=True),
                    dbc.ModalBody(id="country-modal-body"),
                ],
            ),

            dbc.Row(dbc.Col(html.P(
                "Data sourced from Joshua Project API (joshuaproject.net). For research use only.",
                style={"fontSize": "11px", "color": "#A0AEC0",
                       "textAlign": "center", "padding": "12px"},
            ))),
        ],
    )


# ── Root layout ───────────────────────────────────────────────────────────────
app.layout = dbc.Container(
    fluid=True,
    style={"padding": "0", "margin": "0"},
    children=[
        dcc.Store(id="user-prefs"),
        dcc.Store(id="current-page", data="questionnaire"),
        html.Div(id="page-content"),
    ],
)


# ── Routing ───────────────────────────────────────────────────────────────────
@app.callback(
    Output("page-content", "children"),
    Input("current-page", "data"),
    State("user-prefs", "data"),
)
def render_page(page, prefs):
    if page == "questionnaire":
        if prefs:
            return make_questionnaire_layout(
                init_regions=prefs.get("regions"),
                init_languages=prefs.get("languages"),
                init_religions=prefs.get("religions"),
                init_frontier=prefs.get("frontier_focus", "unreached"),
                init_exclude_continents=prefs.get("exclude_continents"),
            )
        return make_questionnaire_layout()

    if page == "results" and prefs:
        top5 = score_countries(
            prefs.get("regions") or [],
            prefs.get("religions") or [],
            prefs.get("languages") or [],
            prefs.get("frontier_focus", "unreached"),
            exclude_continents=prefs.get("exclude_continents") or [],
        )
        if not top5:
            return dbc.Container(
                style={"padding": "48px", "textAlign": "center"},
                children=[
                    html.P("No results found — try broadening your preferences.",
                           style={"color": "#718096"}),
                    dbc.Button("← Go back", id="back-to-questionnaire",
                               color="light", size="sm"),
                ],
            )
        return make_results_layout(top5, prefs)

    if page == "dashboard":
        return make_dashboard_layout()

    return make_questionnaire_layout()


@app.callback(
    Output("user-prefs", "data"),
    Output("current-page", "data"),
    Input("submit-btn", "n_clicks"),
    State("q-regions", "value"),
    State("q-languages", "value"),
    State("q-religions", "value"),
    State("q-frontier", "value"),
    State("q-exclude-continents", "value"),
    prevent_initial_call=True,
)
def submit_questionnaire(_, regions, languages, religions, frontier_focus,
                         exclude_continents):
    return (
        {
            "regions":            regions or [],
            "languages":          languages or [],
            "religions":          religions or [],
            "frontier_focus":     frontier_focus or "unreached",
            "exclude_continents": exclude_continents or [],
        },
        "results",
    )


@app.callback(
    Output("current-page", "data", allow_duplicate=True),
    Input("back-to-questionnaire", "n_clicks"),
    prevent_initial_call=True,
)
def go_back(_):
    return "questionnaire"


@app.callback(
    Output("current-page", "data", allow_duplicate=True),
    Input("go-to-dashboard", "n_clicks"),
    prevent_initial_call=True,
)
def go_to_dashboard(_):
    return "dashboard"


@app.callback(
    Output("current-page", "data", allow_duplicate=True),
    Input("dashboard-back-btn", "n_clicks"),
    prevent_initial_call=True,
)
def dashboard_back(_):
    return "results"


# ── Dashboard helpers ─────────────────────────────────────────────────────────
def _apply_filters(region, religion, frontier_only):
    dff = DF.copy()
    if region != "ALL":
        dff = dff[dff["RegionName"] == region]
    if religion != "ALL":
        dff = dff[dff["PrimaryReligion"] == religion]
    if frontier_only:
        dff = dff[dff["Frontier"] == True]
    return dff


# ── Dashboard callbacks ───────────────────────────────────────────────────────
@app.callback(
    Output("stats-bar", "children"),
    Input("region-filter", "value"),
    Input("religion-filter", "value"),
    Input("frontier-toggle", "value"),
)
def update_stats(region, religion, frontier_only):
    dff = _apply_filters(region, religion, frontier_only)
    stats = [
        ("People groups",    f"{len(dff):,}"),
        ("Total population", f"{dff['Population'].sum() / 1_000_000:.1f}M"),
        ("Frontier groups",  f"{dff['Frontier'].sum():,}"),
        ("Avg % Evangelical",f"{dff['PercentEvangelical'].mean():.2f}%"),
        ("Countries",        f"{dff['Ctry'].nunique():,}"),
    ]
    return [
        dbc.Col(dbc.Card(
            style={"border": "1px solid #E2E8F0", "borderRadius": "8px",
                   "textAlign": "center", "padding": "10px",
                   "backgroundColor": "#FFFFFF"},
            children=[
                html.P(val,   style={"fontSize": "20px", "fontWeight": "500",
                                     "margin": "0", "color": "#1A2B45"}),
                html.P(label, style={"fontSize": "11px", "color": "#718096",
                                     "margin": "0"}),
            ],
        ), width=True)
        for label, val in stats
    ]


@app.callback(
    Output("choropleth-map", "figure"),
    Input("region-filter", "value"),
    Input("religion-filter", "value"),
    Input("frontier-toggle", "value"),
)
def update_map(region, religion, frontier_only):
    dff = _apply_filters(region, religion, frontier_only)

    # Aggregate people-group counts per country from the filtered dataset.
    pg_agg = (
        dff.groupby("Ctry")
        .apply(lambda g: pd.Series({
            "TrackedGroups":   len(g),
            "FrontierCount":   int(g["Frontier"].sum()),
            "UnreachedCount":  int(g["LeastReached"].sum()),
        }))
        .reset_index()
    )

    # Prefer country-level data from the /countries.json endpoint so that
    # Population and % Evangelical reflect the whole country, not just the
    # subset of people groups that appear in the filtered view.
    use_country_level = not COUNTRIES_DF.empty and "PercentEvangelical" in COUNTRIES_DF.columns

    if use_country_level:
        # Use ALL countries from JP's country dataset so the full world map
        # is coloured — not just countries that happen to have people groups
        # surviving the current dashboard filters.
        country_df = COUNTRIES_DF.copy()
        country_df = country_df.merge(pg_agg, on="Ctry", how="left")
        for col in ("TrackedGroups", "FrontierCount", "UnreachedCount"):
            if col in country_df.columns:
                country_df[col] = country_df[col].fillna(0).astype(int)

        color_col   = "PercentEvangelical"
        color_label = "% Evangelical (country)"

        _candidate_hover = {
            "PercentEvangelical":        ":.2f",
            "PercentChristianAdherents": ":.2f",
            "PeopleGroupsLR":            True,
            "FrontierCount":             True,
            "Population":                ":,",
            "Ctry":                      False,
        }
        hover_extra = {k: v for k, v in _candidate_hover.items()
                       if k == "Ctry" or k in country_df.columns}
        labels = {
            "PercentEvangelical":        "% Evangelical",
            "PercentChristianAdherents": "% Christian adherents",
            "PeopleGroupsLR":            "Least-reached groups",
            "FrontierCount":             "Frontier groups (filtered view)",
            "Population":                "Country population",
        }
        color_range = [0, 100]
    else:
        # Fallback: build country-level colour from the full unfiltered DF so
        # all countries with JP people-group data appear on the map.  Filtered
        # counts (from dff) are merged in as supplementary hover info.
        all_country_agg = (
            DF.groupby("Ctry")
            .apply(lambda g: pd.Series({
                "PG_AvgEvangelical": (
                    (g["PercentEvangelical"] * g["Population"]).sum()
                    / g["Population"].sum()
                    if g["Population"].sum() > 0 else 0
                ),
                "TotalTracked": len(g),
            }))
            .reset_index()
        )
        country_df = all_country_agg.merge(pg_agg, on="Ctry", how="left")
        for col in ("TrackedGroups", "FrontierCount", "UnreachedCount"):
            if col in country_df.columns:
                country_df[col] = country_df[col].fillna(0).astype(int)

        color_col   = "PG_AvgEvangelical"
        color_label = "Avg % evangelical (JP-tracked groups)"
        hover_extra = {
            "PG_AvgEvangelical": ":.2f",
            "TotalTracked":      True,
            "FrontierCount":     True,
            "Ctry":              False,
        }
        labels = {
            "PG_AvgEvangelical": "Avg % Evangelical (tracked groups)",
            "TotalTracked":      "Total JP-tracked groups",
            "FrontierCount":     "Frontier groups (filtered view)",
        }
        color_range = [0, 10]

    fig = px.choropleth(
        country_df,
        locations="Ctry",
        locationmode="country names",
        color=color_col,
        hover_name="Ctry",
        hover_data=hover_extra,
        color_continuous_scale=[
            [0.0, "#B03A2E"], [0.1, "#E07B39"], [0.3, "#F0C040"],
            [0.6, "#6AAF6A"], [1.0, "#2E7D52"],
        ],
        range_color=color_range,
        labels=labels,
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(
            showframe=False, showcoastlines=True, coastlinecolor="#D0D0D0",
            showland=True, landcolor="#F0F0F0",
            showocean=True, oceancolor="#E8F4FD",
            projection_type="natural earth",
        ),
        coloraxis_colorbar=dict(
            title=dict(text=color_label, font=dict(size=11)),
            thickness=12, len=0.6,
            tickfont=dict(size=10),
        ),
    )
    return fig


# ── Callback: country modal ───────────────────────────────────────────────────
@app.callback(
    Output("country-modal", "is_open"),
    Output("country-modal-title", "children"),
    Output("country-modal-body", "children"),
    Input("choropleth-map", "clickData"),
    State("region-filter", "value"),
    State("religion-filter", "value"),
    State("frontier-toggle", "value"),
    prevent_initial_call=True,
)
def open_country_modal(click_data, region, religion, frontier_only):
    if not click_data:
        return False, "", []

    country = (click_data["points"][0].get("location")
               or click_data["points"][0].get("hovertext", ""))
    if not country:
        return False, "", []

    # People-group rows for this country (unfiltered — full picture).
    cdf = DF[DF["Ctry"] == country].copy()
    if cdf.empty:
        return False, country, [html.P("No data available for this country.",
                                       style={"color": "#718096"})]

    # Prefer country-level stats from the /countries.json endpoint.
    crow = (
        COUNTRIES_DF[COUNTRIES_DF["Ctry"] == country].iloc[0]
        if not COUNTRIES_DF.empty and (COUNTRIES_DF["Ctry"] == country).any()
        else None
    )

    if crow is not None:
        total_pop     = int(crow.get("Population") or 0)
        avg_evang     = float(crow.get("PercentEvangelical") or 0)
        pct_christian = float(crow.get("PercentChristianAdherents") or 0)
        num_lr        = int(crow.get("PeopleGroupsLR") or 0)
        num_frontier  = int(crow.get("PeopleGroupsFrontier") or cdf["Frontier"].sum())
        num_total_pg  = int(crow.get("PeopleGroups") or len(cdf))
        region_name   = str(crow.get("RegionName") or "")
        using_country_level = True
    else:
        total_pop     = int(cdf["Population"].sum())
        avg_evang     = float(
            (cdf["PercentEvangelical"] * cdf["Population"]).sum() / total_pop
            if total_pop > 0 else 0
        )
        pct_christian = None
        num_lr        = int(cdf["LeastReached"].sum())
        num_frontier  = int(cdf["Frontier"].sum())
        num_total_pg  = len(cdf)
        region_name   = cdf["RegionName"].mode().iloc[0] if len(cdf) > 0 else ""
        using_country_level = False

    num_tracked_groups = len(cdf)

    def stat_col(value, label, color="#1A2B45", width=3):
        return dbc.Col([
            html.P(value, style={"fontSize": "18px", "fontWeight": "600",
                                  "color": color, "margin": "0"}),
            html.P(label, style={"fontSize": "11px", "color": "#718096", "margin": "0"}),
        ], width=width)

    # Religion breakdown
    rel_breakdown = (
        cdf.groupby("PrimaryReligion")["Population"].sum()
           .sort_values(ascending=False)
           .reset_index()
    )
    rel_rows = [
        html.Tr([
            html.Td(r["PrimaryReligion"],
                    style={"fontSize": "12px", "paddingBottom": "4px",
                           "paddingRight": "16px"}),
            html.Td(f"{int(r['Population']):,}",
                    style={"fontSize": "12px", "color": "#718096",
                           "paddingBottom": "4px", "textAlign": "right"}),
        ])
        for _, r in rel_breakdown.iterrows()
    ]

    # Top 6 people groups by population
    top_groups = cdf.nlargest(6, "Population")
    group_rows = []
    for _, g in top_groups.iterrows():
        frontier_tag = (
            html.Span("F", style={
                "backgroundColor": "#FED7D7", "color": "#C53030",
                "fontSize": "10px", "fontWeight": "600",
                "padding": "1px 5px", "borderRadius": "3px", "marginLeft": "4px",
            })
            if g.get("Frontier") else None
        )
        group_rows.append(html.Tr([
            html.Td([g["PeopNameInCountry"], frontier_tag],
                    style={"fontSize": "12px", "paddingBottom": "6px",
                           "paddingRight": "12px"}),
            html.Td(g["PrimaryReligion"],
                    style={"fontSize": "12px", "color": "#718096",
                           "paddingBottom": "6px", "paddingRight": "12px"}),
            html.Td(f"{int(g['Population']):,}",
                    style={"fontSize": "12px", "color": "#718096",
                           "paddingBottom": "6px", "paddingRight": "12px",
                           "textAlign": "right"}),
            html.Td(f"{g['PercentEvangelical']:.1f}%",
                    style={"fontSize": "12px", "color": "#718096",
                           "paddingBottom": "6px", "textAlign": "right"}),
            html.Td(
                html.A("↗", href=g.get("JPProfileURL", "#"), target="_blank",
                       style={"color": "#3182CE", "textDecoration": "none"}),
                style={"paddingBottom": "6px", "textAlign": "center"},
            ),
        ]))

    top_languages = (
        cdf["PrimaryLanguageName"].value_counts().index[:6].tolist()
    )

    evang_label    = "% evangelical (country)" if using_country_level else "avg % evangelical (JP-tracked groups only)"
    christian_stat = stat_col(f"{pct_christian:.1f}%", "% Christian adherents", width=2) if pct_christian is not None else None

    body = html.Div([
        # Region + data-source note
        html.P(region_name,
               style={"fontSize": "12px", "color": "#718096", "marginBottom": "4px"}),
        html.P(
            "Country statistics from Joshua Project." if using_country_level
            else "Note: country-level data unavailable — showing JP-tracked people groups only.",
            style={"fontSize": "11px", "color": "#A0AEC0", "marginBottom": "16px",
                   "fontStyle": "italic"},
        ),

        # Stats strip — country-level numbers
        dbc.Row(
            [c for c in [
                stat_col(f"{total_pop:,}",    "total country population", width=3),
                stat_col(f"{avg_evang:.2f}%", evang_label,                width=3),
                christian_stat,
                stat_col(f"{num_lr:,}",       "least-reached groups", color="#C53030", width=2),
                stat_col(f"{num_frontier:,}", "frontier groups",      color="#C53030", width=2),
            ] if c is not None],
            style={"marginBottom": "20px"},
        ),

        html.Hr(style={"margin": "0 0 16px"}),

        # Religion breakdown + languages side by side
        dbc.Row([
            dbc.Col([
                html.P("Religion breakdown",
                       style={"fontSize": "12px", "fontWeight": "600",
                              "color": "#4A5568", "marginBottom": "8px"}),
                html.Table(html.Tbody(rel_rows), style={"width": "100%"}),
            ], width=6),
            dbc.Col([
                html.P("Key languages",
                       style={"fontSize": "12px", "fontWeight": "600",
                              "color": "#4A5568", "marginBottom": "8px"}),
                html.Ul([
                    html.Li(lang, style={"fontSize": "12px", "color": "#2D3748",
                                         "marginBottom": "2px"})
                    for lang in top_languages
                ], style={"paddingLeft": "16px", "margin": "0"}),
            ], width=6),
        ], style={"marginBottom": "20px"}),

        html.Hr(style={"margin": "0 0 16px"}),

        # People groups table
        html.P(f"Largest JP-tracked people groups ({num_tracked_groups} groups in dataset)",
               style={"fontSize": "12px", "fontWeight": "600",
                      "color": "#4A5568", "marginBottom": "8px"}),
        html.Table(
            style={"width": "100%"},
            children=[
                html.Thead(html.Tr([
                    html.Th("Name",       style={"fontSize": "11px", "color": "#718096",
                                                  "fontWeight": "500", "paddingBottom": "6px"}),
                    html.Th("Religion",   style={"fontSize": "11px", "color": "#718096",
                                                  "fontWeight": "500", "paddingBottom": "6px"}),
                    html.Th("Population", style={"fontSize": "11px", "color": "#718096",
                                                  "fontWeight": "500", "paddingBottom": "6px",
                                                  "textAlign": "right"}),
                    html.Th("% Evang.",   style={"fontSize": "11px", "color": "#718096",
                                                  "fontWeight": "500", "paddingBottom": "6px",
                                                  "textAlign": "right"}),
                    html.Th("Profile",    style={"fontSize": "11px", "color": "#718096",
                                                  "fontWeight": "500", "paddingBottom": "6px",
                                                  "textAlign": "center"}),
                ])),
                html.Tbody(group_rows),
            ],
        ),
        html.P("F = Frontier group (< 0.1% evangelical)",
               style={"fontSize": "10px", "color": "#A0AEC0", "marginTop": "8px"}),
    ])

    return True, country, body


@app.callback(
    Output("scatter-plot", "figure"),
    Input("region-filter", "value"),
    Input("religion-filter", "value"),
    Input("frontier-toggle", "value"),
)
def update_scatter(region, religion, frontier_only):
    dff = _apply_filters(region, religion, frontier_only).copy()
    dff["BubbleSize"] = dff["Population"].clip(upper=5_000_000) / 100_000

    fig = px.scatter(
        dff,
        x="PercentEvangelical",
        y="Population",
        color="PrimaryReligion",
        size="BubbleSize",
        size_max=30,
        hover_name="PeopNameInCountry",
        hover_data={"Ctry": True, "PrimaryReligion": True,
                    "PercentEvangelical": ":.2f", "Population": ":,",
                    "Frontier": True, "BubbleSize": False},
        color_discrete_map=RELIGION_COLORS,
        labels={"PercentEvangelical": "% Evangelical", "Population": "Population",
                "PrimaryReligion": "Religion"},
        log_y=True,
        custom_data=["PeopNameInCountry", "Ctry", "PrimaryReligion",
                     "PercentEvangelical", "Population", "Frontier",
                     "BibleStatus", "PrimaryLanguageName", "HasJesusFilm",
                     "JPProfileURL", "BibleStatusLabel"],
    )
    fig.update_traces(marker=dict(opacity=0.75, line=dict(width=0.5, color="white")))
    fig.update_layout(
        margin={"r": 8, "t": 8, "l": 8, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(title="Religion", font=dict(size=10),
                    itemsizing="constant", orientation="v"),
        xaxis=dict(title="% Evangelical", gridcolor="#F0F0F0", zeroline=False),
        yaxis=dict(title="Population (log scale)", gridcolor="#F0F0F0", zeroline=False),
    )
    return fig


@app.callback(
    Output("region-bar", "figure"),
    Input("region-filter", "value"),
    Input("religion-filter", "value"),
    Input("frontier-toggle", "value"),
)
def update_bar(region, religion, frontier_only):
    # Use the full DF (not evangelical-threshold filtered) so the chart shows
    # the complete religious population of the countries on the map, not just
    # the unreached subset.  Only the region filter is applied so the chart
    # stays in sync with the map's visible countries.
    bar_df = DF.copy()
    if region != "ALL":
        bar_df = bar_df[bar_df["RegionName"] == region]

    # When country-level data is available, restrict further to countries that
    # actually appear in COUNTRIES_DF (i.e., confirmed JP-tracked countries).
    if not COUNTRIES_DF.empty:
        valid = set(COUNTRIES_DF["Ctry"])
        bar_df = bar_df[bar_df["Ctry"].isin(valid)]

    rel_totals = (
        bar_df.groupby("PrimaryReligion")["Population"]
        .sum()
        .reset_index()
        .sort_values("Population", ascending=False)
    )

    fig = px.bar(
        rel_totals,
        x="PrimaryReligion",
        y="Population",
        color="PrimaryReligion",
        color_discrete_map=RELIGION_COLORS,
        labels={"PrimaryReligion": "Religion", "Population": "Population"},
    )
    fig.update_traces(showlegend=False)
    fig.update_layout(
        margin={"r": 8, "t": 8, "l": 8, "b": 60},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="", tickangle=-30, tickfont=dict(size=11),
                   gridcolor="#F0F0F0"),
        yaxis=dict(title="Population", gridcolor="#F0F0F0"),
    )
    return fig


@app.callback(
    Output("detail-content", "children"),
    Input("scatter-plot", "clickData"),
)
def update_detail(click_data):
    if click_data is None:
        return html.P("Click any dot on the scatter plot to see details about that people group.",
                      style={"fontSize": "13px", "color": "#718096", "fontStyle": "italic"})

    cd = click_data["points"][0].get("customdata", [])
    if len(cd) < 10:
        return html.P("Could not load details.", style={"color": "#718096"})

    name, country, religion, pct_evang, population, is_frontier, \
        bible_status, language, jesus_film, profile_url = cd[:10]
    bible_label = cd[10] if len(cd) > 10 else "Unknown"

    def row(label, value):
        return html.Tr([
            html.Td(label, style={"fontSize": "12px", "color": "#718096",
                                   "paddingRight": "12px", "paddingBottom": "6px",
                                   "whiteSpace": "nowrap"}),
            html.Td(value, style={"fontSize": "13px", "fontWeight": "500",
                                   "paddingBottom": "6px"}),
        ])

    return html.Div([
        html.Div([
            html.H6(name, style={"fontWeight": "500", "marginBottom": "4px"}),
            html.P(country, style={"fontSize": "12px", "color": "#718096",
                                    "marginBottom": "8px"}),
            html.Div([
                dbc.Badge("Frontier Group", color="danger", className="me-1")
                if is_frontier else None,
                dbc.Badge("Unreached", color="warning",
                          text_color="dark", className="me-1"),
            ], style={"marginBottom": "12px"}),
        ]),
        html.Table(style={"width": "100%"}, children=[
            row("Religion",      religion),
            row("Population",    f"{int(population):,}" if population else "Unknown"),
            row("% Evangelical", f"{pct_evang:.2f}%"),
            row("Language",      language or "Unknown"),
            row("Bible status",  bible_label),
            row("Jesus Film",    "Yes" if jesus_film else "No"),
        ]),
        html.Hr(style={"margin": "12px 0"}),
        html.A("View Joshua Project profile →", href=profile_url, target="_blank",
               style={"fontSize": "12px", "color": "#3182CE"}),
    ])


@app.callback(
    Output("download-csv", "data"),
    Input("export-btn", "n_clicks"),
    State("region-filter", "value"),
    State("religion-filter", "value"),
    State("frontier-toggle", "value"),
    prevent_initial_call=True,
)
def export_csv(_, region, religion, frontier_only):
    dff = _apply_filters(region, religion, frontier_only)
    export_cols = ["PeopNameInCountry", "Ctry", "RegionName", "PrimaryReligion",
                   "PrimaryLanguageName", "Population", "PercentEvangelical",
                   "BibleStatusLabel", "HasJesusFilm", "Frontier", "LeastReached",
                   "JPProfileURL"]
    available  = [c for c in export_cols if c in dff.columns]
    export_df  = dff[available].copy()
    col_labels = ["People Group", "Country", "Region", "Primary Religion",
                  "Language", "Population", "% Evangelical", "Bible Status",
                  "Has Jesus Film", "Frontier Group", "Least Reached",
                  "Joshua Project Profile URL"]
    export_df.columns = col_labels[:len(available)]
    return dcc.send_data_frame(export_df.to_csv,
                               filename="unreached_people_groups.csv",
                               index=False)


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
