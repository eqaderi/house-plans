# Stairs: rules, safety and configuration

Researched 2026-10-13. The question: the owner's stair is used many times a
day. It must be easy and never dangerous, it should be beautiful, and ideally
it has daylight and a view ("when you go down, in front of you, a window").
He asks about riser height, going, rest landings and whether to use a U-turn.

The draft under review is one straight flight of 18 risers x 177.8 mm with a
280 mm going, no intermediate landing, 1100 mm wide, floor-to-floor 3200 mm,
three levels (garage at road level, then the living floor, then the bedroom
floor below).

Tags: **[primary]** means I read the regulation, standard or paper itself.
**[secondary]** means a summary by an official body, a professional reference
or a trade portal. **[weak]** means a forum, DIY site or unread book. Every
number in sections 4 and 6 that is not quoted from a source comes from
`stairs.py` / `stairs2.py`. Those scripts were run during this research and
are not kept in the repo. Their source and raw output are in the appendix.

Persian quotes were transcribed by reading the scanned page images, without
OCR, and the digits were checked at high resolution. Compare the wording
with the print before citing it formally.

---

## 1. Iranian rules

### 1.1 Mabhas 4 (General building requirements, 1396 edition)

Source: a scan of the printed edition,
https://dl.civilgeotech.ir/free/library/national-building-regulations/building-codes/mabhas-4/mabhas-04-1396.pdf
[primary]. Printed page = PDF page − 14 (PDF p. 62 is printed p. 48).

| Clause | Printed page | Text (Persian, verbatim) | Meaning |
|---|---|---|---|
| 4-5-1-7-1 | 48 | «در راه‌پلهٔ ساختمان، حداقل اندازه عمق کف‌پله ۰/۲۸ متر است. ارتفاع پله باید به میزانی باشد که مجموع اندازه کف‌پله و دو برابر ارتفاع آن بین ۰/۶۳ تا ۰/۶۴ متر باشد.» … «یکسان بودن اندازه کف و عمق پله در یک شیب پلکان الزامی است.» | Going ≥ 280 mm; 630 ≤ 2R+G ≤ 640 mm; risers and goings uniform within a flight. **No explicit maximum riser.** |
| 4-5-1-7-2 | 48 | «رعایت مفاد مبحث سوم مقررات ملّی ساختمان در مورد راه‌پله و پلکان الزامی است.» | The Mabhas 3 stair clauses (1.2 below) are mandatory too. |
| 4-5-1-7-3 | 48 | «… در هر صورت پله‌هایی با عرض مفید کمتر از ۱/۱۰ متر و پلکان‌های دارای پاگردی که عموم از آن استفاده کنند با عرض مفید کمتر از ۲/۴۰ متر مجاز نیست، مگر آن‌که در مقررات اختصاصی تصرفی به‌گونه‌ای دیگر تعیین شده باشد.» | General rule: clear width ≥ 1.10 m, unless the occupancy chapter says otherwise (it does; see 4-7-1-1-3). |
| 4-5-1-7-4 | 48 | «حداقل عرض یا شعاع پاگرد، مساوی عرض پله می‌باشد.» | Landing depth or radius ≥ stair width. |
| **4-5-1-7-5** | 48 | «حداکثر تعداد پله‌های بین دو پاگرد در ساختمان‌های مورد استفاده افراد دارای معلولیت و کم‌توانان جسمی حرکتی باید ۱۲ پله باشد.» | **At most 12 steps between two landings in buildings used by people with disabilities or reduced mobility.** |
| 4-5-1-7-6 | 48 | «حداقل ارتفاع غیر سرگیر پله‌ها و پاگردهای آن‌ها در تمام طول مسیر ۲/۰۵ متر است که از لبهٔ هر کف پله اندازه‌گیری می‌شود.» | Headroom ≥ 2.05 m from the nosing line. The print reads 2/05, which settles the digit-reversal doubt (open question 7) for stairs. |
| 4-5-1-10-2 | 50 | «در راه‌پله‌ها، در مواردی که تأمین نور بصورت طبیعی صورت گیرد، سطح شیشه الزامی طبق جدول ۴-۶ و حداقل ۰/۹۰ مترمربع به ازای هر طبقه است.» | A naturally lit stair needs glazing per Table 4-6, at least 0.90 m² per floor. |
| 4-5-1-10-3 | 50 | «درصورت عدم امکان نورگیری راه‌پله‌ها با پنجره‌های دیواری، تأمین نور طبیعی از سقف محفظه پلکان نیز … مجاز است.» | A rooflight is allowed when wall windows are impossible. |
| Table 4-6 | 81–82 | Row «راه‌پله‌ها (در هر طبقه)»: glazing 1:8, ventilation 1:16, minimum ventilation opening 0.45; the "natural light required" column is «–». | Daylight in a stair is **not** mandatory. If it is provided: glazing 1/8 of floor area, ventilation 1/16. |
| 4-5-1-11-1 | 50 | «درمحل‌هایی که اختلاف سطح‌ها از ۰/۷۰ متر بیشتر باشد، باید به وسیلهٔ دست‌انداز یا جان‌پناه … از احتمال سقوط افراد ممانعت شود.» | A guard is needed where the drop exceeds 0.70 m. |
| 4-5-1-11-2 | 51 | «ارتفاع دست‌اندازهای شیب‌دار پله‌ها یا شیب‌راه‌ها از لبهٔ پله یا سطح شیب‌راه باید حداقل ۰/۹۰ متر باشد.» | Sloping guard ≥ 0.90 m above the nosing. |
| 4-5-1-11-3 | 51 | «الف- در دو طرف راه‌پله‌هایی که بیش از دو ارتفاع پله را طی می‌کنند و در مسیرهای دسترس یا خروج اصلی ساختمان یا تصرف قرار دارند.» «… مگر آن‌که در ضوابط اختصاصی تصرف‌ها به گونهٔ دیگری تعیین شده باشد» | General rule: handrails on **both sides** of any stair of more than two risers on a main route. |
| 4-5-1-12-1/2/3 | 51 | «… باید … از مصالح سخت، غیرلغزنده و ثابت باشند.» «کف‌پله‌ها در هر راه‌پله باید از مصالح، رنگ و اندازه‌های یکسان تشکیل شده باشد.» «شعاع گردی لبه کف پله (نوک پله) نباید بیش از ۱۳ میلیمتر باشد.» | Hard, non-slip, fixed treads; the same material, colour and size throughout; nosing radius ≤ 13 mm. |
| 4-7-1-1-3 | 85 | «در ساختمان‌های گروه ۱ تا ۳ با تصرف مسکونی، حداقل عرض مفید پلهٔ مستقیم ۰/۹۰ متر و حداقل عرض پله‌ای که دارای گردش یا پاگرد باشد، ۱/۱۰ متر است.» | Dwellings, building groups 1–3: a straight stair ≥ 0.90 m; a stair with a turn **or a landing** ≥ 1.10 m. |
| 4-7-1-1-6 | 85 | «حداقل پهنای الزامی راهروهای مستقیم و پله‌های داخلی تصرف‌های مسکونی ۰/۹۰ متر است.» | Internal stairs in a dwelling ≥ 0.90 m. |
| 4-7-1-1-7 | 85 | «در پله‌های داخلی تصرف‌های مسکونی که قابل دسترس بودن آن‌ها برای افراد معلول مطابق ضوابط مربوط الزامی نباشد یا سطوح دارای اختلاف سطح ۰/۷۰ متر و کمتر، نیازی به نصب میلهٔ دستگرد نیست، در سایر موارد لازم است که حداقل در یک طرف آن‌ها میله دستگرد نصب شود. در این حالت، میله دستگرد تنها باید از بالاترین ارتفاع پله به پایین‌ترین ارتفاع پله امتداد داشته باشد و نیازی به برگشتن انتهای میله دستگرد یا امتداد بیشتر از طول پله یا شیب‌راه ندارد.» | Inside a dwelling, a handrail on at least one side; none at all if the stair need not be accessible or rises ≤ 0.70 m. No extensions beyond the flight are required. |
| 4-9-9-1-1 | 105 | «ارتفاع دست‌اندازها یا جان‌پناه‌ها از سطح فضا یا بام در دسترس، باید حداقل ۱/۱۰ متر و از لبهٔ پله یا سطح شیب‌دار حداقل ۰/۹۰ متر باشد.» | Guard ≥ 1.10 m above a floor or landing; ≥ 0.90 m above the nosing line. |
| 4-9-9-1-2 | 105 | «فاصلهٔ خالی بین دو نرده عمودی دست‌انداز و جان‌پناه نباید بیشتر از ۰/۱۱ متر باشد. …» | Gaps in a guard ≤ 0.11 m (also for decorative infill). |
| 4-9-9-1-3 | 105 | «… طراحی دست‌انداز باید به گونه‌ای باشد که از بالا رفتن کودکان و احتمال سقوط آنها … جلوگیری کند.» | Horizontal rails must not be climbable by children. |
| 4-9-9-1-4 | 105 | «استفاده از شیشه ایمن و غیر ریزنده در جان‌پناه‌ها و دست‌اندازهای دارای شیشه … الزامی است.» | Glass in guards must be safety glass. |
| 4-9-9-2-1 | 106 | «ارتفاع میله‌های دستگرد که از لب پله … اندازه‌گیری می‌شود، باید ۰/۹۰ متر باشد. این ارتفاع در تمام طول میلهٔ دستگرد باید به صورت یکنواخت امتداد داشته باشد.» | Handrail 0.90 m above the nosing, constant along the rail. |
| 4-9-9-2-2/3 | 106 | «… باید پیوسته و یکنواخت باشد و به وسیلهٔ هیچ قطعه یا عنصری قطع نشود.» … «… باید حداقل ۰/۳۰ متر به صورت افقی از لبه‌های ابتدا و انتهای شیب‌راه و از بالاترین پیشانی پله ادامه داشته باشد. در پله‌ها، میله دستگرد باید از سمت پایین شیب آن به اندازه عمق یک کف پله بعد از پائین‌ترین پیشانی پله ادامه یابد.» | The grip surface is continuous. General rule: the rail extends 0.30 m past the top nosing and one going past the bottom nosing. Dwellings are exempt under 4-7-1-1-7. |
| 4-9-9-2-4/5 | 106 | «میله دستگرد با مقطع دایره باید دارای قطر خارجی بین ۳۵ تا ۴۰ میلی‌متر باشد … اندازه محیطی آن باید حداقل ۱۰۰ و حداکثر ۱۶۰ میلی‌متر و حداکثر اندازه قطر آن ۵۷ میلی‌متر باشد.» «فاصله آزاد میان یک میله دستگرد و دیوار … باید حداقل ۴۰ میلی‌متر باشد.» | Round rail 35–40 mm. A non-round rail has a perimeter of 100–160 mm and is at most 57 mm across. At least 40 mm clear of the wall. |

