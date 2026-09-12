---
name: meta-basics-lite
description: >
  พื้นฐาน title tag และ meta description วิธีนับตัวอักษรไทย อังกฤษ และ emoji
  กฎความยาว หลักการตั้ง title และ checklist ตรวจก่อนใช้จริง
  (Lite edition for workshop use.)
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


# meta-basics-lite

Read and execute the agent workflow from [agent.json](agent.json).

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

## 1. การนับตัวอักษร

นับเป็น character ไม่ใช่ byte และไม่ใช่จำนวนคำ

- **อังกฤษ** นับทีละตัว รวมช่องว่างและเครื่องหมายวรรคตอน
- **ไทย** นับเป็น character ถ้าเผลอนับเป็น byte ตัวเลขจะผิดไปราว 3 เท่า
- **emoji** 1 ตัว นับเป็น 2 ตัวอักษร

**จุดพลาดของภาษาไทย** สระบน สระล่าง และวรรณยุกต์ นับเป็นตัวอักษร 1 ตัวเสมอ
แม้จะลอยเหนือหรือใต้พยัญชนะและดูเหมือนไม่กินที่ ข้อความไทยที่ตาเห็นว่าสั้น
จึงมักยาวเกินจริง เช่น `เชียงใหม่` ตาเห็นราว 6 ช่อง แต่นับได้ 9 ตัวอักษร
คือ เ ช ี ย ง ใ ห ม ่ ให้ไล่นับทีละตัว ห้ามกะจากความกว้างที่เห็น

## 2. กฎความยาว

| ส่วน | ความยาว |
|---|---|
| title tag | 50 ถึง 60 ตัวอักษร |
| meta description | 140 ถึง 160 ตัวอักษร |

สั้นกว่านี้เสียพื้นที่ฟรี ยาวกว่านี้ส่วนเกินเสี่ยงถูกตัด

## 3. หลักการตั้ง title

1. วางคำค้นหลักไว้ช่วงต้น
2. ระบุให้ชัดว่าหน้านี้คืออะไร
3. ไม่ซ้ำกับหน้าอื่นในเว็บเดียวกัน
4. ตรงกับเนื้อหาจริงบนหน้านั้น
5. อ่านเดี่ยว ๆ แล้วเข้าใจได้
6. **ใส่ชื่อแบรนด์ใน title เฉพาะหน้าแรก** หน้าอื่นไม่ต้องใส่ เพราะ Google แสดงชื่อเว็บให้อยู่แล้ว และการใส่ทุกหน้ากินที่ของคำที่คนค้นจริง · ส่วน meta description ให้มีชื่อแบรนด์ทุกหน้า · **ห้ามใช้ขีดตั้งคั่นแบรนด์** ให้ใช้ช่องว่างหรือจุดกลางแทน

## 4. Checklist

- [ ] title 50 ถึง 60 ตัวอักษร
- [ ] meta description 140 ถึง 160 ตัวอักษร
- [ ] นับแบบ character นับสระและวรรณยุกต์ครบ
- [ ] emoji นับเป็น 2 ตัวอักษรแล้ว
- [ ] คำค้นหลักอยู่ช่วงต้นของ title
- [ ] ไม่ซ้ำกับหน้าอื่นในเว็บเดียวกัน
- [ ] ตรงกับเนื้อหาจริงบนหน้า
- [ ] มีชื่อแบรนด์ใน title เฉพาะหน้าแรก และมีใน description ทุกหน้า ไม่มีขีดตั้ง

## 5. กฎการตัดสินใจเมื่อดูผลบน SERP

**ตั้งใจเว้น description ว่างได้ ในงานชุดใหญ่**
เว็บที่มีสินค้าหรือบทความหลายร้อยหน้า แต่ละหน้าตอบคำค้นหางยาวต่างกัน การเว้น meta description ว่างเป็นผลลัพธ์ที่ยอมรับได้
เพราะระบบจะตัดข้อความที่ตรงคำค้นจากหน้ามาแสดงให้เอง ต่อแถว ถ้าเขียน description ที่ไม่ซ้ำใครไม่ได้ ให้เว้นว่างแทนการเติมจากแม่แบบ
แล้วบันทึกแถวนั้นว่า เว้นว่างโดยตั้งใจ พร้อมเหตุผล นี่คือการตัดสินใจ ไม่ใช่ข้อผิดพลาด
ถ้าเขียน **title** ที่ไม่ซ้ำไม่ได้ ปัญหาไม่ใช่เรื่อง meta อีกแล้ว แต่เป็นคำถามว่าหน้านั้นควรมีอยู่ในดัชนีไหม ห้ามฝืนออก title ซ้ำ
ให้ส่งไปพิจารณาเรื่อง noindex ใน `technical-audit-lite`

**Google เขียน title ใหม่ ไม่ใช่คำสั่งให้แก้ทันที**

1. วินิจฉัยสาเหตุก่อน: title ไม่ตรงเนื้อหาจริง, ไม่ตรงกับคำค้นที่หน้านั้นถูกแสดงจริง, หรือใช้ถ้อยคำโฆษณาตัวเองเกินไป
2. แก้เฉพาะเมื่อการเขียนใหม่เกิดกับคำค้นเป้าหมายหลักของหน้า แก้ตามสาเหตุที่วินิจฉัยโดยคงเจตนาหลักและกฎความยาวข้างบน
3. ปล่อยไว้เมื่อการเขียนใหม่เกิดกับคำค้นรองเท่านั้น เพราะข้อความที่ระบบเลือกต่อคำค้นเหมาะกว่า และ title ที่เราเขียนยังรับใช้เจตนาหลัก
   บันทึกว่า ติดตามอยู่ ไม่แก้ พร้อมคำค้นที่เกิดการเขียนใหม่

## Output

```
{domain}_meta-basics_{YYYY-MM-DD}.md
```

## การวางไฟล์ผลลัพธ์

สกิลนี้อยู่ในชุดที่ใช้โครงโฟลเดอร์ของสกิล `new-workspace-lite`

1. ผลลัพธ์ทุกไฟล์อยู่ใต้ `work/{domain}/`
2. ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์หัวข้อเดียวกัน ให้เขียนลง `00-baseline/` ถ้ามีแล้ว ให้เขียนลง `01-current/`
3. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร
4. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน ห้ามสร้างโครงเองแบบอื่น

## กฎ

- ข้อความที่ยกมาจากหน้าเว็บในรายงาน ต้องคัดลอกตรงตัวอักษร ห้ามพิมพ์ใหม่จากความจำ เพราะ quote ที่คลาดแม้คำเดียวทำให้ผู้ใช้ค้นหาไม่เจอ

- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`** สองคำนี้คนละความหมาย ถ้าเขียนผิดผู้ใช้จะสรุปกลับด้าน
- **ทำได้บางส่วนต้องส่งส่วนนั้นเสมอ** ห้ามส่งตารางที่ทุกช่องว่าง และห้ามปฏิเสธทั้งงานเพราะขาดข้อมูลบางอย่าง ให้ติดป้ายว่าข้อไหนยืนยันแล้ว ข้อไหนต้องยืนยันเพิ่ม · การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์
