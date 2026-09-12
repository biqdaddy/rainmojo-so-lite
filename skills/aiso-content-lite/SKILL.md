---
name: aiso-content-lite
description: >
  Content quality and E-E-A-T assessment for AI citability -- evaluate experience, expertise,
  authoritativeness, trustworthiness, and content structure. Reports a qualitative level per
  dimension (ดี / พอใช้ / ต้องแก้), not a numeric score. (Lite edition for workshop use.)
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


# aiso content

## ขั้นที่ 0 ดึง HTML ดิบมาเก็บไว้ก่อน

**ต้องทำก่อนขั้นอื่นทั้งหมด** เพราะ WebFetch คืนเนื้อหาที่แปลงเป็นข้อความแล้ว
แท็กใน `<head>` และบล็อก JSON-LD ถูกตัดทิ้ง รวมถึงแอตทริบิวต์ `src` และ `href`
ของที่สกิลนี้ต้องใช้แล้วหายไปกับการแปลง คือ วันที่เผยแพร่และวันอัปเดต ชื่อผู้เขียน
ลิงก์ภายใน และร่องรอย mixed content
ถ้าประเมินจากผล WebFetch อย่างเดียว จะรายงานว่า ไม่มี ทั้งที่มีอยู่ ซึ่งเป็นผลลบลวง

```bash
mkdir -p work/{domain}/uploads
curl -sSL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120" \
  -m 25 "https://{domain}/" -o work/{domain}/uploads/home.html
```

ทำแบบเดียวกันกับทุกหน้าที่จะประเมิน ตั้งชื่อไฟล์ให้รู้ว่าเป็นหน้าไหน

**แล้วค่อยใช้ Grep กับไฟล์ที่ดาวน์โหลดมา** ไม่ใช่กับผล WebFetch
เช่น Grep `application/ld\+json` เพื่อหา structured data ที่บอกผู้เขียนและวันที่
Grep `src="http://` และ `href="http://` เพื่อดู mixed content

### ถ้าใช้คำสั่งพวกนี้ไม่ได้

**บาง host ไม่มีเครื่องมือรันคำสั่งให้** เช่น Cowork, Claude Desktop และ GPT desktop
ถ้าเป็นแบบนั้น ให้ทำแบบนี้แทน แล้วงานจะยังเดินต่อได้

1. บอกผู้ใช้ว่า **ขอให้ช่วยเปิดหน้าเว็บแล้วคัดลอกซอร์สมาให้**
   วิธีคือเปิดหน้านั้นในเบราว์เซอร์ กด `Ctrl+U` หรือ `Cmd+Option+U` เพื่อดู source
   แล้วเลือกทั้งหมด คัดลอก มาวางในแชท
2. ถ้าผู้ใช้ทำให้ได้ ให้ทำงานต่อจากซอร์สที่ได้มา ตามขั้นตอนเดิมทุกอย่าง
3. ถ้าผู้ใช้ไม่สะดวก ให้ใช้ WebFetch เท่าที่ได้ แล้ว**เขียนกำกับทุกหัวข้อที่กระทบว่า `ตรวจไม่ได้`**
   ห้ามเขียนว่า `ไม่มี` เพราะสองคำนี้คนละความหมาย และการเขียนผิดจะทำให้ผู้ใช้เข้าใจกลับด้าน

**บน Windows** ถ้ารันแล้วขึ้นว่าไม่รู้จักคำสั่ง ให้ลองใน Git Bash หรือ WSL
ถ้าไม่มีทั้งสองอย่าง ให้ใช้วิธีคัดลอกซอร์สในข้อ 1

## ขั้นตอนหลัก

Read and execute the agent workflow from [agent.json](agent.json).
Follow all phases and steps sequentially.

## กฎ

- **ก่อนเคลมว่า ไม่มีการอ้างอิงภายนอกเลย** ต้อง grep ลิงก์ออกนอกโดเมนใน HTML ดิบของทุกหน้าที่ดึงมา (หา `https://` ที่ไม่ใช่โดเมนตัวเอง) เจอแม้ลิงก์เดียวคำว่า เลย หรือ แม้แต่จุดเดียว ก็ใช้ไม่ได้แล้ว ให้รายงานตามจริงว่าน้อยและอยู่หน้าไหน
- ตัวเลขเชิงนับ เช่น จำนวนหัวข้อต่อบทความ ต้องบอกวิธีนับกำกับ (นับทั้งหน้า หรือเฉพาะส่วนเนื้อหา) และตัวเลขต้องมาจากการนับจริงในไฟล์ที่ดึงมา


- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`** สองคำนี้คนละความหมาย ถ้าเขียนผิดผู้ใช้จะสรุปกลับด้าน
- **ดึงข้อมูลไม่สำเร็จให้เขียน `ตรวจไม่ได้` ห้ามเขียน `ไม่มี`** สองคำนี้คนละความหมาย
  ไม่มี แปลว่าเห็นซอร์สแล้วและยืนยันว่าไม่มีจริง ตรวจไม่ได้ แปลว่ายังไม่ได้เห็น
  เขียนผิดคำเดียวผู้ใช้จะสรุปกลับด้าน แล้วไปแก้ของที่ไม่ได้เสีย
- **ทำได้บางส่วนต้องส่งส่วนนั้น** ห้ามจบด้วยตารางที่ทุกช่องเขียนว่าประเมินไม่ได้
  และห้ามปฏิเสธทั้งงานเพราะขาดข้อมูลบางอย่าง
- ในรายงานต้องติดป้ายทุกข้อว่า **ยืนยันแล้ว** คือเห็นหลักฐานจากซอร์สจริง
  หรือ **ต้องยืนยันเพิ่ม** คือยังไม่เห็น พร้อมบอกว่าขาดอะไรถึงจะยืนยันได้
- **การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์** ส่งเท่าที่ตรวจได้พร้อมป้ายกำกับเสมอ
- **ห้ามให้คะแนนรวม ห้ามคิดเปอร์เซ็นต์ ห้ามตั้งเกณฑ์ตัวเลขขึ้นเอง**
  ใช้ระดับ ดี พอใช้ ต้องแก้ ต่อมิติเท่านั้น

## ขอบเขตความเป็นเจ้าของ

- **citability เป็นของ `aiso-citability-lite`** สกิลนี้ไม่มีเกณฑ์ citability ของตัวเอง
  ห้ามพิมพ์คอลัมน์ Citability ในตารางหน้าที่ตรวจ และห้ามมีหัวข้อ Citability Assessment
  ถ้ามีผลจากสกิลนั้นในรอบเดียวกัน ให้อ้างผลนั้นภายใต้ชื่อ ผล citability ถ้าไม่มี ให้เขียนว่ายังไม่ได้ตรวจ
  ห้ามประเมินซ้ำ หนึ่งค่า หนึ่งเจ้าของ หนึ่งผลลัพธ์ทั่วทั้งรายงาน
- **ช่องว่างเนื้อหาเชิงแข่งขันเป็นของ `seo-content-gap-analysis-lite`** ข้อ Content Gaps ในคำแนะนำของสกิลนี้
  หมายถึงช่องว่าง E-E-A-T รายหน้าที่พบระหว่างตรวจเท่านั้น ห้ามออกแผน gap ชุดที่สอง

## การ์ด Tier 1 ของสกิลนี้

จบงานทุกครั้งด้วยการ์ดสรุปตามชั้นแสดงผล (`so-present-lite`): โหมด `audit` `dimensions` คือ E-E-A-T 4 มิติ แต่ละมิติ value = 1 เมื่อระดับ ดี, 0 เมื่อ ต้องแก้ และ max = 1 (หรือจำนวนหน้าที่ได้ระดับ ดี ต่อจำนวนหน้าที่ตรวจ เมื่อตรวจหลายหน้า), `key_risk` คือมิติที่ ต้องแก้ และกระทบหน้ามากที่สุด, `actions` คือ 4 ข้อแรกของ Quick Wins
ทุกค่าบนการ์ดคัดลอกจากไฟล์ผลลัพธ์ที่เพิ่งเขียน ห้ามประเมินเพิ่ม ข้อที่ตรวจไม่ได้ให้ขึ้นว่า ตรวจสอบไม่ได้
รุ่น Lite ไม่มีคะแนน จึงไม่ใส่บล็อก `score` ค่าใน `dimensions` คือจำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจ
เรนเดอร์ด้วย `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --summary <summary.json> --target auto --host {host}`
แล้วปิดด้วยบรรทัดส่งต่อไปยังไฟล์ผลลัพธ์ฉบับเต็ม ซึ่งต้องครบและไม่ถูกย่อ

## Output
### Naming convention

ไฟล์ที่สร้างต้องตั้งชื่อตาม pattern:

```
{domain}_ai-content_{YYYY-MM-DD}.{ext}
```

ตัวอย่าง: `example-com_ai-content_2026-03-28.md`

## การวางไฟล์ผลลัพธ์

สกิลนี้อยู่ในชุดที่ใช้โครงโฟลเดอร์ของสกิล `new-workspace-lite`

1. ผลลัพธ์ทุกไฟล์อยู่ใต้ `work/{domain}/`
2. ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์หัวข้อเดียวกัน ให้เขียนลง `00-baseline/` ถ้ามีแล้ว ให้เขียนลง `01-current/`
3. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร
4. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน ห้ามสร้างโครงเองแบบอื่น

## Reference files

- Agent definition: [agent.json](agent.json)
