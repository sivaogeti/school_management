BEGIN TRANSACTION;

-- Clean any existing rows for the same student & year
DELETE FROM fee_schedule
WHERE student_id = 'S1A01' AND academic_year = '2025-26';

-- April (04) → March (03)
INSERT INTO fee_schedule
(student_id, academic_year, month, tuition_due, bus_due, food_due, books_due, uniform_due, hostel_due, misc_due)
VALUES
-- April
('S1A01','2025-26','04', 5000, 800, 1200, 1500, 1000, 0, 0),
-- May
('S1A01','2025-26','05', 5000, 800, 1200,    0,    0, 0, 0),
-- June
('S1A01','2025-26','06', 5000, 800, 1200,    0,    0, 0, 0),
-- July
('S1A01','2025-26','07', 5000, 800, 1200,    0,    0, 0, 0),
-- August
('S1A01','2025-26','08', 5000, 800, 1200,    0,    0, 0, 0),
-- September
('S1A01','2025-26','09', 5000, 800, 1200,    0,    0, 0, 0),
-- October
('S1A01','2025-26','10', 5000, 800, 1200,    0,    0, 0, 0),
-- November
('S1A01','2025-26','11', 5000, 800, 1200,    0,    0, 0, 0),
-- December
('S1A01','2025-26','12', 5000, 800, 1200,    0,    0, 0, 0),
-- January
('S1A01','2025-26','01', 5000, 800, 1200,    0,    0, 0, 0),
-- February
('S1A01','2025-26','02', 5000, 800, 1200,    0,    0, 0, 0),
-- March
('S1A01','2025-26','03', 5000, 800, 1200,    0,    0, 0, 0);

COMMIT;


(If you want a quick payment to test with:)

INSERT INTO payments (student_id, amount, date, method)
VALUES ('S1A01', 2000, '2025-08-15', 'UPI');