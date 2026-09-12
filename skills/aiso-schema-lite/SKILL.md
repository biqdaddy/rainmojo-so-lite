---
name: aiso-schema-lite
description: >
  Schema.org structured data audit and generation optimized for AI discoverability,
  detect, validate, and generate JSON-LD markup. (Lite edition.)
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


# aiso schema

Read and execute the agent workflow from [agent.json](agent.json).
Follow all phases and steps sequentially.
**ก่อนเริ่ม workflow ให้ทำขั้นที่ 0 ด้านล่างให้เสร็จก่อน**

## ขั้นที่ 0 ดึง HTML ดิบมาเก็บไว้ก่อน

**ต้องทำก่อนขั้นอื่นทั้งหมด** เพราะ WebFetch คืนเนื้อหาที่แปลงเป็นข้อความแล้ว
บล็อก `<script type="application/ld+json">` ที่อยู่ใน `<head>` ถูกตัดทิ้ง
ถ้าตรวจจากผล WebFetch อย่างเดียว จะรายงานว่า ไม่มี schema ทั้งที่มีอยู่จริง ซึ่งเป็นผลลบลวง

```bash
mkdir -p work/{domain}/uploads
curl -sSL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120" \
  -m 25 "https://{domain}/" -o work/{domain}/uploads/home.html
```

ทำแบบเดียวกันกับหน้าอื่นที่ต้องตรวจ เช่น หน้าบทความหนึ่งหน้าและหน้าบริการหนึ่งหน้า
ตั้งชื่อไฟล์ให้ต่างกัน แล้ว **ใช้ Grep กับไฟล์ที่ดาวน์โหลดมา** ไม่ใช่กับผล WebFetch
คำที่ใช้ค้นคือ `application/ld+json` `itemscope` `itemtype` `typeof` และ `@type`

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

## กฎ

