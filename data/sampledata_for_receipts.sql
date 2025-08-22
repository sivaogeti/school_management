INSERT INTO receipts
(receipt_no, student_id, date, payment_item, amount, mode, late_fine, transaction_id, status)
VALUES
('E-3507', 'S1A01', '2024-09-25', 'LUNCH',    100,  'Cash',   0,  'TXN1001', 'Live'),
('E-4213', 'S1A01', '2024-10-29', 'MESS',   50000,  'Cash',   0,  'TXN1002', 'Live'),
('E-4214', 'S1A01', '2024-11-05', 'BUS',     3000,  'Online', 0,  'TXN1003', 'Cancelled'),
('E-4215', 'S1A01', '2024-11-12', 'BOOKS',   2000,  'Cheque', 50, 'TXN1004', 'Live'),
('E-4216', 'S1A01', '2024-11-20', 'UNIFORM', 1500,  'DD',     0,  'TXN1005', 'Live');
