"""Scraper for Logan Theatre using Playwright with stealth."""
from bs4 import BeautifulSoup
from .utils import parse_time, logger
import re
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


THEATER_INFO = {
    'name': 'Logan Theatre',
    'url': 'https://www.thelogantheatre.com',
    'address': '2646 N Milwaukee Ave'
}


def scrape_logan():
    """Scrape Logan Theatre schedule using Playwright with stealth settings."""
    movies = []
    base_url = 'https://www.thelogantheatre.com'

    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright not available for Logan Theatre")
        return movies

    try:
        with sync_playwright() as p:
            # Launch with more stealth-like settings
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )

            # Create context with realistic browser fingerprint
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/Chicago'
            )

            page = context.new_page()

            # Navigate to the page
            page.goto(f'{base_url}/?p=showtimes', timeout=60000, wait_until='networkidle')

            # Additional wait for dynamic content
            page.wait_for_timeout(3000)

            # Try to find moviepad, if not found wait more
            moviepad_count = page.locator('.moviepad').count()
            if moviepad_count == 0:
                logger.warning("Logan Theatre: No moviepad found initially, waiting longer...")
                page.wait_for_timeout(5000)
                moviepad_count = page.locator('.moviepad').count()

            logger.info(f"Logan Theatre: Found {moviepad_count} moviepad elements via Playwright")

            html = page.content()
            context.close()
            browser.close()

        soup = BeautifulSoup(html, 'lxml')
        today = datetime.now().strftime('%Y-%m-%d')

        # Find moviepad elements
        movie_pads = soup.find_all(class_='moviepad')

        for pad in movie_pads:
            # Title is in the img tag's title attribute
            img = pad.find('img')
            if not img:
                continue

            title = img.get('title', '').strip()
            if not title:
                title = img.get('alt', '').strip()
            if not title:
                continue

            # Find showtimes
            showtime_links = pad.find_all('a', href=True)
            times = []
            for link in showtime_links:
                link_text = link.get_text().strip()
                # Match time patterns like "1:00p" or "7:30p"
                if re.match(r'\d{1,2}:\d{2}[ap]', link_text, re.I):
                    time_normalized = parse_time(link_text + 'm')
                    if time_normalized and time_normalized not in times:
                        times.append(time_normalized)

            if not times:
                continue

            # Get ticket URL
            ticket_link = pad.find('a', href=re.compile(r'formovietickets|ticket'))
            ticket_url = ticket_link['href'] if ticket_link else f'{base_url}/?p=showtimes'

            movies.append({
                'title': title,
                'theater': THEATER_INFO['name'],
                'theater_url': THEATER_INFO['url'],
                'address': THEATER_INFO['address'],
                'date': today,
                'times': times,
                'format': None,
                'director': None,
                'year': None,
                'ticket_url': ticket_url
            })

        logger.info(f"Logan Theatre: Found {len(movies)} screenings")

    except Exception as e:
        logger.error(f"Failed to scrape Logan Theatre: {e}")

    return movies


if __name__ == '__main__':
    results = scrape_logan()
    for m in results:
        print(f"{m['date']} - {m['title']} @ {m['times']}")
