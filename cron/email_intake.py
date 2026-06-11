#!/usr/bin/env python3
"""Email intake handler for Archilles Job Pipeline.
Checks Gmail inbox for forwarded job alerts from Arinze.
Runs via cron every 30 minutes.
"""
import imaplib
import email as em
from email.header import decode_header
import json
import os
import re
from datetime import datetime, timezone, timedelta

INTAKE_DIR = "/home/hermes/haxjobs/intake"
STATE_DIR = "/home/hermes/haxjobs/state"
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
EMAIL_ADDRESS = "archilleshaxsys@gmail.com"
ALLOWED_SENDERS = ["elenasuluarinze@gmail.com", "pentacker@gmail.com"]


def get_password():
    """Read EMAIL_PASSWORD from Hermes .env file."""
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("EMAIL_PASSWORD="):
                    pw = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return pw.replace(" ", "")  # Gmail app passwords: no spaces
    return None


def decode_str(s):
    if s is None:
        return ""
    parts = decode_header(s)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(str(part))
    return " ".join(result)


def extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode("utf-8", errors="replace")
    return ""


def is_job_related(subject, body):
    text = (subject + " " + body).lower()
    signals = [
        "job", "position", "role", "hiring", "vacancy", "opening",
        "backend engineer", "python developer", "software engineer",
        "apply", "requirements", "responsibilities",
        "salary", "full-time", "remote", "hybrid", "london",
        "fastapi", "postgresql", "docker", "kubernetes",
        "linkedin.com/jobs", "reed.co.uk", "greenhouse.io",
        "lever.co", "indeed.com", "workday",
    ]
    return any(s in text for s in signals)


def extract_company(subject, body):
    patterns = [
        r"(?:at|with|@)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s*[-–]\s*|\s*$|\s*\()",
        r"([A-Z][A-Za-z0-9]+)\s+(?:is hiring|are hiring)",
    ]
    for p in patterns:
        m = re.search(p, subject + " " + body[:500])
        if m:
            return m.group(1).strip()
    return "Unknown"


def already_queued(title, company):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    if not os.path.isdir(INTAKE_DIR):
        return False
    for fname in os.listdir(INTAKE_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(INTAKE_DIR, fname)) as f:
                data = json.load(f)
            if data.get("title") == title and data.get("company") == company:
                if data.get("received_at", "") > cutoff.isoformat():
                    return True
        except Exception:
            continue
    return False


def main():
    password = get_password()
    if not password:
        print("No EMAIL_PASSWORD found")
        return

    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(EMAIL_ADDRESS, password)
    mail.select("inbox")

    since = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
    queued = 0

    for sender in ALLOWED_SENDERS:
        status, messages = mail.search(None, f'(UNSEEN FROM "{sender}" SINCE "{since}")')
        if status != "OK":
            continue
        for num in messages[0].split():
            status, data = mail.fetch(num, "(RFC822)")
            if status != "OK":
                continue
            msg = em.message_from_bytes(data[0][1])
            subject = decode_str(msg["Subject"])
            body = extract_body(msg)

            if not is_job_related(subject, body):
                continue

            company = extract_company(subject, body)
            title = subject.strip()[:100]

            if already_queued(title, company):
                print(f"Skipping dup: {title} at {company}")
                continue

            ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            fname = f"{ts}_{company.replace(' ', '_')}_{title.replace(' ', '_')[:50]}.json"
            intake = {
                "received_at": datetime.now(timezone.utc).isoformat(),
                "source": "email",
                "source_url": "",
                "company": company,
                "title": title,
                "jd_text": body,
                "status": "pending",
            }
            os.makedirs(INTAKE_DIR, exist_ok=True)
            with open(os.path.join(INTAKE_DIR, fname), "w") as f:
                json.dump(intake, f, indent=2)
            print(f"Queued: {title} at {company} -> {fname}")
            queued += 1

    mail.logout()

    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "email_intake.log"), "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {queued} new job(s)\n")

    print(f"Done. {queued} job(s) queued.")


if __name__ == "__main__":
    main()
