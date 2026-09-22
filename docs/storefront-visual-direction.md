# Storefront visual direction — reference approved 21 September 2026

Use the user's multi-page cream-and-green home decor reference for all subsequent phases. Keep the existing Home Decor name until the user chooses a final brand. Do not adopt sample claims, ratings, return policies or delivery promises from the reference.

## Shared design

- Warm ivory canvas `#fbf9f3`, charcoal/brown text, forest green `#3f5138`, warm brown purchase accent.
- Elegant serif headings, clean sans-serif controls, narrow uppercase section labels, generous spacing.
- Search-led header, product category navigation, wishlist and bag icons; a compact delivery message with no unverified promise.
- Photography-led hero, category tiles, new arrivals and curated edit. Best sellers require genuine sales; reviews require real published reviews.
- Consistent product cards throughout homepage, shop, category, related products and wishlist. Shared shell applies to existing cart and purchase preview; full checkout/account/admin remain later phases.
- Use the same tokens and components when implementing prompts 12 onward. No disconnected page themes.

## Product image contract

All catalog cards and main gallery frames have a fixed **4:5 aspect ratio**. Future product uploads automatically use the same frame. Use 1200 × 1500 px or larger 4:5 source photography, full object centred with roughly 10–15% breathing room. Cards use `cover`; the main gallery uses `contain` to avoid hiding product edges. Thumbnails are also 4:5. Do not stretch source images.

Provide four separate, consistent views per product: front, alternate angle, material/construction detail, and styled setting. Preserve the actual item's shape, colour and material across views. Give each a meaningful alt description and explicit dimensions. Product image order controls the primary image and hover image. One-image products still work without a false alternate view.

Hover-capable devices crossfade to the second view, gently scale the image and reveal a product link. Touch users can tap the full photo/title and use visible gallery thumbnails/previous/next buttons. Keyboard users can tab through images, use left/right arrows in the thumbnail list, and toggle zoom. Reduced-motion preferences suppress transitions. Never require hover to access an essential action.

## Local demo assets

Six sample products, each with four AI-created photographs, are in `frontend/public/demo/`; the hero is `hero.png`. The built-in image generation tool was used. Product source images are 1122 × 1402 px, rendered in a uniform 4:5 frame; hero is 1536 × 1024 px. Next Image serves responsive optimized versions. Original generated sources remain in the user's Codex generated_images directory; all website dependencies are copied into this repository.

`python -m app.seed_demo` refreshes only explicitly labelled local demo records, preserving product/variant IDs, image IDs and current stock. The entrypoint refuses non-development environments and nonlocal database hosts. Prices, stock, dimensions and materials are labelled illustrative. No reviews or delivery rows are seeded.

Demo DB image references use reserved `https://local-preview.invalid/demo/<file>.png` URLs. `imageSource` resolves that exact reserved prefix to the bundled `/demo/` path for Next Image and metadata. The invalid domain is never fetched by the storefront. This is a local fixture convention; real admin uploads retain HTTPS Cloudinary validation. Replace/deactivate demo records and use real Cloudinary assets before launch.

## Image prompt set

Common product prompt: premium ecommerce product photography, warm beige plaster studio and limestone surface, soft natural daylight, full object centred, portrait 4:5, no text, logo, border or collage.

Subjects: ivory speckled pear-shaped ceramic vase with dried stems; natural seagrass basket with charcoal stripe and loop handles; sage linen cushion with fine piping; oatmeal cotton throw with caramel stripes and fringe; terracotta ceramic lamp with ivory linen shade; bell-shaped woven rattan pendant on black cord.

Each primary image was used as the identity reference for three additional built-in image generation calls: higher three-quarter side angle, tactile material close-up, and warm cream/oak living-room styling. The prompt explicitly preserves silhouette, colour, material, proportions and pattern.

Hero prompt: wide sunlit cream wall, sculptural oak console on the right, large ivory ribbed vase with olive branches, small caramel vase, oatmeal throw and cream boucle chair; quiet left space for heading, natural window light and leaf shadows, no embedded text.
