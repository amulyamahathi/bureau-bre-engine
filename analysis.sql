-- Queries run on outputs/bre_output_v1.csv loaded as table `bre_output`
-- Columns: applicant_id, bureau_score, enq_6m, active_tradelines, max_dpd_12m,
--          utilization_pct, util_change_3m, monthly_income, defaulted,
--          decision, reason, offer

-- Q1. Band performance: volume, default rate, average score
SELECT decision,
       COUNT(*)                                   AS applicants,
       ROUND(100.0 * AVG(defaulted), 2)           AS default_rate_pct,
       ROUND(AVG(bureau_score), 1)                AS avg_score
FROM bre_output
GROUP BY decision
ORDER BY default_rate_pct;

-- Q2. Decline reasons with share of all declines
SELECT reason,
       COUNT(*) AS declines,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_declines
FROM bre_output
WHERE decision = 'DECLINE'
GROUP BY reason
ORDER BY declines DESC;

-- Q3. Default rate by score bucket (risk segmentation)
SELECT CASE WHEN bureau_score < 650 THEN '1. <650'
            WHEN bureau_score < 700 THEN '2. 650-699'
            WHEN bureau_score < 750 THEN '3. 700-749'
            WHEN bureau_score < 800 THEN '4. 750-799'
            ELSE '5. 800+' END                    AS score_bucket,
       COUNT(*)                                   AS applicants,
       ROUND(100.0 * AVG(defaulted), 2)           AS default_rate_pct
FROM bre_output
GROUP BY score_bucket
ORDER BY score_bucket;

-- Q4. Enquiry velocity vs default rate
SELECT MIN(enq_6m, 7)                             AS enquiries_6m_capped,
       COUNT(*)                                   AS applicants,
       ROUND(100.0 * AVG(defaulted), 2)           AS default_rate_pct
FROM bre_output
GROUP BY enquiries_6m_capped
ORDER BY enquiries_6m_capped;

-- Q5. Health offer segments: size and risk profile (window function share)
SELECT offer,
       COUNT(*)                                   AS applicants,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_base,
       ROUND(100.0 * AVG(defaulted), 2)           AS default_rate_pct,
       ROUND(AVG(monthly_income), 0)              AS avg_income
FROM bre_output
GROUP BY offer
ORDER BY applicants DESC;

-- Q6. Score cutoff analysis: if we approve everyone at/above a score floor,
--     what are cumulative approval and default rates? (window functions)
WITH by_floor AS (
  SELECT (bureau_score / 25) * 25 AS score_floor,
         COUNT(*)                 AS n,
         SUM(defaulted)           AS defaults
  FROM bre_output
  GROUP BY score_floor
),
cum AS (
  SELECT score_floor,
         ROUND(100.0 * SUM(n) OVER (ORDER BY score_floor DESC)
               / (SELECT COUNT(*) FROM bre_output), 1)             AS cum_approval_pct,
         ROUND(100.0 * SUM(defaults) OVER (ORDER BY score_floor DESC)
               / SUM(n) OVER (ORDER BY score_floor DESC), 2)       AS cum_default_pct
  FROM by_floor
)
SELECT * FROM cum WHERE score_floor >= 600 ORDER BY score_floor DESC;
