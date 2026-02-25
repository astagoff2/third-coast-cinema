"""Scraper for Davis Theater."""
from bs4 import BeautifulSoup
from .utils import parse_time, logger
import requests
import re
from datetime import datetime, timedelta

THEATER_INFO = {
    'name': 'Davis Theater',
    'url': 'https://davistheater.com',
    'address': '4614 N Lincoln Ave'
}


def scrape_davis():
    """Scrape Davis Theater schedule from their website."""
    movies = []

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        # Scrape today and next 6 days
        for day_offset in range(7):
            date = datetime.now() + timedelta(days=day_offset)
            date_str = date.strftime('%Y-%m-%d')

            # Davis Theater uses date paths like /2026-02-25
            url = f'{THEATER_INFO["url"]}/{date_str}'
            resp = requests.get(url, headers=headers, timeout=30)

            if resp.status_code != 200:
                logger.warning(f"Davis Theater: Got status code {resp.status_code} for {date_str}")
                continue

            soup = BeautifulSoup(resp.text, 'lxml')

            # Find the now-playing panel
            panel = soup.find('div', {'data-type': 'now-playing'})
            if not panel:
                continue

            # Find all show divs and their corresponding showtimes
            shows = panel.find_all('div', class_='show')

            for show in shows:
                # Get title from h2
                h2 = show.find('h2')
                if not h2:
                    continue

                title = h2.get_text(strip=True)
                # Remove quotes from title if present (e.g., "Wuthering Heights")
                title = title.strip('"').strip("'")
                if not title:
                    continue

                # Get movie page URL
                movie_link = show.find('a', href=lambda x: x and '/movies/' in x)
                movie_url = movie_link['href'] if movie_link else THEATER_INFO['url']

                # Find the showtimes ol that follows this show div
                # It's a sibling element after the show div
                showtimes_ol = show.find_next_sibling('ol', class_='showtimes')
                if not showtimes_ol:
                    # Sometimes showtimes might be in parent
                    parent = show.parent
                    if parent:
                        showtimes_ol = parent.find('ol', class_='showtimes')

                times = []
                ticket_url = THEATER_INFO['url']

                if showtimes_ol:
                    time_links = showtimes_ol.find_all('a', class_='showtime')
                    for time_link in time_links:
                        time_text = time_link.get_text(strip=True)
                        if time_text:
                            # Parse the time (format: "3:00 pm" or "6:15 pm")
                            parsed_time = parse_time(time_text)
                            if parsed_time and parsed_time not in times:
                                times.append(parsed_time)
                            # Get ticket URL from first showtime
                            if not ticket_url.startswith('https://davistheater.com/purchase'):
                                href = time_link.get('href', '')
                                if href:
                                    ticket_url = href

                if not times:
                    times = ['See website']

                # Check for series tags (for format info like "Big Screen Classics")
                format_tag = None
                series_container = show.find('div', class_='show__series')
                if series_container:
                    series_links = series_container.find_all('a')
                    for series_link in series_links:
                        series_name = series_link.get_text(strip=True).lower()
                        # Check for format indicators
                        if 'analog' in series_name or '35mm' in series_name:
                            format_tag = '35mm'
                            break

                movies.append({
                    'title': title,
                    'theater': THEATER_INFO['name'],
                    'theater_url': THEATER_INFO['url'],
                    'address': THEATER_INFO['address'],
                    'date': date_str,
                    'times': times,
                    'format': format_tag,
                    'director': None,
                    'year': None,
                    'ticket_url': ticket_url
                })

        logger.info(f"Davis Theater: Found {len(movies)} screenings")

    except Exception as e:
        logger.error(f"Failed to scrape Davis Theater: {e}")

    return movies


if __name__ == '__main__':
    results = scrape_davis()
    for m in results:
        print(f"{m['date']} - {m['title']} @ {m['times']}")