**General and residential clauses conflict twice.** On width, the general
clause asks for 1.10 m and the residential one for 0.90 m. On handrails, the
general clause asks for both sides, while the residential one asks for one
side, or none when the stair need not be accessible or rises ≤ 0.70 m. The
general clauses (4-5-1-7-3, 4-5-1-11-3) say they yield «مگر آن‌که در مقررات
اختصاصی تصرفی به‌گونه‌ای دیگر تعیین شده باشد», so for a dwelling the
residential clauses (4-7-1-1-3, 4-7-1-1-7) govern. The width bar for the
house is therefore 0.90 m for a straight stair and **1.10 m once the stair
has a landing or turns**. The handrail minimum is zero or one side,
depending on the question below.

One question decides both the 12-step limit (4-5-1-7-5) and the handrail
minimum (4-7-1-1-7): **is this a stair that "must be accessible" to people
with disabilities?** If no, Mabhas 4 asks for no handrail at all and no
landing limit. If yes, it asks for a rail on at least one side and at most
12 steps between landings. The recommendation in section 6 (rails on both
sides, two flights) does not depend on the answer.

**Does the 12-step limit (4-5-1-7-5) bind a private house?** It can be read
two ways:
- Narrow reading: it binds buildings that must be accessible, which a private
  single-family house in Iran is not.
- Broad reading: it binds any building that is in fact "used by people with
  disabilities or reduced mobility". The brief expects elderly and wheelchair
  users within 20 years.

The lift serves the wheelchair users. The ambulant elderly person, who is the
one at risk on a stair, will still take the stairs. Under either reading the
clause states what Iranian regulation considers a safe flight length for
that user.

### 1.2 Mabhas 3 (Fire protection, 1395 edition)

Source: a scan of the printed edition,
https://dl.civilgeotech.ir/free/library/national-building-regulations/building-codes/mabhas-3/mabhas-03-1395.pdf
[primary]. Printed page = PDF page − 16. Mabhas 4 4-5-1-7-2 makes these
clauses mandatory. 3-6-11-4-1 (p. 115) applies the general exit rules
3-6-2 to 3-6-10 to one- and two-family houses «حسب مورد» ("as relevant").

