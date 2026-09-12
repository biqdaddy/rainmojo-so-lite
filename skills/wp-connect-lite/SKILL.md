---
name: wp-connect-lite
description: >
  ตั้งค่าและทดสอบการเชื่อมต่อ WordPress ผ่าน REST API โดยอ่าน credential จากไฟล์ .env เท่านั้น
  ใช้เมื่อผู้ใช้จะเริ่มส่งเนื้อหาขึ้นเว็บ หรือถามว่าเชื่อม WordPress ยังไง
  หรือเจอ error ตอนส่งขึ้นเว็บแล้วไม่รู้ว่าพังตรงไหน
  ต้องรันตัวนี้ให้ผ่านก่อนใช้ wp-publish-draft-lite เสมอ
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


# WP Connect

ตรวจว่าเชื่อม WordPress ได้จริงก่อน ไม่ใช่ไปพังตอนส่งบทความ

---

## กฎเรื่อง credential ที่ห้ามฝ่าฝืน

- เขียนไฟล์เสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน

> **ห้ามขอให้ผู้ใช้พิมพ์รหัสผ่านหรือ application password ลงในบทสนทนา**
> **ห้ามอ่านค่าเหล่านั้นออกมาแสดง และห้ามเขียนลงไฟล์ผลลัพธ์ใด ๆ**

ผู้ใช้ใส่ค่าเองในไฟล์ `.env` ที่รากโฟลเดอร์งาน สกิลนี้อ่านผ่าน environment variable เท่านั้น

ถ้าผู้ใช้พิมพ์ credential มาในแชท **ให้เตือนทันทีว่าควรเปลี่ยนรหัสนั้นใหม่** เพราะถือว่ารั่วแล้ว

---

## ขั้นที่ 1 ตรวจว่ามีไฟล์ .env หรือยัง

มองหา `.env` ที่รากโฟลเดอร์งาน ถ้าไม่มี ให้สร้าง `.env.example` ให้แทน แล้วบอกผู้ใช้ให้คัดลอกเป็น `.env` แล้วเติมค่าเอง

```
WP_SITE_URL=https://example.com
WP_USERNAME=your-wp-username
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

**ห้ามสร้างไฟล์ `.env` ที่มีค่าจริงให้เอง** สร้างได้แค่ `.env.example` ที่เป็นค่าตัวอย่าง

### บอกวิธีเอา application password ให้ผู้ใช้

1. ล็อกอิน WordPress แล้วไปที่ **Users** จากนั้น **Profile**
2. เลื่อนลงไปหาหัวข้อ **Application Passwords**
3. ตั้งชื่อว่า `rainmojo-so-lite` แล้วกด **Add New Application Password**
4. คัดลอกรหัสที่ขึ้นมา **มันจะแสดงครั้งเดียว** แล้ววางลง `.env`

**อย่าใช้รหัสผ่านที่ใช้ล็อกอินปกติ** ต้องเป็น application password เท่านั้น
เพราะถอนได้ทีละอันโดยไม่กระทบการล็อกอิน

### เตือนเรื่อง .gitignore

ถ้าโฟลเดอร์งานอยู่ใน git ให้ตรวจว่า `.env` อยู่ใน `.gitignore` แล้ว
ถ้ายังไม่มีให้เพิ่มให้ และบอกผู้ใช้

---

## ขั้นที่ 2 ทดสอบการเชื่อมต่อ

ยิงคำสั่งเดียวที่เป็นการ **อ่านอย่างเดียว** ไม่เขียนอะไรทั้งสิ้น

```bash
curl -sS -o /dev/null -w "%{http_code}\n" \
  -u "$WP_USERNAME:$WP_APP_PASSWORD" \
  "$WP_SITE_URL/wp-json/wp/v2/users/me?context=edit"
