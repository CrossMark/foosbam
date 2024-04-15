-- database: ../app.sqlite
-- This is a SQL script to add seasons to the matches and the ratings table.
-- Normally this happens automatically, but the first time, this column has to be initialized manually.

UPDATE matches
SET season = CASE
                WHEN played_at IS NULL          THEN 1
                WHEN played_at < '2024-04-01'   THEN 1
                ELSE DATEDIFF(QUARTER, played_at, CURRENT_DATE)
            END;

UPDATE ratings
SET season = CASE
                WHEN since IS NULL          THEN 1
                WHEN since < '2024-04-01'   THEN 1
                ELSE DATEDIFF(QUARTER, since, CURRENT_DATE)
            END;