# WTTJ Job Lead Scraper

Automated job lead extraction from [Welcome to the Jungle](https://www.welcometothejungle.com) platform.

---

## Problem Statement

Manually browsing job listings to collect lead data is slow and unscalable. This project automates the full extraction pipeline — navigating the site, handling popups, searching, scrolling through all pages, and saving clean structured data to CSV.

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Core language |
| Playwright | Browser automation (handles React/JS pages) |
| asyncio | Async execution required by Playwright |
| csv | Built-in CSV writer for output |
| re | Regex for data cleaning |

---

## Project Structure

```
wttj_scraper/
├── wttj_scraper.py     # Main scraper script
├── results.csv         # Output file (auto-generated)
└── README.md         
```

---

## Setup

```bash
# Install dependencies
pip install playwright
playwright install chromium
```

---

## Usage

```bash
python wttj_scraper.py
```

The browser will open automatically. The script will:
1. Navigate to WTTJ with US filter
2. Close the regional redirect popup
3. Search for "Business"
4. Scrape all pages (8 pages, ~239 records)
5. Save results to `results.csv`
6. Print contest answers to terminal

---

## Output — CSV Schema

| Column | Description | Example |
|--------|-------------|---------|
| Job_Title | Full job title | Business Development Representative |
| Company_Title | Company name | Brevo |
| Company_Slogan | Company tagline | CRM for global organizations |
| Job_Type | Contract type | Permanent contract |
| Location | City | New York |
| Work_Location | Remote policy | No remote work |
| Industry | Sector | SaaS / Cloud Services |
| Employes_Count | Employee count (integer) | 950 |
| Posted_Ago | Days since posted | 5 days ago |
| Job_Link | Full URL to job | https://www.welcometothejungle.com/... |

---

## Data Cleaning Rules

- `yesterday` → `1 days ago`
- `120 employees` → `120` (integer)
- All other fields stored as-is from the website

---

## Notes

- Some cards (MSX International, Credit Agricole) do not display Work_Location or Posted_Ago on WTTJ — these fields are blank on the website itself, not a scraper bug
- CSV saved with `utf-8-sig` encoding for correct Excel rendering
