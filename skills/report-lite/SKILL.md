---
name: report-lite
description: >
  สร้างรายงาน AISO หน้าเดียวเป็นไฟล์ HTML จากผลตรวจของสกิล aiso ในปลั๊กอินเดียวกัน
  มี 3 ส่วน คือ สรุปสถานะผ่านหรือไม่ผ่าน สิ่งที่ต้องแก้ และขั้นตอนถัดไป
  (Lite edition for workshop use.)
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


# report-lite

Read and execute the agent workflow from [agent.json](agent.json).

## โครงรายงาน

รายงานมี 3 ส่วนเท่านั้น

1. **สรุปสถานะ** ตารางบอกว่าแต่ละด้านผ่านหรือไม่ผ่าน แบ่งเป็นกลุ่ม
2. **สิ่งที่ต้องแก้** เรียงจากสำคัญมากไปน้อย ไม่เกิน 10 ข้อ
3. **ขั้นตอนถัดไป** 3 ถึง 5 ข้อ

ไม่มีคะแนนรวม ไม่มีค่าน้ำหนัก ไม่มีการให้คะแนน 0 ถึง 100 ไม่แยกมุมมองผู้บริหารกับมุมมองเทคนิค
และไม่มีระบบแท็บ

## แหล่งข้อมูล

อ่านผลจากสกิลอื่นในปลั๊กอินเดียวกัน รวม 25 ด้าน แบ่งเป็น 4 กลุ่ม

**ใส่ลงรายงานเฉพาะด้านที่มีไฟล์ผลตรวจจริง** ด้านที่ไม่มีไฟล์ให้ข้ามไป และกลุ่มที่ไม่มีไฟล์เลยสักด้าน ให้ตัดทั้งกลุ่มออก **ห้ามเดาหรือแต่งผลตรวจขึ้นเอง**

**มีไฟล์ผลตรวจน้อยก็ยังต้องส่งรายงาน** มีกี่ด้านทำเท่านั้นด้าน แล้วเขียนในบรรทัดสรุปว่า
ตรวจไปกี่ด้าน ยังไม่ได้ตรวจกี่ด้าน และต้องรันสกิลไหนต่อเพื่อให้ครบ
**การอ้างว่าข้อมูลไม่ครบแล้วไม่ส่งงาน ไม่ใช่ความซื่อสัตย์** ส่วนที่ทำได้ต้องส่ง

**ถ้าไม่มีไฟล์ผลตรวจเลยแม้แต่ไฟล์เดียว** ห้ามสร้างรายงานเปล่าที่ทุกช่องว่าง
ให้บอกผู้ใช้ว่าหาในโฟลเดอร์ไหนแล้วไม่เจออะไร แล้วให้รันสกิลตรวจอย่างน้อยหนึ่งตัวก่อน

**ฝั่ง AI**

| ด้าน | ไฟล์ผลตรวจ |
|---|---|
| AI crawlers | `*_crawler-access_*.md` |
| llms.txt | `*_llmstxt_*.md` |
| Schema ฝั่ง AI | `*_aiso-schema_*.md` |
| Technical ฝั่ง AI | `*_ai-technical_*.md` |
| เนื้อหาสำหรับ AI | `*_ai-content_*.md` |
| Citability | `*_citability-review_*.md` |
| รายแพลตฟอร์ม | `*_platform-analysis_*.md` |
| การถูกพูดถึง | `*_brand-mentions_*.md` |

**ฝั่ง SEO**

| ด้าน | ไฟล์ผลตรวจ |
|---|---|
| ภาพรวมเว็บ | `*_overview_*.md` |
| Technical พื้นฐาน | `*_technical-audit_*.md` |
| โครงหัวข้อ | `*_heading-matrix_*.md` |
| Title และ description | `*_meta-basics_*.md` |
| Schema ที่สร้างใหม่ | `*_schema-markup_*.md` |
| ลิงก์ภายใน | `*_internal-link-plan_*.md` |
| รูปภาพ | `*_image-optimization_*.md` |

**คำค้นและเนื้อหา**

| ด้าน | ไฟล์ผลตรวจ |
|---|---|
| คำค้น | `*_keyword-research_*.md` |
| กลุ่มคำค้น | `*_keyword-clusters_*.md` |
| ช่องว่างเนื้อหา | `*_content-gap_*.md` |
| คู่แข่ง | `*_competitor-analysis_*.md` |
| โครงหัวข้อเชิงลึก | `*_topical-map_*.md` |
| ตรวจเนื้อหาเดิม | `*_content-audit_*.md` |
| ปรับเนื้อหาเดิม | `*_content-enhancement_*.md` |
| กลยุทธ์เนื้อหา | `*_content-strategy_*.md` |

