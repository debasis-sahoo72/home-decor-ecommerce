# Warm modern home decor design system

Phase 03 defines reusable foundations, not complete store pages. The brand name remains provisional. Tailwind v4 tokens live in `frontend/src/app/tokens.css`, imported by the global stylesheet. Example utilities: `bg-canvas`, `text-ink`, `font-display`, `rounded-lg`, `shadow-card`, `md:grid-cols-3`. Do not introduce an additional CSS framework.

## Color and type

Canvas #FAF7F2, surface #FFFFFF and muted surface #F0E9DF form a warm neutral base. Ink #302923 is primary text; muted ink #665C52 supports descriptions. Olive #5B6548 is the primary action, with #454E35 hover and white text. Clay #A65336 is a restrained accent, never the sole indication of status. Input border #8B7D6E distinguishes interactive fields; decorative borders use #D8CFC3. Blue #315F86 is a visible focus ring. Success #306444, warning #805312 and danger #A22C29 have soft background variants and always include words/icons.

Elegant headings use local Georgia, while controls/body use Arial/Helvetica. This avoids network font requests and layout shifts. A licensed/self-hosted brand font can replace these tokens later. Weights: 400 body, 500 labels, 600 controls, 700 emphasis. Do not simulate thin weights. Body is 16px/1.6, UI labels 14px/1.4, captions 12px/1.5, small headings 20–24px/1.3, section headings 30–36px/1.2 and hero headings 36px mobile/48px desktop with 1.1–1.2 line height. Never put essential purchase information only in captions. Limit prose to about 65 characters per line.

## Layout foundations

Spacing follows a 4px unit: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64 and 96px (`1`–`24` Tailwind units). Mobile page gutters 16px, tablet 24px, desktop 32px; max content width 1280px. Group related controls tightly; separate sections with 48px mobile/80px desktop. Radius: 4px small, 8px controls, 12px cards, 16px dialogs and pill for badges. Shadows are subtle card, popover and modal tokens; borders remain visible without shadows.

Breakpoints are mobile-first: default <640px, sm 640px, md 768px, lg 1024px, xl 1280px and 2xl 1536px. Layout changes follow available space. Product grids start at two columns only when card content fits at 320px; otherwise use one, then three at md and four at xl. Reflow at 400% zoom without horizontal page scrolling. Use logical DOM order, not visual CSS reordering.

## Component contracts

| Component | Appearance and required behavior |
| --- | --- |
| Buttons | `.button` plus primary/secondary/danger; 44px minimum target, text labels, visible focus. One primary action per decision area. Busy state retains width, shows “Saving…” and `aria-busy`; prevent duplicate submission. Links navigate, buttons act. Disabled is accompanied by an explanation where needed. |
| Inputs | Persistent label above `.input`, helper/error linked with `aria-describedby`, `aria-invalid` on error. Appropriate autocomplete/inputmode; 16px text avoids mobile zoom. Never use placeholders as labels. Password visibility control has a clear accessible name. |
| Cards | `.card`, restrained border/shadow and predictable spacing. No hover-only content or nested links/buttons inside a clickable card link. |
| Product cards | Fixed 4:5 image ratio, product name, INR price, availability and optional factual badge. Product title/image link separately; wishlist has its own button and state. Show genuine sale reference prices only. Meaningful image alt text, responsive source widths and lazy loading below the fold. |
| Badges | `.badge` plus semantic variant; concise visible text, no meaning from color alone. Delivery claims only after postcode validation. |
| Navigation | Clear logo/home link, category links, search, account and cart count. Mobile menu is a button with expanded state; keyboard-operable drawer, Escape close, focus return. Provide skip-to-content link when navigation is implemented. Sticky headers must not obscure focus. |
| Footer | Customer help, shipping/returns, contact and policy links with readable contrast. Do not invent address, certifications or contact details. Collapse groups only with accessible buttons. |
| Modal | Prefer native dialog with accessible title; focus enters, stays within modal, Escape closes when safe and returns to trigger. Backdrop dark overlay; max width 560px, 16px mobile margin. Destructive actions state their consequence and retain a cancel option. No modal code is shipped in this phase. |
| Toast | Future live region with polite status for success, alert for actionable failures. Do not steal focus. Provide dismiss control; critical errors persist and also appear inline. Success notices remain at least 5 seconds and pause while hovered/focused. |
| Loading | Skeletons preserve final image/text dimensions and are hidden from screen readers; one textual status announces loading. No animation under reduced motion. Do not fake stock or prices while loading. |
| Empty | Short title, explanation and useful action: “Your wishlist is empty” with browse link. Avoid treating an API failure as an empty catalog. |
| Error | Plain-language cause when known, field-level correction and retry when safe. Keep entered form data. Never expose stack traces or secrets. Checkout errors distinguish pending payment from confirmed failure. |

## Accessibility and motion

Target WCAG 2.2 AA: 4.5:1 normal text, 3:1 large text and interactive boundaries/focus; test rendered states as components are built. Use semantic landmarks, one page h1, logical heading hierarchy, visible labels, keyboard operation and screen-reader names. Status must be conveyed in text. Respect reduced motion, support text resizing, and ensure overlays work with virtual keyboards. Motion is optional, typically 120–180ms color/opacity; never essential to comprehension.

Token contrast is checked with a deterministic script under `frontend/scripts/check-contrast.mjs`. It checks intended pairs, not every possible token combination. Full accessibility verification requires real components and manual keyboard/screen-reader testing in later UI phases.
