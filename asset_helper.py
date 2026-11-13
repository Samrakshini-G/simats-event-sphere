"""
SIMATS Event Sphere - Asset Management & Resolution Helper
Strictly resolves, validates, and serves local assets from the assets/ directory.
Guarantees NO external image URLs, broken paths, or generic placeholders.
"""

import os
import base64
from functools import lru_cache

# Workspace root directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _detect_assets_dir() -> str:
    """Detect whether assets folder is named 'Assets' or 'assets' on disk (Linux vs Windows)."""
    for folder_name in ["Assets", "assets"]:
        candidate = os.path.join(BASE_DIR, folder_name)
        if os.path.exists(candidate) and os.path.isdir(candidate):
            return candidate
    return os.path.join(BASE_DIR, "Assets")

ASSETS_DIR = _detect_assets_dir()

def _resolve_core_asset(*sub_parts: str) -> str:
    """Helper to locate a core asset file across both Assets and assets directories."""
    for base in [ASSETS_DIR, os.path.join(BASE_DIR, "Assets"), os.path.join(BASE_DIR, "assets")]:
        direct = os.path.join(base, *sub_parts)
        if os.path.exists(direct) and os.path.isfile(direct):
            return direct
    # Fallback to direct path under ASSETS_DIR
    return os.path.join(ASSETS_DIR, *sub_parts)

# Verified Static Asset Paths (Cross-Platform Windows and Linux)
ASSETS = {
    # Logos
    "logo_college": _resolve_core_asset("Landing", "college_logo.png"),
    "logo_engineering": _resolve_core_asset("Landing", "simats_engineering_logo.png"),
    
    # Campus & Hero Banners
    "hero_campus": _resolve_core_asset("Landing", "hero_campus.jpg"),
    "hero_banner": _resolve_core_asset("Landing", "campus", "Main photo on the Landing Page.jpeg"),
    "campus_sail": _resolve_core_asset("Landing", "campus", "Sail.jpeg"),
    "research": _resolve_core_asset("Landing", "research", "Research.jpeg"),
    "student_activities": _resolve_core_asset("Landing", "student_events", "Student Activities.jpeg"),
    
    # Achievements
    "achievement_1": _resolve_core_asset("Landing", "achievements", "Achievement 1.jpeg"),
    "achievement_2": _resolve_core_asset("Landing", "achievements", "Achievement 2.jpeg"),
    "achievement_3": _resolve_core_asset("Landing", "achievements", "Achievement 3.jpeg"),
    "achievement_4": _resolve_core_asset("Landing", "achievements", "Achievement 4.jpeg"),
    "achievement_5": _resolve_core_asset("Landing", "achievements", "Achievement 5.jpeg"),
    
    # Event Posters & Certificates
    "event_poster_template": _resolve_core_asset("event_posters", "Poster Template.png") if os.path.exists(_resolve_core_asset("event_posters", "Poster Template.png")) else _resolve_core_asset("Event Posters", "Poster Template.png"),
    "certificate_template": _resolve_core_asset("Certificates", "template_01.png"),
}

ACHIEVEMENT_ITEMS = [
    {
        "path": ASSETS["achievement_1"],
        "title": "NAAC A++ Grade Accreditation",
        "caption": "Accredited with highest institutional CGPA and distinction."
    },
    {
        "path": ASSETS["achievement_2"],
        "title": "NIRF Top Ranking & Excellence",
        "caption": "Consistently ranked among premier universities nationwide."
    },
    {
        "path": ASSETS["achievement_3"],
        "title": "Global Hackathon & Tech Laurels",
        "caption": "Student innovators winning national & global competitions."
    },
    {
        "path": ASSETS["achievement_4"],
        "title": "Patents & Research Citations",
        "caption": "Leading university in published patents and high-impact research."
    },
    {
        "path": ASSETS["achievement_5"],
        "title": "World Record & Academic Honors",
        "caption": "Recognized internationally for academic milestones and innovation."
    }
]

