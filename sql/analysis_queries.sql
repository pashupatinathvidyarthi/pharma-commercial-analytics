-- ============================================================
-- Commercial Analytics SQL — ProcDNA-style questions
-- Tables: hcps, reps, calls, sales, rep_targets
-- ============================================================

-- Q1. HCP segmentation summary: potential vs receptivity, count & avg Rx by segment
SELECT
    h.segment,
    COUNT(DISTINCT h.hcp_id)                AS hcp_count,
    ROUND(AVG(h.potential_score), 1)        AS avg_potential,
    ROUND(AVG(h.receptivity_score), 1)      AS avg_receptivity,
    ROUND(SUM(s.rx_volume), 0)              AS total_rx_volume
FROM hcps_with_segment h
JOIN sales s ON s.hcp_id = h.hcp_id
GROUP BY h.segment
ORDER BY total_rx_volume DESC;

-- Q2. Call plan compliance: actual call frequency vs target frequency by segment
SELECT
    h.segment,
    COUNT(c.hcp_id) * 1.0 / 12                          AS avg_calls_per_month,
    CASE h.segment
        WHEN 'Key Target'   THEN 2.0
        WHEN 'Growth'       THEN 1.5
        WHEN 'Maintain'     THEN 1.0
        ELSE 0.4
    END                                                   AS target_calls_per_month
FROM hcps_with_segment h
LEFT JOIN calls c ON c.hcp_id = h.hcp_id
GROUP BY h.segment;

-- Q3. Rep-level call efficiency: Rx volume generated per call, ranked
SELECT
    r.rep_id,
    r.rep_name,
    COUNT(c.hcp_id)                          AS total_calls,
    ROUND(SUM(s.rx_volume), 0)               AS total_rx,
    ROUND(SUM(s.rx_volume) * 1.0 / NULLIF(COUNT(c.hcp_id), 0), 2) AS rx_per_call
FROM reps r
LEFT JOIN calls c ON c.rep_id = r.rep_id
LEFT JOIN hcps_with_segment h ON h.hcp_id = c.hcp_id
LEFT JOIN sales s ON s.hcp_id = h.hcp_id
GROUP BY r.rep_id
ORDER BY rx_per_call DESC
LIMIT 10;

-- Q4. Incentive compensation: quarterly attainment % and payout tier per rep
SELECT
    rep_id,
    quarter,
    quota_volume,
    actual_volume,
    ROUND(actual_volume * 100.0 / NULLIF(quota_volume, 0), 1) AS attainment_pct,
    CASE
        WHEN actual_volume * 1.0 / NULLIF(quota_volume, 0) >= 1.10 THEN 'Accelerator (150%)'
        WHEN actual_volume * 1.0 / NULLIF(quota_volume, 0) >= 1.00 THEN 'Full Payout (100%)'
        WHEN actual_volume * 1.0 / NULLIF(quota_volume, 0) >= 0.80 THEN 'Partial Payout (50%)'
        ELSE 'No Payout (0%)'
    END AS payout_tier
FROM rep_targets
ORDER BY quarter, attainment_pct DESC;

-- Q5. Marketing mix proxy: which specialty x region combos have highest Rx-per-call (efficiency)
SELECT
    h.specialty,
    h.region,
    ROUND(SUM(s.rx_volume), 0)                                     AS total_rx,
    COUNT(c.hcp_id)                                                 AS total_calls,
    ROUND(SUM(s.rx_volume) * 1.0 / NULLIF(COUNT(c.hcp_id), 0), 2)   AS rx_per_call
FROM hcps_with_segment h
LEFT JOIN calls c ON c.hcp_id = h.hcp_id
LEFT JOIN sales s ON s.hcp_id = h.hcp_id
GROUP BY h.specialty, h.region
ORDER BY rx_per_call DESC;
