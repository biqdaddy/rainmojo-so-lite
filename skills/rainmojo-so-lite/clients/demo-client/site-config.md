# Site Brief — [CLIENT NAME]

Machine-enforced content, image, logo, metadata, and draft-publishing rules
live in `content-pipeline.json`. Keep this Markdown file as the human-readable
site brief and keep both files aligned.

## CMS & Platform

- **CMS**: [WordPress / Shopify / Wix / Custom / อื่นๆ]
- **Version**: [e.g. WordPress 6.5]
- **Page Builder**: [Elementor / Divi / Gutenberg / WPBakery / Oxygen / none]
- **Theme**: [theme name]

## SEO Plugin

- **Plugin**: [Yoast SEO / RankMath / SEOPress / All-in-One SEO / none]
- **Version**: [e.g. Yoast 23.x]
- **Meta fields**:
  - Title: [yoast_wpseo_title / rank_math_title / custom field name]
  - Description: [yoast_wpseo_metadesc / rank_math_description / custom]
  - Focus keyword: [yoast_wpseo_focuskw / rank_math_focus_keyword]

## Content Posting Instructions

### Format
- **Editor**: [Block Editor (Gutenberg) / Classic Editor / Page Builder]
- **Content format**: [HTML / Markdown / Blocks / Shortcodes]
- **Image handling**: [upload to media library / external URL / CDN]

### Structure
- **H1**: [auto from title / manual in content]
- **Table of Contents**: [plugin name / manual / none]
- **Schema**: [auto from SEO plugin / manual JSON-LD / theme built-in]

### Publishing
- **Default status**: [draft / publish / pending review]
- **Categories**: [list main categories]
- **Tags**: [tagging convention]
- **Featured image**: [required? / size requirement]
- **Approval process**: [direct publish / needs client approval / staging first]

### Production Pipeline
- **Machine config**: `content-pipeline.json`
- **Article package path**: `content/production/{slug}/`
- **Default pipeline status**: `planned`
- **Public publishing**: outside the content-production-lite pipeline; draft only

## Custom Post Types

| Post Type | Slug | SEO Plugin Support | Notes |
|-----------|------|--------------------|-------|
| Posts | `post` | Yes | Blog articles |
| Pages | `page` | Yes | Static pages |
| [Custom] | [slug] | [Yes/No] | [notes] |

## Page Builder Notes

### Shortcodes Used
```
[example_shortcode param="value"]
```

### Custom CSS Classes
```
.custom-class-name — [what it does]
```

### Element Templates
- **CTA Button**: [how to insert]
- **Contact Form**: [plugin + shortcode]
- **FAQ Accordion**: [plugin / built-in]

## API Access

- **REST API**: [enabled / disabled / restricted]
- **API Base URL**: [e.g. https://example.com/wp-json/wp/v2/]
- **Authentication**: [Application Passwords / JWT / API Key]
- **Rate Limits**: [if any]

## Notes

[Additional instructions, quirks, or things to be careful about]
