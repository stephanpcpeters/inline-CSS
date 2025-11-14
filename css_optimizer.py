#!/usr/bin/env python3
"""
CSS Optimizer Tool
Scans HTML and CSS files, identifies used styles, and outputs optimized versions
in three formats: external CSS, style tags, or inline styles.
"""

import argparse
import os
import shutil
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import cssutils
from bs4 import BeautifulSoup, Tag
import logging

# Suppress cssutils warnings
cssutils.log.setLevel(logging.CRITICAL)


class CSSRule:
    """Represents a CSS rule with selector and declarations"""
    def __init__(self, selector: str, declarations: Dict[str, str], specificity: Tuple[int, int, int, int]):
        self.selector = selector
        self.declarations = declarations
        self.specificity = specificity

    def __repr__(self):
        return f"CSSRule({self.selector}, specificity={self.specificity})"


class CSSParser:
    """Parses CSS from various sources and extracts rules"""

    @staticmethod
    def calculate_specificity(selector: str) -> Tuple[int, int, int, int]:
        """
        Calculate CSS specificity: (inline, ids, classes/attributes/pseudo-classes, elements)
        Returns tuple of (0, id_count, class_count, element_count) for regular selectors
        """
        # Remove pseudo-elements for specificity calculation
        selector = re.sub(r'::(before|after|first-line|first-letter)', '', selector)

        # Count IDs
        id_count = len(re.findall(r'#[\w-]+', selector))

        # Count classes, attributes, and pseudo-classes
        class_count = len(re.findall(r'\.[\w-]+', selector))
        attr_count = len(re.findall(r'\[[^\]]+\]', selector))
        pseudo_class_count = len(re.findall(r':[\w-]+(?:\([^)]*\))?', selector))
        class_count += attr_count + pseudo_class_count

        # Count elements and pseudo-elements
        # Remove IDs, classes, attributes first
        temp = re.sub(r'#[\w-]+', '', selector)
        temp = re.sub(r'\.[\w-]+', '', temp)
        temp = re.sub(r'\[[^\]]+\]', '', temp)
        temp = re.sub(r':[\w-]+(?:\([^)]*\))?', '', temp)
        # Count remaining element names
        element_count = len(re.findall(r'\b[a-z][\w-]*\b', temp, re.IGNORECASE))

        return (0, id_count, class_count, element_count)

    @staticmethod
    def parse_css_string(css_text: str) -> List[CSSRule]:
        """Parse CSS string and return list of CSSRule objects"""
        rules = []
        try:
            sheet = cssutils.parseString(css_text)
            for rule in sheet:
                if rule.type == rule.STYLE_RULE:
                    # Handle multiple selectors
                    selector_list = rule.selectorText.split(',')
                    declarations = {}
                    for prop in rule.style:
                        declarations[prop.name] = prop.value

                    for selector in selector_list:
                        selector = selector.strip()
                        specificity = CSSParser.calculate_specificity(selector)
                        rules.append(CSSRule(selector, declarations.copy(), specificity))

                elif rule.type == rule.FONT_FACE_RULE:
                    # Handle @font-face specially
                    declarations = {}
                    for prop in rule.style:
                        declarations[prop.name] = prop.value
                    rules.append(CSSRule('@font-face', declarations, (0, 0, 0, 0)))
        except Exception as e:
            print(f"Warning: CSS parsing error: {e}")

        return rules

    @staticmethod
    def parse_inline_style(style_attr: str) -> Dict[str, str]:
        """Parse inline style attribute and return declarations dict"""
        declarations = {}
        if not style_attr:
            return declarations

        try:
            style = cssutils.parseStyle(style_attr)
            for prop in style:
                declarations[prop.name] = prop.value
        except Exception:
            # Fallback to simple parsing
            for decl in style_attr.split(';'):
                if ':' in decl:
                    prop, value = decl.split(':', 1)
                    declarations[prop.strip()] = value.strip()

        return declarations


