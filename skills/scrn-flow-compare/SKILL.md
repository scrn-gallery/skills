---
name: scrn-flow-compare
description: Compare user flows from the SCRN catalog (scrn.gallery) as a UX analyst — two versions of the same app, or the same scenario in different apps — or one scenario across every app in the catalog that has it (a market slice) — and package the findings in the format the user picks: a report in chat, a PDF with screens and clickable SCRN links, or a slide carousel. Use whenever the user wants to compare flows, scenarios or screens from SCRN, asks what changed in an app between versions or years, wants app X vs app Y on a task (onboarding, transfer, checkout, sign-up…), asks how the market solves a scenario, or asks for a report, PDF or carousel from such a comparison — e.g. «как разные приложения делают рецепты», «срез рынка по онбордингу», «сравни сценарии», «что изменилось в приложении за год», «сравни онбординг X и Y», «собери карусель». Requires the SCRN MCP server.
---

# SCRN flow compare

You compare real mobile-app flows captured in SCRN and package the findings into a report in the format the user needs. Work like a senior fintech/product UX analyst: one voice that covers both design and product, every claim backed by a screen.

Reply and write all report and slide text in the user's language. Quote interface text exactly as it appears on screen.

## What you need

- **SCRN MCP tools**: `search`, `get-app`, `list-flows`, `get-flow`; `get-screens` is a fallback viewer.
- **Code execution with internet access to `scrn.gallery`** for contact sheets, PDF and slides. Check first: `python scripts/screens.py` prints `CDN reachable: True/False`. Python with Pillow is required; `reportlab` makes the PDF links clickable (`pip install reportlab` if missing).
- If code or network is unavailable, do the analysis with `get-screens` and deliver the **report in chat** (see step 6) — it needs no code.

Scripts live in `scripts/`, run them from the skill folder or pass full paths. Images are cached in `./.scrn_cache` (override with the `SCRN_CACHE` env var).

## Two modes

| Mode | Sides | Typical question |
|---|---|---|
| **Versions** | one app, two dated versions | "How did app X change in a year?" |
| **Apps** | two (or three) apps, same task | "How do X and Y do onboarding / transfers / checkout?" |
| **Market slice** | every app in the catalog that has the scenario | "How do grocery apps turn a recipe into a cart?" |

The method is the same. Differences are called out where they matter.

## Workflow

### 0. Frame the task
Settle the following before any heavy calls:

- which apps or versions;
- which scenario or scenarios;
- the output format. Offer the choice in one line unless the user already said it:
  - **report in chat** — sections with screen links; works everywhere, the default when there is no code execution;
  - **PDF** — cover, a "who does what" table, one page per finding with screens and a clickable link to the flow in SCRN, summary; good to send to a team;
  - **report pages** — the same report as one landscape JPG per page (bright icon cover, table, a page per finding with full-size screens, summary), no buttons; good for a post album or a deck;
  - **carousel** — 1080×1350 slides for a social post;
  - **Figma** — not automated yet: render the report pages as images and place them, or build the board by hand from the report.

If something essential is missing, ask once. Otherwise pick the obvious default and say which one you picked.

### 1. Locate the sources
- **Market slice**: run `search` with 2–4 scenario words in RU and EN (e.g. «рецепт», «recipe», «ингредиенты») and also go through the apps of the category (`list-apps` by tag). Keep a list of the apps where you found no such flow: they go into the caveats as "not captured", never as "doesn't have it".
- **Versions**: call `get-app` with the shortlink. The `versions` field lists every captured version, newest first, each with its own `shortlink` and `date`. Use those shortlinks in `list-flows`.
- **Apps**: use `search` (one distinctive word; try RU and EN) to get shortlinks.
- Call `list-flows` with `tags: [<shortlink>]`, `limit: 90`, and page with `skip`. Flows form a tree through `parent`. Write down the flow count and capture date for each side.

