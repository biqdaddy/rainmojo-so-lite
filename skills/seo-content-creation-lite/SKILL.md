---
name: seo-content-creation-lite
description: >
   Expert content creation including brand configuration setup. Creates high-quality, brand-consistent content that reads naturally while achieving SEO objectives. Copy-paste results to other agents for complete workflow. 
allowed-tools:
  - Read
  - Grep
  - Glob
  - WebFetch
  - Write
---
<!-- RAINMOJO_CLIENT_WORKSPACE_ROUTING_V1 -->
## Client workspace routing (mandatory for file changes)

Every generated file has exactly one home. Audit, keyword and comparison
outputs live under `work/{domain}/` created by `new-workspace-lite`
(`00-baseline/` first run, `01-current/` later runs, `02-fixes/`, `03-content/`,
`04-reports/`, `uploads/` read-only for user files); never invent another
top-level folder there. Content production and WordPress publishing use the
client workspace `clients/<client>/` created by `new-client-lite`: read
`workspace-routing.json` first, resolve every artifact with
`{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/client_workspace.py route`, use the
most precise registered route, edit root files only when their exact filename is
in `root_policy.allowed_files`, treat `uploads/` as read-only, and when no route
fits use `create-work` then `route-work`; never construct a `work/<name>/...`
path by hand inside a client workspace. Never write generated files to the
plugin tree or the caller's working directory. Append one line to the
workspace's `CHANGELOG.md` or `log.md` after every write. Run
`client_workspace.py validate` before handing a client workspace over. Direct
CMS/API operations retain their own safety and verification gates.

<!-- RAINMOJO_PRESENTATION_LAYER_V1 -->
## Presentation (Two-Tier, 7 modes)

Answer in the response mode that matches the request
(`{PLUGIN_ROOT}/skills/rainmojo-so-lite/_base/presentation-scaffold.md`): quick fact,
how-to, comparison, troubleshoot, audit, deployable, always closing with next
steps. A run that writes a deliverable ends with a Tier 1 card built from
`summary.json` (`templates/widget/summary.schema.json`) and rendered with
`{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --target auto`, then hands
off to the Tier 2 file, which stays complete and unchanged. Lite cards carry
counts of checks passed, never a weighted score. Every card value is copied
from the deliverable; unmeasured values show as could not verify. No emoji on
any surface; the glyph allowlist applies to chat and Markdown only.


# content creation

## Mandatory output rules (meta tags + content)

These override any conflicting guidance below.

- Title tag brand: include the brand / site name ONLY in the homepage title (as the first element). For every other page type (service, product, category, blog, about, contact, trust and credibility, local, informational) do NOT include the brand name and do NOT use a `|` brand separator. Use the full character budget for the topic, keywords, and context. Google already shows the Sitename in the SERP, so a brand in the title wastes space.
  - Wrong: `บริการรับทำ SEO เพิ่มยอดขาย ติดอันดับ | BIQDADDY`
  - Right: `บริการรับทำ SEO เพิ่มยอดขาย ติดอันดับ และรองรับ AI Search`
- No em dash and no pipe `|` in generated title tags, meta descriptions, headings, or body content and recommendations. Use commas, spaces, the word และ, or rephrase. Markdown table delimiters are exempt because they are structural formatting, not content.


Read and execute the agent workflow from [agent.json](agent.json).
Follow all phases and steps sequentially. If a value in agent.json is an `_externalized` pointer, Read the referenced framework file at `reference/frameworks/*.json` RELATIVE TO THE PLUGIN ROOT (not this skill folder) before applying it. The pointer value uses {PLUGIN_ROOT}/ to make this explicit.

> Inherits shared conventions from [_base/skill-scaffold.md](../rainmojo-so-lite/_base/skill-scaffold.md): Brand Context auto-load and User Uploads auto-detect. Read it once before executing.

## Phase W4 ใครเป็นเจ้าของการออกแบบจุดสกัดข้อมูล

- **การเลือกรูปแบบคำตอบต่อ heading** (prose, list, table) ถ้ามีบรีฟที่ล็อกไว้แล้ว ให้คัดลอกค่านั้น ห้ามเลือกใหม่หรือแปลงรูปแบบ
  เฟสนี้เลือกเองเฉพาะเมื่อเขียนโดยไม่มีบรีฟ
