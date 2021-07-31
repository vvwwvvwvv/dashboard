import dash
import dash_table
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
df['KOI'] = df['KOI'].astype(int, errors='ignore')

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

""" RELATIVE DISTANCE (Distance to SUN/SUM radii) """
df.loc[:, "relative_dist"] = df["A"]/df["RSTAR"]

""" FILTERS """
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

#TABS CONTENT
tab1_content = [dbc.Row([
        dbc.Col(html.Div(id="dist-temp-chart"), md=6),
        dbc.Col(html.Div(id="celestial-chart"), md=6)
        ], style={"margin-top": 20}),
    dbc.Row([
        dbc.Col(html.Div(id="relative-dist-chart"), md=6),
        dbc.Col(html.Div(id="mstar-tstar-chart"))
    ])]
tab2_content = [dbc.Row(html.Div(id="data-table"), style={"margin-top": 20})]

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
    dbc.Tabs([
        dbc.Tab(tab1_content, label="Charts"),
        dbc.Tab(tab2_content, label="Data"),
        dbc.Tab(html.Div("About app"), label="About")
    ])
    ],
    style={"margin-left": "80px",
           "margin-right": "80px"})

""" CALLBACKS """


@app.callback(
    [Output(component_id="dist-temp-chart", component_property="children"),
     Output(component_id="celestial-chart", component_property="children"),
     Output(component_id="relative-dist-chart", component_property="children"),
     Output(component_id="mstar-tstar-chart", component_property="children"),
     Output(component_id="data-table", component_property="children")],
    [Input(component_id="submit_val", component_property="n_clicks")],
    [State(component_id="range-slider", component_property="value"),
     State(component_id="star-selector", component_property="value")]
)
def update_dist_temp_chart(n, radius_range, star_size):
    chart_data = df[(df["RPLANET"] > radius_range[0]) &
                    (df["RPLANET"] < radius_range[1]) &
                    (df["Star_Size"].isin(star_size))]

    if len(chart_data) == 0:
        return html.Div("Please select more data"), html.Div(), html.Div(), html.Div()

    fig1 = px.scatter(chart_data, x="TPLANET", y="A", color="Star_Size")

    html1 = [html.Div("Planet Temperature - Distance from the Star"),
             dcc.Graph(figure=fig1)]

    fig2 = px.scatter(chart_data, x="RA", y="DEC", size="RPLANET",
                      color="status")
    html2 = [html.Div("Position on the Celestial Sphere"),
             dcc.Graph(figure=fig2)]
    fig3 = px.histogram(chart_data, x="relative_dist",
                        color="status", barmode="overlay", marginal="violin")
    fig3.add_vline(x=1, y0=0, y1=160, annotation_text="Earth", line_dash="dot")
    html3 = [html.Div("Relative distance (AU/Sol) radii"),
             dcc.Graph(figure=fig3)]
    fig4 = px.scatter(chart_data, x="MSTAR", y="TSTAR", size="RPLANET",
                      color="status")
    html4 = [html.Div("Star Mass - Star Temperature"),
             dcc.Graph(figure=fig4)]

    #RAW DATA TABLE
    raw_data = chart_data.drop(["relative_dist",
                                "Star_Size",
                                'ROW',
                                'temp',
                                'gravity'], axis=1)
    tbl = dash_table.DataTable(data=raw_data.to_dict("records"),
                               columns=[{"name": i, "id": i}
                                        for i in raw_data.columns],
                               style_data={"width": '100px',
                                           "maxwidth": '100px',
                                           "minwidth":'100px'},
                               style_header={'text-align': 'center'},
                               page_size=40)
    html5 = [html.P("Raw Data"), tbl]
    return html1, html2, html3, html4, html5


if __name__ == "__main__":
    app.run_server(debug=True)

