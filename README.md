# Gliphs

Gliphs is for pages where text should look normal in the browser but be less useful when copied, indexed, or scraped. It replaces real characters with Private Use Area codepoints and generates a font that renders those replacements back as readable text.

Demo: https://denisbackenddev.github.io/gliphs/

## Usage

```python
from gliphs.core import generate_docs_files

text = "The text you want to publish"
font_path, text_path = generate_docs_files(text)
```

This creates two files in `docs`:

- `gliphs-demo.ttf`
- `gliphs-demo.txt`

Use the font in the page and render the encoded text from the `.txt` file:

```html
<style>
  @font-face {
    font-family: Gliphs;
    src: url("gliphs-demo.ttf") format("truetype");
  }
</style>

<p style="font-family: Gliphs">encoded text</p>
```

This is obfuscation, not encryption. Anyone with the generated font can reverse the mapping.
