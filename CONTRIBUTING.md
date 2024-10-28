# Contributing

## Adding translations

To translate the letter, copy `index.md` into `_translations/`
and name it `index_lang.md` where `lang` is language code you are going to translate into.

Make sure to set `locale` to the appropriate language code. Set `image` to a translated version of social-media-preview.png, if there's any. Then you can start translating this file.

For example: `_translations/index_de.md`

```md
---
layout: signed
title: A community statement supporting the Open Source Definition (OSD)
description: A statement from the community in support of the Open Source Definition (OSD) version 1.9
image: /assets/social-media-preview.png
locale: en_US
twitter:
  card: summary_large_image
---

2024-10-28

Dear Open Source Friends & Allies,
```

If you're lost, be sure to check out how its done in existing translations.

When you translated the text you can commit your change and make pull request.