class HTMLProcessor:
    """Processes HTML files and identifies used CSS"""

    def __init__(self, html_path: Path):
        self.html_path = html_path
        with open(html_path, 'r', encoding='utf-8') as f:
            self.soup = BeautifulSoup(f.read(), 'html.parser')
        self.used_selectors: Set[str] = set()
        self.element_styles: Dict[Tag, Dict[str, str]] = {}

    def extract_internal_css(self) -> List[CSSRule]:
        """Extract CSS rules from <style> tags"""
        rules = []
        for style_tag in self.soup.find_all('style'):
            css_text = style_tag.string or ''
            rules.extend(CSSParser.parse_css_string(css_text))
        return rules

    def extract_external_css_refs(self) -> List[str]:
        """Extract external CSS file references"""
        refs = []
        for link in self.soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                refs.append(href)
        return refs

    def get_all_elements(self) -> List[Tag]:
        """Get all HTML elements (tags) from the document"""
        return self.soup.find_all(True)  # True matches all tags

    def element_matches_selector(self, element: Tag, selector: str) -> bool:
        """Check if an element matches a CSS selector"""
        try:
            # Use BeautifulSoup's CSS selector matching
            matches = self.soup.select(selector)
            return element in matches
        except Exception:
            return False

    def identify_used_selectors(self, all_rules: List[CSSRule]) -> List[CSSRule]:
        """Identify which CSS rules are actually used in the HTML"""
        used_rules = []

        # Always include @font-face rules
        for rule in all_rules:
            if rule.selector == '@font-face':
                used_rules.append(rule)

        # Check regular selectors
        for rule in all_rules:
            if rule.selector == '@font-face':
                continue

            # Check if any element matches this selector
            try:
                if self.soup.select(rule.selector):
                    used_rules.append(rule)
                    self.used_selectors.add(rule.selector)
            except Exception:
                # If selector is invalid, skip it
                pass

        return used_rules

    def compute_element_styles(self, used_rules: List[CSSRule]):
        """Compute final styles for each element respecting specificity and cascade"""
        elements = self.get_all_elements()

        for element in elements:
            # Collect all rules that apply to this element
            applicable_rules = []

            for rule in used_rules:
                if rule.selector == '@font-face':
                    continue
                if self.element_matches_selector(element, rule.selector):
                    applicable_rules.append(rule)

            # Sort by specificity (lowest to highest)
            applicable_rules.sort(key=lambda r: r.specificity)

            # Apply rules in order (cascade)
            final_styles = {}
            for rule in applicable_rules:
                final_styles.update(rule.declarations)

            # Apply inline styles (highest specificity)
            inline_style = element.get('style', '')
            if inline_style:
                inline_declarations = CSSParser.parse_inline_style(inline_style)
                final_styles.update(inline_declarations)

            if final_styles:
                self.element_styles[element] = final_styles