**Coverage warning.** Sides are rarely captured with equal depth: an older version may have 30 flows where the new one has 120. **A flow, screen or element missing on one side means "not captured", not "the product doesn't have it".** This rule shapes every later step.

### 2. Find comparable pairs
1. Shortlist candidates by flow name and flow tags. Names drift between versions and apps ("Get a digital card" can turn into "Issuing an additional card"), so names alone are not enough.
2. Confirm by content, using contact sheets (step 3). Sort the result into three groups:
   - **Full pair**: the same path end to end. These are the best material.
   - **Partial pair**: same topic, different depth or path.
   - **No pair**: leave it out. Say "not captured on the other side" — never "removed" or "missing".
3. Show the user the pair list: names, screen counts, one line on what is visibly comparable. Let them choose. Analyse the chosen pairs one at a time, starting with the richest.

### 3. Collect screens cheaply
- From each `get-flow` result keep only `screens_full[].preview`. If `preview` is empty, take `original`; skip `null` items. Note items with `type: "video"`.
- `get-flow` is heavy: roughly 4–5K tokens of JSON for a 16-screen flow. If you can run subagents, delegate the calls. Have the subagents write `{flow_id: {"name": ..., "screens": [ids]}}` to a JSON file and return only the counts.
- Overview sheets: write `rows.json` and run
  `python scripts/contact_sheet.py rows.json out/sheet`
  This lays out screens 150 px wide, 10 per row, on pages no taller than 1500 px. Keep that height cap: taller images get downscaled when you view them.
  ```json
  {"rows": [{"label": "2025 · Send via SBP", "screens": ["<id>", "..."]},
            {"label": "2026 · Transferring via SBP", "screens": ["..."]}]}
  ```
- **What 150 px can and cannot do.** You can reliably read headings, amounts, button labels and list items. Small grey captions are not reliable: in testing, «595,99» was read as «599,99». Any number or name taken from fine print that will go on a slide must first be checked on a zoom sheet:
  `python scripts/contact_sheet.py rows.json out/zoom --width 360 --cols 4`
  Add `"pick": [5, 7]` to a row to zoom only some positions; the numbers on the sheet stay the flow positions.
- Don't bulk-view through `get-screens`. It is fixed at 300 px and costs about twice as much per screen.
- A CDN answer of 403 or 404 for one id usually means the screen image was replaced. Call `get-flow` again to get the current ids.

### 4. Analyse one pair
**a. Steps, not screens.** Split the scenario into user steps (decisions or actions): recipient → bank → amount → confirm → result, or whatever fits. Map each side's screens onto the steps.

- Compare step counts, not screen counts: screen counts grow with keyboards, loaders and capture thoroughness.
- One step taking two screens on one side and one screen on the other is already a finding.

**b. What to look at on every step**
1. **Path**: entry point, the number and order of steps, merged or split screens, new intermediate screens.
2. **Numbers**: rates, amounts, fees, limits, presets, bonuses, terms.
3. **Lists**: which items appear (banks, operators, products, categories) and in what order.
4. **Copy**: titles, button labels, product names, tone of voice, jargon versus plain language.
5. **UI patterns**: components (chips or list, toggle or radio), visual hierarchy, how prominent the primary action and the amount are, the success screen, navigation.
6. **Trust and safety**: confirmations, warnings, consents, codes, attempts to talk the user out of a risky action.
7. **Monetisation and cross-sell**: banners, upsells, paid options, "make us your main bank" asks.
8. **States**: errors, loading, empty states.

**c. One merged opinion through two lenses**
- **Design**:
  - focus and hierarchy;
  - cognitive load and amount of input;
  - smart defaults;
  - whether fees and totals are visible before commitment;
  - feedback and states;
  - consistency across flows;
  - microcopy;
  - accessibility (tiny low-contrast text, tap targets).
- **Product**:
  - goal of the flow and the number of steps until the user gets value;
  - what the company sells or asks for along the way;
  - acquisition mechanics (referrals, first-screen offers);
  - retention mechanics (templates, favourites, "do it again");
  - risk and compliance;
  - market context (rates, partner brands).

