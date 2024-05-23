-- This is a SQL script to add seasons to the matches and the ratings table.
-- Normally this happens automatically, but the first time, this column has to be initialized manually.

UPDATE matches
SET season = CASE
                WHEN played_at < '2024-04-01'   THEN 1
                ELSE TIMESTAMPDIFF(QUARTER, '2024-01-01' , played_at) + 1 
            END;

UPDATE ratings
SET season = CASE
                WHEN since < '2024-04-01'   THEN 1
                ELSE TIMESTAMPDIFF(QUARTER, '2024-01-01' , since) + 1
            END;