# Judging a screen, 26 August 2026

Two questions the kit has no answer for: **make it neat with no reference**, and **make it exactly
like this reference**. What follows is what was measured, what the field already has, and the shape
that follows from both. Nothing here is built yet; a prototype exists and is named at the end.

---

## 1. The finding that decides the design

**Models cannot compare two images.** DiffSpot (2026, 4400 UI pairs, one CSS property changed per
pair): the best model finds **40.7%** of real differences. `justify` 87%, **`line-height` 4%**,
`border-radius` 13%. And the size of the pixel change does not predict whether it is noticed
(r = −0.08), so "make the difference more visible" is not a fix.

Design2Code measured the loop that follows from it — reference plus own render plus "fix the
differences": **GPT-4o −0.3 points**, Claude 3 Opus +0.1, and weak models collapse (DeepSeek 39.7 →
30.1). That loop is what Anthropic's own docs recommend, and it is the loop that is failing today.

**Structured feedback works instead.** A separate critic returning a list of discrepancies:
Claude **+10.8%** over two rounds. The ablation in the same paper: the same second pass without the
critic gives **+1.5%**. The gain is in the form of the feedback, not in the retry. The plateau is
after round two; the third round breaks more than it fixes.

## 2. What is worth measuring at all

Design2Code fitted a regression over 435 human pairwise judgements (79.9% test accuracy):

| Measured | Weight |
|---|---|
| **Position of elements** | **+0.76** |
| **Blocks matched** | **+0.74** |
| CLIP similarity | +0.49 |
| Text colour | +0.35 |
| **Text similarity** | **−0.35** |

Geometry and presence carry the signal. Text similarity is worse than useless — it saturates near 98
for every serious model and correlates negatively with human preference.

## 3. Where the boxes come from, best first

1. **Instrument the renderer.** Design2Code refuses OCR outright — "open-source OCR tools usually
   output noisy outputs" — and instead recolours each text segment in the source, takes two more
   screenshots, and reads the boxes off the changed pixels. Zero recognition error. For a game the
   analogue is a debug pass that fills every UI element with a flat marker colour.
2. **The engine's own tree.** For HTML5 canvas games, extracting the scene graph and checking each
   object against its sprite found **100%** of 24 injected defects against **44.6%** for ordinary
   snapshot testing (ASE 2022).
3. **Computer vision plus OCR.** The fallback, for an engine that can show nothing. Measured here on
   fixtures: see §6.

For comparison, a VLM looking at a canvas screenshot alone detects **26%** of visual bugs; with a
clean reference frame, 39%; on the "appearance" class, 14%.

## 4. What the open source world has, and the hole in it

**The field splits in two and the halves never meet.** One half eats pixels and can only answer *did
it change* — every visual-regression tool. The other eats an object tree and can only answer *is the
widget there, click it* — AltTester, Poco. **Nobody reads the tree in order to judge the layout.**
The inhabitants of that gap are `layout-lint-mcp` (1 star) and `agent-vision` (11 stars).

Mature and not worth rewriting: axe-core, Lighthouse, pa11y (contrast, accessibility); pixelmatch,
odiff, Playwright `toHaveScreenshot` (pixel diff against a baseline); Project Wallace (token
consistency in CSS).

Absent entirely: **geometric quality with no reference**, and **text overflow under localisation**
(measured text width against container width) — mechanically solvable from a scene graph, built by
nobody for games. There is no UXML/USS linter. GUT has zero mentions of screenshots; gdUnit4 has no
image assertion. The only tool anywhere that judges a frame *wrong* rather than *changed* is GLIB, a
2021 research artefact on PyTorch 0.4.

**And no popular project does spec-extraction or a render-compare loop.** `screenshot-to-code`
(74.5k stars) is one shot plus human chat; its own quality evaluation is a person scoring 16
screenshots by hand.

## 5. Worth stealing

