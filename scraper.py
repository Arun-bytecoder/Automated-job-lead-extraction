import asyncio
import csv
import re
from playwright.async_api import async_playwright

URL = "https://www.welcometothejungle.com/en/jobs?refinementList%5Boffices.country_code%5D%5B%5D=US"
OUTPUT_CSV = "results.csv"
CSV_HEADERS = [
    "Job_Title", "Company_Title", "Company_Slogan",
    "Job_Type", "Location", "Work_Location",
    "Industry", "Employes_Count", "Posted_Ago", "Job_Link"
]

# ── Step 6: Data Cleaning ─────────────────────────────────
def clean_posted_ago(value):
    if value.strip().lower() == "yesterday":
        return "1 days ago"
    return value.strip()

def clean_employee_count(value):
    numbers = re.findall(r"\d+", value.replace(",", ""))
    return int(numbers[0]) if numbers else ""

# ── Step 5: Extract cards from current page ───────────────
async def extract_cards(page):
    return await page.evaluate("""
    () => {
        const results = [];
        const anchors = [...document.querySelectorAll('a[href*="/companies/"][href*="/jobs/"]')];
        const seen = new Set();

        for (const anchor of anchors) {
            const href = anchor.getAttribute('href');
            if (seen.has(href)) continue;
            seen.add(href);

            anchor.scrollIntoView({ behavior: 'instant', block: 'center' });

            let card = anchor;
            for (let i = 0; i < 10; i++) {
                if (!card.parentElement) break;
                card = card.parentElement;
                if (card.tagName === 'LI') break;
            }

            const leafTexts = [];
            for (const el of card.querySelectorAll('*')) {
                if (el.children.length === 0) {
                    const t = (el.innerText || '').trim();
                    if (t && t.length < 200) leafTexts.push(t);
                }
            }

            const find = (pattern) => leafTexts.find(t => pattern.test(t)) || '';

            // Job Title
            let jobTitle = '';
            const heading = card.querySelector('h2, h3, h4');
            if (heading) {
                jobTitle = heading.innerText.trim();
            } else {
                jobTitle = (card.innerText || '').split('\\n')[0].trim();
            }

            // Company Title
            let companyTitle = '';
            const img = card.querySelector('img[alt]');
            if (img && img.getAttribute('alt')) {
                companyTitle = img.getAttribute('alt');
            }
            if (!companyTitle) {
                companyTitle = find(/^[A-Z][A-Z\s&\-\.0-9]+$/);
            }

            // Company Slogan
            const companySlogan = (() => {
                const p = card.querySelector('p');
                return p ? p.innerText.trim() : '';
            })();

            // Job Type — expanded to cover VIE, Indépendant, Apprentice etc.
            let jobType = '';
            for (const el of card.querySelectorAll('*')) {
                const t = (el.innerText || '').trim();
                if (/^(Permanent contract|Internship|Freelance|Fixed-term|Part-time|Full-time|Apprenticeship|Apprentice|VIE|V\.I\.E\.|Ind[eé]pendant|Independent|Temporary|Contractor|Analyst program|Graduate program|Work-study)$/i.test(t)) {
                    jobType = t;
                    break;
                }
            }

            // Location — skip ALL CAPS, skip periods (slogans), skip keywords
            const location = leafTexts.find((t, index) => {
                if (index < 2) return false;
                if (t === 'Business') return false;
                if (t === t.toUpperCase() && t.length > 2) return false;
                if (t.includes('.')) return false;
                if (t.includes(',') && t.length > 30) return false;
                if (/employee|ago|remote|contract|internship|freelance|salary/i.test(t)) return false;
                if (/saas|software|luxury|fintech|marketing|insurance|automotive|finance|artificial|logistics|mobile|health|security|media|retail|education|energy|biotech|consulting|environment/i.test(t)) return false;
                if (/\d+\s*(day|hour|week|month)/i.test(t)) return false;
                if (/^(yesterday|today|just now|a few days ago)$/i.test(t)) return false;
                if (t.length > 50 || t.length < 2) return false;
                if (/^[A-Z]/.test(t)) return true;
                return false;
            }) || '';

            // Work Location
            const workLocation = find(/^(No remote work|Fully-remote|Full remote|Partial remote|Hybrid|A few days at home|Remote friendly|No remote|Remote)$/i);

            // Industry
            const industry = find(/saas|software|luxury|fintech|marketing|media|retail|education|health|security|mobile|logistics|insurance|automotive|finance|artificial intelligence|machine learning|environment|energy|biotech|pharma|hardware|gaming|legal|real estate|food|travel|recruitment|consulting|construction|agriculture|e-commerce|cloud|it \/ digital|digital|big data|cybersecurity|cleantech|mobility/i);

            // Employee Count
            const empRaw = find(/^\d[\d,]*\s*employees$/i);

            // Posted Ago
            const postedAgo = find(/^(yesterday|today|just now|A few days ago|a few days ago|\d+\s*(day|hour|week|month)s?\s*ago)$/i);

            results.push({
                Job_Title:      jobTitle,
                Company_Title:  companyTitle,
                Company_Slogan: companySlogan,
                Job_Type:       jobType,
                Location:       location,
                Work_Location:  workLocation,
                Industry:       industry,
                Employes_Count: empRaw,
                Posted_Ago:     postedAgo,
                Job_Link:       'https://www.welcometothejungle.com' + href
            });
        }
        return results;
    }
    """)

