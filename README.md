Guest Lifecycle Sentiment Dashboard

A six-panel Power BI dashboard analysing 515,738 hotel guest reviews, broken down by
stage of the guest journey, to find out where the guest experience actually breaks
down — not just whether guests are happy overall.

Pipeline: Raw reviews → Python (cleaning + lifecycle tagging) → SQLite → SQL (six
aggregation queries) → Power BI.

The summary below highlights the core findings at a glance. The full report including detailed analysis and recommendations is in the file Operational Summary.docx. SQL queries
are in queries.sql, and the Python cleaning script is in clean_reviews.py.

Key findings:

1. Guests forgive a so-so room. They don't forgive feeling forgotten. In-stay
experience generates the most feedback of any stage but moves the score the least
(a 0.96-point gap between praise and complaint). Post-stay sentiment (would they
return) moves the score by 2.44 points — more than double.
2. Cleanliness is rare, but it's the one thing guests won't forgive. Only 3.3% of
complaints mention it, but when they do, average score drops to 6.14 — the lowest
of any issue tracked, well below more common complaints like food & beverage (7.90).
3. Solo business travellers are the hardest guests to satisfy — 7.94 average score
with in-stay issues in 55.9% of their reviews, versus 8.55 for leisure couples.
4. Standards drift the longer a guest stays. Complaint rate climbs from 73.7% on
1-night stays to 81.2% on 8+ night stays, with score dropping alongside it.
5. Complaints have been rising, not falling, across the two-year window this data
covers — both in-stay and arrival complaint rates trended upward.
