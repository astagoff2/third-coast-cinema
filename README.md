# Chicago Art House Cinema

A minimal, elegant website showing weekly movie schedules from Chicago's independent and repertory theaters.

**Live site:** https://astagoff2.github.io/chicago-arthouse-movies/

## Theaters

- Gene Siskel Film Center
- Doc Films (University of Chicago)
- Music Box Theatre
- Logan Theatre
- Facets Cinematheque

## How It Works

Python scrapers fetch showtimes from each theater's website, combine them into a unified JSON file, and generate a static HTML page organized by date.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the build
python build.py

# View the site
open site/index.html
```

## Automated Updates

To enable daily automatic updates, create `.github/workflows/deploy.yml` with the contents from `workflow-template.yml`. The site will rebuild daily at 6am Chicago time.

## Tech Stack

- Python 3 + BeautifulSoup for scraping
- Jinja2 for templating
- Vanilla HTML/CSS (no frameworks)
- GitHub Pages for hosting
