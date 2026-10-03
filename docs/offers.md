# Offers

The header, footer, homepage and shop filter replace the former editorial collection with Offers at `/shop?on_sale=true`.

Offers are calculated from active product variants whose compare-at price is strictly greater than the current selling price. No manual offer/featured checkbox is required. In Admin → Products, set the variant's selling price and a genuine previous/compare-at price. An equal or blank compare-at price does not create an offer. Stock and price filters must match the same discounted variant. Sold-out offers remain visible unless In stock only is selected.

Migration 0008 removes the unused `products.featured` column. Product write/read schemas, seeds, admin controls and query logic no longer use it. Historic migrations remain intact for database upgrades. Downgrading recreates the column with false values; removed editorial selections are not restored. Product records, media, prices and stock are preserved.

Offers/filter URLs retain the shop's noindex policy. Existing `/shop?featured=true` links redirect permanently to Offers. No coupons, countdowns, fake discounts or new payment behavior are introduced.
