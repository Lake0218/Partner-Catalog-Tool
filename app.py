import threading
import time
import webbrowser

import streamlit as st
import pandas as pd
import snowflake.connector

from processor import load_sales_lookup, update_partner_catalog

st.set_page_config(page_title="Partner Catalog Zero-Sales Tool", layout="wide")


class SnowflakeAuthState:
    def __init__(self):
        self.lock = threading.Lock()
        self.status = "idle"
        self.auth_url = None
        self.conn = None
        self.error = None
        self.thread = None

    def reset(self):
        with self.lock:
            self.status = "idle"
            self.auth_url = None
            self.conn = None
            self.error = None
            self.thread = None


@st.cache_resource(show_spinner=False)
def get_externalbrowser_auth_state():
    return SnowflakeAuthState()

st.title("Partner Catalog Zero-Sales Tool")

st.write(
    "Upload the partner catalog Excel file. The app reads UPCs from column A "
    "starting at row 3 and writes `0 USD` into column I when Snowflake sales "
    "over the last 12 months equal zero."
)

uploaded_catalog = st.file_uploader("Upload partner catalog (.xlsx)", type=["xlsx"])

with st.sidebar:
    st.header("Snowflake settings")
    st.caption(
        "Authentication uses the Snowflake connection provided by Streamlit. "
        "In Snowflake, no password secret is needed."
    )
    st.code(
        """# Optional for local development only:
[connections.snowflake]
account = "JD38204-MT76814"
user = "L.HAWK@FETCHREWARDS.COM"
authenticator = "externalbrowser"
login_timeout = 300
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

def get_local_snowflake_config():
    try:
        sf = st.secrets.get("connections", {}).get("snowflake", {})
    except Exception:
        return {}

    if hasattr(sf, "to_dict"):
        sf = sf.to_dict()
    else:
        sf = dict(sf)

    return {
        key: value
        for key, value in sf.items()
        if value and not str(value).startswith("YOUR_")
    }


def connect_with_captured_sso(config, auth_state):
    original_open_new = webbrowser.open_new

    def capture_auth_url(url):
        with auth_state.lock:
            auth_state.auth_url = url
            auth_state.status = "waiting_for_sso"
        return True

    try:
        webbrowser.open_new = capture_auth_url
        conn = snowflake.connector.connect(**config)
        with auth_state.lock:
            auth_state.conn = conn
            auth_state.status = "connected"
    except Exception as exc:
        with auth_state.lock:
            auth_state.error = exc
            auth_state.status = "error"
    finally:
        webbrowser.open_new = original_open_new


def start_externalbrowser_auth(config, auth_state):
    with auth_state.lock:
        if auth_state.status in {"starting", "waiting_for_sso"}:
            return
        auth_state.status = "starting"
        auth_state.auth_url = None
        auth_state.error = None
        auth_state.conn = None

    thread = threading.Thread(
        target=connect_with_captured_sso,
        args=(config, auth_state),
        daemon=True,
    )
    with auth_state.lock:
        auth_state.thread = thread
    thread.start()


def get_externalbrowser_connection(config):
    auth_state = get_externalbrowser_auth_state()

    with auth_state.lock:
        if auth_state.conn is not None:
            return auth_state.conn

    start_externalbrowser_auth(config, auth_state)

    for _ in range(30):
        with auth_state.lock:
            if auth_state.auth_url or auth_state.conn is not None or auth_state.error:
                break
        time.sleep(0.1)

    with auth_state.lock:
        status = auth_state.status
        auth_url = auth_state.auth_url
        conn = auth_state.conn
        error = auth_state.error

    if conn is not None:
        return conn

    if status == "error":
        st.error("Snowflake sign-in did not complete.")
        st.exception(error)
        if st.button("Start Snowflake sign-in again"):
            auth_state.reset()
            st.rerun()
        st.stop()

    st.warning("Snowflake needs browser SSO before the catalog can be processed.")
    if auth_url:
        st.link_button("Open Snowflake SSO", auth_url, type="primary")
        st.info(
            "After the Snowflake sign-in tab says login succeeded, return here "
            "and click Process catalog again."
        )
    else:
        st.info("Preparing the Snowflake SSO link. Click Process catalog again in a moment.")
    st.stop()


def get_snowflake_connection():
    try:
        config = get_local_snowflake_config()
        authenticator = str(config.get("authenticator", "")).lower()
        if config and authenticator == "externalbrowser":
            return get_externalbrowser_connection(config)
        if config:
            return snowflake.connector.connect(**config)
        return st.connection("snowflake")
    except Exception as exc:
        st.error(
            "Could not create the Snowflake connection. In Snowflake, make sure "
            "the Streamlit app has a query warehouse. For local development, add "
            "a [connections.snowflake] block to .streamlit/secrets.toml."
        )
        st.exception(exc)
        st.stop()

if process_clicked:
    try:
        conn = get_snowflake_connection()

        with st.spinner("Querying Snowflake for the last 12 months of sales..."):
            sales_lookup = load_sales_lookup(conn=conn)

        with st.spinner("Updating workbook..."):
            updated_file, summary = update_partner_catalog(
                workbook_file=uploaded_catalog,
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
