---
name: aiso-agent-readiness-lite
description: >
  AI agent readiness checklist of the rendered page for autonomous web agents (ChatGPT agent,
  Claude in Chrome, Gemini and Copilot agents, Playwright MCP, Browser Use): semantic landmarks,
  interactive roles and accessible names, clickable div-soup, ARIA conformance, form labels and
  autocomplete tokens, live regions, dialog focus containment, closed Shadow DOM, headless render
  integrity and the agent tool surface (WebMCP, /.well-known/ucp, agent cards), measured by
  agent_readiness_lite.py (static HTML plus the Playwright accessibility tree). Produces 14 checks
  per page answered PASS, FAIL, N/A or could not verify, with per-defect fixes; no score, no
  weights, no gate. Sole owner of the accessibility-tree, ARIA, control-name and form-semantics
  verdicts. Not for heading hierarchy (seo-heading-matrix-lite), SSR (aiso-technical-lite), robots
  (aiso-crawlers-lite), llms.txt (aiso-llmstxt-lite) or JSON-LD (aiso-schema-lite): cite those,
  never re-measure. Not a WCAG conformance claim. (Lite edition.)
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


# aiso-agent-readiness-lite: AI-Ready Web, HTML เชิงความหมาย และ accessibility tree

Read and execute the agent workflow from [agent.json](agent.json).
Follow all phases and steps sequentially.

> สืบทอด [_base/skill-scaffold.md](../rainmojo-so-lite/_base/skill-scaffold.md)
> และ [_base/presentation-scaffold.md](../rainmojo-so-lite/_base/presentation-scaffold.md) อ่านครั้งเดียว

## ทำไมต้องมีสกิลนี้

AI agent รับรู้หน้าเว็บ 3 แบบ (ตรวจสอบกับเอกสารผู้ผลิต 2026-09): accessibility tree (Playwright MCP,
Claude in Chrome, Perplexity Comet, ChatGPT Atlas, Stagehand), DOM บวกภาพหน้าจอ (Browser Use, Project Mariner)
และภาพหน้าจออย่างเดียว (OpenAI Operator, Anthropic computer use, Gemini Computer Use, Nova Act, Edge Copilot Actions)
สำหรับสองกลุ่มแรก `div` ที่คลิกได้มี role generic และไม่มีชื่อ, input ที่มีแต่ placeholder จะเสียชื่อทันทีที่ agent พิมพ์
และ modal ที่เป็น `div` ปล่อยให้พื้นหลังยังคลิกได้ กลุ่มที่สามยังพึ่งข้อความที่มองเห็นและเลย์เอาต์ที่นิ่งเร็ว

ถ้อยคำสองอย่างที่สกิลนี้ไม่พูด เพราะหลักฐานหักล้าง: **agent ไม่ค้างเมื่อไม่มี `aria-live`** (มันกลับมาอ่านหน้าใหม่เอง
หลังลงมือทำ) และ **INP ไม่ใช่สิ่งที่ agent รอ** (งบเวลาต่อขั้นเป็นวินาทีถึงนาที) สิ่งที่สำคัญคือ DOM นิ่งในช่วงนั้น
และข้อความยืนยันยังอยู่ให้เห็น และ **accessibility ไม่ใช่ปัจจัยจัดอันดับของ Google** ผลของสกิลนี้จึงเป็นเรื่อง
การใช้งานโดย agent และผู้ใช้ ไม่ใช่เรื่องอันดับ

## ตรวจอะไร (14 ข้อ ตอบ PASS, FAIL, N/A, COULD NOT VERIFY, INFO)

