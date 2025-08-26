#! /usr/bin/python

import pandas as pd
import streamlit as st
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_bokeh import streamlit_bokeh
from bokeh.plotting import figure
from bokeh.models import (
    GeoJSONDataSource, LinearColorMapper, ColorBar,
    HoverTool, ColumnDataSource, DataTable, TableColumn,
    LabelSet
)
from bokeh.palettes import YlOrRd9, Blues
from bokeh.layouts import row
import xyzservices.providers as xyz

# Load json data file
cols = ['EVENT_UNIQUE_ID', 'REPORT_YEAR', 'REPORT_MONTH', 'REPORT_DOW', 'REPORT_HOUR',
        'OCC_DOW', 'OCC_HOUR', 'DIVISION', 'LOCATION_TYPE', 'PREMISES_TYPE', 'HOOD_158', 'NEIGHBOURHOOD_158',
        'LONG_WGS84', 'LAT_WGS84', 'x', 'y']
autotheft_df = pd.read_csv('Auto_Theft_Toronto.csv', usecols=cols)
autotheft_df_filtered = autotheft_df[autotheft_df['REPORT_YEAR'] < 2025]

# Groupby year and count number of entries per year
theft_by_year = autotheft_df_filtered.groupby('REPORT_YEAR').size().reset_index(name='THEFT_COUNT')
theft_by_year.set_index('REPORT_YEAR', inplace=True)

#Create year list as list string
years_list = list(map(str, theft_by_year.index.tolist()))
#years_list = autotheft_df_filtered['REPORT_YEAR'].unique().tolist()

# Function to filter and merge by year
def get_geojson_for_year(selected_year):
    filtered_df = df[df['REPORT_YEAR'] == selected_year]
    merged = gdf.merge(filtered_df, on='CATEGORY')
    return merged.to_json()

# Inject custom HTML and JavaScript to detect browser
st.markdown("""
    <script>
    const ua = navigator.userAgent;
    const isOldSafari = /Safari/.test(ua) && !/Chrome/.test(ua) && (
        ua.includes("Version/16.3") || ua.includes("Version/15") || ua.includes("Version/14")
    );
    const isIOS = /iPad|iPhone|iPod/.test(ua);

    if (isOldSafari || isIOS) {
        const warningDiv = document.createElement("div");
        warningDiv.innerHTML = `
            <div style="background-color:#fff3cd; color:#856404; padding:1em; border-radius:5px; border:1px solid #ffeeba; margin-bottom:1em;">
                 <strong>Browser Compatibility Notice:</strong><br>
                This app may not work properly on older versions of Safari or iPad browsers due to limited support for modern JavaScript features.<br>
                Please use Chrome, Firefox, or Safari 16.4+ for the best experience.
            </div>
        `;
        document.body.prepend(warningDiv);
    }
    </script>
""", unsafe_allow_html=True)

# Streamlit UI
st.set_page_config(layout="wide")
st.title('Toronto Auto Theft Analysis')

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["Yearly Trend", "Hourly Insights", "Density", "Location Type"])