**นอกเว็บ**

| ด้าน | ไฟล์ผลตรวจ |
|---|---|
| ท้องถิ่น | `*_local-seo_*.md` |
| ลิงก์จากเว็บอื่น | `*_backlink-strategy_*.md` |

## กติกาความซื่อสัตย์ของตัวเลข

ใช้กับ **ทุกตัวเลข** ที่หลุดเข้ามาในรายงาน ไม่ว่าจะยกมาจากไฟล์ผลตรวจของสกิลอื่น
หรือผู้ใช้แปะมาเองจากเครื่องมือภายนอก เช่น หน้าคอนโซลของ search engine หรือ analytics ของเว็บ

ข้อนี้ **ไม่เปลี่ยนโครงรายงาน 3 ส่วน ไม่เพิ่ม placeholder และไม่เปลี่ยนค่าสถานะในตาราง**
เป็นกติกาว่าจะเขียนอะไรรอบ ๆ ตัวเลขได้บ้างเท่านั้น รอบไหนไม่มีตัวเลขแบบนี้เลยให้ข้ามหัวข้อนี้

### 1 ติดป้ายว่าตัวเลขนั้นเก็บมาด้วยวิธีไหน และวิธีนั้นมองไม่เห็นอะไร

| วิธีเก็บ | จุดบอดที่ต้องเขียนกำกับ |
|---|---|
| ฝั่งเซิร์ฟเวอร์ เช่น log ของเว็บ | นับทุกอย่างที่ยิงเข้ามารวมทั้งบอท ต้องแยกบอทออกก่อนถึงจะเรียกว่าคนเข้าเว็บ |
| ฝั่งเบราว์เซอร์ ผ่านสคริปต์ติดตาม | ต้องรันสคริปต์สำเร็จถึงจะถูกนับ ไม่รันคือหายไปเลย |
| ฝั่งแพลตฟอร์มค้นหา เช่นหน้าคอนโซล | เห็นเฉพาะสิ่งที่เกิดในผลค้นหาของเจ้านั้น ไม่เห็นทางเข้าอื่น |

ไม่รู้ว่าตัวเลขมาจากทางไหน ให้เขียนว่า `ตรวจไม่ได้` **ห้ามเดาที่มาให้**

### 2 สคริปต์ติดตามวัดบอทไม่ได้ ห้ามเอามาตอบว่า AI เข้าเว็บหรือไม่

บอทที่เรนเดอร์หน้าเว็บได้ จะรู้จักสคริปต์ติดตามยอดนิยมแล้วข้ามมันไปเพื่อประหยัดทรัพยากร
ส่วนบอทอื่นส่วนใหญ่ไม่รันสคริปต์อยู่แล้ว
ตัวเลขจากสคริปต์ติดตามจึง **ใช้เป็นหลักฐานว่าบอทเข้าหรือไม่เข้าเว็บไม่ได้เลย**
คำถามว่า AI crawler เข้าถึงได้ไหม ให้ตอบจากไฟล์ผลของ `aiso-crawlers-lite` เท่านั้น

### 3 สองแหล่งไม่ตรงกันเป็นเรื่องปกติ ห้ามเกลี่ยให้เท่ากัน

VPN ส่วนขยายเบราว์เซอร์ และเครื่องมือกันติดตาม ทำให้สคริปต์ไม่ทำงาน
แต่การเข้าชมนั้นยังโผล่ในฝั่งเซิร์ฟเวอร์อยู่ ตัวเลขฝั่งสคริปต์จึงเป็นส่วนย่อยของของจริงเสมอ
ตัวเลขสองฝั่งไม่ตรงกันคือ **สิ่งที่ควรเป็น ไม่ใช่ข้อผิดพลาดที่ต้องหาทางทำให้ตรงกัน**
ให้รายงานทั้งสองค่าพร้อมบอกว่าแต่ละค่ามาจากไหน ห้ามเลือกมาค่าเดียวแล้วทิ้งอีกค่าเงียบ ๆ

### 4 ค่าที่ประมาณจากแบบจำลอง ห้ามวางข้างค่าที่นับได้จริงเหมือนเป็นของชนิดเดียวกัน

ตัวเลขบางตัวในเครื่องมือสมัยใหม่ไม่ได้นับจากเหตุการณ์จริงทั้งหมด แต่เป็นค่าที่แบบจำลองเติมให้
ตัวเลขแบบนั้น **ต้องติดป้ายว่าเป็นค่าประมาณ** และห้ามวางเรียงกับค่าที่นับได้จริงราวกับมั่นใจเท่ากัน

