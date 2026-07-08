import streamlit as st
import pandas as pd

from processor import load_sales_lookup, update_partner_catalog

st.set_page_config(page_title="Partner Catalog Zero-Sales Tool", layout="wide")
st.title("Partner Catalog Zero-Sales Tool")

st.write(
    "Upload the partner catalog Excel file. The app reads UPCs from column A "
    "starting at row 3 and writes `0 USD` into column I when Snowflake sales "
    "over the last 12 months equal zero."
)

conn = st.connection("snowflake")

with st.sidebar:
    st.header("Snowflake settings")
    sales_table = st.text_input("Sales table", value="SALES_TABLE")
    upc_column = st.text_input("UPC column in Snowflake", value="UPC")
    sales_amount_column = st.text_input("Sales amount column", value="SALES_AMOUNT")
    sale_date_column = st.text_input("Sale date column", value="SALE_DATE")
    st.caption("Use trusted internal table and column names.")

uploaded_catalog = st.file_uploader("Upload partner catalog (.xlsx)", type=["xlsx"])

process_clicked = st.button(
    "Process catalog",
    type="primary",
    disabled=uploaded_catalog is None,
)

if process_clicked:
    try:
        with st.spinner("Querying Snowflake for the last 12 months of sales..."):
            sales_lookup, matched_upcs = load_sales_lookup(
                conn=conn,
                sales_table=sales_table,
                upc_column=upc_column,
                sales_amount_column=sales_amount_column,
                sale_date_column=sale_date_column,
            )

        with st.spinner("Updating workbook..."):
            updated_file, summary = update_partner_catalog(
                workbook_file=uploaded_catalog,
                sales_lookup=sales_lookup,
            )

        st.success("Workbook processed successfully.")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("UPCs in file", summary["total_rows"])
        col2.metric("UPCs with zero sales", summary["zero_sales_rows"])
        col3.metric("UPCs found in Snowflake", matched_upcs)
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
