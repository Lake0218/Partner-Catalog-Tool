from io import BytesIO

import pandas as pd
from openpyxl import load_workbook


UPC_COL = "A"
OUTPUT_COL = "I"
START_ROW = 3


def normalize_upc(value):
    """Normalize UPC values so Excel and Snowflake values match cleanly."""
    if value is None or pd.isna(value):
        return None

    if isinstance(value, float) and value.is_integer():
        value = int(value)

    return str(value).strip()


def load_sales_lookup_from_snowflake(
    conn,
    sales_table: str,
    upc_column: str,
    sales_amount_column: str,
    sale_date_column: str,
):
    """
    Query Snowflake for UPC-level sales totals over the last 12 months.
    Returns a dict like: { '123456789012': 0, '999999999999': 42.50 }
    """
    sql = f"""
        SELECT
            TO_VARCHAR({upc_column}) AS UPC,
            COALESCE(SUM({sales_amount_column}), 0) AS TOTAL_SALES
        FROM {sales_table}
        WHERE {sale_date_column} >= DATEADD(month, -12, CURRENT_DATE())
        GROUP BY TO_VARCHAR({upc_column})
    """

    df = conn.query(sql, ttl="10m")
    df["UPC"] = df["UPC"].apply(normalize_upc)
    return dict(zip(df["UPC"], df["TOTAL_SALES"]))


def update_partner_catalog(workbook_file, sales_lookup):
    """
    Reads the first worksheet in the uploaded workbook.
    For each row starting at row 3:
      - read UPC from column A
      - if sales over last 12 months are 0, write '0 USD' to column I
    Returns workbook bytes.
    """
    wb = load_workbook(workbook_file)
    ws = wb[wb.sheetnames[0]]

    for row in range(START_ROW, ws.max_row + 1):
        upc = normalize_upc(ws[f"{UPC_COL}{row}"].value)
        if not upc:
            continue

        total_sales = sales_lookup.get(upc, 0)
        if total_sales == 0:
            ws[f"{OUTPUT_COL}{row}"] = "0 USD"

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
