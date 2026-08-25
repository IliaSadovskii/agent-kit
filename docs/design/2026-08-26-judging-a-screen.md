# S13 · A screen is measured against what it declared

Last in the build order. Written after two reviews took the first draft apart: one against the real
code of `v3`, one against the method. What follows is the corrected version. The argument, the
measurements and the refusals live in `docs/design/2026-08-26-judging-a-screen.md`; this page holds
only what a run has to know while it decides.

## What this is, and what it is not

**Not** "judge whether a screen is beautiful", and **not** "geometric quality with no reference".
That second one is unsolvable and that is why nobody has solved it: no measurement distinguishes a
deliberate asymmetry from a slipped element. A diegetic HUD, an isometric board, a hand-drawn
interface would each produce a finding on every element.

What is solvable: **the geometry disagrees with what this screen declared about itself.** So the
inventory is not an optional first step, it is the thing the check is against.

Everything below is a program. The model's part is writing the inventory and, at the end and only
sometimes, reading a checklist.

## Five frozen forms this needs, each its own step before it

The first draft claimed it changed nothing that came before. That was false. Each of these is a
change to a shape already in use and travels with a migration and a test, on its own:

1. **A fractional field type.** `contract.py` has `Text, LongText, Bool, Int, Enum, TextList,
   Records`; `Int` refuses anything that is not an `int`. Offsets, ratios and tolerances are
   fractional.
2. **A step that need not run.** `DEFAULT_STEPS` is a six-tuple and every step is compulsory. A
   project with no interface has no way not to have this one. Absence of a `[screens]` declaration
   must mean *not planned*, which is a third thing beside *passed* and *refused*.
3. **`SCHEMA_VERSION`.** Adding steps changes the shape of every run file.
4. **`deliverable.READ`.** It reads four steps; a fifth one's output reaches no pull request until it
   is named there.
5. **`[screens]` in `project.toml`.** `_TOP_KEYS` is `{project, commands, roles}` and unknown keys are
   refused.

## What a project declares

```toml
[screens.battle]
command = "make screenshot SCREEN=battle"   # renders it, writes a PNG and an element list
surface = "game"                            # web | mobile | game | pixels
paths   = ["src/ui/battle/**"]              # what building this screen touches
aspects = ["16:9", "19.5:9", "4:3"]         # rendered once per aspect
[screens.battle.thresholds]
tap_target = 48                             # 24 by WCAG 2.2, 44 on Apple, 48 on Google — the
                                            # project decides, the kit ships a default and never
                                            # decides for anybody
[[screens.battle.accepted]]
finding = "near-axis:title"
since   = "2026-09-01"
why     = "the title is deliberately off the column axis"
```

`accepted` is the third answer the first draft did not have: **a finding is closed by a record beside
the screen it belongs to, with a date and a reason.** Without it the first deliberate asymmetry stops
a night and the whole gate gets switched off.

## How the step is planned — by a program, never by a claim

The driver takes `git diff --name-only` against the run's base, intersects it with the `paths` of
every declared screen, and plans the step for the screens that intersect. No field written by a model
takes part in that decision. A model saying "this feature changed a screen" is prose, and prose is
obeyed 29–56% of the time — which is the measurement this whole plan exists because of.

## Where the numbers come from, and how honest each source is

The element list is `(type, box, text, colour, visible, z, opacity)`. What produces it is a **surface
adapter**, the same shape as a provider adapter, declared per screen:

| Surface | Source |
|---|---|
| web | DOM and computed styles through Playwright |
| mobile | the accessibility tree — XCUITest, `uiautomator` |
| game | the engine's own tree — Pixi/Phaser display list, Godot `Control`, Unity via AltTester |
| pixels | computer vision and OCR, the fallback |

**A tree gives exact layout rectangles, which are not the visible shape.** This has to be written
down because the first draft claimed the opposite: trimmed atlas frames, rotation (an AABB is much
larger than a rotated card), masks that bounds do not intersect with, elements at `alpha: 0`, text
baked into a texture, and Unity's `RectTransform` being the layout rect rather than the drawn one.
Each of those makes a number true and misleading at once.

So the report carries `source` with three values, and the gate reads it:

- `tree` — findings may block;
- `pixels` — every finding is a warning, never a block. Measured on the prototype: a variance-based
  panel detector found 5 and 6 panels on two nearly identical frames where 8 were drawn, and its
  boxes were inset by 6–7px by the border radius;
- `none` — the step **refuses** with a code and a hint, exactly as `verify` refuses when a project
  declares no commands. Silence never means "fine".

