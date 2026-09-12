---
name: seo-schema-lite
description: >
   Schema.org markup generation for business entities, local SEO, and AI citation readiness with JSON-LD structured data implementation (Lite edition for workshop use.)
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


# schema markup generator

Read and execute the agent workflow from [agent.json](agent.json).
Follow all phases and steps sequentially.

## ขั้นแรกสุด ดึง HTML ดิบมาก่อน

**ห้ามข้ามขั้นนี้** เพราะ WebFetch คืนเนื้อหาที่แปลงเป็นข้อความแล้ว
ของที่อยู่ใน `<head>` เช่น title, meta description, canonical และ JSON-LD **ถูกตัดทิ้งหมด**
ถ้าตรวจจากผล WebFetch อย่างเดียว จะรายงานว่า **ไม่มี** ทั้งที่มีอยู่จริง ซึ่งเป็นผลลบลวง

```bash
mkdir -p work/{domain}/uploads
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"
curl -sSL -A "$UA" -m 25 "https://{domain}/" -o work/{domain}/uploads/home.html
```

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

ทำแบบเดียวกันกับทุกหน้าที่ต้องตรวจ ตั้งชื่อไฟล์ตามหน้า แล้ว **ใช้ Grep กับไฟล์ที่ดาวน์โหลดมา**

ตัวอย่างคำสั่งที่ใช้บ่อย

```bash
grep -o '<title>[^<]*</title>' work/{domain}/uploads/home.html
grep -o '<meta name="description" content="[^"]*"' work/{domain}/uploads/home.html
grep -o '<link rel="canonical" href="[^"]*"' work/{domain}/uploads/home.html
grep -o '<meta name="robots" content="[^"]*"' work/{domain}/uploads/home.html
sed -n 's/.*<script type="application\/ld+json">\(.*\)<\/script>.*/\1/p' work/{domain}/uploads/home.html
```

**JSON-LD ส่วนใหญ่เขียนหลายบรรทัด** คำสั่ง `sed` บรรทัดเดียวข้างบนจับได้เฉพาะแบบบรรทัดเดียว
ถ้ารันแล้วไม่ได้อะไรกลับมา **ห้ามสรุปว่าหน้านั้นไม่มี schema** ให้เปิดไฟล์ที่ดาวน์โหลดมา
ด้วย Read หรือใช้ Grep หาคำว่า `application/ld+json` ในไฟล์นั้นอีกรอบก่อนเสมอ

**ถ้าดึงหน้าเดิมสองครั้งแล้วได้ค่าไม่ตรงกัน ให้ดึงครั้งที่สาม** แล้วใช้ค่าที่ซ้ำกันสองในสาม
ถ้ายังไม่ตรงอีก ให้บันทึกว่าค่าไม่นิ่ง และห้ามสรุปว่าหน้านั้นผิดกฎ

**ถ้า `curl` ใช้ไม่ได้ในเครื่องผู้ใช้** ให้บอกตรง ๆ แล้วทำเท่าที่ WebFetch ให้ได้
พร้อมเขียนกำกับทุกหัวข้อที่กระทบว่า **ตรวจไม่ได้** ไม่ใช่ **ไม่มี** สองคำนี้คนละความหมาย

## Markup ต้องสะท้อนสิ่งที่มองเห็น ความลึกของชนิด และภาชนะของหน้า

- **markup สะท้อนเนื้อหาที่มองเห็นเท่านั้น** ข้อมูลที่มีในฐานข้อมูลแต่ไม่แสดงให้ผู้เข้าชม มีทางเลือกสองทาง คือแสดงแล้วค่อยใส่ markup
  หรือตัดออกทั้งคู่ ห้ามฝังแบบมองไม่เห็น การตัดสินใจว่าจะแสดงหรือไม่เป็นของเจ้าของเนื้อหา ให้เสนอสองทางแล้วส่งกลับ
- **ข้อยกเว้นแคบ ๆ** คือบริบทที่คนอนุมานได้จากภาพแต่เครื่องอ่านไม่ออก กรณีมาตรฐานคือค่าสูงสุดและต่ำสุดของสเกลคะแนนรีวิว
  ซึ่งต้องระบุใน markup แม้ผู้ชมเห็นแค่รูปดาว ข้อยกเว้นครอบเฉพาะข้อมูลสเกลแบบนี้
- **บล็อกอื่นที่มี markup แต่มองไม่เห็น เป็นความเสี่ยงถูกลงโทษด้วยมือ** ลงในรายงานเป็นความเสี่ยงต่อการแสดงผล ไม่ใช่ข้อติเรื่องรูปแบบ
  และรวมชื่อ property ทั้งหมดไว้ในข้อค้นพบเดียว
- **เลือกความลึกของชนิดก่อนเขียน** ใช้ชนิดที่ลึกที่สุดในสายสืบทอดที่ยังบรรยาย entity ได้ถูกต้อง เช่น Dentist แทน LocalBusiness
  หยุดตรงชั้นที่ลึกกว่านั้นจะไม่ตรงความจริง
