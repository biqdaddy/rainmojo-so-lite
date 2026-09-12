---
name: seo-keyword-clustering-lite
description: >
  จัดกลุ่มคำค้นตามความหมายและ search intent แล้ววางโครงเนื้อหาแบบ pillar-cluster พร้อมแผนลิงก์ภายใน
  ใช้เมื่อมีคำค้นแล้ว ต้องตัดสินใจว่าจะทำเนื้อหากี่กลุ่ม หน้าไหนเป็น pillar และเริ่มกลุ่มไหนก่อน
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


# Keyword Clustering

ตอบคำถามเดียวคือ **คำค้นกองนี้ควรกลายเป็นเนื้อหากี่กลุ่ม และแต่ละกลุ่มหน้าตาเป็นอย่างไร**

## ข้อมูลที่ต้องมี

| ต้องมี | อยู่ที่ไหน |
|---|---|
| คำค้น 20 ถึง 50 คำ | ผลจาก `seo-keyword-research-lite` ใต้ `work/{domain}/` หรือวางมาในแชต |
| ธุรกิจทำอะไร ขายใคร | ผู้ใช้บอก หรือไฟล์ใต้ `work/{domain}/` |
| หน้าเดิมบนเว็บ | มี URL ให้เปิดอ่านด้วย WebFetch เพื่อตรวจว่าชนของเดิมไหม เปิดไม่ได้ให้เขียนว่า `ตรวจไม่ได้` ไม่มี URL ให้เขียนเป็นข้อจำกัด |

**คำค้นน้อยกว่า 15 คำ ให้บอกตรง ๆ ว่าไม่พอ** ทำเท่าที่มีได้แต่ต้องระบุข้อจำกัด

## ขั้นที่ 1 ติดป้ายคำค้นสองแกน

**แกนความหมาย** คำไหนพูดเรื่องเดียวกันจริง ไม่ใช่แค่มีคำซ้ำ
"รากฟันเทียม ราคา" กับ "ค่าใช้จ่ายรากฟันเทียม" เรื่องเดียวกัน "เจ็บไหม" คนละเรื่อง

| แกน search intent | ผู้ค้นต้องการ | เนื้อหาที่ตอบได้ |
|---|---|---|
| หาความรู้ | เข้าใจเรื่องนั้น "X คืออะไร" | บทความอธิบาย คู่มือ |
| เปรียบเทียบ | ชั่งใจก่อนตัดสินใจ "X ที่ไหนดี" | หน้าเปรียบเทียบ รีวิว |
| ลงมือทำ | ซื้อ จอง นัดหมาย | หน้าบริการ หน้าราคา |
| หาแบรนด์ | ไปหน้าที่รู้จักอยู่แล้ว | หน้าแบรนด์ หน้าสาขา |

คำไทยกับอังกฤษความหมายเดียวกันอยู่กลุ่มเดียวกัน เผื่อคำถามยาวแบบภาษาพูด
และคำต่อท้ายอย่าง "pantip" ที่แปลว่าอยากได้ความเห็นคนจริง

## ขั้นที่ 2 สร้างกลุ่มและจัดลำดับชั้นคำ

ทำ 5 ถึง 8 กลุ่ม หนึ่งกลุ่มคือหนึ่งหัวเรื่องที่เราตั้งใจเป็นเจ้าของ ไม่ใช่ถังรวมคำที่เหลือ
ตั้งชื่อให้รู้ธีม เขียนจุดประสงค์กำกับกลุ่มละหนึ่งประโยค เกิน 8 กลุ่มให้ควบรวม
กลุ่มที่ใหญ่ผิดปกติให้แตกออก แล้วแบ่งคำสามระดับ

| ระดับ | จำนวน | เกณฑ์เลือก |
|---|---|---|
| Primary | 1 คำ | แทนหัวเรื่องทั้งกลุ่มได้ดีสุดและตรงเป้าธุรกิจสุด |
| Secondary | 3 ถึง 5 คำ | ขยายมุมหัวเรื่อง ใช้เป็นหัวข้อย่อยหรือบทความรอง |
| Long-tail | ที่เหลือ | คำเฉพาะเจาะจง ใช้เป็น FAQ หรือประเด็นย่อย |