```

### ถ้าใช้คำสั่งพวกนี้ไม่ได้

**บาง host ไม่มีเครื่องมือรันคำสั่งให้** เช่น Cowork, Claude Desktop และ GPT desktop
ถ้าเป็นแบบนั้น ให้ทำแบบนี้แทน แล้วงานจะยังเดินต่อได้

1. บอกผู้ใช้ว่า **ขอให้ช่วยเปิดลิงก์นี้ในเบราว์เซอร์ที่ล็อกอิน WordPress อยู่**
   คือ `{WP_SITE_URL}/wp-json/wp/v2/users/me?context=edit` แล้วคัดลอกสิ่งที่เห็นมาวางในแชท
   **ห้ามให้ผู้ใช้พิมพ์ username หรือ application password มาในแชทเด็ดขาด** ขอแค่ผลลัพธ์ที่หน้าจอแสดง
2. ถ้าผู้ใช้ทำให้ได้ ให้อ่านผลจากสิ่งที่เขาวางมา ตามตารางอ่านผลลัพธ์ข้างล่างทุกอย่าง
   เห็นชื่อผู้ใช้และ `capabilities` แปลว่า REST API เปิดอยู่ เห็นข้อความ error แปลว่ายังติดตรงนั้น
   รายการหมวดหมู่ในขั้นที่ 3 ก็ขอด้วยวิธีเดียวกัน คือเปิด `{WP_SITE_URL}/wp-json/wp/v2/categories`
3. ถ้าผู้ใช้ไม่สะดวก **ยังต้องส่งงานส่วนที่ทำได้** คือเขียนไฟล์ในขั้นที่ 4 ตามปกติ
   แล้ว**เขียนกำกับทุกช่องที่ยังไม่ได้พิสูจน์ว่า `ตรวจไม่ได้`**
   ห้ามเขียนว่า `ไม่มี` หรือ `ไม่ผ่าน` เพราะสองคำนี้คนละความหมายกับตรวจไม่ได้
   และการเขียนผิดจะทำให้ผู้ใช้เข้าใจกลับด้าน

**บน Windows** ถ้ารันแล้วขึ้นว่าไม่รู้จักคำสั่ง ให้ลองใน Git Bash หรือ WSL
ถ้าไม่มีทั้งสองอย่าง ให้ใช้วิธีเปิดลิงก์ในข้อ 1

### อ่านผลลัพธ์

| รหัสที่ได้ | แปลว่า | ทำอะไรต่อ |
|---|---|---|
| **200** | เชื่อมได้ ผ่าน | ไปขั้นที่ 3 |
| **401** | ชื่อผู้ใช้หรือ application password ผิด | ให้สร้าง application password ใหม่ ระวังเรื่องช่องว่างตอนคัดลอก |
| **403** | ล็อกอินได้แต่ไม่มีสิทธิ์ หรือถูกไฟร์วอลล์กั้น | ดูหัวข้อ 403 ข้างล่าง |
| **404** | REST API ถูกปิด หรือ URL ผิด | ตรวจว่า `WP_SITE_URL` ไม่มี `/` ปิดท้าย และไม่ใช่ URL หน้า wp-admin |
| **301 หรือ 302** | URL ผิดโปรโตคอลหรือมี www ไม่ตรง | ใช้ URL ที่เบราว์เซอร์แสดงจริงหลัง redirect |
| **ต่อไม่ติดเลย** | เว็บล่ม หรือ DNS ไม่ตอบ | ลองเปิดเว็บในเบราว์เซอร์ก่อน |

### ถ้าได้ 403

**อย่าพยายามหลบไฟร์วอลล์** ให้รายงานตรง ๆ ว่าถูกกั้น แล้วเสนอทางเลือกให้ผู้ใช้

| สาเหตุที่พบบ่อย | ให้ผู้ใช้ทำ |
|---|---|
| ปลั๊กอินความปลอดภัยปิด REST API ไว้ | เปิดสิทธิ์ให้ REST API ในตั้งค่าปลั๊กอินนั้น |
| โฮสต์หรือ CDN กั้น request ที่มี auth header | แจ้งผู้ดูแลเว็บให้เปิดให้ |
| บัญชีไม่ใช่ Editor หรือ Administrator | ต้องมีสิทธิ์อย่างน้อยระดับ Author ถึงจะสร้าง draft ได้ |

**ถ้าแก้ไม่ได้ ให้ใช้ทางสำรอง** คือให้สกิล `content-draft-lite` สร้างไฟล์ไว้
แล้วผู้ใช้คัดลอกวางเข้าหลังบ้าน WordPress เอง ซึ่งได้ผลเหมือนกัน แค่ช้ากว่า

---

## ขั้นที่ 3 ตรวจสิทธิ์และสภาพเว็บ

ยิงอีก 2 คำสั่ง อ่านอย่างเดียวทั้งคู่

```bash
curl -sS -u "$WP_USERNAME:$WP_APP_PASSWORD" \
  "$WP_SITE_URL/wp-json/wp/v2/users/me?context=edit" | head -c 400
```

ดูว่า `capabilities` มี `publish_posts` หรือ `edit_posts` ไหม

```bash
curl -sS "$WP_SITE_URL/wp-json/wp/v2/categories?per_page=100" | head -c 800
```

เก็บรายการหมวดหมู่ไว้ใช้ตอนส่งบทความ

---

## ขั้นที่ 4 เขียนผลลงไฟล์

สร้าง `work/{domain}/wp-connection.md`

```markdown
# สถานะการเชื่อมต่อ WordPress

| | |
|---|---|
| ตรวจเมื่อ | {วันที่} |
| เว็บ | {WP_SITE_URL} |
| ผลการเชื่อมต่อ | ผ่าน หรือ ไม่ผ่าน พร้อมรหัสที่ได้ |
| สิทธิ์ที่มี | |
| หมวดหมู่ที่มี | |
| ข้อจำกัดที่เจอ | |
```

**ห้ามเขียน username หรือ password ลงไฟล์นี้เด็ดขาด** เขียนได้แค่ URL กับผลลัพธ์

**ต่อให้ทดสอบไม่สำเร็จก็ต้องเขียนไฟล์นี้** ช่องไหนยังไม่รู้ให้เขียนว่า `ตรวจไม่ได้`
พร้อมบอกว่าขาดอะไรและต้องทำอะไรถึงจะตรวจต่อได้ **ห้ามจบงานด้วยการไม่ส่งอะไรเลย**
การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์

---

## สิ่งที่สกิลนี้ไม่ทำ

- **ไม่เขียนอะไรลงเว็บ** ทุกคำสั่งเป็น GET อย่างเดียว
- **ไม่หลบไฟร์วอลล์** ถ้าโดนกั้นจะรายงานตรง ๆ แล้วเสนอทางคัดลอกวางแทน
- **ไม่เก็บ credential ไว้ที่ไหน** อ่านจาก environment ตอนรันเท่านั้น
- ไม่แก้ตั้งค่าใด ๆ ใน WordPress

## กฎ

- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`** สองคำนี้คนละความหมาย ถ้าเขียนผิดผู้ใช้จะสรุปกลับด้าน