| Clause | Page | Text (verbatim) | Meaning |
|---|---|---|---|
| 3-6-4-3-2 | 91 | «هر راه‌پله باید دست‌کم ۱۱۰ سانتی‌متر عرض مفید داشته باشد، مگر آن‌که مجموع تعداد متصرفان تمام طبقات استفاده‌کننده از راه‌پله کمتر از ۵۰ نفر باشد، که در آن صورت، عرض مفید را می‌توان به حداقل ۹۰ سانتی‌متر کاهش داد.» | ≥ 1100 mm, or ≥ 900 mm for fewer than 50 occupants (true of this house). |
| 3-6-4-3-3 | 91 | «ارتفاع غیر سرگیر هر راه‌پله … باید دست‌کم ۲۰۵ سانتی‌متر باشد … این حداقل ارتفاع باید به طور پیوسته در بالای راه‌پله تأمین شده باشد و در پایین راه پله، به اندازه یک کف پله جلوتر از پایین‌ترین پله، برقرار باشد.» | Headroom ≥ 2050 mm, held to one going beyond the bottom step. |
| **3-6-4-3-4** | 91 | «هر کف پله باید حداقل ۲۸ سانتی‌متر عمق و حداکثر ۲ درصد شیب داشته باشد. ارتفاع هر پله باید حداقل ۱۰ و حداکثر ۱۸ سانتی‌متر و به گونه‌ای تعیین شود که مجموع اندازهٔ عمق کف پله و دو برابر ارتفاع آن بین ۶۳ و ۶۴ سانتی‌متر باشد.» | **Riser 100–180 mm**, going ≥ 280 mm, 2R+G 630–640 mm. This is the printed source of the 180 mm maximum. |
| 3-6-4-3-5 | 92 | «… رواداری بین اندازهٔ بزرگ‌ترین و کوچک‌ترین ارتفاع، یا میان بزرگ‌ترین و کوچک‌ترین کف پله نباید در هر خیز (بال) پله‌ها بیش از ۱۰ میلی‌متر باشد.» | Within a flight, risers and goings vary by ≤ 10 mm. |
| 3-6-4-3-6 | 92 | Curved stairs: going ≥ 280 mm measured 300 mm from the narrow end, ≥ 250 mm at the narrowest point. | Applies only if winders or curves are used. |
| 3-6-4-3-7 | 92 | Spiral stairs are allowed only inside a dwelling unit or for spaces under 23 m² with ≤ 5 users: width ≥ 650 mm, riser ≤ 240 mm. | Not for a main family stair. |
| 3-6-4-3-8 | 93 | «پلکان‌های واقع در راه خروج باید در هر دو طرف … دارای میله دستگرد … باشند.» | Exit stairs have handrails on both sides. |
| **3-6-4-3-10** | 93 | «حداکثر اختلاف تراز دو سطح افقی متوالی شامل کف هر یک از طبقات و یا پاگردها،که با یک سلسله پلکان پیموده می‌شود، … نباید از ۳۷۰ سانتی‌متر بیشتر باشد، مگر در راه پله‌های قابل دسترس الزامی برای افراد معلول، که باید با ضوابط بخش ۳-۶-۱۰ منطبق باشد.» | **Maximum rise of one flight 3700 mm.** A single 3200 mm flight is legal under Mabhas 3. |

### 1.3 Accessibility regulation (ضوابط و مقررات شهرسازی و معماری برای افراد دارای معلولیت, 3rd edition)

Source: PDF of the 3rd edition, approved by the Supreme Council of Urban
Planning and Architecture on 1398/08/20 (p. 2). Mirror:
https://s34.picofile.com/file/8487306350/Bhrc_Urban_and_Architectural_Design_Criteria_For_People_With_Disabilities_1399_3.zip.html
[primary]. Mabhas 4 4-5-1-8-4 points to it. Printed page = PDF page − 9.

| Clause | Page | Text (verbatim) |
|---|---|---|
| 2-1-5-3 | 50 | «پلکان مستقیم برای استفاده افراد با محدودیت‌های حرکتی مناسب‌تر است.» (a straight stair is better for people with mobility limitations; this is about winders and curves, not landings) |
| 2-1-5-6 | 50 | «حداقل عرض پله باید ۱۲۰ سانتی‌متر باشد.» |
| **2-1-5-7** | 50 | «عرض کف پله باید ۳۰ سانتی‌متر و حداکثر ارتفاع آن ۱۷ سانتی‌متر باشد» |
| **2-1-5-8** | 50 | «حداکثر تعداد پله بین دو پاگرد باید ۱۲ پله باشد.» |
| 2-1-5-9 | 51 | «حداقل ابعاد پاگرد پله باید ۱۲۰×۱۲۰ سانتی‌متر باشد» |
| 2-1-5-10/11 | 51 | Closed risers; nosing projection ≤ 30 mm; nosing radius ≤ 13 mm. |
| 2-1-5-12 | 51 | «نصب میله دستگرد در طرفین پله … الزامی است.» (handrails on both sides) |
| 2-1-11-1/2 | 64 | Handrail diameter 35–40 mm; ≥ 40 mm from a smooth wall. |
| 2-1-11-10 | 66 | «ارتفاع میله دستگرد از کف … پله، باید برای بزرگسالان ۸۵ سانتی‌متر و برای کودکان ۶۰ سانتی‌متر باشد» |
| Fig. 57 | 51 | Handrails run 300 mm past the top and bottom of each flight and continue around the landing. |

Scope: chapter 2 sets architectural design rules. I did not find a clause
that makes it binding for a private single-family house, so applicability is
**not established**. It is the Iranian benchmark for a stair that elderly
people can use. A secondary summary (haftshahraria.com, [secondary]) repeats
the 30/17, 12-step and 1200 mm values.

### 1.4 Checking `rules/iran.yaml` (recommendations only; not edited)

| Rule | Current | Finding | Recommendation |
|---|---|---|---|
| IR4-STAIR-WIDTH 900 | transcribed | Printed 4-7-1-1-3 (p. 85) confirms 0.90 m straight and 1.10 m with a turn or landing. | Keep `transcribed`; add "read from a scan of the printed edition, p. 85" and the mirror URL. With a landing, the check must use 1100. |
| IR4-STAIR-GOING 280 | transcribed | Printed 4-5-1-7-1 (p. 48), and Mabhas 3 3-6-4-3-4 (p. 91). | Keep `transcribed`; add the page and the scan note. |
| IR4-STAIR-2RG 630–640 | transcribed | Printed 4-5-1-7-1 (p. 48), and Mabhas 3 3-6-4-3-4. | Keep `transcribed`; add the page and the scan note. |
| IR4-STAIR-RISE 180 | unverified, "derived" | Mabhas 4 states no riser maximum; **Mabhas 3 3-6-4-3-4 states 180 mm** (minimum 100). | Re-source to Mabhas 3 3-6-4-3-4, p. 91, and raise it to `transcribed`. |
| `iran.md` "Known but not encoded" table | — | It cites the guard and handrail clauses as 4-5-7-1-4, 4-8-9-4, 4-9-9-1. The print has them at 4-5-1-11-1/2 (pp. 50–51), 4-9-9-1-1/2 (p. 105) and 4-9-9-2-1 (p. 106). | Correct the clause numbers. |

Status: the repo kept IR4-PARK-* (read from this same scan) and IR15-* (read
from the same mirror) as `transcribed`. To stay consistent, this research
recommends `transcribed` with the page, not `verified`. Whether a scan of
the printed edition meets the "official edition" bar is the caller's or
owner's decision.
| (new) headroom 2050 | not encoded | Mabhas 4 4-5-1-7-6 (p. 48) and Mabhas 3 3-6-4-3-3 (p. 91). | Encode when the kit can check headroom. |
| (new) landing depth ≥ stair width | not encoded | Mabhas 4 4-5-1-7-4 (p. 48). | Encode. |
| (new) flight rise ≤ 3700 mm | not encoded | Mabhas 3 3-6-4-3-10 (p. 93). | Encode as an error. |
| (new) ≤ 12 steps between landings | not encoded | Mabhas 4 4-5-1-7-5 (p. 48), and accessibility reg. 2-1-5-8. | Encode as a warning, or as an error if the owner adopts it (see section 6). |
| (new) handrail 900 mm, one side minimum | not encoded | Mabhas 4 4-7-1-1-7, 4-9-9-2-1. | Encode when handrails are modelled. |

---

## 2. Comparable codes for dwellings

