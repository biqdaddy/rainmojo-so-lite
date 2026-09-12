---
name: new-workspace-lite
description: >
  สร้างโครงโฟลเดอร์ตั้งต้นสำหรับเว็บหนึ่งเว็บ ให้ผลลัพธ์จากทุกสกิลมีที่อยู่ที่แน่นอน
  ใช้เมื่อผู้ใช้เริ่มงานเว็บใหม่ หรือถามว่าควรเก็บไฟล์ไว้ที่ไหน
  ควรรันเป็นสกิลแรกเสมอก่อนใช้สกิลอื่น
allowed-tools:
  - Read
  - Write
  - Glob
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


# New Workspace

สร้างบ้านให้ผลลัพธ์ ก่อนจะเริ่มสแกนอะไร

**รันตัวนี้ก่อนเสมอ** ถ้าไม่มีโครงโฟลเดอร์ ไฟล์จากสกิลอื่นจะกระจัดกระจายจนหาไม่เจอ
และตอนวัดซ้ำรอบสองจะเทียบกับรอบแรกไม่ได้

---

## ถามก่อน 1 ข้อ

ถามผู้ใช้ว่า **โดเมนอะไร** ถ้ายังไม่บอกอย่าเดา

ใช้โดเมนแบบไม่มี `https://` และไม่มี `www.` เป็นชื่อโฟลเดอร์
เช่น `example.com` กลายเป็น `example-com`

---

## โครงที่สร้าง

```
work/{domain}/
  00-baseline/          ผลสแกนรอบแรก ห้ามแก้หลังจากสแกนรอบสองแล้ว
  01-current/           ผลสแกนรอบล่าสุด
  02-fixes/             สิ่งที่ต้องแก้ และที่แก้ไปแล้ว
  03-content/           แพ็กเกจบทความที่เขียนไว้ รอส่งขึ้นเว็บ
  04-reports/           รายงานที่ประกอบเสร็จแล้ว
  uploads/              ไฟล์ที่ผู้ใช้เอามาเอง เช่น CSV จาก extension หรือ export จาก GSC
                        และซอร์ส HTML ดิบที่สกิลอื่นดึงมาเก็บไว้ก่อนตรวจ
  site.md               ข้อมูลเว็บนี้ อ่านทุกครั้งก่อนทำงาน
  CHANGELOG.md          บันทึกว่าทำอะไรไปเมื่อไร
```

**กฎการวางไฟล์ที่ทุกสกิลต้องทำตาม**

| ผลลัพธ์แบบไหน | วางที่ไหน |
|---|---|
| สแกนครั้งแรกของเว็บนี้ | `00-baseline/` |
| สแกนครั้งต่อ ๆ ไป | `01-current/` |
| รายการสิ่งที่ต้องแก้ | `02-fixes/` |
| บทความหรือ meta ที่เขียนใหม่ | `03-content/` |
| รายงานที่รวมทุกอย่างแล้ว | `04-reports/` |
| ไฟล์ที่ผู้ใช้เอามาเอง | `uploads/` **ห้ามเขียนทับไฟล์ของผู้ใช้** |
| ซอร์ส HTML ดิบที่สกิลดึงมาเองเพื่ออ่าน head และ JSON-LD | `uploads/` เขียนได้และเขียนซ้ำได้ ตั้งชื่อไม่ให้ชนกับไฟล์ของผู้ใช้ |

**ห้ามสร้างโฟลเดอร์ระดับบนเพิ่มเอง** ยกเว้น `history/` ตอนเริ่มรอบวัดใหม่ ถ้าไม่รู้จะวางตรงไหนให้ถามผู้ใช้

---

## ไฟล์ site.md ที่ต้องสร้าง

เติมเท่าที่รู้ ช่องที่ยังไม่รู้ให้เขียนว่า `ยังไม่ทราบ` **ห้ามเดา**

```markdown
# {domain}

| | |
|---|---|
| โดเมน | |
| ชื่อแบรนด์ | |
| ธุรกิจทำอะไร | |
| กลุ่มลูกค้า | |
| ภาษาหลักของเว็บ | |
| CMS | WordPress / อื่น ๆ / ยังไม่ทราบ |
| มี Google Search Console ไหม | |
| มี GA4 ไหม | |

## คำถามที่ลูกค้าจริงถาม 10 ข้อ
ใส่คำถามที่ลูกค้าถามจริง ไม่ใช่คำค้นที่เราอยากติด

1.
2.

## คู่แข่ง 3 ราย
1.
2.
3.

## สิ่งที่ยังไม่รู้
เขียนออกมาตรง ๆ ว่ายังไม่รู้อะไร ช่องนี้สำคัญพอกับช่องอื่น
```

---

## ไฟล์ CHANGELOG.md ที่ต้องสร้าง

```markdown
# บันทึกการทำงาน {domain}

| วันที่ | ทำอะไร | ไฟล์ที่ได้ |
|---|---|---|
```

**ทุกสกิลต้องเพิ่มบรรทัดลงตารางนี้หลังทำงานเสร็จ** ไม่ใช่แค่สร้างไฟล์ทิ้งไว้
เพราะตอนวัดซ้ำรอบสอง คุณต้องรู้ว่าระหว่างสองรอบทำอะไรไปบ้าง ไม่งั้นอ่าน delta ไม่ออก

---

## หลังสร้างเสร็จ

บอกผู้ใช้ว่า

1. โฟลเดอร์อยู่ที่ไหน
2. ให้เปิด `site.md` เติมข้อมูลก่อน โดยเฉพาะคำถาม 10 ข้อ
3. ถ้ามีไฟล์ CSV จาก Chrome Extension: Rainmojo Query Fan-Out ให้วางไว้ใน `uploads/`
4. สกิลถัดไปที่ควรรันคือ `aiso-crawlers-lite` เพราะถ้า crawler เข้าไม่ได้ อย่างอื่นไม่มีความหมาย

---

## ถ้าโฟลเดอร์มีอยู่แล้ว

**อย่าเขียนทับ** ให้บอกผู้ใช้ว่ามีอยู่แล้ว แล้วถามว่าจะทำอะไร

| ผู้ใช้ต้องการ | ทำอะไร |
|---|---|
| ทำงานต่อจากเดิม | อ่าน `site.md` และ `CHANGELOG.md` แล้วบอกว่าครั้งก่อนทำถึงไหน |
| เริ่มรอบวัดใหม่ | ย้ายของใน `01-current/` ไปเก็บใน `history/01-current-{YYYY-MM-DD}/` (ใช้วันที่วันนี้ ถามผู้ใช้ถ้าไม่แน่ใจ) แล้วสร้าง `01-current/` ว่างใหม่ นี่คือข้อยกเว้นเดียวที่อนุญาตให้มีโฟลเดอร์นอกโครง 6 อัน |
| เริ่มใหม่หมด | **ต้องให้ผู้ใช้ยืนยันก่อน** แล้วบอกให้เขาลบเองด้วยมือ สกิลนี้ไม่ลบไฟล์ให้ |

**สกิลนี้ไม่ลบไฟล์ใด ๆ ทั้งสิ้น**

## กฎ

- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`** สองคำนี้คนละความหมาย ถ้าเขียนผิดผู้ใช้จะสรุปกลับด้าน
- **ทำได้บางส่วนต้องส่งส่วนนั้นเสมอ** ห้ามส่งตารางที่ทุกช่องว่าง และห้ามปฏิเสธทั้งงานเพราะขาดข้อมูลบางอย่าง ให้ติดป้ายว่าข้อไหนยืนยันแล้ว ข้อไหนต้องยืนยันเพิ่ม · การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์
