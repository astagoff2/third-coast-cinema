"""Scraper for Logan Theatre using BigScreen.com as data source."""
from bs4 import BeautifulSoup
from .utils import parse_time, logger
import requests
import re
from datetime import datetime, timedelta


THEATER_INFO = {
    'name': 'Logan Theatre',
    'url': 'https://www.thelogantheatre.com',
    'address': '2646 N Milwaukee Ave'
}

BIGSCREEN_URL = 'https://www.bigscreen.com/Marquee.php?theater=932&view=sched'


def scrape_logan():
    """Scrape Logan Theatre schedule from BigScreen.com."""
    movies = []

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        # Scrape today and next 6 days
        for day_offset in range(7):
            date = datetime.now() + timedelta(days=day_offset)
            date_str = date.strftime('%Y-%m-%d')

            url = f'{BIGSCREEN_URL}&showdate={date_str}'
            resp = requests.get(url, headers=headers, timeout=30)

            if resp.status_code != 200:
                logger.error(f"Logan Theatre: Got status code {resp.status_code} for {date_str}")
                continue

            soup = BeautifulSoup(resp.text, 'lxml')

            # Find all rows with movie data (graybar_0 or graybar_1)
            rows = soup.find_all('tr', class_=re.compile(r'graybar_'))

            for row in rows:
                # Get title from movieNameList link
                title_elem = row.find('a', class_='movieNameList')
                if not title_elem:
                    continue

                title = title_elem.get_text().strip()
                if not title:
                    continue

                # Get showtimes from col_showtimes
                showtime_td = row.find('td', class_='col_showtimes')
                if not showtime_td:
                    continue

                # Extract times (format: "4:30, 6:45, 9:00")
                showtime_text = showtime_td.get_text()
                # Get just the times part (before any <br> or showcomment)
                times_part = showtime_text.split('\n')[0].strip()

                times = []
                for time_match in re.findall(r'(\d{1,2}:\d{2})', times_part):
                    # Convert to 12-hour format with AM/PM
                    hour, minute = map(int, time_match.split(':'))
                    if hour < 12:
                        # Morning shows before noon (rare)
                        if hour == 0:
                            time_str = f"12:{minute:02d} AM"
                        else:
                            time_str = f"{hour}:{minute:02d} AM"
                    elif hour == 12:
                        time_str = f"12:{minute:02d} PM"
                    else:
                        time_str = f"{hour}:{minute:02d} PM"

                    # BigScreen uses 24h times implicitly based on typical movie schedules
                    # Most showtimes are PM (afternoon/evening)
                    # Re-parse: assume times like 4:30, 6:45 are PM
                    if hour < 10:
                        # 4:30 means 4:30 PM
                        time_str = f"{hour}:{minute:02d} PM"
                    elif hour >= 10 and hour <= 11:
                        # 10:00, 11:00 - late night, could be AM (midnight show) or PM
                        # Check context - if it's the only time or very late, it's PM
                        time_str = f"{hour}:{minute:02d} PM"

                    if time_str not in times:
                        times.append(time_str)

                if not times:
                    continue

                # Check if already have this movie for this date
                existing = next(
                    (m for m in movies if m['title'] == title and m['date'] == date_str),
                    None
                )
                if existing:
                    # Add any new times
                    for t in times:
                        if t not in existing['times']:
                            existing['times'].append(t)
                    continue

                movies.append({
                    'title': title,
                    'theater': THEATER_INFO['name'],
                    'theater_url': THEATER_INFO['url'],
                    'address': THEATER_INFO['address'],
                    'date': date_str,
                    'times': times,
                    'format': None,
                    'director': None,
                    'year': None,
                    'ticket_url': f"{THEATER_INFO['url']}/?p=showtimes"
                })

        logger.info(f"Logan Theatre: Found {len(movies)} screenings")

    except Exception as e:
        logger.error(f"Failed to scrape Logan Theatre: {e}")

    return movies


if __name__ == '__main__':
    results = scrape_logan()
    for m in results:
        print(f"{m['date']} - {m['title']} @ {m['times']}")