| หมวด | ข้อตรวจ | วิธี |
|---|---|---|
| Controls | CTL-01 ไม่มี div หรือ span ที่คลิกได้โดยไม่มี role | static (onclick, cursor:pointer) และ rendered (computed cursor) |
| | CTL-02 ARIA ถูกต้อง role ที่มีจริง และ IDREF ชี้ไปที่ id ที่มีอยู่ | static |
| | CTL-03 control ที่โต้ตอบได้ทุกตัวมีชื่อใน accessibility tree | rendered accname จาก CDP getFullAXTree, static เมื่อไม่มี Playwright |
| | CTL-04 control มีข้อความที่มองเห็นหรือไอคอนที่มีป้าย | static |
| Forms | FRM-01 ทุก field มี label แบบผูกด้วยโค้ด (placeholder อย่างเดียวไม่นับ) | static |
| | FRM-02 field ตัวตน (ชื่อ อีเมล โทร ที่อยู่ บัตร) มี autocomplete token ตามไวยากรณ์ WHATWG | static |
| | FRM-03 type, name และ required ตรงกับข้อมูล | static |
| Structure | STR-01 มีโครง landmark ครบ: main หนึ่งเดียว, navigation, banner, contentinfo | static |
| | STR-02 เนื้อหาทุกก้อนอยู่ใน landmark | static |
| Dynamic state | DYN-01 มี live region เมื่อหน้ามี action ที่เปลี่ยนสถานะ | static |
| | DYN-02 modal ใช้ dialog หรือ aria-modal พร้อมกักโฟกัส | static และ dialog ที่เปิดอยู่ตอน rendered |
| | DYN-03 ไม่มี closed Shadow DOM ครอบ control | static และ rendered |
| Render | ACC-01 headless Chromium ได้หน้าจริง (200, DOM จริง, ไม่ติด bot wall) | rendered เท่านั้น ไม่มี Playwright = COULD NOT VERIFY |
| Inventory | ACC-02 พื้นผิวเครื่องมือของ agent: WebMCP, MCP server card, WordPress MCP Adapter, Shopify MCP, /.well-known/ucp, api-catalog, OAuth discovery, A2A card, OpenAPI, NLWeb, text/markdown negotiation, ai-plugin.json ที่เลิกใช้แล้ว | HTTP probe, INFO เท่านั้น |

กติกาที่ทำให้รายการซื่อสัตย์

- **ไม่มีคะแนน ไม่มีน้ำหนัก ไม่มีคะแนนรวมของเว็บ และไม่มี gate** รายงานคือจำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจได้ ต่อหน้า
  และรายการ defect พร้อมวิธีแก้ระดับโค้ด ผู้อ่านตัดสินลำดับความสำคัญเองจากจำนวนหน้าที่ข้อนั้นล้ม
- ข้อที่ไม่เข้าข่าย (ไม่มีฟอร์ม ไม่มี modal ไม่มี custom element) เป็น N/A ข้อที่ rendered tier ไม่ได้รันเป็น COULD NOT VERIFY
  ทั้งสองอย่างไม่นับเป็นผ่านและไม่นับเป็นไม่ผ่าน ห้ามประเมินแทน
- ตัวเลข token, latency และต้นทุนที่บางบทความอ้าง ไม่ถูกนำมาใช้ เพราะไม่มีผู้ผลิตรายใดเผยแพร่ รายงานอ้างเฉพาะสิ่งที่มาตรฐาน
  เอกสารผู้ผลิต หรืองานวิจัยระบุ
- โครงหัวข้อ, SSR, robots, llms.txt และ JSON-LD อ้างจากสกิลเจ้าของในแผงผลที่อ้างมา ไม่ตรวจซ้ำที่นี่
- รุ่นนี้ไม่มี axe-core subset, ไม่มี settle probe, ไม่มี legal note และไม่มี Task Completion Rate (บริการ aiso-task-completion
  ของรุ่นเต็มไม่อยู่ในชุดนี้) ถ้าผู้ใช้ถามถึง ให้บอกตรง ๆ ว่าไม่มีในรุ่นนี้

## วิธีรัน

```bash
python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/agent_readiness_lite.py https://{domain}/ --scope representative_templates --output json --out work/{domain}/01-current/{domain}_agent-readiness_{YYYY-MM-DD}.json
python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/agent_readiness_lite.py https://{domain}/ --scope representative_templates --output md
```

- `--scope` เหมือน `aiso-technical-lite`: `homepage_only` (1 หน้า), `representative_templates` (static ไม่เกิน 60 หน้า, rendered 12 หน้า,
  3 หน้าต่อ template), `full_site_crawl` (static ไม่เกิน 500, rendered 18) การค้นหาหน้าอ่าน sitemap.xml บวกเมนูหน้าแรก
  แล้วสุ่มต่อ template (home, service, product, category, article, contact, checkout)
- `--render auto` ใช้ Playwright Chromium เมื่อติดตั้งแล้ว (`pip install playwright` แล้ว `playwright install chromium`)
  `--render off` รันเฉพาะ static และรายงานข้อที่ต้องเรนเดอร์เป็น COULD NOT VERIFY สคริปต์ไม่ส่งฟอร์ม ไม่กด checkout, ชำระเงิน, login หรือลบ
