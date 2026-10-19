-- ========================================================
-- Database Schema for: Student Attendance Analyzer Using Set Theory
-- Target DBMS: MySQL 8.0+
-- ========================================================

-- 1. Create Database (if not exists)
CREATE DATABASE IF NOT EXISTS `attendance_db`
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE `attendance_db`;

-- 2. Drop existing tables if needed (in reverse foreign key order)
DROP TABLE IF EXISTS `attendance`;
DROP TABLE IF EXISTS `subjects`;
DROP TABLE IF EXISTS `students`;

-- --------------------------------------------------------
-- Table: students
-- Purpose: Stores the master details of each student
-- --------------------------------------------------------
CREATE TABLE `students` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` VARCHAR(30) NOT NULL UNIQUE COMMENT 'Unique Institutional ID e.g. S001',
    `name` VARCHAR(100) NOT NULL COMMENT 'Full name of the student',
    `roll_number` VARCHAR(30) NOT NULL UNIQUE COMMENT 'Roll number / Hall ticket number',
    `class_name` VARCHAR(50) NOT NULL COMMENT 'Class or Course e.g. CSE-A, IT, Mech',
    `section` VARCHAR(10) NOT NULL COMMENT 'Section e.g. A, B, C',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_class_sec` (`class_name`, `section`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: subjects
-- Purpose: Stores academic course / subject offerings
-- --------------------------------------------------------
CREATE TABLE `subjects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `subject_id` VARCHAR(30) NOT NULL UNIQUE COMMENT 'Unique Subject ID e.g. SUB001',
    `subject_code` VARCHAR(30) NOT NULL COMMENT 'Course Code e.g. MATH101',
    `subject_name` VARCHAR(100) NOT NULL COMMENT 'Subject Name e.g. Mathematics',
    `class_name` VARCHAR(50) NOT NULL COMMENT 'Class / Department',
    `section` VARCHAR(10) NOT NULL COMMENT 'Section',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_subj_class` (`class_name`, `section`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: attendance
-- Purpose: Records daily attendance for each student and subject
-- Foreign Keys: References students(student_id) & subjects(subject_id)
-- --------------------------------------------------------
CREATE TABLE `attendance` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` VARCHAR(30) NOT NULL COMMENT 'Refers to students.student_id',
    `subject_id` VARCHAR(30) NOT NULL DEFAULT 'SUB001' COMMENT 'Refers to subjects.subject_id',
    `attendance_date` DATE NOT NULL COMMENT 'Date of the attendance',
    `status` ENUM('Present', 'Absent') NOT NULL COMMENT 'Attendance status',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_attendance_student`
        FOREIGN KEY (`student_id`)
        REFERENCES `students` (`student_id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_attendance_subject`
        FOREIGN KEY (`subject_id`)
        REFERENCES `subjects` (`subject_id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    UNIQUE KEY `unique_student_subject_date` (`student_id`, `subject_id`, `attendance_date`),
    INDEX `idx_attendance_date` (`attendance_date`),
    INDEX `idx_subject_date` (`subject_id`, `attendance_date`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Optional Initial Sample Data for Quick College Demo & Testing
-- --------------------------------------------------------
INSERT INTO `students` (`Prn_number`, `name`, `roll_number`, `class_name`, `section`) VALUES
('250015230019', 'Raju ', '2S101', 'CSE-A', 'A'),
('250015231129', 'sai', '21CS02', 'CSE-A', 'A'),
('250015231643', 'priya', '21CS03', 'CSE-A', 'A'),
('250015231256', 'roopesh',   '21CS04', 'CSE-A', 'A'),
('250015231053', 'hari',  '21CS05', 'CSE-A', 'A'),
('250015231567', 'vignesh',   '21CS06', 'CSE-A', 'A'),
('250015231123', 'satya','21CS07', 'CSE-A', 'A'),
('250015236672', 'Harshitha ',  '21CS08', 'CSE-A', 'A'),
('250015233224', 'venkat',  '21CS09', 'CSE-A', 'A'),
('250015231253', 'satish',   '21CS10', 'CSE-A', 'A');

-- Sample Working Days Attendance (5 distinct dates to test calculations & set theory)
-- Date 1: 2026-09-22
INSERT INTO `attendance` (`student_id`, `attendance_date`, `status`) VALUES
('S001', '2026-09-22', 'Present'),
('S002', '2026-09-22', 'Present'),
('S003', '2026-09-22', 'Present'),
('S004', '2026-09-22', 'Present'),
('S005', '2026-09-22', 'Absent'),
('S006', '2026-09-22', 'Present'),
('S007', '2026-09-22', 'Present'),
('S008', '2026-09-22', 'Absent'),
('S009', '2026-09-22', 'Present'),
('S010', '2026-09-22', 'Present');

-- Date 2: 2026-09-23
INSERT INTO `attendance` (`student_id`, `attendance_date`, `status`) VALUES
('S001', '2026-09-23', 'Present'),
('S002', '2026-09-23', 'Present'),
('S003', '2026-09-23', 'Absent'),
('S004', '2026-09-23', 'Present'),
('S005', '2026-09-23', 'Absent'),
('S006', '2026-09-23', 'Present'),
('S007', '2026-09-23', 'Present'),
('S008', '2026-09-23', 'Absent'),
('S009', '2026-09-23', 'Absent'),
('S010', '2026-09-23', 'Present');

-- Date 3: 2026-09-24
INSERT INTO `attendance` (`student_id`, `attendance_date`, `status`) VALUES
('S001', '2026-09-24', 'Present'),
('S002', '2026-09-24', 'Present'),
('S003', '2026-09-24', 'Present'),
('S004', '2026-09-24', 'Present'),
('S005', '2026-09-24', 'Present'),
('S006', '2026-09-24', 'Present'),
('S007', '2026-09-24', 'Present'),
('S008', '2026-09-24', 'Absent'),
('S009', '2026-09-24', 'Present'),
('S010', '2026-09-24', 'Present');

-- Date 4: 2026-09-25
INSERT INTO `attendance` (`student_id`, `attendance_date`, `status`) VALUES
('S001', '2026-09-25', 'Present'),
('S002', '2026-09-25', 'Absent'),
('S003', '2026-09-25', 'Present'),
('S004', '2026-09-25', 'Present'),
('S005', '2026-09-25', 'Absent'),
('S006', '2026-09-25', 'Absent'),
('S007', '2026-09-25', 'Present'),
('S008', '2026-09-25', 'Absent'),
('S009', '2026-09-25', 'Absent'),
('S010', '2026-09-25', 'Present');

-- Date 5: 2026-09-26 (Recent date for analysis demonstration)
INSERT INTO `attendance` (`student_id`, `attendance_date`, `status`) VALUES
('S001', '2026-09-26', 'Present'),
('S002', '2026-09-26', 'Present'),
('S003', '2026-09-26', 'Absent'),
('S004', '2026-09-26', 'Present'),
('S005', '2026-09-26', 'Present'),
('S006', '2026-09-26', 'Present'),
('S007', '2026-09-26', 'Present'),
('S008', '2026-09-26', 'Absent'),
('S009', '2026-09-26', 'Absent'),
('S010', '2026-09-26', 'Present');