- **กลไกการสกัดที่บรีฟไม่ได้ล็อก** คือ grouper question เหนือลิสต์, การบังคับคำแกนให้ตรงคำต่อคำ (เทียบระดับ code point
  ห้าม normalize สระวรรณยุกต์ก่อนเทียบ), เพดานกันยัดคำ และ snippet cut test เป็นของเฟสนี้เสมอ
  `aiso-citability-lite` ประเมินเฉพาะหน้าที่เผยแพร่แล้ว ไม่ตั้งชุดกฎออกแบบซ้ำ
- **เพดานกันยัดคำ** ตรงคำหมายถึงใช้คำเดียวกัน ไม่ใช่พูดคำเดิมซ้ำหลายรอบ ถ้าการตรงคำทำให้ประโยคไม่เป็นธรรมชาติ
  ให้เลือกภาษาที่เป็นธรรมชาติแล้วบันทึกเหตุผลในตาราง การเลี่ยงโดยไม่บันทึกเหตุผลถือว่าไม่ผ่าน
- เกณฑ์ผ่าน W4: ตัด heading พร้อมย่อหน้าหรือลิสต์แรกออกมาเป็นก้อนเดียวแล้วต้องอ่านรู้เรื่องโดยไม่มีสรรพนามอ้างถึงข้อความก่อนหน้า
  และจำนวน list item ที่คำแกนไม่ตรงกับ heading โดยไม่มีเหตุผลบันทึกไว้เท่ากับ 0

## Phase W8 ตรวจสองรอบทุก section ที่โมเดลร่าง (ความถูกต้อง แยกจาก ความครบ)

ทำกับทุก section ที่โมเดลร่าง ไม่ว่าจะทั้ง section หรือบางย่อหน้า ทำหลังการตรวจ dual-summary เสมอ
เหตุผลที่ต้องแยกเป็นสองรอบ: ความถูกต้องกับความครบพังคนละอัตรากันมาก และ **การตกหล่นคือข้อบกพร่องที่พบมากที่สุด**
อ่านรวดเดียวจะเจอประโยคที่ผิด แต่มองไม่เห็นครึ่งที่หายไป

- **รอบที่ 1 เดินไล่ทุก claim** ตามลำดับที่ปรากฏ ให้ค่าหนึ่งในสาม คือ verified (ต้องมีชื่อแหล่งกำกับ), wrong (แหล่งที่ระบุชื่อขัดกับ claim),
  unverifiable (หาแหล่งไม่ได้ ให้เขียน could not verify ห้ามแปลงเป็นผิดหรือไม่มีจริง)
- **รอบที่ 2 ถามว่าผู้เชี่ยวชาญจะยืนยันว่าต้องมีอะไร** เขียนรายการนั้นก่อนกลับไปอ่านร่าง แล้วอ่านร่างเทียบรายการ
  ออกรายการสิ่งที่ขาดพร้อมตำแหน่งที่ควรอยู่ ตัดสินการขาดจากบรีฟและรายการผู้เชี่ยวชาญ ไม่ใช่ตรรกะภายในของร่าง
- **รอบที่ 2 มีน้ำหนักเหนือรอบที่ 1** ร่างที่ผ่านรอบแรกสะอาดแต่ขาดสาระในรอบสอง ถือว่าไม่ผ่าน ส่งกลับไปเขียนเพิ่ม
- **คนที่ระบุชื่อจริงลงชื่อรับรองทั้งสองรอบ** พร้อมวันที่ ก่อนร่างจะเดินต่อไปขั้นเผยแพร่ ชื่อตำแหน่งอย่างเดียวหรือคำอนุมัติที่โมเดลเขียนเองไม่นับ
- เกณฑ์ผ่าน W8: ทุก claim มีค่าพร้อมชื่อแหล่งหรือ could not verify, จำนวน claim ที่ wrong และยังอยู่ในร่างเท่ากับ 0,
  รายการสิ่งที่ขาดถูกปิดครบหรือบันทึกเหตุผลที่ไม่ปิด, และมีชื่อผู้ลงชื่อพร้อมวันที่
