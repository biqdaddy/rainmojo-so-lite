---
name: aiso-crawlers-lite
description: >
  AI crawler access analysis. ตรวจว่าบอทของค่าย AI เข้าเว็บได้จริงไหม โดยอ่าน robots.txt แล้ว**ยิงทดสอบด้วยชื่อบอทจริง**
  เพราะสิ่งที่ประกาศกับสิ่งที่เกิดขึ้นจริงมักไม่ตรงกัน Provides a complete access map per crawler with
  allow or block status. (Lite edition.)
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


# aiso crawlers

Read and execute the agent workflow from [agent.json](agent.json).
Follow all phases and steps sequentially.

## ขั้นที่ 1 อ่านสิ่งที่เว็บประกาศไว้

ดึง `https://{domain}/robots.txt` มาอ่าน แล้วจดว่าบอทตัวไหนถูกเขียน `Allow` หรือ `Disallow` ไว้บ้าง
ดึง `/llms.txt` และ `/sitemap.xml` ด้วย ถ้ามี

**นี่คือแค่การประกาศเจตนา ยังไม่ใช่ของจริง** ต้องทำขั้นที่ 2 ต่อเสมอ

### อ่าน robots.txt ให้ถูกกลไก

**บอทหนึ่งตัวเชื่อฟังกลุ่มเดียวเท่านั้น** คือกลุ่มที่ชื่อ user-agent ตรงกับชื่อของมันแบบเจาะจงที่สุด
และ **เมื่อมันมีกลุ่มของตัวเองแล้ว มันจะไม่อ่านกลุ่ม `*` เลย ไม่อ่านแม้แต่บรรทัดเดียวในนั้น**

- **ห้ามรายงานผลเป็นการเอากฎในกลุ่มเจาะจงมารวมกับกฎในกลุ่ม `*`** สองกลุ่มนี้ไม่ได้บวกกัน
  ให้รายงานเป็นสองส่วนคือ **กลุ่มไหนที่ใช้กับบอทตัวนี้** และ **กฎที่อยู่ในกลุ่มนั้น** เท่านั้น
- ลำดับของกลุ่มในไฟล์ **ไม่มีความหมายอะไรเลย** อยู่บนหรืออยู่ล่างให้ผลเหมือนกัน
- การจับคู่ชื่อจะไม่สนใจส่วนที่เหลือที่ไม่ตรง บอทที่ชื่อมีส่วนต่อท้ายจึงเข้ากลุ่มที่ประกาศด้วยส่วนต่อท้ายนั้น
  **ไม่ใช่กลุ่มที่ประกาศด้วยชื่อสั้นกว่า** เช่น `Google-Extended` กับ `Googlebot` เป็นคนละกลุ่มกัน
- ผลลัพธ์ที่ผิดบ่อยที่สุดของข้อนี้คือการรายงานว่าบอทตัวหนึ่งถูกบล็อกด้วยกฎในกลุ่ม `*`
  ทั้งที่บอทตัวนั้นมีกลุ่มของตัวเองอยู่ และจะไม่มีวันอ่านกลุ่ม `*` นั้นเลย

**ขอบเขตของไฟล์ คือหนึ่งไฟล์ต่อหนึ่งโฮสต์ และต่อหนึ่ง scheme**

- ทุก subdomain ต้องมีไฟล์ของตัวเอง และ `http://` กับ `https://` ก็นับเป็นคนละโฮสต์ ต้องมีคนละไฟล์
- ไฟล์ต้องอยู่ที่ราก ชื่อไฟล์ต้องเป็นตัวพิมพ์เล็กทั้งหมด และต้องถูกส่งมาเป็น plain text
  ไม่งั้นจะถูกเมินทั้งไฟล์
- ตรวจ `blog.example.com/robots.txt` แล้วเอาผลไปสรุปแทน `example.com` **คือการรายงานผิดไฟล์**

**บรรทัด `Noindex:` ใน robots.txt ตายไปตั้งแต่ปี 2019 แล้ว**
หน้าไหนที่ยังพึ่งมันอยู่ **เข้าดัชนีได้เต็มที่** ต้องย้ายไปใช้ meta robots บนหน้า
หรือ header `x-robots-tag` แทน **ลงเป็นความเสี่ยงที่เปิดอยู่จริง ไม่ใช่ข้อติเรื่องความเรียบร้อย**

