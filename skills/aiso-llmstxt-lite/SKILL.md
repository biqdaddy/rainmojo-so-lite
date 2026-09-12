---
name: aiso-llmstxt-lite
description: >
  Analyzes and generates llms.txt files, the emerging standard for helping AI systems
  understand website structure and content. Can validate existing llms.txt files or generate
  new ones from scratch by crawling the site. (Lite edition for workshop use.)
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


# aiso llmstxt

Read and execute the agent workflow from [agent.json](agent.json).
Follow all phases and steps sequentially.
**ก่อนเริ่ม workflow ให้ทำขั้นที่ 0 ด้านล่างให้เสร็จก่อน**

## ขั้นที่ 0 ดึงไฟล์ดิบมาเก็บไว้ก่อน

**ต้องทำก่อนขั้นอื่นทั้งหมด** เพราะ WebFetch คืนเนื้อหาที่แปลงเป็นข้อความแล้ว
เครื่องหมาย Markdown ของ llms.txt อย่าง `#` `>` และ `- [ชื่อ](URL)` ถูกกลืนหายไป
และ WebFetch ไม่บอกรหัสสถานะ HTTP ทำให้แยกไม่ออกว่าไฟล์ไม่มีจริง
หรือมีอยู่แต่เซิร์ฟเวอร์ตอบหน้า 404 ที่เป็น HTML กลับมาแทน
ส่วนหน้าแรกที่ใช้ทำ llms.txt ก็ต้องดูซอร์สดิบ เพราะ title, meta description
และ `href` ของเมนูกับฟุตเตอร์ ถูก WebFetch ตัดทิ้งไปตอนแปลงเป็นข้อความ
ถ้าตรวจจากผล WebFetch อย่างเดียว จะรายงานว่า ไม่มี ทั้งที่มีอยู่ ซึ่งเป็นผลลบลวง

```bash
mkdir -p work/{domain}/uploads
curl -sSL -w "llms.txt %{http_code}\n" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120" \
  -m 25 "https://{domain}/llms.txt" -o work/{domain}/uploads/llms.txt
curl -sSL -w "llms-full.txt %{http_code}\n" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120" \
  -m 25 "https://{domain}/llms-full.txt" -o work/{domain}/uploads/llms-full.txt
curl -sSL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120" \
  -m 25 "https://{domain}/" -o work/{domain}/uploads/home.html
```

รหัสที่ `-w` พิมพ์ออกมาคือคำตอบว่าไฟล์มีอยู่ไหม 200 คือมี 404 คือไม่มี 403 คือถูกบล็อก
**แล้วค่อยใช้ Read และ Grep กับไฟล์ที่ดาวน์โหลดมา** ไม่ใช่กับผล WebFetch
ถ้าได้รหัส 404 แต่ไฟล์ที่ได้เป็น HTML ให้ถือว่าไม่มีไฟล์ ห้ามเอาเนื้อหาหน้า 404 ไปตรวจ

### ถ้าใช้คำสั่งพวกนี้ไม่ได้

**บาง host ไม่มีเครื่องมือรันคำสั่งให้** เช่น Cowork, Claude Desktop และ GPT desktop
ถ้าเป็นแบบนั้น ให้ทำแบบนี้แทน แล้วงานจะยังเดินต่อได้

1. บอกผู้ใช้ว่า **ขอให้ช่วยเปิดไฟล์แล้วคัดลอกของจริงมาให้**
   llms.txt ให้เปิด `https://{domain}/llms.txt` แล้วคัดลอกทั้งหน้ามาวางในแชท
   ส่วนหน้าแรกให้เปิดในเบราว์เซอร์ กด `Ctrl+U` หรือ `Cmd+Option+U` เพื่อดู source
   แล้วเลือกทั้งหมด คัดลอก มาวางในแชท
2. ถ้าผู้ใช้ทำให้ได้ ให้ทำงานต่อจากของที่ได้มา ตามขั้นตอนเดิมทุกอย่าง
3. ถ้าผู้ใช้ไม่สะดวก ให้ใช้ WebFetch เท่าที่ได้ แล้ว**เขียนกำกับทุกหัวข้อที่กระทบว่า `ตรวจไม่ได้`**
   ห้ามเขียนว่า `ไม่มี` เพราะสองคำนี้คนละความหมาย และการเขียนผิดจะทำให้ผู้ใช้เข้าใจกลับด้าน

**บน Windows** ถ้ารันแล้วขึ้นว่าไม่รู้จักคำสั่ง ให้ลองใน Git Bash หรือ WSL
ถ้าไม่มีทั้งสองอย่าง ให้ใช้วิธีคัดลอกของจริงในข้อ 1

