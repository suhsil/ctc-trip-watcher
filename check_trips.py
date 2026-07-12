import json
import os
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://ctc.org.nz/triphub/web/#/public"
STATE_FILE = Path("trips_seen.json")


def get_page_lines():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)  # give the app extra time to finish rendering
        text = page.inner_text("body")
        browser.close()
    return [line.strip() for line in text.split("\n") if line.strip()]


def load_previous():
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text())
        return data.get("lines", [])
    return []


def save_current(lines):
    STATE_FILE.write_text(json.dumps({"lines": lines}, indent=2))


def send_email(new_lines):
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    body = (
        "New content was detected on the CTC Trips & Socials page:\n\n"
        + "\n".join(f"- {line}" for line in new_lines)
        + "\n\nCheck it out here: https://ctc.org.nz/trips-socials"
    )

    msg = MIMEText(body)
    msg["Subject"] = "New CTC trip may be available"
    msg["From"] = gmail_address
    msg["To"] = recipient

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [recipient], msg.as_string())


def main():
    current_lines = get_page_lines()
    previous_lines = load_previous()

    if not previous_lines:
        print("First run — saving baseline, no email sent.")
        save_current(current_lines)
        return

    previous_set = set(previous_lines)
    new_lines = [line for line in current_lines if line not in previous_set]

    if new_lines:
        print(f"Found {len(new_lines)} new line(s). Sending email.")
        send_email(new_lines)
    else:
        print("No changes detected.")

    save_current(current_lines)


if __name__ == "__main__":
    main()
