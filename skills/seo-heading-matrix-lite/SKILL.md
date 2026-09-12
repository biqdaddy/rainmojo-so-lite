---
name: seo-heading-matrix-lite
description: >
  ตรวจโครงหัวข้อ H1 ถึง H6 ของหน้าเว็บว่าเรียงถูกไหม มี H1 เดียวไหม และข้ามระดับหรือเปล่า
  ใช้เมื่อผู้ใช้ถามว่าโครงหน้าเว็บถูกต้องไหม ทำไม AI อ่านหน้าเราไม่เข้าใจ
  หรือใช้ต่อจาก aiso-citability-lite เมื่อพบว่าย่อหน้าเขียนดีแล้วแต่ยังไม่ถูกหยิบไปอ้างอิง
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


# Heading Matrix

ตรวจว่าโครงหัวข้อของหน้าเล่าเรื่องได้ด้วยตัวมันเองไหม

**ทำไมเรื่องนี้สำคัญกับ AI มากกว่ากับ Google**

Google อ่านทั้งหน้าแล้วจัดอันดับทั้งหน้า แต่ AI หยิบเป็นชิ้นไปตอบคำถาม
มันใช้หัวข้อเป็นตัวบอกว่าชิ้นไหนตอบเรื่องอะไร **หัวข้อที่เรียงมั่วทำให้มันหยิบผิดชิ้น**
หรือไม่หยิบเลยเพราะไม่แน่ใจว่าย่อหน้านั้นอยู่ใต้เรื่องอะไร

