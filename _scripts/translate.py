import openai
from dotenv import load_dotenv
import os
import logging
import argparse

languages = {
    "ar": ("العربية", "🇦🇪"),
    "bn": ("বাংলা", "🇧🇩"),
    "cs": ("Čeština", "🇨🇿"),
    "de": ("Deutsch", "🇩🇪"),
    "el": ("Ελληνικά", "🇬🇷"),
    "es": ("Español", "🇪🇸"),
    "fa": ("فارسی", "🇮🇷"),
    "fr": ("Français", "🇫🇷"),
    "he": ("עברית", "🇮🇱"),
    "hi": ("हिन्दी", "🇮🇳"),
    "hu": ("Magyar", "🇭🇺"),
    "id": ("Bahasa Indonesia", "🇮🇩"),
    "it": ("Italiano", "🇮🇹"),
    "ja": ("日本語", "🇯🇵"),
    "ko": ("한국어", "🇰🇷"),
    "ms": ("Bahasa Melayu", "🇲🇾"),
    "nl": ("Nederlands", "🇳🇱"),
    "pl": ("Polski", "🇵🇱"),
    "pt-br": ("Português (Brasil)", "🇧🇷"),
    "ro": ("Română", "🇷🇴"),
    "ru": ("Русский", "🇷🇺"),
    "sr": ("Српски", "🇷🇸"),
    "sv": ("Svenska", "🇸🇪"),
    "ta": ("தமிழ்", "🇮🇳"),
    "th": ("ไทย", "🇹🇭"),
    "tl": ("Tagalog", "🇵🇭"),
    "tr": ("Türkçe", "🇹🇷"),
    "uk": ("Українська", "🇺🇦"),
    "vi": ("Tiếng Việt", "🇻🇳"),
    "zh-cn": ("简体中文", "🇨🇳")
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

def update_readme_flag_list(readme_path: str):
    """Update the README file with the new flag list."""
    with open(readme_path, "r") as f:
        content = f.read()
    
    # Generate the new flag list
    flag_list = "\n".join(
        f"[{flag}](README_{code.upper()}.md)" for code, (name, flag) in sorted(languages.items(), key=lambda x: x[1][0])
    )
    
    # Replace the __TRANSLATIONS__ token with the new flag list
    updated_content = content.replace("__TRANSLATIONS__", flag_list)
    
    with open(readme_path, "w") as f:
        f.write(updated_content)

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

if __name__ == "__main__":
    main()
