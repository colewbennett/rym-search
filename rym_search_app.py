import pandas as pd
import streamlit as st
import re
import unicodedata
from pathlib import Path

WS_RE = re.compile(r"\s+")

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def norm(s: str) -> str:
    s = strip_accents(str(s)).casefold()
    s = s.replace("’", "'")
    s = re.sub(r"[^\w\s]+", " ", s)
    s = WS_RE.sub(" ", s).strip()
    return s

def load_df_from_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    # normalize expected columns
    if "album_title" not in df.columns and "title" in df.columns:
        df["album_title"] = df["title"]

    needed = ["ranking", "album_title", "artist", "rating", "num_ratings"]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    df["ranking"] = pd.to_numeric(df["ranking"], errors="coerce").astype("Int64")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["num_ratings"] = pd.to_numeric(df["num_ratings"], errors="coerce").astype("Int64")

    df["title_norm"] = df["album_title"].fillna("").map(norm)
    df["artist_norm"] = df["artist"].fillna("").map(norm)
    return df

st.set_page_config(page_title="RYM Search", layout="wide")
st.title("RYM Chart Search")

# Try to load rym_chart.csv from repo root by default
default_csv = Path("rym_chart.csv")

uploaded = st.sidebar.file_uploader("If needed, upload rym_chart.csv", type=["csv"])

df = None
try:
    if uploaded is not None:
        df = pd.read_csv(uploaded)
        # save it in-memory pipeline by writing to a temp-like DataFrame process
        # (no need to persist on Streamlit Cloud)
        if "album_title" not in df.columns and "title" in df.columns:
            df["album_title"] = df["title"]
        for col in ["ranking", "album_title", "artist", "rating", "num_ratings"]:
            if col not in df.columns:
                df[col] = ""
        df["ranking"] = pd.to_numeric(df["ranking"], errors="coerce").astype("Int64")
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        df["num_ratings"] = pd.to_numeric(df["num_ratings"], errors="coerce").astype("Int64")
        df["title_norm"] = df["album_title"].fillna("").map(norm)
        df["artist_norm"] = df["artist"].fillna("").map(norm)
    else:
        if not default_csv.exists():
            st.error("I can’t find `rym_chart.csv` in the app repo. Upload it in the sidebar or add it to the repo root.")
            st.stop()
        df = load_df_from_csv(default_csv)
except Exception as e:
    st.error(f"Failed to load chart CSV: {e}")
    st.stop()

st.success(f"Loaded {len(df):,} rows.")

query = st.text_input(
    "Search album or artist",
    placeholder="e.g., The Cure / Greatest Hits / Cocteau Twins ..."
)
max_rows = st.slider("Max results", 5, 100, 25)

if query.strip():
    q = norm(query)
    hits = df[df["title_norm"].str.contains(q, na=False) | df["artist_norm"].str.contains(q, na=False)].copy()
    hits = hits.sort_values("ranking", na_position="last").head(max_rows)

    st.write(f"Matches: {len(hits)} (showing up to {max_rows})")

    show = hits[["ranking", "artist", "album_title", "rating", "num_ratings"]].copy()
    show = show.rename(columns={
        "ranking": "Rank",
        "artist": "Artist",
        "album_title": "Title",
        "rating": "Rating",
        "num_ratings": "#Ratings",
    })
    st.dataframe(show, use_container_width=True, hide_index=True)
else:
    st.info("Type a name to search your chart list.")
