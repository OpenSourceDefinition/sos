#!/usr/bin/env python3

import json
import os
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

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

# Function to create a gradient image
def create_gradient_image(size, color1, color2):
    base = Image.new('RGBA', size)
    draw = ImageDraw.Draw(base)
    for y in range(size[1]):
        r, g, b = (
            int(color1[0] + (color2[0] - color1[0]) * y / size[1]),
            int(color1[1] + (color2[1] - color1[1]) * y / size[1]),
            int(color1[2] + (color2[2] - color1[2]) * y / size[1])
        )
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))
    return base

# Create a gradient base image
color_start = (255, 255, 255)  # White
color_end = (0, 178, 89)  # Green
base_image = create_gradient_image(IMAGE_SIZE, color_start, color_end)

# Font setup
try:
    main_font = ImageFont.truetype(str(FONT_PATH), 48)
    button_font = ImageFont.truetype(str(FONT_PATH), 32)
except IOError:
    print("Font file not found. Please update FONT_PATH to a valid font.")
    # Use a default font as a fallback
    main_font = ImageFont.load_default()
    button_font = ImageFont.load_default()

# Function to create a preview image with translations
def create_image(text_main, text_call_to_action, button_text, language_code):
    img = base_image.copy()
    draw = ImageDraw.Draw(img)
    
    # Draw main text
    text_bbox = draw.textbbox((0, 0), text_main, font=main_font)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    draw.text(
        ((IMAGE_SIZE[0] - text_width) / 2, 200),  # Centered positioning
        text_main,
        font=main_font,
        fill=TEXT_COLOR
    )

    # Draw call-to-action text
    cta_bbox = draw.textbbox((0, 0), text_call_to_action, font=main_font)
    cta_width, cta_height = cta_bbox[2] - cta_bbox[0], cta_bbox[3] - cta_bbox[1]
    draw.text(
        ((IMAGE_SIZE[0] - cta_width) / 2, 100),
        text_call_to_action,
        font=main_font,
        fill=TEXT_COLOR
    )

    # Draw button background
    button_x = (IMAGE_SIZE[0] - BUTTON_SIZE[0]) / 2
    button_y = 400
    draw.rectangle(
        [button_x, button_y, button_x + BUTTON_SIZE[0], button_y + BUTTON_SIZE[1]],
        fill=BUTTON_COLOR
    )

    # Draw button text
    button_text_bbox = draw.textbbox((0, 0), button_text, font=button_font)
    button_text_width, button_text_height = button_text_bbox[2] - button_text_bbox[0], button_text_bbox[3] - button_text_bbox[1]
    draw.text(
        (button_x + (BUTTON_SIZE[0] - button_text_width) / 2, button_y + (BUTTON_SIZE[1] - button_text_height) / 2),
        button_text,
        font=button_font,
        fill=TEXT_COLOR
    )

    # Determine the output path based on language code
    if language_code == "en":
        output_path = script_dir / "../assets/social-media-preview.png"
    else:
        output_path = script_dir / f"../assets/social-media-preview_{language_code}.png"

    # Save image with the determined path
    img.save(output_path)

# Generate images for each translation
for lang_code, translation in translations.items():
    main_text_translated = translation.get("main_text", MAIN_TEXT)
    call_to_action_translated = translation.get("call_to_action", CALL_TO_ACTION_TEXT)
    button_text_translated = translation.get("button_text", BUTTON_TEXT)

    create_image(main_text_translated, call_to_action_translated, button_text_translated, lang_code)

print(f"Images generated in {OUTPUT_DIR}/ for each language.")
