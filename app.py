from flask import Flask, render_template, request, send_file
from scraper import scrape_jobs, generate_charts
import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        keyword = request.form.get("keyword").lower()
        location = request.form.get("location").lower()

        df = scrape_jobs(keyword, location, pages=2)

        if not df.empty:
            df = df[
                df["Title"].str.lower().str.contains(keyword, na=False) &
                df["Location"].str.lower().str.contains(location, na=False)
            ]

        if df.empty:
            return render_template(
                "results.html",
                jobs=[],
                keyword=keyword,
                location=location,
                no_results=True,
                top_companies_exists=False,
                jobs_by_location_exists=False,
                wordcloud_exists=False
            )

        df.to_csv("jobs.csv", index=False)

        generate_charts(df)

        jobs = df.to_dict(orient="records")

        context = {
            "jobs": jobs,
            "keyword": keyword,
            "location": location,
            "no_results": False,
            "top_companies_exists": os.path.exists("static/top_companies.png"),
            "jobs_by_location_exists": os.path.exists("static/jobs_by_location.png"),
            "wordcloud_exists": os.path.exists("static/wordcloud.png"),
        }
        return render_template("results.html", **context)

    return render_template("index.html")

# ------------------- DOWNLOAD ROUTES -------------------

@app.route("/download_csv")
def download_csv():
    if os.path.exists("jobs.csv"):
        return send_file("jobs.csv", as_attachment=True)
    return "⚠️ No jobs file found!"

@app.route("/download_pdf")
def download_pdf():
    if not os.path.exists("jobs.csv"):
        return "⚠️ No jobs file found!"

    file_path = "jobs.pdf"
    df = pd.read_csv("jobs.csv")

    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 50, "Job Listings Report")

    # Job Data
    c.setFont("Helvetica", 10)
    y = height - 80
    for _, row in df.iterrows():
        text = f"{row['Title']} | {row['Company']} | {row['Location']} | {row['Date']}"
        c.drawString(50, y, text)
        y -= 15
        if y < 50:  # Start new page if space runs out
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 50
    c.save()
    return send_file(file_path, as_attachment=True)

# ------------------- RUN -------------------
if __name__ == "__main__":
    app.run(debug=True)