**Before measuring, the screen is still**: no tween running, fonts loaded, animations disabled. A
screenshot is a moment, and a moment inside a transition measures the transition.

## What is measured

**Structural, cheap, and the same on every surface.** These block:

| Check | How | Note |
|---|---|---|
| the screen is empty | one colour, or ink below a floor, or fewer than N visible nodes | the cheapest check there is and it catches what actually breaks in a build |
| a texture is missing | node present, texture is the engine's default or the area's entropy is ~0 | |
| the frame is blurred or scaled wrong | gradient energy against neighbours, or the render size against the requested one | |
| text is clipped | measured glyph width against its container | needs per-glyph metrics; unavailable for text baked into a texture, and that is reported |
| text overflows under localisation | the same check, run against the longest declared translation | named as an industry-wide hole and closed here |
| tofu | replacement glyphs present | the classic Cyrillic and CJK failure |
| content escapes its parent or the safe area | box not contained | run once per declared aspect; **the highest-yield check for anything not on the web** |
| an element declared in the inventory is absent | join against the inventory | |
| an element is present that the inventory does not declare | the same join | catches the debug overlay, the stray label |

**Advisory. These warn and never block:**

alignment points (edges merged within a tolerance **derived from the base unit and the device pixel
ratio**, never a fixed 2px); spacing off the base unit, where the unit is **derived from the frame** —
the mode of the pairwise gaps — or declared, never a hardcoded 4 or 8; distinct block sizes; the
histogram of type sizes; contrast.

**Two hardcoded numbers from the first draft are deleted.** The 4/8 grid, because correct centring —
`(W − w) / 2` — lands off an 8px grid unless the widths happen to agree, and five of seven
coordinates of the prototype's own clean fixture fail it. And "1–5px is worse than 20", which
contradicts the number this plan cites elsewhere: the size of a change does not predict whether it is
noticed (r = −0.08). A detector must therefore report *any* deviation from a declared axis, not a
band of them.

**Overlap needs a model, not a rectangle intersection.** Overlap is normal in a UI — a badge on an
icon, a panel over a background. The defect is content *occluded*, which needs z-order and opacity.
Without them, a raw pairwise AABB intersection returns hundreds of pairs on a real HUD.

## Contrast, and the trap in it

WCAG 2 contrast is computed where it can be: **blocking only where the background is known from
styles**, and a **warning with its number when it was derived from pixels**. Over artwork the
threshold is legitimately failed by a correct design — a light title over a sunset, an outlined caption
over a sprite — and a gate that fires on every good frame is a gate that gets turned off in a week,
taking the rest of this step with it.

The algorithm is `ContrastSwatch`: histogram, drop what is under a share **of the element's box** —
not of the frame, where a title is 0.36% and a caption 0.22% and both would be discarded before
anything is compared — merge near colours, most frequent is the ground. Which means **contrast needs
the element boxes**, so it is not an independent source but a consumer of the tree.

## The judge, and the rung it needs

A separate step, run only when the program is silent, given the code and two or three screenshots and
a per-screen checklist, returning `Records` with a `severity` — the same contract shape as review, not
prose in a role.

The provider ladder is `binary, answers, login, one_shot, contract, observed, limits`. It needs
**`images`**, and the program must refuse to put the judge role on a provider that does not hold it —
otherwise the judge silently degrades to a text-only judge and nobody notices. That refusal is the
same one that already stops a level-A provider from taking an unattended role.

And the question is never "score this screen out of ten": pairwise, a model agrees with humans on UI
design quality **51.58%** of the time, which is a coin toss, and human designers agree with each other
at α = 0.37.

## Rolled out in two stages, and the first stage blocks nothing

The prototype produced four blocking findings on a frame with nothing wrong with it. Every false
finding is a round of feedback in which a model rewrites a correct screen — the exact failure this
plan quotes from Design2Code and promises to avoid.

So: **stage one, every finding is a warning**, on every surface, and the run records them. **Stage two
turns on blocking for one class at a time**, and only for a class whose precision has been measured
over at least ten real screens from at least two projects. A class that has not been measured cannot
block. This is the same discipline the kit already applies to a provider: a level nobody measured is
not a level.

## Done when

- a screen declared in `project.toml` is rendered at each declared aspect, and the step is planned by
  the diff rather than by anybody's word;
- a run on a project with no `[screens]` shows the step as *not planned* — not passed, not refused;
- a render that fails, and a frame that cannot be parsed, both stop the step with a named reason;
- the bench carries one trap per surface — a web page, a mobile screen and a game frame — each with a
  planted defect of a class that blocks, and each fires;
- precision is measured over ten real screens before any class is allowed to block, and the number is
  written down beside the class.
