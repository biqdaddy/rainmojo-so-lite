#!/usr/bin/env python3
"""
SEO Content Formatter — Convert Markdown to CMS-ready formats.

Supports WordPress Gutenberg blocks, clean HTML, and Shopify Liquid.
Auto-generates TOC, Schema markup, meta tag suggestions, and FAQ schema.

Note on FAQPage schema: Google restricted FAQ Rich Results to authoritative
government/health sites since Aug 2023. For most sites, FAQPage no longer
triggers Google Rich Results, but AI platforms (ChatGPT, Claude, Perplexity,
Gemini) still parse it to extract Q&A pairs for citation. We emit FAQPage for
AISO benefit, not for Google Rich Results.

Usage:
    python seo_content_formatter.py content.md --format gutenberg
    python seo_content_formatter.py content.md --format html --toc
    python seo_content_formatter.py content.md --format shopify --schema Article
    cat content.md | python seo_content_formatter.py --stdin --format html
    python seo_content_formatter.py content.md --format gutenberg --output formatted.html
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def slugify(text: str) -> str:
    """Create a URL-friendly slug from text, handling Thai and other Unicode."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text or 'section'


def parse_inline(text: str) -> str:
    """Parse inline Markdown elements: bold, italic, code, links, images."""
    # Images: ![alt](src)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" />', text)
    # Links: [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # Bold + italic: ***text*** or ___text___
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'___(.+?)___', r'<strong><em>\1</em></strong>', text)
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    # Italic: *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<em>\1</em>', text)
    # Inline code: `code`
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text


def starts_block(line: str) -> bool:
    """Return True when a non-blank line starts a Markdown block.

    Horizontal rules must match the whole line. The old paragraph look-ahead
    used a prefix regex, so valid inline emphasis such as ``***Important***``
    looked like a horizontal rule without being consumed by the horizontal-rule
    branch. That left the parser index unchanged and caused an infinite loop.
    """
    stripped = line.strip()
    return bool(
        re.match(r'^(#{1,6})\s+', line)
        or stripped.startswith('```')
        or re.match(r'^[\s]*[-*+]\s+', line)
        or re.match(r'^[\s]*\d+[.)]\s+', line)
        or line.startswith('>')
        or re.fullmatch(r'(?:---|\*\*\*|___)', stripped)
    )


def parse_markdown(content: str) -> list:
    """Parse Markdown into a list of block elements."""
    blocks = []
    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Blank line — skip
        if not line.strip():
            i += 1
            continue

        # Code block (fenced)
        if line.strip().startswith('```'):
            lang = line.strip()[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            blocks.append({'type': 'code', 'lang': lang, 'content': '\n'.join(code_lines)})
            continue

        # Heading
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            blocks.append({'type': 'heading', 'level': level, 'text': text, 'id': slugify(text)})
            i += 1
            continue

        # Table
        if '|' in line and i + 1 < len(lines) and re.match(r'^[\s|:-]+$', lines[i + 1]):
            headers = [c.strip() for c in line.strip().strip('|').split('|')]
            i += 2  # skip header and separator
            rows = []
            while i < len(lines) and '|' in lines[i] and lines[i].strip():
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                rows.append(cells)
                i += 1
            blocks.append({'type': 'table', 'headers': headers, 'rows': rows})
            continue

        # Unordered list
        if re.match(r'^[\s]*[-*+]\s+', line):
            items = []
            while i < len(lines) and re.match(r'^[\s]*[-*+]\s+', lines[i]):
                item_text = re.sub(r'^[\s]*[-*+]\s+', '', lines[i])
                items.append(item_text.strip())
                i += 1
            blocks.append({'type': 'ul', 'items': items})
            continue

        # Ordered list
        if re.match(r'^[\s]*\d+[.)]\s+', line):
            items = []
            while i < len(lines) and re.match(r'^[\s]*\d+[.)]\s+', lines[i]):
                item_text = re.sub(r'^[\s]*\d+[.)]\s+', '', lines[i])
                items.append(item_text.strip())
                i += 1
            blocks.append({'type': 'ol', 'items': items})
            continue

        # Image (standalone line)
        img_match = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', line)
        if img_match:
            blocks.append({'type': 'image', 'alt': img_match.group(1), 'src': img_match.group(2)})
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^(---|\*\*\*|___)\s*$', line):
            blocks.append({'type': 'hr'})
            i += 1
            continue

        # Blockquote
        if line.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].startswith('>'):
                quote_lines.append(re.sub(r'^>\s?', '', lines[i]))
                i += 1
            blocks.append({'type': 'blockquote', 'content': '\n'.join(quote_lines)})
            continue

        # Paragraph (collect consecutive non-blank lines)
        para_lines = []
        while i < len(lines) and lines[i].strip() and not starts_block(lines[i]):
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            blocks.append({'type': 'paragraph', 'text': ' '.join(para_lines)})
            continue

        # Defensive progress guarantee for any future block detector mismatch.
        # A parser iteration must always consume at least one input line.
        blocks.append({'type': 'paragraph', 'text': line})
        i += 1

    return blocks