**ไฟล์ที่ใช้ประกอบหน้า ถ้าโดนปิด ต้องรายงานแยกจาก path ของหน้า**

ดึงรายชื่อไฟล์ CSS และ JS ที่หน้านั้นเรียกใช้จริงออกมา แล้วเอาไปทดสอบกับ robots.txt ทีละไฟล์
ไฟล์ประกอบไหนที่ถูกปิด **จะทำให้ตัวเรนเดอร์ประกอบหน้าไม่สำเร็จ**
ทั้งเลย์เอาต์ ขอบเขตของเนื้อหาหลัก และทุกอย่างที่สคริปต์ใส่เข้ามา จะพังตามกันหมด
**แม้แต่กับเว็บที่เซิร์ฟเวอร์เรนเดอร์มาให้แล้วก็ตาม**

ให้ลงรายชื่อ URL ของไฟล์ประกอบที่โดนปิด พร้อมบรรทัดกฎที่ปิดมัน
ส่วนการวินิจฉัยว่าหน้ามันเรนเดอร์อะไรไม่ออกบ้าง เป็นข้อค้นพบของ `aiso-technical-lite` ไม่ใช่ของสกิลนี้

## ขั้นที่ 2 ทดสอบว่าเข้าได้จริงไหม

**ขั้นนี้สำคัญที่สุดและห้ามข้าม** เพราะเว็บจำนวนมากเขียน robots.txt ต้อนรับบอทไว้อย่างดี
แต่เซิร์ฟเวอร์หรือ WAF ด้านหน้ากลับปิดประตูใส่บอทตัวเดียวกัน ผลคือ robots.txt สูญเปล่าทั้งไฟล์

ยิงทดสอบด้วยชื่อบอทจริง แล้วดูรหัสตอบกลับ

```bash
for UA in "OAI-SearchBot/1.0" "ChatGPT-User/1.0" "Claude-SearchBot/1.0" "PerplexityBot/1.0" "meta-webindexer/1.0" "Applebot/0.1" "Googlebot/2.1" "bingbot/2.0" "GPTBot/1.0" "ClaudeBot/1.0"; do
  for P in "/" "/robots.txt" "/sitemap.xml"; do
    printf "%-22s %-14s %s\n" "$UA" "$P" "$(curl -s -o /dev/null -w '%{http_code}' -A "$UA" -m 15 "https://{domain}$P")"
  done
done
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

**แล้วยิงเทียบอีกสองรอบเพื่อพิสูจน์ว่าเป็นการคัดตามชื่อบอท ไม่ใช่การจำกัดจำนวนครั้งธรรมดา**

```bash
curl -s -o /dev/null -w 'Chrome        %{http_code}\n' -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120" -m 15 "https://{domain}/"
curl -s -o /dev/null -w 'UA มั่ว        %{http_code}\n' -A "abcdef" -m 15 "https://{domain}/"
```

ถ้า Chrome ได้ 200 และ UA มั่วได้ 200 แต่ชื่อบอทได้ 403 หรือ 429 **แปลว่าเว็บคัดตามชื่อบอทแน่นอน**
ให้เขียนหลักฐานสามบรรทัดนี้ลงรายงาน เพราะทีมเซิร์ฟเวอร์จะเถียงว่าบังเอิญไม่ได้

## ทะเบียนบอทและแพลตฟอร์ม (registry) ใช้เป็นแหล่งเดียว

รายชื่อบอท 68 token ของ 10 แพลตฟอร์ม (11 การ์ด) อยู่ใน
`{PLUGIN_ROOT}/skills/rainmojo-so-lite/reference/frameworks/ai-platform-registry.json`
ทุก token ระบุเจ้าของ บทบาท (`search_index`, `training`, `user_fetcher`, `ads`, `link_preview`, `agent`)
ระดับหลักฐาน (`official` = ผู้ผลิตประกาศเอง, `observed` = ชุมชนสังเกตเห็น, `none`)
พฤติกรรมต่อ robots.txt และลิงก์เอกสาร พิมพ์รายการด้วย
`python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/ai_platforms.py --list-crawlers`

- **บอทค้นหาและบอทที่ผู้ใช้สั่งเปิดหน้า ตัดสินว่าเว็บถูกอ้างอิงได้ไหม** ได้แก่ OAI-SearchBot, ChatGPT-User,
  Claude-SearchBot, Claude-User, PerplexityBot, Perplexity-User, Googlebot, bingbot, meta-webindexer,
  meta-externalfetcher, Applebot, Amzn-SearchBot
- **บอทเก็บข้อมูลฝึกโมเดล ไม่กระทบการมองเห็น** ได้แก่ GPTBot, ClaudeBot, Google-Extended,
  Applebot-Extended, meta-externalagent, Amazonbot, CCBot การบล็อกหรืออนุญาตเป็นนโยบายของเจ้าของเว็บ
  ลงผลเป็น **เจ้าของเว็บตัดสิน** ไม่ใช่ผ่านหรือไม่ผ่าน
- **GPTBot เป็นบอทฝึกโมเดลเท่านั้น** ไม่ได้ตัดสินว่าเว็บขึ้นใน ChatGPT search หรือไม่
  ตัวที่ตัดสินคือ OAI-SearchBot และการตั้งค่าบอทแต่ละตัวของ OpenAI เป็นอิสระต่อกัน
  รายงานรุ่นก่อนที่เขียนว่า บล็อก GPTBot แล้วจะหายจาก ChatGPT search เป็นข้อความที่ผิด
- **Grok และ DeepSeek ไม่ประกาศชื่อบอท ส่วน Qwen มีแต่ชื่อที่ชุมชนสังเกต** การเข้าถึงของสามค่ายนี้
  ให้ลงว่า **ตรวจสอบไม่ได้** เสมอ ห้ามเดา และห้ามนับเป็นไม่ผ่าน
- **บรรทัดประกาศความต้องการใช้งาน** ที่พบใน robots.txt ปี 2026 คือ `Content-Signal` (Cloudflare),
  `Content-Usage` (IETF AIPREF), `License` (RSL) และ HTTP 402 crawler paywall ให้อ่านแล้วรายงานตามที่พบ
  ไม่ให้คะแนน และถ้าประกาศ `ai-input=no` ให้เขียนว่าเว็บเลือกไม่เข้าร่วมคำตอบ AI โดยนโยบาย
- **การบล็อกที่ขอบเครือข่าย** เช่น Cloudflare AI bot policy บล็อกบอทค้นหาได้โดยไม่มีบรรทัดใน robots.txt
  ดังนั้น robots.txt ที่อนุญาต เป็นเงื่อนไขจำเป็นแต่ไม่พอ ต้องยิงทดสอบด้วยชื่อบอทตามขั้นที่ 2 เสมอ

สคริปต์ที่ให้มาด้วย (อ่าน robots.txt ตาม RFC 9309: กลุ่ม User-agent หลายบรรทัดใช้กฎร่วมกัน
จับคู่ชื่อแบบไม่สนตัวพิมพ์ ตัด BOM ทิ้ง path สุขอนามัยอย่าง `/wp-admin/` ไม่ทำให้เป็น บางส่วน)

```bash
python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/robots_generator.py https://{domain} --mode analyze --output json
python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/robots_generator.py https://{domain} --mode generate --policy selective --output txt
```

`--policy` มีสามแบบ `friendly` (อนุญาตทุกบอทที่มีเอกสาร), `selective` (อนุญาตบอทค้นหา ปิดโฟลเดอร์ส่วนตัว),
`blocked` (ปิดบอทที่ไม่มีเอกสารหรือไม่เคารพ robots.txt) ไฟล์ที่สร้างดึงชื่อบอทจาก registry เสมอ ไม่พิมพ์ชื่อเอง

## ขั้นที่ 3 ตารางผล ต้องมีสองคอลัมน์เสมอ

| บอท | robots.txt ประกาศว่า | เข้าได้จริงไหม | ตรงกันไหม |
|---|---|---|---|
| GPTBot | อนุญาต | 429 | **ไม่ตรง** |

**ช่องว่างระหว่างสองคอลัมน์นี้คือสิ่งที่ต้องรายงานเป็นหัวข้อแรก** ถ้าทุกแถวตรงกัน ให้เขียนว่าตรงกันทั้งหมด
ถ้ามีแถวไหนไม่ตรง ให้ขึ้นต้นรายงานด้วยแถวนั้น

**ห้ามสรุปว่าเว็บผ่าน โดยดูจาก robots.txt อย่างเดียวเด็ดขาด** เพราะเป็นการรายงานผลที่กลับด้านจากความจริง
รายงานที่ทำให้เจ้าของเว็บสบายใจทั้งที่มีปัญหา แย่กว่าไม่มีรายงาน

## ขั้นที่ 4 ระบุว่าใครต้องแก้

ถ้าเจอว่าถูกบล็อกจริง ให้ดูหน้า error ว่ามาจากใคร แล้วบอกให้ชัดว่าต้องไปแก้ที่ไหน

| หน้า error บอกว่า | ต้องแก้ที่ | บอกใคร |
|---|---|---|
| nginx | เซิร์ฟเวอร์ต้นทาง | ทีมโฮสต์หรือ dev |
| cloudflare | ตั้งค่า WAF หรือ Bot Fight Mode | คนดูแลบัญชี Cloudflare |
| ไม่ระบุ | ให้ถามโฮสต์ว่ามีการกรอง user-agent ไหม | ทีมโฮสต์ |

**ห้ามแก้ robots.txt เป็นทางแก้ ถ้าต้นเหตุคือการบล็อกที่ชั้นเซิร์ฟเวอร์** เพราะแก้แล้วจะไม่มีอะไรดีขึ้นเลย

ปิดท้ายด้วยคำสั่ง `curl` ชุดเดิมไว้ให้ผู้ใช้เอาไปทดสอบซ้ำหลังแก้เสร็จ

## ขั้นที่ 5 ชื่อบอทเป็นแค่คำกล่าวอ้าง ต้องยืนยันก่อนเชื่อ

ชื่อ user-agent ใครก็พิมพ์ได้ **ทั้งใน log ของเซิร์ฟเวอร์ และตอนที่เราจะไปเขียนกฎอนุญาตหรือปิดที่ชั้นเซิร์ฟเวอร์
ต้องยืนยันตัวตนก่อนเสมอ** วิธียืนยันมีขั้นตอนตายตัว ทำสองทางเสมอ

1. เอา IP ที่ยิงเข้ามา ทำ **reverse DNS** ให้ได้ชื่อโฮสต์ออกมา
2. เอาชื่อโฮสต์ที่ได้นั้น **resolve กลับไปข้างหน้า** แล้วดูว่าได้ IP เดิมกลับมาไหม
3. ได้ IP เดิมกลับมา จึงถือว่ายืนยันแล้ว **ไม่ตรงกัน คือของปลอม**

```bash
nslookup 66.249.66.1          # ขั้นที่ 1 ได้ชื่อโฮสต์
nslookup crawl-66-249-66-1.googlebot.com   # ขั้นที่ 2 ต้องได้ IP เดิมกลับมา
```

**ทำ reverse อย่างเดียวไม่พอ และปลอมได้** เพราะคนที่ถือ IP นั้นตั้งชื่อ reverse ของตัวเอง
ให้ดูน่าเชื่อถือได้ตามใจ **การข้ามขั้นที่ 2 คือการเชื่อของปลอม**

รันคำสั่งพวกนี้ไม่ได้ ให้เขียนว่า **ตรวจไม่ได้** แล้วบอกว่าต้องใช้อะไรถึงจะตรวจได้
ห้ามเขียนว่ายืนยันแล้ว และห้ามเขียนว่าเป็นของปลอม

**การบล็อกเป็นช่วง IP ให้ลงเป็นความเสี่ยงสูงเสมอ** วิธีนี้ถูกเปิดใช้กันบ่อยเพื่อประหยัดแบนด์วิดท์
และมันตัดบอทของเครื่องมือค้นหาและบอท AI ตัวจริงออกไปด้วยเป็นประจำ

**คำสั่งใน robots.txt เป็นการประกาศเจตนา ไม่ใช่การบังคับ** ตัวเลขรายบอทที่เห็นใน log
จึงเป็นตัวตนที่ถูกกล่าวอ้างทั้งหมด และการจะหยุดบอทที่ไม่สนใจ robots.txt จริง ๆ
ต้องไปทำที่ชั้นเซิร์ฟเวอร์ **การอ่าน log ของเซิร์ฟเวอร์อยู่นอกขอบเขตของชุดสกิลรุ่นนี้**
ถ้าผู้ใช้มี log ให้ใช้กฎการยืนยันข้างบนกับมัน แล้วเขียนกำกับว่าข้อมูลมาจากผู้ใช้

## การ์ด Tier 1 ของสกิลนี้

จบงานทุกครั้งด้วยการ์ดสรุปตามชั้นแสดงผล (`so-present-lite`): โหมด `audit` `dimensions` หนึ่งแถวคือ จำนวนบอทค้นหาที่มีเอกสารและเข้าได้ ต่อ จำนวนบอทค้นหาที่มีเอกสารทั้งหมด (ผลจาก `robots_generator.py --output json` ผ่าน `build_summary.py --robots`), `key_risk` คือแถวที่ประกาศกับของจริงไม่ตรงกัน, `actions` คือรายการที่ต้องแก้ไม่เกิน 4 ข้อ, `transparency.could_not_verify` คือบอทที่ตรวจสอบไม่ได้
ทุกค่าบนการ์ดคัดลอกจากไฟล์ผลลัพธ์ที่เพิ่งเขียน ห้ามประเมินเพิ่ม ข้อที่ตรวจไม่ได้ให้ขึ้นว่า ตรวจสอบไม่ได้
รุ่น Lite ไม่มีคะแนน จึงไม่ใส่บล็อก `score` ค่าใน `dimensions` คือจำนวนข้อที่ผ่านต่อจำนวนข้อที่ตรวจ
เรนเดอร์ด้วย `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --summary <summary.json> --target auto --host {host}`
แล้วปิดด้วยบรรทัดส่งต่อไปยังไฟล์ผลลัพธ์ฉบับเต็ม ซึ่งต้องครบและไม่ถูกย่อ

## Output
### Naming convention

ไฟล์ที่สร้างต้องตั้งชื่อตาม pattern:

```
{domain}_crawler-access_{YYYY-MM-DD}.{ext}
```

ตัวอย่าง: `example-com_crawler-access_2026-03-28.md`

## การวางไฟล์ผลลัพธ์

สกิลนี้อยู่ในชุดที่ใช้โครงโฟลเดอร์ของสกิล `new-workspace-lite`

1. ผลลัพธ์ทุกไฟล์อยู่ใต้ `work/{domain}/`
2. ถ้า `work/{domain}/00-baseline/` ยังไม่มีไฟล์หัวข้อเดียวกัน ให้เขียนลง `00-baseline/` ถ้ามีแล้ว ให้เขียนลง `01-current/`
3. เขียนเสร็จ ให้เพิ่มบรรทัดลงตารางใน `work/{domain}/CHANGELOG.md` ว่าวันที่ รันสกิลอะไร ได้ไฟล์อะไร
4. ถ้ายังไม่มี `work/{domain}/` ให้แนะนำผู้ใช้รันสกิล `new-workspace-lite` ก่อน ห้ามสร้างโครงเองแบบอื่น

## Reference files

- Agent definition: [agent.json](agent.json)

## กฎ

- **ถ้าดึงข้อมูลไม่สำเร็จ ให้เขียนว่า `ตรวจไม่ได้` ห้ามเขียนว่า `ไม่มี`** สองคำนี้คนละความหมาย ถ้าเขียนผิดผู้ใช้จะสรุปกลับด้าน
- **ทำได้บางส่วนต้องส่งส่วนนั้นเสมอ** ห้ามส่งตารางที่ทุกช่องว่าง และห้ามปฏิเสธทั้งงานเพราะขาดข้อมูลบางอย่าง ให้ติดป้ายว่าข้อไหนยืนยันแล้ว ข้อไหนต้องยืนยันเพิ่ม · การใช้ข้อจำกัดเป็นข้ออ้างไม่ส่งงาน ไม่ใช่ความซื่อสัตย์
- **ห้ามรายงานว่าบอทถูกบล็อก โดยเอากฎในกลุ่มเจาะจงมารวมกับกฎในกลุ่ม `*`**
  บอทที่มีกลุ่มของตัวเองจะไม่อ่านกลุ่ม `*` เลย ต้องบอกให้ชัดว่าใช้กลุ่มไหนตัดสิน
- **ห้ามสรุปแทนโฮสต์อื่นหรือ scheme อื่น** ไฟล์ robots.txt เป็นของหนึ่งโฮสต์ต่อหนึ่ง scheme เท่านั้น
- **ห้ามยืนยันตัวตนบอทด้วย reverse DNS อย่างเดียว** ต้อง resolve กลับไปข้างหน้าให้ได้ IP เดิมด้วยเสมอ
