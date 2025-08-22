-- Admin
INSERT INTO users (fk_school_id, email, password, role, name)
VALUES (1, 'admin@school.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Admin', 'System Admin');

-- Principal
INSERT INTO users (fk_school_id, email, password, role, name)
VALUES (1, 'principal@school.com', '46f94c8de14fb36680850768ff1b7f2a5d2a2d2737d8d4b4f1c0efb9dba7cbb3', 'Principal', 'School Principal');

-- Front Office
INSERT INTO users (fk_school_id, email, password, role, name)
VALUES (1, 'frontoffice@school.com', '4c32a3b5d6c9f8b7f0cb8d0ed6f3cb6e7f9d7a0a4e8a9d3d0f9c3b2a7d6f8a2c', 'Front Office Admin', 'Front Office');

-- Teacher
INSERT INTO users (fk_school_id, email, password, role, name)
VALUES (1, 'teacher@school.com', '4e9f9c3f9d5f4b6a0c1a6b8f4d2f3c6a7e9b1c2a7f9b3d0c8e1a6f4d7b9f0c5e', 'Teacher', 'Class Teacher');

-- Student
INSERT INTO users (fk_school_id, student_id, name, email, password, role, class, section)
VALUES (1, 'S1001', 'Ravi Kumar', 'student1@school.com', '4dc968ff0ee35f1bd6cf1c69d7f4b8a6c7d8f9b3d2c4e5a1f7b8c6e2a3d9f0b7', 'Student', '10', 'A');


--chairman
INSERT INTO users(fk_school_id, student_id, student_name, name, email, password, role)
VALUES (1, 'CHAIR01', 'Chairman', 'Chairman', 'chairman@school.com', 'chairman123', 'Chairman')
VALUES (1, 'CHAIR01', 'Chairman', 'Chairman', 'chairman@school.com', 'chairman123', 'Chairman')
VALUES (1, 'CHAIR01', 'Chairman', 'Chairman', 'chairman@school.com', 'chairman123', 'Chairman')