with tab1:
    st.subheader("Yearly Trend of Total Thefts 2014-2024")

    colors = [Blues[256][x*20] for x in range(1, 12)]
    plot_year = figure(title='Total Auto Thefts per year',
                    tooltips="Thefts: @top", 
                    x_range=years_list, y_range=(0,14000))
    plot_year.vbar(x=years_list, top=theft_by_year['THEFT_COUNT'], width=0.5, color=colors[::-1])
    plot_year.xaxis.axis_label = 'Year'
    plot_year.yaxis.axis_label = 'Number of thefts reported'

    data = {'x': years_list,
            'y': theft_by_year['THEFT_COUNT'],
            'labels': theft_by_year['THEFT_COUNT']}
    source = ColumnDataSource(data=data)

    labels = LabelSet(x='x', y='y', text='labels', level='glyph',
                    x_offset=-12, y_offset=5, angle=0,
                    text_font_style = 'bold',
                    text_font_size = '10px', source=source)

    plot_year.add_layout(labels)

    # Plot yearly percentage change in a line chart
    # Calculate the percentage increase or decrease from previous year
    theft_by_year['YoY_CHANGE_PERCENT'] = (((theft_by_year['THEFT_COUNT'] / theft_by_year['THEFT_COUNT'].shift(1)) - 1) * 100).round(2)
    year_change_percent = theft_by_year['YoY_CHANGE_PERCENT']

    #Build the plots
    plot_yoy_percent = figure(title="YoY % Change in Auto Thefts",
                            tooltips="Thefts: @y", 
                            x_range=years_list, y_range=(0,14000))
    plot_yoy_percent.line(x=years_list, y=theft_by_year['THEFT_COUNT'])
    plot_yoy_percent.xaxis.axis_label = 'Year'
    plot_yoy_percent.yaxis.axis_label = 'Number of thefts reported'
    percent_change = [str(x)+"%" for x in year_change_percent]
    percent_change[0] = ""
    data = {'x': years_list, 'y': theft_by_year['THEFT_COUNT'], 'labels': percent_change}
    source = ColumnDataSource(data=data)

    labels = LabelSet(x='x', y='y', text='labels', level='glyph',
                    x_offset=-12, y_offset=5, angle=0,
                    text_font_style = 'bold',
                    text_font_size = '10px', source=source)

    plot_yoy_percent.add_layout(labels)
    plot_yoy_percent.scatter(x=years_list, y=theft_by_year['THEFT_COUNT'], size=5, color="black", fill_alpha=0.6)

    col1, col2 = st.columns(2)
    with col1:
        streamlit_bokeh(plot_year, use_container_width=True, theme='streamlit', key="yearly_chart")
    with col2:
        streamlit_bokeh(plot_yoy_percent, use_container_width=True, theme='streamlit', key="percent_chart")

with tab2:
    st.subheader("Hour of Day Insights")

    hourly_df_year = autotheft_df_filtered.groupby(['REPORT_YEAR', 'OCC_HOUR']).size().reset_index(name='THEFT_COUNT')
    hourly_df_year['REPORT_YEAR'] = hourly_df_year['REPORT_YEAR'].astype(str)

    legend_dict=dict(
        x=0,
        y=1.05,
        xanchor='left',
        yanchor='top',
        orientation='h'
    )
    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(
            hourly_df_year,
            x='OCC_HOUR',
            y='THEFT_COUNT',
            color='REPORT_YEAR',
            markers='o',
            title='Total Thefts by Hour of the day',
            custom_data=['REPORT_YEAR']
            )
        fig.update_traces(
            hovertemplate="Hour: %{x}<br>Thefts: %{y}<br>Year: %{customdata[0]}<extra></extra>"
        )
        fig.update_layout(
            xaxis_title='Hour of the day',
            yaxis_title='Number of thefts',
            legend_title='Year',
            width=800, height=600,
            xaxis=dict(range=[0, 23], tickmode='linear', tick0=0, dtick=1, tickangle=0),
            legend=legend_dict
            )
        st.plotly_chart(fig, key='hourly_chart')
    with col2:
        # Visualize for a year and check if it displays similar trend
        # Visualize hour of the day theft data by year. To be done per year as aggregate data might not be accurate
        hourly_rep_df = autotheft_df_filtered.groupby('REPORT_HOUR').size().reset_index(name='THEFT_COUNT')
        hourly_occ_df = autotheft_df_filtered.groupby('OCC_HOUR').size().reset_index(name='THEFT_COUNT')
        # Create a figure
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hourly_rep_df['REPORT_HOUR'], 
            y=hourly_rep_df['THEFT_COUNT'], 
            mode='lines+markers', 
            name='Reporting Hour'))
        fig.add_trace(go.Scatter(
            x=hourly_occ_df['OCC_HOUR'], 
            y=hourly_occ_df['THEFT_COUNT'], 
            mode='lines+markers', 
            name='Occurrence Hour'))
        fig.update_traces(
            hovertemplate="Hour: %{x}<br>Thefts: %{y}<br><extra></extra>"
        )
        fig.update_layout(
            title='Thefts: Reporting Hour vs Occurrence Hour (2014-2024)', 
            xaxis_title='Hour of the day', 
            yaxis_title='Number of thefts',
            xaxis_range=[0,24],
            width=800, height=600,
            xaxis=dict(range=[0, 23], tickmode='linear', tick0=0, dtick=1, tickangle=0),
            legend=legend_dict
        )
        # Display
        st.plotly_chart(fig, key='rep_occ_chart')