class StyleOptimizer:
    """Main optimizer that coordinates the CSS optimization process"""

    def __init__(self, input_dir: Path, output_dir: Path, mode: str):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.mode = mode
        self.all_css_rules: List[CSSRule] = []
        self.html_files: List[Path] = []
        self.css_files: List[Path] = []
        self.other_files: List[Path] = []

    def scan_input_directory(self):
        """Scan input directory for HTML, CSS, and other files"""
        for item in self.input_dir.rglob('*'):
            if item.is_file():
                if item.suffix.lower() == '.html':
                    self.html_files.append(item)
                elif item.suffix.lower() == '.css':
                    self.css_files.append(item)
                else:
                    self.other_files.append(item)

    def load_all_css(self):
        """Load all CSS from external files"""
        for css_file in self.css_files:
            try:
                with open(css_file, 'r', encoding='utf-8') as f:
                    css_text = f.read()
                rules = CSSParser.parse_css_string(css_text)
                self.all_css_rules.extend(rules)
            except Exception as e:
                print(f"Warning: Could not read {css_file}: {e}")

    def process_html_file(self, html_path: Path) -> Tuple[HTMLProcessor, List[CSSRule]]:
        """Process a single HTML file"""
        processor = HTMLProcessor(html_path)

        # Extract internal CSS
        internal_rules = processor.extract_internal_css()

        # Combine with external CSS
        all_rules = self.all_css_rules + internal_rules

        # Identify used rules
        used_rules = processor.identify_used_selectors(all_rules)

        # Compute final styles for each element (only needed for inline mode)
        if self.mode == 'inline':
            processor.compute_element_styles(used_rules)

        return processor, used_rules

    def generate_output_external(self, processor: HTMLProcessor, used_rules: List[CSSRule], output_html_path: Path):
        """Generate output with external CSS file"""
        # Create CSS file content from used rules
        css_content = []

        # Add font-face rules first
        for rule in used_rules:
            if rule.selector == '@font-face':
                css_content.append('@font-face {')
                for prop, value in rule.declarations.items():
                    css_content.append(f'  {prop}: {value};')
                css_content.append('}')
                css_content.append('')

        # Add regular rules
        for rule in used_rules:
            if rule.selector != '@font-face':
                css_content.append(f'{rule.selector} {{')
                for prop, value in rule.declarations.items():
                    css_content.append(f'  {prop}: {value};')
                css_content.append('}')
                css_content.append('')

        # Write CSS file
        css_filename = output_html_path.stem + '.css'
        css_path = output_html_path.parent / css_filename
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(css_content))

        # Modify HTML to reference the CSS file
        soup = processor.soup

        # Remove existing style tags and external CSS links
        for tag in soup.find_all('style'):
            tag.decompose()
        for tag in soup.find_all('link', rel='stylesheet'):
            tag.decompose()

        # Remove inline styles
        for element in soup.find_all(style=True):
            del element['style']

        # Add new CSS link in head
        head = soup.find('head')
        if not head:
            head = soup.new_tag('head')
            if soup.html:
                soup.html.insert(0, head)
            else:
                soup.insert(0, head)

        link_tag = soup.new_tag('link', rel='stylesheet', href=css_filename)
        head.append(link_tag)

        # Write HTML file
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))

    def generate_output_style_tag(self, processor: HTMLProcessor, used_rules: List[CSSRule], output_html_path: Path):
        """Generate output with <style> tag in HTML"""
        # Build CSS content from used rules
        css_lines = []

        # Add font-face rules first
        for rule in used_rules:
            if rule.selector == '@font-face':
                css_lines.append('@font-face {')
                for prop, value in rule.declarations.items():
                    css_lines.append(f'  {prop}: {value};')
                css_lines.append('}')
                css_lines.append('')

        # Add regular rules
        for rule in used_rules:
            if rule.selector != '@font-face':
                css_lines.append(f'{rule.selector} {{')
                for prop, value in rule.declarations.items():
                    css_lines.append(f'  {prop}: {value};')
                css_lines.append('}')

        css_text = '\n'.join(css_lines)

        # Modify HTML
        soup = processor.soup

        # Remove existing style tags and external CSS links
        for tag in soup.find_all('style'):
            tag.decompose()
        for tag in soup.find_all('link', rel='stylesheet'):
            tag.decompose()

        # Remove inline styles
        for element in soup.find_all(style=True):
            del element['style']

        # Add new style tag in head
        head = soup.find('head')
        if not head:
            head = soup.new_tag('head')
            if soup.html:
                soup.html.insert(0, head)
            else:
                soup.insert(0, head)

        style_tag = soup.new_tag('style')
        style_tag.string = '\n' + css_text + '\n'
        head.append(style_tag)

        # Write HTML file
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))

    def generate_output_inline(self, processor: HTMLProcessor, output_html_path: Path):
        """Generate output with inline styles only"""
        soup = processor.soup

        # Remove existing style tags and external CSS links
        for tag in soup.find_all('style'):
            tag.decompose()
        for tag in soup.find_all('link', rel='stylesheet'):
            tag.decompose()

        # Apply computed styles as inline styles
        for element, styles in processor.element_styles.items():
            if isinstance(element, Tag) and styles:
                style_parts = [f'{prop}: {value}' for prop, value in sorted(styles.items())]
                element['style'] = '; '.join(style_parts)

        # Write HTML file
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))

    def _create_selector_for_element(self, element: Tag) -> Optional[str]:
        """Create a CSS selector for an element based on its attributes"""
        # Prefer ID
        if element.get('id'):
            return f"#{element['id']}"

        # Then class
        if element.get('class'):
            classes = ' '.join(element['class'])
            return f".{element['class'][0]}"

        # Fall back to element name
        return element.name

    def copy_resources(self):
        """Copy non-HTML/CSS files to output directory"""
        for file_path in self.other_files:
            rel_path = file_path.relative_to(self.input_dir)
            output_path = self.output_dir / rel_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, output_path)

    def optimize(self):
        """Main optimization process"""
        print(f"Scanning input directory: {self.input_dir}")
        self.scan_input_directory()

        print(f"Found {len(self.html_files)} HTML files")
        print(f"Found {len(self.css_files)} CSS files")
        print(f"Found {len(self.other_files)} other files")

        # Load all CSS
        print("Loading CSS files...")
        self.load_all_css()
        print(f"Loaded {len(self.all_css_rules)} CSS rules")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Process each HTML file
        for html_file in self.html_files:
            print(f"\nProcessing: {html_file.name}")
            processor, used_rules = self.process_html_file(html_file)

            # Generate output based on mode
            rel_path = html_file.relative_to(self.input_dir)
            output_path = self.output_dir / rel_path
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if self.mode == 'external':
                self.generate_output_external(processor, used_rules, output_path)
            elif self.mode == 'style-tag':
                self.generate_output_style_tag(processor, used_rules, output_path)
            elif self.mode == 'inline':
                self.generate_output_inline(processor, output_path)

            print(f"  → Output: {output_path}")

        # Copy other resources
        print("\nCopying resource files...")
        self.copy_resources()

        print(f"\n✓ Optimization complete! Output in: {self.output_dir}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='CSS Optimizer - Extract and optimize CSS from HTML files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate external CSS file
  %(prog)s -i ./input -o ./output --mode external

  # Embed styles in <style> tags
  %(prog)s -i ./input -o ./output --mode style-tag

  # Inline all styles (for email newsletters)
  %(prog)s -i ./input -o ./output --mode inline
        """
    )

    parser.add_argument('-i', '--input', type=str, required=True,
                       help='Input directory containing HTML and CSS files')
    parser.add_argument('-o', '--output', type=str, required=True,
                       help='Output directory for processed files')
    parser.add_argument('--mode', type=str, required=True,
                       choices=['external', 'style-tag', 'inline'],
                       help='Output mode: external (CSS file), style-tag (<style> in HTML), or inline (inline styles)')

    args = parser.parse_args()

    # Validate paths
    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        return 1

    if not input_dir.is_dir():
        print(f"Error: Input path is not a directory: {input_dir}")
        return 1

    # Run optimization
    optimizer = StyleOptimizer(input_dir, output_dir, args.mode)
    optimizer.optimize()

    return 0


if __name__ == '__main__':
    exit(main())
