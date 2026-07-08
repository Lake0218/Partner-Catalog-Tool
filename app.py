import streamlit as st
import pandas as pd
import snowflake.connector

from processor import load_sales_lookup, update_partner_catalog

st.set_page_config(page_title="Partner Catalog Zero-Sales Tool", layout="wide")
st.title("Partner Catalog Zero-Sales Tool")

st.write(
    "Upload the partner catalog Excel file. The app reads UPCs from column A "
    "starting at row 3 and writes `0 USD` into column I when Snowflake sales "
    "over the last 12 months equal zero."
)

uploaded_catalog = st.file_uploader("Upload partner catalog (.xlsx)", type=["xlsx"])

with st.sidebar:
    st.header("Snowflake settings")
    st.caption("These values come from Streamlit Secrets.")
    st.code(
        """[connections.snowflake]
account = "JD38204-MT76814"
user = "L.HAWK@FETCHREWARDS.COM"
password = "YOUR_PASSWORD"
warehouse = "YOUR_WAREHOUSE"
database = "YOUR_DATABASE"
schema = "YOUR_SCHEMA"
role = "H_DATASCI"
""",
        language="toml",
    )

process_clicked = st.button(
    "Process catalog",
    type="primary",
    disabled=uploaded_catalog is None,
)

def get_snowflake_connection():
    try:
        sf = st.secrets["connections"]["snowflake"]
    except Exception:
        st.error(
            "Missing Streamlit secrets. Add the [connections.snowflake] block "
            "in the app settings."
        )
        st.stop()

    required = ["account", "user", "password"]
    missing = [key for key in required if not sf.get(key)]
    if missing:
        st.error(f"Missing required Snowflake secret values: {', '.join(missing)}")
        st.stop()

    return snowflake.connector.connect(
        account=sf["account"],
        user=sf["user"],
        password=sf["password"],
        role=sf.get("role"),
        warehouse=sf.get("warehouse"),
        database=sf.get("database"),
        schema=sf.get("schema"),
    )

if process_clicked:
    try:
        conn = get_snowflake_connection()

        with st.spinner("Querying Snowflake for the last 12 months of sales..."):
            sales_lookup, matched_upcs = load_sales_lookup(
                conn=conn,
                sales_table="YOUR_DATABASE.YOUR_SCHEMA.SALES_TABLE",
                upc_column="UPC",
                sales_amount_column="SALES_AMOUNT",
                sale_date_column="SALE_DATE",
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
