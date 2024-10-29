#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import cairosvg
import io
import textwrap

# Load configuration from JSON file
config_path = Path(__file__).resolve().parent.parent / 'config.json'
with config_path.open('r', encoding='utf-8') as f:
    config = json.load(f)

# Load languages from JSON file
languages_path = Path(__file__).resolve().parent.parent / '_data' / 'languages.json'
with languages_path.open('r', encoding='utf-8') as f:
    languages = json.load(f)

# Determine the script's directory
script_dir = Path(__file__).resolve().parent

# Constants
base_dir = script_dir.parent
assets_dir = base_dir / config['directories']['assets']
fonts_dir = assets_dir / "fonts"
BUTTON_COLOR = (0, 178, 89)
TEXT_COLOR = (255, 255, 255)
IMAGE_SIZE = (1280, 640)
BUTTON_SIZE = (300, 70)

# Create output directory
assets_dir.mkdir(exist_ok=True)

# Load the new background image
background_path = assets_dir / "background.jpg"
background_image = Image.open(background_path).convert("RGBA")

# Convert SVG to PNG
def convert_svg_to_png(svg_path):
    with open(svg_path, 'rb') as svg_file:
        svg_data = svg_file.read()
    png_data = cairosvg.svg2png(bytestring=svg_data)
    return Image.open(io.BytesIO(png_data))

# Use the function to open the logo
logo_path = assets_dir / "logo.svg"
logo_image = convert_svg_to_png(logo_path).convert("RGBA")

# Resize logo while maintaining aspect ratio
def resize_logo(image, scale_factor, max_width, max_height):
    new_width = int(image.width * scale_factor)
    new_height = int(image.height * scale_factor)
    
    if new_width > max_width or new_height > max_height:
        aspect_ratio = image.width / image.height
        if new_width > new_height:
            new_width = min(max_width, new_width)
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = min(max_height, new_height)
            new_width = int(new_height * aspect_ratio)
    
    return image.resize((new_width, new_height), Image.LANCZOS)

# Resize and position the logo
scale_factor = 2
logo_size = (500, 500)
logo_image = resize_logo(logo_image, scale_factor, *logo_size)
logo_position = (background_image.width - logo_image.width + 20, -20)

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
def create_image(text_main, text_call_to_action, button_text, language_code, font_file):
    # Print the font path to verify
    font_path = fonts_dir / font_file

    img = background_image.copy()
    draw = ImageDraw.Draw(img)

    # Load the fonts for the specific language
    main_font = ImageFont.truetype(str(font_path), 62)
    button_font = ImageFont.truetype(str(font_path), 40)
    cta_font = ImageFont.truetype(str(font_path), 30)

    # Paste the logo
    img.paste(logo_image, logo_position, logo_image)

    # Draw additional text in top left
    draw.text(
        (20, 20),
        text_call_to_action.upper(),
        font=cta_font,
        fill=TEXT_COLOR
    )

    # Draw the main title text, wrapping to fit and increase size
    text_main_wrapped = "\n".join(textwrap.wrap(text_main, width=30))
    draw.text(
        (40, logo_image.height - 10),
        text_main_wrapped,
        font=main_font,
        fill=TEXT_COLOR
    )

    # Adjust button size and position
    button_size = (500, 120)
    button_position = (background_image.width - button_size[0] - 80, background_image.height - button_size[1] - 80)

    # Draw the pill-shaped button
    draw.rounded_rectangle(
        [button_position, (button_position[0] + button_size[0], button_position[1] + button_size[1])],
        radius=70,
        fill=BUTTON_COLOR
    )

    # Draw button text
    text_bbox = draw.textbbox((0, 0), button_text, font=button_font)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    draw.text(
        (button_position[0] + (button_size[0] - text_width) / 2, button_position[1] + (button_size[1] - text_height) / 2),
        button_text,
        font=button_font,
        fill="white"
    )

    # Determine the output path based on language code
    if language_code == "":
        output_path = assets_dir / "social-media-preview.png"
    else:
        output_path = assets_dir / f"social-media-preview-{language_code}.png"

    # Save image with the determined path
    img.save(output_path)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Generate images with translated texts.")
    parser.add_argument(
        "--languages",
        nargs='*',
        help="Specify languages to generate images for (e.g., 'fr-FR', 'en-US'). Use 'all' to generate for all languages including default."
    )
    args = parser.parse_args()

    if not args.languages:
        print("Usage: python image.py --languages <language_codes>")
        print("Available languages:")
        print("  all: Generate images for all languages including the default.")
        print("  default: Generate image using default texts from config.json.")
        for lang_code, (lang_name, _, _) in languages.items():
            print(f"  {lang_code}: {lang_name}")
        return

    selected_languages = args.languages

    if "all" in selected_languages:
        selected_languages = list(languages.keys()) + [""]

    # Add handling for "default" language
    if "default" in selected_languages:
        selected_languages.remove("default")
        selected_languages.append("")

    # Generate images for each translation
    for lang_code in selected_languages:
        print(f"Generating image for language: {lang_code if lang_code else 'default'}")

        if lang_code == "":
            # Use default texts from config.json for the default language
            main_text_translated = config['images']['main_text']
            call_to_action_translated = config['images']['call_to_action_text']
            button_text_translated = config['images']['button_text']
            font_file = config['images']['font_file']
            font_path = fonts_dir / font_file
        else:
            translation_file = script_dir.parent / config['directories']['translations'] / f"image-{lang_code}.json"
            if not translation_file.exists():
                print(f"Warning: Translation file for {lang_code} not found. Skipping.")
                continue

            with translation_file.open("r", encoding="utf-8") as file:
                translation = json.load(file)

            main_text_translated = translation.get("main_text", config['images']['main_text'])
            call_to_action_translated = translation.get("call_to_action_text", config['images']['call_to_action_text'])
            button_text_translated = translation.get("button_text", config['images']['button_text'])

            # Get the font path from languages.json
            font_file = languages[lang_code][2]

        create_image(main_text_translated, call_to_action_translated, button_text_translated, lang_code, font_file)

    print(f"Images generated in {assets_dir} for each language.")

if __name__ == "__main__":
    main()