### 5 ตัวเลขฝั่งค้นหากับฝั่ง analytics นับคนละอย่าง ต้องเคลียร์ก่อนเทียบ

| เรื่อง | ฝั่งแพลตฟอร์มค้นหา | ฝั่ง analytics ของเว็บ |
|---|---|---|
| URL ที่รายงาน | ยุบไปรวมที่ URL หลัก แม้คนคลิกเข้าหน้าที่เป็นตัวแปร | รายงาน URL หลังการเปลี่ยนเส้นทางแล้ว |
| ขอบเขต | ผูกกับโดเมนเดียว | ครอบได้หลายโดเมน |
| เวลา | ใช้เขตเวลาของแพลตฟอร์ม | ใช้เขตเวลาที่ตั้งไว้ในบัญชี |
| ต้องรันสคริปต์ไหม | ไม่ต้อง | ต้อง ไม่รันคือไม่ถูกนับ |
| จำนวน URL ที่เก็บ | มีเพดานต่อวัน เกินเพดานคือหายเงียบ ตัวเลขที่เห็นจึงเป็นอย่างน้อยเท่านั้น | ไม่มีเพดานแบบนั้น |

คำเดียวกันยังหมายคนละอย่างระหว่างเครื่องมือ เช่นคำว่า impression และ click
บางเครื่องมือรวมโฆษณาเข้าไปด้วย บางเครื่องมือนับเฉพาะผลค้นหาธรรมชาติ
**ห้ามเอาค่าของสองเครื่องมือมาวางในแกนเดียวกันโดยไม่บอกว่าแต่ละค่านับอะไร**

### 6 อีกสองข้อที่ต้องเขียนกำกับเมื่อมีตัวเลขพวกนี้

- **ประวัติย้อนหลังของคอนโซลมีเพดาน** เก่ากว่านั้นหายถาวรและเรียกกลับมาไม่ได้
  งานที่ตั้งใจจะเทียบข้ามปี ต้องเริ่มดึงข้อมูลออกมาเก็บตั้งแต่วันแรก ไม่ใช่ไปหาเอาตอนจะเทียบ
- **รายงานอัตราส่วนคู่กับยอดรวมเสมอ** เช่น สัดส่วนหน้าที่ถูกเก็บเข้าระบบเทียบกับหน้าที่ถูกไล่อ่าน
  สัดส่วนหน้าที่มีคนเข้าจากการค้นหาจริงเทียบกับหน้าทั้งหมด และสัดส่วนคำค้นที่มีชื่อแบรนด์เทียบกับที่ไม่มี
  สัดส่วนที่ตกลงชี้ปัญหาคุณภาพหรือปัญหาแม่แบบ ซึ่งกราฟยอดรวมกลบไว้
  รุ่นนี้รายงานเป็นแนวโน้มขึ้นหรือลง ไม่ตั้งเกณฑ์ตัวเลขว่าเท่าไรถึงจะผ่าน

## เทมเพลต

อ่าน [templates/report-template.html](templates/report-template.html) แล้วแทนค่า placeholder ทุกตัว

| Placeholder | ใส่อะไร |
|---|---|
| `{{REPORT_TITLE}}` | ชื่อรายงาน เช่น รายงานสถานะ AI visibility |
| `{{DOMAIN}}` | โดเมนที่ตรวจ |
| `{{REPORT_DATE}}` | วันที่ตรวจ รูปแบบ YYYY-MM-DD |
| `{{SUMMARY_LINE}}` | สรุปภาพรวม 1 ถึง 2 ประโยค |
| `{{SUMMARY_HINT}}` `{{FIX_HINT}}` `{{NEXT_HINT}}` | คำอธิบายสั้นใต้หัวข้อแต่ละส่วน |
| `{{STATUS_ROWS}}` | แถวทั้งหมดของตารางสรุปสถานะ สร้างเองตามรูปแบบใน comment ของเทมเพลต |
| `{{FIX_ITEMS}}` | รายการ `<li>` ของสิ่งที่ต้องแก้ ไม่เกิน 10 |
| `{{NEXT_STEPS}}` | รายการ `<li>` ของขั้นตอนถัดไป 3 ถึง 5 |
| `{{FOOTER_NOTE}}` | ที่มาของข้อมูลและวันที่สร้างไฟล์ |

รูปแบบแถวและรูปแบบ `<li>` ของแต่ละรายการ ดูได้จาก comment ในไฟล์เทมเพลต

## ปิดท้ายทุกครั้งด้วยการ์ด Tier 1

