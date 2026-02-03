#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

WS_RE = re.compile(r"\s+")

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def norm(s: str) -> str:
    s = strip_accents(str(s)).casefold()
    s = s.replace("’", "'")
    s = re.sub(r"[^\w\s]+", " ", s)
    s = WS_RE.sub(" ", s).strip()
    return s

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rym_csv", required=True)
    args, _ = parser.parse_known_args()

    rym_csv = Path(args.rym_csv)
    st.set_page_config(page_title="RYM Search", layout="wide")
    st.title("RYM Chart Search")

    if not rym_csv.exists():
        st.error(f"Missing file: {rym_csv}")
        st.stop()

    @st.cache_data
    def load_df(path: str) -> pd.DataFrame:
        df = pd.read_csv(path)
        # normalize expected columns
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
        return df

    df = load_df(str(rym_csv))

    query = st.text_input("Search album or artist", placeholder="e.g., The Cure / Greatest Hits / Cocteau Twins ...")
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

if __name__ == "__main__":
    main()