---

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
grep -o '<h[1-6][^>]*>[^<]*</h[1-6]>' work/{domain}/uploads/home.html
```

**บรรทัดสุดท้ายคือคำสั่งหลักของสกิลนี้** ให้ไล่ลำดับหัวข้อจากผลของคำสั่งนี้
ไม่ใช่จากผล WebFetch เพราะ WebFetch แปลงเป็นข้อความแล้วระดับหัวข้อเพี้ยนได้

**ถ้าดึงหน้าเดิมสองครั้งแล้วได้ค่าไม่ตรงกัน ให้ดึงครั้งที่สาม** แล้วใช้ค่าที่ซ้ำกันสองในสาม
ถ้ายังไม่ตรงอีก ให้บันทึกว่าค่าไม่นิ่ง และห้ามสรุปว่าหน้านั้นผิดกฎ

**ถ้า `curl` ใช้ไม่ได้ในเครื่องผู้ใช้** ให้บอกตรง ๆ แล้วทำเท่าที่ WebFetch ให้ได้
พร้อมเขียนกำกับทุกหัวข้อที่กระทบว่า **ตรวจไม่ได้** ไม่ใช่ **ไม่มี** สองคำนี้คนละความหมาย

## ดูภาพรวมทั้งเว็บก่อน อย่าดูแค่หน้าที่หยิบมา

ถ้าตรวจแค่ 3 ถึง 4 หน้า จะมองไม่เห็นปัญหาที่เกิดซ้ำทั้งเว็บ ซึ่งมักใหญ่กว่าปัญหารายหน้ามาก

```bash
curl -sSL -m 25 "https://{domain}/sitemap.xml" -o work/{domain}/uploads/sitemap.xml
grep -o '<loc>[^<]*</loc>' work/{domain}/uploads/sitemap.xml | sed 's/<[^>]*>//g' | head -60
```

ถ้าไฟล์เป็นดัชนีที่ชี้ไป sitemap ย่อย ให้ตามไปดึงอันที่เกี่ยวข้อง
แล้ว**สุ่มมาอย่างน้อย 10 หน้าที่เป็นหน้าประเภทเดียวกัน** เพื่อดูว่าใช้แม่แบบซ้ำกันหรือเปล่า

ถ้าพบว่าซ้ำกันตั้งแต่ 3 หน้าขึ้นไป ให้รายงานเป็น**ปัญหาระดับเว็บ** แยกจากปัญหารายหน้า
และประเมินคร่าว ๆ ว่ากระทบกี่หน้าจากทั้งหมดกี่หน้า

## ตรวจ 6 ข้อ

| ข้อ | เกณฑ์ | ทำไมถึงสำคัญ |
|---|---|---|
| **H1 มีกี่อัน** | ต้องมี 1 อันพอดี | 0 อันแปลว่าไม่มีหัวเรื่อง มากกว่า 1 แปลว่าไม่รู้ว่าหน้านี้เรื่องอะไร |
| **ข้ามระดับไหม** | H2 ตามหลัง H1 ห้ามกระโดดจาก H2 ไป H4 | การข้ามระดับทำให้ลำดับความสำคัญเพี้ยน |
| **หัวข้อว่างเปล่าไหม** | ห้ามมีแท็กหัวข้อที่ไม่มีข้อความ | มักเกิดจาก page builder ที่ใส่แท็กเปล่าไว้ |
| **ใช้หัวข้อจัดหน้าไหม** | ห้ามใช้ H2 เพราะอยากได้ตัวใหญ่ | ถ้าอยากได้ตัวใหญ่ให้ใช้ CSS ไม่ใช่แท็กหัวข้อ |
| **หัวข้ออ่านเดี่ยวรู้เรื่องไหม** | หัวข้อว่า รายละเอียด หรือ ข้อมูลเพิ่มเติม ใช้ไม่ได้ | ไม่บอกอะไรเลยว่าข้างล่างพูดเรื่องอะไร |
| **มีคำถามจริงในหัวข้อไหม** | หัวข้อที่เป็นคำถามที่คนถามจริงจะถูกหยิบง่ายกว่า | ตรงกับวิธีที่คนพิมพ์ถาม AI |

**ข้อที่ 5 กับ 6 สำคัญกว่าอีก 4 ข้อ** เพราะสี่ข้อแรกเป็นเรื่องโครงสร้างที่เครื่องมือทั่วไปก็ตรวจได้
แต่สองข้อหลังคือสิ่งที่ทำให้ถูกหยิบไปตอบจริง

---

## ขั้นตอน

1. ถามผู้ใช้ว่าจะตรวจหน้าไหน ถ้าให้มาหลายหน้าให้ **จัดกลุ่มตามประเภทหน้า**
   เช่น หน้าแรก หน้าบริการ หน้าบทความ หน้าติดต่อ เพราะแต่ละประเภทมีโครงที่ควรเป็นต่างกัน
2. ดึงหน้ามาอ่าน แล้วไล่หัวข้อ **ตามลำดับที่ปรากฏในโค้ดจริง ไม่ใช่ตามที่ตาเห็นบนจอ**
   เพราะ CSS ย้ายตำแหน่งได้ แต่ AI อ่านตามลำดับในโค้ด
3. เทียบกับเกณฑ์ 6 ข้อ
4. เสนอโครงที่ควรเป็น พร้อมเหตุผล

---

## ส่งออก

ไฟล์ `{domain}_heading-matrix_{YYYY-MM-DD}.md` วางตามกฎนี้

ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์ `heading-matrix` ให้เขียนลง `00-baseline/`
ถ้ามีแล้ว ให้เขียนลง `work/{domain}/01-current/` เพื่อให้สกิล `compare-lite` เทียบสองรอบได้
เขียนเสร็จ เพิ่มบรรทัดลง `work/{domain}/CHANGELOG.md` เรียงตามนี้

1. **สรุป** ตารางคอลัมน์ ประเภทหน้า / จำนวนหน้าที่ตรวจ / ผ่าน / มีปัญหา
2. **รายหน้า** แต่ละหน้าให้แสดง URL ประเภทหน้า โครงที่เป็นอยู่ในบล็อกโค้ด
   ปัญหาที่พบเป็นตาราง โครงที่ควรเป็นในบล็อกโค้ด และเหตุผลที่ควรเปลี่ยน
3. **สิ่งที่ควรแก้ก่อน** เรียงตามหน้าที่มีคนเข้าเยอะที่สุด ไม่ใช่ตามที่แก้ง่ายที่สุด

ตอนแสดงโครงที่เป็นอยู่ ให้ทำเครื่องหมายตรงบรรทัดที่มีปัญหา เช่นเขียนกำกับว่าข้ามระดับ
เพื่อให้ผู้ใช้เห็นทันทีว่าปัญหาอยู่ตรงไหน ไม่ต้องไล่หาเอง

---

## ตรวจการแสดงผลจริงของหัวข้อ (รันคู่กับการตรวจโครง ต่อ page template type)

tag ถูกอย่างเดียวไม่พอ ขนาดที่เรนเดอร์จริงต้องเล่าลำดับชั้นเดียวกับ tag ตรวจชั้นนี้ทุกครั้งที่ตรวจโครงหัวข้อ

1. ดึง computed font-size และ font-weight ของทุกระดับหัวข้อที่ใช้จริงในแต่ละ page template type จากหน้าที่เรนเดอร์แล้ว
   ถ้าเรนเดอร์ไม่ได้ ให้ inspect CSS ของธีม (stylesheet หรือการตั้งค่า page builder) แล้วบันทึกว่าอ่านจากที่ไหน
2. เกณฑ์: font-size ต้องลดลงตามความลึก (H1 เด่นสุด) และ font-weight ต้องไม่เพิ่มเมื่อลึกลง
   หัวข้อระดับลึกที่เรนเดอร์ใหญ่กว่าระดับตื้น เช่น H3 ใหญ่กว่า H2 เป็น defect เสมอ ระดับติดกันขนาดเท่ากันให้ลงเป็น ควรปรับ
3. ทุก defect ต้องแนบคำแนะนำแก้ CSS ที่ชี้ selector ที่ผิดและทิศทางที่ควรเป็น (เล็กลง บางลง)
4. **แก้ที่ CSS เท่านั้น ห้ามแก้ด้วยการเปลี่ยนระดับ tag** เพราะระดับ tag คือโครงสร้าง ไม่ใช่เครื่องมือจัดขนาด
   การสลับ tag เพื่อขนาดจะสร้าง defect โครงสร้างใหม่แทน
5. จุดที่พลาดบ่อย: ธีมสาย page builder มักตั้ง style ให้ H3 หรือ H4 เด่นกว่า H2 ให้ตรวจ template ที่ประกอบจาก builder ก่อน

เกณฑ์ผ่าน: matrix ต่อ page type มีค่า font-size และ font-weight ของทุกระดับ (หรือ ตรวจไม่ได้ พร้อมเหตุ)
verdict ต่อระดับว่าเรียงถูกหรือ defect และทุก defect มีคำแนะนำแก้ CSS แนบ

**ขอบเขต** ถ้ามีไฟล์กายวิภาคหน้าเดียวจากสกิลอื่นอยู่แล้ว การย้ายหัวข้อรองต้องอยู่ในตำแหน่งที่ไฟล์นั้นอนุญาต
ส่วนการตรวจว่ามี H1 เดียวและไม่ข้ามระดับยังครอบคลุมทั้งหน้าทุก page type ตามเดิม

## กฎ

- **ห้ามแก้เว็บให้** สกิลนี้เสนอโครงที่ควรเป็น ผู้ใช้ไปแก้เอง
- ห้ามให้คะแนนรวมเป็นตัวเลข ให้บอกว่าผ่านหรือมีปัญหาอะไรบ้าง
- ถ้าหน้าโหลดด้วย JavaScript แล้วอ่านหัวข้อไม่ได้ **ให้บอกตรง ๆ ว่าอ่านไม่ได้**
  แล้วแนะนำให้ดูจาก view-source แทน **ห้ามเดาโครง**
- ถ้าหน้าเดียวมี H1 หลายอันเพราะใช้ template ซ้ำ ให้ระบุว่าเป็นปัญหาระดับ template
  ไม่ใช่ระดับหน้า เพราะแก้ที่เดียวจบทุกหน้า
- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`**
  สองคำนี้คนละความหมาย เขียนผิดแล้วผู้ใช้จะสรุปกลับด้าน เช่นคิดว่าหน้านั้นไม่มี H1
  ทั้งที่ความจริงคือเราอ่านหน้านั้นไม่ได้
- **อ่านได้กี่หน้าให้ส่งเท่านั้น ห้ามกลั้นทั้งงานเพราะบางหน้าอ่านไม่ได้**
  ในรายงานให้ติดป้ายรายหน้าว่า ยืนยันจากซอร์สแล้ว หรือ ต้องยืนยันเพิ่ม
  **การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์**
