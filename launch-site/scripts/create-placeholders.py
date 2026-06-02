"""Create placeholder screenshots for the launch site."""

from PIL import Image, ImageDraw, ImageFont
import os


def create_placeholder_screenshots():
    """Generate placeholder screenshots matching ImgTagPlus UI style."""

    screenshots_dir = "launch-site/screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)

    # Dimensions for desktop screenshots
    width, height = 1920, 1080

    def draw_card(draw, x, y, w, h, title, bg_color, border_color):
        """Draw a card-like container."""
        # Card background
        draw.rectangle([x, y, x + w, y + h], fill=bg_color, outline=border_color, width=1)
        # Card header
        draw.rectangle([x, y, x + w, y + 50], fill=(250, 250, 252) if bg_color[0] > 100 else (39, 39, 42))
        # Title
        draw.text((x + 20, y + 15), title, fill=(9, 9, 11) if bg_color[0] > 100 else (250, 250, 250))
        return y + 60

    def create_web_ui_light():
        """Create light mode web UI screenshot."""
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Header
        draw.rectangle([0, 0, width, 70], fill=(255, 255, 255), outline=(228, 228, 231), width=1)
        draw.text((30, 25), "ImgTagPlus", fill=(9, 9, 11))
        draw.text((150, 28), "v1.0.0", fill=(113, 113, 122))

        # Navigation buttons
        draw.rounded_rectangle(
            [width - 300, 20, width - 220, 50], radius=6, fill=(244, 244, 245), outline=(228, 228, 231)
        )
        draw.text((width - 290, 28), "Tagger", fill=(9, 9, 11))
        draw.rounded_rectangle(
            [width - 210, 20, width - 130, 50], radius=6, fill=(255, 255, 255), outline=(228, 228, 231)
        )
        draw.text((width - 200, 28), "Viewer", fill=(113, 113, 122))

        # Status badge
        draw.rounded_rectangle(
            [width - 120, 20, width - 30, 50], radius=6, fill=(244, 244, 245), outline=(228, 228, 231)
        )
        draw.ellipse([width - 110, 30, width - 100, 40], fill=(161, 161, 170))
        draw.text((width - 95, 28), "Idle", fill=(63, 63, 70))

        # Left column - Job Configuration card
        card_y = draw_card(draw, 30, 100, 450, 550, "Job Configuration", (255, 255, 255), (228, 228, 231))

        # Form fields
        y = card_y + 20
        draw.text((50, y), "Source Folder Path", fill=(63, 63, 70))
        draw.rounded_rectangle([50, y + 25, 430, y + 55], radius=6, fill=(255, 255, 255), outline=(228, 228, 231))
        draw.text((60, y + 32), "/path/to/photos", fill=(161, 161, 170))
        draw.rounded_rectangle([350, y + 25, 430, y + 55], radius=6, fill=(244, 244, 245), outline=(228, 228, 231))
        draw.text((365, y + 32), "Browse", fill=(63, 63, 70))

        y += 70
        draw.text((50, y), "Model", fill=(63, 63, 70))
        draw.rounded_rectangle([50, y + 25, 430, y + 55], radius=6, fill=(255, 255, 255), outline=(228, 228, 231))
        draw.text((60, y + 32), "CLIP (Zero-Shot Classification)", fill=(9, 9, 11))

        y += 70
        draw.text((50, y), "Confidence Threshold", fill=(63, 63, 70))
        draw.text((380, y), "0.25", fill=(113, 113, 122))
        draw.rounded_rectangle([50, y + 25, 430, y + 35], radius=3, fill=(228, 228, 231))
        draw.rounded_rectangle([50, y + 25, 150, y + 35], radius=3, fill=(37, 99, 235))

        y += 50
        draw.text((50, y), "Max Tags", fill=(63, 63, 70))
        draw.text((380, y), "20", fill=(113, 113, 122))
        draw.rounded_rectangle([50, y + 25, 430, y + 35], radius=3, fill=(228, 228, 231))
        draw.rounded_rectangle([50, y + 25, 200, y + 35], radius=3, fill=(37, 99, 235))

        y += 60
        draw.text((50, y), "Scan subdirectories recursively", fill=(63, 63, 70))
        draw.rounded_rectangle([380, y, 410, y + 20], radius=10, fill=(37, 99, 235))

        # Start button
        draw.rounded_rectangle([50, 580, 430, 620], radius=8, fill=(37, 99, 235))
        draw.text((200, 590), "Start Tagging", fill=(255, 255, 255))

        # System Profile card
        draw_card(draw, 30, 680, 450, 200, "System Profile", (255, 255, 255), (228, 228, 231))
        draw.rounded_rectangle([50, 760, 220, 810], radius=6, fill=(244, 244, 245), outline=(228, 228, 231))
        draw.text((60, 770), "RAM", fill=(113, 113, 122))
        draw.text((60, 790), "16 GB", fill=(9, 9, 11))

        draw.rounded_rectangle([240, 760, 430, 810], radius=6, fill=(244, 244, 245), outline=(228, 228, 231))
        draw.text((250, 770), "Accelerator", fill=(113, 113, 122))
        draw.text((250, 790), "MPS", fill=(37, 99, 235))

        draw.rounded_rectangle([50, 830, 430, 860], radius=6, fill=(244, 244, 245), outline=(228, 228, 231))
        draw.text((60, 837), "Performance Rating", fill=(113, 113, 122))
        draw.rounded_rectangle([340, 833, 420, 857], radius=4, fill=(244, 244, 245), outline=(228, 228, 231))
        draw.text((355, 837), "Excellent", fill=(22, 163, 74))

        # Right column - Progress card
        draw_card(draw, 510, 100, 1380, 180, "Ready", (255, 255, 255), (228, 228, 231))
        draw.text((530, 170), "Waiting to start...", fill=(113, 113, 122))
        draw.text((530, 210), "Runtime", fill=(161, 161, 170))
        draw.text((530, 230), "00:00:00", fill=(113, 113, 122))
        draw.text((1750, 210), "0%", fill=(9, 9, 11))
        draw.text((1700, 235), "0 / 0 images", fill=(113, 113, 122))
        draw.rounded_rectangle([530, 255, 1850, 265], radius=3, fill=(228, 228, 231))

        # Terminal card
        draw.rounded_rectangle([510, 300, 1850, 880], radius=12, fill=(9, 9, 11))
        draw.rectangle([510, 300, 1850, 350], fill=(24, 24, 27), outline=(39, 39, 42))
        draw.ellipse([530, 315, 545, 330], fill=(239, 68, 68))
        draw.ellipse([555, 315, 570, 330], fill=(234, 179, 8))
        draw.ellipse([580, 315, 595, 330], fill=(34, 197, 94))
        draw.text((620, 317), "server_logs ~", fill=(161, 161, 170))
        draw.text((530, 380), "System standing by. Waiting for job...", fill=(161, 161, 170))

        img.save(f"{screenshots_dir}/web-ui-light.png")
        print(f"Created: web-ui-light.png")

    def create_web_ui_dark():
        """Create dark mode web UI screenshot."""
        img = Image.new("RGB", (width, height), (9, 9, 11))
        draw = ImageDraw.Draw(img)

        # Header
        draw.rectangle([0, 0, width, 70], fill=(9, 9, 11), outline=(39, 39, 42), width=1)
        draw.text((30, 25), "ImgTagPlus", fill=(250, 250, 250))
        draw.text((150, 28), "v1.0.0", fill=(161, 161, 170))

        # Navigation buttons
        draw.rounded_rectangle([width - 300, 20, width - 220, 50], radius=6, fill=(24, 24, 27), outline=(39, 39, 42))
        draw.text((width - 290, 28), "Tagger", fill=(250, 250, 250))

        # Status badge
        draw.rounded_rectangle([width - 120, 20, width - 30, 50], radius=6, fill=(24, 24, 27), outline=(39, 39, 42))
        draw.ellipse([width - 110, 30, width - 100, 40], fill=(161, 161, 170))
        draw.text((width - 95, 28), "Idle", fill=(161, 161, 170))

        # Left column - Job Configuration card
        draw.rounded_rectangle([30, 100, 480, 650], radius=12, fill=(9, 9, 11), outline=(39, 39, 42))
        draw.rectangle([30, 100, 480, 150], fill=(24, 24, 27))
        draw.text((50, 115), "Job Configuration", fill=(250, 250, 250))

        # Form fields
        y = 170
        draw.text((50, y), "Source Folder Path", fill=(161, 161, 170))
        draw.rounded_rectangle([50, y + 25, 430, y + 55], radius=6, fill=(24, 24, 27), outline=(39, 39, 42))
        draw.text((60, y + 32), "/path/to/photos", fill=(113, 113, 122))

        y += 70
        draw.text((50, y), "Model", fill=(161, 161, 170))
        draw.rounded_rectangle([50, y + 25, 430, y + 55], radius=6, fill=(24, 24, 27), outline=(39, 39, 42))
        draw.text((60, y + 32), "CLIP (Zero-Shot Classification)", fill=(250, 250, 250))

        y += 70
        draw.text((50, y), "Confidence Threshold", fill=(161, 161, 170))
        draw.text((380, y), "0.25", fill=(161, 161, 170))
        draw.rounded_rectangle([50, y + 25, 430, y + 35], radius=3, fill=(39, 39, 42))
        draw.rounded_rectangle([50, y + 25, 150, y + 35], radius=3, fill=(37, 99, 235))

        y += 50
        draw.text((50, y), "Max Tags", fill=(161, 161, 170))
        draw.text((380, y), "20", fill=(161, 161, 170))

        # Start button
        draw.rounded_rectangle([50, 580, 430, 620], radius=8, fill=(37, 99, 235))
        draw.text((200, 590), "Start Tagging", fill=(255, 255, 255))

        # System Profile card
        draw.rounded_rectangle([30, 680, 480, 880], radius=12, fill=(9, 9, 11), outline=(39, 39, 42))
        draw.rectangle([30, 680, 480, 730], fill=(24, 24, 27))
        draw.text((50, 695), "System Profile", fill=(250, 250, 250))

        # Right column
        draw.rounded_rectangle([510, 100, 1850, 280], radius=12, fill=(9, 9, 11), outline=(39, 39, 42))
        draw.rectangle([510, 100, 1850, 150], fill=(24, 24, 27))
        draw.text((530, 115), "Ready", fill=(250, 250, 250))
        draw.text((530, 170), "Waiting to start...", fill=(161, 161, 170))

        # Terminal
        draw.rounded_rectangle([510, 300, 1850, 880], radius=12, fill=(9, 9, 11), outline=(39, 39, 42))
        draw.rectangle([510, 300, 1850, 350], fill=(24, 24, 27))
        draw.ellipse([530, 315, 545, 330], fill=(239, 68, 68))
        draw.ellipse([555, 315, 570, 330], fill=(234, 179, 8))
        draw.ellipse([580, 315, 595, 330], fill=(34, 197, 94))
        draw.text((530, 380), "System standing by. Waiting for job...", fill=(161, 161, 170))

        img.save(f"{screenshots_dir}/web-ui-dark.png")
        print(f"Created: web-ui-dark.png")

    def create_dialog_screenshot(filename, title, content_lines, is_dark=False):
        """Create a dialog screenshot."""
        bg_color = (9, 9, 11) if is_dark else (255, 255, 255)
        text_color = (250, 250, 250) if is_dark else (9, 9, 11)
        secondary_color = (161, 161, 170) if is_dark else (113, 113, 122)
        card_bg = (24, 24, 27) if is_dark else (255, 255, 255)
        border_color = (39, 39, 42) if is_dark else (228, 228, 231)

        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # Background blur effect (simplified)
        draw.rectangle([0, 0, width, height], fill=bg_color)

        # Dialog
        dialog_w, dialog_h = 800, 600
        dialog_x = (width - dialog_w) // 2
        dialog_y = (height - dialog_h) // 2

        draw.rounded_rectangle(
            [dialog_x, dialog_y, dialog_x + dialog_w, dialog_y + dialog_h],
            radius=16,
            fill=card_bg,
            outline=border_color,
        )

        # Header
        draw.rectangle([dialog_x, dialog_y, dialog_x + dialog_w, dialog_y + 80], fill=card_bg)
        draw.text((dialog_x + 30, dialog_y + 25), title, fill=text_color)

        # Content
        y = dialog_y + 100
        for line in content_lines:
            if line.startswith("**"):
                draw.text((dialog_x + 30, y), line.replace("**", ""), fill=text_color)
            else:
                draw.text((dialog_x + 30, y), line, fill=secondary_color)
            y += 30

        # Close button
        draw.rounded_rectangle(
            [dialog_x + dialog_w - 150, dialog_y + dialog_h - 70, dialog_x + dialog_w - 30, dialog_y + dialog_h - 30],
            radius=8,
            fill=(37, 99, 235),
        )
        draw.text((dialog_x + dialog_w - 120, dialog_y + dialog_h - 60), "Got it", fill=(255, 255, 255))

        img.save(f"{screenshots_dir}/{filename}")
        print(f"Created: {filename}")

    def create_viewer_screenshot():
        """Create viewer mode screenshot."""
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Header
        draw.rectangle([0, 0, width, 70], fill=(255, 255, 255), outline=(228, 228, 231))
        draw.text((30, 25), "ImgTagPlus", fill=(9, 9, 11))

        # Navigation
        draw.rounded_rectangle(
            [width - 300, 20, width - 220, 50], radius=6, fill=(255, 255, 255), outline=(228, 228, 231)
        )
        draw.text((width - 290, 28), "Tagger", fill=(113, 113, 122))
        draw.rounded_rectangle(
            [width - 210, 20, width - 130, 50], radius=6, fill=(244, 244, 245), outline=(228, 228, 231)
        )
        draw.text((width - 200, 28), "Viewer", fill=(9, 9, 11))

        # Select Folder card
        draw.rounded_rectangle([30, 100, 1850, 300], radius=12, fill=(255, 255, 255), outline=(228, 228, 231))
        draw.rectangle([30, 100, 1850, 150], fill=(250, 250, 252))
        draw.text((50, 115), "Select Folder", fill=(9, 9, 11))
        draw.text((50, 170), "Folder Path", fill=(63, 63, 70))
        draw.rounded_rectangle([50, 200, 1600, 240], radius=6, fill=(255, 255, 255), outline=(228, 228, 231))
        draw.text((60, 210), "/path/to/photos", fill=(161, 161, 170))
        draw.rounded_rectangle([1620, 200, 1700, 240], radius=6, fill=(244, 244, 245))
        draw.text((1635, 210), "Browse", fill=(63, 63, 70))
        draw.rounded_rectangle([1720, 200, 1830, 240], radius=6, fill=(37, 99, 235))
        draw.text((1740, 210), "Load Files", fill=(255, 255, 255))

        # Image Files card
        draw.rounded_rectangle([30, 330, 1850, 1000], radius=12, fill=(255, 255, 255), outline=(228, 228, 231))
        draw.rectangle([30, 330, 1850, 380], fill=(250, 250, 252))
        draw.text((50, 345), "Image Files", fill=(9, 9, 11))

        # Grid view placeholder
        y = 400
        for row in range(3):
            x = 50
            for col in range(4):
                draw.rounded_rectangle(
                    [x, y, x + 420, y + 280], radius=8, fill=(244, 244, 245), outline=(228, 228, 231)
                )
                # Image placeholder
                draw.rectangle([x + 10, y + 10, x + 410, y + 210], fill=(228, 228, 231))
                draw.text((x + 20, y + 230), f"image_{row * 4 + col + 1}.jpg", fill=(63, 63, 70))
                # Tags
                draw.rounded_rectangle([x + 20, y + 255, x + 80, y + 275], radius=4, fill=(37, 99, 235))
                draw.text((x + 30, y + 258), "nature", fill=(255, 255, 255))
                draw.rounded_rectangle([x + 90, y + 255, x + 150, y + 275], radius=4, fill=(37, 99, 235))
                draw.text((x + 100, y + 258), "outdoor", fill=(255, 255, 255))
                x += 450
            y += 310

        img.save(f"{screenshots_dir}/web-ui-viewer.png")
        print(f"Created: web-ui-viewer.png")

    def create_file_picker_screenshot():
        """Create file picker dialog screenshot."""
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Background (simplified main UI)
        draw.rectangle([0, 0, width, height], fill=(244, 244, 245))

        # Dialog
        dialog_w, dialog_h = 700, 600
        dialog_x = (width - dialog_w) // 2
        dialog_y = (height - dialog_h) // 2

        draw.rounded_rectangle(
            [dialog_x, dialog_y, dialog_x + dialog_w, dialog_y + dialog_h],
            radius=16,
            fill=(255, 255, 255),
            outline=(228, 228, 231),
        )

        # Header
        draw.rectangle([dialog_x, dialog_y, dialog_x + dialog_w, dialog_y + 80], fill=(255, 255, 255))
        draw.text((dialog_x + 30, dialog_y + 25), "Select Directory", fill=(9, 9, 11))

        # Warning banner
        draw.rounded_rectangle(
            [dialog_x + 30, dialog_y + 100, dialog_x + dialog_w - 30, dialog_y + 140],
            radius=6,
            fill=(255, 251, 235),
            outline=(251, 191, 36),
        )
        draw.text(
            (dialog_x + 50, dialog_y + 110),
            "⚠ Sandbox Mode: Access is restricted to the workspace sandbox directory.",
            fill=(180, 83, 9),
        )

        # Current path
        draw.rounded_rectangle(
            [dialog_x + 30, dialog_y + 160, dialog_x + dialog_w - 30, dialog_y + 200], radius=6, fill=(244, 244, 245)
        )
        draw.text((dialog_x + 50, dialog_y + 170), "Current: /home/user/workspace", fill=(63, 63, 70))

        # Directory list
        y = dialog_y + 220
        folders = ["📁 Documents", "📁 Photos", "📁 Projects", "📁 Downloads", "📁 Sandbox"]
        for folder in folders:
            draw.text((dialog_x + 50, y), folder, fill=(63, 63, 70))
            y += 40

        # Footer buttons
        draw.rounded_rectangle(
            [dialog_x + dialog_w - 280, dialog_y + dialog_h - 70, dialog_x + dialog_w - 160, dialog_y + dialog_h - 30],
            radius=8,
            fill=(255, 255, 255),
            outline=(228, 228, 231),
        )
        draw.text((dialog_x + dialog_w - 250, dialog_y + dialog_h - 60), "Cancel", fill=(63, 63, 70))

        draw.rounded_rectangle(
            [dialog_x + dialog_w - 150, dialog_y + dialog_h - 70, dialog_x + dialog_w - 30, dialog_y + dialog_h - 30],
            radius=8,
            fill=(37, 99, 235),
        )
        draw.text((dialog_x + dialog_w - 130, dialog_y + dialog_h - 60), "Select", fill=(255, 255, 255))

        img.save(f"{screenshots_dir}/web-ui-file-picker.png")
        print(f"Created: web-ui-file-picker.png")

    # Generate all screenshots
    print("Generating placeholder screenshots...")
    create_web_ui_light()
    create_web_ui_dark()
    create_viewer_screenshot()
    create_file_picker_screenshot()

    # Help dialog
    help_content = [
        "Welcome to ImgTagPlus. It uses locally run models to automatically",
        "assign tags to your images without requiring internet access.",
        "",
        "1. Directory Path",
        "Provide an absolute path to the directory containing your images.",
        "",
        "2. Models",
        "**CLIP (Zero-Shot)**: The default, lightning-fast model.",
        "**Florence-2**: A rich Small Vision Language Model.",
        "",
        "3. Tags & Thresholds",
        "Max Tags controls the maximum amount of keywords added.",
        "Confidence Threshold: The lower the number, the more lenient.",
    ]
    create_dialog_screenshot("web-ui-help-dialog.png", "How to use ImgTagPlus", help_content)

    # Performance dialog
    perf_content = [
        "**Excellent** - GPU Native (MPS or VRAM > 8GB)",
        "CLIP: ~0.1s per image",
        "Florence-2 Base: ~0.5s - 1s per image",
        "",
        "**Good** - Optimized CPU (RAM > 16GB)",
        "CLIP: ~1s per image",
        "Florence-2 Base: ~2s - 4s per image",
        "",
        "**Poor** - Heavy CPU (Low RAM)",
        "CLIP: ~3s per image",
        "Florence-2 Large: Not recommended",
    ]
    create_dialog_screenshot("web-ui-perf-dialog.png", "System Performance Ratings", perf_content)

    print(f"\nAll screenshots created in: {screenshots_dir}/")


if __name__ == "__main__":
    create_placeholder_screenshots()
