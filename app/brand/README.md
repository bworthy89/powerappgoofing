# Brand assets

## `app-icon.png` — the app icon

512x512 PNG, transparent outside the chamfer. Upload in Power Apps Studio under
**Settings → General → Icon**.

The letterform is **lifted from Glory's own wordmark artwork**, not redrawn — the same
chamfered terminals, at the same proportions. Two alternatives are kept beside it
(`-alt-rows`, `-alt-page`); both read as generic document icons below about 40px, which is
where an app icon spends most of its life.

The cut corner is transparent rather than filled, so the icon sits correctly on a light tile
or a dark one. Do not flatten it onto a background.

## `glory-wordmark-white.png` — the wordmark

200px wide, white on transparency, extracted from `glory-logo-602x590.jpg` and embedded as
base64 in every screen's brand band via `scripts/screen_parts.py`. Regenerating it means
re-encoding that base64 — it is not read from this file at build time, so this copy is the
source of record, not the thing the app uses.

## Colour

`#111987` — Glory brand indigo. Established from two independent sources: the logo artwork is
97.6% that value by ink pixel, and it is the most frequent hex in glory-global.com's
stylesheet. Not from a brand guide; if Glory's guide names a different value, that wins.
