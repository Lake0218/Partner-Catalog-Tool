import streamlit as st

from processor import load_sales_lookup_from_snowflake, update_partner_catalog


st.set_page_config(page_title="Partner Catalog Zero-Sales Tool", layout="wide")
st.title("Partner Catalog Zero-Sales Tool")

st.write(
    "Upload the partner catalog Excel file. The app will read UPCs from column A "
    "starting at row 3 and write `0 USD` into column I when Snowflake sales over "
    "the last 12 months equal zero."
)

# Streamlit Snowflake connection helper
conn = st.connection("snowflake")

uploaded_catalog = st.file_uploader("Upload partner catalog (.xlsx)", type=["xlsx"])

st.subheader("Snowflake settings")
sales_table = st.text_input("Sales table", value="SALES_TABLE")
upc_column = st.text_input("UPC column in Snowflake", value="UPC")
sales_amount_column = st.text_input("Sales amount column", value="SALES_AMOUNT")
sale_date_column = st.text_input("Sale date column", value="SALE_DATE")

process_clicked = st.button("Process catalog")

if process_clicked:
    if not uploaded_catalog:
        st.error("Please upload a partner catalog file first.")
    else:
        try:
            with st.spinner("Querying Snowflake..."):
                sales_lookup = load_sales_lookup_from_snowflake(
                    conn=conn,
                    sales_table=sales_table,
                    upc_column=upc_column,
                    sales_amount_column=sales_amount_column,
                    sale_date_column=sale_date_column,
                )

            with st.spinner("Updating workbook..."):
                updated_file = update_partner_catalog(uploaded_catalog, sales_lookup)

            zero_count = sum(1 for v in sales_lookup.values() if v == 0)

            st.success("Workbook processed successfully.")
            st.metric("UPCs with zero sales in Snowflake results", zero_count)

            st.download_button(
                label="Download updated workbook",
                data=updated_file,
                file_name="partner_catalog_updated.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            st.error(f"Something went wrong: {e}")
