import openai
from dotenv import load_dotenv
import os
import logging
import argparse
import yaml
import json
import sys
import re
from pathlib import Path

# Load configuration from JSON file
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Load languages from JSON file
languages_path = Path(__file__).resolve().parent.parent / '_data' / 'languages.json'
with languages_path.open('r', encoding='utf-8') as f:
    languages = json.load(f)
def translate_texts(texts, target_language, client):
    """Translate a dictionary of texts to the target language."""
    system_prompt = f"""
    You are a professional translator. Translate the following JSON structured data to {languages[target_language][0]}.
    """

    user_prompt = json.dumps(texts)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)

def extract_links(text):
    """Extract links from the text and replace them with placeholders."""
    link_pattern = re.compile(r'(https?://\S+)')
    links = link_pattern.findall(text)
    placeholder_text = text
    for i, link in enumerate(links):
        placeholder = f"__LINK_{i}__"
        placeholder_text = placeholder_text.replace(link, placeholder)
    return placeholder_text, links

def restore_links(translated_text, links):
    """Restore links in the translated text using placeholders."""
    for i, link in enumerate(links):
        placeholder = f"__LINK_{i}__"
        translated_text = translated_text.replace(placeholder, link)
    return translated_text

def translate_file(file_path: str, target_language: str, client: openai.AzureOpenAI) -> str:
    """Translate the title, description, and body of a file to the target language."""
    file_path = Path(file_path)
    with file_path.open("r", encoding="utf-8") as f:
        content = f.read()

    # Check if the content has front matter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) < 3:
            logging.error(f"File {file_path} does not contain the expected front matter format.")
            return ""
        front_matter, body = parts[1:3]
        front_matter_data = yaml.safe_load(front_matter)
    else:
        # No front matter, treat the entire content as body
        front_matter_data = {}
        body = content

    # Extract and replace links in the body
    body_with_placeholders, links = extract_links(body.strip())

    # Prepare structured data for translation
    data_to_translate = {
        "front_matter": {key: front_matter_data[key] for key in ['title', 'description'] if key in front_matter_data},
        "body": body_with_placeholders
    }

    translated_data = translate_texts(data_to_translate, target_language, client)

    # Restore links in the translated body
    translated_body = restore_links(translated_data["body"], links)

    # Update the front matter with translated fields
    for key, value in translated_data["front_matter"].items():
        front_matter_data[key] = value

    # Only add locale if the file has front matter
    if front_matter_data:
        front_matter_data['locale'] = target_language

    # Update image link in front matter
    if 'image' in front_matter_data:
        image_path = Path(front_matter_data['image'])
        new_image_name = f"{image_path.stem}-{target_language}.png"
        front_matter_data['image'] = str(image_path.with_name(new_image_name))

    # Reconstruct the file content
    if front_matter_data:
        translated_front_matter = yaml.dump(front_matter_data, allow_unicode=True)
        return f"---\n{translated_front_matter}---\n{translated_body}"
    else:
        return translated_body

def save_translated_file(content: str, directory: Path, file_name: str):
    """Save the translated content to a specified directory."""
    file_path = directory / file_name
    with file_path.open("w", encoding="utf-8") as f:
        f.write(content)

def translate_image_texts(target_language: str, client: openai.AzureOpenAI):
    """Translate image texts to the target language."""
    image_texts = config['image_fields']
    translated_texts = translate_texts(image_texts, target_language, client)
    return translated_texts