## กฎ

- **ดึงข้อมูลไม่สำเร็จให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`**
  ไม่มี แปลว่าเห็นไฟล์จริงแล้วและไม่พบหัวข้อนั้น ตรวจไม่ได้ แปลว่ายังไม่ได้เห็นไฟล์
  สองคำนี้คนละความหมาย เขียนผิดจะทำให้ผู้ใช้สรุปกลับด้าน
  ทุกช่องที่เขียนว่าตรวจไม่ได้ ต้องบอกด้วยว่าขาดอะไรถึงจะตรวจได้
- **ทำได้แค่ไหนให้ส่งแค่นั้น ห้ามส่งงานเปล่าและห้ามปฏิเสธทั้งงาน**
  ตรวจ URL ได้ไม่ครบ หรือหาข้อเท็จจริงบางข้อไม่เจอ ก็ยังต้องส่งไฟล์และรายงานที่ทำได้
  พร้อมติดป้ายทุกบรรทัดว่า ยืนยันแล้ว หรือ ต้องยืนยันเพิ่ม
  แล้วแยกรายการที่ยังขาดไว้ท้ายรายงานพร้อมบอกว่าต้องใช้อะไรเพิ่ม
  **การอ้างข้อจำกัดเพื่อไม่ส่งงาน ไม่ใช่ความซื่อสัตย์**
- **ห้ามเดาข้อเท็จจริงลงในไฟล์ llms.txt** ปีที่ก่อตั้ง ที่ตั้ง จำนวนพนักงาน จำนวนลูกค้า
  ต้องมาจากหน้าเว็บจริงและระบุได้ว่าเจอที่หน้าไหน ข้อไหนไม่เจอให้ตัดออกจากไฟล์
  แล้วยกไปอยู่ในรายการที่ต้องให้ผู้ใช้ยืนยันแทน

## สถานะหลักฐานปี 2026 ต้องเขียนกำกับทุกครั้ง

llms.txt เป็น **ข้อสุขอนามัย** ไม่ใช่คันโยกการมองเห็น

- เอกสาร AI features ของ Google ระบุว่าไม่ต้องมีไฟล์ใหม่ใด ๆ เพื่อขึ้นใน AI Overviews หรือ AI Mode
  และ Gary Illyes ของ Google ยืนยันว่า Google ไม่ใช้ llms.txt (Search Central Live, 2025)
- Ahrefs (2026) พบว่า 97 เปอร์เซ็นต์ของโดเมนราว 38,000 แห่งที่มี llms.txt ไม่ถูกขอไฟล์นี้เลยในเดือนพฤษภาคม 2026
- SE Ranking (พฤศจิกายน 2025, 300,000 โดเมน) ไม่พบความสัมพันธ์อย่างมีนัยสำคัญระหว่างการมีไฟล์กับการถูกอ้างอิงในคำตอบ AI
- ยังไม่มีแพลตฟอร์มหลักรายใด (OpenAI, Anthropic, Perplexity, Google, Meta, Microsoft, Apple) ประกาศว่าอ่านไฟล์นี้

**กติกาการเขียน** ทุกผลตรวจหรือคำแนะนำเรื่อง llms.txt ต้องมีป้ายว่า `หลักฐานการใช้งานต่ำ ข้อสุขอนามัย`
ห้ามเขียนว่า Claude, ChatGPT หรือ Perplexity อ่านไฟล์นี้ และห้ามเขียนว่าการมีไฟล์นี้ทำให้ถูกอ้างอิงมากขึ้น
ยังสร้างไฟล์ให้ได้ตามปกติ เพราะต้นทุนต่ำและไม่มีข้อเสีย แต่ลำดับความสำคัญในรายงานอยู่ท้ายสุดเสมอ

## Output
### Naming convention

ไฟล์ที่สร้างต้องตั้งชื่อตาม pattern:

```
{domain}_llmstxt_{YYYY-MM-DD}.{ext}
```

ตัวอย่าง: `example-com_llmstxt_2026-03-28.md`

## การวางไฟล์ผลลัพธ์

สกิลนี้อยู่ในชุดที่ใช้โครงโฟลเดอร์ของสกิล `new-workspace-lite`

1. ผลลัพธ์ทุกไฟล์อยู่ใต้ `work/{domain}/`
2. ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์หัวข้อเดียวกัน ให้เขียนลง `00-baseline/` ถ้ามีแล้ว ให้เขียนลง `01-current/`
3. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร
4. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน ห้ามสร้างโครงเองแบบอื่น

## Reference files

- Agent definition: [agent.json](agent.json)