def extract_headings(blocks: list) -> list:
    """Extract heading blocks for TOC generation."""
    return [b for b in blocks if b['type'] == 'heading']


def extract_faq(blocks: list) -> list:
    """Extract FAQ pairs from Q&A patterns (headings with ? or Q:/A: paragraphs)."""
    faqs = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        # Pattern 1: heading ending with ?
        if block['type'] == 'heading' and block['text'].strip().endswith('?'):
            question = block['text'].strip()
            answer_parts = []
            j = i + 1
            while j < len(blocks) and blocks[j]['type'] == 'paragraph':
                answer_parts.append(blocks[j]['text'])
                j += 1
            if answer_parts:
                faqs.append({'question': question, 'answer': ' '.join(answer_parts)})
        i += 1
    return faqs


def extract_meta(blocks: list) -> dict:
    """Extract meta tag suggestions from content."""
    title = ''
    description = ''
    for b in blocks:
        if b['type'] == 'heading' and b['level'] == 1 and not title:
            title = b['text']
        if b['type'] == 'paragraph' and not description:
            plain = re.sub(r'<[^>]+>', '', parse_inline(b['text']))
            description = plain[:160].rsplit(' ', 1)[0] if len(plain) > 160 else plain
    return {'title': title, 'description': description}


def generate_toc_html(headings: list) -> str:
    """Generate an HTML table of contents."""
    if not headings:
        return ''
    toc = '<nav class="toc" aria-label="Table of Contents">\n'
    toc += '  <h2>Table of Contents</h2>\n  <ul>\n'
    for h in headings:
        indent = '    ' * h['level']
        toc += f'{indent}<li><a href="#{h["id"]}">{parse_inline(h["text"])}</a></li>\n'
    toc += '  </ul>\n</nav>\n'
    return toc


def generate_toc_gutenberg(headings: list) -> str:
    """Generate a Gutenberg TOC block."""
    if not headings:
        return ''
    items = ''
    for h in headings:
        items += f'<li><a href="#{h["id"]}">{h["text"]}</a></li>\n'
    return (
        '<!-- wp:heading {"level":2} -->\n<h2>Table of Contents</h2>\n<!-- /wp:heading -->\n\n'
        f'<!-- wp:list -->\n<ul>\n{items}</ul>\n<!-- /wp:list -->\n\n'
    )


def generate_schema(schema_type: str, meta: dict, faqs: list = None) -> str:
    """Generate JSON-LD schema markup."""
    schema = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "headline": meta.get('title', ''),
        "description": meta.get('description', ''),
    }
    if schema_type == 'HowTo':
        schema['step'] = [{"@type": "HowToStep", "text": "Step placeholder"}]
    if schema_type == 'FAQ' or faqs:
        # FAQPage: AISO/AI-citation benefit only.
        # Google Rich Results restricted to authoritative govt/health sites since Aug 2023.
        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f['question'],
                    "acceptedAnswer": {"@type": "Answer", "text": f['answer']}
                }
                for f in (faqs or [])
            ]
        }
        if schema_type == 'FAQ':
            schema = faq_schema
        else:
            return (
                '<script type="application/ld+json">\n'
                + json.dumps(schema, ensure_ascii=False, indent=2)
                + '\n</script>\n'
                + '<!-- FAQPage schema: AISO/AI-citation benefit only. Google Rich Results restricted to govt/health since Aug 2023. -->\n'
                + '<script type="application/ld+json">\n'
                + json.dumps(faq_schema, ensure_ascii=False, indent=2)
                + '\n</script>\n'
            )
    return '<script type="application/ld+json">\n' + json.dumps(schema, ensure_ascii=False, indent=2) + '\n</script>\n'


