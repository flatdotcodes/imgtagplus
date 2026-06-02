# ImgTagPlus Launch Site

A marketing/launch website for ImgTagPlus featuring:
- Automated screenshots via Playwright
- Dark & Light mode previews
- CLI & TUI examples
- Zoomable screenshot highlights
- Responsive design matching the app

## Setup

```bash
cd launch-site
pip install -r requirements.txt
python -m playwright install chromium
```

## Taking Screenshots

1. First, start the ImgTagPlus server:
```bash
cd ..
imgtagplus --start-server
```

2. Then run the screenshot script:
```bash
cd launch-site
python scripts/take-screenshots.py
```

This will capture:
- Web UI in Light Mode
- Web UI in Dark Mode
- Help Dialog
- Performance Dialog
- File Picker Dialog
- Image Viewer

## Viewing the Site

Open `index.html` in your browser:

```bash
# Using Python's built-in server
python -m http.server 8080

# Then visit http://localhost:8080
```

Or simply open the file directly in a browser.

## Screenshots Placeholder

If you don't have the app running, you can use placeholder images:

```bash
# Create placeholder screenshots
python scripts/create-placeholders.py
```

## Customization

- Edit `index.html` to modify content
- Update zoom markers in the hero section
- Add more screenshots to the gallery
- Customize colors in the Tailwind config
