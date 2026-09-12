---
name: seo-image-optimizer-lite
description: >
  แปลงภาพเป็น WebP ย่อขนาด ตั้งชื่อไฟล์อังกฤษจากการดูภาพจริง และลบ EXIF
  ใช้เมื่อมีภาพจะเอาขึ้นเว็บ ภาพหนักเกิน หรือชื่อไฟล์เป็นไทยหรือเป็นรหัสกล้อง
allowed-tools:
  - Read
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


# SEO Image Optimizer

ทำภาพให้พร้อมขึ้นเว็บ 4 เรื่อง ไฟล์เบา ชื่อสื่อความหมาย ไม่มี EXIF และเป็น WebP
AI ไม่ได้ดูภาพ **มันอ่านชื่อไฟล์กับ alt text** ชื่อ `IMG_1234.jpg` จึงไม่บอกอะไรเลย

---

## ขั้นที่ 1 เตรียมและสแกน

| ต้องมี | อยู่ที่ไหน |
|---|---|
| ภาพต้นฉบับ | `work/{domain}/uploads/` หรือโฟลเดอร์ที่ผู้ใช้ระบุ |
| บริบท ใช้กับหน้าไหน แบรนด์อะไร ภาษาเว็บ | ถามผู้ใช้ หรือ `work/{domain}/site.md` |
| ความกว้างเป้าหมาย | ไม่ระบุใช้ 1200px |

**`uploads/` อ่านอย่างเดียว** ผลลัพธ์ต้องเป็นไฟล์ใหม่เสมอ

ตรวจ Pillow ด้วย `python -c "import PIL; print(PIL.__version__)"` ถ้าไม่มีให้เสนอ `pip install Pillow`
ห้ามเดาผลแทนการรัน จากนั้นแก้ path แล้วสแกน

**ถ้าติดตั้ง Pillow ไม่ได้ หรือ host นี้รันคำสั่งไม่ได้ ห้ามจบงานเปล่า**
บาง host ไม่มีเครื่องมือรันคำสั่งให้ เช่น Cowork, Claude Desktop และ GPT desktop
กรณีนั้นให้ทำส่วนที่ยังทำได้ต่อ คือเปิดดูภาพด้วย Read ตั้งชื่อใหม่ตามขั้นที่ 2
เขียน alt text แนะนำ และส่งสคริปต์ในขั้นที่ 3 ให้ผู้ใช้ไปรันเอง
แล้วติดป้ายทุกบรรทัดว่า **ยืนยันแล้ว** หรือ **ต้องยืนยันเพิ่ม**
ช่องที่ยังไม่ได้รันจริง เช่น ฟอร์แมต มิติ ขนาดไฟล์ และ EXIF ให้เขียนว่า **ตรวจไม่ได้**

```bash
python - <<'PY'
from PIL import Image
from pathlib import Path
E = {".jpg",".jpeg",".png",".bmp",".tiff",".tif",".gif",".webp"}
for p in sorted(Path("work/example-com/uploads").rglob("*")):
    if p.suffix.lower() in E:
        im = Image.open(p)
        print(p.name, im.format, f"{im.width}x{im.height}",
              p.stat().st_size // 1024, "KB", "EXIF", bool(im.getexif()))
PY
```

สรุปรายไฟล์เป็นระดับ ไม่มีคะแนน

| สิ่งที่เจอ | ระดับ |
|---|---|
| ไม่ใช่ WebP หรือกว้างเกินเป้าหมายมาก | ต้องแก้ |
| ชื่อไฟล์เป็นไทย มีช่องว่าง หรือเป็นรหัสกล้อง | ต้องแก้ |
| มี EXIF เสี่ยงพิกัด GPS ติดไปกับไฟล์ | ต้องแก้ |
| WebP ชื่อดี ขนาดพอดี ไม่มี EXIF | ผ่าน |

ถ้าผู้ใช้ขอแค่ตรวจ ให้จบที่นี่แล้วข้ามไปขั้นที่ 4 โดยไม่แตะไฟล์

---

## ขั้นที่ 2 ตั้งชื่อจากการดูภาพจริง

**ห้ามข้ามขั้นนี้** เปิดดูภาพทีละไฟล์ด้วย Read แล้วตั้งชื่ออังกฤษจากสิ่งที่เห็น ไม่ใช่จากชื่อเดิม

| กติกา | ตัวอย่าง |
|---|---|
| พิมพ์เล็ก คั่นขีดกลาง ไม่มีอักษรไทย ช่องว่าง อักขระพิเศษ | `dental-implant-procedure` |
| บอกสิ่งที่อยู่ในภาพจริง ห้าม generic แบบ image-1 | `thai-food-signature-dish` |
| ใส่แบรนด์หรือสถานที่เมื่อเกี่ยว ยาวไม่เกิน 5-6 คำ | `condo-river-view-bangkok` |
| ภาพชุดเดียวกันต่อท้ายเลขลำดับ | `dental-implant-guide-1`, `-2` |

