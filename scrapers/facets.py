"""Scraper for Facets Cinematheque."""
from bs4 import BeautifulSoup
from .utils import make_request, parse_date, parse_time, clean_text, logger
import re
from datetime import datetime


THEATER_INFO = {
    'name': 'Facets',
    'url': 'https://facets.org',
    'address': '1517 W Fullerton Ave'
}


def scrape_facets():
    """Scrape Facets screening schedule."""
    movies = []
    base_url = 'https://facets.org'

    # Use cinema page which lists screenings
    resp = make_request(f'{base_url}/cinema/')
    if not resp:
        logger.error("Failed to fetch Facets")
        return movies

    soup = BeautifulSoup(resp.text, 'lxml')
    current_year = datetime.now().year

    # Facets uses portfolio list items with class 'edgtf-pli-title'
    # Find all portfolio items
    items = soup.find_all('article', class_=re.compile(r'portfolio-item'))

    if not items:
        # Fallback: find title elements directly
        items = soup.find_all('h5', class_='edgtf-pli-title')

    seen = set()

    for item in items:
        # Get title
        title_elem = item.find('h5', class_='edgtf-pli-title') if item.name == 'article' else item
        if not title_elem:
            continue

        title = clean_text(title_elem.get_text())
        if not title or len(title) < 2:
            continue

        # Skip non-movie items
        skip_words = ['film camp', 'critic', 'trivia', 'party', 'membership',
                      'gift', 'rental', 'anime club', 'presents']
        title_lower = title.lower()
        if any(s in title_lower for s in skip_words):
            continue

        if title in seen:
            continue
        seen.add(title)

        # Get the full item text for date/time extraction
        text = clean_text(item.get_text()) if item.name == 'article' else ''

        # Find dates in the item
        date_match = re.search(
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}',
            text, re.I
        )
        date_str = None
        if date_match:
            date_str = parse_date(date_match.group(0), current_year)

        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')

        # Find times
        time_matches = re.findall(r'(\d{1,2}:\d{2}\s*(?:pm|am)?)', text, re.I)
        times = [parse_time(t) for t in time_matches if t]

        # Get link
        link = item.find('a', href=True)
        if link:
            event_url = link.get('href', '')
            if event_url and not event_url.startswith('http'):
                event_url = base_url + event_url
        else:
            event_url = f'{base_url}/cinema/'

        movies.append({
            'title': title,
            'theater': THEATER_INFO['name'],
            'theater_url': THEATER_INFO['url'],
            'address': THEATER_INFO['address'],
            'date': date_str,
            'times': times if times else ['See website'],
            'format': None,
            'director': None,
            'year': None,
            'ticket_url': event_url
        })

    logger.info(f"Facets: Found {len(movies)} screenings")
    return movies


if __name__ == '__main__':
    results = scrape_facets()
    for m in results:
        print(f"{m['date']} - {m['title']} @ {m['times']}")
