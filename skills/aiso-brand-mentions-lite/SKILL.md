---
name: aiso-brand-mentions-lite
description: >
  Brand mention scanner for AI visibility. Counts brand presence across the platforms that
  AI models rely on for entity recognition and citation decisions (YouTube, Reddit,
  Wikipedia, LinkedIn) and reports a per-platform mention count table with
  platform-specific recommendations. (Lite edition.)
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


# aiso brand-mentions

Read and execute the agent workflow from [agent.json](agent.json).
Follow all phases and steps sequentially.

## ตารางคำถามที่สุ่มถาม AI และ 6 มิติการมองเห็น (สกิลนี้เป็นเจ้าของ)

สกิลนี้เป็นเจ้าของ **ตารางคำถามที่สุ่มถาม AI จริง** และ 6 มิติที่แสดงบนการ์ด Tier 1
`aiso-platform-lite` และ `aiso-citability-lite` อ้างผลจากที่นี่ ไม่สุ่มถามเอง

**วิธีสุ่ม**

1. เลือกคำถาม 8 ถึง 18 ข้อจากชุดคำค้นที่ผ่านประตูคัดคำค้นของ `aiso-platform-lite` แล้ว
   ผสมสี่แบบ คือ คำถามเกี่ยวกับแบรนด์ (X เชื่อถือได้ไหม, รีวิว X), คำถามเปรียบเทียบ (X กับ Y, ทางเลือกแทน X),
   คำถามหมวดหมู่ (คลินิกไหนดีในกรุงเทพ) และคำถามให้ความรู้ที่หน้าเว็บของลูกค้าตอบได้ 1 ถึง 2 ข้อ
2. ถามคำเดียวกันทุกคำบนทุกแพลตฟอร์มที่เข้าถึงได้ (Perplexity, ChatGPT, Gemini, Copilot, Grok เมื่อมีบัญชี X,
   Claude เมื่อเปิดค้นเว็บ) บันทึกวันที่ แพลตฟอร์ม ข้อความคำตอบจริงหรือภาพหน้าจอใน `work/{domain}/uploads/ai-answers/`
   และ URL ทุกอันที่ถูกอ้าง
3. **ห้ามให้ผู้ช่วยแต่งคำตอบขึ้นเอง** แพลตฟอร์มที่ไม่ได้ถามจริง ไม่มีในตาราง และลงไว้ในรายการ ตรวจไม่ได้
4. ถ้ามีเวลา ถามคำถามแบรนด์หนึ่งข้อซ้ำในอีกวัน มิติความสม่ำเสมอต้องมีสองรอบ รอบเดียวลงว่า ตรวจไม่ได้

**แถวของตาราง** `query, platform, cited, position, sentiment, evidence_url`
`cited` เป็น `yes` เมื่อเว็บลูกค้าถูกอ้างเป็นแหล่ง, `partial` เมื่อเอ่ยถึงหน้าโดยไม่มีลิงก์, `context` เมื่อเอ่ยชื่อแบรนด์ในเนื้อคำตอบเท่านั้น, `no` เมื่อไม่ปรากฏ
`position` คือลำดับที่ถูกอ้าง `#1` ถึง `#n`, `displaced` เมื่อคู่แข่งมาแทนตำแหน่งเดิม, `not_found`
`sentiment` คือ `positive`, `neutral`, `mixed`, `negative` ตัดสินจากข้อความที่พูดถึงแบรนด์

**6 มิติ รายงานเป็นจำนวนนับ ไม่แปลงเป็นคะแนน**

| มิติ | รายงานอะไร |
|---|---|
| presence | จำนวนคำถามที่แบรนด์ปรากฏ (cited, partial หรือ context) ต่อจำนวนคำถามที่สุ่ม |
| position | รายการลำดับที่ถูกอ้างต่อคำถาม และจำนวนครั้งที่เป็นอันดับแรก |
| accuracy | จำนวนข้อความเกี่ยวกับแบรนด์ที่ตรงกับข้อเท็จจริงบนเว็บ ต่อจำนวนข้อความทั้งหมด พร้อมรายการที่ผิดทุกข้อ |
| completeness | จำนวนบริการหรือสินค้าหลักที่ถูกเอ่ยถึง ต่อจำนวนบริการหลักทั้งหมด |
| sentiment | จำนวนคำถามในแต่ละอารมณ์ positive, neutral, mixed, negative |
| consistency | จำนวนคำถามแบรนด์ที่ผลสองรอบตรงกัน ต่อจำนวนที่ถามซ้ำ (รอบเดียว = ตรวจไม่ได้) |

**ส่งต่อ** เขียน `{domain}_ai-answer-sampling_{YYYY-MM-DD}.json` รูปแบบ
`{"query_matrix": [...แถวตามข้างบน...], "dimensions": [{"key", "label", "value": จำนวนที่ผ่าน, "max": จำนวนทั้งหมด, "status"}], "competitors": [{"name", "tagline", "score": จำนวนครั้งที่ถูกอ้าง, "max": จำนวนคำถาม, "is_client"}]}`
ให้ `build_summary.py --sampling` อ่าน และเขียนข้อเท็จจริงนอกเว็บ (`x_account_active`, `reddit_presence`, `youtube_channel_active`,
`wikidata_present`, `knowledge_panel_present`, `tech_hub_presence`) ไว้ในรายงานเพื่อให้ `aiso-platform-lite` อ้างต่อ เฉพาะข้อที่ตรวจจริง

## การ์ด Tier 1 ของสกิลนี้

จบงานทุกครั้งด้วยการ์ดสรุปตามชั้นแสดงผล (`so-present-lite`): โหมด `audit` `query_matrix` และ `competitors` จากไฟล์ sampling, `dimensions` คือ 6 มิติแบบจำนวนนับ, `key_risk` คือคำถามแบรนด์ที่คู่แข่งมาแทน หรือข้อความที่ AI พูดผิดเกี่ยวกับแบรนด์, `actions` คือช่องทางที่ยังขาดไม่เกิน 4 ข้อ
ทุกค่าบนการ์ดคัดลอกจากไฟล์ผลลัพธ์ที่เพิ่งเขียน ห้ามประเมินเพิ่ม ข้อที่ตรวจไม่ได้ให้ขึ้นว่า ตรวจสอบไม่ได้
รุ่น Lite ไม่มีคะแนน จึงไม่ใส่บล็อก `score` ค่าใน `dimensions` คือจำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจ
เรนเดอร์ด้วย `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --summary <summary.json> --target auto --host {host}`
แล้วปิดด้วยบรรทัดส่งต่อไปยังไฟล์ผลลัพธ์ฉบับเต็ม ซึ่งต้องครบและไม่ถูกย่อ

## Output
### Naming convention

ไฟล์ที่สร้างต้องตั้งชื่อตาม pattern:

```
{domain}_brand-mentions_{YYYY-MM-DD}.{ext}
```

ตัวอย่าง: `example-com_brand-mentions_2026-03-28.md`

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
