---
name: wp-publish-draft-lite
description: >
  ส่งแพ็กเกจบทความจาก content-draft-lite ขึ้น WordPress เป็นสถานะ draft เท่านั้น
  อัปภาพพร้อม alt text ผูกภาพหลัก แล้วดึงกลับมาตรวจว่าขึ้นครบจริง
  ใช้เมื่อผู้ใช้เขียนบทความเสร็จแล้วและต้องการเอาขึ้นเว็บ
  ทำทีละบทความ ค่าเริ่มต้นเป็น dry-run และไม่เผยแพร่หน้าให้เด็ดขาด
allowed-tools:
  - Read
  - Grep
  - Glob
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


# WP Publish Draft

ส่งขึ้นเว็บเป็น **draft เท่านั้น** คนกดเผยแพร่คือผู้ใช้ ไม่ใช่สกิลนี้

---

## สามข้อที่สกิลนี้จะไม่ทำไม่ว่าจะถูกขอยังไง

1. **ไม่ตั้ง status เป็น publish** ต่อให้ผู้ใช้ยืนยันก็ตาม ให้เขาไปกดเองในหลังบ้าน
2. **ไม่แก้หรือลบหน้าที่มีอยู่แล้ว** สร้างใหม่อย่างเดียว
3. **ไม่ส่งทีละหลายบทความ** ทำทีละชิ้น จบชิ้นหนึ่งแล้วให้ผู้ใช้ตรวจก่อน

เหตุผลข้อ 3 คือ **ถ้าพลาดกับบทความเดียว แก้ง่าย ถ้าพลาดพร้อมกัน 20 บทความ ตามเก็บไม่ไหว**

---

## ขั้นที่ 0 ตรวจก่อนเริ่ม

หยุดทันทีถ้าข้อใดข้อหนึ่งไม่ผ่าน

- [ ] รัน `wp-connect-lite` แล้วได้ 200
- [ ] มีโฟลเดอร์ `03-content/{slug}/` ครบทั้ง `article.md`, `meta.json`, `images.md`
- [ ] `meta.json` มี `"status": "draft"` ถ้าเป็นอย่างอื่น **ให้หยุดแล้วถามผู้ใช้**
- [ ] `checklist.md` ติ๊กครบแล้ว ถ้ายังไม่ครบให้เตือนแล้วถามว่าจะไปต่อไหม
- [ ] หมวดหมู่ใน `meta.json` มีอยู่จริงในเว็บ ตรวจจากผลของ `wp-connect-lite`

---

## ขั้นที่ 1 dry-run ก่อนเสมอ

**ค่าเริ่มต้นคือ dry-run** แสดงให้ผู้ใช้ดูว่าจะส่งอะไรขึ้นไปบ้าง โดยยังไม่ยิงจริง

```
จะส่งขึ้น {WP_SITE_URL}

  ชื่อเรื่อง     : ...
  slug          : ...
  สถานะ         : draft
  หมวดหมู่      : ...
  ความยาว       : ... คำ
  ภาพที่จะอัป    : 3 ไฟล์
     hero.jpg      alt: "..."
     chart-1.jpg   alt: "..."

  หน้าที่ slug ซ้ำในเว็บ : ไม่มี

พิมพ์ว่า ส่งจริง เพื่อดำเนินการ
```

**ถ้าเจอ slug ซ้ำ ให้หยุด** แล้วถามว่าจะเปลี่ยน slug หรือยกเลิก **ห้ามเขียนทับ**

---

## ขั้นที่ 2 อัปภาพก่อน

อัปทีละไฟล์ แล้วเก็บ `id` ที่ได้กลับมา

```bash
curl -sS -u "$WP_USERNAME:$WP_APP_PASSWORD" \
  -H "Content-Disposition: attachment; filename=hero.jpg" \
  -H "Content-Type: image/jpeg" \
  --data-binary @hero.jpg \
  "$WP_SITE_URL/wp-json/wp/v2/media"
```

### ถ้าใช้คำสั่งพวกนี้ไม่ได้