หนึ่งคำอยู่ได้หนึ่งกลุ่ม ถ้าเข้าได้สองกลุ่มให้ตัดสินด้วย intent แล้วจดไว้ตรวจซ้ำในขั้นที่ 4

## ขั้นที่ 3 วางโครง pillar-cluster และลิงก์ภายใน

| ส่วน | เป้าคำค้น | ลักษณะ |
|---|---|---|
| Pillar | primary หน้าเดียวต่อกลุ่ม | ครอบคลุมภาพรวม ลึกพอเป็นหน้าอ้างอิงของเรื่องนั้น |
| Supporting | secondary และ long-tail | เจาะหนึ่งประเด็นต่อหน้าให้จบ ไม่ทับภาพรวม pillar |

รูปแบบ pillar เลือกตาม intent ของ primary ตามคอลัมน์ขวาของตารางในขั้นที่ 1
ความลึกดูว่า **อ่านจบแล้วไม่ต้องไปหาต่อไหม** ห้ามกำหนดเป็นจำนวนคำ

ลิงก์แบบ hub-and-spoke คือหน้ารองลิงก์ขึ้นหา pillar ของกลุ่มตัวเอง และ pillar ลิงก์ลงหาทุกหน้ารอง
anchor ต้องหลากหลาย ห้ามใช้คำ primary เป๊ะ ๆ ทุกลิงก์ ข้ามกลุ่มเฉพาะที่เกี่ยวข้องจริงและให้เป็น
pillar ถึง pillar ผลคือตาราง จากหน้า / ไปหน้า / anchor

## ขั้นที่ 4 ตรวจหน้าชนกันเองแล้วจัดลำดับ

ไล่ทุกคู่กลุ่มและคำก้ำกึ่งจากขั้นที่ 2 มีหน้าเดิมให้เปิดด้วย WebFetch แล้วเทียบด้วย
เปิดหน้านั้นไม่สำเร็จให้เขียนว่า `ตรวจไม่ได้` ไม่มี URL ของหน้าเดิมเลยให้เขียนว่ายังไม่ได้ตรวจ

| อาการ | ความเสี่ยง | วิธีแก้ |
|---|---|---|
| สองหน้า intent เดียวกัน ความหมายแทบเดียวกัน | สูง | รวมเป็นหน้าเดียว หรือย้ายคำไปกลุ่มเดียว |
| คำใกล้กันแต่ intent ต่างชัด | ต่ำ | แยกหน้าได้ แต่เขียนมุมให้ต่างกันชัด |
| หน้ารองเขียนภาพรวมจนทับ pillar | กลาง | ตัดภาพรวมออก แล้วลิงก์ไป pillar แทน |

จากนั้นตัดสินแต่ละกลุ่มสามแกน ให้ค่าได้แค่ สูง กลาง ต่ำ

| แกน | ถามว่า |
|---|---|
| ผลต่อธุรกิจ | ใกล้เงินแค่ไหน พาไปซื้อหรือติดต่อได้ตรงไหม |
| โอกาสแข่งขัน | มีคนทำดีอยู่แล้วเยอะไหม ยังมีมุมที่ไม่มีใครครอบคลุมไหม |
| แรงที่ต้องใช้ | ต้องเขียนกี่หน้า ใช้ความเชี่ยวชาญพิเศษไหม มีของเดิมต่อยอดไหม |

เริ่มจากกลุ่มที่ผลต่อธุรกิจสูงและแรงที่ต้องใช้ต่ำ **ห้ามแปลงสามแกนเป็นคะแนนหรือถ่วงน้ำหนัก**

## ขั้นที่ 5 ส่งออก

```
work/{domain}/(00-baseline|01-current)/{domain}_keyword-clusters_{YYYY-MM-DD}.md
```

ชื่อไฟล์นี้ประกาศเหมือนกันเป๊ะกับใน agent.json เรียงหัวข้อในไฟล์ตามนี้

