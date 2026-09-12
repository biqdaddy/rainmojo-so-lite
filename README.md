# RAINMOJO SO Lite

SEO and AISO (AI Search Optimization) toolkit for Claude Code, Claude Desktop and Cowork, Codex CLI, ChatGPT, Gemini CLI and Antigravity. 43 skills and 17 agents that check whether ChatGPT, Perplexity, Claude, Google AI Overviews, Gemini and 5 more AI answer platforms can reach, read and cite your website, run the classic SEO audits, fix what fails, and publish WordPress drafts. Every result is a checklist or a count, never a weighted score.

Free lite edition of [RAINMOJO SO](https://rainmojo.com/) by [BIQDADDY](https://biqdaddy.com). Version 2.0.0.

[Install](#install) · [First run](#first-run) · [What is inside](#what-is-inside) · [How results look](#how-results-look) · [Requirements](#requirements) · [Privacy and license](#privacy-and-license) · [ภาษาไทย](#ภาษาไทย)

## Install

Pick the host you use. The same repository serves every host; nothing else to download.

### Claude Code

```bash
claude plugin marketplace add biqdaddy/rainmojo-so-lite
claude plugin install rainmojo-so-lite@biqdaddy
```

Update later with `claude plugin update rainmojo-so-lite@biqdaddy`.

### Claude Desktop and Cowork

Download `rainmojo-so-lite.plugin` from the [latest release](https://github.com/biqdaddy/rainmojo-so-lite/releases) and drag it into the chat window. Cowork users can also install from the Claude plugin directory once it is listed there.

### Codex CLI

```bash
codex plugin marketplace add biqdaddy/rainmojo-so-lite
codex plugin add rainmojo-so-lite@biqdaddy
```

### ChatGPT

Install from the ChatGPT plugin directory when listed, or drag `rainmojo-so-lite.plugin` from the latest release into the ChatGPT desktop app.

### Gemini CLI

```bash
gemini extensions install https://github.com/biqdaddy/rainmojo-so-lite
```

### Antigravity

```bash
agy plugin install https://github.com/biqdaddy/rainmojo-so-lite
```

Or copy this folder into `.agents/plugins/` of your workspace, or into `~/.gemini/config/plugins/` for every workspace.

### From source, any host

```bash
git clone https://github.com/biqdaddy/rainmojo-so-lite.git
```

Then point your host at the folder: Claude Code `claude plugin marketplace add ./rainmojo-so-lite`, Codex `codex plugin marketplace add ./rainmojo-so-lite`, Gemini CLI `gemini extensions install ./rainmojo-so-lite`.

## First run

Talk to your assistant in plain language. It picks the skill or agent for you.

1. Start with a workspace so every result has a home: `Create a workspace for example.com`. The plugin creates `work/example-com/` with folders for the first scan, later scans, fixes, content and reports.
2. Check access first, because nothing else matters if AI crawlers cannot get in: `Check whether AI crawlers can reach example.com`.
3. Run the full picture: `Audit AI visibility for example.com` (AISO only) or `Run a full SEO and AI visibility audit for example.com` (both).
4. Fix, then measure again: `Compare the two audit rounds for example.com`.

To force one unit, name it: `Use the skill aiso-citability-lite on this page` or `Run the agent seo-keyword-lite for dental clinics in Bangkok`.

Publishing to WordPress needs an application password in a local `.env` file inside your client workspace (see `wp-connect-lite`). Never paste credentials into the chat; the plugin refuses them. It publishes drafts only and never presses Publish for you.

## What is inside

### Agents (17)

Agents run several skills in the right order and end with a summary card.

| Agent | What it does |
|---|---|
| `so-audit-lite` | Full SEO plus AISO audit in one run, one combined report |
| `seo-audit-lite` | Classic SEO audit across six areas |
| `aiso-audit-lite` | AISO audit across nine areas, including AI agent readiness |
| `aiso-ai-visibility-lite` | AI visibility tracking with a two-round comparison |
| `aiso-content-review-lite` | Content quality for AI citation |
| `aiso-platform-analysis-lite` | Readiness per AI answer platform, 11 cards for 10 platforms |
| `aiso-schema-audit-lite` | Audit existing JSON-LD and generate what is missing |
| `aiso-technical-audit-lite` | Technical checks from both the SEO and the AI side |
| `seo-technical-lite` | Technical SEO |
| `seo-onpage-lite` | Meta tags, schema, heading structure, internal links |
| `seo-keyword-lite` | Keyword research, clustering, content gaps |
| `seo-content-lite` | Content strategy through writing and enhancement |
| `seo-local-lite` | Local SEO |
| `seo-offpage-lite` | Competitors and link building plan |
| `seo-disavow-auditor-lite` | First-pass backlink risk review |
| `content-production-orchestrator-lite` | From client workspace to a verified WordPress draft |
| `remediation-orchestrator-lite` | Turns audit results into a fix plan (never edits the site itself) |

### Skills (43)

| Group | Skills |
|---|---|
| Start and finish | `new-workspace-lite`, `new-client-lite`, `report-lite`, `compare-lite`, `so-present-lite`, `rainmojo-so-lite` (catalog) |
| AISO | `aiso-crawlers-lite`, `aiso-llmstxt-lite`, `aiso-schema-lite`, `aiso-technical-lite`, `aiso-content-lite`, `aiso-citability-lite`, `aiso-platform-lite`, `aiso-brand-mentions-lite`, `aiso-agent-readiness-lite` |
| SEO checks | `seo-website-overview-lite`, `technical-audit-lite`, `seo-heading-matrix-lite`, `meta-basics-lite`, `seo-schema-lite`, `seo-internal-linking-lite`, `seo-image-optimizer-lite`, `sitemap-architecture-lite` |
| Keywords and gaps | `seo-keyword-research-lite`, `seo-keyword-clustering-lite`, `seo-content-gap-analysis-lite`, `seo-competitor-lite`, `seo-topical-authority-lite` |
| Content | `seo-content-audit-lite`, `seo-content-enhancement-lite`, `seo-content-strategy-lite`, `seo-video-lite` |
| Off site and local | `seo-local-seo-lite`, `seo-backlink-strategy-lite` |
| Migrations and tests | `seo-migration-lite`, `seo-experiment-lite` |
| Content production | `seo-content-creation-lite`, `content-production-lite`, `wp-rest-ops-lite`, `wp-content-publisher-lite` |
| Quick path | `content-draft-lite`, `wp-connect-lite`, `wp-publish-draft-lite` |

The catalog skill `rainmojo-so-lite` answers "what can this plugin do" and routes you to the right unit.

### Platforms covered

ChatGPT, Perplexity, Claude, Google AI Overviews, Gemini, DeepSeek, Grok, Qwen, Meta AI, Microsoft Copilot, Apple Intelligence. Crawler tokens, roles and evidence tiers come from one registry of 68 documented crawlers (`skills/rainmojo-so-lite/reference/frameworks/ai-platform-registry.json`). Platforms without a documented crawler (DeepSeek, Grok, Qwen) are reported as could not verify, never guessed.

### Scripts

Local Python scripts the skills call, each with `--self-test`: `robots_generator.py` (robots.txt analysis per RFC 9309 and generation from three policies), `page_analyzer.py` (rendering, crawler access, content blocks, llms.txt), `agent_readiness_lite.py` (14 checks from the HTML and the accessibility tree), `present.py` and `build_summary.py` (summary card), `client_workspace.py`, `content_pipeline.py`, `content_formatter.py`, `image_production.py`, `wordpress_publisher.py`.

## How results look

Every run writes a full deliverable (Markdown or HTML report, JSON-LD file, article package) into your workspace, then ends with a short summary card in the chat: what passed, what failed, the biggest risk, the next actions, and a link to the full file. The card is rendered for your host (inline widget, artifact, Mermaid, ASCII tree or Markdown).

Results are checklists and counts. When something cannot be measured the plugin says could not verify instead of guessing, and it never turns a missing check into a fail.

## Requirements

- An AI host from the install list above.
- Python 3.10 or newer for the bundled scripts, with `pip install requests beautifulsoup4 lxml pillow jsonschema`.
- Optional: `pip install playwright` and `playwright install chromium` to enable the rendered tier of the AI agent readiness checklist. Without it, rendered checks are reported as could not verify.
- No API keys. The plugin reads public web pages, Google Suggest, and your own WordPress site.

## Privacy and license

The plugin runs inside your own AI assistant and on your own machine. It has no server, no account, no analytics and no tracking; BIQDADDY never receives your prompts, pages or results. Requests go only to the domains you name, to Google Suggest for keyword ideas, and to your own WordPress REST API when you publish a draft. Full policy: [rainmojo.com/privacy/rainmojo-so-lite](https://rainmojo.com/privacy/rainmojo-so-lite/). Terms: [rainmojo.com/terms](https://rainmojo.com/terms/).

Licensed under the BIQDADDY Free Tools License 1.0 (see [LICENSE](LICENSE)): install and use it, modified or not, for your own sites and your clients; do not redistribute it or a derivative under another name.

Support and questions: [biqdaddy.com/contact](https://biqdaddy.com/contact/) or info@biqdaddy.com. Bug reports: [GitHub issues](https://github.com/biqdaddy/rainmojo-so-lite/issues).

---

## ภาษาไทย

ชุดเครื่องมือ SEO และ AISO (AI Search Optimization) สำหรับ Claude Code, Claude Desktop และ Cowork, Codex CLI, ChatGPT, Gemini CLI และ Antigravity 43 สกิล 17 agent ตรวจว่า ChatGPT, Perplexity, Claude, Google AI Overviews, Gemini และอีก 5 แพลตฟอร์มคำตอบ AI เข้าถึง อ่าน และอ้างอิงเว็บของคุณได้ไหม ตรวจ SEO พื้นฐาน แก้จุดที่ไม่ผ่าน และส่งบทความขึ้น WordPress เป็นฉบับร่าง ทุกผลลัพธ์เป็นเช็กลิสต์หรือจำนวนนับ ไม่มีคะแนนถ่วงน้ำหนัก

รุ่นฟรีของ [RAINMOJO SO](https://rainmojo.com/) โดย [BIQDADDY](https://biqdaddy.com) เวอร์ชัน 2.0.0

[ติดตั้ง](#ติดตั้ง) · [เริ่มใช้ครั้งแรก](#เริ่มใช้ครั้งแรก) · [มีอะไรข้างใน](#มีอะไรข้างใน) · [ผลลัพธ์หน้าตาเป็นยังไง](#ผลลัพธ์หน้าตาเป็นยังไง) · [สิ่งที่ต้องมี](#สิ่งที่ต้องมี) · [ความเป็นส่วนตัวและสิทธิ์การใช้](#ความเป็นส่วนตัวและสิทธิ์การใช้) · [English](#rainmojo-so-lite)

### ติดตั้ง

เลือกตาม host ที่ใช้ ทุก host ใช้ repo เดียวกันนี้ ไม่ต้องโหลดอย่างอื่นเพิ่ม

**Claude Code**

```bash
claude plugin marketplace add biqdaddy/rainmojo-so-lite
claude plugin install rainmojo-so-lite@biqdaddy
```

อัปเดตภายหลังด้วย `claude plugin update rainmojo-so-lite@biqdaddy`

**Claude Desktop และ Cowork**: โหลดไฟล์ `rainmojo-so-lite.plugin` จาก [release ล่าสุด](https://github.com/biqdaddy/rainmojo-so-lite/releases) แล้วลากมาวางในหน้าต่างแชต หรือติดตั้งจาก plugin directory ของ Claude เมื่อขึ้นรายการแล้ว

**Codex CLI**

```bash
codex plugin marketplace add biqdaddy/rainmojo-so-lite
codex plugin add rainmojo-so-lite@biqdaddy
```

**ChatGPT**: ติดตั้งจาก plugin directory ของ ChatGPT เมื่อขึ้นรายการแล้ว หรือลากไฟล์ `rainmojo-so-lite.plugin` จาก release ล่าสุดลงในแอป ChatGPT desktop

**Gemini CLI**

```bash
gemini extensions install https://github.com/biqdaddy/rainmojo-so-lite
```

**Antigravity**

```bash
agy plugin install https://github.com/biqdaddy/rainmojo-so-lite
```

หรือคัดลอกโฟลเดอร์นี้ไปไว้ใน `.agents/plugins/` ของ workspace หรือ `~/.gemini/config/plugins/` ถ้าต้องการใช้ทุก workspace

**จากซอร์ส ใช้ได้ทุก host**: `git clone https://github.com/biqdaddy/rainmojo-so-lite.git` แล้วชี้ host ไปที่โฟลเดอร์ เช่น `claude plugin marketplace add ./rainmojo-so-lite`

### เริ่มใช้ครั้งแรก

พิมพ์เป็นภาษาปกติ ระบบเลือกสกิลหรือ agent ให้เอง

1. สร้างพื้นที่งานก่อน ผลลัพธ์จะได้มีที่อยู่: `สร้างโครงโฟลเดอร์สำหรับเว็บ example.com` ได้ `work/example-com/` พร้อมโฟลเดอร์สแกนรอบแรก รอบถัดไป สิ่งที่ต้องแก้ เนื้อหา และรายงาน
2. ตรวจการเข้าถึงก่อน เพราะถ้าบอท AI เข้าไม่ได้ อย่างอื่นไม่มีความหมาย: `ตรวจว่า AI crawler เข้าเว็บ example.com ได้ไหม`
3. ตรวจภาพรวม: `ตรวจ AI visibility ของ example.com ให้ครบทุกด้าน` (เฉพาะ AISO) หรือ `ตรวจ SEO และ AI visibility ของ example.com ในรอบเดียว` (ทั้งสองฝั่ง)
4. แก้แล้ววัดซ้ำ: `เทียบผลตรวจสองรอบของ example.com`

ถ้าอยากบังคับใช้ตัวใดตัวหนึ่ง ให้พิมพ์ชื่อลงไปตรง ๆ เช่น `ใช้สกิล aiso-citability-lite กับหน้านี้`

การส่งขึ้น WordPress ต้องมี application password ในไฟล์ `.env` ในโฟลเดอร์ลูกค้าของคุณเอง (ดู `wp-connect-lite`) ห้ามพิมพ์รหัสลงในแชต ปลั๊กอินจะปฏิเสธ และปลั๊กอินส่งเป็นฉบับร่างเท่านั้น ไม่กดเผยแพร่แทนคุณ

### มีอะไรข้างใน

**agent 17 ตัว** เรียกสกิลหลายตัวตามลำดับที่ถูกต้องแล้วปิดด้วยการ์ดสรุป

| agent | ใช้ทำอะไร |
|---|---|
| `so-audit-lite` | ตรวจครบทั้ง SEO และ AISO ในรอบเดียว รวมเป็นรายงานเดียว |
| `seo-audit-lite` | ตรวจ SEO พื้นฐาน 6 ด้าน |
| `aiso-audit-lite` | ตรวจฝั่ง AI 9 ด้าน รวม AI agent readiness |
| `aiso-ai-visibility-lite` | วัดการมองเห็นบน AI แล้วเทียบสองรอบ |
| `aiso-content-review-lite` | คุณภาพเนื้อหาสำหรับให้ AI อ้างอิง |
| `aiso-platform-analysis-lite` | ความพร้อมรายแพลตฟอร์ม 11 การ์ดของ 10 แพลตฟอร์ม |
| `aiso-schema-audit-lite` | ตรวจ JSON-LD ที่มี แล้วสร้างส่วนที่ขาด |
| `aiso-technical-audit-lite` | ตรวจเทคนิคทั้งมุม SEO และมุม AI |
| `seo-technical-lite` | เทคนิค SEO |
| `seo-onpage-lite` | meta, schema, โครงหัวข้อ, ลิงก์ภายใน |
| `seo-keyword-lite` | หาคำค้น จัดกลุ่ม หาช่องว่าง |
| `seo-content-lite` | กลยุทธ์เนื้อหาถึงการเขียนและปรับ |
| `seo-local-lite` | SEO ท้องถิ่น |
| `seo-offpage-lite` | คู่แข่งและแผนสร้างลิงก์ |
| `seo-disavow-auditor-lite` | ประเมินความเสี่ยง backlink เบื้องต้น |
| `content-production-orchestrator-lite` | จากโฟลเดอร์ลูกค้าถึงฉบับร่างบน WordPress ที่ตรวจแล้ว |
| `remediation-orchestrator-lite` | แปลงผลตรวจเป็นแผนแก้ (ไม่แก้เว็บเอง) |

**สกิล 43 ตัว** แบ่ง 9 กลุ่ม: เริ่มและจบงาน, AISO, ตรวจ SEO, คำค้นและช่องว่าง, เนื้อหา, นอกเว็บและท้องถิ่น, ย้ายเว็บและทดสอบ, สายผลิตเนื้อหา, เส้นทางลัด รายชื่อเต็มอยู่ในตารางภาษาอังกฤษด้านบน สกิล `rainmojo-so-lite` คือสารบัญ ถามว่า "ปลั๊กอินนี้ทำอะไรได้บ้าง" ได้เลย

**แพลตฟอร์มที่ครอบคลุม**: ChatGPT, Perplexity, Claude, Google AI Overviews, Gemini, DeepSeek, Grok, Qwen, Meta AI, Microsoft Copilot, Apple Intelligence ชื่อบอท บทบาท และระดับหลักฐานมาจากทะเบียนบอทที่มีเอกสาร 68 ชื่อชุดเดียว แพลตฟอร์มที่ไม่ประกาศชื่อบอท (DeepSeek, Grok, Qwen) รายงานว่า ตรวจสอบไม่ได้ ไม่เดา

### ผลลัพธ์หน้าตาเป็นยังไง

ทุกรอบเขียนไฟล์ผลลัพธ์ฉบับเต็ม (รายงาน Markdown หรือ HTML, ไฟล์ JSON-LD, แพ็กเกจบทความ) ลงพื้นที่งานของคุณ แล้วปิดด้วยการ์ดสรุปสั้น ๆ ในแชต: ผ่านอะไร ไม่ผ่านอะไร ความเสี่ยงใหญ่สุด สิ่งที่ควรทำต่อ และลิงก์ไปไฟล์ฉบับเต็ม การ์ดเรนเดอร์ตาม host ที่ใช้ (widget, artifact, Mermaid, ต้นไม้ ASCII หรือ Markdown)

ผลลัพธ์เป็นเช็กลิสต์และจำนวนนับ สิ่งที่วัดไม่ได้จะขึ้นว่า ตรวจสอบไม่ได้ ไม่เดา และไม่นับข้อที่ตรวจไม่ได้เป็นไม่ผ่าน

### สิ่งที่ต้องมี

- AI host ตัวใดตัวหนึ่งจากรายการติดตั้ง
- Python 3.10 ขึ้นไป สำหรับสคริปต์ที่แนบมา พร้อม `pip install requests beautifulsoup4 lxml pillow jsonschema`
- ทางเลือก: `pip install playwright` และ `playwright install chromium` เพื่อเปิดชั้น rendered ของเช็กลิสต์ AI agent readiness ถ้าไม่ติดตั้ง ข้อที่ต้องเรนเดอร์จะขึ้นว่า ตรวจสอบไม่ได้
- ไม่ต้องใช้ API key ปลั๊กอินอ่านหน้าเว็บสาธารณะ, Google Suggest และ WordPress ของคุณเองเท่านั้น

### ความเป็นส่วนตัวและสิทธิ์การใช้

ปลั๊กอินทำงานในผู้ช่วย AI ของคุณและบนเครื่องของคุณ ไม่มีเซิร์ฟเวอร์ ไม่มีบัญชี ไม่มี analytics ไม่มีการติดตาม BIQDADDY ไม่เคยได้รับ prompt หน้าเว็บ หรือผลลัพธ์ของคุณ request ออกไปเฉพาะโดเมนที่คุณสั่งตรวจ, Google Suggest สำหรับไอเดียคำค้น และ REST API ของ WordPress ของคุณเองตอนส่งฉบับร่าง นโยบายฉบับเต็ม: [rainmojo.com/privacy/rainmojo-so-lite](https://rainmojo.com/privacy/rainmojo-so-lite/) ข้อกำหนด: [rainmojo.com/terms](https://rainmojo.com/terms/)

สิทธิ์การใช้ตาม BIQDADDY Free Tools License 1.0 (ดู [LICENSE](LICENSE)): ติดตั้งและใช้ได้ ทั้งแบบแก้และไม่แก้ กับเว็บของคุณและงานลูกค้าของคุณ ห้ามแจกซ้ำตัวมันหรือของที่ดัดแปลงจากมันในชื่ออื่น

ติดต่อและสอบถาม: [biqdaddy.com/contact](https://biqdaddy.com/contact/) หรือ info@biqdaddy.com แจ้งบั๊กที่ [GitHub issues](https://github.com/biqdaddy/rainmojo-so-lite/issues)