**บาง host ไม่มีเครื่องมือรันคำสั่งให้** เช่น Cowork, Claude Desktop และ GPT desktop
สกิลนี้ต้องยิง REST API จริงถึงจะส่งขึ้นเว็บได้ **ถ้ารันคำสั่งไม่ได้ ห้ามแกล้งทำเป็นส่งสำเร็จ**
ให้เปลี่ยนไปทางทำมือแทน แล้วงานจะยังเดินต่อได้

1. บอกผู้ใช้ว่า **ให้ทำเองในหลังบ้าน WordPress** คืออัปภาพเข้า Media Library
   เติม alt text ตามที่เขียนไว้ใน `images.md` แล้วสร้างโพสต์ใหม่
   คัดลอกเนื้อหาจาก `article.md` วางลงไป ตั้งหมวดหมู่ตาม `meta.json`
   แล้ว **กด Save draft ไม่ใช่ Publish**
2. ถ้าผู้ใช้ทำเสร็จแล้ว ขอให้วางลิงก์แก้ไขของโพสต์นั้นมา แล้วไล่ตรวจ 6 ข้อในขั้นที่ 4
   เท่าที่ผู้ใช้ยืนยันได้ ข้อไหนยังไม่ได้ดูให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`
3. ต่อให้ส่งขึ้นเว็บไม่ได้เลย **ยังต้องส่งงานส่วนที่ทำได้** คือเขียน `published.md` ตามขั้นที่ 5
   ระบุว่าทำถึงไหน ค้างตรงไหน และผู้ใช้ต้องทำอะไรต่อ
   **การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์**

**บน Windows** ถ้ารันแล้วขึ้นว่าไม่รู้จักคำสั่ง ให้ลองใน Git Bash หรือ WSL
ถ้าไม่มีทั้งสองอย่าง ให้ใช้วิธีทำมือในข้อ 1

จากนั้นเขียน alt text ลงไป **ข้อนี้ห้ามข้าม** เพราะ alt text คือสิ่งที่ AI อ่าน

```bash
curl -sS -u "$WP_USERNAME:$WP_APP_PASSWORD" \
  -X POST -H "Content-Type: application/json" \
  -d '{"alt_text":"...","title":"...","caption":"..."}' \
  "$WP_SITE_URL/wp-json/wp/v2/media/{id}"
```

**เว้นอย่างน้อย 2 วินาทีระหว่างแต่ละไฟล์** โฮสต์ทั่วไปจะเริ่มปฏิเสธถ้ายิงรัวเกินไป
ถ้าเจอ 429 ให้หยุดแล้วรอ อย่ายิงซ้ำทันที

---

## ขั้นที่ 3 สร้าง draft

```bash
curl -sS -u "$WP_USERNAME:$WP_APP_PASSWORD" \
  -X POST -H "Content-Type: application/json" \
  -d @payload.json \
  "$WP_SITE_URL/wp-json/wp/v2/posts"
```

`payload.json` ต้องมี `"status": "draft"` เสมอ และมี `featured_media` เป็น id ของภาพหลัก

**เก็บ `id` ของโพสต์ที่ได้กลับมาไว้** ต้องใช้ในขั้นถัดไป

---

## ขั้นที่ 4 ดึงกลับมาตรวจ

**ข้อนี้คือหัวใจ** อย่าเชื่อว่าส่งขึ้นแล้วจะขึ้นครบ ให้ดึงกลับมาดูจริง

```bash
curl -sS -u "$WP_USERNAME:$WP_APP_PASSWORD" \
  "$WP_SITE_URL/wp-json/wp/v2/posts/{id}?context=edit"
