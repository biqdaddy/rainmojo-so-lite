---
name: rainmojo-so-lite
description: >
  จุดเริ่มต้นของปลั๊กอิน บอกว่ามีสกิลอะไรบ้าง ควรใช้ตัวไหนกับงานแบบไหน และเก็บไฟล์อ้างอิงกลางที่สกิลอื่นเรียกใช้
  ใช้เมื่อผู้ใช้ถามว่าปลั๊กอินนี้ทำอะไรได้บ้าง เริ่มยังไง ควรใช้สกิลไหน หรือพิมพ์ว่า help
allowed-tools:
  - Read
  - Grep
  - Glob
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


# RAINMOJO SO Lite

สกิลนี้เป็น**จุดเริ่มต้น** ไม่ได้ตรวจเว็บเอง แต่บอกว่าควรไปใช้ตัวไหนต่อ
และเป็นที่เก็บไฟล์อ้างอิงกลางที่สกิลกลุ่มผลิตเนื้อหาเรียกใช้

---

## ถ้าผู้ใช้เพิ่งเริ่ม ให้ตอบแบบนี้

**ขั้นแรกเสมอคือ `new-workspace-lite`** เพื่อสร้างโฟลเดอร์ `work/{domain}/` ให้ผลลัพธ์ทุกอย่างมีที่อยู่
ถ้ายังไม่ได้ทำ สกิลอื่นจะเขียนไฟล์กระจัดกระจายแล้วหากันไม่เจอ

แล้วถามผู้ใช้ว่าอยากได้อะไร แล้วชี้ไปตามตารางนี้

| ผู้ใช้อยากรู้ว่า | ให้ใช้ |
|---|---|
| AI มองเห็นเว็บเราไหม ครบทุกด้าน | agent `aiso-audit-lite` |
| SEO พื้นฐานของเว็บเป็นยังไง | agent `seo-audit-lite` |
| อยากได้ทั้งสองอย่างในรอบเดียว | agent `so-audit-lite` |
| บอทของ AI เข้าเว็บได้ไหม | สกิล `aiso-crawlers-lite` |
| ควรเขียนอะไรก่อนหลัง | agent `seo-content-lite` |
| คู่แข่งคือใคร เขาได้เปรียบตรงไหน | agent `seo-offpage-lite` |
| อยากเขียนบทความแล้วส่งขึ้นเว็บ | agent `content-production-orchestrator-lite` |
| แก้เว็บไปแล้ว อยากรู้ว่าดีขึ้นไหม | สกิล `compare-lite` |
| อยากได้รายงานรวมส่งลูกค้า | สกิล `report-lite` |
| AI agent (ChatGPT agent, Claude in Chrome) กดใช้เว็บเราได้ไหม | สกิล `aiso-agent-readiness-lite` |
| อยากได้การ์ดสรุปในแชตจากผลที่ตรวจไปแล้ว | สกิล `so-present-lite` |

**ถ้าไม่แน่ใจ ให้เริ่มที่ `so-audit-lite`** เพราะครอบคลุมที่สุด แล้วค่อยเจาะทีหลัง

---

## สกิลทั้งหมด 43 ตัว แบ่ง 9 กลุ่ม

