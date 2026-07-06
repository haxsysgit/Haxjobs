"""Profile business logic."""
import json
from haxjobs.config import PROFILE_PATH


def get_profile():
    if not PROFILE_PATH.exists():
        return {"name": "", "profile": None}
    try:
        with open(PROFILE_PATH) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"name": "", "profile": None}
    personal = data.get("personal", {})
    name = personal.get("name", "")
    return {"name": name, "profile": data}