- เวอร์ชันที่บล็อกการเผยแพร่ (blocklist หัวข้อที่โมเดลเป็นแหล่งอ้างอิงไม่ได้, การบันทึก engine, รูปแบบ record ของการลงชื่อ)
  เป็นของ `content-production-lite` ที่นี่คือวิธีเดินตรวจตอนเขียน

## หน้าชุดพี่น้องที่สร้างจากฐานข้อมูล (ต่อสาขา ต่อพื้นที่ ต่อรุ่น)

ใช้เมื่อสร้างหลายหน้าจาก template เดียวกันโดยต่างกันที่ entity ชั้นนี้เสียบเพิ่มจาก W1 ถึง W8 ไม่ได้แทนที่

1. **ข้อเท็จจริงมาจาก record เท่านั้น** ฟิลด์ที่ record ไม่มี ให้ตัดออกจากหน้า ห้ามเติมค่าเอง และห้ามยกค่าจาก record ของพี่น้องมาใช้
2. **ให้หน้าที่เขียนด้วยมือหนึ่งหน้าเป็นตัวอย่างผลลัพธ์** ส่งเข้าไปเป็น exemplar ให้ทำตามโครง ไม่ใช่คิดโครงขึ้นเอง
3. **หน้าพี่น้องห้ามใช้ถ้อยคำซ้ำกัน** โครงร่วมกันได้ ประโยคร่วมกันไม่ได้
4. **ตรวจทีละฟิลด์ย้อนกลับไปที่ record ของหน้านั้นเอง** ก่อนเผยแพร่ ไม่เทียบกับ exemplar และไม่เทียบกับหน้าพี่น้อง

ขาดชั้นนี้ งานหลายสาขาจะออกมาสองแบบเท่านั้น คือแต่งเวลาทำการและบริการขึ้นเอง หรือได้ clone ที่อ่านแล้วเป็น duplicate content
procedure เต็มอยู่ที่ `{PLUGIN_ROOT}/skills/rainmojo-so-lite/reference/frameworks/content-creation-sibling-page-generation.json`

## การตั้งค่าแบรนด์เป็นของ `new-client-lite`

คำถามสัมภาษณ์แบรนด์ 5 ข้ออยู่ครั้งเดียวที่ `{PLUGIN_ROOT}/skills/rainmojo-so-lite/reference/frameworks/brand-configuration-interview.json`
และ `new-client-lite` เป็นผู้เขียน brand-guidelines.md กับ client-profile.md สกิลนี้อ่านสองไฟล์นั้นอย่างเดียว
ถ้าไฟล์หาย ถามคำถามชุดเดียวกันได้เฉพาะสำหรับรอบนี้ แต่ห้ามเขียนไฟล์ทั้งสอง เพราะผู้เขียนสองคนจะได้โปรไฟล์แบรนด์สองชุดที่ไม่รู้จักกัน

## Output
### Naming convention

ไฟล์ที่สร้างต้องตั้งชื่อตาม pattern:

```
{domain}_content-draft_{YYYY-MM-DD}.{ext}
```

ตัวอย่าง: `example-com_content-draft_2026-03-28.md`

Resolve a standalone article with `client_workspace.py route --client
./clients/{domain} --type content-draft-lite --filename
"{domain}_content-draft_{YYYY-MM-DD}.{ext}"`. For a complete article package,
use the `content-production-lite` route and its per-slug contract. Resolve schemas,
images, and publishing evidence with their own registered package or report route.

## Available Scripts

ใช้ scripts เหล่านี้สำหรับการวิเคราะห์อัตโนมัติ:
- `python skills/rainmojo-so-lite/scripts/content_formatter.py` แปลง Markdown เป็น HTML/Gutenberg/Shopify
## Reference files

- Agent definition: [agent.json](agent.json)
- For Google quality guidelines, see reference/google/

## Production handoff

This skill creates and reviews content; it does not upload media or write to
WordPress. For a complete article package, image production, and verified draft,
invoke `/rainmojo-so:content-production-lite`, which dispatches the
`content-production-orchestrator-lite`, after content QA passes.
