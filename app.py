# app.py
import os
import re
import pickle
import requests
import streamlit as st


st.set_page_config(page_title="Movie Recommender (OMDb Posters)", layout="wide")


OMDB_API_KEY = os.environ.get("OMDB_API_KEY", "")

# try to read st.secrets only if necessary, and handle missing secrets gracefully
if not OMDB_API_KEY:
    try:
        OMDB_API_KEY = st.secrets.get("OMDB_API_KEY", "")  # safe even if secrets.toml missing in recent Streamlit
    except Exception:
        OMDB_API_KEY = "88596c57"
FALLBACK_POSTER = "https://via.placeholder.com/300x450?text=No+Poster"
REQUEST_TIMEOUT = (3.05, 7)

_imdb_re = re.compile(r"^tt\d+$", re.IGNORECASE)

def looks_like_imdb_id(x):
    try:
        return bool(isinstance(x, str) and _imdb_re.match(x.strip()))
    except Exception:
        return False

@st.cache_data(show_spinner=False)
def fetch_poster_omdb_by_imdb(imdb_id):
    if not OMDB_API_KEY:
        return FALLBACK_POSTER
    url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        j = r.json()
        poster = j.get("Poster")
        if poster and poster != "N/A":
            return poster
    except Exception as e:
        print("OMDb by imdb failed:", e)
    return FALLBACK_POSTER

@st.cache_data(show_spinner=False)
def fetch_poster_omdb_by_title(title):
    if not OMDB_API_KEY:
        return FALLBACK_POSTER
    q = requests.utils.quote(title)
    url = f"http://www.omdbapi.com/?t={q}&apikey={OMDB_API_KEY}"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        j = r.json()
        poster = j.get("Poster")
        if poster and poster != "N/A":
            return poster
    except Exception as e:
        print("OMDb by title failed:", e)
    return FALLBACK_POSTER

def fetch_poster_for_row(row):
    mid = row.get("movie_id", None)
    if mid is not None and looks_like_imdb_id(str(mid)):
        return fetch_poster_omdb_by_imdb(str(mid).strip())
    title = row.get("title") or row.get("Title")
    if title:
        return fetch_poster_omdb_by_title(title)
    return FALLBACK_POSTER

def recommend(movie, topn=5):
    matched = movies[movies['title'] == movie]
    if matched.empty:
        return [], []
    idx = matched.index[0]
    try:
        sims = list(enumerate(similarity[idx]))
    except Exception as e:
        print("Similarity indexing failed:", e)
        return [], []
    distances = sorted(sims, reverse=True, key=lambda x: x[1])
    names = []
    posters = []
    for i_score in distances[1: 1 + topn]:
        i = i_score[0]
        try:
            title = movies.iloc[i].title
            row = movies.iloc[i]
        except Exception:
            title = "Unknown"
            row = {}
        names.append(title)
        posters.append(fetch_poster_for_row(row))
    return names, posters


try:
    movies = pickle.load(open("movie_list.pkl", "rb"))
    similarity = pickle.load(open("similarity.pkl", "rb"))
except Exception as e:
    st.error(f"Failed to load pickles: {e}")
    st.stop()

st.sidebar.markdown("### Dataset check")
with st.sidebar.expander("Preview movie_id samples"):
    try:
        sample_ids = movies['movie_id'].head(10).tolist()
        st.write(sample_ids)
        st.write("Looks like IMDb id? ", [looks_like_imdb_id(str(x)) for x in sample_ids])
    except Exception as e:
        st.write("Could not preview movie_id:", e)

if 'title' not in movies.columns:
    st.error("Your movies DataFrame must contain a 'title' column (case-sensitive).")
    st.stop()

movie_list = movies['title'].values
selected_movie = st.selectbox("Type or select a movie from the dropdown", movie_list)

if st.button("Show Recommendation"):
    names, poster_urls = recommend(selected_movie)
    if not names:
        st.info("No recommendations available.")
    else:
        n = len(names)
        width_map = {1: 800, 2: 500, 3: 360, 4: 280, 5: 220}
        img_width = width_map.get(n, max(160, int(1100 / n)))
        cols = st.columns(n)
        for i, col in enumerate(cols):
            with col:
                st.subheader(names[i])
                try:
                    st.image(poster_urls[i], width=img_width)
                except Exception as e:
                    print("st.image failed:", e)
                    st.write("Poster unavailable")