async def main():
    all_records = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()

        # Step 1: Navigate
        await page.goto(URL)
        await page.wait_for_timeout(3000)

        # Step 2: Close popup
        backdrop = page.locator("[data-backdrop][data-open='true']")
        if await backdrop.count() > 0:
            await backdrop.click(force=True)
            await page.wait_for_timeout(1000)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)

        # Step 3: Click search bar
        search_bar = page.locator("[data-testid='jobs-home-search-field-query']")
        await search_bar.click(force=True)
        await page.wait_for_timeout(1000)

        # Step 4: Type Business and press Enter
        await search_bar.type("Business")
        await page.wait_for_timeout(500)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)

        # Step 5: Loop through all pages
        page_num = 1
        while True:
            print(f"Extracting page {page_num}...")

            for pct in range(0, 110, 10):
                await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct/100})")
                await page.wait_for_timeout(200)
            await page.wait_for_timeout(500)

            cards = await extract_cards(page)
            print(f"  -> {len(cards)} cards found")

            # Step 6: Clean and collect
            for card in cards:
                card["Posted_Ago"]     = clean_posted_ago(card["Posted_Ago"])
                card["Employes_Count"] = clean_employee_count(card["Employes_Count"])
                all_records.append(card)

            next_btn = page.get_by_role("link", name=str(page_num + 1), exact=True).first
            if await next_btn.count() == 0:
                print("No more pages.")
                break
            await next_btn.click()
            await page.wait_for_timeout(3000)
            page_num += 1

        await browser.close()

    # Step 7: Save CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\nDone! {len(all_records)} records saved to {OUTPUT_CSV}")

    # Step 8: Print contest answers
    def emp_int(r):
        try: return int(r["Employes_Count"])
        except: return None

    total = len(all_records)
    print("\n" + "="*50)
    print("  CONTEST ANSWERS")
    print("="*50)
    print(f"(a) Total jobs                    : {total}")
    print(f"(b) Jobs in New York              : {sum(1 for r in all_records if 'new york' in (r['Location'] or '').lower())}")
    print(f"(c) Companies > 200 employees     : {sum(1 for r in all_records if (emp_int(r) or 0) > 200)}")
    print(f"(d) Companies < 200 employees     : {sum(1 for r in all_records if emp_int(r) is not None and emp_int(r) < 200)}")
    print(f"(e) Permanent contract jobs       : {sum(1 for r in all_records if 'permanent' in (r['Job_Type'] or '').lower())}")
    print(f"(f) Internship jobs               : {sum(1 for r in all_records if 'internship' in (r['Job_Type'] or '').lower())}")
    print("="*50)

asyncio.run(main())