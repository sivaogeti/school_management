INSERT INTO transport_routes 
(route_name, driver_name, driver_contact, vehicle_number, stops, timing, incharge_name, incharge_phone, fk_school_id)
VALUES
('Route 5 — East Loop',
 'Mr. Ramesh',
 '+91-90000-11111',
 'AP 09 AB 1234',
 'NTR Circle → Guntur Road → School Gate',
 'Pickup 7:25–7:45; Drop 15:10–15:30',
 'Ms. Rekha',
 '+91-90000-22222',
 1);

INSERT OR REPLACE INTO student_transport
(student_id, fk_route_id, fk_student_id, route_name, pickup_point, drop_point, driver_name, driver_phone, bus_lat, bus_lon)
VALUES
(
  1,  -- student_id (INTEGER, PK)  ← use users.id here
  (SELECT id FROM transport_routes WHERE route_name='Route 5 — East Loop'), -- fk_route_id
  1,  -- fk_student_id (same users.id)
  NULL,                                  -- route_name (NULL so we rely on route table)
  'NTR Circle (Gate A)',                 -- pickup_point
  'NTR Circle (Gate A)',                 -- drop_point
  NULL,                                  -- driver_name  (NULL → use route table)
  NULL,                                  -- driver_phone (NULL → use route table)
  16.2365, 80.0531                       -- optional last-known coords
);

