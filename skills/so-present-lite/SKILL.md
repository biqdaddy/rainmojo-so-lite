---
name: so-present-lite
description: >
  Presentation layer for every RAINMOJO SO Lite answer: the Tier 1 quick-glance card in chat
  (dimension bars as checks passed out of checks run, 11-platform strip, query and competitor
  tables, one key risk, priority actions, transparency footer, hand-off to the Tier 2 file) and
  the seven response modes (quick fact, how-to, comparison, troubleshoot, audit, deployable,
  next steps). Builds or validates summary.json, renders it for the current host (Claude
  Desktop or Cowork widget, artifact HTML, Mermaid, ASCII tree, Markdown) with present.py,
  and lints emoji, glyph, em dash and pipe policy. Use when a run has finished and its result
  must be shown, when a card must be re-rendered for another host, or when a plain answer
  needs the mode structure. Not for producing the Tier 2 deliverable itself and never a
  substitute for it: every card value is copied from the deliverable, unmeasured values show
  as could not verify, and the Lite card carries counts, never a weighted score. (Lite edition.)
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash
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


# so-present-lite: ชั้นแสดงผลสองระดับและ 7 โหมดคำตอบ

Read and execute the agent workflow from [agent.json](agent.json).

> สืบทอด [_base/presentation-scaffold.md](../rainmojo-so-lite/_base/presentation-scaffold.md)
> (บันไดความสามารถของ host, 7 โหมด, กฎตายตัว) และ [_base/skill-scaffold.md](../rainmojo-so-lite/_base/skill-scaffold.md)
> อ่านทั้งสองไฟล์ครั้งเดียวก่อนเริ่ม

## สกิลนี้ทำอะไร

1. **สร้าง** `summary.json` (สัญญาข้อมูล `templates/widget/summary.schema.json`) จากไฟล์ผลลัพธ์ที่สกิลหรือ agent
   เพิ่งเขียน คัดลอกตัวเลข ห้ามคำนวณใหม่ ใส่ `transparency.could_not_verify` จากทุกข้อที่ตรวจไม่ได้ในรอบนั้น
   รอบตรวจที่มี JSON จากสคริปต์ ให้ประกอบด้วย
   `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/build_summary.py --agent <agent_readiness_lite json> --page <page_analyzer json> --robots <robots_generator json> --checklist <aiso-platform-lite checklist json> --sampling <aiso-brand-mentions-lite sampling json> --client "{ชื่อ}" --domain {domain} --lang th --skill {skillkey} --tier2 "{path ไฟล์ฉบับเต็ม}" --summary "{สรุป 2 ถึง 3 ประโยค}" --out {summary path}`
   ตัวประกอบไม่ประเมินอะไรเพิ่ม ข้อมูลที่ไม่มีก็ไม่มีบล็อกนั้น
2. **ตรวจและ lint**: `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --summary <file> --lint`
   (schema, emoji และ pictograph ต้องห้าม, em dash, pipe) lint ไม่ผ่านห้ามเรนเดอร์ แก้ JSON ไม่ใช่แก้ตัว lint
3. **เรนเดอร์ตาม host**: `present.py --summary <file> --target auto --host <host>`
   host ที่รู้จัก: `claude-desktop`, `cowork` (widget fragment), `artifact`, `chatgpt`, `gemini`, `cursor`, `vscode`,
   `preview` (HTML ไฟล์เดียว), `github`, `obsidian` (Mermaid), `claude-code`, `cli`, `terminal`, `email` (Markdown)
   host ที่ไม่รู้จักได้ Markdown `--target ascii` วาดการ์ดเดียวกันเป็นต้นไม้ ASCII ล้วนสำหรับ viewer ที่แสดง Mermaid เป็นโค้ดดิบ
4. **แสดง** ผ่านพื้นผิวของ host เอง: เครื่องมือ widget ในแชตถ้ามี, artifact หรือ canvas สำหรับ HTML, บล็อก `mermaid`
   เฉพาะที่เรนเดอร์ได้, บล็อก `text` สำหรับต้นไม้ ASCII, หรือข้อความ Markdown **ห้ามวางซอร์ส HTML ลงแชตเป็นข้อความ**
5. **ส่งต่อ**: บล็อกส่งต่อของการ์ดระบุไฟล์ชั้นที่ 2 (path ใต้ `work/{domain}/` หรือ route ของลูกค้า หรือ URL ของ artifact)
   และรูปแบบไฟล์ ไฟล์ชั้นที่ 2 ต้องครบและไม่ถูกแก้

## รุ่น Lite ต่างจากรุ่นเต็มตรงไหน

- **ไม่มีบล็อก `score`** เพราะไม่มีสกิลใดในรุ่นนี้ผลิตคะแนน ถ้าใส่ `score` โดยไม่มีตัวเลขในไฟล์ผลลัพธ์ ถือเป็น defect
- `dimensions[].value` คือ **จำนวนข้อที่ผ่าน** และ `max` คือ **จำนวนข้อที่ตรวจได้** ของด้านนั้น `status` เป็น `ok` เมื่อผ่านครบ,
  `critical` เมื่อไม่ผ่านเลย, `warning` เมื่อผ่านบางส่วน, `info` เมื่อไม่มีข้อที่ตรวจได้