ทำตารางจับคู่ให้ผู้ใช้ดูก่อนแปลง คอลัมน์ ไฟล์เดิม / เห็นอะไรในภาพ / ชื่อใหม่
ภาพที่เปิดไม่ได้ ให้แยกกลุ่มข้ามพร้อมเหตุผล **ห้ามตั้งชื่อเดา**

---

## ขั้นที่ 3 แปลงภาพ

แก้ path และ `NAMES` ตามงานจริงแล้วรัน การ save ใหม่โดยไม่ส่ง exif ทำให้ EXIF และ GPS หายหมด

```bash
python - <<'PY'
from PIL import Image
from pathlib import Path
SRC = Path("work/example-com/uploads")
DST = Path("work/example-com/03-content/images")
NAMES = {"IMG_1234.jpg": "dental-checkup-procedure-1"}
W, Q = 1200, 85
DST.mkdir(parents=True, exist_ok=True)
for old, new in NAMES.items():
    im = Image.open(SRC / old)
    if "A" in im.getbands() or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        im = Image.new("RGB", rgba.size, (255, 255, 255))
        im.paste(rgba, mask=rgba.split()[-1])
    else:
        im = im.convert("RGB")
    if im.width > W:
        im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    out = DST / f"{new}.webp"
    im.save(out, "WEBP", quality=Q)
    print(old, "->", out.name, out.stat().st_size // 1024, "KB")
PY
```

| เรื่อง | วิธีจัดการ |
|---|---|
| ภาพโปร่งใส | วางทับพื้นขาวก่อน ไม่งั้นพื้นเป็นดำ |
| ภาพเล็กกว่าเป้าหมาย | คงขนาดเดิม **ห้ามขยาย** เพราะขยายแล้วแตก |
| อัตราส่วน | คงเดิม ย่อตามสัดส่วน |
| `Q` | ค่าตั้ง encoder ไม่ใช่คะแนนภาพ เริ่มต้น 85 ปรับได้ |

ความกว้างตามการใช้งาน hero 1920px, บทความ 1200px, สินค้า 800px, thumbnail 400px

---

## ขั้นที่ 4 ตรวจผลและเขียนรายงาน

รันสแกนขั้นที่ 1 ซ้ำที่ปลายทาง ยืนยันว่าเป็น WebP กว้างไม่เกินเป้าหมาย และ EXIF ไม่เหลือ
**ตัวเลขทุกตัวต้องมาจากผลรันจริง** ถ้ารันสแกนซ้ำไม่สำเร็จ ให้เขียนช่องนั้นว่า `ตรวจไม่ได้`
ห้ามเขียนว่า `ไม่มี EXIF` เพราะยังไม่ได้ยืนยัน แล้วส่งรายงานส่วนที่ทำได้ต่อไปตามปกติ
รายงาน `{domain}_image-optimization_{YYYY-MM-DD}.md` เรียงตามนี้

1. **สรุปย่อหน้าเดียว** แปลงกี่ไฟล์ ข้ามกี่ไฟล์ ขนาดรวมก่อนและหลัง
2. **ผลรายไฟล์** ไฟล์เดิม / ชื่อใหม่ / ขนาดก่อน / ขนาดหลัง / มิติใหม่ / ผ่านหรือไม่ผ่านพร้อมเหตุผล
3. **alt text แนะนำ** ไฟล์ใหม่ / alt text ตามภาษาเว็บ บรรยายสิ่งที่เห็นจริง ไม่ยัดคำค้น
4. **ไฟล์ที่ข้าม** พร้อมเหตุผลรายไฟล์
5. **ขั้นถัดไป** เช่นใช้ภาพกับ `content-draft-lite` หรือส่งขึ้นเว็บด้วย `wp-publish-draft-lite`

ภาพที่แปลงแล้วอยู่ที่ `work/{domain}/03-content/images/` รายงานวางตามกติกาข้างล่าง

---

## ตรวจว่าภาพถูก index ได้ และ alt เป็น markup ที่ใช้ได้จริง (รันต่อจากการจัดชื่อไฟล์และ alt)

ตารางโหมดความล้มเหลว ขั้นตอนตรวจ และเกณฑ์ตัดสินอยู่ที่
`{PLUGIN_ROOT}/skills/rainmojo-so-lite/reference/frameworks/image-optimizer-indexability-and-alt.json`
อ่านไฟล์นั้นก่อนรัน กฎด้านล่างบังคับผลตัดสินไม่ว่าจะอ่านหรือไม่

