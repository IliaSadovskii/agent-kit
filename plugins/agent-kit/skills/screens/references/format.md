# The screen map data format

`docs/screens/screens.data.js` is the whole map. It is plain JavaScript assigning one object
literal, because a `<script src>` load works from `file://` and fetching a sibling JSON does not —
the viewer has to open with a double click, on a laptop with no server and no network.

```js
window.SCREENS = {
  meta: { platform: 'mobile', nextScreenId: 11, nextTransitionId: 13 },
  screens: [ /* … */ ],
  transitions: [ /* … */ ],
};
```

The demo map that ships with the kit —
`${CLAUDE_PLUGIN_ROOT}/templates/screens/screens.data.js` — exercises every feature below and is
the fastest way to see a valid file.

## `meta`

| Field | Values | Meaning |
|---|---|---|
| `platform` | `mobile` \| `web` \| `desktop` | Picks the card frame: a phone for `mobile`, a browser window otherwise. Set once at first generation; once it has a value it is the owner's, and no later run re-detects it. |
| `nextScreenId` | integer | The next free `S<n>`. |
| `nextTransitionId` | integer | The next free `T<n>`. |

## Ids never get reused

Screens are `S1`, `S2`, …; transitions are `T1`, `T2`, …. Allocate from the counter, then raise the
counter. A deleted screen leaves a permanent gap and its id is never handed to another screen: a
brief written last month that says "after S7" must still mean the same screen today, and
renumbering would silently corrupt every conversation, spec, and commit message that ever pointed
at the map.

## A screen

```js
{
  id: 'S5',
  title: 'Item',
  purpose: 'One item in full, with its rating and actions.',
  status: 'implemented',
  flow: 'Browse',
  code: 'src/screens/Item.tsx',
  layout: [ /* rows */ ],
}
```

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | `S<n>`, never reused. |
| `title` | yes | What the team calls this screen. |
| `purpose` | yes | One line: what a person does here. Not a description of the widgets. |
| `status` | yes | `implemented` \| `planned` \| `idea` \| `rejected` — see below. |
| `flow` | yes | Grouping key; each distinct value becomes a column, in first-appearance order. |
| `code` | implemented only | Repo-relative path to the file that implements it. This is what lets a later run tell "planned" from "shipped" without guessing. |
| `type` | no | `screen` (default) or `overlay` — a sheet, modal, or dialog drawn over another screen. |
| `parent` | overlays | The screen id an overlay is drawn over. It is drawn smaller, attached under its parent, which requires the parent to share its `flow` and to appear earlier in the file. |
| `global` | no | `true` for a screen reachable from everywhere — a tab bar destination, an offline notice, a global error. It gets an "everywhere" badge instead of an arrow from every other card. |
| `layout` | yes | The wireframe, as rows. |

### Statuses

- **`implemented`** — the code exists; `code` points at it. Solid border.
- **`planned`** — agreed and not built. Dashed border.
- **`idea`** — floated, not agreed. A third colour, dotted. This is where a product-thinking pass
  puts a screen it proposes, so the owner sees proposals without them looking like commitments.
- **`rejected`** — considered and dropped. Hidden until its filter is switched on, and kept
  forever: the map's job includes remembering *why not*, so the same idea does not get re-proposed
  every quarter. Put the reason in `purpose`.

Anything else is drawn as `planned`: of the four, "agreed but not built" is the reading least
likely to overstate what exists. A screen silently downgraded from shipped to planned would be
exactly the lie this document exists to prevent, so the viewer names it instead.

## `layout` — the wireframe

A layout is an array of rows; a row is an array of one to three elements sharing a line. Rows are
drawn top to bottom, and a row containing a `tabbar` is pinned to the bottom of the frame.

```js
layout: [
  [{ type: 'header', label: 'Welcome back' }],
  [{ type: 'input', label: 'Email' }],
  [{ type: 'text', label: 'Terms' }, { type: 'button', label: 'Continue' }],
]
```

An element is `{ type, label?, n?, html? }`, where `n` counts the repeated parts of a `list`,
`chips`, `tabs`, or `tabbar` — it defaults to 3 and is drawn as at most 8, because past that a
card-sized wireframe is a grey smear either way. This is a card-sized wireframe, not a mockup: the
reader must recognize the screen at a glance, so three to six rows of the load-bearing elements
beats a faithful transcription of every control.

| `type` | Drawn as | Uses |
|---|---|---|
| `header` | Heavy title block | `label` |
| `text` | Light text line | `label` |
| `input` | Outlined field | `label` |
| `search` | Rounded field | `label` |
| `button` | Filled action | `label` |
| `card` | Outlined block | `label` |
| `image` | Hatched media block | `label` |
| `list` | `n` stacked rows (default 3) | `n` |
| `chips` | `n` pills (default 3) | `n` |
| `tabs` | `n` segments, first one active | `n` |
| `tabbar` | Bottom navigation bar with `n` items | `n` |
| `icon` | Small fixed-width square | — |
| `custom` | Raw HTML, for the block nothing above can express | `html` |

`custom` is the escape hatch and should stay rare — one or two per map, not per screen. Its `html`
is inserted as-is, which is no more reach than the file already has: `screens.data.js` is a script
this repository loads, so its contents are trusted exactly as far as the repository is.

**An unknown `type` renders as a labelled neutral block rather than breaking the map.** The data
file outlives the viewer copied beside it, and a grey box next to a readable label still tells the
reader what is on the screen; a blank page tells them nothing.

## A transition

```js
{ id: 'T5', from: 'S3', to: 'S4', trigger: 'account created', condition: 'email confirmed' }
```

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | `T<n>`, never reused. |
| `from`, `to` | yes | Screen ids. `from` equal to `to` is a real transition — a refresh, a re-entry — and draws as a loop on the card's edge. |
| `trigger` | yes | The arrow's label — what the person did. Two or three words: "taps Save", "session expires". |
| `condition` | no | When the trigger only sometimes leads here. Shown in the details panel. |

Transitions into a `global` screen are usually not worth recording: that is what the badge is for.

## What the viewer reports rather than hides

The map is read by people who did not write it, so the viewer never silently repairs a file. These
appear in the legend, and each names the ids involved:

| Situation | What is drawn | What is said |
|---|---|---|
| A transition points at a screen that is not in the map | Nothing for that transition | The transition ids |
| Two entries share an id | The later one wins | The duplicated ids |
| `status` is not one of the four | The card, as `planned` | The screen ids and the value found |
| `meta.platform` is not one of the three | Phone frame | The value found |
| An overlay's `parent` is missing, or not earlier in the same flow | The card, in its own place in the column | The screen ids |
| `type` is not a known element | A neutral block labelled with the type | Nothing — this one is legitimate; see above |

## Writing the file

The agent edits this file and nothing else in `docs/screens/`. Keep it reviewable:

- One element per line inside a row when the row is long; one transition per line.
- Screens in reading order within their flow, flows in the order a person meets them.
- Append new screens at the end of their flow's group rather than reordering the file — a diff that
  moves ten entries to insert one hides the change.