| กลุ่ม | สกิล |
|---|---|
| เปิดงานและจบงาน | `new-workspace-lite` `report-lite` `compare-lite` `so-present-lite` |
| ตรวจฝั่ง AI | `aiso-crawlers-lite` `aiso-llmstxt-lite` `aiso-schema-lite` `aiso-technical-lite` `aiso-content-lite` `aiso-citability-lite` `aiso-platform-lite` `aiso-brand-mentions-lite` `aiso-agent-readiness-lite` |
| ตรวจฝั่ง SEO | `seo-website-overview-lite` `technical-audit-lite` `seo-heading-matrix-lite` `meta-basics-lite` `seo-schema-lite` `seo-internal-linking-lite` `seo-image-optimizer-lite` `sitemap-architecture-lite` |
| คำค้นและช่องว่าง | `seo-keyword-research-lite` `seo-keyword-clustering-lite` `seo-content-gap-analysis-lite` `seo-competitor-lite` `seo-topical-authority-lite` |
| ตรวจและปรับเนื้อหา | `seo-content-audit-lite` `seo-content-enhancement-lite` `seo-content-strategy-lite` `seo-video-lite` |
| นอกเว็บและท้องถิ่น | `seo-local-seo-lite` `seo-backlink-strategy-lite` |
| โรงงานเนื้อหา | `new-client-lite` `seo-content-creation-lite` `content-production-lite` `wp-rest-ops-lite` `wp-content-publisher-lite` |
| เส้นทางง่าย | `content-draft-lite` `wp-connect-lite` `wp-publish-draft-lite` |
| ย้ายเว็บและพิสูจน์ผล | `seo-migration-lite` `seo-experiment-lite` |

รายละเอียดของแต่ละตัวอยู่ใน `CLAUDE.md` ของปลั๊กอิน

---

## ไฟล์อ้างอิงกลางในโฟลเดอร์นี้

โฟลเดอร์นี้เก็บของที่สกิลกลุ่มโรงงานเนื้อหาเรียกใช้

| โฟลเดอร์ | คืออะไร |
|---|---|
| `reference/` | ข้อกำหนดและตัวอย่างที่สกิลผลิตเนื้อหาอ่าน |
| `scripts/` | สคริปต์ Python ที่สกิลเรียกใช้ ทุกตัวมี `--self-test`: `client_workspace.py`, `content_pipeline.py`, `content_formatter.py`, `image_production.py`, `wordpress_publisher.py`, `robots_generator.py`, `page_analyzer.py`, `agent_readiness_lite.py`, `ai_platforms.py`, `present.py`, `present_html.py`, `build_summary.py`, `routing_instruction_gate.py`, `presentation_instruction_gate.py` |
| `templates/widget/` | สัญญาข้อมูลการ์ด Tier 1 (`summary.schema.json`), ป้ายข้อความ, ไอคอน SVG, สไตล์ และตัวอย่าง 6 โหมด |
| `reference/frameworks/ai-platform-registry.json` | ทะเบียนบอท 68 token และ 11 การ์ดของ 10 แพลตฟอร์ม ข้อเท็จจริงสาธารณะ ไม่มีน้ำหนักคะแนน |
| `_base/presentation-scaffold.md` | ชั้นแสดงผลสองระดับและ 7 โหมดคำตอบที่ทุกสกิลสืบทอด |
| `clients/demo-client/` | ตัวอย่างโครงโฟลเดอร์ลูกค้า ใช้เป็นแบบตอนสร้างของจริง |
| `_base/` | แบบร่างโครงสกิล |

**ห้ามแก้ไฟล์ในโฟลเดอร์เหล่านี้ระหว่างทำงานให้ลูกค้า** เพราะสกิลอื่นอ่านจากที่นี่ร่วมกัน
ถ้าอยากได้ค่าเฉพาะลูกค้ารายไหน ให้ไปตั้งในโฟลเดอร์ของลูกค้ารายนั้นแทน

---

## กฎ

- สกิลนี้ **ไม่ตรวจเว็บเองและไม่เขียนไฟล์รายงาน** หน้าที่เดียวคือชี้ทางและเก็บไฟล์อ้างอิง
- ถ้าผู้ใช้ขอให้ตรวจเว็บ ให้เรียกสกิลหรือ agent ที่ตรงกับงานทันที **ห้ามตอบเองแบบเดา**
- ถ้าผู้ใช้ถามถึงสกิลที่ไม่มีในรายการข้างบน ให้บอกตรง ๆ ว่าไม่มีในรุ่นนี้ แล้วเสนอตัวที่ใกล้เคียงที่สุด
