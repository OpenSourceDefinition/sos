import openai
from dotenv import load_dotenv
import os
import logging
import argparse

languages = {
    "es": "Español",
    "zh-cn": "简体中文",
    "hi": "हिन्दी",
    "fr": "Français",
    "de": "Deutsch",
    "ru": "Русский",
    "pt-br": "Português (Brasil)",
    "ja": "日本語",
    "ar": "العربية",
    "ko": "한국어",
    "it": "Italiano",
    "tr": "Türkçe",
    "nl": "Nederlands",
    "vi": "Tiếng Việt",
    "id": "Bahasa Indonesia",
    "th": "ไทย",
    "pl": "Polski",
    "sv": "Svenska",
    "uk": "Українська",
    "he": "עברית",
    "fa": "فارسی",
    "tl": "Tagalog",
    "ms": "Bahasa Melayu",
    "ro": "Română",
    "cs": "Čeština",
    "hu": "Magyar",
    "el": "Ελληνικά",
    "bn": "বাংলা",
    "ta": "தமிழ்",
    "sr": "Српски"
}

def translate_file(file_path: str, target_language: str, client: openai.AzureOpenAI) -> str:
    """Translate the content of a file to the target language."""
    with open(file_path, "r") as f:
        content = f.read()
    
    system_prompt = f"""
    You are a professional translator. Translate the following content to {languages[target_language]}.
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

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='translate.log'
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
    
    for lang_code, lang_name in languages.items():
        if translate_target in ["readme", "both"]:
            logging.info(f"Translating README to {lang_name}...")
            translated_content = translate_file("README.md", lang_code, client)
            save_translated_file(translated_content, f"README_{lang_code.upper()}.md")
            logging.info(f"Saved translated README for {lang_name}")

        if translate_target in ["index", "both"]:
            logging.info(f"Translating index.md to {lang_name}...")
            translated_content = translate_file("_translations/index.md", lang_code, client)
            save_translated_file(translated_content, f"_translations/index_{lang_code}.md")
            logging.info(f"Saved translated index for {lang_name}")

if __name__ == "__main__":
    main()