รายงาน HTML คือชั้นที่ 2 (ฉบับเต็ม ส่งลูกค้า) ทุกการเรนเดอร์ต้องจบด้วยการ์ดสรุปในแชตซึ่งเป็นชั้นที่ 1
สร้าง `work/{domain}/04-reports/{domain}_{skillkey}_{YYYY-MM-DD}_summary.json` จากข้อมูลชุดเดียวกับรายงาน

- ถ้ารอบนี้มี JSON จาก `agent_readiness_lite.py`, `page_analyzer.py`, `robots_generator.py --output json`,
  ไฟล์ checklist ของ `aiso-platform-lite` หรือไฟล์ sampling ของ `aiso-brand-mentions-lite` ให้ประกอบด้วย
  `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/build_summary.py --agent ... --page ... --robots ... --checklist ... --sampling ... --client "{ชื่อ}" --domain {domain} --lang th --skill {skillkey} --tier2 "{path รายงาน}" --summary "{สรุป 2 ถึง 3 ประโยค}" --out {summary path}`
  ตัวประกอบไม่ประเมินอะไรเพิ่ม ข้อมูลที่ไม่มีก็ไม่มีบล็อกนั้น
- ถ้าไม่มีไฟล์พวกนั้น ให้เขียน summary.json ด้วยมือตาม `templates/widget/summary.schema.json`
  `dimensions[]` คือด้านในตารางสถานะ value = จำนวนข้อที่ได้ระดับ ดี, max = จำนวนข้อที่ตรวจ, `status` ตามระดับ
  `key_risk` คือข้อแรกของรายการงาน, `actions` คือ 4 ข้อแรก, `transparency.could_not_verify` คือทุกแถวที่ ตรวจไม่ได้
  `handoff.tier2_path` คือ path ของรายงาน HTML **ห้ามใส่บล็อก `score`** รุ่นนี้ไม่มีคะแนน
- ตรวจด้วย `present.py --summary {summary path} --lint` แล้วเรนเดอร์ `present.py --summary {summary path} --target auto --host {host}`
  แสดงผ่านพื้นผิวของ host (widget, artifact, บล็อก text สำหรับ ascii, หรือ Markdown) ตามบันไดใน `so-present-lite`
- การ์ดคือประตูสู่รายงาน ไม่ใช่ตัวแทน รายงาน HTML ไม่ถูกย่อเพราะมีการ์ด

## กฎการเขียน


- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`** สองคำนี้คนละความหมาย ถ้าเขียนผิดผู้ใช้จะสรุปกลับด้าน
- ห้ามใช้ em dash และห้ามใส่ emoji ในรายงาน
- ทุกข้อในส่วนที่ 2 ต้องบอกว่าต้องทำอะไร ไม่ใช่บอกแค่ว่าอะไรผิด
- **ไฟล์ต้นทางเขียนว่า `ตรวจไม่ได้` ให้คงคำว่า `ตรวจไม่ได้` ห้ามแปลงเป็น `ไม่ผ่าน`**
  ใช้ badge แบบ `na` กับแถวนั้น แล้วเขียนในช่องสิ่งที่ตรวจพบว่าขาดอะไรถึงตรวจไม่ได้
  สองคำนี้คนละความหมาย เขียนผิดแล้วคนอ่านจะสรุปกลับด้าน
- ด้านที่มีไฟล์ แต่ในไฟล์ยืนยันไม่ได้ทุกหัวข้อ ให้คงแถวไว้ด้วยสถานะ `ตรวจไม่ได้` ห้ามตัดแถวทิ้ง
- **ตัวเลขทุกตัวที่ยกมาใส่รายงาน ต้องผ่านหัวข้อ กติกาความซื่อสัตย์ของตัวเลข ก่อน**
  อย่างน้อยต้องบอกได้ว่าเก็บมาด้วยวิธีไหน และเป็นค่าที่นับได้จริงหรือค่าประมาณ
  บอกไม่ได้ให้เขียนว่า `ตรวจไม่ได้` แทนการใส่ตัวเลขลอย ๆ
- ก่อนส่งงาน ต้องไม่เหลือข้อความ `{{` ในไฟล์ผลลัพธ์

## Output

```
{domain}_aiso-report_{YYYY-MM-DD}.html
```

## การวางไฟล์ผลลัพธ์

1. หาไฟล์ต้นทางใน `work/{domain}/01-current/` ก่อน ถ้าหัวข้อไหนไม่มีให้หาต่อใน `work/{domain}/00-baseline/`
2. ถ้าหัวข้อเดียวกันมีหลายไฟล์ ให้ใช้ไฟล์ที่วันที่ในชื่อล่าสุด
3. เขียนรายงานลง `work/{domain}/04-reports/`
4. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md`
5. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน
