---
name: aiso-platform-lite
description: >
  Platform-specific AI search optimization for all ten documented AI answer platforms:
  ChatGPT, Perplexity, Claude, Google AI Overviews and Gemini, DeepSeek, Grok, Qwen, Meta AI,
  Microsoft Copilot and Apple Intelligence (11 cards), bound to the shared AI platform
  registry. Reports a readiness checklist per platform (ผ่าน, บางส่วน, ยังไม่มี, ตรวจไม่ได้),
  never a numeric score; platforms without a documented crawler are reported as could not
  verify. (Lite edition for workshop use.)
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


# aiso platform-optimizer

ตรวจความพร้อม 11 การ์ดของ 10 แพลตฟอร์มคำตอบ AI จากทะเบียนเดียวกับ `aiso-crawlers-lite`
ทุกการ์ดเป็นเช็กลิสต์ ไม่มีคะแนน ไม่มีเปอร์เซ็นต์ ไม่มีระดับตัวเลข

## ขั้นที่ 0 ดึง HTML ดิบมาเก็บไว้ก่อน

**ต้องทำก่อนขั้นอื่นทั้งหมด** เพราะ WebFetch คืนเนื้อหาที่แปลงเป็นข้อความแล้ว
แท็กใน `<head>` อย่าง title, meta description, canonical, meta robots และบล็อก JSON-LD ถูกตัดทิ้ง
ข้อในเช็กลิสต์ที่พึ่งของพวกนี้ คือ วันที่เผยแพร่ ชื่อผู้เขียน และ structured data
ถ้ากาว่า ยังไม่มี เพราะมองไม่เห็นในผล WebFetch นั่นคือผลลบลวง ทั้งที่ของมีอยู่จริง

```bash
mkdir -p work/{domain}/uploads
curl -sSL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120" \
  -m 25 "https://{domain}/" -o work/{domain}/uploads/home.html
```

ทำแบบเดียวกันกับทุกหน้าที่จะประเมิน ตั้งชื่อไฟล์ให้รู้ว่าเป็นหน้าไหน

**แล้วค่อยใช้ Grep กับไฟล์ที่ดาวน์โหลดมา** ไม่ใช่กับผล WebFetch
เช่น Grep `application/ld\+json` เพื่อหา structured data
Grep `<h2` และ `<h3` เพื่อดูโครงหัวข้อและหัวข้อที่เป็นคำถาม
Grep `<table` และ `<ol` เพื่อดูตารางกับลำดับขั้นตอน

### ถ้าใช้คำสั่งพวกนี้ไม่ได้

**บาง host ไม่มีเครื่องมือรันคำสั่งให้** เช่น Cowork, Claude Desktop และ GPT desktop
ถ้าเป็นแบบนั้น ให้ทำแบบนี้แทน แล้วงานจะยังเดินต่อได้

1. บอกผู้ใช้ว่า **ขอให้ช่วยเปิดหน้าเว็บแล้วคัดลอกซอร์สมาให้**
   วิธีคือเปิดหน้านั้นในเบราว์เซอร์ กด `Ctrl+U` หรือ `Cmd+Option+U` เพื่อดู source
   แล้วเลือกทั้งหมด คัดลอก มาวางในแชท
2. ถ้าผู้ใช้ทำให้ได้ ให้ทำงานต่อจากซอร์สที่ได้มา ตามขั้นตอนเดิมทุกอย่าง
3. ถ้าผู้ใช้ไม่สะดวก ให้ใช้ WebFetch เท่าที่ได้ แล้ว**เขียนกำกับทุกข้อที่กระทบว่า `ตรวจไม่ได้`**
   ห้ามเขียนว่า `ยังไม่มี` เพราะสองคำนี้คนละความหมาย และการเขียนผิดจะทำให้ผู้ใช้เข้าใจกลับด้าน

**บน Windows** ถ้ารันแล้วขึ้นว่าไม่รู้จักคำสั่ง ให้ลองใน Git Bash หรือ WSL
ถ้าไม่มีทั้งสองอย่าง ให้ใช้วิธีคัดลอกซอร์สในข้อ 1

## ขั้นที่ 0.5 ข้อที่ต้องขอให้ผู้ใช้ช่วย

เช็กลิสต์บางข้ออยู่นอกเว็บของเรา และสกิลนี้ไม่มีเครื่องมือค้นหาให้ใช้
ได้แก่ อันดับบนหน้าแรกของ Google, การเก็บหน้าของ Bing, การถูกพูดถึงบน Reddit
และการมีลิงก์จากเว็บที่น่าเชื่อถือ

ทำแบบนี้ ขอให้ผู้ใช้ค้นเองแล้ววางผลมาในแชท เช่น เปิด Bing แล้วค้น `site:{domain}`
หรือเปิด Search Console ดูอันดับของหน้านั้น
ส่วน Wikipedia และ Wikidata ให้ใช้ WebFetch ยิงที่ API ของสองเว็บนั้นโดยตรง เชื่อถือได้กว่าการค้น
ข้อไหนที่ไม่ได้ผลกลับมา ให้ลงว่า **ตรวจไม่ได้** พร้อมบอกว่าต้องใช้อะไรถึงจะตรวจได้
**ห้ามลงว่า ยังไม่มี** และห้ามหยุดงานเพราะข้อพวกนี้ ให้ทำข้อที่เหลือต่อจนจบ

## ขั้นที่ 0.7 ประตูคัดคำค้น ต้องผ่านก่อนถึงจะเริ่มกาเช็กลิสต์

**ห้ามกาเช็กลิสต์ให้หน้าไหนก็ตาม จนกว่าชุดคำค้นของลูกค้าจะผ่านประตูนี้ก่อน**
ประตูนี้คัดที่ตัวคำค้น ไม่ได้ให้คะแนนตัวหน้า

### ด่านแรก คัดตามโหมดของการค้น

คำค้นที่ **ผู้ใช้รู้อยู่แล้วว่าจะไปที่ไหน** และคำค้นที่ **อยากได้ข้อเท็จจริงเดียวสั้น ๆ**
ถูกตอบด้วยผลค้นหาแบบเดิมอยู่แล้ว **ไม่ใช่เป้าหมายของงาน AI visibility**
สิ่งที่หน้าจอคำตอบแบบสนทนาถูกออกแบบมาดูดไป คือ **คำค้นที่ปกติคนต้องค้นซ้ำหลายรอบกว่าจะได้คำตอบ**

**วิธีทดสอบ ถามว่าคนจริง ๆ ต้องค้นแก้คำถามซ้ำอีกสามรอบขึ้นไปไหมกว่างานจะเสร็จ**

| เข้าข่ายเป้าหมาย | ไม่เข้าข่าย |
|---|---|
| คำค้นที่มีหลายเงื่อนไขพร้อมกัน | คำค้นที่ต้องการข้อเท็จจริงเดียว |
| คำค้นเปรียบเทียบ | คำค้นที่รู้ปลายทางอยู่แล้ว เช่น พิมพ์ชื่อแบรนด์เพื่อเข้าเว็บนั้น |
| คำค้นแนว ควรเลือกอันไหนดี | |

คำค้นที่ไม่เข้าข่าย **ให้ตัดออก แล้วบันทึกไว้ว่าส่งกลับไปทำ organic แบบเดิม** ไม่ใช่ทิ้งเงียบ ๆ

### ด่านสอง คัดตามว่าหน้าจอนั้นยอมตอบไหม

ชั้นที่สร้างคำตอบ **ไม่ตอบเลย** สำหรับหัวข้อที่ข้อมูลน่าเชื่อถือมีน้อย
**ปฏิเสธที่จะสร้างคำตอบ** สำหรับคำค้นที่ส่งสัญญาณว่าผู้ถามกำลังอยู่ในสถานการณ์เปราะบาง
และ **แปะข้อความให้ไปตรวจสอบที่อื่น** กับผลลัพธ์ของหัวข้อ YMYL

แบ่งคำค้นที่เหลือเป็นสามถัง

| ถัง | คือคำค้นแบบไหน | ทำอะไรต่อ |
|---|---|---|
| **ถูกปิดการสร้างคำตอบ** | ข้อมูลน่าเชื่อถือมีน้อย หรือผู้ถามอยู่ในสถานการณ์เปราะบาง | **โอกาสได้คำตอบจาก AI เป็นศูนย์** ห้ามกาเช็กลิสต์ให้ ให้เอาแรงไปลงที่ organic แบบเดิม แล้วเขียนบอกเหตุผลในรายงาน |
| **มีข้อความให้ไปตรวจสอบที่อื่นแปะมาด้วย** | คำค้น YMYL ที่ยังตอบอยู่ | **กาเช็กลิสต์** โดยเน้นสองเรื่องเป็นหลัก คือความสอดคล้องกับสิ่งที่แหล่งอื่นพูดตรงกัน และความน่าเชื่อถือที่หยิบไปอ้างได้ |
| **ปกติ** | ทุกอย่างที่เหลือ | **กาเช็กลิสต์เต็มทั้งชุด** |

**กาเช็กลิสต์ให้เฉพาะสองถังหลังเท่านั้น**

การตัดสินว่าหัวข้อไหนเป็น YMYL เป็นงานของ `seo-content-audit-lite` ให้อ้างผลจากที่นั่น
ไม่มีผลจากที่นั่น ให้บันทึกว่าเป็นการจัดถังเบื้องต้นที่รอยืนยัน ห้ามพิมพ์เป็นข้อเท็จจริง

### ลำดับการทำและสิ่งที่รายงานต้องมี

1. รวบรวมชุดคำค้นของลูกค้าให้ครบ **ก่อนเปิดเช็กลิสต์ของแพลตฟอร์มไหนก็ตาม**
2. คัดด่านแรกก่อน ตัดคำค้นที่ไม่ใช่เป้าหมาย แล้วจดไว้ทีละคำว่าส่งกลับไป organic
3. เอาที่เหลือมาแบ่งสามถังตามด่านสอง
4. กาเช็กลิสต์ให้เฉพาะถัง มีข้อความให้ไปตรวจสอบที่อื่น และถัง ปกติ
5. **รายงานต้องแสดงจำนวนคำค้นในแต่ละถัง และรายชื่อคำค้นที่ถูกส่งกลับไป organic**
   เพื่อให้ลูกค้าเห็นว่าอะไรถูกตัดออกและถูกตัดเพราะอะไร

**ถ้าไม่มีประตูนี้ สกิลจะกาเช็กลิสต์ให้ทุกหน้าเท่ากันหมด** โดยไม่สนว่าคำค้นนั้นมีโอกาสเกิดคำตอบจาก AI หรือเปล่า
แล้วส่งแผนแก้ไขยาวเหยียดให้ลูกค้าสำหรับชุดคำค้นที่หน้าจอนั้นถูกออกแบบมาให้ไม่ตอบตั้งแต่แรก

**ยังไม่มีชุดคำค้นจากลูกค้า** ให้ขอ ถ้าขอแล้วยังไม่ได้ ให้ทำงานต่อกับคำค้นที่เดาจากเนื้อหาหน้าเว็บได้
แล้ว **เขียนกำกับว่าการจัดถังนี้ยังไม่ได้ยืนยันกับคำค้นจริง** ห้ามหยุดงานทั้งหมดเพราะข้อนี้

## 11 การ์ด 10 แพลตฟอร์ม ผูกกับทะเบียน

| การ์ด | ผู้ผลิต | บอทที่ตัดสินการมองเห็น | หลักฐานชื่อบอท |
|---|---|---|---|
| ChatGPT | OpenAI | OAI-SearchBot, ChatGPT-User | ผู้ผลิตประกาศ |
| Perplexity | Perplexity | PerplexityBot, Perplexity-User | ผู้ผลิตประกาศ |
| Claude | Anthropic | Claude-SearchBot, Claude-User | ผู้ผลิตประกาศ |
| Google AI Overviews | Google | Googlebot | ผู้ผลิตประกาศ |
| Gemini | Google | Googlebot | ผู้ผลิตประกาศ |
| DeepSeek | DeepSeek | ไม่ประกาศ | ไม่มี ให้ลง ตรวจไม่ได้ |
| Grok | xAI | ไม่ประกาศ | ไม่มี ให้ลง ตรวจไม่ได้ |
| Qwen | Alibaba Cloud | ชุมชนสังเกตเห็นเท่านั้น | สังเกต ให้ลง ตรวจไม่ได้ |
| Meta AI | Meta | meta-webindexer, meta-externalfetcher | ผู้ผลิตประกาศ |
| Microsoft Copilot | Microsoft | bingbot | ผู้ผลิตประกาศ |
| Apple Intelligence | Apple | Applebot | ผู้ผลิตประกาศ |

- ทะเบียนอยู่ที่ `{PLUGIN_ROOT}/skills/rainmojo-so-lite/reference/frameworks/ai-platform-registry.json`
  พิมพ์รายการด้วย `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/ai_platforms.py --platforms`
  รายการเช็กลิสต์ต่อการ์ดอยู่ในคีย์ `platforms[].checklist` และใน `agent.json` ของสกิลนี้
- การ์ดที่ไม่มีชื่อบอทประกาศ ข้อ การเข้าถึงของบอท ให้ลงว่า **ตรวจไม่ได้** และไม่นับรวมในจำนวนข้อ
  ห้ามเดา ห้ามลงว่าไม่ผ่าน
- ข้อเท็จจริงนอกเว็บ (Wikidata, Knowledge Panel, Reddit, YouTube, บัญชี X, การมีอยู่บนแหล่งนักพัฒนา)
  เอามาจาก `aiso-brand-mentions-lite` เท่านั้น ข้อที่ยังไม่มีผลจากสกิลนั้น ลงว่า ตรวจไม่ได้
- **llms.txt เป็นข้อสุขอนามัย** ทุกการ์ด การวัดปี 2025 ถึง 2026 ไม่พบแพลตฟอร์มหลักรายใดอ่านไฟล์นี้
  ยังคงสร้างผ่าน `aiso-llmstxt-lite` แต่ห้ามเขียนว่าเป็นเหตุให้การ์ดผ่านหรือไม่ผ่าน
- รายงานต่อการ์ด คือจำนวนข้อในแต่ละสถานะ ผ่าน บางส่วน ยังไม่มี ตรวจไม่ได้ พร้อมรายการข้อที่ต้องแก้
  **ไม่มีการรวมเป็นคะแนน ไม่มีการเฉลี่ยข้ามการ์ด**
- รุ่นนี้ไม่มีสคริปต์ให้คะแนน (`platform_readiness.py` ของรุ่นเต็มไม่อยู่ในชุดนี้) ทุกข้อกาด้วยมือ
  จากซอร์สดิบที่ดึงมาในขั้นที่ 0 และหลักฐานจากผู้ใช้

เมื่อกาครบ ให้เขียนไฟล์ JSON สำหรับการ์ด Tier 1 ไว้ข้างรายงาน ชื่อ `{domain}_platform-checklist_{YYYY-MM-DD}.json`

```json
{"platforms": [{"id": "chatgpt", "label": "ChatGPT", "status": "warning", "crawler_access": "allowed", "note": "..."}],
 "dimensions": [{"key": "platform_checklist", "label": "Platform checklist", "passed": 0, "total": 0}]}
```

`status` ใช้ `ok` เมื่อทุกข้อที่ตรวจได้ผ่าน, `critical` เมื่อบอทค้นหาถูกบล็อก, `info` เมื่อตรวจไม่ได้เป็นส่วนใหญ่, ที่เหลือ `warning`
`build_summary.py --checklist` อ่านไฟล์นี้ตรง ๆ ไม่ต้องพิมพ์ตัวเลขซ้ำ

## ขั้นตอนหลัก

Read and execute the agent workflow from [agent.json](agent.json).
Follow all phases and steps sequentially.

## กฎ


- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`** สองคำนี้คนละความหมาย ถ้าเขียนผิดผู้ใช้จะสรุปกลับด้าน
- **ดึงข้อมูลไม่สำเร็จให้เขียน `ตรวจไม่ได้` ห้ามเขียน `ยังไม่มี` หรือ `ไม่มี`**
  ยังไม่มี แปลว่าไปดูมาแล้วและยืนยันว่าไม่มีจริง ตรวจไม่ได้ แปลว่ายังไม่ได้เห็น
  เขียนผิดคำเดียวผู้ใช้จะสรุปกลับด้าน แล้วไปแก้ของที่ไม่ได้เสีย
- **ตรวจได้กี่ข้อส่งกี่ข้อ** ห้ามจบด้วยเช็กลิสต์ที่ทุกช่องเขียนว่าตรวจไม่ได้
  และห้ามปฏิเสธทั้งงานเพราะขาดข้อมูลของแพลตฟอร์มใดแพลตฟอร์มหนึ่ง
  แพลตฟอร์มไหนตรวจได้ก็ส่งของแพลตฟอร์มนั้นไปก่อน
- ในรายงานต้องติดป้ายทุกข้อว่า **ยืนยันแล้ว** คือเห็นหลักฐานจริง
  หรือ **ต้องยืนยันเพิ่ม** คือยังไม่เห็น พร้อมบอกว่าขาดอะไรถึงจะยืนยันได้
- **การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์** ส่งเท่าที่ตรวจได้พร้อมป้ายกำกับเสมอ
- **ห้ามให้คะแนนรวม ห้ามคิดเปอร์เซ็นต์ ห้ามตั้งเกณฑ์ตัวเลขขึ้นเอง**
  ใช้เช็กลิสต์ที่กาเป็น ผ่าน บางส่วน ยังไม่มี ตรวจไม่ได้ เท่านั้น ทั้ง 11 การ์ด
- **การ์ดที่ไม่มีชื่อบอทประกาศ ห้ามเดาการเข้าถึง** ลงว่าตรวจไม่ได้และไม่นับรวม
- **ห้ามกาเช็กลิสต์ก่อนผ่านประตูคัดคำค้นในขั้นที่ 0.7**
  และห้ามกาเช็กลิสต์ให้คำค้นในถังที่ถูกปิดการสร้างคำตอบ
- **รายงานต้องแสดงผลของประตูเสมอ** คือจำนวนคำค้นต่อถัง และรายชื่อคำค้นที่ส่งกลับไป organic แบบเดิม
  ตัดคำค้นออกโดยไม่บอกว่าตัดอะไรไปบ้าง คือรายงานที่ใช้ไม่ได้

## การ์ด Tier 1 ของสกิลนี้

จบงานทุกครั้งด้วยการ์ดสรุปตามชั้นแสดงผล (`so-present-lite`): โหมด `audit` `platforms` 11 แถว (id, label, status, crawler_access, note) และ `dimensions` หนึ่งแถว platform_checklist = จำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจได้ ทั้งสองมาจากไฟล์ `{domain}_platform-checklist_{YYYY-MM-DD}.json` ผ่าน `build_summary.py --checklist`, `key_risk` คือการ์ดที่บอทค้นหาถูกบล็อกหรือขาดมากที่สุด, `actions` คือ 4 ข้อแรกของแผน
ทุกค่าบนการ์ดคัดลอกจากไฟล์ผลลัพธ์ที่เพิ่งเขียน ห้ามประเมินเพิ่ม ข้อที่ตรวจไม่ได้ให้ขึ้นว่า ตรวจสอบไม่ได้
รุ่น Lite ไม่มีคะแนน จึงไม่ใส่บล็อก `score` ค่าใน `dimensions` คือจำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจ
เรนเดอร์ด้วย `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --summary <summary.json> --target auto --host {host}`
แล้วปิดด้วยบรรทัดส่งต่อไปยังไฟล์ผลลัพธ์ฉบับเต็ม ซึ่งต้องครบและไม่ถูกย่อ

## Output
### Naming convention

ไฟล์ที่สร้างต้องตั้งชื่อตาม pattern:

```
{domain}_platform-analysis_{YYYY-MM-DD}.{ext}
```

ตัวอย่าง: `example-com_platform-analysis_2026-03-28.md`

## การวางไฟล์ผลลัพธ์

สกิลนี้อยู่ในชุดที่ใช้โครงโฟลเดอร์ของสกิล `new-workspace-lite`

1. ผลลัพธ์ทุกไฟล์อยู่ใต้ `work/{domain}/`
2. ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์หัวข้อเดียวกัน ให้เขียนลง `00-baseline/` ถ้ามีแล้ว ให้เขียนลง `01-current/`
3. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร
4. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน ห้ามสร้างโครงเองแบบอื่น

## Reference files

- Agent definition: [agent.json](agent.json)
