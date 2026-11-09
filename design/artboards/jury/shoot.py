"""Screenshot every board of design/artboards/Jury.html into design/artboards/jury/*.png (system Chromium, as tests/test_frontend.py does)."""
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
PAGE = HERE.parent / "Jury.html"
CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser") or "/snap/bin/chromium"
NAMES = ["1_desktop_light_ai_essay", "2_desktop_dark_split_jury", "3_desktop_light_rerun", "4_phone_light_student_wrong",
         "5_phone_dark_earlier_detector", "6_phone_light_rerun", "7_decisions"]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROMIUM if Path(CHROMIUM).exists() else None, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1520, "height": 1000}, device_scale_factor=1)
    pg.goto(PAGE.as_uri())
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(400)
    for el, name in zip(pg.locator("figure.board .frame").all(), NAMES):
        el.screenshot(path=str(HERE / f"{name}.png"))
        print(name)
    for el in pg.locator(".frame.phone").all():           # no horizontal overflow inside the phone frames
        print("phone frame scrollWidth vs clientWidth:", el.evaluate("e => [e.scrollWidth, e.clientWidth]"))
    b.close()
