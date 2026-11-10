
-- -----------------------------------------------------------------
-- QUERY 1: Lifecycle Stage Impact
-- For each stage: how often guests praise it, how often they complain,
-- and what the average score is in each case. The score gap shows
-- which stage moves the needle most.
-- Powers Panel 1 (stage impact ranking)

SELECT 'Pre-Arrival' AS lifecycle_stage,
       SUM(neg_pre_arrival)                                                     AS complaint_mentions,
       SUM(pos_pre_arrival)                                                     AS praise_mentions,
       ROUND(AVG(CASE WHEN neg_pre_arrival = 1 THEN reviewer_score END), 2)     AS avg_score_when_criticised,
       ROUND(AVG(CASE WHEN pos_pre_arrival = 1 THEN reviewer_score END), 2)     AS avg_score_when_praised,
       ROUND(AVG(CASE WHEN pos_pre_arrival = 1 THEN reviewer_score END)
           - AVG(CASE WHEN neg_pre_arrival = 1 THEN reviewer_score END), 2)     AS score_gap
FROM reviews
UNION ALL
SELECT 'Arrival',
       SUM(neg_arrival), SUM(pos_arrival),
       ROUND(AVG(CASE WHEN neg_arrival = 1 THEN reviewer_score END), 2),
       ROUND(AVG(CASE WHEN pos_arrival = 1 THEN reviewer_score END), 2),
       ROUND(AVG(CASE WHEN pos_arrival = 1 THEN reviewer_score END)
           - AVG(CASE WHEN neg_arrival = 1 THEN reviewer_score END), 2)
FROM reviews
UNION ALL
SELECT 'In-Stay',
       SUM(neg_in_stay), SUM(pos_in_stay),
       ROUND(AVG(CASE WHEN neg_in_stay = 1 THEN reviewer_score END), 2),
       ROUND(AVG(CASE WHEN pos_in_stay = 1 THEN reviewer_score END), 2),
       ROUND(AVG(CASE WHEN pos_in_stay = 1 THEN reviewer_score END)
           - AVG(CASE WHEN neg_in_stay = 1 THEN reviewer_score END), 2)
FROM reviews
UNION ALL
SELECT 'Checkout',
       SUM(neg_checkout), SUM(pos_checkout),
       ROUND(AVG(CASE WHEN neg_checkout = 1 THEN reviewer_score END), 2),
       ROUND(AVG(CASE WHEN pos_checkout = 1 THEN reviewer_score END), 2),
       ROUND(AVG(CASE WHEN pos_checkout = 1 THEN reviewer_score END)
           - AVG(CASE WHEN neg_checkout = 1 THEN reviewer_score END), 2)
FROM reviews
UNION ALL
SELECT 'Post-Stay',
       SUM(neg_post_stay), SUM(pos_post_stay),
       ROUND(AVG(CASE WHEN neg_post_stay = 1 THEN reviewer_score END), 2),
       ROUND(AVG(CASE WHEN pos_post_stay = 1 THEN reviewer_score END), 2),
       ROUND(AVG(CASE WHEN pos_post_stay = 1 THEN reviewer_score END)
           - AVG(CASE WHEN neg_post_stay = 1 THEN reviewer_score END), 2)
FROM reviews;


-- -----------------------------------------------------------------
-- QUERY 2: In-Stay Issue Breakdown
-- In-Stay generates the most feedback of any stage, so this splits it
-- into the specific operational issues underneath it. Sorted by score
-- damage, not by volume the two are very different.
-- Powers Panel 2 (issue severity vs frequency)

SELECT 'Cleanliness' AS issue,
       SUM(issue_cleanliness)                                                AS mentions,
       ROUND(100.0 * SUM(issue_cleanliness) / SUM(has_negative_feedback), 1) AS pct_of_complaints,
       ROUND(AVG(CASE WHEN issue_cleanliness = 1 THEN reviewer_score END), 2) AS avg_score_when_mentioned
FROM reviews
UNION ALL
SELECT 'Staff & Service', SUM(issue_staff_service),
       ROUND(100.0 * SUM(issue_staff_service) / SUM(has_negative_feedback), 1),
       ROUND(AVG(CASE WHEN issue_staff_service = 1 THEN reviewer_score END), 2) FROM reviews
UNION ALL
SELECT 'Room Size', SUM(issue_room_size),
       ROUND(100.0 * SUM(issue_room_size) / SUM(has_negative_feedback), 1),
       ROUND(AVG(CASE WHEN issue_room_size = 1 THEN reviewer_score END), 2) FROM reviews
UNION ALL
SELECT 'Sleep Quality', SUM(issue_sleep_quality),
       ROUND(100.0 * SUM(issue_sleep_quality) / SUM(has_negative_feedback), 1),
       ROUND(AVG(CASE WHEN issue_sleep_quality = 1 THEN reviewer_score END), 2) FROM reviews
UNION ALL
SELECT 'Climate Control', SUM(issue_climate),
       ROUND(100.0 * SUM(issue_climate) / SUM(has_negative_feedback), 1),
       ROUND(AVG(CASE WHEN issue_climate = 1 THEN reviewer_score END), 2) FROM reviews
UNION ALL
SELECT 'Noise', SUM(issue_noise),
       ROUND(100.0 * SUM(issue_noise) / SUM(has_negative_feedback), 1),
       ROUND(AVG(CASE WHEN issue_noise = 1 THEN reviewer_score END), 2) FROM reviews
UNION ALL
SELECT 'Bathroom', SUM(issue_bathroom),
       ROUND(100.0 * SUM(issue_bathroom) / SUM(has_negative_feedback), 1),
       ROUND(AVG(CASE WHEN issue_bathroom = 1 THEN reviewer_score END), 2) FROM reviews
