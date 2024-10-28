#!/usr/bin/env python3

import json
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path
import cairosvg
import io
import textwrap

# Determine the script's directory
script_dir = Path(__file__).resolve().parent

# Constants
OUTPUT_DIR = script_dir.parent / "assets"
FONT_PATH = script_dir.parent / "assets" / "fonts" / "DejaVuSans-Bold.ttf"  # Update as needed
BUTTON_COLOR = (0, 178, 89)  # Color for the "Sign it now" button
TEXT_COLOR = (255, 255, 255)  # White text color
BUTTON_TEXT = "Sign it now"
MAIN_TEXT = "A community statement supporting the Open Source Definition (OSD)"
CALL_TO_ACTION_TEXT = "Call to Open Source Software users"
IMAGE_SIZE = (1280, 640)
BUTTON_SIZE = (300, 70)  # Width and height of the button

# Load translations from translate.py output JSON file
translations_path = script_dir.parent / "_translations" / "image.json"  # Path to translations.json

# Default translations in case translations.json is not found
default_translations = {
    "button_text": BUTTON_TEXT,
    "main_text": MAIN_TEXT,
    "call_to_action_text": CALL_TO_ACTION_TEXT,
    "language_code": "en"
}

# Check if translations.json exists
if not translations_path.exists():
    # Use default translations if translations.json doesn't exist
    translations = {"en": default_translations}
else:
    try:
        # Load translations
        with open(translations_path, "r") as file:
            translations = json.load(file)
    except json.JSONDecodeError:
        print("Error: translations.json is not a valid JSON file. Using default translations.")
        translations = {"en": default_translations}

# Create output directory
OUTPUT_DIR.mkdir(exist_ok=True)

# Load the new background image
background_path = script_dir.parent / "assets" / "social-media-preview-background.jpg"
background_image = Image.open(background_path).convert("RGBA")

# Convert SVG to PNG
def convert_svg_to_png(svg_path):
    with open(svg_path, 'rb') as svg_file:
        svg_data = svg_file.read()
    png_data = cairosvg.svg2png(bytestring=svg_data)
    return Image.open(io.BytesIO(png_data))

# Use the function to open the logo
logo_path = script_dir.parent / "assets" / "logo.svg"
logo_image = convert_svg_to_png(logo_path).convert("RGBA")

# Resize logo while maintaining aspect ratio
def resize_logo(image, max_width, max_height):
    aspect_ratio = image.width / image.height
    if image.width > image.height:
        new_width = min(max_width, image.width)
        new_height = int(new_width / aspect_ratio)
    else:
        new_height = min(max_height, image.height)
        new_width = int(new_height * aspect_ratio)
    return image.resize((new_width, new_height), Image.LANCZOS)

# Resize and position the logo
logo_size = (600, 600)  # Increase max size significantly
logo_image = resize_logo(logo_image, *logo_size)
logo_position = (background_image.width - logo_image.width - 40, 40)  # Top right with more padding

# Load the main font
main_font = ImageFont.truetype(str(FONT_PATH), 40)  # Adjust the size as needed

# Load the button font
button_font = ImageFont.truetype(str(FONT_PATH), 30)  # Adjust the size as needed

# Function to create a pill-shaped button
def create_pill_button(draw, position, size, color, text, font, text_color):
    x, y = position
    width, height = size
    radius = height // 2
    draw.rounded_rectangle(
        [x, y, x + width, y + height],
        radius=radius,
        fill=color
    )
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    draw.text(
        (x + (width - text_width) / 2, y + (height - text_height) / 2),
        text,
        font=font,
        fill=text_color
    )

# Function to create a preview image with translations
def create_image(text_main, text_call_to_action, button_text, language_code):
    img = background_image.copy()
    draw = ImageDraw.Draw(img)

    # Paste the logo
    img.paste(logo_image, logo_position, logo_image)

    # Draw the main title text, wrapping to fit
    text_main_wrapped = "\n".join(textwrap.wrap(text_main, width=30))  # Adjust width for wrapping
    draw.text(
        (40, logo_image.height + 60),  # Position below the logo with more padding
        text_main_wrapped,
        font=main_font,
        fill=TEXT_COLOR
    )

    # Draw call-to-action text
    cta_bbox = draw.textbbox((0, 0), text_call_to_action, font=main_font)
    cta_width, cta_height = cta_bbox[2] - cta_bbox[0], cta_bbox[3] - cta_bbox[1]
    draw.text(
        ((IMAGE_SIZE[0] - cta_width) / 2, (IMAGE_SIZE[1] - cta_height) / 2 + 60),
        text_call_to_action,
        font=main_font,
        fill=TEXT_COLOR
    )

    # Draw additional text in bottom left
    additional_text = "CALL TO OPEN SOURCE SOFTWARE USERS"
    draw.text(
        (40, background_image.height - 80),  # Bottom left with padding
        additional_text,
        font=button_font,  # Use smaller font
        fill=TEXT_COLOR
    )

    # Adjust button color, position, and shape
    button_color = "#0072CE"  # Blue color from the logo
    button_size = (250, 70)  # Adjust size for pill shape
    button_position = (background_image.width - button_size[0] - 40, background_image.height - button_size[1] - 40)  # Bottom right with more padding

    # Draw the pill-shaped button
    draw.rounded_rectangle(
        [button_position, (button_position[0] + button_size[0], button_position[1] + button_size[1])],
        radius=35,  # Radius for pill shape
        fill=button_color
    )

    # Draw button text
    draw.text(
        (button_position[0] + 20, button_position[1] + 15),  # Center text within the button
        button_text,
        font=button_font,
        fill="white"
    )

    # Determine the output path based on language code
    if language_code == "en":
        output_path = script_dir.parent / "assets" / "social-media-preview.png"
    else:
        output_path = script_dir.parent / "assets" / f"social-media-preview_{language_code}.png"

    # Save image with the determined path
    img.save(output_path)

# Generate images for each translation
for lang_code, translation in translations.items():
    main_text_translated = translation.get("main_text", MAIN_TEXT)
    call_to_action_translated = translation.get("call_to_action", CALL_TO_ACTION_TEXT)
    button_text_translated = translation.get("button_text", BUTTON_TEXT)

    create_image(main_text_translated, call_to_action_translated, button_text_translated, lang_code)

print(f"Images generated in {OUTPUT_DIR}/ for each language.")