def block_to_html(block: dict) -> str:
    """Convert a parsed block to clean semantic HTML."""
    t = block['type']
    if t == 'heading':
        lvl = block['level']
        return f'<h{lvl} id="{block["id"]}">{parse_inline(block["text"])}</h{lvl}>'
    if t == 'paragraph':
        return f'<p>{parse_inline(block["text"])}</p>'
    if t == 'ul':
        items = '\n'.join(f'  <li>{parse_inline(item)}</li>' for item in block['items'])
        return f'<ul>\n{items}\n</ul>'
    if t == 'ol':
        items = '\n'.join(f'  <li>{parse_inline(item)}</li>' for item in block['items'])
        return f'<ol>\n{items}\n</ol>'
    if t == 'code':
        lang_attr = f' class="language-{block["lang"]}"' if block['lang'] else ''
        escaped = block['content'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<pre><code{lang_attr}>{escaped}</code></pre>'
    if t == 'image':
        return f'<figure><img src="{block["src"]}" alt="{block["alt"]}" /><figcaption>{block["alt"]}</figcaption></figure>'
    if t == 'table':
        thead = '<tr>' + ''.join(f'<th>{parse_inline(h)}</th>' for h in block['headers']) + '</tr>'
        rows = '\n'.join(
            '<tr>' + ''.join(f'<td>{parse_inline(c)}</td>' for c in row) + '</tr>'
            for row in block['rows']
        )
        return f'<table>\n<thead>\n{thead}\n</thead>\n<tbody>\n{rows}\n</tbody>\n</table>'
    if t == 'blockquote':
        return f'<blockquote><p>{parse_inline(block["content"])}</p></blockquote>'
    if t == 'hr':
        return '<hr />'
    return ''


def block_to_gutenberg(block: dict) -> str:
    """Convert a parsed block to WordPress Gutenberg block format."""
    t = block['type']
    if t == 'heading':
        lvl = block['level']
        inner = parse_inline(block['text'])
        return f'<!-- wp:heading {{"level":{lvl}}} -->\n<h{lvl} id="{block["id"]}">{inner}</h{lvl}>\n<!-- /wp:heading -->'
    if t == 'paragraph':
        return f'<!-- wp:paragraph -->\n<p>{parse_inline(block["text"])}</p>\n<!-- /wp:paragraph -->'
    if t == 'ul':
        items = '\n'.join(f'<li>{parse_inline(item)}</li>' for item in block['items'])
        return f'<!-- wp:list -->\n<ul>\n{items}\n</ul>\n<!-- /wp:list -->'
    if t == 'ol':
        items = '\n'.join(f'<li>{parse_inline(item)}</li>' for item in block['items'])
        return f'<!-- wp:list {{"ordered":true}} -->\n<ol>\n{items}\n</ol>\n<!-- /wp:list -->'
    if t == 'code':
        lang_attr = f' class="language-{block["lang"]}"' if block['lang'] else ''
        escaped = block['content'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<!-- wp:code -->\n<pre class="wp-block-code"><code{lang_attr}>{escaped}</code></pre>\n<!-- /wp:code -->'
    if t == 'image':
        return f'<!-- wp:image -->\n<figure class="wp-block-image"><img src="{block["src"]}" alt="{block["alt"]}" /><figcaption>{block["alt"]}</figcaption></figure>\n<!-- /wp:image -->'
    if t == 'table':
        thead = '<tr>' + ''.join(f'<th>{parse_inline(h)}</th>' for h in block['headers']) + '</tr>'
        rows = '\n'.join(
            '<tr>' + ''.join(f'<td>{parse_inline(c)}</td>' for c in row) + '</tr>'
            for row in block['rows']
        )
        return f'<!-- wp:table -->\n<figure class="wp-block-table"><table><thead>\n{thead}\n</thead><tbody>\n{rows}\n</tbody></table></figure>\n<!-- /wp:table -->'
    if t == 'blockquote':
        return f'<!-- wp:quote -->\n<blockquote class="wp-block-quote"><p>{parse_inline(block["content"])}</p></blockquote>\n<!-- /wp:quote -->'
    if t == 'hr':
        return '<!-- wp:separator -->\n<hr class="wp-block-separator" />\n<!-- /wp:separator -->'
    return ''


def block_to_shopify(block: dict) -> str:
    """Convert a parsed block to Shopify-compatible HTML (no shortcodes)."""
    t = block['type']
    if t == 'heading':
        lvl = block['level']
        return f'<h{lvl} id="{block["id"]}">{parse_inline(block["text"])}</h{lvl}>'
    if t == 'paragraph':
        return f'<p>{parse_inline(block["text"])}</p>'
    if t == 'ul':
        items = '\n'.join(f'  <li>{parse_inline(item)}</li>' for item in block['items'])
        return f'<ul>\n{items}\n</ul>'
    if t == 'ol':
        items = '\n'.join(f'  <li>{parse_inline(item)}</li>' for item in block['items'])
        return f'<ol>\n{items}\n</ol>'
    if t == 'code':
        escaped = block['content'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<pre><code>{escaped}</code></pre>'
    if t == 'image':
        return f'<div class="rte__image"><img src="{block["src"]}" alt="{block["alt"]}" loading="lazy" /><p class="caption">{block["alt"]}</p></div>'
    if t == 'table':
        thead = '<tr>' + ''.join(f'<th>{parse_inline(h)}</th>' for h in block['headers']) + '</tr>'
        rows = '\n'.join(
            '<tr>' + ''.join(f'<td>{parse_inline(c)}</td>' for c in row) + '</tr>'
            for row in block['rows']
        )
        return f'<div class="table-wrapper"><table>\n<thead>\n{thead}\n</thead>\n<tbody>\n{rows}\n</tbody>\n</table></div>'
    if t == 'blockquote':
        return f'<blockquote>{parse_inline(block["content"])}</blockquote>'
    if t == 'hr':
        return '<hr />'
    return ''


FORMAT_RENDERERS = {
    'html': block_to_html,
    'gutenberg': block_to_gutenberg,
    'shopify': block_to_shopify,
}


def format_content(content: str, fmt: str, toc: bool = False, schema_type: str = None) -> str:
    """Main conversion: Markdown content to the specified output format."""
    blocks = parse_markdown(content)
    headings = extract_headings(blocks)
    faqs = extract_faq(blocks)
    meta = extract_meta(blocks)
    renderer = FORMAT_RENDERERS[fmt]

    parts = []

    # Meta suggestions as HTML comment
    if meta['title'] or meta['description']:
        parts.append(f'<!-- Meta Title: {meta["title"]} -->')
        parts.append(f'<!-- Meta Description: {meta["description"]} -->')
        parts.append('')

    # Schema markup
    if schema_type:
        parts.append(generate_schema(schema_type, meta, faqs))
        parts.append('')

    # FAQ schema (auto-detected, only if not already FAQ type)
    # AISO benefit only — Google Rich Results restricted to govt/health Aug 2023
    if faqs and schema_type != 'FAQ':
        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f['question'],
                    "acceptedAnswer": {"@type": "Answer", "text": f['answer']}
                }
                for f in faqs
            ]
        }
        parts.append('<!-- FAQPage schema: AISO/AI-citation benefit only. Google Rich Results restricted to govt/health since Aug 2023. -->')
        parts.append('<script type="application/ld+json">')
        parts.append(json.dumps(faq_schema, ensure_ascii=False, indent=2))
        parts.append('</script>')
        parts.append('')

    # Table of Contents
    if toc and headings:
        if fmt == 'gutenberg':
            parts.append(generate_toc_gutenberg(headings))
        else:
            parts.append(generate_toc_html(headings))

    # Render blocks
    for block in blocks:
        rendered = renderer(block)
        if rendered:
            parts.append(rendered)
            parts.append('')

    return '\n'.join(parts)


