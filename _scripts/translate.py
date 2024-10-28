import openai
from dotenv import load_dotenv
import os
import logging
import argparse

languages = {
    "ar": ("العربية", "🇦🇪", "ar_AE"),
    "bn": ("বাংলা", "🇧🇩", "bn_BD"),
    "cs": ("Čeština", "🇨🇿", "cs_CZ"),
    "de": ("Deutsch", "🇩🇪", "de_DE"),
    "el": ("Ελληνικά", "🇬🇷", "el_GR"),
    "es": ("Español", "🇪🇸", "es_ES"),
    "fa": ("فارسی", "🇮🇷", "fa_IR"),
    "fr": ("Français", "🇫🇷", "fr_FR"),
    "he": ("עברית", "🇮🇱", "he_IL"),
    "hi": ("हिन्दी", "🇮🇳", "hi_IN"),
    "hu": ("Magyar", "🇭🇺", "hu_HU"),
    "id": ("Bahasa Indonesia", "🇮🇩", "id_ID"),
    "it": ("Italiano", "🇮🇹", "it_IT"),
    "ja": ("日本語", "🇯🇵", "ja_JP"),
    "ko": ("한국어", "🇰🇷", "ko_KR"),
    "ms": ("Bahasa Melayu", "🇲🇾", "ms_MY"),
    "nl": ("Nederlands", "🇳🇱", "nl_NL"),
    "pl": ("Polski", "🇵🇱", "pl_PL"),
    "pt-br": ("Português (Brasil)", "🇧🇷", "pt_BR"),
    "ro": ("Română", "🇷🇴", "ro_RO"),
    "ru": ("Русский", "🇷🇺", "ru_RU"),
    "sr": ("Српски", "🇷🇸", "sr_RS"),
    "sv": ("Svenska", "🇸🇪", "sv_SE"),
    "ta": ("தமிழ்", "🇮🇳", "ta_IN"),
    "th": ("ไทย", "🇹🇭", "th_TH"),
    "tl": ("Tagalog", "🇵🇭", "tl_PH"),
    "tr": ("Türkçe", "🇹🇷", "tr_TR"),
    "uk": ("Українська", "🇺🇦", "uk_UA"),
    "vi": ("Tiếng Việt", "🇻🇳", "vi_VN"),
    "zh-cn": ("简体中文", "🇨🇳", "zh_CN")
}

def translate_file(file_path: str, target_language: str, client: openai.AzureOpenAI) -> str:
    """Translate the content of a file to the target language."""
    with open(file_path, "r") as f:
        content = f.read()
    
    system_prompt = f"""
    You are a professional translator. Translate the following content to {languages[target_language][0]}.
    """
    
    user_prompt = content
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={ "type": "text" }
    )
    
    return response.choices[0].message.content

def save_translated_file(content: str, file_name: str):
    """Save the translated content to a file."""
    with open(file_name, "w") as f:
        f.write(content)

def generate_translation_links():
    """Generate HTML links for translations with correct flags."""
    translation_links = []
    for code, (name, flag, locale) in languages.items():
        translation_links.append(f'<a class="translation" href="/index-{code}.html">{flag}</a>')
    return "\n".join(translation_links)

def update_readme_flag_list(readme_path: str):
    """Update the README file with the new flag list."""
    with open(readme_path, "r") as f:
        content = f.read()
    
    # Generate the new flag list using the correct flags
    flag_list = generate_translation_links()
    
    # Replace the __TRANSLATIONS__ token with the new flag list
    updated_content = content.replace("__TRANSLATIONS__", flag_list)
    
    with open(readme_path, "w") as f:
        f.write(updated_content)

def update_locale_in_metadata(file_path, new_locale):
    """Update the locale in the metadata of a markdown file."""
    with open(file_path, "r") as file:
        lines = file.readlines()

    # Debug: Print the file being processed
    print(f"Processing file: {file_path}")

    # Update the locale in the front matter
    for i, line in enumerate(lines):
        if line.startswith("locale:"):
            # Debug: Print the old and new locale
            print(f"Old locale: {line.strip()}")
            lines[i] = f"locale: {new_locale}\n"
            print(f"New locale: {lines[i].strip()}")
            break

    with open(file_path, "w") as file:
        file.writelines(lines)

def process_translation_files(directory):
    """Process each translation file to update the locale."""
    for code, (name, flag, locale) in languages.items():
        file_path = os.path.join(directory, f"index_{code}.md")
        if os.path.exists(file_path):
            update_locale_in_metadata(file_path, locale)
        else:
            # Debug: Print a warning if the file does not exist
            print(f"Warning: File not found for language code '{code}'")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Translate files to different languages.")
    parser.add_argument(
        "translate_target",
        choices=["index", "readme", "both"],
        default="index",
        help="Specify which files to translate: 'index', 'readme', or 'both'."
    )
    args = parser.parse_args()

    # Set up logging to console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Load environment variables from .env file in the parent directory
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    
    # Initialize OpenAI client
    client = openai.AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version="2024-02-15-preview"
    )
    
    # Determine which files to translate based on the command line argument
    translate_target = args.translate_target.lower()
    
    total_languages = len(languages)
    for index, (lang_code, lang_name) in enumerate(languages.items(), start=1):
        if translate_target in ["readme", "both"]:
            logging.info(f"Translating README to {lang_name[0]} ({index}/{total_languages})...")
            translated_content = translate_file("README.md", lang_code, client)
            save_translated_file(translated_content, f"README_{lang_code.upper()}.md")
            logging.info(f"Saved translated README for {lang_name[0]}")

        if translate_target in ["index", "both"]:
            logging.info(f"Translating index.md to {lang_name[0]} ({index}/{total_languages})...")
            translated_content = translate_file("index.md", lang_code, client)
            save_translated_file(translated_content, f"_translations/index_{lang_code}.md")
            logging.info(f"Saved translated index for {lang_name[0]}")

    # Update the README flag list
    update_readme_flag_list("README.md")

    # Process translation files
    process_translation_files("_translations")

if __name__ == "__main__":
    main()