```

ตรวจ 6 ข้อ

| ตรวจอะไร | ต้องได้อะไร |
|---|---|
| `status` | ต้องเป็น `draft` **ถ้าเป็น publish ให้แจ้งผู้ใช้ทันทีว่าผิดพลาด** |
| `title.raw` | ตรงกับที่ส่งไป |
| `content.raw` | **ต้องไม่ว่างเปล่า** ถ้าว่างแปลว่าธีมหรือ page builder กินเนื้อหาไป |
| `featured_media` | ไม่ใช่ 0 |
| `categories` | ตรงกับที่ตั้งไว้ |
| ภาพในเนื้อหา | ชี้ไป media id ที่เพิ่งอัป ไม่ใช่ path ในเครื่อง |

**ถ้า `content.raw` ว่างเปล่า** มักเกิดกับเว็บที่ใช้ page builder
ให้แจ้งผู้ใช้ว่าต้องวางเนื้อหาผ่านหลังบ้านแทน **อย่าพยายามยิงซ้ำหลายรูปแบบเพื่อให้ผ่าน**

**ถ้าดึงกลับมาไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ในข้อนั้น ห้ามเขียนว่า `ไม่มี` และห้ามเขียนว่าผ่าน**
เพราะสองคำนี้คนละความหมาย และการเขียนผิดจะทำให้ผู้ใช้เข้าใจกลับด้าน
ดึงกลับมาไม่ได้ก็ยังต้องเขียนรายงานในขั้นที่ 5 ให้ครบ พร้อมบอกว่าเหลือข้อไหนที่ผู้ใช้ต้องไปดูเอง

---

## ขั้นที่ 5 รายงานผล

เขียนลง `work/{domain}/03-content/{slug}/published.md`

```markdown
# ผลการส่งขึ้นเว็บ

| | |
|---|---|
| ส่งเมื่อ | |
| post id | |
| สถานะ | draft |
| ลิงก์แก้ไข | {WP_SITE_URL}/wp-admin/post.php?post={id}&action=edit |
| ภาพที่อัป | id และ alt text ของแต่ละไฟล์ |
| ผลการตรวจ 6 ข้อ | |
| สิ่งที่ผู้ใช้ต้องทำต่อ | |
```

แล้วเพิ่มบรรทัดลง `CHANGELOG.md` ของเว็บนั้น

### บอกผู้ใช้ให้ชัด

> บทความขึ้นเป็น **draft** แล้ว ยังไม่มีใครเห็น
> เปิดลิงก์แก้ไขไปตรวจหน้าตาก่อน แล้วกด **Publish** เองเมื่อพอใจ

---

## เมื่อเกิดข้อผิดพลาด

| รหัส | แปลว่า | ทำอะไร |
|---|---|---|
| 401 | credential ผิดหรือหมดอายุ | ให้สร้าง application password ใหม่ |
| 403 | ไม่มีสิทธิ์ หรือถูกไฟร์วอลล์กั้น | **รายงานตรง ๆ อย่าพยายามหลบ** เสนอให้คัดลอกวางเข้าหลังบ้านแทน |
| 413 | ไฟล์ภาพใหญ่เกิน | ให้ย่อภาพก่อน แนะนำไม่เกิน 1 MB |
| 429 | ยิงถี่เกินไป | หยุด รอ แล้วบอกผู้ใช้ว่าเว็บจำกัดอัตรา |
| 500 | ฝั่งเว็บพัง | หยุดทันที **ห้ามยิงซ้ำ** เพราะอาจสร้างโพสต์ซ้ำโดยไม่รู้ตัว |

**ถ้าพลาดกลางทางหลังอัปภาพไปแล้ว** ให้รายงานว่าอัปภาพไหนขึ้นไปแล้วบ้าง
พร้อม id เพื่อให้ผู้ใช้ไปลบเองได้ **สกิลนี้ไม่ลบอะไรในเว็บ**

---

## ขอบเขตของเวอร์ชันนี้

| ทำได้ | ทำไม่ได้ |
|---|---|
| สร้างโพสต์ใหม่เป็น draft | เผยแพร่หน้า |
| อัปภาพพร้อม alt text | แก้หรือลบหน้าที่มีอยู่ |
| ตั้งหมวดหมู่และแท็ก | ส่งทีละหลายบทความ |
| ดึงกลับมาตรวจ | ตั้ง canonical, redirect, หรือแก้ค่าปลั๊กอิน SEO |
| รายงานว่าพลาดตรงไหน | หลบไฟร์วอลล์หรือ rate limit |

ส่วนที่ทำไม่ได้อยู่ในรุ่นที่ใช้กับงานลูกค้า เพราะเป็นงานที่ถ้าพลาดแล้วกู้คืนยาก
และต้องมีระบบสำรองสถานะก่อนแก้ ซึ่งอยู่นอกขอบเขตของรุ่นสำหรับการเรียน
