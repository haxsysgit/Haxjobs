#!/usr/bin/env python3
"""Send well-designed HTML fit report emails from Archilles pipeline."""
import smtplib, os, json, sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
FROM = "archilleshaxsys@gmail.com"
TO = "elenasuludavid@gmail.com"


def get_password():
    env = os.path.expanduser("~/.hermes/.env")
    if not os.path.exists(env):
        return None
    with open(env) as f:
        for line in f:
            line = line.strip()
            if 'EMAIL_PASSWORD' in line and '=' in line and not line.strip().startswith('#'):
                pw = line.split('=', 1)[1].strip().strip('"').strip("'")
                return pw.replace(' ', '').replace('***', '').strip()
    return None


def html_body(company, title, score, url, summary, matches, gaps, risk, pack_dir):
    rc = {"low": "#166534", "medium": "#92400e", "high": "#991b1b"}.get(risk, "#64748b")
    rb = {"low": "#dcfce7", "medium": "#fef3c7", "high": "#fee2e2"}.get(risk, "#f1f5f9")
    ml = "".join(f'<li style="margin-bottom:6px">{m}</li>' for m in matches)
    gl = "".join(f'<li style="margin-bottom:6px">{g}</li>' for g in gaps) if gaps else '<li>None identified</li>'
    ab = f'<a href="{url}" style="display:inline-block;padding:10px 20px;background:#2563eb;color:white;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px">View Job &amp; Apply</a>' if url else ''
    ts = datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f7f3ea;font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:600px;margin:30px auto;background:#fffaf0;border:1px solid #cbd5e1;border-radius:12px;overflow:hidden">

<div style="background:linear-gradient(135deg,#0f172a 0%,#2563eb 100%);padding:28px 24px;color:white">
<h1 style="margin:0;font-size:20px;font-weight:700;letter-spacing:-0.3px">Job Fit: {score}% — {title}</h1>
<p style="margin:8px 0 0;font-size:14px;opacity:0.9">{company}</p>
</div>

<div style="padding:24px;text-align:center;border-bottom:1px solid #d9d6cc">
<div style="font-size:48px;font-weight:800;color:#0f172a;font-family:monospace;line-height:1">{score}%</div>
<div style="font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-top:4px">Fit Score</div>
<div style="display:inline-block;margin-top:12px;padding:4px 14px;border-radius:999px;font-size:12px;font-weight:600;background:{rb};color:{rc}">{risk.upper()} sponsorship risk</div>
</div>

<div style="padding:20px 24px;border-bottom:1px solid #d9d6cc">
<h2 style="margin:0 0 8px;font-size:14px;color:#0f172a;text-transform:uppercase;letter-spacing:0.5px">Summary</h2>
<p style="margin:0;font-size:14px;line-height:1.6;color:#334155">{summary}</p>
</div>

<div style="padding:20px 24px">
<table width="100%" cellpadding="0" cellspacing="0"><tr>
<td width="50%" valign="top" style="padding-right:10px">
<h2 style="margin:0 0 8px;font-size:13px;color:#166534;text-transform:uppercase;letter-spacing:0.5px">Strongest Matches</h2>
<ul style="margin:0;padding-left:18px;font-size:13px;color:#334155;line-height:1.5">{ml}</ul>
</td>
<td width="50%" valign="top" style="padding-left:10px">
<h2 style="margin:0 0 8px;font-size:13px;color:#92400e;text-transform:uppercase;letter-spacing:0.5px">Major Gaps</h2>
<ul style="margin:0;padding-left:18px;font-size:13px;color:#334155;line-height:1.5">{gl}</ul>
</td>
</tr></table>
</div>

<div style="padding:16px 24px;background:#f8fafd;border-top:1px solid #d9d6cc;text-align:center">
{ab}
<p style="margin:12px 0 0;font-size:12px;color:#64748b">Pack: {pack_dir}<br>Sent by Archilles · {ts}</p>
</div>

</div></body></html>"""


def send(subject, body, attachments=None):
    pw = get_password()
    if not pw:
        print("ERROR: no EMAIL_PASSWORD")
        return False
    msg = MIMEMultipart()
    msg["From"] = FROM
    msg["To"] = TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))
    if attachments:
        for fp in attachments:
            if os.path.isfile(fp):
                with open(fp, "rb") as f:
                    p = MIMEBase("application", "octet-stream")
                    p.set_payload(f.read())
                    encoders.encode_base64(p)
                    p.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(fp)}"')
                    msg.attach(p)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(FROM, pw)
            s.send_message(msg)
        print(f"Sent: {subject}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 9:
        print("Usage: send_email.py COMPANY TITLE SCORE URL SUMMARY MATCHES_GAPS_RISK PACK_DIR [ATTACH...]")
        print("MATCHES and GAPS are JSON arrays. Example:")
        print('  send_email.py Spotify "Backend Engineer" 85 "https://..." "summary here" \'["match1"]\' \'["gap1"]\' low /path/to/pack /path/to/cv.pdf')
        sys.exit(1)

    company, title, score, url, summary = sys.argv[1:6]
    matches = json.loads(sys.argv[6])
    gaps = json.loads(sys.argv[7])
    risk = sys.argv[8]
    pack_dir = sys.argv[9]
    attachments = sys.argv[10:] if len(sys.argv) > 10 else []

    body = html_body(company, title, score, url, summary, matches, gaps, risk, pack_dir)
    subj = f"Job Fit: {score}% - {title} at {company}"
    send(subj, body, attachments)
