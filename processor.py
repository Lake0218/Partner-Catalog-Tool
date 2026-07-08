from io import BytesIO
import re

import pandas as pd
from openpyxl import load_workbook

UPC_COL = "A"
OUTPUT_COL = "I"
START_ROW = 3


def normalize_upc(value):
    if value is None or pd.isna(value):
        return None

    if isinstance(value, float) and value.is_integer():
        value = int(value)

    return str(value).strip()


def _validate_identifier(value, label):
    if not value or not isinstance(value, str):
        raise ValueError(f"{label} cannot be empty.")

    allowed = re.compile(r"^[A-Za-z0-9_.$]+$")
    if not allowed.fullmatch(value):
        raise ValueError(
            f"{label} contains invalid characters. Use only letters, numbers, "
            f"underscore, dot, and dollar sign."
        )

    return value


def load_sales_lookup(conn, sales_table, upc_column, sales_amount_column, sale_date_column):
    sales_table = _validate_identifier(sales_table, "Sales table")
    upc_column = _validate_identifier(upc_column, "UPC column")
    sales_amount_column = _validate_identifier(sales_amount_column, "Sales amount column")
    sale_date_column = _validate_identifier(sale_date_column, "Sale date column")

    sql = f"""
        SELECT
            TO_VARCHAR({upc_column}) AS UPC,
            COALESCE(SUM({sales_amount_column}), 0) AS TOTAL_SALES
        FROM {sales_table}
        WHERE {sale_date_column} >= DATEADD(month, -12, CURRENT_DATE())
        GROUP BY TO_VARCHAR({upc_column})
    """

    df = conn.query(sql)

    if df.empty:
        return {}, 0

    df["UPC"] = df["UPC"].apply(normalize_upc)
    df["TOTAL_SALES"] = pd.to_numeric(df["TOTAL_SALES"], errors="coerce").fillna(0)

    sales_lookup = dict(zip(df["UPC"], df["TOTAL_SALES"]))
    return sales_lookup, len(sales_lookup)


def update_partner_catalog(workbook_file, sales_lookup):
    wb = load_workbook(workbook_file)
    ws = wb[wb.sheetnames[0]]

    total_rows = 0
    zero_sales_rows = 0
    missing_rows = 0
    missing_upcs = []

    for row in range(START_ROW, ws.max_row + 1):
        upc = normalize_upc(ws[f"{UPC_COL}{row}"].value)

        if not upc:
            continue

        total_rows += 1
        total_sales = sales_lookup.get(upc, None)

        if total_sales is None:
            missing_rows += 1
            missing_upcs.append(upc)
            ws[f"{OUTPUT_COL}{row}"] = "0 USD"
            zero_sales_rows += 1
        elif float(total_sales) == 0:
            ws[f"{OUTPUT_COL}{row}"] = "0 USD"
            zero_sales_rows += 1

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    summary = {
        "total_rows": total_rows,
        "zero_sales_rows": zero_sales_rows,
        "missing_rows": missing_rows,
        "missing_upcs": missing_upcs,
    }

    return output, summary
