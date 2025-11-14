# CSS Optimizer

A Python tool that scans HTML and CSS files, identifies actually used styles, and creates optimized output in three different formats: external CSS files, embedded `<style>` tags, or inline styles (perfect for email newsletters).

## Features

- **Smart CSS Extraction**: Identifies only the CSS rules actually used in your HTML
- **Multiple Output Modes**:
  - `external`: Single optimized CSS file with updated HTML references
  - `style-tag`: Embedded `<style>` tags in each HTML file
  - `inline`: All styles as inline attributes (ideal for email newsletters)
- **CSS Specificity Support**: Properly handles CSS cascade and specificity rules
- **Comprehensive Selector Support**: Works with classes, IDs, elements, pseudo-classes, pseudo-elements (::before, ::after), attributes, and more
- **@media Query Support**: Fully preserves responsive design with @media queries (external and style-tag modes)
- **Pseudo-element Support**: Handles ::before, ::after, ::first-line, ::first-letter, and other pseudo-elements
- **@font-face Support**: Preserves font declarations
- **External CDN Preservation**: Keeps external font links (Google Fonts, etc.) intact
- **Resource Management**: Automatically copies non-HTML/CSS files and maintains proper references
- **Multi-file Processing**: Handles multiple HTML files in a single pass
- **Safe**: Never modifies original files - all output goes to a separate directory

## Installation

1. Ensure you have Python 3.8 or higher installed:
```bash
python3 --version
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make the script executable (optional):
```bash
chmod +x css_optimizer.py
```

## Usage

### Basic Syntax

```bash
python3 css_optimizer.py -i <input_dir> -o <output_dir> --mode <mode>
```

### Parameters

- `-i`, `--input`: Input directory containing HTML and CSS files (required)
- `-o`, `--output`: Output directory for processed files (required)
- `--mode`: Output format (required)
  - `external`: Generate a single CSS file per HTML file
  - `style-tag`: Embed styles in `<style>` tags within HTML
  - `inline`: Convert all styles to inline attributes

### Examples

#### 1. Generate External CSS Files
Perfect for standard websites:
```bash
python3 css_optimizer.py -i ./source -o ./dist --mode external
```

This will:
- Create optimized `.css` files
- Update HTML to reference these files
- Remove unused CSS rules

#### 2. Embed Styles in `<style>` Tags
Useful for single-file distribution:
```bash
python3 css_optimizer.py -i ./source -o ./dist --mode style-tag
```

This will:
- Embed optimized CSS in `<style>` tags in the HTML `<head>`
- Remove external CSS references
- Remove inline styles

#### 3. Inline All Styles
Ideal for email newsletters:
```bash
python3 css_optimizer.py -i ./newsletter -o ./newsletter-output --mode inline
```

This will:
- Convert all CSS to inline `style` attributes
- Remove all `<style>` tags and external CSS references
- Ensure maximum email client compatibility

## How It Works

1. **Scanning**: Recursively scans the input directory for HTML, CSS, and other files
2. **CSS Collection**: Gathers CSS from:
   - External `.css` files
   - `<style>` tags in HTML
   - Inline `style` attributes
3. **Usage Analysis**: Identifies which CSS rules are actually used by elements in the HTML
4. **Specificity Calculation**: Respects CSS specificity and cascade rules
5. **Style Computation**: Calculates the final computed styles for each element
6. **Output Generation**: Produces optimized output in the requested format
7. **Resource Copying**: Copies all non-HTML/CSS files (images, fonts, etc.) to maintain functionality

## Project Structure

```
input-dir/
├── index.html
├── about.html
├── styles/
│   ├── main.css
│   └── theme.css
├── images/
│   └── logo.png
└── fonts/
    └── custom-font.woff2

output-dir/
├── index.html          # Optimized
├── index.css           # (if mode=external)
├── about.html          # Optimized
├── about.css           # (if mode=external)
├── images/
│   └── logo.png        # Copied
└── fonts/
    └── custom-font.woff2  # Copied
```

## CSS Feature Support

### ✅ Supported
- All CSS selectors (class, ID, element, attribute, pseudo-classes)
- **Pseudo-elements** (::before, ::after, ::first-line, ::first-letter, etc.)
- **@media queries** (fully preserved in external and style-tag modes)
- CSS specificity and cascade
- `@font-face` rules
- External stylesheets
- **External CDN links preserved** (Google Fonts, etc.)
- `<style>` tags
- Inline styles
- Multiple HTML files
- Nested directories

### ❌ Not Supported
- CSS variables (custom properties)
- `@keyframes` animations
- `@import` statements (use external files instead)

### ⚠️ Important Notes
- **@media queries**: Cannot be inlined in `inline` mode (media queries are CSS-only and don't work as inline styles)
- **Pseudo-elements**: Cannot be inlined in `inline` mode (::before, ::after, etc. are virtual elements)
- For email newsletters needing responsive design, use `external` or `style-tag` mode instead of `inline`

## Tips for Email Newsletters

When using `--mode inline` for email newsletters:

1. **Test thoroughly**: Different email clients have varying CSS support
2. **Keep it simple**: Stick to basic CSS properties for maximum compatibility
3. **Avoid pseudo-classes**: Most email clients don't support `:hover`, `:focus`, etc.
4. **Use tables for layout**: Inline styles work best with table-based layouts in emails
5. **Test tools**: Use services like Litmus or Email on Acid to test across clients

## Troubleshooting

### "No HTML files found"
- Ensure your input directory contains `.html` files
- Check that the path is correct

### "CSS parsing error"
- Some complex or invalid CSS might not parse correctly
- Check your CSS for syntax errors
- The tool will warn you and continue processing

### "Output looks different"
- Ensure all CSS files are in the input directory
- Check that selectors match actual HTML elements
- Verify that `@font-face` declarations are complete

## Requirements

- Python 3.8+
- beautifulsoup4 >= 4.9.3
- cssutils >= 2.3.0
- lxml >= 4.6.3

## License

MIT License - feel free to use in your projects!

## Contributing

Contributions welcome! Please ensure:
- Code follows PEP 8 style guidelines
- All features are documented
- Test with various HTML/CSS combinations

## Support

For issues or questions, please open an issue on the project repository.