1. **A typed evidence gate** — `styleseed`: five kinds of report (`deterministic`, `code`, `visual`,
   `temporal`, `human`), each schema-validated, sha256-hashed and tied to a git commit; a `visual`
   report is invalid without at least one render carrying a viewport and a hash. This is the kit's
   own rule about silence, enforced: "it passed" cannot be written in prose.
2. **Rules as data** — `ux-skill`: 152 entries of `id / severity / category / detector / why / fix`.
3. **The validator is a separate read-only agent** — `baoyu-design`: it runs the script, passes the
   output verbatim, and is forbidden to fix what it finds. Invented numbers are banned outright.
4. **Deterministic geometry with no baseline** — `layout-lint-mcp`: spacing off the grid (tolerance
   0.15 of the base unit), horizontal overflow, vertical clipping, viewport escape, small type,
   tight leading, skipped heading levels, mixed font families, small tap targets, z-index overlap
   risk. Its author scopes it at a day of work.
5. **A finding must name its ground** — `agent-vision`: DOM geometry, computed style, an OCR box, the
   console. Plus a confidence flag that degrades honestly on gradients instead of lying.
6. **A refusal list before the work** — `iterata`: the sixth interview question is "what would make
   you reject this", and the answer becomes checkable statements. "Nothing important is hidden behind
   a click" is checkable; "feels premium" is not.
7. **Naming the current defaults** — Anthropic's own `frontend-design` skill names the three clusters
   a model slides into today and forbids spending freedom on them. One page of prose that replaces a
   dozen prohibitions.

## 6. The prototype, and what it actually does

Built and run in a container: OpenCV, Tesseract, Pillow. Two fixtures generated with four flaws
planted on purpose — a title 9px off centre, a button 6px off the column axis, a caption glued to the
bar above it, and that caption at low contrast.

| Attempt | Result |
|---|---|
| OCR over the whole frame | **useless** — 43 phantom lines on a clean frame, real text drowned |
| panels first, OCR only inside them | **precise, blind** — zero false findings, but text not on a panel is invisible |
| tuned whole-frame OCR | 9 of 14 real words, zero junk; the light title over artwork still missed |
| **multi-pass** (grey, light strokes, dark strokes, union) | **12 of 14 words**, title recovered |

What it now catches, with numbers: the title offset reported as **+9.0px** against a planted 9, the
button as **6.0px** against a planted 6, and the unreadable caption by *disappearing from OCR
entirely* while remaining on the clean frame.

What it gets wrong: the contrast detector fires on light text over artwork — four false alarms on a
clean frame — because it takes the median of the whole box. It must measure against the local
background around the strokes, over the worst window rather than the mean.

## 7. The shape that follows

**Three steps, two of them programs.**

1. **Specification before code.** The model writes an inventory — elements, hierarchy, colour and
   spacing tokens — as data, before any code exists. With a reference, the numbers are extracted from
   the image by program and the model only names them. Removing this step costs DesignCoder 42% of
   its structural accuracy.
2. **The program measures.** Render, measure, emit findings with numbers, and a threshold that
   refuses to close the step. Measure position and presence first — they are what tracks human
   judgement — then colours against the tokens, contrast, collisions, frame margins, axes, rhythm.
   Never text similarity.
3. **A judge, optional and last.** Only once the program is silent. It is given the code *and* two or
   three screenshots and a checklist — ArtifactsBench reports over 90% agreement with human experts
   that way, and a screenshot-only judge is documented to rule too early. Never "compare these two
   images".

**Two rounds, then stop.**

## 8. What a project can do today, without any of this

- **Screenshot hygiene**: 1440p, no debug overlay, no window chrome. On Claude 4.7 and newer a 1080p
  frame arrives untouched; below that it is scaled by 0.758 and an 11px caption becomes 8px, which is
  the mechanism behind "the model cannot see its own spacing error". A 4K frame is worse than 1440p —
  it is downscaled anyway and costs the same.
- **A debug render pass** with flat colours per element. An hour of work in the engine, and it
  replaces every guess with a number.
- **A comparison script wired as the declared visual command**, returning a non-zero exit code. A
  check that cannot fail changes nothing.
