"""Scraper for Doc Films (University of Chicago)."""
from bs4 import BeautifulSoup
from .utils import make_request, parse_date, parse_time, clean_text, logger
import re
from datetime import datetime


THEATER_INFO = {
    'name': 'Doc Films',
    'url': 'https://docfilms.org',
    'address': 'Max Palevsky Cinema, Ida Noyes Hall, 1212 E 59th St'
}


def scrape_doc_films():
    """Scrape Doc Films weekly schedule."""
    movies = []
    base_url = 'https://docfilms.org'

    resp = make_request(base_url)
    if not resp:
        logger.error("Failed to fetch Doc Films")
        return movies

    soup = BeautifulSoup(resp.text, 'lxml')
    current_year = datetime.now().year

    # Build a map of film titles to their calendar URLs from carousel
    title_to_url = {}
    for slide in soup.find_all(class_='carousel__slide'):
        link = slide.find('a')
        if link:
            href = link.get('href', '')
            text = slide.get_text(strip=True)
            # Extract title from format: "Title (Year) · Director · ..."
            title_match = re.match(r'([^(]+)\s*\((\d{4})\)', text)
            if title_match:
                title = clean_text(title_match.group(1))
                if href and not href.startswith('http'):
                    href = base_url + '/' + href.lstrip('/')
                title_to_url[title.lower()] = href

    # Parse the cards section for weekly schedule
    cards = soup.find(class_='cards')
    if not cards:
        logger.warning("Doc Films: Could not find cards section")
        return movies

    seen = set()

    for item in cards.find_all(['div', 'a'], recursive=False):
        text = item.get_text(strip=True)
        if not text:
            continue

        # Pattern: "Title (Year)Day, Month Date @ Time[Format]"
        # Some films have multiple dates: "Friday, February 6 @ 7:00 PM · Saturday, February 7 @ 9:30 PM"

        # Extract title and year
        title_match = re.match(r'([^(]+)\s*\(([^)]+)\)', text)
        if not title_match:
            continue

        title = clean_text(title_match.group(1))
        year_str = title_match.group(2)

        # Try to parse year (might be "2020 / 2002 / 1976" for shorts programs)
        year = None
        year_match = re.search(r'\d{4}', year_str)
        if year_match:
            year = int(year_match.group())

        remainder = text[title_match.end():]

        # Find format at the end (35mm, DCP, Digital, etc.)
        format_match = re.search(r'(35mm|16mm|70mm|DCP|[Dd]igital)(?:\s*/\s*(?:35mm|16mm|DCP|[Dd]igital))*\s*$', remainder)
        film_format = format_match.group(1) if format_match else None

        # Find all date/time pairs
        # Pattern: "Day, Month Date @ Time"
        datetime_pattern = r'((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+\w+\s+\d{1,2})\s*@\s*(\d{1,2}:\d{2}\s*[APap][Mm])'
        datetime_matches = re.findall(datetime_pattern, remainder)

        if not datetime_matches:
            continue

        # Get ticket URL
        ticket_url = title_to_url.get(title.lower(), base_url)

        for date_str, time_str in datetime_matches:
            date = parse_date(date_str, current_year)
            time = parse_time(time_str)

            if not date:
                continue

            key = f"{title}|{date}|{time}"
            if key in seen:
                continue
            seen.add(key)

            movies.append({
                'title': title,
                'theater': THEATER_INFO['name'],
                'theater_url': THEATER_INFO['url'],
                'address': THEATER_INFO['address'],
                'date': date,
                'times': [time] if time else ['See website'],
                'format': film_format,
                'director': None,
                'year': year,
                'ticket_url': ticket_url
            })

    logger.info(f"Doc Films: Found {len(movies)} screenings")
    return movies


if __name__ == '__main__':
    results = scrape_doc_films()
    for m in results:
        print(f"{m['date']} - {m['title']} ({m.get('year', '?')}) @ {m['times']} [{m.get('format', '')}] -> {m['ticket_url']}")
