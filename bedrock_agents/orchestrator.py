import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from .config import COMFYUI_HOST, DASHBOARD_DIR
from .validate import check_image, valid_hero_path, validate_updates
from .staff.content_director import ContentDirector
from .staff.web_developer import WebDeveloper
from .staff.publishing_manager import PublishingManager
from .staff.photo_designer import PhotoDesigner

MEETING_LOG = os.path.join(DASHBOARD_DIR, "bedrock", "meeting_latest.json")


def comfyui_reachable(timeout=4):
    try:
        with urllib.request.urlopen(f"{COMFYUI_HOST}/system_stats", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def run_meeting_generator(publish=None):
    """Runs the daily staff meeting. Yields (agent, message) tuples as it goes.

    Runs on the M3 (see run_meeting.py). Stages: Director -> [Photo Designer render || Web Developer copy]
    -> Publisher. Every event is timestamped and saved to meeting_latest.json, which the Bedrock page
    replays when a visitor presses the staff-meeting button.
    """
    if publish is None:
        publish = os.getenv("BEDROCK_PUBLISH", "1") != "0"

    t0 = time.time()
    events = []

    def ev(agent, message):
        events.append({"agent": agent, "message": message, "t": round(time.time() - t0, 1)})
        return agent, message

    # 0. Is the image engine up?
    render_ok = comfyui_reachable()
    yield ev("system", "Visual cortex online." if render_ok else "Visual cortex OFFLINE: no new image this run.")

    # 1a. Read the current Swiss Re Institute report (cached after the first read)
    from .sigma_report import get_sigma_context
    sigma = get_sigma_context()
    if sigma["ok"]:
        yield ev("director", f"Read {sigma['label']} ({sigma['published']}): {len(sigma['findings'])} key findings.")
        if sigma.get("newer"):
            yield ev("director", "Swiss Re has published a newer sigma report; the pinned source needs updating.")
    else:
        yield ev("director", f"Swiss Re report unavailable ({sigma['note'] or 'unknown'}); not citing it today.")

    # 1b. Content Director plans (real market data + news -> brief)
    director = ContentDirector()
    try:
        yield ev("director", "Analyzing market trends & drafting brief...")
        brief = director.create_daily_brief()
        theme = brief.get("theme", brief.get("headline", "Global Market Risk"))
        yield ev("director", f"Theme selected: {theme}")
    except Exception as e:
        yield ev("error", f"Director failed: {e}")
        return

    # 2. Photo Designer (Flux render) and Web Developer (page copy) work at the same time
    designer, web_dev = PhotoDesigner(), WebDeveloper()
    concept = brief.get("image_concept", brief.get("headline", "Modern Insurance Office"))
    image_path, updates = None, None

    with ThreadPoolExecutor(max_workers=2) as pool:
        if render_ok:
            yield ev("designer", "Composing high-fidelity imagery...")
            f_img = pool.submit(designer.generate_image, theme, concept)
        else:
            f_img = None
        yield ev("developer", "Coding responsive HTML structure...")
        f_web = pool.submit(web_dev.build_page, brief)

        pending = [f for f in (f_img, f_web) if f is not None]
        for fut in as_completed(pending):
            if fut is f_web:
                try:
                    updates = fut.result()
                    yield ev("developer", f"Page copy ready ({len(updates)} fields; market tiles from live data).")
                except Exception as e:
                    yield ev("error", f"Web Developer failed: {e}")
            else:
                try:
                    image_path = fut.result()
                except Exception as e:
                    image_path = None
                    print(f"Designer error: {e}")
                if valid_hero_path(image_path):
                    ok, why = check_image(os.path.join(DASHBOARD_DIR, image_path.lstrip("/")))
                    if ok:
                        yield ev("designer", f"Image rendered: {os.path.basename(image_path)}")
                    else:
                        print(f"Rejected image {image_path}: {why}")
                        image_path = None
                        yield ev("designer", f"Render REJECTED ({why}): keeping the previous image.")
                else:
                    image_path = None
                    yield ev("designer", "Render FAILED: keeping the previous image.")

    if updates is None:
        yield ev("error", "No page copy produced; nothing to publish.")
        return
    updates, problems = validate_updates(updates)
    for p in problems:
        print(f"Validation: {p}")
    if problems:
        yield ev("publisher", f"Dropped {len(problems)} invalid field(s); keeping previous text for them.")
    if not updates and not image_path:
        yield ev("error", "Nothing valid to publish.")
        return
    if image_path:
        updates["hero_image"] = image_path

    # 3. Publishing Manager: edit the page, save the replay log, then commit + push + hot-swap
    publisher = PublishingManager()
    try:
        yield ev("publisher", "Applying updates to the page...")
        changes = publisher.apply_updates(updates, theme)
        yield ev("publisher", f"Page updated ({changes} changes).")
    except Exception as e:
        yield ev("error", f"Publisher failed: {e}")
        return

    yield ev("system", "Meeting Adjourned")
    try:
        with open(MEETING_LOG, "w") as f:
            json.dump({
                "date": datetime.now().isoformat(timespec="seconds"),
                "theme": theme,
                "duration_s": round(time.time() - t0, 1),
                "image": image_path,
                "brief": {k: brief.get(k) for k in ("headline", "market_sentiment", "briefing_body", "date", "source", "sigma")},
                "events": events,
            }, f, indent=2)
    except Exception as e:
        print(f"⚠️ Could not write meeting log: {e}")

    if publish:
        yield ("publisher", "Committing, pushing and hot-swapping...")
        ok = publisher.publish(theme)
        yield ("publisher", "Published live." if ok else "Publish FAILED: see log.")
    else:
        yield ("publisher", "Dry run: page edited locally, nothing pushed.")


def main():
    print("========================================")
    print("🏢 Bedrock Insurance - Daily Cycle Start")
    print("========================================")
    t = time.time()
    for agent, msg in run_meeting_generator():
        print(f"[{time.time() - t:6.1f}s] [{agent.upper()}] {msg}", flush=True)


if __name__ == "__main__":
    main()
