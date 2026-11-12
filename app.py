# Sellers dashboard made with Streamlit

# Import the libraries we need
import streamlit as st   # to build the web interface
import pandas as pd      # to read and handle the data
from pathlib import Path # to find the Excel file in the same folder as this script

# Basic page settings (title that shows in the browser tab and wide layout)
st.set_page_config(page_title="Sellers Dashboard", layout="wide")

# Path to the Excel file (it has to be in the same folder as app.py)
FILE_PATH = Path(__file__).parent / "sellers.xlsx"


# Function that reads the Excel file
# @st.cache_data makes Streamlit remember the data so it does not reload it every time
@st.cache_data
def load_data(path):
    data = pd.read_excel(path)
    # Join name and last name in one column, so we can use it to pick a seller
    data["FULL NAME"] = data["NAME"] + " " + data["LASTNAME"]
    return data


# Load the data into a dataframe
df = load_data(FILE_PATH)

# Title of the app
st.title("Sellers Dashboard")

# ---------------------------------------------------------------
# SIDEBAR: filter by region
# ---------------------------------------------------------------
st.sidebar.header("Filters")

# Get the list of regions without repeats
regions = sorted(df["REGION"].unique())

# Multiselect so the user can choose one or more regions (all selected by default)
selected_regions = st.sidebar.multiselect("Region", regions, default=regions)

# Keep only the rows that belong to the selected regions
filtered_df = df[df["REGION"].isin(selected_regions)]

# If nothing is selected there is no data to show, so we stop the app here
if filtered_df.empty:
    st.warning("Please select at least one region.")
    st.stop()

# ---------------------------------------------------------------
# SECTION 1: table filtered by region
# ---------------------------------------------------------------
# Container to keep the table section together
with st.container():
    st.header("Sellers table")

    # Show the table (without the extra FULL NAME column and without the index)
    st.dataframe(
        filtered_df.drop(columns=["FULL NAME"]),
        hide_index=True,
    )

    # Show how many sellers are in the table
    st.write("Number of sellers:", len(filtered_df))

    # Button to download the filtered table as a CSV file
    st.download_button(
        label="Download table as CSV",
        data=filtered_df.to_csv(index=False),
        file_name="sellers_filtered.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------------
# SECTION 2: graphs of Units Sold, Total Sales and Average Sales
# ---------------------------------------------------------------
with st.container():
    st.header("Graphs")

    # Use FULL NAME as the index so it is the label of each bar
    chart_df = filtered_df.set_index("FULL NAME")

    # Three columns so the graphs are side by side
    col1, col2, col3 = st.columns(3)

    # Graph 1: units sold by seller
    with col1:
        st.subheader("Units Sold")
        st.bar_chart(chart_df["SOLD UNITS"])

    # Graph 2: total sales by seller
    with col2:
        st.subheader("Total Sales")
        st.bar_chart(chart_df["TOTAL SALES"])

    # Graph 3: average sales by seller
    with col3:
        st.subheader("Average Sales")
        st.bar_chart(chart_df["SALES AVERAGE"])

    # Note about the Average Sales column (I checked it in the data)
    st.caption(
        "Note: in the file, SALES AVERAGE is the seller's Total Sales "
        "divided by the Total Sales of the whole region."
    )

# ---------------------------------------------------------------
# SECTION 3: data for one specific seller
# ---------------------------------------------------------------
with st.container():
    st.header("Seller details")

    # Select box with the names of the sellers (we use the name because the ID 9091 is repeated)
    seller_name = st.selectbox("Select a seller", sorted(filtered_df["FULL NAME"]))

    # Get the row of the selected seller
    seller = filtered_df[filtered_df["FULL NAME"] == seller_name].iloc[0]

    # Show the main data of the seller in columns
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Region", seller["REGION"])
    c2.metric("Income", seller["INCOME"])
    c3.metric("Units Sold", seller["SOLD UNITS"])
    c4.metric("Total Sales", seller["TOTAL SALES"])

    st.write("ID:", seller["ID"])
    st.write("Average Sales:", round(seller["SALES AVERAGE"], 4))

    # Button to compare the seller against the average of his/her region
    if st.button("Compare with region average"):
        # Rows of the full data that are in the same region as the seller
        region_df = df[df["REGION"] == seller["REGION"]]

        # Small table with the seller values and the region averages
        comparison = pd.DataFrame(
            {
                "Seller": [seller["SOLD UNITS"], seller["TOTAL SALES"]],
                "Region average": [
                    region_df["SOLD UNITS"].mean(),
                    region_df["TOTAL SALES"].mean(),
                ],
            },
            index=["Units Sold", "Total Sales"],
        )

        # Show the table and a bar chart with it
        st.table(comparison)
        st.bar_chart(comparison)
