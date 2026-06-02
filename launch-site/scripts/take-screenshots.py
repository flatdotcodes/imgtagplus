# Playwright configuration for ImgTagPlus launch site screenshots
# Run: python -m playwright install
# Then: python launch-site/scripts/take-screenshots.py

from playwright.sync_api import sync_playwright
import time
import os


def take_screenshots():
    """Capture screenshots of ImgTagPlus app in various states and modes."""

    screenshots_dir = "launch-site/screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)

        # Create contexts for different viewports
        desktop_context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,  # Retina quality
        )

        # Screenshot 1: Web UI - Light Mode
        print("Taking Web UI Light Mode screenshot...")
        page = desktop_context.new_page()
        page.goto("http://127.0.0.1:5000")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Ensure light mode
        page.evaluate("""() => {
            if (window.imgtagplusTheme) {
                window.imgtagplusTheme.applyTheme('light');
            }
            document.documentElement.classList.remove('dark');
        }""")
        time.sleep(0.5)

        page.screenshot(path=f"{screenshots_dir}/web-ui-light.png", full_page=True)

        # Screenshot 2: Web UI - Dark Mode
        print("Taking Web UI Dark Mode screenshot...")
        page.evaluate("""() => {
            if (window.imgtagplusTheme) {
                window.imgtagplusTheme.applyTheme('dark');
            }
            document.documentElement.classList.add('dark');
        }""")
        time.sleep(0.5)

        page.screenshot(path=f"{screenshots_dir}/web-ui-dark.png", full_page=True)

        # Screenshot 3: Help Dialog Open
        print("Taking Help Dialog screenshot...")
        page.evaluate("""() => {
            const dialog = document.getElementById('help-dialog');
            if (dialog) dialog.showModal();
        }""")
        time.sleep(0.5)
        page.screenshot(path=f"{screenshots_dir}/web-ui-help-dialog.png", full_page=True)
        page.evaluate("""() => {
            const dialog = document.getElementById('help-dialog');
            if (dialog) dialog.close();
        }""")

        # Screenshot 4: Performance Dialog
        print("Taking Performance Dialog screenshot...")
        page.evaluate("""() => {
            const dialog = document.getElementById('perf-dialog');
            if (dialog) dialog.showModal();
        }""")
        time.sleep(0.5)
        page.screenshot(path=f"{screenshots_dir}/web-ui-perf-dialog.png", full_page=True)
        page.evaluate("""() => {
            const dialog = document.getElementById('perf-dialog');
            if (dialog) dialog.close();
        }""")

        # Screenshot 5: Viewer Mode
        print("Taking Viewer Mode screenshot...")
        page.click("#show-viewer-view")
        time.sleep(1)
        page.screenshot(path=f"{screenshots_dir}/web-ui-viewer.png", full_page=True)

        # Screenshot 6: File Picker Dialog
        print("Taking File Picker Dialog screenshot...")
        page.click("#show-tagger-view")
        time.sleep(0.5)
        page.click("#browse-btn")
        time.sleep(1)
        page.screenshot(path=f"{screenshots_dir}/web-ui-file-picker.png", full_page=True)

        page.close()
        desktop_context.close()
        browser.close()

    print(f"\nScreenshots saved to: {screenshots_dir}/")
    print("Screenshots captured:")
    for f in os.listdir(screenshots_dir):
        if f.endswith(".png"):
            print(f"  - {f}")


if __name__ == "__main__":
    take_screenshots()