UNION ALL
SELECT 'WiFi', SUM(issue_wifi),
       ROUND(100.0 * SUM(issue_wifi) / SUM(has_negative_feedback), 1),
       ROUND(AVG(CASE WHEN issue_wifi = 1 THEN reviewer_score END), 2) FROM reviews
UNION ALL
SELECT 'Food & Beverage', SUM(issue_food_beverage),
       ROUND(100.0 * SUM(issue_food_beverage) / SUM(has_negative_feedback), 1),
       ROUND(AVG(CASE WHEN issue_food_beverage = 1 THEN reviewer_score END), 2) FROM reviews
ORDER BY avg_score_when_mentioned ASC;


-- -----------------------------------------------------------------
-- QUERY 3: Lifecycle Complaints by Guest Segment
-- Do business travellers complain about different stages than leisure
-- guests? This is the segmentation view same lifecycle, different guests.
-- Powers Panel 3 (segment heatmap)

SELECT trip_type,
       traveller_type,
       COUNT(*)                                                      AS reviews,
       ROUND(AVG(reviewer_score), 2)                                 AS avg_score,
       ROUND(100.0 * SUM(neg_pre_arrival) / COUNT(*), 1)             AS pct_pre_arrival_issues,
       ROUND(100.0 * SUM(neg_arrival)     / COUNT(*), 1)             AS pct_arrival_issues,
       ROUND(100.0 * SUM(neg_in_stay)     / COUNT(*), 1)             AS pct_in_stay_issues,
       ROUND(100.0 * SUM(neg_checkout)    / COUNT(*), 1)             AS pct_checkout_issues
FROM reviews
WHERE trip_type != 'Unknown' AND traveller_type != 'Unknown'
GROUP BY trip_type, traveller_type
ORDER BY trip_type, avg_score ASC;


-- -----------------------------------------------------------------
-- QUERY 4: Service Consistency Across Stay Length
-- Does the guest experience hold up on longer stays? Tests whether
-- complaint rates rise the longer someone stays.
-- Powers Panel 4 (stay length degradation)

SELECT stay_length_band,
       COUNT(*)                                              AS reviews,
       ROUND(AVG(reviewer_score), 2)                          AS avg_score,
       ROUND(100.0 * SUM(has_negative_feedback) / COUNT(*), 1) AS pct_leaving_a_complaint,
       ROUND(100.0 * SUM(issue_cleanliness) / COUNT(*), 1)    AS pct_cleanliness_issues,
       ROUND(100.0 * SUM(issue_staff_service) / COUNT(*), 1)  AS pct_staff_issues,
       ROUND(100.0 * SUM(issue_noise) / COUNT(*), 1)          AS pct_noise_issues
FROM reviews
GROUP BY stay_length_band
ORDER BY CASE stay_length_band
           WHEN '1 night'    THEN 1
           WHEN '2-3 nights' THEN 2
           WHEN '4-7 nights' THEN 3
           WHEN '8+ nights'  THEN 4
         END;


-- -----------------------------------------------------------------
-- QUERY 5: What Separates a Promoter From a Detractor
-- Compares which stages and issues appear in the feedback of the
-- happiest vs unhappiest guests. The biggest differences are the
-- levers that actually convert a mediocre stay into a great one.
-- Powers Panel 5 (promoter vs detractor comparison)

SELECT score_band,
       COUNT(*)                                                AS reviews,
       ROUND(100.0 * SUM(neg_arrival)        / COUNT(*), 1)     AS pct_arrival_issues,
       ROUND(100.0 * SUM(neg_in_stay)        / COUNT(*), 1)     AS pct_in_stay_issues,
       ROUND(100.0 * SUM(issue_cleanliness)  / COUNT(*), 1)     AS pct_cleanliness_issues,
       ROUND(100.0 * SUM(issue_staff_service)/ COUNT(*), 1)     AS pct_staff_issues,
       ROUND(100.0 * SUM(issue_noise)        / COUNT(*), 1)     AS pct_noise_issues,
       ROUND(100.0 * SUM(pos_in_stay)        / COUNT(*), 1)     AS pct_praising_in_stay,
       ROUND(100.0 * SUM(pos_arrival)        / COUNT(*), 1)     AS pct_praising_arrival
FROM reviews
GROUP BY score_band
ORDER BY CASE score_band
           WHEN 'Detractor (<=6)'  THEN 1
           WHEN 'Passive (6-8)'    THEN 2
           WHEN 'Satisfied (8-9)'  THEN 3
           WHEN 'Promoter (9-10)'  THEN 4
         END;


-- -----------------------------------------------------------------
-- QUERY 6: Lifecycle Complaint Trend Over Time
-- Are complaints at each stage rising or falling across the two-year
-- window? Shows whether issues are being fixed or getting worse.
-- Powers Panel 6 (trend line)

SELECT strftime('%Y-%m', review_date)                          AS year_month,
       COUNT(*)                                                AS reviews,
       ROUND(AVG(reviewer_score), 2)                            AS avg_score,
       ROUND(100.0 * SUM(neg_arrival)   / COUNT(*), 1)          AS pct_arrival_issues,
       ROUND(100.0 * SUM(neg_in_stay)   / COUNT(*), 1)          AS pct_in_stay_issues,
       ROUND(100.0 * SUM(neg_checkout)  / COUNT(*), 1)          AS pct_checkout_issues,
       ROUND(100.0 * SUM(issue_cleanliness) / COUNT(*), 1)      AS pct_cleanliness_issues
FROM reviews
GROUP BY year_month
ORDER BY year_month;