### 2.1 England: Approved Document K (2013 edition, online version)

Source: https://assets.publishing.service.gov.uk/media/60d5bdcde90e07716f516cfd/Approved_Document_K.pdf
[primary].

- Table 1.1 (p. 5): "Private stair 150 [min rise] 220 [max rise] 220 [min
  going] 300 [max going]". Note 1: "The maximum pitch for a private stair is
  42°." Footnote: "The normal relationship between the dimensions of the rise
  and going is: twice the rise plus the going (2R + G) equals between 550mm
  and 700mm."
- 1.5 (p. 6): "ensuring that the rise and going of each step are consistent
  throughout a flight".
- 1.9 (dwellings, p. 6): open risers only if treads overlap by ≥ 16 mm and "a
  100mm diameter sphere cannot pass through the open risers."
- 1.11 / Diagram 1.3 (p. 7): minimum headroom 2 m.
- **Flight length.** 1.17 (all buildings, p. 9): "If stairs have more than 36
  risers in consecutive flights, make a minimum of one change of direction".
  1.18 (p. 10) limits risers per flight, "utility stairs – 16 risers" and
  "general access stairs – 12 risers, but exceptionally no more than 16", but
  its heading is "**For buildings other than dwellings** and common access
  areas in buildings that contain flats". **A private stair in a house has no
  riser-count limit in AD K.** The "16 risers" figure does not apply to
  houses.
- 1.20 (p. 10): "At the top and bottom of every flight, provide landings the
  width and length at least as great as the smallest width of the flight".
- 1.24 / Diagram 1.8 (dwellings, p. 11): a door may swing across a bottom
  landing only if it leaves "At least 400mm" clear.
- 1.34 (all buildings, p. 14): "Position the top of the handrail 900mm to
  1000mm from the pitch line or floor." "If the stairs are 1000mm or wider:
  provide a handrail on both sides."
- 1.39 (p. 16): where children under five may use the stair, "ensure that a
  100mm sphere cannot pass through any openings in the guarding" and "Prevent
  children from readily being able to climb the guarding."
- 1.41 (dwellings, p. 17): guarding where the drop is more than 600 mm.
  Guard height for single-family dwellings at stairs and landings: "900mm for
  all elements" (Diagram 3.1 table).

### 2.2 England: Approved Document M, volume 1 (M4(2) accessible and adaptable dwellings)

Source: https://assets.publishing.service.gov.uk/media/5a7f8a82ed915d74e622b17b/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf
[primary]. 2.23: "to allow a stair-lift to be fitted … The stair … has a
minimum clear width of 850mm when measured 450mm above the pitch line of the
treads". This is the UK's "ready for old age" provision: a straight stair a
stair-lift can be fitted to.

### 2.3 USA: International Residential Code R311.7 (as adopted in California, CRC 2022)

Source: City of Gilroy, "Residential Stairways, Handrails and Guards"
(revised 03/03/2025), https://cityofgilroy.org/DocumentCenter/View/12314/Residential-Stairs-Handrails-and-Guards-Handout
[secondary: an official municipal summary of the code text]. The ICC text
itself (codes.iccsafe.org) returned 403.

- R311.7.5: "Riser height shall be not more than 7-¾ inches." "Tread depth
  shall be not less than 10 inches." Variation within a flight ≤ 3/8 inch.
- **R311.7.3: "The maximum vertical distance between floor levels or landings
  is 151 inches."** NACHI quotes the 2021 IRC as "12 feet 7 inches (3835 mm
  or 151 inches)" (https://nachi.org/gallery/general-5/stairway-vertical-height-maximum,
  [secondary]). A 3200 mm single flight complies.
- R311.7.6: a landing at the top and bottom; on a straight run "the depth in
  the direction of travel shall be not less than 36 inches."
- R311.7.2: headroom 6 ft 8 in.
- R311.7.8: handrail "on at least one side of each flight of stairs with four
  or more risers", 34–38 inches above the nosing line, continuous for the
  full flight. Circular grip 1-¼ to 2 inches.
- R312.1: openings in guards must not pass "a 4-inch diameter sphere"
  (4-3/8 inch on the open side of stairs).