- **Feed the agent the list, not the pictures.** And cap it at two rounds.

---

Prototype and fixtures: `screen_report.py`, `make_fixtures.py`, container `screen-check`.

---

# S12 · Judging a screen — the plan entry

Goes last in the build order, after roles across providers. It needs the step contract (S2), the
bench (S5) and the knowledge-through-the-program (S6) to already exist, and it changes nothing that
came before.

## How it is invoked — no new command

Three pieces, each in its own home, and none of them is a thing a person has to remember:

1. **A program**, `programs/screen_check.py`. It measures and prints findings with numbers.
2. **A kind of verification**, `screen`, in the kit's own catalogue, marked `runs: feature`. A project
   answers it by declaring the command that renders a named screen, or refuses it with a date and a
   reason like any other kind.
3. **A step contract.** A step that changed a screen owes a render and a report in its output. The
   driver runs the program itself and compares against the threshold. No report, or a report over the
   threshold, and the step is not passed.

So it rides inside `ship` and `fix` on its own. One manual entry point exists for debugging:
`agent-kit screen check <png>`.

The conversational half stays where a program cannot replace it: the **screen inventory** is written
at Design and becomes a file of numbers, and the **judge** is a separate step with its own role, run
only once the program is silent, given the code and several screenshots and a checklist — never two
images to compare.

## What the program measures, best source first

1. **The scene graph, when the engine has one.** Pixi and Phaser through `page.evaluate`, Unity
   through AltTester, the browser through the DOM. Every number is then exact rather than estimated.
   Checks: pairwise overlap of visible rectangles, escape from parent or viewport, text clipped
   (measured glyph width against the box), spacing off the base unit, **alignment points** — collect
   every left/right/top/bottom edge, merge within 2px, count what remains — distinct block sizes, and
   the histogram of type sizes and leadings.
2. **Contrast from the rendered pixels**, by the `ContrastSwatch` algorithm: ARGB histogram, drop
   below 1%, merge colours under CIE-94 ΔE 2.0, most frequent is the ground, up to five foregrounds.
   This is the only way to get contrast for text over sprites and gradients, which in a game is the
   normal case rather than the exception. WCAG 2 thresholds as the gate. A pixel-derived contrast is
   reported as a warning; a style-derived one as an error.
3. **Regression against the previous build** with ꟻLIP, and pixelmatch as the cheap gate. The
   previous build is a reference for free.
4. **Computer vision and OCR**, only where the engine can show nothing. The prototype's path.

Never text similarity: it correlates negatively with human judgement.

## What is refused, with the reason

- **A judge asked to score a screen out of ten.** GPT-4V on pairwise UI design quality scores 51.58%
  — a coin toss. Human designers agree with each other at α = 0.37, so the target is barely agreed
  either.
- **No-reference image-quality metrics** (BRISQUE, NIQE, NIMA, MUSIQ). BRISQUE correlates 0.225 with
  human judgement on photographs and NIQE 0.482 on screen content. They measure a damaged photograph.
- **SSIM as the comparison metric.** It is documented to be anomalously high exactly on
  high-contrast edges, which is what a UI is made of.
- **Saliency as a score.** No published work links attention prediction to UI quality, and the most
  mature toolkit in the field returns a heatmap rather than a number, deliberately.
- **APCA in the output.** Better model, restrictive licence and a pending trademark; axe-core refused
  it. WCAG 2 is the gate; if an APCA number is ever wanted it comes from the MIT implementation in
  colorjs.io and is not called APCA.

## Worth taking rather than writing

`ContrastSwatch` from Google's Accessibility Test Framework (Apache-2.0), the m21 grid metrics from
AIM (MIT), ꟻLIP (BSD-3), and the canvas testbed from `asgaardlab/canvas-visual-bugs-testbed` (MIT) as
the worked example of reading a display list.

## Done when

A feature that changes a screen cannot be closed while the program's findings are over the
threshold; the bench carries a trap where a screen is built off-grid and the trap fires; and one real
feature on a real project is built with the loop closed and no human comparing pictures.
