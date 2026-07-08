import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
from snowflake.snowpark.context import get_active_session

from processor import load_sales_lookup, update_partner_catalog

LOOKBACK_MONTHS = 24

UPC_COL = "A"
OUTPUT_COL = "I"
START_ROW = 3


st.set_page_config(page_title="Partner Catalog Zero-Sales Tool", layout="wide")
st.title("Partner Catalog Zero-Sales Tool")

st.write(
    "Upload the partner catalog Excel file. The app reads UPCs from column A "
    "starting at row 3 and writes `0 USD` into column I when Snowflake sales "
    f"over the last {LOOKBACK_MONTHS} months equal zero."
)

uploaded_catalog = st.file_uploader("Upload partner catalog (.xlsx)", type=["xlsx"])

if st.button("Process", disabled=uploaded_catalog is None):
    try:
        session = get_active_session()

        with st.spinner(f"Querying Snowflake for the last {LOOKBACK_MONTHS} months of sales..."):
            sales_lookup = load_sales_lookup(session, lookback_months=LOOKBACK_MONTHS)

        with st.spinner("Updating workbook..."):
            workbook_bytes = BytesIO(uploaded_catalog.getvalue())
            updated_file, summary = update_partner_catalog(
                workbook_file=workbook_bytes,
                sales_lookup=sales_lookup,
            )

        st.success("Workbook processed successfully.")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("UPCs in file", summary["total_rows"])
        col2.metric("UPCs with zero sales", summary["zero_sales_rows"])
        col3.metric("UPCs found in Snowflake", summary["matched_rows"])
        col4.metric("UPCs missing in Snowflake", summary["missing_rows"])

        st.download_button(
            label="Download updated workbook",
            data=updated_file.getvalue(),
            file_name="partner_catalog_updated.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        if summary["missing_upcs"]:
            with st.expander("UPCs not found in Snowflake sales data"):
                st.write(pd.DataFrame({"UPC": summary["missing_upcs"]}))

    except Exception as e:
        st.error(f"Something went wrong: {e}")
