---
name: seo-website-overview-lite
description: >
  ตรวจว่าเว็บติดตั้งเครื่องมือพื้นฐานครบไหม เช่น GA4 Google Search Console
  Google Business Profile Bing Webmaster และมีไฟล์พื้นฐานอย่าง robots.txt sitemap.xml หรือยัง
  ใช้เป็นสกิลแรก ๆ เพื่อรู้ว่าเว็บนี้มีของอะไรอยู่แล้วบ้าง ก่อนจะไปวัดอะไรที่ลึกกว่านี้
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


# Website Overview

ตรวจว่าเว็บนี้ **ติดตั้ง**อะไรไว้แล้วบ้าง

**ตรวจจากสิ่งที่เห็นได้จากภายนอกเท่านั้น** ไม่ได้ตรวจว่าล็อกอินเข้าได้ไหม
ผลที่ได้จึงบอกว่า **ตรวจพบ** หรือ **ตรวจไม่พบ** ไม่ใช่ **มี** หรือ **ไม่มี**

ความต่างนี้สำคัญ เพราะหลายอย่างติดตั้งผ่าน Google Tag Manager หรือฝั่งเซิร์ฟเวอร์
แล้วมองไม่เห็นจากหน้าเว็บ **การเขียนว่าไม่มีทั้งที่แค่ตรวจไม่พบ คือการให้ข้อมูลผิด**

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
```

**JSON-LD ส่วนใหญ่เขียนหลายบรรทัด** คำสั่ง `sed` บรรทัดเดียวข้างบนจับได้เฉพาะแบบบรรทัดเดียว
ถ้ารันแล้วไม่ได้อะไรกลับมา **ห้ามสรุปว่าหน้านั้นไม่มี schema** ให้เปิดไฟล์ที่ดาวน์โหลดมา
ด้วย Read หรือใช้ Grep หาคำว่า `application/ld+json` ในไฟล์นั้นอีกรอบก่อนเสมอ

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

## ตรวจอะไรบ้าง

### กลุ่มไฟล์พื้นฐาน

| ไฟล์ | ดูที่ | ถ้าไม่มีแปลว่า |
|---|---|---|
| `robots.txt` | `/robots.txt` | ไม่ได้คุมว่าใครเข้าได้ ค่าเริ่มต้นคือเข้าได้หมด |
| `sitemap.xml` | `/sitemap.xml` หรือที่ระบุใน robots.txt | เครื่องมือค้นหาต้องเดาโครงเว็บเอง |
| `llms.txt` | `/llms.txt` | ยังไม่มี ซึ่งปกติ เพราะยังเป็นข้อตกลงของชุมชน ไม่ใช่มาตรฐาน |
| favicon | `/favicon.ico` | เรื่องเล็กแต่กระทบความน่าเชื่อถือ |

### กลุ่มเครื่องมือวัดผล ดูจากซอร์สหน้าแรก

| เครื่องมือ | สัญญาณที่มองหา |
|---|---|
| Google Analytics 4 | `gtag(` หรือรหัสที่ขึ้นต้นด้วย `G-` |
| Google Tag Manager | `googletagmanager.com/gtm.js` หรือรหัสที่ขึ้นต้นด้วย `GTM-` |
| Google Search Console | meta `google-site-verification` **ถ้าไม่มีอาจยืนยันด้วยวิธีอื่น ไม่ได้แปลว่าไม่ได้เชื่อม** |
| Bing Webmaster | meta `msvalidate.01` |
| Facebook Pixel | `connect.facebook.net` |

**ถ้าเจอ Google Tag Manager ให้เขียนกำกับว่า** เครื่องมืออื่นอาจถูกติดตั้งผ่าน GTM
ซึ่งตรวจจากหน้าเว็บไม่เห็น ต้องเข้าไปดูในบัญชี GTM เอง

### กลุ่มตัวตนของธุรกิจ

| เรื่อง | มองหาอะไร |
|---|---|
| Google Business Profile | สกิลนี้ค้นเว็บเองไม่ได้ ให้ถามผู้ใช้ว่าเคยตั้ง Google Business Profile ไหม หรือให้ผู้ใช้ค้นชื่อแบรนด์บน Google Maps แล้วบอกผล บันทึกเป็น ผู้ใช้ยืนยันว่ามี หรือ ผู้ใช้ยืนยันว่าไม่มี หรือ ยังไม่ทราบ |
| ชื่อ ที่อยู่ เบอร์โทร | อยู่บนเว็บไหม และตรงกันทุกหน้าไหม |
| ลิงก์โซเชียล | มีและกดเข้าได้จริงไหม |
| Schema Organization | มี JSON-LD ประเภท Organization หรือ LocalBusiness ไหม |

**ชื่อ ที่อยู่ เบอร์โทร ที่ไม่ตรงกันคือปัญหาที่คนมองข้ามบ่อยที่สุด**
เพราะมันทำให้ AI ไม่แน่ใจว่าเป็นธุรกิจเดียวกันหรือคนละที่
เจอบ่อยมากเวลาเบอร์บนหน้าติดต่อกับเบอร์บนท้ายเว็บไม่ตรงกัน

---

## ติดเครื่องวัดก่อน แล้วค่อยวางกลยุทธ์

สกิลนี้เป็นก้าวแรกของงาน ผลที่ได้จึงกำหนดด้วยว่า **อะไรรันต่อได้ และอะไรยังรันไม่ได้**
ลำดับนี้ **ห้ามลัดคิว**

1. **หาก่อนว่าเคยทำ SEO อะไรไว้บ้าง** และมีสัญญาเครื่องมือหรือสัญญากับผู้ให้บริการเดิม
   ที่ล็อกชุดเครื่องมือไว้หรือเปล่า **ชุดเครื่องมือที่ถูกล็อกไว้เปลี่ยนข้อเสนอทุกข้อที่จะตามมา**
   จึงต้องรู้ให้ได้ก่อนเสนออะไรทั้งสิ้น
2. **ติดตั้งหรือซ่อมเครื่องมือวัดผลให้ทำงาน แล้วเริ่มสะสมประวัติ**
   **ประวัติเดินหน้าอย่างเดียว ไม่มีอะไรย้อนไปเก็บสัปดาห์ที่ไม่ได้วัดกลับคืนมาได้**
3. **แก้ปัญหาเทคนิคก้อนใหญ่ให้เสร็จก่อน**
4. **ถึงตรงนี้ค่อยทำงานที่ต้องใช้ข้อมูล** คือวิเคราะห์คู่แข่ง หาคำค้น และวางแผนตามฤดูกาล
   ทั้งสามอย่างต้องใช้ข้อมูลที่ตอนอยู่ขั้นที่ 1 ยังไม่มี **ทำเร็วเกินไปจะได้ผลลัพธ์
   ที่ฟันธงหนักแน่นบนพื้นที่ว่างเปล่า**

**เขียนด่านนี้ลงในรายงานด้วย** ถ้าเพิ่งติดตั้งหรือเพิ่งซ่อมเครื่องมือวัดผลไป
ให้ระบุงานขั้นที่ 4 ว่า **ติดด่าน** พร้อมเหตุผลและวันที่เริ่มวัดจริง
ห้ามรันงานขั้นที่ 4 ไปก่อน และห้ามเงียบไม่พูดถึงมันเลย

**กฎเรื่องความคาดหวัง** การแก้เทคนิคมักเห็นผลไว แต่มัน **แค่คืนเว็บกลับสู่ความสามารถพื้นฐาน
ที่ควรจะมีอยู่แล้ว** ไม่ใช่ผลของกลยุทธ์ ให้รายงานว่าเป็นการกู้ฐานกลับคืน
**ห้ามรายงานผลไวจากการแก้เทคนิคว่าเป็นผลของกลยุทธ์**
เพราะผู้ใช้จะคาดหวังให้กราฟขึ้นแบบนั้นต่อไปเรื่อย ๆ แล้วงานกลยุทธ์ทุกชิ้นหลังจากนั้น
จะถูกตัดสินเทียบกับความเร็วที่ไม่มีทางเกิดซ้ำ

**สกิลนี้กำหนดลำดับและด่าน ไม่ได้ทำงานเหล่านั้นเอง** ตัวงานอยู่ที่สกิลอื่น
การแก้เทคนิคอยู่ที่ `technical-audit-lite` วิเคราะห์คู่แข่งอยู่ที่ `seo-competitor-lite`
หาคำค้นอยู่ที่ `seo-keyword-research-lite` ส่วนการวางแผนตามฤดูกาล **รุ่น Lite ไม่มีสกิลเฉพาะ**
ให้ทำรวมไปในแผนเนื้อหาที่ `seo-content-strategy-lite`

---

## ส่งออก

ไฟล์ `{domain}_overview_{YYYY-MM-DD}.md` วางตามกฎนี้

ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์ `overview` ให้เขียนลง `00-baseline/`
ถ้ามีแล้ว ให้เขียนลง `work/{domain}/01-current/` เพื่อให้สกิล `compare-lite` เทียบสองรอบได้
เขียนเสร็จ เพิ่มบรรทัดลง `work/{domain}/CHANGELOG.md` เรียงหัวข้อตามนี้

1. **ไฟล์พื้นฐาน** ตารางคอลัมน์ ไฟล์ / ผล / หมายเหตุ
2. **เครื่องมือวัดผล** ตารางคอลัมน์ เครื่องมือ / ผล / ที่มาของการตรวจ
3. **ตัวตนของธุรกิจ** ตารางคอลัมน์ เรื่อง / ผล / หมายเหตุ
4. **สิ่งที่ควรทำก่อน 3 ข้อ** เรียงตามผลกระทบ ไม่ใช่ตามความง่าย
5. **ด่านลำดับงาน** ระบุว่างานที่ต้องใช้ข้อมูล คือคู่แข่ง คำค้น และแผนตามฤดูกาล
   รันได้แล้วหรือยังติดด่านอยู่ ถ้าติดให้บอกเหตุผลและวันที่เริ่มวัดจริง
6. **ข้อจำกัดของการตรวจนี้** ระบุว่าตรวจจากภายนอกเท่านั้น สิ่งที่ติดตั้งผ่าน
   Google Tag Manager หรือฝั่งเซิร์ฟเวอร์อาจตรวจไม่พบ และผลว่าตรวจไม่พบไม่ได้แปลว่าไม่มี

**หัวข้อที่ 5 และ 6 ต้องมีทุกครั้ง ไม่ใช่ทางเลือก**

---

## กฎ

- **เขียนว่าตรวจพบหรือตรวจไม่พบ ห้ามเขียนว่ามีหรือไม่มี**
- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`**
  และห้ามใช้ `ตรวจไม่พบ` แทนด้วย เพราะสามคำนี้คนละความหมาย
  `ตรวจไม่พบ` คือดึงซอร์สมาดูแล้วแต่ไม่เจอสัญญาณ ส่วน `ตรวจไม่ได้` คือดึงมาดูไม่ได้ตั้งแต่แรก
  เขียนผิดแล้วผู้ใช้จะสรุปกลับด้าน
- ห้ามเดารหัส GA4 หรือรหัสยืนยันใด ๆ ถ้าอ่านไม่ได้ให้เขียนว่าอ่านไม่ได้
- ห้ามแนะนำให้ติดตั้งทุกอย่างพร้อมกัน ให้เรียง 3 ข้อที่กระทบมากที่สุดพอ
- **ห้ามแนะนำให้เริ่มงานที่ต้องใช้ข้อมูลก่อนที่เครื่องมือวัดผลจะทำงานและเริ่มสะสมประวัติ**
  ถ้าเพิ่งติดตั้งหรือเพิ่งซ่อม ให้เขียนว่างานนั้นติดด่าน พร้อมวันที่เริ่มวัดจริง
- **ห้ามรายงานผลไวจากการแก้เทคนิคว่าเป็นผลของกลยุทธ์** การแก้เทคนิคคืนเว็บสู่ความสามารถพื้นฐาน
  ที่ควรมีอยู่แล้ว ให้เขียนว่าเป็นการกู้ฐานกลับคืน
- ถ้าเว็บเข้าไม่ได้หรือ redirect วนให้บอกตรง ๆ แล้วหยุด
- **ตรวจได้กี่หัวข้อให้ส่งเท่านั้น ห้ามกลั้นทั้งงานเพราะบางหัวข้อดึงข้อมูลไม่ได้**
  ตารางที่ทุกช่องเขียนว่าตรวจไม่ได้ ถือว่าใช้ไม่ได้ ต้องแยกให้ชัดว่าช่องไหนยืนยันแล้ว
  ช่องไหนต้องยืนยันเพิ่ม และต้องยืนยันด้วยวิธีไหน
  **การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์**