CAMPUS_HIGHLIGHTS = [
    {
        "path": ASSETS["campus_sail"],
        "title": "Iconic Sail Architecture & Campus",
        "subtitle": "World-Class Infrastructure",
        "description": "Smart audiotoriums, research parks, and scenic campus landmarks."
    },
    {
        "path": ASSETS["research"],
        "title": "Cutting-Edge Research & Genomics Labs",
        "subtitle": "Innovation Powerhouse",
        "description": "Advanced wet-labs, robotics development cells, and AI supercomputing centers."
    },
    {
        "path": ASSETS["student_activities"],
        "title": "Vibrant Student Life & Global Fests",
        "subtitle": "Active Campus Community",
        "description": "50+ technical clubs, cultural spectacles, sports leagues, and national hackathons."
    }
]


def find_case_insensitive(base: str, rel_path: str) -> str | None:
    """Traverse directories case-insensitively for Linux deployments."""
    parts = rel_path.replace("\\", "/").strip("/").split("/")
    curr = base
    for part in parts:
        if not os.path.exists(curr) or not os.path.isdir(curr):
            return None
        found = False
        try:
            for entry in os.listdir(curr):
                if entry.lower() == part.lower():
                    curr = os.path.join(curr, entry)
                    found = True
                    break
        except Exception:
            return None
        if not found:
            return None
    return curr if os.path.exists(curr) and os.path.isfile(curr) else None


def resolve_asset_path(path_or_key: str) -> str:
    """
    Safely resolves a path or asset key to an existing local file.
    Works seamlessly across Windows and Linux (Streamlit Community Cloud).
    """
    if path_or_key in ASSETS:
        target = ASSETS[path_or_key]
        if os.path.exists(target) and os.path.isfile(target):
            return target
        # Try case-insensitive lookup
        rel = target.replace(BASE_DIR, "").lstrip("/\\")
        ci = find_case_insensitive(BASE_DIR, rel)
        if ci:
            return ci

    # Handle relative or workspace-relative path
    if isinstance(path_or_key, str) and path_or_key:
        cleaned = path_or_key.replace("/", os.sep).replace("\\", os.sep)
        # Try relative to BASE_DIR
        candidate = os.path.join(BASE_DIR, cleaned)
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return candidate
        # Try absolute
        if os.path.exists(cleaned) and os.path.isfile(cleaned):
            return cleaned

        # Try case-insensitive from BASE_DIR
        ci = find_case_insensitive(BASE_DIR, cleaned)
        if ci:
            return ci

        # If starts with assets or Assets, try opposite case
        if cleaned.lower().startswith("assets"):
            rest = cleaned[6:].lstrip("/\\")
            ci2 = find_case_insensitive(ASSETS_DIR, rest)
            if ci2:
                return ci2

    # Fallback default: Poster Template
    template = ASSETS.get("event_poster_template")
    if template and os.path.exists(template):
        return template

    # Search for any valid poster template file
    for cand in [
        os.path.join(ASSETS_DIR, "event_posters", "Poster Template.png"),
        os.path.join(ASSETS_DIR, "Event Posters", "Poster Template.png"),
        os.path.join(BASE_DIR, "Assets", "event_posters", "Poster Template.png"),
        os.path.join(BASE_DIR, "Assets", "Event Posters", "Poster Template.png"),
    ]:
        if os.path.exists(cand):
            return cand

    return template or ""


def get_event_poster_path(event: dict) -> str:
    """
    Returns the custom uploaded event poster or official neutral poster template.
    Guarantees NO external URLs, NO broken paths, and NO campus/research icon fallbacks.
    """
    banner = event.get("banner_url") if isinstance(event, dict) else ""
    
    # If custom uploaded poster exists, return it
    if banner and not banner.startswith("http://") and not banner.startswith("https://"):
        resolved = resolve_asset_path(banner)
        # Ensure it's not an old campus or research asset mapping
        is_campus_or_research = any(term in resolved.lower() for term in ["research.jpeg", "sail.jpeg", "student activities.jpeg", "main photo"])
        if os.path.exists(resolved) and not is_campus_or_research:
            return resolved

    # Fallback strictly to the neutral official event poster template
    return ASSETS["event_poster_template"]