1. **ภาพรวม** ตาราง กลุ่ม / จุดประสงค์ / primary / ผลต่อธุรกิจ / ลำดับที่ควรทำ
2. **รายกลุ่ม** คำค้นสามระดับ รูปแบบ pillar และหน้ารองที่ต้องเขียน
3. **แผนลิงก์ภายใน** และ **หน้าที่เสี่ยงชนกัน** พร้อมวิธีแก้
4. **ลำดับการลงมือทำ** และ **ข้อจำกัดครั้งนี้** ว่าอะไรที่ยังสรุปไม่ได้

ต่อด้วย `meta-basics-lite` เพื่อเขียน title และ meta description ของแต่ละหน้า

## ส่งต่อคู่ลิงก์ให้ `seo-internal-linking-lite` ไม่กำหนด anchor เอง

- สกิลนี้ออกได้แค่ **คู่คลัสเตอร์ที่ควรมีลิงก์ถึงกัน** พร้อมเหตุผลต่อคู่ (ต้นทาง, ปลายทาง, เหตุผล)
  แล้วส่งเป็น input ของสกิลลิงก์ภายใน ซึ่งเป็นเจ้าของ anchor text, โหมด anchor, ตำแหน่งลิงก์ และจำนวนลิงก์ต่อหน้า
  คู่ที่ไม่ผ่านเกณฑ์ของสกิลนั้นถูกตัดออกได้ตามปกติ ห้ามเลือกข้อความ anchor หรือกำหนดจำนวนลิงก์ที่นี่
- **การนับตัวอักษร** ของชื่อคลัสเตอร์ title ที่เสนอ และคำถาม นับทุก code point ไทยเป็น 1 รวมสระและวรรณยุกต์
  ใช้กติกาเดียวกับ `meta-basics-lite`

## การวางไฟล์ผลลัพธ์

สกิลนี้อยู่ในชุดที่ใช้โครงโฟลเดอร์ของสกิล `new-workspace-lite`

1. ผลลัพธ์ทุกไฟล์อยู่ใต้ `work/{domain}/`
2. ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์หัวข้อเดียวกัน ให้เขียนลง `00-baseline/` ถ้ามีแล้ว ให้เขียนลง `01-current/`
3. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร
4. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน ห้ามสร้างโครงเองแบบอื่น

## กฎ

- **ห้ามเดาตัวเลข** ไม่มี search volume ไม่มีค่าความยาก ไม่ได้รับมาให้เขียนว่าไม่มีข้อมูล
- **ห้ามให้คะแนนหรือถ่วงน้ำหนัก** ใช้ระดับ สูง กลาง ต่ำ พร้อมเหตุผลเป็นประโยค
- **ห้ามแต่งคำค้นเพิ่มแล้วอ้างว่ามาจากการวิจัย** เสนอเพิ่มได้แต่ต้องติดป้ายว่าเป็นคำแนะนำ
- **ห้ามฟันธงเรื่องคู่แข่งถ้าไม่ได้อ่านหน้าเขาจริง** ให้เขียนว่าเป็นข้อสันนิษฐาน
- หนึ่งคำอยู่ได้หนึ่งกลุ่ม คำก้ำกึ่งต้องผ่านขั้นที่ 4 ก่อนสรุป
- ถ้าข้อมูลไม่พอ ให้บอกตรง ๆ และเขียนข้อจำกัดไว้ ห้ามทำเหมือนข้อมูลครบ
- **ขาดข้อมูลบางอย่างแล้วยังทำได้บางส่วน ต้องส่งส่วนที่ทำได้เสมอ** เช่นไม่รู้หน้าเดิมบนเว็บ
  ก็ยังจัดกลุ่มและวางโครง pillar-cluster ได้ แล้วติดป้ายให้ชัดว่าข้อไหนยืนยันจากคำค้นที่ได้รับจริง
  ข้อไหนต้องยืนยันเพิ่ม **การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์**
- **ดึงหน้าเว็บไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`** สองคำนี้คนละความหมาย
  และเขียนผิดจะทำให้ผู้ใช้สรุปกลับด้าน
