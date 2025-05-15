import streamlit as st
import pandas as pd
import aiohttp
import asyncio
import pickle
import time
import numpy as np

# Load the processed data and similarity matrix
with open('movie_data.pkl', 'rb') as file:
    movies, cosine_sim = pickle.load(file)

# Convert movie titles to a NumPy array for fast indexing
movie_titles = movies['title'].to_numpy()

# Function to get movie recommendations (cached for performance)
@st.cache_data
def get_recommendations(title):
    try:
        idx = np.where(movie_titles == title)[0][0]  # Use NumPy for fast lookup
        sim_scores = cosine_sim[idx]
        top_indices = np.argsort(sim_scores)[::-1][1:21]  # Get top 20 recommendations
        return movies.iloc[top_indices][['title', 'movie_id']]
    except IndexError:
        return pd.DataFrame(columns=['title', 'movie_id'])

# Asynchronous function to fetch movie posters with error handling
async def fetch_poster(session, movie_id, api_key):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}"
    await asyncio.sleep(0.5)  # Rate limit to prevent TMDB blocking requests

    try:
        async with session.get(url, timeout=5) as response:
            if response.status == 200:
                data = await response.json()
                poster_path = data.get('poster_path', None)
                if poster_path:
                    return f"https://image.tmdb.org/t/p/w500{poster_path}"
                else:
                    print(f"⚠️ No poster found for movie ID {movie_id}")
                    return "https://via.placeholder.com/150"  # Placeholder for missing posters
            else:
                print(f"❌ Error fetching poster for movie ID {movie_id}: HTTP {response.status}")
                return "https://via.placeholder.com/150"
    except Exception as e:
        print(f"❌ Exception fetching poster for movie ID {movie_id}: {e}")
        return "https://via.placeholder.com/150"

# Batch fetch posters using async
async def fetch_posters(movie_ids, api_key):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_poster(session, movie_id, api_key) for movie_id in movie_ids]
        return await asyncio.gather(*tasks)

# Streamlit UI customization
st.set_page_config(page_title="Movie Recommendation System", layout="wide")

st.markdown("""
    <style>
        .title { text-align: center; font-size: 36px; font-weight: bold; color: #FF1493; }
        .movie-title { font-size: 16px; font-weight: bold; text-align: center; color: #FF1493; }
        .stButton>button { background-color: #FF69B4 !important; color: white !important; border-radius: 15px !important; font-size: 18px !important; transition: all 0.3s ease-in-out; }
        .stButton>button:hover { background-color: #FF1493 !important; transform: scale(1.1); }
    </style>
""", unsafe_allow_html=True)

# Sidebar for user input
st.sidebar.title("💖 Movie Recommendation System")
st.sidebar.write("Find similar movies based on your selection!")

selected_movie = st.sidebar.selectbox("🎥 Select a movie:", movies['title'].values)

if st.sidebar.button('💗 Recommend'):
    with st.spinner('Finding your recommendations...'):
        time.sleep(1)

    recommendations = get_recommendations(selected_movie)

    if recommendations.empty:
        st.error("❌ No recommendations found. Please select a different movie.")
    else:
        st.markdown('<p class="title">💞 Top 20 Recommended Movies 💞</p>', unsafe_allow_html=True)

        # Fetch posters asynchronously
        movie_ids = recommendations['movie_id'].tolist()
        api_key = '7b995d3c6fd91a2284b4ad8cb390c7b8'  # Replace with your TMDB API key

        print("📢 Fetching posters for movie IDs:", movie_ids)  # Debugging

        posters = asyncio.run(fetch_posters(movie_ids, api_key))

        # Display movies in a 4-row grid layout
        cols_per_row = 5
        for i in range(0, 20, cols_per_row):
            cols = st.columns(cols_per_row)
            for col, j in zip(cols, range(i, i + cols_per_row)):
                if j < len(recommendations):
                    movie_title = recommendations.iloc[j]['title']
                    with col:
                        st.image(posters[j], width=180)
                        st.markdown(f'<p class="movie-title">🎬 {movie_title}</p>', unsafe_allow_html=True)
