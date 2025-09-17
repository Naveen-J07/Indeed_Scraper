import requests
from bs4 import BeautifulSoup
import pandas as pd
import time, random, urllib.parse, os
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS

BASE_URL = "https://www.indeed.com/jobs"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}

# Ensure static folder exists
if not os.path.exists("static"):
    os.makedirs("static")

# ------------------ SCRAPER ------------------
def scrape_jobs(keyword, location, pages=2):
    """Scrape jobs from Indeed. Fallback to sample dataset if blocked."""
    all_jobs = []
    for i in range(pages):
        params = {"q": keyword, "l": location, "start": i * 10}
        r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)

        # Handle blocked/empty responses
        if r.status_code == 403 or "job_seen_beacon" not in r.text:
            print("⚠️ Blocked by Indeed or no results. Loading sample dataset.")
            return pd.read_csv("sample_jobs.csv", quotechar='"', on_bad_lines="skip")

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("div.job_seen_beacon")
        if not cards:
            print("⚠️ No job cards found. Using sample dataset.")
            return pd.read_csv("sample_jobs.csv", quotechar='"', on_bad_lines="skip")

        for card in cards:
            title_tag = card.select_one("h2.jobTitle") or card.select_one("a.jobtitle")
            company_tag = card.select_one(".companyName") or card.select_one(".company")
            loc_tag = card.select_one(".companyLocation")
            date_tag = card.select_one(".date")
            desc_tag = card.select_one(".job-snippet") or card.select_one(".summary")
            a_tag = card.select_one("a")

            all_jobs.append([
                title_tag.get_text(strip=True) if title_tag else None,
                company_tag.get_text(strip=True) if company_tag else None,
                loc_tag.get_text(strip=True) if loc_tag else None,
                date_tag.get_text(strip=True) if date_tag else None,
                desc_tag.get_text(" ", strip=True) if desc_tag else "",
                urllib.parse.urljoin(BASE_URL, a_tag["href"]) if a_tag and a_tag.get("href") else None
            ])

        time.sleep(random.uniform(2, 4))  # polite delay

    df = pd.DataFrame(all_jobs, columns=["Title", "Company", "Location", "Date", "Description", "URL"])
    df.dropna(subset=["Title", "Company"], inplace=True)

    if df.empty:
        print("⚠️ Scraper returned empty. Using sample dataset.")
        return pd.read_csv("sample_jobs.csv", quotechar='"', on_bad_lines="skip")

    print(f"✅ Scraped {len(df)} jobs.")
    return df

# ------------------ ANALYTICS ------------------
def generate_charts(df):
    """Generate charts & wordcloud safely."""
    if df.empty:
        print("⚠️ No jobs found. Skipping chart generation.")
        return

    # Top Companies
    if "Company" in df.columns and not df["Company"].dropna().empty:
        top = df["Company"].value_counts().nlargest(5)
        if not top.empty:
            ax = top.plot.bar(figsize=(6, 4), color="skyblue", edgecolor="black")
            ax.set_title("Top Hiring Companies")
            ax.set_ylabel("Job Count")
            plt.tight_layout()
            plt.savefig(os.path.join("static", "top_companies.png"))
            plt.close()

    # Jobs by Location
    if "Location" in df.columns and not df["Location"].dropna().empty:
        locs = df["Location"].value_counts().nlargest(5)
        if not locs.empty:
            ax = locs.plot.bar(figsize=(6, 4), color="lightgreen", edgecolor="black")
            ax.set_title("Jobs by Location")
            ax.set_ylabel("Job Count")
            plt.tight_layout()
            plt.savefig(os.path.join("static", "jobs_by_location.png"))
            plt.close()

    # Word Cloud
    if "Description" in df.columns and not df["Description"].dropna().empty:
        text = " ".join(df["Description"].dropna())
        if text.strip():
            wc = WordCloud(
                width=800, height=400,
                stopwords=STOPWORDS,
                background_color="white",
                colormap="viridis"
            ).generate(text)
            wc.to_file(os.path.join("static", "wordcloud.png"))
