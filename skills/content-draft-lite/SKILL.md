---
name: content-draft-lite
description: >
  เขียนแพ็กเกจบทความหนึ่งชิ้นเก็บไว้ในเครื่อง พร้อม meta title description schema และบรีฟภาพ
  ใช้เมื่อผู้ใช้ต้องการเขียนหน้าใหม่ แก้หน้าเดิมให้ AI หยิบไปอ้างอิงได้ หรือเตรียมบทความก่อนส่งขึ้นเว็บ
  ผลลัพธ์เป็นไฟล์ในเครื่อง ยังไม่ส่งขึ้นเว็บ ส่งด้วยสกิล wp-publish-draft-lite ต่างหาก
allowed-tools:
  - Read
  - Grep
  - Glob
  - WebFetch
  - Write
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


# Content Draft

เขียนบทความให้ครบชุดในเครื่องก่อน แล้วค่อยตัดสินใจว่าจะส่งขึ้นเว็บไหม

**สกิลนี้ไม่แตะเว็บจริง** ผลลัพธ์ทั้งหมดเป็นไฟล์ใน `work/{domain}/03-content/`

---

## ข้อมูลที่ต้องมีก่อนเริ่ม

| ต้องมี | เอามาจากไหน |
|---|---|
| หัวข้อหรือคำถามที่จะตอบ | ผู้ใช้บอก |
| **คำค้นจริงที่ AI ยิง** | ไฟล์ CSV ใน `uploads/` ที่ export จาก Chrome Extension: Rainmojo Query Fan-Out |
| ข้อมูลเว็บ | `work/{domain}/site.md` |
| หน้าที่มีอยู่แล้ว | เพื่อไม่ให้เขียนซ้ำกับของเดิม |

**ถ้ามีไฟล์ CSV ให้ใช้เสมอ** เพราะคำค้นในนั้นคือสิ่งที่ AI ยิงจริง ไม่ใช่คำที่เราเดา
ถ้าไม่มี ให้บอกผู้ใช้ว่าบทความจะแม่นน้อยลง แล้วถามว่าจะไปเก็บมาก่อนไหม

**ขาดข้อมูลบางอย่างไม่ใช่เหตุผลที่จะไม่ส่งงาน** ถ้าไม่มี CSV หรือไม่มี `site.md`
ให้เขียนบทความต่อจากข้อมูลเท่าที่มี แล้วติดป้ายกำกับให้ชัดว่าส่วนไหนยืนยันแล้ว
และส่วนไหนต้องให้ผู้ใช้ยืนยันเพิ่ม แล้วบอกไว้ท้ายงานว่าถ้าได้ CSV มาจะกลับมาปรับให้แม่นขึ้นได้
**การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์**

---

## ขั้นที่ 1 กำหนดคำถามที่บทความนี้ต้องตอบ

เขียนออกมาเป็น **คำถามเดียว** ที่บทความนี้ตอบให้จบ

ถ้าตอบได้หลายคำถาม แปลว่าควรแยกเป็นหลายหน้า **อย่ายัดทุกอย่างลงหน้าเดียว**
เพราะ AI หยิบเป็นย่อหน้า ไม่ได้หยิบทั้งหน้า หน้าที่ตอบหลายเรื่องจะไม่ชนะเรื่องไหนเลย

---

## ขั้นที่ 2 วางโครงให้ AI หยิบง่าย

```
H1  คำถามหรือหัวข้อหลัก
    ย่อหน้าแรก  ตอบคำถามให้จบใน 2 ถึง 4 ประโยค  <-- ย่อหน้านี้สำคัญที่สุด
H2  รายละเอียดประเด็นที่ 1
    ย่อหน้าที่อ่านจบได้ในตัวเอง
H2  รายละเอียดประเด็นที่ 2
H2  คำถามที่พบบ่อย
    คำถาม แล้วตามด้วยคำตอบที่จบในย่อหน้าเดียว
```

**กฎเดียวที่สำคัญที่สุด** คือ **ทุกย่อหน้าต้องอ่านจบได้ในตัวเอง**
ถ้าย่อหน้าไหนต้องอ่านย่อหน้าก่อนหน้าถึงจะเข้าใจ AI จะไม่หยิบไปใช้
เพราะมันหยิบทีละชิ้นไปวางในคำตอบ ไม่ได้ยกไปทั้งหน้า

### ตรวจตัวเองด้วยคำถามนี้

หยิบย่อหน้าไหนก็ได้มาอ่านเดี่ยว ๆ **ถ้าคนอ่านแล้วเข้าใจ แปลว่าใช้ได้**
ถ้าต้องถามว่า "อันนี้พูดถึงอะไร" แปลว่าต้องเขียนใหม่

---

## ขั้นที่ 3 เขียนเนื้อหา

| เรื่อง | ทำ | ไม่ทำ |
|---|---|---|
| ตัวเลขและราคา | เขียนตัวเลขจริงลงไป | เขียนว่าติดต่อเพื่อขอใบเสนอราคา |
| แหล่งอ้างอิง | ระบุที่มาและวันที่ | อ้างลอย ๆ ว่ามีงานวิจัยบอกว่า |
| ชื่อแบรนด์ | สะกดเหมือนกันทุกที่ | สลับไทยอังกฤษไปมา |
| คำเฉพาะไทย | ใช้ตรง ๆ เช่น LINE OA, PDPA, พร้อมเพย์ | แปลเป็นอังกฤษ เพราะไม่มีคำแทน |
| ความยาวย่อหน้า | ให้จบความคิดเดียว | ยาวจนมีสามความคิดในย่อหน้าเดียว |