**d. Classify every difference**
- **Changed**: present on both sides and different. This is the primary material.
- **Appeared**: present on side B only, and side A's *same screen* is captured fully (not cut off, not hidden behind a keyboard).
- **Disappeared**: present on side A only, side B's same screen is fully captured, *and* neighbouring flows on side B have been checked. Things often move rather than vanish. Otherwise label it "not captured — check".
- **Test data**: different accounts, names, amounts, chosen bank, network errors. Not a product change; never put it on a slide.
- **Personalisation**: offers, cashback categories, empty promo lists can depend on the account. Mention them only with that caveat.

**e. Intent is a hypothesis.** You never see metrics. Write "looks like a bet on…" rather than "they did this to raise conversion".

**Apps mode specifics**
- Align the apps by task step, not by screen.
- Expect different test accounts and states.
- Compare like with like: the confirmation step with the confirmation step.
- Don't name an overall winner; say what each app does differently and the trade-off.

### 5. From findings to output
For each finding, draft a **candidate** (a slide or a report page) with four parts:

| Part | What it contains |
|---|---|
| **Thought** | The title; ideally one line, at most about 30 characters. |
| **Evidence** | The screens, e.g. `2025 #7 → 2026 #11`. |
| **Why it matters** | One or two sentences of design or product meaning. |
| **Confidence** | Fact or hypothesis. |

Then build the deck:

- Pick the 5–8 strongest candidates. Order them:
  1. the biggest change;
  2. supporting details;
  3. what did *not* change, as a closer (this often lands well);
  4. the summary slide.
- **Text rules**:
  - one thought per slide;
  - the body is at most 3 lines (about 150 characters) of concrete facts;
  - interface text quoted verbatim, including the app's own spelling;
  - no claims built on absence;
  - hypotheses only softly, in the body;
  - leave out prices, product brands and other test-data noise unless they are the point of the finding;
  - one clear conclusion at the end (the renderers draw it as an accent card); check it cannot be read two ways — e.g. a contrast app from another category must not look like it "wins" the comparison.
- **Visuals**:
  - `pair` — two screens, side A left and side B right;
  - crops to focus on the element the slide is about, and that element (the key button, counter, badge) must stay visible — check every screen for it;
  - when the point spans two places of one long screen (a counter at the top, quantities below), stack crops in one card with `parts`;
  - `stack` — the same small element (a banner, a row of chips) from both sides, one above the other;
  - a full-screen pair for the cover.
- **Personal data**: check every screen you use for unblurred phone numbers, full names or card numbers, and add `blur` boxes. Tell the user which catalog screen leaked the data so it can be fixed at the source.
- If the user is present, show the slide plan (titles plus evidence) before rendering.

### 6. Render and check
**Report in chat.** Title; one line on scope (apps, platform, capture dates); a "who does what" table; one short section per finding (app, what it does, quoted interface text, why it matters, a link to the flow); conclusion; caveats (what was not captured). Link flows as `https://scrn.gallery/app/{shortlink}?tab=flows&flow={flow_id}`.

**PDF.** Write `report.json` (schema at the top of `scripts/render_report.py`) and run:
```
python scripts/render_report.py report.json out/report.pdf [--theme my-theme.json]   # PDF
python scripts/render_report.py report.json out/report/  [--theme my-theme.json]     # one JPG per page
```
In the PDF every finding page gets a clickable «Сценарий в SCRN» button; image pages have no buttons. With 3+ app logos the cover is bright: a big title (`cover_title`, `\n` for a line break) and large tilted icons; set `"cover": "plain"` for the text cover. Use screens full size (no `crop`) unless the key element is tiny; up to 3 screens per finding. When a finding is about one control changing other parts of the screen (a portions counter, a currency switch), use `callouts`: one big screen in `screens` plus 2–3 floating cards, each stacked from thin `parts` strips of the interface in another state (`{"label": "28 порций", "parts": [{screen, crop}, ...]}`); crop each strip around its text line, measured by pixels, so rows sit centred. Tag `confidence` only for a hypothesis («Гипотеза») — a fact needs no tag. The summary `conclusion` is centred in the accent card. A theme may set `fallback_fonts`: glyphs the main font lacks (→, ✓, +) are drawn with them (needs `fonttools`). `fallback_chars` (e.g. `{"semibold": "*"}`) forces chars the main font draws oddly to the fallback too. Don't repeat coverage excuses on finding pages («возможно, глубже, просто не сняли», «сняли только…»): describe what is there, with the version date, and let the one footnote carry the caveat. Under the "who does what" table put one footnote, not a legend: «* Отсутствие сценария в галерее не означает его отсутствия в реальном приложении». App logos: `get-app` → `logo_original` (or `logo`) image id; open every page before delivering.