- Building Code Trainer explains the 151-inch limit as giving "a reasonable
  interval for the user so that they may rest on a level surface"
  (https://buildingcodetrainer.com/?p=466, [secondary]).

### 2.4 Germany: DIN 18065 Gebäudetreppen (2020)

The standard is paywalled and was not read.
- Baunetz Wissen, Podest (https://www.baunetzwissen.de/treppen/fachwissen/treppenelemente/podest-167520)
  [secondary]: for required stairs, "außer in Wohngebäuden mit bis zu zwei
  Wohnungen", a landing must interrupt the flight "nach spätestens 18
  Steigungen". Landing length in houses with up to two dwellings: "80 cm bzw.
  2,5 Auftritte (2,5 x a)". Landings are "Ruhe-, Ausweich- und
  Sicherheitsebenen". **So a single family house is exempt from the
  18-riser rule. The draft's 18 risers sits exactly at the limit that applies
  to every other building.**
- Baunetz Wissen, Auftritt (https://www.baunetzwissen.de/glossar/a/auftritt-3347851)
  [secondary]: houses with up to two dwellings, "mindestens 230 mm, höchstens
  370 mm".
- Maximum riser 200 mm, minimum 140 mm for those houses: heimwerker.de
  (https://www.heimwerker.de/treppe-berechnen/) [weak]. The repo's
  `ergonomics.md` already notes that sources disagree (200 vs 190).
- Baunetz Wissen, Steigungsverhältnis (https://www.baunetzwissen.de/treppen/fachwissen/planungsgrundlagen/steigungsverhaeltnis-167510)
  [secondary]:
  - Schrittmaßregel: 2s + a = 590–650 mm, "die wichtigste".
  - Bequemlichkeitsregel: a − s = 120 mm.
  - Sicherheitsregel: a + s = 460 mm, which concerns "die Sicherheit beim
    Herabsteigen einer Treppe".
  - 170/290 is "sehr angenehm empfunden".
  - Tolerances ±5 mm.

### 2.5 Neufert

Neufert's *Bauentwurfslehre* was not read: **not found** online in primary
form. The 17/29 "comfortable stair" pair and 2R+G = 630 are attributed to it
widely; the closest checked source is Baunetz (2.4) [secondary].

---

## 3. Safety and ageing research

**How big the problem is.**
- Roys, "Serious stair injuries can be prevented by improved stair design",
  *Applied Ergonomics* 2001, PMID 11277505 (BRE) [primary]. For the UK in
  1995: "About 230,000 of these injuries and 497 deaths resulted from falls on
  stairs. When exposure is taken into account, stairs are one of the most
  hazardous locations in buildings. Of these falls, those where the person
  falls forward are most likely to cause severe injuries. … the 'going' …
  can be changed to decrease the potential number of serious trip accidents.
  Builders should therefore be encouraged to build stairs with larger
  goings."
- Blazewick (D. H.) … Smith (G. A.), "Stair-related injuries treated in United States emergency departments", *Am J Emerg Med* 2017,
  NEISS 1990–2012 (https://ajemjournal.com/article/S0735-67571730759-3/fulltext)
  [primary]:
  - The rate was "37.8 injuries per 10,000 United States residents".
  - "the highest injury rates occurred among younger children and older
    adults".
  - "the majority of injuries (61.2%) occurred at home".
  - "Older adult patients more frequently sustained fractures".
  - The authors call for uniform step geometry and "stair rails that allow for
    use of a power grip".
- Startzell et al., "Stair negotiation in older people: a review", *J Am
  Geriatr Soc* 2000, PMID 10811553 [primary]: "Locomotion on stairs is among
  the most challenging and hazardous activities of daily living for older
  individuals … stair falls account for more than 10% of fatal fall
  accidents."

**Riser and going.**
- NIOSH contract report CDC 210-79-0020, *Stairway and Handrail Design for
  Reducing Fall Injuries* (Cohen, Templer, Archea; Templer, Archea, Cohen),
  https://stacks.cdc.gov/view/cdc/179833/cdc_179833_DS1.pdf [primary]:
  - "the safest stairs have an effective riser height not greater than 7
    inches, and an effective tread depth no less than 11 inches."
  - Descent "was associated with 92% of the injuries", and larger nosing
    projections went with higher incident rates.
  - Converted by script, 7 in = 177.8 mm and 11 in = 279.4 mm. **The draft
    (177.8/280) sits exactly on this "7-11" boundary**: it meets the limit
    but has no margin.
- Novak, Komisar, Maki, Fernie, "Age-related differences in dynamic balance
  control during stair descent and effect of varying step geometry",
  *Applied Ergonomics* 2016, PMID 26360219 [primary]. The study tested risers
  of 178, 190 and 203 mm and runs of 203–356 mm with 20 young and 20 older
  adults: "for both age groups, the longer run lengths were found to provide
  the largest margins of stability. In addition, increase in run length and
  decrease in riser height tended to reduce forward upper body tilt."
  **Deeper goings and lower risers are safer on the way down, for old and
  young alike.**
- NBS BSS 120, Archea, Collins, Stahl, *Guidelines for Stair Safety* (1979),
  https://nvlpubs.nist.gov/nistpubs/Legacy/BSS/nbsbuildingscience120.pdf
  [primary], p. 24 (videotape and inventory analysis): the accident rate "was
  not found to be related to the number of risers", and "There was a
  tendency, however, for the least preferred set of dimensions to have a
  greater number of reported incidents."
- John Templer, *The Staircase: Studies of Hazards, Falls, and Safer Design*
  (MIT Press, 1992) [weak: not read; only catalogue descriptions found]. The
  7/11 finding above is from the NIOSH report by Templer and colleagues.

**How far you can fall, and landings.**
- Hörauf et al., "Injury Patterns after Falling down Stairs", *J Clin Med*
  2022;11:697, https://pmc.ncbi.nlm.nih.gov/articles/PMC8836855/ [primary],
  118 trauma patients:
  - "More than 80% of patients suffered a traumatic brain injury, which
    increased as a function of the number of stairs fallen."
  - "As the height of the fall increases, severe traumatic brain injury
    should be anticipated."
  - Caution: their own tables show these trends are not statistically
    significant (TBI p = 0.338, ISS p = 0.468). Only subdural haemorrhage
    (p = 0.024) and fractures (p = 0.015) were.
  - "the patients who suffered from domestic falls were older".
- A pediatric study summarised by Cincinnati Children's found "no correlation
  between severity of injury and number of steps fallen down"
  (https://www.cincinnatichildrens.org/service/m/mayerson-center/hcp/clinical/falls/stairway)
  [secondary].
- **Not found:** a study that directly tests whether an intermediate landing
  reduces injury severity. What exists is the code reasoning (rest, "Ruhe-,
  Ausweich- und Sicherheitsebenen") and the weak trend above.

**Handrails.**
- NBS BSS 120 §2.3.1 (p. 56) [primary]: handrails serve "(1) to slide a hand
  while monitoring one's progress and stability, (2) to use as a pivot at
  corners or doglegs, (3) to provide support for an elderly or infirm user,
  and (4) to grab onto for support in the event of an accident … the
  handrails should be continuous on the inside of 90° or 180° landings, and
  should be graspable at any point". Its figure caption: "continuous handrails
  (preferably 2)".
- NIOSH report above [primary]: incident treads were associated with "less
  handrail-to-handrail width".
- Komisar & Novak, *Human Factors* 2021, https://pmc.ncbi.nlm.nih.gov/articles/PMC9969491
  [primary]: "Higher handrails (up to 42 inches) may be advantageous for trunk
  control when recovering from destabilizations during gait". 42 in is
  1066.8 mm by script. This was a level-walking study, not stairs, so it
  supports staying at the upper end of the allowed handrail heights rather
  than setting one.

**Nosing visibility, lighting, glare, views.**
- Foster et al., "Safety on stairs: influence of a tread edge highlighter and
  its position", *Exp Gerontol* 2014, PMID 24768822 [primary]: "stairs with
  high-contrast edge highlighters positioned flush with the tread edge will
  improve safety on stairs, particularly for those with age-related visual
  impairment". A highlighter set back 30 mm made things worse. AD K 1.7 asks
  for a 55 mm contrasting nosing in non-dwellings [primary].
- NBS BSS 120 §2.4.9 (p. 76) [primary]: "switches should be provided at every
  point of entry to or exit from the stairway. No stair user should have to
  traverse a stair in the dark", reachable "at least 1 stride before the
  first riser".
- NBS BSS 120 §2.2.4 (p. 54) [primary], quoting Hopkinson and Kay: "Under
  daylighting conditions, glare results from a very bright sky seen through a
  large window." Over (1966) is cited on the hypothesis that elderly falls
  follow "false interpretation of visual information".
- **NBS BSS 120 §2.5.2 (p. 79) [primary], abrupt changes in view.** An
  "orientation edge" where a view suddenly opens "at the top or bottom of the
  flight" draws the eye away from the treads. The remedy is to make
  "the level of illumination on the stair treads and handrails exceeds the
  levels found in surrounding areas", or to "extend or reduce the opening so
  that its edge is farther from the extreme ends of the flight". The
  commentary: "An important factor in successful stair use involves looking
  down at the stair treads from at least one stride away from the first riser
  until the completion of the first step". **This bears directly on the
  owner's "window in front of you when you go down"**: a view is fine, but not
  as a sudden reveal at the top step, and not as bright sky in the line of
  sight on the way down.

**Children, open risers, winders, single steps, slip.**
- AD K 1.9 and 1.39 [primary]: 100 mm sphere through open risers and guards;
  guards hard to climb. Riley, Roys, Cayless 1998, PMID 10076694 (BRE)
  [primary]: "the majority of children aged between four and six years can
  climb onto or over stair guarding unassisted". The family has four
  children, so use vertical infill or solid or glass guards, never horizontal
  rails (also Mabhas 4 4-9-9-1-3).
- Mabhas 4 4-9-9-1-2 [primary]: gaps ≤ 110 mm (already in `iran.md` as
  0.11 m). The UK uses 100 mm (AD K 1.39), the US 4 in, which is 101.6 mm by
  script.
- Winders: Mabhas 3 3-6-4-3-6 requires a 280 mm going 300 mm from the narrow
  end [primary]. The Iranian accessibility regulation 2-1-5-3 prefers
  straight flights for mobility-impaired users [primary]. A U-stair with a
  flat half landing has no winders and meets both.
- Single steps: AD K 1.18a "Do not have single steps" (non-dwellings)
  [primary]. NBS BSS 120 §2.5.6 asks for accentuation of single steps and
  2-riser stairs [primary].
- Slip: Mabhas 4 4-5-1-12-1 «غیرلغزنده» [primary]. NBS BSS 120 p. 24 found
  no correlation between ordinary tread materials and accident rates, but
  warns about very low or very high friction [primary]. Avoid polished stone
  treads.

---

## 4. Configuration comparison for one 3200 mm storey

Numbers come from the scripts, which compute the footprint of the flights
and the intermediate landing. Floor landings at the top and bottom are part
of the floors and not counted. Where a landing exists its depth equals the
flight width (Mabhas 4 4-5-1-7-4).

The width used is the clear (useful) width of each flight, «عرض مفید», between
finished walls or guards. Handrails are assumed to project into it, as the
US code allows (R311.7.1). If the rails must sit outside the clear width,
add their projection (≥ 40 mm wall gap + 35–40 mm rail, 4-9-9-2-4/5) on
each side. The U widths of 2200 and 2400 are two flights with no wall
between them. A wall or well adds its thickness.

Condensed from the `stairs.py` output (raw output in the appendix), allowed goings per riser count with 630 ≤ 2R+G ≤ 640 and G ≥ 280:

```
n=17 risers  R= 188.24  goings allowed: (none)
n=18 risers  R= 177.78  goings allowed: 280.0..284.4
n=19 risers  R= 168.42  goings allowed: 293.2..303.2
n=20 risers  R= 160.00  goings allowed: 310.0..320.0
n=21 risers  R= 152.38  goings allowed: 325.2..335.2
```

So under Mabhas 4, 18 risers allow only 280–284 mm goings. **19 risers is the
first count that permits the 300 mm going of the accessibility regulation.**

Condensed from the `stairs.py` and `stairs2.py` output (raw output in the appendix), footprints:

```
18 risers R=177.78 G=280 2R+G=635.6 pitch=32.4 deg; flights 9+9, landing at +1600 mm
   straight single flight, width 1100: length 4760, area 5.24 m2
   straight with mid landing, width 1100: length 5580, area 6.14 m2
   L, quarter landing 1100x1100: legs 3340 x 3340
   U, half landing 1100: length 3340 x width 2200 (no well) / 2400 (200 well); area 7.35 m2
19 risers R=168.42 G=300 2R+G=636.8 pitch=29.3 deg; flights 10+9, landing at +1684 mm
   straight single flight, width 1100: length 5400, area 5.94 m2
   straight with mid landing, width 1100: length 6200, area 6.82 m2
   L, quarter landing 1100x1100: legs 3500 x 3800
   U, half landing 1100: length 3800 x width 2200 (no well) / 2400 (200 well); area 8.36 m2
   U, flight width 1200, half landing 1200: length 3900 x width 2400 (no well); area 9.36 m2
```

| | Straight, one flight (draft) | Straight with mid landing | L, quarter landing | U / dog-leg, half landing |
|---|---|---|---|---|
| Longest uninterrupted flight | 18–19 risers, full 3200 mm | 9–10 risers | 9–10 risers | 9–10 risers |
| Iranian 12-step limit (4-5-1-7-5; access. reg. 2-1-5-8) | **fails** | passes | passes | passes |
| Mabhas 3 flight rise ≤ 3700 | passes | passes | passes | passes |
| Minimum width (4-7-1-1-3) | 900 | 1100 | 1100 | 1100 |
| Footprint (18 R / 19 R, above) | smallest: 4760 / 5400 long | longest: 5580 / 6200 long | two 3.3–3.8 m legs | most compact: 3340 / 3800 x 2200 |
| Stacking over 3 levels | Arrivals at opposite ends on each floor: needs circulation at both ends, or flights alternating in direction | Same problem, and longer | Spirals around a square core | **Start and finish on the same side; stacks directly over itself, and a lift fits beside the arrival side** |
| Rest, and a pivot for the hand | none | landing only | landing; the turn is a pivot point (NBS §2.3.1) | landing plus a 180° turn with a continuous inner rail |
| Daylight and view | One window at the low end faces the descending user for the whole flight: view, but also glare (NBS §2.2.4) | A landing window is possible on the side | A window on the outer corner of the landing | **Landing on an outer wall: a window directly in front of the user on the first flight down, at mid-height (≈1.6–1.7 m above the floor below), so the view appears mid-stair, not as a sudden reveal at the top step (NBS §2.5.2)** |
| Stair-lift later (AD M 2.23) | easiest (straight rail) | easy | curved rail | curved rail (the lift makes this moot) |
| Carrying furniture | easy | easy | the turn limits long items | the turn limits long items; a 1100–1200 landing is tight for a sofa |
| Cost (structure) | one long slab or stringer | longer, plus a landing | two short flights plus a landing | two short flights plus a landing; the shorter spans are easier in a concrete frame |

On cost I found no source with prices: **not found**. The row above states
only the obvious difference in parts.

**The garage end of the stack.** Mabhas 3 §3-11-3 (light-vehicle parking,
pp. 196–197) [primary]:
- 3-11-3-2: «شیب‌راه‌های اتومبیل روی پارکینگ نباید به عنوان راه خروج یا قسمتی از آن در نظر گرفته شود.»
  The car ramp is not an exit route.
- 3-11-3-5: «جداسازی پارکینگ از سایرتصرف‌ها باید مطابق با الزامات جدول ۳-۲-۳ صورت گیرد.»
  Table 3-2-3 was **not read**, so the required fire rating between the
  garage and the stair is open.
- 3-11-3-6: «ایجاد بازشوی مستقیم از پارکینگ به اتاقی که برای خوابیدن استفاده شود، مجاز نیست» …
  otherwise a vestibule with one-hour walls «حداقل ۱/۲۰ در ۱/۲۰ متر».

The garage may open to the stair hall, not to a bedroom. A 1200 x 1200
lobby between the garage and the stair or lift would satisfy the vestibule
dimension and keep fumes out of the stair. For the fire rating, read Table
3-2-3 next.

**The draft's problem is the missing landing, not its riser and going.**
177.8/280 meets every code read, but it sits at the edge of each one:
- the maximum riser in Mabhas 3 (180) and the NIOSH 7-11 safe-stair
  boundary;
- the minimum going in Mabhas 4 and Mabhas 3 (280);
- the 18-riser landing trigger of DIN 18065 for every building except small
  houses.

It fails the 17 cm and 30 cm values of the accessibility regulation and the
12-step limit of both Iranian texts.

---

## 5. Design quality: the stair as an experience

- Alexander et al., *A Pattern Language* (1977), pattern 133 "Staircase as a
  Stage", transcription at https://www.iwritewordsgood.com/apl/patterns/apl133.htm
  [secondary]: "A staircase is not just a way of getting from one floor to
  another. The stair is itself a space, a volume, a part of the building …
  Treat the whole staircase as a room … Flare out the bottom of the stair
  with open windows or balustrades and with wide-steps".
- Width for two people: dimensions.com (https://www.dimensions.com/element/straight-stairs)
  [secondary]: "Comfortable two person stair widths range between 49” (125
  cm) to 60” (152 cm)", and a single-user private stair "a minimum of 36” (91
  cm)". The accessibility regulation asks for 1200 mm (2-1-5-6) [primary].
  1100 lets an adult pass a child or help an elderly parent. 1200 meets the
  accessibility value and comes close to the "two people" comfort range.
- Daylight: Mabhas 4 sets 0.90 m² of glazing per floor as the minimum for a
  naturally lit stair (4-5-1-10-2), and a rooflight is acceptable
  (4-5-1-10-3) [primary]. NBS BSS 120 [primary] adds what keeps a beautiful
  stair safe:
  - treads lit brighter than their surroundings;
  - no bright sky in the line of sight at the top step;
  - low-gloss treads, so window light does not reflect as glare;
  - switches at every end.
- What "feels good" in the evidence:
  - a lower riser and a deeper going (Novak 2016; Roys 2001; Baunetz 170/290);
  - a flight short enough to see its end;
  - a landing to pause on (DIN's "Ruhe-… ebenen");
  - a continuous, graspable rail on both sides (NBS §2.3.1; Blazewick's
    "power grip");
  - visible nosings (Foster 2014).

---

## 6. Recommendation for this house

Each item cites its source above. This is a design recommendation, not a
rule change. `rules/iran.yaml` was not edited.

1. **Riser/going: 19 risers of 168.4 mm with a 300 mm going** (script: 2R+G =
   636.8, pitch 29.3°). This pair:
   - meets Mabhas 4 4-5-1-7-1 (G ≥ 280, 630–640) and Mabhas 3 3-6-4-3-4
     (R ≤ 180);
   - meets the accessibility regulation 2-1-5-7 (G = 300, R ≤ 170);
   - is inside the NIOSH "7-11" safe zone with margin, instead of on its
     boundary;
   - follows Novak 2016 and Roys 2001 (deeper going, lower riser).

   18 risers cannot take a 300 mm going under Mabhas 4 (script: 280–284
   only), so it cannot meet the accessibility values.
2. **Flights and landings: two flights per storey, 10 + 9 risers, with one
   intermediate landing** at about +1684 mm (script). This meets the 12-step
   limit (Mabhas 4 4-5-1-7-5; accessibility reg. 2-1-5-8) under either
   reading, and halves the longest possible uninterrupted fall (Hörauf 2022,
   weak trend). Landing depth ≥ flight width (Mabhas 4 4-5-1-7-4), and
   1200 x 1200 if the accessibility value is adopted (2-1-5-9).
3. **Configuration: a U (dog-leg) stair with a flat half landing, no
   winders, stacked over the three levels, with the lift beside the arrival
   side.**
   - Footprint (script): 3800 x 2200 for 1100 flights, or 3900 x 2400 for
     1200 flights, plus a 200 mm well if wanted.
   - Why U: start and finish on the same side make it stack. It is the most
     compact form with a landing. The 180° turn gives the hand a pivot on a
     continuous inner rail (NBS §2.3.1). And it places the landing on an
     outer wall.
   - The straight-with-landing alternative is 6200 long (script) and puts
     arrivals at opposite ends of each floor.
4. **Width: 1100 mm minimum** (Mabhas 4 4-7-1-1-3: required once there is a
   landing). **1200 mm preferred**: accessibility reg. 2-1-5-6, and closer to
   the 1250 "two people" comfort width (dimensions.com).
5. **Handrails on both sides**, continuous, including around the inner side
   of the landing, with no newel interruptions:
   - sources: accessibility reg. 2-1-5-12; Mabhas 4 general rule 4-5-1-11-3;
     AD K 1.34c for stairs ≥ 1000 wide; NBS §2.3.1. The residential minimum
     of one side (4-7-1-1-7) is not enough for an ageing household.
   - height 900 mm above the nosing line (Mabhas 4 4-9-9-2-1). The
     accessibility regulation 2-1-11-10 gives 850 mm for adults. This
     research uses 900 because it is the binding Mabhas 4 value, it sits
     inside AD K's 900–1000, and the balance-recovery evidence favours
     higher rails, not lower (Komisar & Novak 2021).
   - round, 35–40 mm (4-9-9-2-4), ≥ 40 mm from the wall (4-9-9-2-5).
   - optionally a second rail at 600 mm for the children (accessibility reg.
     2-1-11-10).
6. **Guards and children:** vertical infill or solid or safety-glass guards
   (4-9-9-1-4), gaps ≤ 110 mm (4-9-9-1-2), nothing climbable (4-9-9-1-3;
   Riley 1998). Guard 1100 at landings and floor edges and 900 above the
   nosing line (4-9-9-1-1). Closed risers (accessibility reg. 2-1-5-10; AD K
   1.9 if open: 100 mm sphere).
7. **Treads:** non-slip and not polished (4-5-1-12-1); one material and
   colour (4-5-1-12-2); nosing radius ≤ 13 mm (4-5-1-12-3), projection ≤ 30 mm
   (2-1-5-10); a high-contrast nosing strip flush with the edge (Foster
   2014).
8. **Light and view:**
   - Put the half landing on the **east facade**, with a window in front of
     the user on the first flight down. That is the owner's "in front of you,
     a window".
   - The window counts toward the 0.90 m² per floor (4-5-1-10-2).
   - Keep its top step and the floor openings away from sudden reveals, and
     light the treads brighter than the surroundings (NBS §2.5.2).
   - Expect low morning sun from the east: low-gloss treads and a
     shading/diffusing option (NBS §2.2.4).
   - If the sill is low and the drop outside exceeds 0.70 m, the window needs
     a guard or safety glazing (4-5-1-11-1, 4-9-9-1-4).
   - Switches at both ends of every flight, reachable a stride before the
     first riser (NBS §2.4.9).
   - Headroom ≥ 2050 everywhere, including under the upper flight at the
     landing (4-5-1-7-6; Mabhas 3 3-6-4-3-3).
9. **Open items for the owner:**
   - whether to adopt the accessibility values (1200 width, 17/30, 12 steps)
     as the house standard; this research recommends yes;
   - whether the stair sits on the east facade.

   Neither changes the brief. Both are design choices.

Nothing here is permit-ready: the stair geometry, its structure and its
guards need review and signature by a licensed engineer (مهندس دارای پروانه
اشتغال، نظام مهندسی).

---

## Appendix: scripts and raw output

### stairs.py

```python
# Stair arithmetic for H = 3200 mm floor-to-floor. Run: python3 -I stairs.py
H = 3200; W = 1100
for n in range(17, 22):
    r = H / n
    gmin = max(280, 630 - 2*r); gmax = 640 - 2*r
    print(f"n={n:2d} risers  R={r:7.2f}  goings allowed by 630<=2R+G<=640 & G>=280: "
          f"{gmin:6.1f}..{gmax:6.1f}" + ("  (none)" if gmin > gmax else ""))
print()
def runs(n, g):
    t = n - 1  # treads in a single straight flight (top floor acts as last tread)
    out = {}
    out["straight, 1 flight"] = (t*g, None)
    # straight with one mid landing of depth W: flights n1 + n2 = n, treads (n1-1)+(n2-1)
    out["straight, 1 mid landing (depth 1100)"] = ((n-2)*g + W, None)
    # L with quarter landing W x W: two flights at right angles
    a = (n//2 - 1)*g; b = (n - n//2 - 1)*g
    out["L, quarter landing 1100x1100 (legs)"] = (a + W, b + W)
    # U / dog-leg, half landing depth W, two flights side by side, width 2W (+ well 0)
    out["U, half landing, no well (length x width)"] = (max(a, b) + W, 2*W)
    out["U, half landing, 200 well (length x width)"] = (max(a, b) + W, 2*W + 200)
    return out
for n, g in [(18, 280), (18, 285), (19, 290), (19, 300), (20, 300)]:
    r = H / n
    print(f"--- {n} risers of {r:.2f}, going {g}, 2R+G = {2*r+g:.1f}, pitch = "
          f"{__import__('math').degrees(__import__('math').atan(r/g)):.1f} deg")
    for k, (x, y) in runs(n, g).items():
        print(f"   {k:45s} {x:6.0f}" + (f" x {y:6.0f}" if y else ""))
    # longest uninterrupted fall: risers in the longest flight
    print(f"   longest flight risers: straight {n}, landing/L/U {n - n//2} (= {(n-n//2)*r:.0f} mm vertical)")
```

Raw output:

```
n=17 risers  R= 188.24  goings allowed by 630<=2R+G<=640 & G>=280:  280.0.. 263.5  (none)
n=18 risers  R= 177.78  goings allowed by 630<=2R+G<=640 & G>=280:  280.0.. 284.4
n=19 risers  R= 168.42  goings allowed by 630<=2R+G<=640 & G>=280:  293.2.. 303.2
n=20 risers  R= 160.00  goings allowed by 630<=2R+G<=640 & G>=280:  310.0.. 320.0
n=21 risers  R= 152.38  goings allowed by 630<=2R+G<=640 & G>=280:  325.2.. 335.2

--- 18 risers of 177.78, going 280, 2R+G = 635.6, pitch = 32.4 deg
   straight, 1 flight                              4760
   straight, 1 mid landing (depth 1100)            5580
   L, quarter landing 1100x1100 (legs)             3340 x   3340
   U, half landing, no well (length x width)       3340 x   2200
   U, half landing, 200 well (length x width)      3340 x   2400
   longest flight risers: straight 18, landing/L/U 9 (= 1600 mm vertical)
--- 18 risers of 177.78, going 285, 2R+G = 640.6, pitch = 32.0 deg
   straight, 1 flight                              4845
   straight, 1 mid landing (depth 1100)            5660
   L, quarter landing 1100x1100 (legs)             3380 x   3380
   U, half landing, no well (length x width)       3380 x   2200
   U, half landing, 200 well (length x width)      3380 x   2400
   longest flight risers: straight 18, landing/L/U 9 (= 1600 mm vertical)
--- 19 risers of 168.42, going 290, 2R+G = 626.8, pitch = 30.1 deg
   straight, 1 flight                              5220
   straight, 1 mid landing (depth 1100)            6030
   L, quarter landing 1100x1100 (legs)             3420 x   3710
   U, half landing, no well (length x width)       3710 x   2200
   U, half landing, 200 well (length x width)      3710 x   2400
   longest flight risers: straight 19, landing/L/U 10 (= 1684 mm vertical)
--- 19 risers of 168.42, going 300, 2R+G = 636.8, pitch = 29.3 deg
   straight, 1 flight                              5400
   straight, 1 mid landing (depth 1100)            6200
   L, quarter landing 1100x1100 (legs)             3500 x   3800
   U, half landing, no well (length x width)       3800 x   2200
   U, half landing, 200 well (length x width)      3800 x   2400
   longest flight risers: straight 19, landing/L/U 10 (= 1684 mm vertical)
--- 20 risers of 160.00, going 300, 2R+G = 620.0, pitch = 28.1 deg
   straight, 1 flight                              5700
   straight, 1 mid landing (depth 1100)            6500
   L, quarter landing 1100x1100 (legs)             3800 x   3800
   U, half landing, no well (length x width)       3800 x   2200
   U, half landing, 200 well (length x width)      3800 x   2400
   longest flight risers: straight 20, landing/L/U 10 (= 1600 mm vertical)
```

### stairs2.py

```python
# U / dog-leg stair footprints for H=3200, landing depth = stair width (Mabhas 4 4-5-1-7-4) or 1200 (accessibility reg 2-1-5-9)
import math
H = 3200
for n, g in [(18, 280), (19, 300)]:
    r = H / n
    f1 = (n + 1) // 2; f2 = n - f1          # risers per flight
    t1, t2 = f1 - 1, f2 - 1                  # treads per flight (landing/floor is the last "tread")
    print(f"{n} risers R={r:.2f} G={g} 2R+G={2*r+g:.1f} pitch={math.degrees(math.atan(r/g)):.1f} deg; "
          f"flights {f1}+{f2} risers, landing at +{f1*r:.0f} mm; treads {t1}+{t2}")
    for w, land in [(1100, 1100), (1200, 1200)]:
        L = max(t1, t2) * g + land
        print(f"   U, flight width {w}, half landing {land}: length {L} x width {2*w} (no well) / {2*w+200} (200 well); "
              f"area {L*2*w/1e6:.2f} m2 (no well)")
        S = (n - 2) * g + land
        print(f"   straight with mid landing, width {w}: length {S}, area {S*w/1e6:.2f} m2")
    S1 = (n - 1) * g
    print(f"   straight single flight, width 1100: length {S1}, area {S1*1100/1e6:.2f} m2")
```

Raw output:

```
18 risers R=177.78 G=280 2R+G=635.6 pitch=32.4 deg; flights 9+9 risers, landing at +1600 mm; treads 8+8
   U, flight width 1100, half landing 1100: length 3340 x width 2200 (no well) / 2400 (200 well); area 7.35 m2 (no well)
   straight with mid landing, width 1100: length 5580, area 6.14 m2
   U, flight width 1200, half landing 1200: length 3440 x width 2400 (no well) / 2600 (200 well); area 8.26 m2 (no well)
   straight with mid landing, width 1200: length 5680, area 6.82 m2
   straight single flight, width 1100: length 4760, area 5.24 m2
19 risers R=168.42 G=300 2R+G=636.8 pitch=29.3 deg; flights 10+9 risers, landing at +1684 mm; treads 9+8
   U, flight width 1100, half landing 1100: length 3800 x width 2200 (no well) / 2400 (200 well); area 8.36 m2 (no well)
   straight with mid landing, width 1100: length 6200, area 6.82 m2
   U, flight width 1200, half landing 1200: length 3900 x width 2400 (no well) / 2600 (200 well); area 9.36 m2 (no well)
   straight with mid landing, width 1200: length 6300, area 7.56 m2
   straight single flight, width 1100: length 5400, area 5.94 m2
```

Inch conversions (`x * 25.4`): 7 in = 177.8 mm, 11 in = 279.4 mm, 42 in = 1066.8 mm, 4 in = 101.6 mm.