def update_readme_flag_list(readme_content: str) -> str:
    """Update the README content with a list of available language flags."""
    # Define the start and end markers for the language section
    start_marker = "<!-- TRANSLATIONS_START -->"
    end_marker = "<!-- TRANSLATIONS_END -->"

    # Split the content into lines
    readme_lines = readme_content.splitlines(keepends=True)

    # Find the index for the start marker and the end marker
    start_index = None
    end_index = None
    for i, line in enumerate(readme_lines):
        if start_marker in line:
            start_index = i
        elif end_marker in line:
            end_index = i
            break

    if start_index is None or end_index is None:
        logging.warning("Language section markers not found in README.")
        return readme_content

    # Generate the new language section content
    language_section = [f"{start_marker}\n"]
    language_section.append("[🇺🇳](README.md)")  # Add UN flag for the canonical source
    for lang_code, (lang_name, flag) in languages.items():
        language_section.append(f"[{flag}](README_{lang_code}.md)")
    language_section.append(f"\n{end_marker}\n")

    # Replace the old language section with the new one
    readme_lines[start_index:end_index + 1] = language_section

    # Return the updated content
    return ''.join(readme_lines)

def print_usage_and_exit():
    """Print usage information and exit."""
    print("Usage: python translate.py <mode> --languages <language_codes>")
    print("Modes: index, readme, images, all")
    print("Available languages:")
    for lang_code, (lang_name, _) in languages.items():
        print(f"  {lang_code}: {lang_name}")
    sys.exit(1)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Translate files to different languages.")
    parser.add_argument(
        "mode",
        choices=["index", "readme", "images", "all"],
        help="Specify which files to translate: 'index', 'readme', 'images', or 'all'."
    )
    parser.add_argument(
        "--languages",
        nargs='*',
        default=list(languages.keys()),
        help="Specify languages to translate (e.g., 'fr-FR', 'en-US'). Defaults to all languages."
    )

    # Check if no arguments are provided
    if len(sys.argv) == 1:
        print_usage_and_exit()

    args = parser.parse_args()

    # Set up logging to console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Load environment variables from .env file in the parent directory
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
    
    # Initialize OpenAI client
    client = openai.AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version="2024-02-15-preview"
    )
    
    # Determine which files to translate based on the command line argument
    translate_target = args.mode.lower()
    selected_languages = args.languages

    total_languages = len(selected_languages)
    # Calculate the project root directory
    project_root = Path(__file__).resolve().parent.parent
    translations_dir = project_root / '_translations'

    if translate_target in ["readme", "all"]:
        # Update the README.md with the language flags
        readme_path = project_root / "README.md"
        with readme_path.open("r", encoding="utf-8") as f:
            readme_content = f.read()

        updated_readme_content = update_readme_flag_list(readme_content)
        save_translated_file(updated_readme_content, project_root, "README.md")
        logging.info("Updated README.md with language flags.")

    for index, lang_code in enumerate(selected_languages, start=1):
        lang_name = languages.get(lang_code)
        if not lang_name:
            logging.warning(f"Language code '{lang_code}' not recognized.")
            print_usage_and_exit()

        if translate_target in ["readme", "all"]:
            logging.info(f"Translating README to {lang_name[0]} ({lang_code}) ({index}/{total_languages})...")
            translated_content = translate_file("README.md", lang_code, client)
            translated_content = update_readme_flag_list(translated_content)
            save_translated_file(translated_content, project_root, f"README-{lang_code}.md")
            logging.info(f"Saved translated README for {lang_name[0]} ({lang_code})")

        if translate_target in ["index", "all"]:
            logging.info(f"Translating index.md to {lang_name[0]} ({lang_code}) ({index}/{total_languages})...")
            translated_content = translate_file("index.md", lang_code, client)
            save_translated_file(translated_content, translations_dir, f"index-{lang_code}.md")
            logging.info(f"Saved translated index for {lang_name[0]} ({lang_code})")

        if translate_target in ["images", "all"]:
            logging.info(f"Translating image texts to {lang_name[0]} ({lang_code}) ({index}/{total_languages})...")
            translated_image_texts = translate_image_texts(lang_code, client)
            # Save each language's translations in a separate file
            translations_path = Path(config['directories']['translations']) / f"image-{lang_code}.json"
            with translations_path.open("w", encoding='utf-8') as f:
                json.dump(translated_image_texts, f, ensure_ascii=False, indent=4)
            logging.info(f"Saved translated image texts for {lang_name[0]} ({lang_code})")

if __name__ == "__main__":
    main()