- **เลือกภาชนะของหน้าแยกต่างหาก** ถามว่าหน้านี้เกี่ยวกับอะไรเป็นหลัก แล้วซ้อนอีกชนิดไว้ข้างใน หน้ารายละเอียดสินค้าคือ Product
  ที่มี Offer ซ้อนอยู่และมี AggregateRating หนึ่งชุด หน้าที่จุดประสงค์คือการขายเองกลับด้านได้ ทบทวนภาชนะอีกครั้งหลังไล่ข้อมูลบนหน้าครบ
  เพราะจำนวนองค์ประกอบ (หลายราคา หนึ่งคะแนน) ช่วยตัดสิน
- **field ของธุรกิจท้องถิ่น** (รูปแบบ NAP, เวลาทำการ, พิกัด, หมวด) กำหนดโดย `seo-local-seo-lite` ถ้ารันแล้วให้รับเป็น input
  ห้ามตั้งมาตรฐาน NAP ชุดที่สอง ถ้ายังไม่รัน สร้าง LocalBusiness จากโปรไฟล์ลูกค้าได้ตามปกติ
- ข้อกำหนดเฉพาะวิดีโอเป็นของ `seo-video-lite`

## วินัยการอ้างประโยชน์ (ถ้อยคำที่ส่งลูกค้า)

ทุก deliverable ระบุประโยชน์ของ markup ได้สามอย่างเท่านั้น คือ ช่วยให้ระบบเข้าใจหน้า, มีสิทธิ์แสดง rich result, และพร้อมให้ AI หยิบไปอ้าง
สิทธิ์ไม่ใช่การรับประกันว่าจะแสดง และการเข้าใจไม่ใช่อันดับ **ห้ามเขียนหรือทำให้เข้าใจว่า markup อย่างเดียวยกอันดับได้**
กฎเดียวกันนี้ผูกกับ `aiso-schema-lite`

## การ์ด Tier 1 ของสกิลนี้

จบงานทุกครั้งด้วยการ์ดสรุปตามชั้นแสดงผล (`so-present-lite`): โหมด `deployable` `deployables` คือไฟล์ JSON-LD ทุกไฟล์ที่เขียนในรอบนี้ (filename, language json, content, path ใน work/{domain}/02-fixes/ หรือ route ที่ลงทะเบียน), `checklist` คือขั้นตอนติดตั้งที่ติดป้าย [Dev] พร้อมขั้นตรวจสอบด้วย Rich Results Test, `next_steps` คือคำสั่งตรวจซ้ำหลังติดตั้ง
ทุกค่าบนการ์ดคัดลอกจากไฟล์ผลลัพธ์ที่เพิ่งเขียน ห้ามประเมินเพิ่ม ข้อที่ตรวจไม่ได้ให้ขึ้นว่า ตรวจสอบไม่ได้
รุ่น Lite ไม่มีคะแนน จึงไม่ใส่บล็อก `score` ค่าใน `dimensions` คือจำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจ
เรนเดอร์ด้วย `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --summary <summary.json> --target auto --host {host}`
แล้วปิดด้วยบรรทัดส่งต่อไปยังไฟล์ผลลัพธ์ฉบับเต็ม ซึ่งต้องครบและไม่ถูกย่อ

## Output
### Naming convention

ไฟล์ที่สร้างต้องตั้งชื่อตาม pattern:

```
{domain}_schema-markup_{YYYY-MM-DD}.{ext}
```

ตัวอย่าง: `example-com_schema-markup_2026-03-28.md`

## การวางไฟล์ผลลัพธ์

สกิลนี้อยู่ในชุดที่ใช้โครงโฟลเดอร์ของสกิล `new-workspace-lite`

1. ผลลัพธ์ทุกไฟล์อยู่ใต้ `work/{domain}/`
2. ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์หัวข้อเดียวกัน ให้เขียนลง `00-baseline/` ถ้ามีแล้ว ให้เขียนลง `01-current/`
3. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร
4. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน ห้ามสร้างโครงเองแบบอื่น

## กฎ

- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`**
  สองคำนี้คนละความหมาย การเขียนผิดทำให้ผู้ใช้สรุปกลับด้าน
  แล้วไปสร้าง schema ซ้ำกับที่หน้านั้นมีอยู่แล้ว
- **ข้อมูลธุรกิจไม่ครบ ไม่ใช่เหตุให้ปฏิเสธทั้งงาน** ให้สร้างเท่าที่ข้อมูลรองรับ
  แล้วติดป้ายทุกค่าว่า ยืนยันแล้ว หรือ ต้องให้ผู้ใช้ยืนยัน
  พร้อมเขียนรายการสั้น ๆ ว่าต้องเติมอะไรถึงจะครบ
  **การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์**
- **ห้ามเดาค่าใน schema** ชื่อ ที่อยู่ เบอร์โทร วันเวลาทำการ และชื่อผู้เขียน
  ต้องมาจากซอร์สที่ดึงมาหรือจากที่ผู้ใช้บอกเท่านั้น ไม่มีให้เว้นไว้แล้วบอกว่าต้องเติม
- **ห้ามให้คะแนนรวมและห้ามคิดเปอร์เซ็นต์** ใช้คำบอกระดับเชิงคุณภาพแทน

## Reference files

- Agent definition: [agent.json](agent.json)