- **CSS background ไม่ถูก index** ระบบอ่านภาพจาก HTML เท่านั้น ภาพที่ต้องถูกค้นเจอต้องมี img element จริง
- **Lazy load ต้องมีตัวช่วยสองอย่างพร้อมกัน** ประกาศภาพใน image sitemap และส่งแบบ responsive ด้วย picture หลาย source หรือ img ที่มี srcset
- **ตำแหน่งใน sidebar, header หรือ footer ถูกนับเป็นของตกแต่ง** ภาพสำคัญต้องอยู่ในเนื้อหาช่วงบน การแก้คือย้ายตำแหน่ง ไม่ใช่เขียน alt ให้ดีขึ้น
- **Hotlink protection ปิดทางขึ้นผลค้นหาภาพ** ถ้าเซิร์ฟเวอร์บล็อกการแสดงข้าม origin ภาพจะไม่ปรากฏในผลค้นหาภาพ
- **โฮสต์ภาพบน top-level domain เดียวกับหน้า**
- **ปิด embedded thumbnail ตอน export** เพราะทำให้ไฟล์ใหญ่เกินจำเป็นและทำให้ pipeline บีบอัดบางตัวพัง
- **แยก decorative กับ content ก่อนเขียน alt** ภาพตกแต่ง (spacer, border) ต้องมี alt ว่างหรือไม่มี alt เลย
  การเขียน alt บรรยายให้ภาพตกแต่งเป็นความผิด ไม่ใช่แค่ไม่จำเป็น
- **ตรวจว่า attribute เป็น markup ที่ใช้ได้** ค่า alt ต้องอยู่ในเครื่องหมายคำพูด ถ้าไม่ใส่ ทุกอย่างหลังคำแรกจะหายไป
  และ alt ที่ CMS สร้างซึ่งมี apostrophe หรือ quotation mark ที่ไม่ escape จะทำให้ tag ใช้ไม่ได้
- **title attribute** เมื่อมี alt แล้ว title ซ้ำซ้อน ไม่ต้องใส่ ถ้าระบบบังคับ ให้ใช้ชุดคำเดียวกับ alt และห้ามปล่อยให้แสดงเป็นขีดคั่นแทนช่องว่าง

เกณฑ์ผ่าน: ทุกภาพที่ตรวจมีแถวระบุว่าโหมดความล้มเหลวใดทำงานหรือไม่มีเลย class ของ alt (decorative หรือ content)
สถานะความถูกต้องของ attribute และหลักฐานที่อ่านได้จริงในรอบนี้ ภาพที่ยืนยัน index ไม่ได้ ลง ตรวจไม่ได้ ห้ามสรุปว่าไม่ถูก index

**โหมดเดี่ยว** ถ้าถูกเรียกตรงโดยไม่มีข้อมูลคำแกนของหน้าจากสกิลอื่น ให้ใช้ H1 ของหน้าปลายทางเป็นคำแกน
และเขียนบรรทัดแรกของรายงานว่าใช้โหมดเดี่ยว

## การวางไฟล์ผลลัพธ์

สกิลนี้อยู่ในชุดที่ใช้โครงโฟลเดอร์ของสกิล `new-workspace-lite`

1. ผลลัพธ์ทุกไฟล์อยู่ใต้ `work/{domain}/`
2. ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์หัวข้อเดียวกัน ให้เขียนลง `00-baseline/` ถ้ามีแล้ว ให้เขียนลง `01-current/`
3. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร
4. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน ห้ามสร้างโครงเองแบบอื่น

ชื่อไฟล์รายงานต้องตรงตามนี้เป๊ะ

```
work/{domain}/(00-baseline|01-current)/{domain}_image-optimization_{YYYY-MM-DD}.md
```

---

## กฎ

- **ห้ามตั้งชื่อโดยไม่เปิดดูภาพจริงทีละไฟล์** และห้ามใช้ชื่อ generic เช่น image-1
- **ห้ามเขียนทับหรือลบต้นฉบับใน `uploads/`**
- **ห้ามขยายภาพให้ใหญ่กว่าต้นฉบับ** ถ้าต้นฉบับเล็กกว่าที่ขอ ให้บอกตรง ๆ
- ห้ามเดาขนาดไฟล์หรือมิติภาพ ทุกตัวเลขต้องมาจากผลรันจริง
- ถ้า Pillow ใช้ไม่ได้ หรือไฟล์เปิดไม่ได้ ให้บอกตรง ๆ แล้วแยกรายงาน ห้ามแต่งผล
- **ทำได้บางส่วนต้องส่งส่วนนั้นเสมอ** เช่น ตารางชื่อใหม่ alt text และสคริปต์ให้ผู้ใช้ไปรันเอง
  พร้อมติดป้ายว่าข้อไหน ยืนยันแล้ว ข้อไหน ต้องยืนยันเพิ่ม
  **การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์**
- **ถ้าดึงข้อมูลไม่สำเร็จให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`**
  เช่นเปิดไฟล์ไม่ได้ ห้ามสรุปว่าไม่มี EXIF สองคำนี้คนละความหมาย เขียนผิดทำให้ผู้ใช้สรุปกลับด้าน
- ถ้าบริบทไม่พอจะตั้งชื่อ ให้ถามผู้ใช้ ไม่ใช่สมมติเอง
