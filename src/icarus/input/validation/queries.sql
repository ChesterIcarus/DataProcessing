SELECT
    COUNT(*)
FROM input_all.routes
WHERE mode <= 4
AND vehicle_id = 0