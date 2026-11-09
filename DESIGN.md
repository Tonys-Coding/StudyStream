# StudyStream design system

One page that says how the interface is built, so a new screen looks like the
rest without anyone having to guess. The values live in
[`classroom-assistant-ui/src/index.css`](classroom-assistant-ui/src/index.css);
this explains why they are what they are.

## The idea

A study hall. A chalkboard-green rail sits beside warm paper. An orange
highlighter marks whatever you are on, and a red pen marks what is wrong.

This is a tool people use to get something done, so the world supplies four
things and no more: **type, colour, density and one signature move**. It never
supplies the layout or the controls. Navigation, tabs, tables, buttons and
inputs are the ordinary ones.

## The signature: the highlighter

Whatever is current or most important is marked the way you would mark a page.

| Where | How |
| --- | --- |
| The current page and the current subject in the rail | Full marker bar behind the row (`swipe`) |
| The current tab | Marker underline (`swipe`) |
| A study plan's focus topics, the average score | Inline marker stroke (`hl`) |
| Marker on a dark surface | Full-height block (`hl-block`) |

It is used for nothing else. If you want to emphasise something that is not
selected and not a key figure, use weight, not the marker.

## Colour

Each colour means one thing.

| Token | Meaning |
| --- | --- |
| `board`, `board-2`, `board-3` | The chalkboard: the rail, the primary button, the sign-in panel |
| `chalk`, `chalk-2` | Text on the chalkboard |
| `paper` | The page |
| `sheet`, `sheet-2` | Panels and inputs, and the subtle fill behind them |
| `rule` | Hairline borders. `line` is the stronger border for controls (3.7:1) |
| `ink`, `ink-2`, `ink-3` | Text: primary, secondary, tertiary. All pass 4.5:1 on paper |
| `hl`, `hl-soft`, `hl-wash`, `amber` | The marker: full orange for a selection, a light wash behind running text (and the logo's stream) |
| `red`, `red-soft` | Red pen: wrong answers, errors, destructive actions |
| `ok`, `ok-soft` | Correct, and a confirmation |
| `blue` | Fountain pen: the focus ring and links |

Never use red for anything that is not an error or a deletion, and never use
the marker as decoration. State is never carried by colour alone: a wrong
answer also gets an X and a screen-reader label.

## Type

**Reading is serif, doing is sans.**

- **Literata** for anything you read: page titles, panel titles, study steps,
  quiz questions, answers, the overview.
- **Atkinson Hyperlegible Next** for everything you operate: labels, buttons,
  tables, navigation, form fields.

Fixed rem scale at roughly 1.2. Nothing is fluid, because product screens are
viewed at a steady size.

| Token | Size | Use |
| --- | --- | --- |
| `text-meta` | 13px | Tags, hints, timestamps |
| `text-ui` | 15px | Buttons, table cells, labels |
| `text-body` | 16px | Default |
| `text-read` | 18px | Serif reading text, 68ch wide (`prose-read`) |
| `text-h3` / `h2` / `h1` | 20 / 26 / 32px | Panel / section / page titles |
| `text-display` | 44px | The sign-in headline only |

Numbers in tables use tabular figures (`tnum`).

## Components

Everything is built from `src/components/ui/`. A screen that needs a new kind
of control should add it there rather than styling it in place.

| Component | Rule |
| --- | --- |
| `PageShell` + `PageHeader` | Every page starts the same way: one title, one line of context, optional actions |
| `Panel` | The only container. A flat sheet with a hairline border. **Never a panel inside a panel**, no shadows, no texture |
| `Button` | `primary` (the one filled action per screen), `secondary`, `ghost`, `danger` (red pen, irreversible only) |
| `IconButton` | Always has a label |
| `Field`, `TextInput`, `Select` | A visible label above the control. Placeholders are examples, not labels |
| `Tag` | A short label: file type, who can see a file, a count |
| `Notice` | An inline message with an icon. Errors say what happened and what to do |
| `Tabs` | Standard tabs; the selected one gets the marker |
| `Table`, `Th`, `Td` | Hairline rules, no zebra, no boxes |
| `Skeleton` | Loading is a grey bar where the text will be, never a spinner in the middle of content |
| `EmptyState` | Says what is missing and what to do next |

Controls are 40px tall (32px small), corners are 6px, panels 8px, tags 4px.

## Things this design deliberately does not do

- No card grids of icon + heading + text, and no big-number tiles. A dashboard's
  numbers go in a sentence or a table.
- No eyebrow labels above headings.
- No gradient text, frosted glass, or textured backgrounds.
- No coloured stripe down the side of a card.
- No emoji or glyphs as icons. Icons are Lucide, one stroke weight.
- No modal where an inline message or confirmation will do.

## Motion

One authored moment: the marker swipes in (220ms, exponential ease-out) when
the selection changes. Everything else is a 150ms colour transition, and all
of it is disabled under `prefers-reduced-motion`.

## Logo

`public/logo.svg`: a pencil whose lead leaves a stream behind it. It is
transparent, drawn in solid shapes so it holds at favicon size, and the dark
parts follow `currentColor` in `src/components/Logo.tsx` so it works on both
the chalkboard and the paper. The orange never changes. `public/favicon.svg`
is the same mark without the faint second wave.

## Browser surfaces

The parts a design usually forgets are themed too: text selection is the
marker orange, the caret and focus ring are fountain-pen blue, scrollbars are
thin and use the border colour.


## Added later

- **Marker colour.** The marker is UTD orange (`--color-hl`), not yellow: it
  reads on the green rail and on paper, and stays clear of the red pen used
  for errors. The logo's stream uses the same orange.
- **Softer shapes.** Controls, panels and tags take their radii from three
  tokens (`--radius-ctl`, `--radius-panel`, `--radius-tag`), and primary
  buttons and panels carry a light lift. This is the part borrowed from the
  Astryx design system: every component takes its look from theme tokens, so
  re-theming is an edit to `index.css`. Astryx itself is not installed; it
  brings its own reset and StyleX build, which would fight Tailwind.
- **Sign-in hero.** The mark is the hero of the chalkboard panel, with the
  stream drawn in once on load (`Logo draw`) and faint wavy lines behind
  it, drawn from the same curve as the logo's stream (`ruled`).
- **Chat history.** Every question is saved with its full answer
  (`chat_sessions`). History lists a subject's past chats and reopens one
  exactly as it was. Switching subjects mounts a fresh workspace.
- **Upcoming assignments.** A personal to-do list at the bottom of the
  Dashboard (`assignments`): add, edit, tick off, delete. Only its owner
  sees it.

## Palette: UTD

The rail is UTD green (`#154734`) and the marker is UTD orange (`#E87500`).
Orange is full strength where it marks a selection (the current page or
subject, the tab underline) and a light wash (`--color-hl-wash`) where it sits
behind running text, such as the Focus topics and the Dashboard average, so
the text stays easy to read. The page itself never scrolls: the app fills the
window and each pane scrolls inside it.

## Shared subjects and teachers

Teachers can mark a subject **Public** with a switch when they create it.
Public subjects show up for linked students and TAs under a **Shared** heading
in the rail, kept apart from their own **Subjects** so it is clear what is
theirs. The **Teachers** page (students and TAs) and **Your class** page
(teachers) use the same panels and tables as the rest of the app, with no new
colours: a teacher code is plain text in a panel, and the roster is a normal
table.
