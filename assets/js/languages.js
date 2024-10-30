document.addEventListener("DOMContentLoaded", function() {
    fetch('/assets/data/languages.json')
        .then(response => response.json())
        .then(languages => {
            const userLang = (navigator.language || navigator.userLanguage);
            const normalizedUserLang = userLang.toLowerCase().replace(/-[a-z]+$/, match => match.toUpperCase());
            const cookieLang = getCookie('preferredLanguage');

            if (cookieLang && languages[cookieLang]) {
                redirectToLanguage(cookieLang);
            } else if (!cookieLang) {
                if (languages[normalizedUserLang]) {
                    setCookie('preferredLanguage', normalizedUserLang, 30);
                    redirectToLanguage(normalizedUserLang);
                } else {
                    setCookie('preferredLanguage', 'en-US', 30);
                    redirectToLanguage('en-US');
                }
            }
        });

    document.querySelectorAll('.translation').forEach(link => {
        link.addEventListener('click', function(event) {
            const hrefParts = this.getAttribute('href').split('-');
            const fullLocale = `${hrefParts[1]}-${hrefParts[2].split('.')[0]}`;
            setCookie('preferredLanguage', fullLocale, 30);
            redirectToLanguage(fullLocale);
        });
    });

    function redirectToLanguage(lang) {
        const currentPath = window.location.pathname;
        const newPath = `/index-${lang.toLowerCase()}.html`;
        if (currentPath !== newPath) {
            window.location.href = newPath;
        }
    }

    function setCookie(name, value, days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        const expires = `expires=${date.toUTCString()}`;
        document.cookie = `${name}=${value};${expires};path=/;SameSite=Lax`;
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
    }
});
