"""
app.py
------
Plotly Dash interactive tool for missionaries exploring unreached people groups.

Run with:
    python app.py

Then open http://127.0.0.1:8050 in your browser.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc

from src.clean import load_and_clean

# ── App init ──────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Unreached People Groups Explorer",
)

# ── Load & cache data at startup ──────────────────────────────────────────────
# This runs once when the server starts. The clean.py layer handles
# reading from local cache so we don't hit the API on every reload.
print("Loading data...")
DF = load_and_clean()
print("Data loaded.\n")

# ── Dropdown options ──────────────────────────────────────────────────────────
REGIONS = sorted(DF["RegionName"].dropna().unique())
RELIGIONS = sorted(DF["PrimaryReligion"].dropna().unique())

REGION_OPTIONS = [{"label": "All regions", "value": "ALL"}] + [
    {"label": r, "value": r} for r in REGIONS
]
RELIGION_OPTIONS = [{"label": "All religions", "value": "ALL"}] + [
    {"label": r, "value": r} for r in RELIGIONS
]

BIBLE_STATUS_LABELS = {
    0: "No scripture",
    1: "No scripture",
    2: "Portions only",
    3: "New Testament",
    4: "Bible portions",
    5: "Complete Bible",
}

# ── Color map for religions ───────────────────────────────────────────────────
RELIGION_COLORS = {
    "Islam": "#E05A2B",
    "Hinduism": "#E8A020",
    "Buddhism": "#5B8DD9",
    "Ethnic Religions": "#7CB87A",
    "Christianity": "#5271C4",
    "Non-Religious": "#9E9E9E",
    "Other/Small": "#B06BB0",
    "Unknown": "#CCCCCC",
}


# ── Layout ────────────────────────────────────────────────────────────────────
app.layout = dbc.Container(
    fluid=True,
    style={"backgroundColor": "#F8F9FA", "minHeight": "100vh", "padding": "0"},
    children=[

        # Header
        dbc.Row(
            dbc.Col(
                html.Div(
                    style={
                        "backgroundColor": "#1A2B45",
                        "padding": "18px 32px",
                        "marginBottom": "24px",
                    },
                    children=[
                        html.H4(
                            "Unreached People Groups Explorer",
                            style={"color": "#FFFFFF", "margin": 0, "fontWeight": "500"},
                        ),
                        html.P(
                            "A research tool for missionaries exploring field placement — powered by Joshua Project data",
                            style={"color": "#A0AEC0", "margin": "4px 0 0", "fontSize": "13px"},
                        ),
                    ],
                )
            )
        ),

        # Controls row
        dbc.Row(
            style={"padding": "0 24px", "marginBottom": "20px"},
            children=[
                # Region filter
                dbc.Col(width=3, children=[
                    html.Label("World region", style={"fontSize": "12px", "fontWeight": "500", "color": "#4A5568", "marginBottom": "4px"}),
                    dcc.Dropdown(
                        id="region-filter",
                        options=REGION_OPTIONS,
                        value="ALL",
                        clearable=False,
                        style={"fontSize": "13px"},
                    ),
                ]),

                # Religion filter
                dbc.Col(width=3, children=[
                    html.Label("Primary religion", style={"fontSize": "12px", "fontWeight": "500", "color": "#4A5568", "marginBottom": "4px"}),
                    dcc.Dropdown(
                        id="religion-filter",
                        options=RELIGION_OPTIONS,
                        value="ALL",
                        clearable=False,
                        style={"fontSize": "13px"},
                    ),
                ]),

                # Evangelical threshold slider
                dbc.Col(width=4, children=[
                    html.Label(
                        id="slider-label",
                        style={"fontSize": "12px", "fontWeight": "500", "color": "#4A5568", "marginBottom": "4px"},
                    ),
                    dcc.Slider(
                        id="evangelical-threshold",
                        min=0,
                        max=10,
                        step=0.1,
                        value=2.0,
                        marks={
                            0: {"label": "0%", "style": {"fontSize": "11px"}},
                            0.1: {"label": "0.1%", "style": {"fontSize": "11px"}},
                            2: {"label": "2%", "style": {"fontSize": "11px"}},
                            5: {"label": "5%", "style": {"fontSize": "11px"}},
                            10: {"label": "10%", "style": {"fontSize": "11px"}},
                        },
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                ]),

                # Frontier toggle
                dbc.Col(width=2, children=[
                    html.Label("Frontier groups only", style={"fontSize": "12px", "fontWeight": "500", "color": "#4A5568", "marginBottom": "8px"}),
                    dbc.Switch(
                        id="frontier-toggle",
                        value=False,
                        label="",
                        style={"marginTop": "4px"},
                    ),
                ]),
            ],
        ),

        # Summary stats bar
        dbc.Row(
            id="stats-bar",
            style={"padding": "0 24px", "marginBottom": "20px"},
        ),

        # Main content: map + scatter
        dbc.Row(
            style={"padding": "0 24px", "marginBottom": "20px"},
            children=[
                # Choropleth map
                dbc.Col(width=7, children=[
                    dbc.Card(
                        style={"border": "1px solid #E2E8F0", "borderRadius": "8px"},
                        children=[
                            dbc.CardHeader(
                                "Evangelical presence by country",
                                style={"fontSize": "13px", "fontWeight": "500", "backgroundColor": "#FFFFFF", "borderBottom": "1px solid #E2E8F0"},
                            ),
                            dbc.CardBody(
                                dcc.Graph(id="choropleth-map", style={"height": "380px"}),
                                style={"padding": "8px"},
                            ),
                        ],
                    )
                ]),

                # Scatter plot
                dbc.Col(width=5, children=[
                    dbc.Card(
                        style={"border": "1px solid #E2E8F0", "borderRadius": "8px"},
                        children=[
                            dbc.CardHeader(
                                "Population vs. % Evangelical (click a dot to inspect)",
                                style={"fontSize": "13px", "fontWeight": "500", "backgroundColor": "#FFFFFF", "borderBottom": "1px solid #E2E8F0"},
                            ),
                            dbc.CardBody(
                                dcc.Graph(id="scatter-plot", style={"height": "380px"}),
                                style={"padding": "8px"},
                            ),
                        ],
                    )
                ]),
            ],
        ),

        # Bottom row: bar chart + detail panel
        dbc.Row(
            style={"padding": "0 24px", "marginBottom": "32px"},
            children=[
                # Religion composition bar chart
                dbc.Col(width=7, children=[
                    dbc.Card(
                        style={"border": "1px solid #E2E8F0", "borderRadius": "8px"},
                        children=[
                            dbc.CardHeader(
                                "Religion composition by world region",
                                style={"fontSize": "13px", "fontWeight": "500", "backgroundColor": "#FFFFFF", "borderBottom": "1px solid #E2E8F0"},
                            ),
                            dbc.CardBody(
                                dcc.Graph(id="region-bar", style={"height": "300px"}),
                                style={"padding": "8px"},
                            ),
                        ],
                    )
                ]),

                # Detail panel
                dbc.Col(width=5, children=[
                    dbc.Card(
                        id="detail-panel",
                        style={"border": "1px solid #E2E8F0", "borderRadius": "8px", "height": "100%"},
                        children=[
                            dbc.CardHeader(
                                "People group detail",
                                style={"fontSize": "13px", "fontWeight": "500", "backgroundColor": "#FFFFFF", "borderBottom": "1px solid #E2E8F0"},
                            ),
                            dbc.CardBody(
                                id="detail-content",
                                style={"padding": "16px"},
                                children=[
                                    html.P(
                                        "Click any dot on the scatter plot to see details about that people group.",
                                        style={"fontSize": "13px", "color": "#718096", "fontStyle": "italic"},
                                    )
                                ],
                            ),
                        ],
                    )
                ]),
            ],
        ),

        # Export row
        dbc.Row(
            style={"padding": "0 24px", "marginBottom": "32px"},
            children=[
                dbc.Col(
                    children=[
                        dbc.Button(
                            "Export current results as CSV",
                            id="export-btn",
                            color="secondary",
                            outline=True,
                            size="sm",
                            style={"fontSize": "13px"},
                        ),
                        dcc.Download(id="download-csv"),
                        html.Span(
                            " Exports all people groups matching current filters",
                            style={"fontSize": "12px", "color": "#718096", "marginLeft": "12px"},
                        ),
                    ]
                )
            ],
        ),

        # Hidden store for filtered data indices
        dcc.Store(id="filtered-indices"),

        # Footer
        dbc.Row(
            dbc.Col(
                html.P(
                    "Data sourced from Joshua Project API (joshuaproject.net). For research use only.",
                    style={"fontSize": "11px", "color": "#A0AEC0", "textAlign": "center", "padding": "12px"},
                )
            )
        ),
    ],
)


# ── Helper: apply filters ─────────────────────────────────────────────────────
def apply_filters(region, religion, threshold, frontier_only):
    """
    Filter the global DataFrame based on current control values.

    Parameters
    ----------
    region : str
        Selected region, or "ALL"
    religion : str
        Selected religion, or "ALL"
    threshold : float
        Max % Evangelical to include
    frontier_only : bool
        If True, only include Frontier groups

    Returns
    -------
    pd.DataFrame
        Filtered subset of DF
    """
    dff = DF.copy()

    if region != "ALL":
        dff = dff[dff["RegionName"] == region]

    if religion != "ALL":
        dff = dff[dff["PrimaryReligion"] == religion]

    dff = dff[dff["PercentEvangelical"] <= threshold]

    if frontier_only:
        dff = dff[dff["Frontier"] == True]

    return dff


# ── Callback: slider label ────────────────────────────────────────────────────
@app.callback(
    Output("slider-label", "children"),
    Input("evangelical-threshold", "value"),
)
def update_slider_label(threshold):
    return f"Show groups with ≤ {threshold:.1f}% Evangelical"


# ── Callback: stats bar ───────────────────────────────────────────────────────
@app.callback(
    Output("stats-bar", "children"),
    Input("region-filter", "value"),
    Input("religion-filter", "value"),
    Input("evangelical-threshold", "value"),
    Input("frontier-toggle", "value"),
)
def update_stats(region, religion, threshold, frontier_only):
    dff = apply_filters(region, religion, threshold, frontier_only)

    stats = [
        ("People groups", f"{len(dff):,}"),
        ("Total population", f"{dff['Population'].sum() / 1_000_000:.1f}M"),
        ("Frontier groups", f"{dff['Frontier'].sum():,}"),
        ("Avg % Evangelical", f"{dff['PercentEvangelical'].mean():.2f}%"),
        ("Countries", f"{dff['Ctry'].nunique():,}"),
    ]

    cards = []
    for label, value in stats:
        cards.append(
            dbc.Col(
                dbc.Card(
                    style={
                        "border": "1px solid #E2E8F0",
                        "borderRadius": "8px",
                        "textAlign": "center",
                        "padding": "10px",
                        "backgroundColor": "#FFFFFF",
                    },
                    children=[
                        html.P(value, style={"fontSize": "20px", "fontWeight": "500", "margin": "0", "color": "#1A2B45"}),
                        html.P(label, style={"fontSize": "11px", "color": "#718096", "margin": "0"}),
                    ],
                ),
                width=True,
            )
        )
    return cards


# ── Callback: choropleth map ──────────────────────────────────────────────────
@app.callback(
    Output("choropleth-map", "figure"),
    Input("region-filter", "value"),
    Input("religion-filter", "value"),
    Input("evangelical-threshold", "value"),
    Input("frontier-toggle", "value"),
)
def update_map(region, religion, threshold, frontier_only):
    dff = apply_filters(region, religion, threshold, frontier_only)

    # Aggregate to country level (mean % Evangelical, weighted by population)
    country_df = (
        dff.groupby("Ctry")
        .apply(
            lambda g: pd.Series({
                "AvgEvangelical": (g["PercentEvangelical"] * g["Population"]).sum() / g["Population"].sum()
                if g["Population"].sum() > 0 else 0,
                "TotalPop": g["Population"].sum(),
                "NumGroups": len(g),
                "FrontierCount": g["Frontier"].sum(),
            })
        )
        .reset_index()
    )

    fig = px.choropleth(
        country_df,
        locations="Ctry",
        locationmode="country names",
        color="AvgEvangelical",
        hover_name="Ctry",
        hover_data={
            "AvgEvangelical": ":.2f",
            "NumGroups": True,
            "FrontierCount": True,
            "Ctry": False,
        },
        color_continuous_scale=[
            [0.0, "#B03A2E"],
            [0.1, "#E07B39"],
            [0.3, "#F0C040"],
            [0.6, "#6AAF6A"],
            [1.0, "#2E7D52"],
        ],
        range_color=[0, min(threshold, 10)],
        labels={
            "AvgEvangelical": "% Evangelical",
            "NumGroups": "People groups",
            "FrontierCount": "Frontier groups",
        },
    )

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#D0D0D0",
            showland=True,
            landcolor="#F0F0F0",
            showocean=True,
            oceancolor="#E8F4FD",
            projection_type="natural earth",
        ),
        coloraxis_colorbar=dict(
            title="% Evangelical",
            thickness=12,
            len=0.6,
            tickfont=dict(size=10),
            titlefont=dict(size=11),
        ),
    )
    return fig


# ── Callback: scatter plot ────────────────────────────────────────────────────
@app.callback(
    Output("scatter-plot", "figure"),
    Input("region-filter", "value"),
    Input("religion-filter", "value"),
    Input("evangelical-threshold", "value"),
    Input("frontier-toggle", "value"),
)
def update_scatter(region, religion, threshold, frontier_only):
    dff = apply_filters(region, religion, threshold, frontier_only)

    # Cap bubble size for readability
    dff = dff.copy()
    dff["BubbleSize"] = dff["Population"].clip(upper=5_000_000) / 100_000

    fig = px.scatter(
        dff,
        x="PercentEvangelical",
        y="Population",
        color="PrimaryReligion",
        size="BubbleSize",
        size_max=30,
        hover_name="PeopNameInCountry",
        hover_data={
            "Ctry": True,
            "PrimaryReligion": True,
            "PercentEvangelical": ":.2f",
            "Population": ":,",
            "Frontier": True,
            "BubbleSize": False,
        },
        color_discrete_map=RELIGION_COLORS,
        labels={
            "PercentEvangelical": "% Evangelical",
            "Population": "Population",
            "PrimaryReligion": "Religion",
        },
        log_y=True,
        custom_data=["PeopNameInCountry", "Ctry", "PrimaryReligion",
                     "PercentEvangelical", "Population", "Frontier",
                     "BibleStatus", "PrimaryLanguageName", "HasJesusFilm",
                     "JPProfileURL", "BibleStatusLabel"],
    )

    fig.update_traces(
        marker=dict(opacity=0.75, line=dict(width=0.5, color="white")),
    )

    fig.update_layout(
        margin={"r": 8, "t": 8, "l": 8, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            title="Religion",
            font=dict(size=10),
            itemsizing="constant",
            orientation="v",
        ),
        xaxis=dict(
            title="% Evangelical",
            gridcolor="#F0F0F0",
            zeroline=False,
        ),
        yaxis=dict(
            title="Population (log scale)",
            gridcolor="#F0F0F0",
            zeroline=False,
        ),
    )
    return fig


# ── Callback: region bar chart ────────────────────────────────────────────────
@app.callback(
    Output("region-bar", "figure"),
    Input("region-filter", "value"),
    Input("religion-filter", "value"),
    Input("evangelical-threshold", "value"),
    Input("frontier-toggle", "value"),
)
def update_bar(region, religion, threshold, frontier_only):
    dff = apply_filters(region, religion, threshold, frontier_only)

    region_religion = (
        dff.groupby(["RegionName", "PrimaryReligion"])["Population"]
        .sum()
        .reset_index()
    )

    fig = px.bar(
        region_religion,
        x="RegionName",
        y="Population",
        color="PrimaryReligion",
        color_discrete_map=RELIGION_COLORS,
        labels={
            "RegionName": "Region",
            "Population": "Population",
            "PrimaryReligion": "Religion",
        },
        barmode="stack",
    )

    fig.update_layout(
        margin={"r": 8, "t": 8, "l": 8, "b": 80},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            title="Religion",
            font=dict(size=10),
            itemsizing="constant",
        ),
        xaxis=dict(
            title="",
            tickangle=-35,
            tickfont=dict(size=10),
            gridcolor="#F0F0F0",
        ),
        yaxis=dict(
            title="Population",
            gridcolor="#F0F0F0",
        ),
    )
    return fig


# ── Callback: detail panel ────────────────────────────────────────────────────
@app.callback(
    Output("detail-content", "children"),
    Input("scatter-plot", "clickData"),
)
def update_detail(click_data):
    if click_data is None:
        return html.P(
            "Click any dot on the scatter plot to see details about that people group.",
            style={"fontSize": "13px", "color": "#718096", "fontStyle": "italic"},
        )

    point = click_data["points"][0]
    cd = point.get("customdata", [])

    if len(cd) < 10:
        return html.P("Could not load details for this group.", style={"color": "#718096"})

    name        = cd[0]
    country     = cd[1]
    religion    = cd[2]
    pct_evang   = cd[3]
    population  = cd[4]
    is_frontier = cd[5]
    bible_status = cd[6]
    language    = cd[7]
    jesus_film  = cd[8]
    profile_url = cd[9]
    bible_label = cd[10] if len(cd) > 10 else "Unknown"

    frontier_badge = (
        dbc.Badge("Frontier Group", color="danger", className="me-1")
        if is_frontier else None
    )
    lr_badge = dbc.Badge("Unreached", color="warning", text_color="dark", className="me-1")

    def row(label, value):
        return html.Tr([
            html.Td(label, style={"fontSize": "12px", "color": "#718096", "paddingRight": "12px", "paddingBottom": "6px", "whiteSpace": "nowrap"}),
            html.Td(value, style={"fontSize": "13px", "fontWeight": "500", "paddingBottom": "6px"}),
        ])

    return html.Div([
        html.Div([
            html.H6(name, style={"fontWeight": "500", "marginBottom": "4px"}),
            html.P(country, style={"fontSize": "12px", "color": "#718096", "marginBottom": "8px"}),
            html.Div([frontier_badge, lr_badge], style={"marginBottom": "12px"}),
        ]),
        html.Table(
            style={"width": "100%"},
            children=[
                row("Religion", religion),
                row("Population", f"{int(population):,}" if population else "Unknown"),
                row("% Evangelical", f"{pct_evang:.2f}%"),
                row("Language", language or "Unknown"),
                row("Bible status", bible_label),
                row("Jesus Film", "Yes" if jesus_film else "No"),
            ],
        ),
        html.Hr(style={"margin": "12px 0"}),
        html.A(
            "View Joshua Project profile →",
            href=profile_url,
            target="_blank",
            style={"fontSize": "12px", "color": "#3182CE"},
        ),
    ])


# ── Callback: CSV export ──────────────────────────────────────────────────────
@app.callback(
    Output("download-csv", "data"),
    Input("export-btn", "n_clicks"),
    State("region-filter", "value"),
    State("religion-filter", "value"),
    State("evangelical-threshold", "value"),
    State("frontier-toggle", "value"),
    prevent_initial_call=True,
)
def export_csv(n_clicks, region, religion, threshold, frontier_only):
    dff = apply_filters(region, religion, threshold, frontier_only)

    export_cols = [
        "PeopNameInCountry", "Ctry", "RegionName", "PrimaryReligion",
        "PrimaryLanguageName", "Population", "PercentEvangelical",
        "BibleStatusLabel", "HasJesusFilm", "Frontier", "LeastReached",
        "JPProfileURL",
    ]
    available = [c for c in export_cols if c in dff.columns]
    export_df = dff[available].copy()

    # Rename for readability in the CSV
    export_df.columns = [
        "People Group", "Country", "Region", "Primary Religion",
        "Language", "Population", "% Evangelical",
        "Bible Status", "Has Jesus Film", "Frontier Group", "Least Reached",
        "Joshua Project Profile URL",
    ][:len(available)]

    return dcc.send_data_frame(
        export_df.to_csv,
        filename="unreached_people_groups.csv",
        index=False,
    )


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