- **ดึงข้อมูลไม่สำเร็จให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`**
  ไม่มี แปลว่าเห็นซอร์สแล้วและไม่พบ ตรวจไม่ได้ แปลว่ายังไม่ได้เห็นซอร์ส
  สองคำนี้คนละความหมาย เขียนผิดจะทำให้ผู้ใช้สรุปกลับด้าน
  ทุกช่องที่เขียนว่าตรวจไม่ได้ ต้องบอกด้วยว่าขาดอะไรถึงจะตรวจได้
- **ทำได้แค่ไหนให้ส่งแค่นั้น ห้ามส่งงานเปล่าและห้ามปฏิเสธทั้งงาน**
  ตรวจได้บางหน้าหรือบางข้อในเช็กลิสต์ ให้ส่งส่วนที่ตรวจได้เสมอ
  พร้อมติดป้ายทุกบรรทัดว่า ยืนยันแล้ว หรือ ต้องยืนยันเพิ่ม
  แล้วแยกรายการที่ยังตรวจไม่ได้ไว้ท้ายรายงานพร้อมบอกว่าต้องใช้อะไรเพิ่ม
  **การอ้างข้อจำกัดเพื่อไม่ส่งงาน ไม่ใช่ความซื่อสัตย์**
- JSON-LD ที่สร้างให้ใหม่ ให้ใส่เฉพาะข้อมูลที่หาเจอจริงบนเว็บ
  ช่องที่ยังไม่รู้ให้เว้นเป็นตัวยึดไว้แล้วบอกผู้ใช้ว่าต้องเติมอะไร ห้ามเดาข้อมูลธุรกิจ

## วินัยการอ้างประโยชน์ (ถ้อยคำที่ส่งลูกค้า)

ทุกข้อค้นพบและคำแนะนำในรายงานของสกิลนี้ ระบุประโยชน์ของ markup ได้สามอย่างเท่านั้น คือ
ช่วยให้ระบบเข้าใจหน้า, มีสิทธิ์แสดง rich result, และพร้อมให้ AI หยิบไปอ้าง
**ห้ามสัญญาหรือใช้ถ้อยคำที่ทำให้เข้าใจว่า markup อย่างเดียวทำให้อันดับดีขึ้น** markup ทำให้หน้าเข้าใจได้
มีสิทธิ์ และอ้างได้ ส่วนอันดับได้มาจากที่อื่น กฎเดียวกันนี้ผูกกับ `seo-schema-lite`

## เมื่อ `technical-audit-lite` รันในรอบเดียวกัน

ขั้น Structured Data for AI ของสกิลนั้นเป็นทางสำรองสำหรับรอบที่ตรวจ SEO อย่างเดียว ไม่ใช่คำตัดสินที่สอง
ผลของสกิลนี้เป็นผลหลักไม่ว่าใครรันก่อน และให้พับผลสำรองนั้นเข้ารายงานของสกิลนี้ ไม่วางคู่กัน
สกิลนี้ไม่แตะข้อตรวจอื่นของสกิลนั้น (indexability, ลิงก์เสีย, Core Web Vitals, responsive)

## Article, paywall และข้อมูลลิขสิทธิ์ภาพ

- **ชุด property ของ Article** ผู้เขียนเป็นบุคคลหรือองค์กรที่มีชื่อและ URL ที่ระบุตัวได้
  (ชื่อโดยไม่มี URL คือผู้เขียนที่ระบุตัวไม่ได้ ไม่ใช่ field ที่ขาดได้), มีทั้ง datePublished และ dateModified ในรูปแบบ ISO 8601,
  headline ไม่เกินความยาวที่กำหนดพร้อมบันทึกจำนวนที่นับได้, และ image เป็น array ของภาพเดียวกันในสัดส่วน 1x1, 4x3, 16x9
- **ชนิดร่วมสามชนิด ใส่เฉพาะเมื่อเข้าเงื่อนไข** speakable เมื่อมีย่อหน้าที่เหมาะกับการอ่านออกเสียง,
  VideoObject เมื่อฝังวิดีโอ (ข้อกำหนดเฉพาะวิดีโอเป็นของ `seo-video-lite`), LiveBlogPosting เมื่อรายงานเหตุการณ์สด ไม่มีชนิดใดเป็นค่าตั้งต้น
- **markup ของ paywall เป็นแค่ครึ่งเดียว** สิทธิ์ถูก crawl ยังต้องมีการตั้งค่าให้ผู้อ่านที่มาจากผลค้นหาอ่านบทความเต็มได้
  จำนวนครั้งที่กำหนดต่อเดือน markup โดยไม่มีการตั้งค่านั้นทำให้ผลค้นหาพังตอนคลิก ห้ามรายงานว่าผ่านจาก markup อย่างเดียว
  บันทึกจำนวนที่ลูกค้าตั้งไว้ หรือ ตรวจไม่ได้ ห้ามแนะนำตัวเลขเอง
- **ข้อมูลลิขสิทธิ์ภาพ** ใส่ structured data ระดับภาพหรือ metadata ในไฟล์ภาพบนหน้าที่แสดงภาพ เพื่อให้ผลค้นหาภาพ
  แสดงผู้สร้าง เครดิต และสิทธิ์การใช้ ข้อนี้ชนกับการล้าง metadata ของสายผลิตภาพ ต้องตรวจก่อนว่าลูกค้าประกาศข้อยกเว้น
  field ลิขสิทธิ์ไว้หรือไม่ ไม่งั้น markup จะไม่มีอะไรรองรับ
- **คำขอถอดเนื้อหาละเมิดลิขสิทธิ์จำนวนมากเป็นความเสี่ยงต่อการมองเห็น** ไม่ใช่เรื่องกฎหมายอย่างเดียว บันทึกในหมวดความเสี่ยงของรายงาน

การตัดสินใจว่าจะแสดงข้อมูลอะไรบนหน้าเป็นของเจ้าของเนื้อหา และกฎว่า markup ต้องสะท้อนสิ่งที่มองเห็นระบุไว้ครั้งเดียวที่ `seo-schema-lite`
การวาง LocalBusiness เป็นของ `seo-local-seo-lite`

## การ์ด Tier 1 ของสกิลนี้

จบงานทุกครั้งด้วยการ์ดสรุปตามชั้นแสดงผล (`so-present-lite`): โหมด `audit` `dimensions` คือจำนวนข้อ checklist 12 ข้อที่ผ่านต่อจำนวนที่ตรวจได้, `deployables` คือ JSON-LD ที่สร้างใหม่ในรอบนี้ (filename, language json, content), `key_risk` คือ markup ที่ผิดหรือขาดที่กระทบมากที่สุด, `actions` ไม่เกิน 4 ข้อ
ทุกค่าบนการ์ดคัดลอกจากไฟล์ผลลัพธ์ที่เพิ่งเขียน ห้ามประเมินเพิ่ม ข้อที่ตรวจไม่ได้ให้ขึ้นว่า ตรวจสอบไม่ได้
รุ่น Lite ไม่มีคะแนน จึงไม่ใส่บล็อก `score` ค่าใน `dimensions` คือจำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจ
เรนเดอร์ด้วย `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --summary <summary.json> --target auto --host {host}`
แล้วปิดด้วยบรรทัดส่งต่อไปยังไฟล์ผลลัพธ์ฉบับเต็ม ซึ่งต้องครบและไม่ถูกย่อ

## Output
### Naming convention

ไฟล์ที่สร้างต้องตั้งชื่อตาม pattern:

```
{domain}_aiso-schema_{YYYY-MM-DD}.{ext}
```

ตัวอย่าง: `example-com_aiso-schema_2026-03-28.md`

## การวางไฟล์ผลลัพธ์

สกิลนี้อยู่ในชุดที่ใช้โครงโฟลเดอร์ของสกิล `new-workspace-lite`

1. ผลลัพธ์ทุกไฟล์อยู่ใต้ `work/{domain}/`
2. ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์หัวข้อเดียวกัน ให้เขียนลง `00-baseline/` ถ้ามีแล้ว ให้เขียนลง `01-current/`
3. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร
4. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน ห้ามสร้างโครงเองแบบอื่น

## Reference files

- Agent definition: [agent.json](agent.json)
