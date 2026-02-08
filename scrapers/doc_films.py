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


def get_series_urls():
    """Get all series page URLs from the calendar page."""
    base_url = 'https://docfilms.org'
    calendar_url = f'{base_url}/calendar/'

    resp = make_request(calendar_url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, 'lxml')
    series_urls = set()

    # Find all series links (format: /calendar/2026winter/series-name)
    for link in soup.find_all('a', href=True):
        href = link['href']
        if re.match(r'/calendar/\d{4}\w+/[\w-]+', href):
            full_url = base_url + href
            series_urls.add(full_url)

    return list(series_urls)


def parse_series_page(url):
    """Parse a series page and extract all screenings."""
    movies = []
    base_url = 'https://docfilms.org'
    current_year = datetime.now().year

    resp = make_request(url)
    if not resp:
        return movies

    soup = BeautifulSoup(resp.text, 'lxml')

    # Find all screening divs
    screenings = soup.find_all('div', class_='screening')

    for screening in screenings:
        # Get title from h2 (format: "Title (Year)")
        h2 = screening.find('h2')
        if not h2:
            continue

        title_text = h2.get_text(strip=True)
        title_match = re.match(r'(.+?)\s*\((\d{4})\)', title_text)
        if not title_match:
            continue

        title = clean_text(title_match.group(1))
        year = int(title_match.group(2))

        # Get director and format from first h3
        h3_list = screening.find_all('h3')
        director = None
        film_format = None

        if h3_list:
            # First h3 has director · runtime · format
            info_h3 = h3_list[0].get_text(strip=True)
            parts = [p.strip() for p in info_h3.split('·')]
            if parts:
                director = parts[0]
            # Look for format
            format_match = re.search(r'(35mm|16mm|70mm|DCP|Digital)', info_h3, re.I)
            if format_match:
                film_format = format_match.group(1)

        # Get dates and times from last h3
        if len(h3_list) >= 2:
            datetime_h3 = h3_list[-1]
            datetime_text = datetime_h3.get_text(strip=True)

            # Pattern: "Friday, February 13 7:00 PM" or "Friday, February 6 7:00 PM · Saturday, February 7 9:30 PM"
            # The time links are inside <a> tags, so text concatenates
            datetime_pattern = r'((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2})\s*(\d{1,2}:\d{2}\s*[APap][Mm])'

            matches = re.findall(datetime_pattern, datetime_text)

            for date_str, time_str in matches:
                date = parse_date(date_str, current_year)
                time = parse_time(time_str)

                if not date:
                    continue

                # Get the screening anchor ID for direct link
                screening_id = screening.get('id', '')
                ticket_url = f"{url}#{screening_id}" if screening_id else url

                movies.append({
                    'title': title,
                    'theater': THEATER_INFO['name'],
                    'theater_url': THEATER_INFO['url'],
                    'address': THEATER_INFO['address'],
                    'date': date,
                    'times': [time] if time else ['See website'],
                    'format': film_format,
                    'director': director,
                    'year': year,
                    'ticket_url': ticket_url
                })

    return movies


def scrape_doc_films():
    """Scrape Doc Films schedule from all series pages."""
    movies = []
    seen = set()

    # Get all series page URLs
    series_urls = get_series_urls()
    logger.info(f"Doc Films: Found {len(series_urls)} series pages")

    # Parse each series page
    for url in series_urls:
        page_movies = parse_series_page(url)
        for movie in page_movies:
            # Deduplicate by title+date+time
            key = f"{movie['title']}|{movie['date']}|{movie['times'][0]}"
            if key not in seen:
                seen.add(key)
                movies.append(movie)

    logger.info(f"Doc Films: Found {len(movies)} total screenings")
    return movies


if __name__ == '__main__':
    results = scrape_doc_films()
    for m in sorted(results, key=lambda x: x['date']):
        print(f"{m['date']} - {m['title']} ({m.get('year', '?')}) @ {m['times']} [{m.get('format', '')}]")
