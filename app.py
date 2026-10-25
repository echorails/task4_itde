"""Task 4 bookstore dashboard, adapted from Cameron Jones's Streamlit Sales Dashboard layout."""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "dashboard_data"


def set_page_config():
    st.set_page_config(page_title="Bookstore Sales Dashboard", page_icon="📚", layout="wide", initial_sidebar_state="expanded")
    st.markdown("<style>footer {visibility: hidden;}</style>", unsafe_allow_html=True)


@st.cache_data
def load_data(store):
    path = DATA_DIR / f"{store.lower()}.json"
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def display_kpi_metrics(data):
    st.header("KPI Metrics")
    daily = pd.DataFrame(data.get("daily_revenue", []))
    total = pd.to_numeric(daily.get("revenue", pd.Series(dtype=float)), errors="coerce").sum()
    cols = st.columns(3)
    cols[0].metric("Total Revenue", f"${total:,.2f}")
    cols[1].metric("Unique Users", f"{data['unique_users']:,}")
    cols[2].metric("Unique Author Sets", f"{data['author_sets']:,}")


def display_charts(data):
    daily = pd.DataFrame(data.get("daily_revenue", []))
    if daily.empty or not {"date", "revenue"}.issubset(daily.columns):
        st.warning("No daily revenue available for this store.")
        return
    daily["date"] = pd.to_datetime(daily["date"])
    daily["revenue"] = pd.to_numeric(daily["revenue"])
    daily = daily.sort_values("date")
    fig = px.line(daily, x="date", y="revenue", title="Daily Revenue", labels={"date": "Date", "revenue": "Revenue (USD)"}, template="plotly_white")
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 5 Days by Revenue")
        top5 = pd.DataFrame(data.get("top_5_days", []))
        if top5.empty:
            top5 = daily.nlargest(5, "revenue").copy()
        top5["date"] = pd.to_datetime(top5["date"]).dt.strftime("%Y-%m-%d")
        top5["revenue"] = pd.to_numeric(top5["revenue"]).map(lambda n: f"${n:,.2f}")
        st.dataframe(top5.rename(columns={"date": "Date", "revenue": "Revenue (USD)"}), hide_index=True, use_container_width=True)
    with col2:
        st.subheader("Most Popular Author(s)")
        authors = data.get("most_popular_authors", [])
        st.write(", ".join(map(str, authors)) if isinstance(authors, list) else str(authors))
        st.subheader("Best Buyer — All User IDs")
        st.code(json.dumps(data.get("best_buyer_ids", [])), language="json")


def main():
    set_page_config()
    st.title("📚 Bookstore Sales Dashboard")
    st.caption("Task 4 · Data Engineering · Five stores")
    st.sidebar.header("Stores")
    st.sidebar.caption("Choose one store to see its results")
    st.sidebar.info("Layout adapted from Cameron Jones's Streamlit Sales Dashboard")
    tabs = st.tabs([f"STORE{i}" for i in range(1, 6)])
    for i, tab in enumerate(tabs, start=1):
        with tab:
            store = f"store{i}"
            data = load_data(store)
            if data is None:
                st.warning(f"Missing dashboard_data/{store}.json. Export results from STORE{i} first.")
                continue
            display_kpi_metrics(data)
            display_charts(data)


if __name__ == "__main__":
    main()
