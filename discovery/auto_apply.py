#!/usr/bin/env python3
"""HaxJobs Auto-Apply Module — Playwright-based form filler for ATS platforms.
Uses site_knowledge.json for selectors. NEVER submits without explicit approval.
Supports: Lever, Greenhouse, Ashby, Workable, SmartRecruiters.
"""
import asyncio, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

HAXJOBS_DIR = "/home/hermes/haxjobs"
KNOWLEDGE_FILE = os.path.join(HAXJOBS_DIR, "discovery", "site_knowledge.json")

# Load site knowledge
with open(KNOWLEDGE_FILE) as f:
    SITES = json.load(f)


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}")


def detect_platform(url):
    """Detect which ATS platform a URL belongs to."""
    url_lower = url.lower()
    for key, cfg in SITES.items():
        if key.startswith("_"):
            continue
        for pattern in cfg.get("url_patterns", []):
            if pattern in url_lower:
                return key, cfg
    return None, None


async def fill_lever(page, cfg, profile, cv_path):
    """Fill a Lever application form."""
    sel = cfg["form_selectors"]
    log("Filling Lever form...")

    async def try_fill(selector, value):
        if not value:
            return False
        try:
            el = await page.query_selector(selector)
            if not el:
                return False
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                await el.select_option(label=value) if value else None
            else:
                await el.fill(value)
            return True
        except:
            return False

    # Basic fields
    await try_fill(sel["full_name"], profile.get("name", ""))
    await try_fill(sel["email"], profile.get("email", ""))
    await try_fill(sel["phone"], profile.get("phone", ""))
    await try_fill(sel["location"], profile.get("location", ""))
    await try_fill(sel["linkedin"], profile.get("linkedin_url", ""))
    await try_fill(sel["github"], profile.get("github_url", ""))
    await try_fill(sel["portfolio"], "")  # No portfolio URL in profile
    await try_fill(sel["current_company"], "")  # Leave blank for now

    # Upload CV
    if cv_path and os.path.exists(cv_path):
        try:
            file_input = await page.query_selector(sel["resume_upload"])
            if file_input:
                await file_input.set_input_files(cv_path)
                log(f"  CV uploaded: {cv_path}")
        except Exception as e:
            log(f"  CV upload failed: {e}")

    # Fill cover letter if textarea exists
    await try_fill(sel["cover_letter"], "I've attached my CV for your review. Happy to discuss how my backend engineering experience with FastAPI, PostgreSQL, and production systems can contribute to the team.")

    # Check for unanswered fields
    custom_questions = await page.query_selector_all(
        "input:not([type='file']):not([type='submit']):not([type='hidden']), textarea, select"
    )
    unanswered = []
    for q in custom_questions:
        try:
            name = await q.get_attribute("name") or ""
            tag = await q.evaluate("el => el.tagName.toLowerCase()")
            value = await q.input_value() if tag != "select" else ""
            if not value and tag not in ("hidden", "radio", "checkbox"):
                label = await q.get_attribute("placeholder") or name
                unanswered.append(f"  - {label}")
        except:
            pass

    if unanswered:
        log("Fields still needing review:")
        for u in unanswered[:8]:
            log(u)
    else:
        log("All fields filled. Ready for submit — awaiting Arinze approval.")

    return len(unanswered) == 0