**ห้ามแต่งข้อมูลที่ตรวจสอบไม่ได้** ถ้าไม่รู้ตัวเลขจริงให้เว้นไว้แล้วบอกผู้ใช้ว่าต้องเติมเอง

---

## ขั้นที่ 4 สร้างไฟล์ให้ครบชุด

วางที่ `work/{domain}/03-content/{slug}/`

```
{slug}/
  article.md        เนื้อหาบทความ
  meta.json         title description slug หมวดหมู่ แท็ก
  schema.json       JSON-LD ที่จะฝังในหน้า
  images.md         บรีฟภาพที่ต้องใช้ พร้อม alt text
  checklist.md      สิ่งที่ต้องตรวจก่อนส่งขึ้นเว็บ
```

### meta.json

```json
{
  "title": "50 ถึง 60 ตัวอักษร นับแบบเดียวกับสกิล meta-basics-lite มีคำที่คนถามจริงอยู่ในนั้น",
  "description": "140 ถึง 160 ตัวอักษร นับแบบเดียวกับสกิล meta-basics-lite ตอบคำถามได้จบในตัวเอง",
  "slug": "คำอังกฤษคั่นด้วยขีด",
  "categories": ["เว้นว่างได้ถ้ายังไม่รู้ แล้วเติมตอนขั้น wp-publish-draft-lite จากรายการหมวดหมู่ที่ wp-connect-lite ดึงมา"],
  "tags": [],
  "status": "draft"
}
```

`status` **ต้องเป็น `draft` เสมอ** สกิลในชุดนี้ไม่เผยแพร่หน้าให้อัตโนมัติ

### images.md

ระบุภาพที่ต้องใช้ พร้อม **alt text ที่เขียนไว้แล้ว** ไม่ใช่ให้ไปคิดตอนอัป

```markdown
## ภาพหลัก
- ควรเป็นภาพอะไร:
- alt text:
- ชื่อไฟล์ที่ควรใช้:

## ภาพประกอบในเนื้อหา
```

**สกิลนี้ไม่สร้างภาพให้** สร้างแต่บรีฟ ผู้ใช้ไปหาหรือถ่ายเอง

### checklist.md

```markdown
- [ ] ย่อหน้าแรกตอบคำถามจบในตัวเอง
- [ ] ทุกย่อหน้าอ่านเดี่ยวแล้วเข้าใจ
- [ ] ตัวเลขและราคาเป็นของจริง ไม่ใช่ค่าสมมติ
- [ ] title ไม่เกิน 60 ตัวอักษร
- [ ] description 140 ถึง 160 ตัวอักษร นับตามกติกาของสกิล meta-basics-lite
- [ ] slug ไม่ซ้ำกับหน้าที่มีอยู่
- [ ] หมวดหมู่ตรงกับที่มีในเว็บจริง
- [ ] มี alt text ครบทุกภาพ
- [ ] ไม่มีข้อความที่แต่งขึ้นโดยตรวจสอบไม่ได้
- [ ] อ่านทวนแล้วไม่เหมือนข้อความที่ AI เขียน
```

---

## ขั้นที่ 5 บอกผู้ใช้ว่าทำอะไรต่อ

1. เปิด `article.md` อ่านทวนด้วยตาตัวเอง **ข้อนี้ข้ามไม่ได้**
2. เติมตัวเลขหรือข้อมูลที่เว้นไว้
3. หาภาพตามบรีฟใน `images.md`
4. ติ๊ก checklist ให้ครบ
5. ถ้าจะส่งขึ้นเว็บ ให้รัน `wp-connect-lite` ก่อน แล้วค่อย `wp-publish-draft-lite`

---

## กฎ

- เขียนไฟล์เสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน

- **ไม่แตะเว็บจริง** สกิลนี้เขียนไฟล์ในเครื่องเท่านั้น
- **ไม่ตั้ง status เป็น publish** ไม่ว่าผู้ใช้จะขอยังไง ให้เขาไปกดเผยแพร่เองในหลังบ้าน
- **ไม่เขียนบทความทับไฟล์เดิม** ถ้า slug ซ้ำให้ถามก่อน
- **ไม่แต่งตัวเลข** ถ้าไม่มีข้อมูลให้เว้นแล้วบอกผู้ใช้
- **ถ้าดึงข้อมูลหน้าเดิมไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`**
  เช่นตอนดูว่า slug ซ้ำกับหน้าที่มีอยู่ไหม ถ้าเปิดดูไม่ได้ ห้ามสรุปว่าไม่ซ้ำ
  ให้เขียนว่ายังตรวจไม่ได้แล้วให้ผู้ใช้ยืนยันเอง เพราะสองคำนี้คนละความหมาย
  และการเขียนผิดจะทำให้ผู้ใช้เข้าใจกลับด้าน
