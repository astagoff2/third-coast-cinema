"""Fetch movie details from Letterboxd."""
import requests
from bs4 import BeautifulSoup
import re
import json
from pathlib import Path
from .utils import logger

CACHE_FILE = Path(__file__).parent.parent / 'data' / 'letterboxd_cache.json'


def load_cache():
    """Load cached Letterboxd data."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_cache(cache):
    """Save Letterboxd cache."""
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)


def title_to_slug(title):
    """Convert movie title to Letterboxd URL slug."""
    # Remove year in parentheses
    title = re.sub(r'\s*\(\d{4}\)\s*', '', title)
    # Convert to lowercase, replace spaces with hyphens
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
    slug = re.sub(r'\s+', '-', slug)  # Spaces to hyphens
    slug = re.sub(r'-+', '-', slug)  # Multiple hyphens to single
    slug = slug.strip('-')
    return slug


def fetch_letterboxd_info(title, year=None):
    """Fetch movie info from Letterboxd."""
    cache = load_cache()

    cache_key = f"{title}|{year}" if year else title
    if cache_key in cache:
        return cache[cache_key]

    slug = title_to_slug(title)
    url = f'https://letterboxd.com/film/{slug}/'

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code != 200:
            # Try with year appended
            if year:
                url = f'https://letterboxd.com/film/{slug}-{year}/'
                resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code != 200:
            cache[cache_key] = None
            save_cache(cache)
            return None

        soup = BeautifulSoup(resp.text, 'lxml')

        info = {
            'letterboxd_url': url,
            'title': None,
            'director': None,
            'rating': None,
            'tagline': None,
            'description': None,
            'poster': None
        }

        # Title
        title_elem = soup.find('h1', class_='headline-1')
        if title_elem:
            info['title'] = title_elem.get_text(strip=True)

        # Director
        director = soup.find('a', href=lambda x: x and '/director/' in x)
        if director:
            info['director'] = director.get_text(strip=True)

        # Rating (from meta tag)
        rating = soup.find('meta', {'name': 'twitter:data2'})
        if rating:
            rating_text = rating.get('content', '')
            match = re.search(r'([\d.]+)', rating_text)
            if match:
                info['rating'] = match.group(1)

        # Tagline
        tagline = soup.find('h4', class_='tagline')
        if tagline:
            info['tagline'] = tagline.get_text(strip=True)

        # Description
        desc = soup.find('div', class_='truncate')
        if desc:
            info['description'] = desc.get_text(strip=True)[:200]

        # Poster - look for the actual poster image
        poster_div = soup.find('div', class_='film-poster')
        if poster_div:
            img = poster_div.find('img')
            if img and img.get('src'):
                info['poster'] = img.get('src')

        cache[cache_key] = info
        save_cache(cache)
        return info

    except Exception as e:
        logger.warning(f"Failed to fetch Letterboxd info for {title}: {e}")
        cache[cache_key] = None
        save_cache(cache)
        return None


def enrich_movies_with_letterboxd(movies):
    """Add Letterboxd info to movies list."""
    # Get unique titles
    unique_titles = {}
    for movie in movies:
        key = movie['title']
        if key not in unique_titles:
            unique_titles[key] = movie.get('year')

    # Fetch info for each unique title
    logger.info(f"Fetching Letterboxd info for {len(unique_titles)} unique films...")
    title_info = {}
    for title, year in unique_titles.items():
        info = fetch_letterboxd_info(title, year)
        if info:
            title_info[title] = info

    logger.info(f"Found Letterboxd data for {len(title_info)} films")

    # Add info to movies
    for movie in movies:
        info = title_info.get(movie['title'])
        if info:
            movie['letterboxd'] = info

    return movies
