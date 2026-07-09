from collections import Counter

from processor import run_snowflake_query


BUSINESS_LOOKUP_SQL = """
    SELECT
        ID AS BUSINESS_ID,
        NAME AS BUSINESS_NAME
    FROM ANALYTICS_PROD.DURIN_SERVICE.P_BUSINESS
    WHERE NAME IS NOT NULL
    ORDER BY NAME
"""


def normalize_column_name(column):
    return str(column).strip().strip('"').upper()


def normalize_business_columns(df):
    df = df.copy()
    df.columns = [normalize_column_name(column) for column in df.columns]

    column_map = {}
    if "BUSINESS_ID" in df.columns:
        column_map["BUSINESS_ID"] = "ID"
    elif "ID" in df.columns:
        column_map["ID"] = "ID"
    elif len(df.columns) >= 1:
        column_map[df.columns[0]] = "ID"

    if "BUSINESS_NAME" in df.columns:
        column_map["BUSINESS_NAME"] = "NAME"
    elif "NAME" in df.columns:
        column_map["NAME"] = "NAME"
    elif len(df.columns) >= 2:
        column_map[df.columns[1]] = "NAME"

    df = df.rename(columns=column_map)
    missing_columns = {"ID", "NAME"} - set(df.columns)
    if missing_columns:
        raise ValueError(
            "Business lookup query did not return expected columns. "
            f"Expected ID and NAME, got: {', '.join(df.columns)}"
        )

    return df[["ID", "NAME"]]


def load_businesses(conn):
    df = run_snowflake_query(conn, BUSINESS_LOOKUP_SQL)
    if df.empty:
        return []

    df = normalize_business_columns(df).dropna()
    df["ID"] = df["ID"].astype(str).str.strip()
    df["NAME"] = df["NAME"].astype(str).str.strip()
    df = df[(df["ID"] != "") & (df["NAME"] != "")]
    df = df.drop_duplicates(subset=["ID"], keep="first")

    name_counts = Counter(df["NAME"])
    businesses = []
    for row in df.sort_values("NAME").itertuples(index=False):
        label = row.NAME
        if name_counts[row.NAME] > 1:
            label = f"{row.NAME} ({row.ID})"

        businesses.append(
            {
                "id": row.ID,
                "name": row.NAME,
                "label": label,
            }
        )

    return businesses