async def fill_greenhouse(page, cfg, profile, cv_path):
    """Fill a Greenhouse application form (multi-page)."""
    sel = cfg["form_selectors"]
    log("Filling Greenhouse form...")

    # Page 1: Personal Info
    try: await page.fill(sel["full_name"].split(", ")[0], profile.get("name", "").split()[0])
    except: pass
    try: await page.fill(sel["full_name"].split(", ")[1], profile.get("name", "").split()[-1])
    except: pass
    try: await page.fill(sel["email"], profile.get("email", ""))
    except: pass
    try: await page.fill(sel["phone"], profile.get("phone", ""))
    except: pass
    try: await page.fill(sel["location"], profile.get("location", ""))
    except: pass

    # Click next if multi-page
    next_btn = await page.query_selector("button:has-text('Next'), button:has-text('Continue')")
    if next_btn:
        await next_btn.click()
        await page.wait_for_timeout(2000)

    # Page 2: Resume + Links
    if cv_path and os.path.exists(cv_path):
        try:
            file_input = await page.query_selector(sel["resume_upload"])
            if file_input:
                await file_input.set_input_files(cv_path)
                log(f"  CV uploaded: {cv_path}")
        except Exception as e:
            log(f"  CV upload failed: {e}")

    try: await page.fill(sel["linkedin"], profile.get("linkedin_url", ""))
    except: pass
    try: await page.fill(sel["github"], profile.get("github_url", ""))
    except: pass

    # Click next again
    next_btn = await page.query_selector("button:has-text('Next'), button:has-text('Continue')")
    if next_btn:
        await next_btn.click()
        await page.wait_for_timeout(2000)

    # Page 3+: Custom questions — STOP HERE, never auto-fill
    log("Stopped at custom questions/screening page. Needs Arinze review.")
    return False


async def fill_generic(page, cfg, profile, cv_path):
    """Generic form filler for Ashby, Workable, SmartRecruiters."""
    sel = cfg["form_selectors"]
    log(f"Filling generic form...")

    # Try each known field
    field_map = {
        "full_name": profile.get("name", ""),
        "email": profile.get("email", ""),
        "phone": profile.get("phone", ""),
        "location": profile.get("location", ""),
        "linkedin": profile.get("linkedin_url", ""),
        "github": profile.get("github_url", ""),
    }

    for key, selector in sel.items():
        if key in ("resume_upload", "cover_letter", "submit"):
            continue
        try:
            if key in field_map:
                await page.fill(selector, field_map[key])
        except:
            pass

    # Upload CV
    if cv_path and os.path.exists(cv_path):
        try:
            file_input = await page.query_selector(sel["resume_upload"])
            if file_input:
                await file_input.set_input_files(cv_path)
                log(f"  CV uploaded")
        except:
            log("  CV upload failed")

    return True


async def apply(job_url, profile_path, cv_path):
    """Main entry point. Fills form, stops before submit. Never auto-submits."""
    log(f"Auto-apply: {job_url}")

    platform, cfg = detect_platform(job_url)
    if not platform:
        log(f"Unknown platform for URL: {job_url}")
        log(f"Known platforms: {list(SITES.keys())}")
        return False

    log(f"Detected platform: {cfg['name']} (confidence: {cfg['confidence']})")

    # Load profile
    with open(profile_path) as f:
        profile = json.load(f).get("user_profile", {})

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # Click "Apply" button if on job description page
        apply_btn = await page.query_selector("a:has-text('Apply'), button:has-text('Apply')")
        if apply_btn:
            await apply_btn.click()
            await page.wait_for_timeout(2000)

        # Route to platform-specific filler
        if platform == "lever":
            success = await fill_lever(page, cfg, profile, cv_path)
        elif platform == "greenhouse":
            success = await fill_greenhouse(page, cfg, profile, cv_path)
        else:
            success = await fill_generic(page, cfg, profile, cv_path)

        # Take screenshot for Arinze to review
        screenshot = f"/tmp/haxjobs_apply_{platform}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        await page.screenshot(path=screenshot, full_page=True)
        log(f"Screenshot saved: {screenshot}")

        # NEVER submit — always stop here
        log("Form filled. STOPPED before submit — requires Arinze approval.")
        log(f"Review screenshot: {screenshot}")

        await browser.close()
    return success


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: auto_apply.py <job_url> <profile_path> [cv_path]")
        print("Example: auto_apply.py https://jobs.lever.co/spotify/abc123 /home/hermes/haxjobs/profile/arinze_profile.local.json /path/to/cv.pdf")
        sys.exit(1)

    job_url = sys.argv[1]
    profile_path = sys.argv[2]
    cv_path = sys.argv[3] if len(sys.argv) > 3 else None

    asyncio.run(apply(job_url, profile_path, cv_path))