with tab3:
    st.subheader("Theft Density")
    category = st.selectbox("Select Category", ["Police Division", "Neighbourhood"])

    # Load data based on category selection
    if category == "Neighbourhood":
        # Group based on neighbourhoods
        nh_yearly_df = autotheft_df_filtered.groupby(['REPORT_YEAR', 'NEIGHBOURHOOD_158']).size().reset_index(name='THEFTS')
        df = nh_yearly_df
        df = df.rename(columns={'NEIGHBOURHOOD_158' : 'CATEGORY'})
        # Load GeoJSON file for Neighborhoods
        gdf = gpd.read_file('Neighbourhoods.geojson')
        gdf = gdf.rename(columns={'AREA_DESC' : 'CATEGORY'})
    else:
        # Group based on division
        division_yearly_df = autotheft_df_filtered.groupby(['REPORT_YEAR', 'DIVISION']).size().reset_index(name='THEFTS')
        df = division_yearly_df
        df = df.rename(columns={'DIVISION' : 'CATEGORY'})
        # Load GeoJSON file for Police boundaries
        gdf = gpd.read_file('Police_Boundaries.geojson')
        gdf = gdf.rename(columns={'DIV' : 'CATEGORY'})

    gdf = gdf.to_crs(epsg=3857)

    # Year Selector
    selected_year = st.slider('Select Year', min_value=int(df['REPORT_YEAR'].min()),
                            max_value=int(df['REPORT_YEAR'].max()),
                            value=int(df['REPORT_YEAR'].min()), step=1)

    # Prepare data
    geo_source = GeoJSONDataSource(geojson=get_geojson_for_year(selected_year))
    color_mapper = LinearColorMapper(palette=YlOrRd9[::-1],
                                    low=df['THEFTS'].min(),
                                    high=df['THEFTS'].max())

    # Create a Bokeh figure
    p = figure(title=f"Theft Density by {category} for {selected_year}",
            x_axis_type="mercator", y_axis_type="mercator",
            width=800, height=600, tools="pan,wheel_zoom,reset")

    p.add_tile(xyz.CartoDB.Positron)
    p.patches('xs', 'ys', source=geo_source, 
            fill_color={'field': 'THEFTS', 'transform': color_mapper},
            line_color='black', line_width=0.5, fill_alpha=0.7)

    hover = HoverTool(tooltips=[(category, "@CATEGORY"), ("Thefts", "@THEFTS")])
    p.add_tools(hover)

    # Add color bar
    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=12, location=(0,0))
    p.add_layout(color_bar, 'right')

    # Add a table 
    div_year = df[df['REPORT_YEAR'] == selected_year].sort_values('THEFTS', ascending=False).reset_index(drop=True)
    div_year.index += 1
    div_year['RANK'] = div_year.index
    data = dict(ColumnDataSource(div_year).data)
    table_source = ColumnDataSource(data=data)
    columns = [
        TableColumn(field="RANK", title="Rank", width=50),
        TableColumn(field="CATEGORY", title=f"{category}", width=200),
        TableColumn(field="THEFTS", title="Theft Count", width=50),
    ]
    data_table = DataTable(source=table_source, columns=columns,
                        width=300, height=600, index_position=None)

    # Display map and table in a single row
    layout = row(p, data_table, sizing_mode='stretch_both')
    # Show plot
    streamlit_bokeh(layout, use_container_width=True, theme='streamlit', key="density_map")

with tab4:
    st.subheader("Theft Distribution by Location Type")

    #Analyze Auto Theft data by location type for all years 2014-2024
    location_df = autotheft_df_filtered.groupby(['LOCATION_TYPE']).size().sort_values(ascending=False).reset_index(name='THEFTS')
    top_n = 7
    df_top = location_df.head(top_n)

    #colors = cividis
    fig = px.pie(df_top,
                 names=df_top['LOCATION_TYPE'],
                 values=df_top['THEFTS'],
                 title='Thefts by Location Type',
                 )
    st.plotly_chart(fig, key='location_chart')


