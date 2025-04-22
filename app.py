from flask import Flask, render_template, request
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
from tmdbv3api import TMDb, Movie
import datetime
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize TMDB
tmdb = TMDb()
tmdb.api_key = app.config['TMDB_API_KEY']
tmdb.language = 'en'
tmdb.debug = True

movie_api = Movie()

def get_tmdb_movie_info(movie_title, year=None):
    """Search for movie in TMDB and return details"""
    try:
        search = movie_api.search(movie_title)
        if search:
            if year:
                # Try to find the movie matching the year
                for result in search:
                    release_date = result.release_date
                    if release_date and str(datetime.datetime.strptime(release_date, '%Y-%m-%d').year) == str(year):
                        return result
            # Return the first result if no year match found
            return search[0]
    except Exception as e:
        print(f"Error searching TMDB: {e}")
    return None

def get_telegram_movies(limit=100):
    """Fetch recent movies from Telegram channel"""
    movies = []
    
    with TelegramClient('session_name', 
                      app.config['TELEGRAM_API_ID'], 
                      app.config['TELEGRAM_API_HASH']) as client:
        for message in client.iter_messages(app.config['TELEGRAM_CHANNEL'], limit=limit):
            if message.media:
                movie_info = {
                    'telegram_message_id': message.id,
                    'date': message.date,
                    'text': message.text,
                    'media': None,
                    'tmdb_info': None
                }
                
                # Extract movie title from message text
                movie_title = message.text.split('\n')[0] if message.text else "Untitled"
                
                # Try to extract year from title (format: "Movie Name (2023)")
                year = None
                if '(' in movie_title and ')' in movie_title:
                    year_part = movie_title.split('(')[-1].split(')')[0]
                    if year_part.isdigit() and len(year_part) == 4:
                        year = int(year_part)
                        movie_title = movie_title.split('(')[0].strip()
                
                # Get TMDB info
                tmdb_info = get_tmdb_movie_info(movie_title, year)
                if tmdb_info:
                    movie_info['tmdb_info'] = {
                        'title': tmdb_info.title,
                        'overview': tmdb_info.overview,
                        'poster_path': f"https://image.tmdb.org/t/p/w500{tmdb_info.poster_path}" if tmdb_info.poster_path else None,
                        'release_date': tmdb_info.release_date,
                        'vote_average': tmdb_info.vote_average,
                        'id': tmdb_info.id
                    }
                
                # Handle media
                if isinstance(message.media, MessageMediaDocument):
                    movie_info['media'] = {
                        'type': 'document',
                        'filename': message.media.document.attributes[0].file_name if hasattr(message.media.document, 'attributes') else 'file'
                    }
                elif isinstance(message.media, MessageMediaPhoto):
                    movie_info['media'] = {'type': 'photo'}
                
                movies.append(movie_info)
    
    return movies

@app.route('/')
def index():
    limit = request.args.get('limit', default=20, type=int)
    movies = get_telegram_movies(limit=limit)
    return render_template('index.html', movies=movies)

if __name__ == '__main__':
    app.run(debug=app.config['FLASK_DEBUG'])