def _self_test_hook() -> None:
    if "--self-test" in sys.argv[1:]:
        raise SystemExit(_self_test())


def main():
    _self_test_hook()
    parser = argparse.ArgumentParser(
        description='SEO Content Formatter -- Convert Markdown to CMS-ready formats.',
        epilog='Supports HTML, WordPress Gutenberg, and Shopify. Handles Thai UTF-8.'
    )
    parser.add_argument('input', nargs='?', help='Path to Markdown file')
    parser.add_argument('--stdin', action='store_true', help='Read content from stdin')
    parser.add_argument('--format', '-f', choices=['html', 'gutenberg', 'shopify'],
                        default='html', help='Output format (default: html)')
    parser.add_argument('--toc', action='store_true', help='Include Table of Contents')
    parser.add_argument('--schema', choices=['Article', 'HowTo', 'FAQ'],
                        help='Add Schema.org markup (Article, HowTo, or FAQ)')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')

    args = parser.parse_args()

    # Read input
    if args.stdin:
        content = sys.stdin.read()
    elif args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f'Error: File not found: {args.input}', file=sys.stderr)
            sys.exit(1)
        content = input_path.read_text(encoding='utf-8')
    else:
        parser.print_help()
        print('\nError: Provide an input file or use --stdin', file=sys.stderr)
        sys.exit(1)

    # Convert
    result = format_content(content, args.format, toc=args.toc, schema_type=args.schema)

    # Output
    if args.output:
        Path(args.output).write_text(result, encoding='utf-8')
        print(f'Written to {args.output}', file=sys.stderr)
    else:
        sys.stdout.buffer.write(result.encode('utf-8'))
        sys.stdout.write('\n')



def _self_test() -> int:
    """Markdown to HTML, Gutenberg and Shopify with TOC and FAQ schema."""
    sample = "# Title\n\nFirst paragraph with **bold** text.\n\n## What is it?\nIt is a test.\n\n## Why?\nBecause.\n"
    html = format_content(sample, "html", toc=True, schema_type="FAQ")
    assert "<h1" in html and "<h2" in html and "FAQPage" in html, html[:200]
    gut = format_content(sample, "gutenberg")
    assert "wp:heading" in gut, gut[:200]
    shop = format_content(sample, "shopify")
    assert "<h2" in shop, shop[:200]
    print("SELF-TEST PASS: html, gutenberg, shopify")
    return 0


if __name__ == '__main__':
    main()