**Carousel.** Write `slides.json` and run:
```
python scripts/render_carousel.py slides.json out/carousel [--theme my-theme.json]
```
Slide types are `cover`, `cover_icons` (big tilted app icons — use only logos of 300 px or more), `pair`, `stack` and `summary`. Give a slide `"app": {"name", "logo"}` to get the app chip with a round icon; `"chip"` then becomes its muted tail («Самокат · ИИ-поиск»). Summary bullets may be `{"text", "logo"}`, plus a `"conclusion"`. The full schema is in the docstring at the top of `scripts/render_carousel.py`. A real 6-slide example (OTP Bank 2025 → 2026, SBP transfer) is in `assets/example-slides.json`.

- Crop and blur boxes are **fractions** `[x0, y0, x1, y1]` of the screenshot, measured from the zoom sheets.
- The right-hand (or last) label gets the accent colour, meaning "now" or "the app in focus".

Then read `out/carousel/overview.jpg` and open each slide at full size. Fix:

- text that wraps badly;
- cards left half-empty (enlarge or move the crop);
- a crop that cuts off the very button the slide talks about;
- personal data that is not yet blurred;
- missing images (a grey placeholder plus a `cannot fetch` warning).

Deliver the slides. If the user wants it, add a short caption for the post: 3–7 bullet facts plus a link (a Telegram album caption is limited to 1024 characters).

**Default look** (`assets/theme-scrn.json`): scrn.gallery styling, which is Inter Semibold, a #050505 background, #1D1E20 cards and a #FA6200 accent, plus the SCRN logo and a closing card linking to scrn.gallery. To rebrand, copy the theme file and change the colours, fonts, logo and CTA. Keep the `credit` line ("Screens: scrn.gallery") when the SCRN logo is removed.

## Fallback: no code or no network
View screens with `get-screens` (prefer `format: "url"` where a link is enough). Deliver the **report in chat**; if a carousel was asked for, add a table with these columns:

- slide number;
- chip;
- title;
- body;
- left screen;
- right screen;
- crop note.

Link every flow as `https://scrn.gallery/app/{shortlink}?tab=flows&flow={flow_id}` and every single screen as `https://scrn.gallery/app/{shortlink}?screen={screen_id}`, so the user can assemble the slides in Figma or Canva. Here `screen_id` is `screens_full[]._id`, not the image id.

## Pitfalls seen in practice
- Reporting "the old version had 220 fewer flows" as a product fact. That number measures capture depth.
- Calling something removed when it moved to a neighbouring flow (a list of countries moved from "Transfer" to "Transfer abroad").
- Comparing screen counts instead of steps.
- Reading fine-print numbers from 150 px sheets and getting them slightly wrong.
- Presenting test-account artefacts (a declined transfer, a different bank) as changes.
- Putting two thoughts on one slide, or writing a body that retells the title.
- Cropping a slide about a button so that the button falls outside the crop.
- Missing an unblurred phone number on a success screen.
- A slide about a button or a counter where the screen is cropped from the top and the button is below the fold.
- Prices and product brands in the text — noise that pulls attention from the pattern.
- A final "nobody has X" bullet that the reader can apply to the contrast app, which does have it.