- `--html <ไฟล์>` ตรวจซอร์สที่ผู้ใช้คัดลอกมาให้ (static เท่านั้น) สำหรับ host ที่รันคำสั่งไม่ได้ ให้ขอซอร์สตามวิธีใน `aiso-technical-lite`
- `--self-test` ต้องขึ้น `SELF-TEST PASS` ก่อนใช้ครั้งแรก

## Output
### Naming convention

```
{domain}_agent-readiness_{YYYY-MM-DD}.{ext}
```

รายงาน Markdown และ JSON ของสคริปต์อยู่ใต้ `work/{domain}/` ตามกติกาของ `new-workspace-lite`
รอบแรกลง `00-baseline/` รอบถัดไปลง `01-current/`

## หัวข้อของรายงาน

1. จำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจได้ ทั้งเว็บ พร้อมขอบเขตและรายการที่ตรวจไม่ได้
2. ตารางต่อหน้า (URL, template, ผ่าน, ไม่ผ่าน, control ที่ไม่มีชื่อ, field ที่ไม่มี label)
3. defect และวิธีแก้ จัดกลุ่มตามข้อตรวจ แต่ละข้อมี selector และตัวอย่างโค้ด (button แทน div, label for=id, autocomplete token,
   dialog showModal, role=status)
4. แผงผลที่อ้างจากสกิลอื่น: หัวข้อ, SSR, robots, llms.txt, JSON-LD
5. พื้นผิวเครื่องมือของ agent (declared, not declared, obsolete) ข้อมูลประกอบ ไม่มีน้ำหนัก

## การวางไฟล์ผลลัพธ์

สกิลนี้อยู่ในชุดที่ใช้โครงโฟลเดอร์ของสกิล `new-workspace-lite`

1. ผลลัพธ์ทุกไฟล์อยู่ใต้ `work/{domain}/`
2. ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์หัวข้อเดียวกัน ให้เขียนลง `00-baseline/` ถ้ามีแล้ว ให้เขียนลง `01-current/`
3. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร
4. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน ห้ามสร้างโครงเองแบบอื่น

## การ์ด Tier 1 ของสกิลนี้

จบงานทุกครั้งด้วยการ์ดสรุปตามชั้นแสดงผล (`so-present-lite`): โหมด `audit` `dimensions` หนึ่งแถว agent_readiness =
จำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจได้ทั้งเว็บ (จาก JSON ของสคริปต์ผ่าน `build_summary.py --agent`), `key_risk` คือข้อตรวจที่ล้ม
บนหน้ามากที่สุด, `actions` คือวิธีแก้ของ 4 ข้อที่ล้มบ่อยที่สุด, `transparency.could_not_verify` คือรายการที่ตรวจไม่ได้
ทุกค่าบนการ์ดคัดลอกจาก JSON ห้ามประเมินเพิ่ม รุ่น Lite ไม่มีคะแนน จึงไม่ใส่บล็อก `score`
เรนเดอร์ด้วย `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --summary <summary.json> --target auto --host {host}`
แล้วปิดด้วยบรรทัดส่งต่อไปยังรายงานฉบับเต็ม ซึ่งต้องครบและไม่ถูกย่อ

## Reference files

- Agent definition: [agent.json](agent.json)
- Script: `skills/rainmojo-so-lite/scripts/agent_readiness_lite.py` (`--self-test` available)

## กฎ

- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`** สองคำนี้คนละความหมาย ถ้าเขียนผิดผู้ใช้จะสรุปกลับด้าน
- **ทำได้บางส่วนต้องส่งส่วนนั้นเสมอ** ห้ามส่งตารางที่ทุกช่องว่าง และห้ามปฏิเสธทั้งงานเพราะขาดข้อมูลบางอย่าง ให้ติดป้ายว่าข้อไหนยืนยันแล้ว ข้อไหนต้องยืนยันเพิ่ม
- **ห้ามคำนวณคะแนน น้ำหนัก หรือเปอร์เซ็นต์** รายงานเป็นจำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจได้เท่านั้น
- **ห้ามอ้างว่าผลนี้คือการรับรอง WCAG** และห้ามเขียนว่าการแก้ตามรายการนี้จะยกอันดับใน Google
- **ห้ามให้สคริปต์หรือผู้ช่วยส่งฟอร์ม กดชำระเงิน login หรือลบอะไรบนเว็บลูกค้า** ทุกกรณี
