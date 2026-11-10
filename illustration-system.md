# Plavia blog covers: illustration system

One system for every cover the blog agent makes. The covers are flat vector pictures built from a small set of
geometric parts. They draw the same way as the site's own icon sprite (`#i-...` in the home page), so a cover looks like
an enlarged Plavia icon scene, not a stock illustration. The two sample covers are the reference renders:
`posts/2026/11/ai-messy-message-to-quote-request/cover.png` (light) and `posts/2026/11/galaxy-smarttag3-trackers-for-business/cover.png` (dark).
`tools/validate.py` checks every rule that can be checked automatically.

## 1. Where the rules come from (read from the live site)

| Source | Value | Rule it gives |
|---|---|---|
| Sprite symbols in the plavia.ir home page | `viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"` | outlined shapes, round ends, stroke = 7.5 % of the icon box |
| Sprite corner radii (`i-chat`, `i-monitor`, `i-card`) | `rx` / arc radius 1.5 to 2 on the 20 grid | corners 7.5 to 10 % of the icon box |
| Brand gradient in the home page hero (`#eng-grad`) | `#19C8F6` to `#2F68F2` to `#7B3BEF` | the only gradient, used once per cover |
| Theme colours in the site's public stylesheet | ink, ivory, violet, blue and teal ramps (below) | the whole palette |
| Blog card tile (`.pattern-tile`) | 16:9 tile, `--r-lg` radius, 1 px line border | covers must survive a 16:9 crop and a ~370 px card |

## 2. Canvas and grid

- Canvas: `viewBox="0 0 1200 630"` (social card ratio 1.91:1). The cover draws its own background rectangle.
- Safe area: 60 px margin on every side. Nothing important outside x 60 to 1140, y 60 to 570.
- The card tile is 16:9. A 1200x630 cover loses about 27 px top and bottom in that crop. Keep the subject inside
  y 90 to 540.
- Layout grid: three columns. Left 100 to 420, centre 450 to 750, right 780 to 1100. One subject per column, or one
  large subject centred over all three.
- Optional background dot grid: dots every 30 px, 4 px round dots. Leave the dots out behind the subject.
- Scale: one sprite unit = 8 px. That gives the stroke and radius values below.

## 3. Palette (hex)

| Name | Hex | Use |
|---|---|---|
| ink-950 | `#111016` | dark background (technology and gadget posts) |
| ink-850 | `#1F1D28` | fills of objects on the dark background, dark dot grid |
| ink-800 | `#17151F` | outlines on the light background |
| ivory-100 | `#F6F3EE` | light background (tutorial and guide posts) |
| ivory-200 | `#EEEAE2` | backdrop disc, light dot grid, inactive states |
| ivory-50 / white | `#FDFBF8` / `#FFFFFF` | object fills on light, outlines on dark (`#EEEBF7`) |
| violet-600 | `#5B3FD9` | primary accent: headers, important marks |
| violet-300 | `#A28FFF` | secondary accent, map pins, dotted paths |
| blue-600 | `#2F5BE0` | small dots, data marks |
| blue-300 | `#86A4FF` | soft lines, keys, secondary objects |
| teal-600 | `#0FA3C4` | "done" and "ok" (checks, active bars) |
| teal-300 | `#5CD3EC` | signals, motion, highlights on dark |
| brand gradient | `#19C8F6` to `#2F68F2` to `#7B3BEF` | one focal element only |

Rules: at most 4 accent colours on one cover, besides ink and ivory. Teal always means "done", "ok" or "signal".
Violet always means "important" or "location". No red, no green, no colours outside this table.

## 4. Strokes and shapes

- Outlines: 12 px (the sprite's 1.5 x 8), round caps and joins. Secondary detail lines: 8 to 10 px. Nothing thinner
  than 6 px. At card size (370 px) a 6 px line is about 2 px, and that is the floor.
- "Text" inside an object (a message, a document row) is drawn as rounded lines 12 to 14 px thick. Never real letters.
- Corner radius: 24 to 28 px on large objects (cards, phones, bubbles), 10 px on small bars.
- Fills are flat. One gradient per cover, on the focal element only. No shadows, no blur, no transparency stacks
  except fading signal arcs (opacity 1, .6, .3).
- Only these elements: `rect circle ellipse line polyline polygon path g defs linearGradient radialGradient clipPath`
  (plus `stop`). No text, script, foreignObject, image, external reference or event attribute. File under 25 KB
  (the samples are about 8 KB).

## 5. Element library (reusable parts)

| Part | Built from | Means |
|---|---|---|
| Chat bubble | rounded rect + tail (sprite `i-chat`) | a message, a request, a conversation |
| Torn document | rect with zigzag bottom (sprite `i-invoice`) | invoice, quote, form, report |
| Row with check | line + teal disc with white tick | a field that is filled or verified |
| Row with "!" | line + ivory disc with violet "!" | a missing or open item |
| Assistant node | gradient disc + white face with two eyes (sprite `i-assistant`) | the AI step |
| Arrow | 12 px line with a 26 px open head | a flow step |
| Sparkle (small) | four-point star, violet | "new" or "smart", accent only, never the focal element |
| Phone | rounded rect 170x320, speaker bar, screen content | a phone or an app |
| Map card | rounded rect + street grid + dotted path + pin | location, route, history |
| Signal arcs | concentric arcs around an object, teal, fading | wireless, broadcast, finding |
| Tag / device puck | circle with a loop hole and a gradient button | a small generic device |
| Key | ring + shaft + two teeth | access, keys, security |
| Bars | three rounded bars, two teal and one muted | progress, distance, level |
| Backdrop disc | large ivory-200 circle behind the centre | groups the scene on light covers |

Add a new part only when a topic needs it, and draw it from the same strokes and palette.

## 6. From topic to composition

1. **Find the change in one sentence.** For example, "a messy message becomes a clean quote" or "a lost thing is found by
   signal". Each cover shows one change or one object, never a list.
2. **Choose 1 to 3 parts** from the library that name the before, the tool and the after.
3. **Order them right to left.** Persian readers scan from the right. Put "before" on the right and "after" on the
   left, and point the arrows leftwards.
4. **Choose the background by category.** Tutorials and guides are light (ivory). Technology and gadget posts are dark
   (ink). The category can be told at a glance in the blog grid.
5. **Give the gradient to the focal element.** That is the tool, the AI step or the device.
6. **Check at 370 px wide.** The subject must still be recognisable. If it is not, remove detail before adding any.

## 7. Do / do not

Do:
- Draw generic objects: a round tracker, a phone rectangle, a document.
- Keep at least 40 px of air between objects.
- Reuse the site's own sprite shapes where one exists (`i-chat`, `i-invoice`, `i-assistant`, `i-monitor`, `i-key`).
- Run `tools/validate.py` (allowed elements, no references, size), render with `tools/render.js`, and look at the PNG at full
  size and at 400 px before accepting a cover.

Do not:
- Draw logos, brand marks or a product's own distinctive shape. A gadget post draws the category ("a tracker"), not
  the model ("the SmartTag3"). For the same reason the AI node uses Plavia's assistant face and not a four-point
  "AI star", because that star is close to a known product mark.
- Use photos, raster textures, real text or numbers inside the picture.
- Use more than one gradient, or put a gradient on a background.
- Fill the canvas edge to edge. The tile crops, and crowded covers turn to noise at card size.

## 8. Delivery

Each post ships `cover.svg` (the source) and `cover.png` (a 1200x630 render). The site cannot take SVG uploads today,
so the feed carries the PNG (the site may convert it to WebP). The SVG stays in this
repository as the editable source.