- `platforms[].score` เป็น `null` เสมอ สถานะของการ์ดแพลตฟอร์มมาจากเช็กลิสต์ของ `aiso-platform-lite`
- `competitors[].score` คือจำนวนครั้งที่ถูกอ้างในคำถามที่สุ่มจริง (`max` = จำนวนคำถาม) จาก `aiso-brand-mentions-lite`
- แถบใน Markdown จึงอ่านว่า `[#####-----] 5/10` ซึ่งหมายถึง 5 ข้อจาก 10 ข้อ ไม่ใช่คะแนน

## การเลือกโหมด

| ผู้ใช้ถาม | โหมด | ฟิลด์ |
|---|---|---|
| คำถามข้อเท็จจริงสั้น ๆ | `quick_fact` | `tldr`, `bullets` |
| ทำยังไง | `howto` | `steps` (do, expect, owner) |
| เลือกอันไหน เทียบ | `comparison` | `comparison` (columns, rows พร้อม impact และ effort, recommendation) |
| ทำไมพัง แก้ยังไง | `troubleshoot` | `root_cause`, `steps` (3 ทางแก้เร็ว) |
| ตรวจ วิเคราะห์ รายงาน | `audit` | `dimensions`, `platforms`, `query_matrix`, `competitors`, `key_risk`, `actions`, `transparency` |
| ขอไฟล์ สร้าง ส่งออก | `deployable` | `deployables` (filename, language, content, path) |
| ทุกครั้ง | footer | `next_steps` (2 ถึง 3 คำสั่งที่พิมพ์ต่อได้ทันที), `handoff` |

บล็อกเสริมใช้ได้ทุกโหมด: `mockup` (ตัวอย่างคำตอบ AI), `diff` (ก่อนและหลัง), `roles` (ผู้บริหาร นักพัฒนา คนเขียน),
`checklist` (ป้ายผู้รับผิดชอบ), `dimensions[].history` (sparkline จาก `compare-lite` เป็นจำนวนข้อที่ผ่านของแต่ละรอบ)

## Output
### Naming convention

```
{domain}_{skillkey}_{YYYY-MM-DD}_summary.json
```

รอบที่ใช้ `work/{domain}/` เขียนไว้ที่ `work/{domain}/04-reports/` ข้างรายงานฉบับเต็ม
รอบที่ใช้ client workspace เขียนตาม route `report-data` ที่ `client_workspace.py route` คืนมา
ไฟล์การ์ดที่เรนเดอร์ (เมื่อ host ต้องการไฟล์ เช่นอัปโหลดเป็น artifact) ชื่อ `{domain}_{skillkey}_{YYYY-MM-DD}_card.html` ที่โฟลเดอร์เดียวกัน
คำถามธรรมดาที่ไม่มี workspace เก็บ summary ไว้ในหน่วยความจำแล้วเรนเดอร์ลงแชตตรง ๆ ไม่เขียนไฟล์

## ตัวอย่างและการตรวจตัวเอง

- `templates/widget/samples/audit-ai-visibility.json` (audit, en) และตัวอย่างไทย 5 โหมด
  (`quick_fact-th`, `howto-th`, `comparison-th`, `troubleshoot-th`, `deployable-th`)
- `present.py --self-test` lint ทุกตัวอย่างและเรนเดอร์ครบทุก target ต้องขึ้น `SELF-TEST PASS`
- `build_summary.py --self-test` ยืนยันว่าการ์ดจากสคริปต์ Lite ไม่มีบล็อก `score` และมิติเป็นจำนวนนับ

## Reference files

- Agent definition: [agent.json](agent.json)
- สัญญาข้อมูล: `templates/widget/summary.schema.json`; ป้ายข้อความ: `templates/widget/labels.json`; ไอคอน SVG: `templates/widget/icons.json`
- โหมดและนโยบาย glyph: `reference/frameworks/presentation-modes.json`
- สคริปต์: `scripts/present.py`, `scripts/present_html.py`, `scripts/build_summary.py`

## กฎ

- **ทุกค่าบนการ์ดคัดลอกจากไฟล์ผลลัพธ์** ค่าที่วัดไม่ได้แสดงเป็น ตรวจสอบไม่ได้ พร้อมเหตุใน `transparency.could_not_verify` ห้ามประเมินเพื่อเติมช่อง
- **ห้าม emoji และ pictograph ทุกพื้นผิว** glyph ตามรายการอนุญาตใช้ได้เฉพาะแชตและ Markdown การ์ด HTML ใช้ไอคอน SVG inline เท่านั้น
- **ห้าม em dash และ pipe ในข้อความที่มองเห็น** (ตัวคั่นตารางใน Markdown เป็นโครงสร้าง ไม่นับ)
- สีสถานะเป็นค่าคงที่ตามความหมาย มีเพียง `--brand-primary`, `--brand-accent`, `--brand-accent-ink` ที่เปลี่ยนตามลูกค้า
- ภาษาตาม `meta.lang` ของโปรไฟล์ลูกค้า การ์ดกับไฟล์ฉบับเต็มใช้ภาษาเดียวกัน