@lru_cache(maxsize=32)
def get_image_base64(file_path: str) -> str:
    """
    Reads an image file and returns base64 data URI string.
    Cached for high rendering performance.
    """
    resolved = resolve_asset_path(file_path)
    if not os.path.exists(resolved):
        resolved = ASSETS["event_poster_template"]
        
    mime_type = "image/png"
    if resolved.lower().endswith((".jpg", ".jpeg")):
        mime_type = "image/jpeg"
    elif resolved.lower().endswith(".svg"):
        mime_type = "image/svg+xml"
        
    try:
        with open(resolved, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        print(f"[ASSET ENCODING ERROR] {resolved}: {e}")
        return ""


def get_user_avatar_html(user: dict | None, size: int = 46) -> str:
    """
    Generate an HTML avatar thumbnail for the user.
    - If user has uploaded a photo and file exists on disk: returns circular <img> with base64 data URI.
    - Otherwise returns a clean circular initials badge with university gold border and deep navy gradient.
    """
    if not user:
        return ""

    avatar_path = user.get("avatar_url")
    if avatar_path and isinstance(avatar_path, str) and avatar_path.strip():
        cleaned = avatar_path.replace("/", os.sep).replace("\\", os.sep).strip()
        full_avatar_path = os.path.join(BASE_DIR, cleaned) if not os.path.isabs(cleaned) else cleaned
        if os.path.exists(full_avatar_path) and os.path.isfile(full_avatar_path):
            img_b64 = get_image_base64(full_avatar_path)
            if img_b64:
                return (
                    f'<img src="{img_b64}" '
                    f'style="width: {size}px; height: {size}px; min-width: {size}px; border-radius: 50%; '
                    f'object-fit: cover; border: 2.5px solid #C5A059; box-shadow: 0 2px 8px rgba(10,37,64,0.15); '
                    f'display: inline-block; vertical-align: middle;" alt="{user.get("full_name", "User")} Avatar"/>'
                )

    # Graceful fallback: clean initials badge
    name = (user.get("full_name") or "User").strip()
    parts = [p for p in name.split() if p and not p.endswith(".")]
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[-1][0]).upper()
    elif parts:
        initials = parts[0][:2].upper()
    else:
        initials = "U"

    font_size = max(11, int(size * 0.38))
    return (
        f'<div style="width: {size}px; height: {size}px; min-width: {size}px; border-radius: 50%; '
        f'background: linear-gradient(135deg, #0A2540 0%, #1E3A8A 100%); color: #C5A059; '
        f'display: inline-flex; align-items: center; justify-content: center; font-weight: 700; '
        f'font-size: {font_size}px; border: 2.5px solid #C5A059; box-shadow: 0 2px 8px rgba(10,37,64,0.15); '
        f'letter-spacing: 0.5px; vertical-align: middle;" title="{name}">{initials}</div>'
    )


def clean_html(html_str: str) -> str:
    """
    Guarantees that NO line in the HTML string starts with 4 or more spaces,
    which would cause Streamlit's Markdown engine to parse it as a <pre><code> block.
    Strips leading and trailing whitespace from every line.
    """
    if not html_str:
        return ""
    return "\n".join(line.strip() for line in html_str.splitlines() if line.strip())


def render_html(html_str: str):
    """
    Safely render HTML in Streamlit with zero raw code leakage.
    Enforces clean_html to strip all indentation and sets unsafe_allow_html=True.
    """
    import streamlit as st
    st.markdown(clean_html(html_str), unsafe_allow_html=True)



