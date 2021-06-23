import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import requests
import pandas as pd
import numpy as np
import plotly.express as px

""" READ DATA """

response = requests.get("http://asterank.com/api/kepler?query={}&limit=2000")
df = pd.json_normalize(response.json())
df = df[df["PER"] > 0]

#создаем категорию для звезд
bins = [0, 0.8, 1.2, 100]
names = ["small", "similar", "bigger"]
df["Star_Size"] = pd.cut(df["RSTAR"], bins, labels=names)

""" TEMEPRATURE BINS """

tp_bins = [0, 200, 400, 500, 5000]
tp_labels = ["low", "optimal", "high", "extreme"]
df["temp"] = pd.cut(df["TPLANET"], tp_bins, labels=tp_labels)

""" SIZE BINS """

rp_bins = [0, 0.5, 2, 4, 100]
rp_labels = ["low", "optimal", "high", "extreme"]
df["gravity"] = pd.cut(df["RPLANET"], rp_bins, labels=rp_labels)

""" ESTIMATE OBJECT STATUS """
df["status"] = np.where((df["temp"] == "optimal") &
                        (df["gravity"] == "optimal"),
                        "promising", None)
df.loc[:, "status"] = np.where((df["temp"] == "optimal") &
                                (df["gravity"].isin(["low", "high"])),
                                "challenging", df["status"])
df.loc[:, "status"] = np.where((df["gravity"] == "optimal") &
                                (df["temp"].isin(["low", "high"])),
                                "challenging", df["status"])
df["status"] = df.status.fillna("extreme")

#print(df.groupby("status")["ROW"].count())

options = []
for k in names:
    options.append({"label": k, "value": k})

star_size_selector = dcc.Dropdown(
    id="star-selector",
    options=options,
    value=["small", "similar", "bigger"],
    multi=True
)

rplanet_selector = dcc.RangeSlider(
    id="range-slider",
    min=min(df["RPLANET"]),
    max=max(df["RPLANET"]),
    marks={5: "5", 10: "10", 20: "20"},
    step=1,
    value=[5, 50]
)

app = dash.Dash(__name__,
                external_stylesheets=[dbc.themes.LUX])

""" LAYOUT """

app.layout = html.Div([
    #header
    dbc.Row(html.H1("Kepler Data Explorer"),
            style={"margin-bottom": 40}),
    #filters
    dbc.Row([
        dbc.Col([
            html.Div("Select Planet main semi-axis range"),
            html.Div(rplanet_selector)
        ],
            width={"size": 4}),
        dbc.Col([
            html.Div("Star size"),
            html.Div(star_size_selector)
        ],
            width={"size": 3, "offset": 1}),
        dbc.Col(dbc.Button("Apply", id="submit_val", n_clicks=0,  # добавляем кнопку apply
                           className="mr-2"))
    ],
            style={"margin-bottom": 40}),
    #charts
    dbc.Row([
        dbc.Col([html.Div(id="dist-temp-chart")
            #html.Div("Planet Temperature - Distance from the Star"),
            #dcc.Graph(id="dist-temp-chart")
        ],
            width={"size": 6}),
        dbc.Col([html.Div(id="celestial-chart")
            #html.Div("Position on the Celestial Sphere"),
            #dcc.Graph(id="celestial-chart")
        ])
    ],
            style={"margin-bottom": 40}),
    ],
    style={"margin-left": "80px",
           "margin-right": "80px"})

""" CALLBACKS """

@app.callback(
    Output(component_id="dist-temp-chart", component_property="children"),
    Output(component_id="celestial-chart", component_property="children"),
    [Input(component_id="submit_val", component_property="n_clicks")],
    [State(component_id="range-slider", component_property="value"),
     State(component_id="star-selector", component_property="value")]
)
def update_dist_temp_chart(n, radius_range, star_size):
    #print(n)
    chart_data = df[(df["RPLANET"] > radius_range[0]) &
                    (df["RPLANET"] < radius_range[1]) &
                    (df["Star_Size"].isin(star_size))]

    if len(chart_data) == 0:
        return html.Div("Please select more data"), html.Div()

    fig1 = px.scatter(chart_data, x="TPLANET", y="A", color="Star_Size")

    html1 = [html.Div("Planet Temperature - Distance from the Star"),
             dcc.Graph(figure=fig1)]

    fig2 = px.scatter(chart_data, x="RA", y="DEC", size="RPLANET",
                      color="status")
    html2 = [html.Div("Position on the Celestial Sphere"),
             dcc.Graph(figure=fig2)]

    return html1, html2


if __name__ == "__main__":
    app.run_server(debug=True)

