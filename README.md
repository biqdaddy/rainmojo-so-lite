# RAINMOJO SO Lite

By [BIQDADDY](https://biqdaddy.com) for [RAINMOJO](https://rainmojo.com/) · Source: [github.com/biqdaddy/rainmojo-so-lite](https://github.com/biqdaddy/rainmojo-so-lite) · License: see [LICENSE](LICENSE)

ตรวจและแก้ AI Visibility ทั้งฝั่ง AEO และ GEO ทำรายงาน วางกลยุทธ์เนื้อหา และผลิตบทความขึ้น WordPress · **43 สกิล 17 agent**

รุ่นสำหรับผู้เรียนคอร์ส **AI Visibility Blueprint** ของ BIQDADDY

---

## ติดตั้งยังไง

**ลากไฟล์ `rainmojo-so-lite.plugin` มาวางในหน้าต่างแชท** ถ้าใช้ Cowork, Claude Desktop หรือ GPT desktop

ถ้าใช้ Claude Code, Codex, Gemini CLI หรือ Antigravity ให้ชี้ไปที่โฟลเดอร์นี้โดยตรง
วิธีเต็มอยู่ใน `INSTALL.md` ของชุดเครื่องมือ

---

## เริ่มยังไง

พิมพ์เป็นภาษาปกติได้เลย ไม่ต้องจำคำสั่ง ระบบจะเลือกให้เอง

**ครั้งแรกให้พิมพ์ว่า** `ตั้งโฟลเดอร์งานให้เว็บ example.com หน่อย`
เพื่อสร้างที่เก็บผลลัพธ์ก่อน แล้วค่อยสั่งงานอื่น

---

## มีอะไรอยู่ข้างใน

**สกิล 43 ตัว**

- `aiso-agent-readiness-lite`
- `aiso-brand-mentions-lite`
- `aiso-citability-lite`
- `aiso-content-lite`
- `aiso-crawlers-lite`
- `aiso-llmstxt-lite`
- `aiso-platform-lite`
- `aiso-schema-lite`
- `aiso-technical-lite`
- `compare-lite`
- `content-draft-lite`
- `content-production-lite`
- `meta-basics-lite`
- `new-client-lite`
- `new-workspace-lite`
- `rainmojo-so-lite`
- `report-lite`
- `seo-backlink-strategy-lite`
- `seo-competitor-lite`
- `seo-content-audit-lite`
- `seo-content-creation-lite`
- `seo-content-enhancement-lite`
- `seo-content-gap-analysis-lite`
- `seo-content-strategy-lite`
- `seo-experiment-lite`
- `seo-heading-matrix-lite`
- `seo-image-optimizer-lite`
- `seo-internal-linking-lite`
- `seo-keyword-clustering-lite`
- `seo-keyword-research-lite`
- `seo-local-seo-lite`
- `seo-migration-lite`
- `seo-schema-lite`
- `seo-video-lite`
- `seo-topical-authority-lite`
- `seo-website-overview-lite`
- `sitemap-architecture-lite`
- `so-present-lite`
- `technical-audit-lite`
- `wp-connect-lite`
- `wp-content-publisher-lite`
- `wp-publish-draft-lite`
- `wp-rest-ops-lite`

**agent 17 ตัว** ตัวคุมที่เรียกสกิลหลายตัวต่อกันให้เอง

- `aiso-ai-visibility-lite`
- `aiso-audit-lite`
- `aiso-content-review-lite`
- `aiso-platform-analysis-lite`
- `aiso-schema-audit-lite`
- `aiso-technical-audit-lite`
- `content-production-orchestrator-lite`
- `remediation-orchestrator-lite`
- `seo-audit-lite`
- `seo-content-lite`
- `seo-disavow-auditor-lite`
- `seo-keyword-lite`
- `seo-local-lite`
- `seo-offpage-lite`
- `seo-onpage-lite`
- `seo-technical-lite`
- `so-audit-lite`

---

## มีอะไรใหม่ใน 2.0.0

- ตามทัน rainmojo-so 3.14.1: ทะเบียนบอท 68 ชื่อของ 10 แพลตฟอร์ม, การ์ดความพร้อม 11 ใบ, robots.txt อ่านตาม RFC 9309, llms.txt ลดน้ำหนักตามหลักฐานปี 2026
- สกิลใหม่ `so-present-lite` (การ์ดสรุปในแชตทุก host, ให้เต็ม) และ `aiso-agent-readiness-lite` (เช็กลิสต์ 14 ข้อสำหรับ AI agent)
- ทุก agent ปิดงานด้วยการ์ด Tier 1 และไม่มี emoji ในไฟล์ใด
- ไม่มี aiso-task-completion (บริการวัด Task Completion Rate ของรุ่นเต็ม มีต้นทุน)

## ข้อควรรู้

- ผลลัพธ์ทุกอย่างเป็น**ข้อเสนอแนะ** ไม่ใช่การเปลี่ยนแปลงเว็บไซต์ คุณเป็นคนตัดสินใจนำไปใช้เอง
- **รหัสเข้าเว็บต้องอยู่ในไฟล์ `.env` เท่านั้น ห้ามพิมพ์ลงในบทสนทนา**
- รุ่นนี้ทำขึ้นเพื่อใช้เรียน ไม่ได้ออกแบบให้ใช้กับงานลูกค้าที่มีความเสี่ยงสูง
