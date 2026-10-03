# Accessibility and responsive audit — 3 October 2026

Target: WCAG 2.2 AA-compatible behavior while preserving the approved cream/green design and product-image framing. This is an engineering audit with targeted browser checks, **not a WCAG conformance certification**.

## Fixed findings

| Finding | Impact | Fix | Verification |
| --- | --- | --- | --- |
| Several account/address/admin/cart fields override the accessible border token with pale borders | Medium: field boundaries are difficult to distinguish | Shared field styles use the existing `input-border` token, including the header search boundary | Token is 4.00:1 against white; mobile shop computed border confirmed `rgb(139,125,110)` |
| White text on the tan header count badge | Medium: small count text has insufficient contrast | Use existing forest-green brand background | White/brand 8.59:1 in contrast script |
| Scrollable operations tables have no explicit keyboard scrolling target or name | Medium: some keyboard users cannot reach offscreen columns conveniently | Focusable, named region around each admin/customer order table; explicit column header scopes | TypeScript and JSX accessibility lint pass; authenticated table interaction still needs testing |
| Product quantity error is not associated with its field | Medium: assistive technology may miss why purchase is disabled | `aria-invalid`, conditional `aria-describedby`, identified live error | Set quantity to zero: field points to `quantity-error`, Add to bag disabled; restored quantity afterwards |
| Registration instruction says 10 characters but validation requires 15 | Medium: instructions contradict accepted input | Help text now says 15–128 characters, matching HTML/backend validation | Browser registration form shows updated instructions; empty submit focuses name, no account created |
| Skip-link destination relies on browser handling of a nonfocusable main element | Low: inconsistent keyboard focus behavior | Main gets `tabIndex={-1}` without adding it to normal Tab sequence | Activating skip link sets active element ID to `main` |
| Small quantity/gallery targets and compact mobile header icons | Usability improvement | Quantity/gallery controls at least 44px; header icons at least 32px wide ×44px high on mobile | Source review and narrow viewport inspection; no forced desktop-sized header |
| Small mobile input text, tight filter grids and long-content risks | Usability/reflow improvement | 16px mobile field text, one filter column <=360px, shrinkable grid children, wrapping long card content, stacked narrow PIN controls and admin metrics | Shop computed input size 16px, opened filters fit at 320px |
| Dark admin sidebar focus ring and review-form field styling | Low: focus/field distinction | White focus ring on dark sidebar; explicit review field borders, spacing and full width | Source review; authenticated review form and admin focus still require browser verification |

Changes are isolated to `accessibility.css`, shared layout/badge styling, product quantity error semantics, operations table markup and registration instructions. No product images or business data were changed.

## Existing behavior retained

- Semantic header/main/footer and named navigation, one page heading on observed content routes, native buttons and labelled native controls.
- Labelled search, quantity, delivery and review controls. Native form validation and live status/error messages are already used throughout the application.
- Product photography has meaningful descriptions; decorative banner/brand imagery intentionally uses empty alt. Product-card photo links are hidden from assistive technology where the named product link supplies the same destination.
- Gallery uses buttons, pressed states, previous/next controls and keyboard arrow handling. Right Arrow on the first thumbnail moved focus and selection to image two during verification.
- Native details/summary filters open with Enter; no artificial modal or focus trap was added.
- Reduced-motion rules suppress animations/transitions, including the hanging brand sign. These rules were source-reviewed, not tested through an operating-system preference change.
- Account/address and media delete confirmations are inline groups, not modals. Gallery zoom is inline. Razorpay owns its external payment dialog: focus trapping, Escape, return focus and screen-reader behavior require a sandbox-payment audit separately.

## Responsive checks

Browser: Codex in-app Chromium browser against the existing development application. Widths: **320, 390, 768, 1024, 1440 and 1920 CSS pixels**. Heights 800–900px. Temporary viewport override was reset afterwards.

The route sweep inspected 12 routes at six widths. Initial streamed-page checks were followed by explicit content-heading reads and repeat measurements for homepage, shop, category and product to avoid treating loading shells as completed pages.

| Surface | Browser coverage | Result/limit |
| --- | --- | --- |
| Header/navigation/footer | Shared across inspected routes | No document-level horizontal overflow; narrow navigation scrolls within its own region |
| Homepage/hero/product grid | Populated demo homepage, six widths | No document overflow; approved imagery and grid framing retained |
| Shop/category | Populated shop and decor category, six widths; opened mobile filters at 320px | No document overflow; keyboard disclosure works, filters stack at narrow widths |
| Product | Demo ceramic vase, six widths; mobile gallery screenshot and keyboard checks | No document overflow; controls operate without requiring hover |
| Cart | Existing guest bag in browser, six widths | No document overflow; no cart mutation performed |
| Wishlist | Current guest state, six widths | No document overflow; large populated wishlist not stress-tested |
| Login/registration | Login sweep plus empty registration validation at mobile width | Fields labelled, name receives focus on invalid empty submit |
| Checkout | Signed-out gate at six widths; authenticated component/CSS source review | Authenticated address/payment/order summary states not browser-verified |
| Account addresses/orders/notifications | Signed-out states at six widths; source review | Populated account states not browser-verified |
| Admin | Access-required screen at six widths; dashboard/forms/tables CSS and component review | Actual authorized dashboard/editor/table states not browser-verified |

No missing image `alt` attributes or unnamed input/select/textarea controls were reported by the basic DOM sweep in the observed states. That check does not prove alt-text quality, full accessible-name correctness, all ARIA relationships or screen-reader usability. Intentionally scrollable tables/navigation are distinct from whole-page overflow.

## Checks run

- `npm run typecheck`: passed.
- `npm run lint`: passed, including configured JSX accessibility rules.
- `node scripts/check-contrast.mjs`: passed all nine existing token pairs. Main text 13.60:1; muted text 6.20:1; focus on canvas 6.41:1. This script does not audit every gradient/photo/translucent background.
- `npm test`: 15 passed. These are existing functional/SEO/client tests, not a new automated accessibility suite.
- Browser keyboard checks: skip link, gallery arrow selection, filter disclosure, invalid quantity and empty registration validation passed.

## Remaining release verification

1. With a dedicated test customer/admin, inspect populated cart, address edit/delete, checkout steps, order details, product/media editors, review form, tables and all inline confirmations at the same six widths. Confirm table keyboard scrolling and focus after save/cancel/delete. Current browser session is signed out; these are not claimed complete.
2. Run NVDA on Windows and VoiceOver on iOS/Safari: page announcements, error messages, live counts, image descriptions, radio groups and checkout reading order. No real screen reader was run here.
3. Test 200% text enlargement and 400% browser zoom, landscape, software keyboard, forced colors and reduced motion on actual devices. Narrow CSS viewport testing is not a substitute for all these modes.
4. Audit Razorpay sandbox modal keyboard containment and focus restoration for success, failure and dismiss; do not mark live payment accessibility verified from local source.
5. Run an automated browser accessibility scanner on authenticated fixture states and manually review results, especially text over photography, focus visibility and contrast not covered by token checks. No axe/Lighthouse conformance score is asserted.

Standards used: [WCAG 2.2](https://www.w3.org/TR/WCAG22/), [non-text contrast](https://www.w3.org/WAI/WCAG22/understanding/non-text-contrast.html), and [reflow guidance](https://www.w3.org/WAI/WCAG21/Understanding/reflow). The fixes target keyboard access, relationships/instructions, visible focus, contrast and reflow without declaring unverified screens compliant.
