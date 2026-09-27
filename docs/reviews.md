# Product reviews

Signed-in customers may submit one review per product after an order containing that product has a recorded delivered event. Pending payment, cancelled-before-delivery, and other customers' orders do not qualify. A subsequent return does not erase the customer's experience or eligibility. Deleted variants fail closed when a purchase can no longer be linked to the product. Admin accounts cannot submit reviews.

The API accepts only an integer rating from 1–5 and trimmed text from 10–2,000 characters. Ownership and purchase history are checked on the server. Submissions are serialized per customer and the existing database unique constraint prevents duplicate customer/product reviews, including rejected reviews and repeat purchases.

New reviews are pending. Administrators moderate them in Admin → Reviews, choosing pending, published, or rejected. Only published stored reviews contribute to public lists, product cards, and structured-data aggregate ratings. No reviews are seeded. Moderation should assess abusive or irrelevant content, not whether the rating is positive.

The product page shows sign-in guidance, eligibility, a submission form, or the customer's existing review and moderation status. Personal eligibility responses are not cached. Public author names use the existing first-name-only display. No new table or migration is needed: the existing review model already has rating/status checks, ownership foreign keys, indexes, and uniqueness.
