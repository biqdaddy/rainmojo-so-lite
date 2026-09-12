---
name: aiso-citability-lite
description: >
  AI citability assessment and optimization. Analyzes web page content to determine how likely
  AI systems (ChatGPT, Claude, Perplexity, Gemini) are to cite or quote passages from the page.
  Gives a qualitative assessment per category (ดี / พอใช้ / ต้องแก้) with specific rewrite
  suggestions. (Lite edition.)
allowed-tools:
  - Read
  - Grep
  - Glob
  - WebFetch
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


# aiso citability

Read and execute the agent workflow from [agent.json](agent.json).
Follow all phases and steps sequentially.

## ขอบเขตและการแบ่งงาน

- สกิลนี้มีโหมดเดียวคือ **ตรวจหน้าที่มีอยู่จริง** ต้องมี URL หรือซอร์สของหน้าที่เผยแพร่แล้ว
  ผลคือระดับ ดี พอใช้ ต้องแก้ ต่อย่อหน้า ตารางย่อหน้าที่หยิบไปอ้างง่ายและยาก และข้อเสนอเขียนใหม่รายย่อหน้า
- **การออกแบบจุดสกัดข้อมูลก่อนเขียนไม่ใช่ของสกิลนี้** ถ้าผู้ใช้ส่งมาแต่โครงหัวข้อหรือบรีฟของหน้าที่ยังไม่มี
  ให้ส่งต่อไป `seo-content-creation-lite` (ขั้น W4 ซึ่งเป็นเจ้าของ grouper question, คำแกนตรงคำต่อคำ,
  เพดานกันยัดคำ และ snippet cut test) ห้ามประเมินจากโครงเปล่า และห้ามตั้งชุดกฎออกแบบซ้ำที่นี่
  ไม่แน่ใจว่ามีหน้าจริงไหม ให้ถามหนึ่งครั้งก่อน
- **คะแนน E-E-A-T เป็นของ `aiso-content-lite`** เมื่อรันทั้งคู่ในรายงานเดียว ให้แสดงสองผลแยกกันโดยมีชื่อกำกับชัด
  ห้ามเฉลี่ยรวม และห้ามให้ผลหนึ่งแทนอีกผล สกิลนั้นไม่ทำ citability เอง และสกิลนี้ไม่ทำ E-E-A-T เอง
- การนับคำและความยาวย่อหน้า นับทุก code point เป็น 1 รวมสระและวรรณยุกต์ไทย

## การ์ด Tier 1 ของสกิลนี้

จบงานทุกครั้งด้วยการ์ดสรุปตามชั้นแสดงผล (`so-present-lite`): โหมด `audit` `dimensions` คือจำนวนย่อหน้าที่ได้ระดับ ดี ต่อจำนวนย่อหน้าที่ตรวจ แยกตามหมวดที่ตรวจ, `diff` คือย่อหน้าเดียวที่เขียนใหม่ (before, after) จากตารางข้อเสนอ, `mockup` คือตัวอย่างคำตอบ AI ที่ยกย่อหน้าที่หยิบง่ายที่สุดไปอ้าง โดย `client_cited` เป็นจริงเฉพาะเมื่อพบในคำตอบที่สุ่มจริง, `actions` คือ 4 ย่อหน้าที่ควรเขียนใหม่ก่อน
ทุกค่าบนการ์ดคัดลอกจากไฟล์ผลลัพธ์ที่เพิ่งเขียน ห้ามประเมินเพิ่ม ข้อที่ตรวจไม่ได้ให้ขึ้นว่า ตรวจสอบไม่ได้
รุ่น Lite ไม่มีคะแนน จึงไม่ใส่บล็อก `score` ค่าใน `dimensions` คือจำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจ
เรนเดอร์ด้วย `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --summary <summary.json> --target auto --host {host}`
แล้วปิดด้วยบรรทัดส่งต่อไปยังไฟล์ผลลัพธ์ฉบับเต็ม ซึ่งต้องครบและไม่ถูกย่อ

## Output
### Naming convention

ไฟล์ที่สร้างต้องตั้งชื่อตาม pattern:

```
{domain}_citability-review_{YYYY-MM-DD}.{ext}
```

ตัวอย่าง: `example-com_citability-review_2026-03-28.md`

## การวางไฟล์ผลลัพธ์

สกิลนี้อยู่ในชุดที่ใช้โครงโฟลเดอร์ของสกิล `new-workspace-lite`

1. ผลลัพธ์ทุกไฟล์อยู่ใต้ `work/{domain}/`
2. ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์หัวข้อเดียวกัน ให้เขียนลง `00-baseline/` ถ้ามีแล้ว ให้เขียนลง `01-current/`
3. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร
4. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน ห้ามสร้างโครงเองแบบอื่น

## Reference files

- Agent definition: [agent.json](agent.json)

## กฎ

- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`** สองคำนี้คนละความหมาย ถ้าเขียนผิดผู้ใช้จะสรุปกลับด้าน
- **ทำได้บางส่วนต้องส่งส่วนนั้นเสมอ** ห้ามส่งตารางที่ทุกช่องว่าง และห้ามปฏิเสธทั้งงานเพราะขาดข้อมูลบางอย่าง ให้ติดป้ายว่าข้อไหนยืนยันแล้ว ข้อไหนต้องยืนยันเพิ่ม · การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์
