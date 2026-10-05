"""
Database Connection and Utility Module
--------------------------------------
Project: Student Attendance Analyzer Using Set Theory

This module manages database connections and query execution.
It is configured to connect to MySQL (attendance_db).
If MySQL credentials are not yet configured in `.env`, it gracefully
initializes a local SQLite database (database/attendance.db) with the exact
same schema and sample data so you can run and test the project immediately!
"""

import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file located in backend directory
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "attendance_db")
DB_PORT = int(os.getenv("DB_PORT", 3306))

# Track active database type ('mysql' or 'sqlite')
ACTIVE_DB_TYPE = "mysql"
SQLITE_DB_PATH = Path(__file__).resolve().parent.parent / "database" / "attendance.db"


def try_mysql_connection(select_db=True):
    """Attempt connecting to MySQL server via PyMySQL."""
    import pymysql
    import pymysql.cursors
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        database=DB_NAME if select_db else None,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        charset='utf8mb4'
    )


def get_db_connection():
    """
    Returns an active database connection.
    Uses MySQL if available; otherwise falls back to SQLite.
    """
    global ACTIVE_DB_TYPE

    if ACTIVE_DB_TYPE == "mysql":
        try:
            return try_mysql_connection(select_db=True)
        except Exception:
            # If MySQL fails during runtime, use SQLite
            ACTIVE_DB_TYPE = "sqlite"

    # SQLite connection with Row factory to behave like dict cursor
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes the database schema and sample records.
    1. Attempts MySQL connection.
    2. If MySQL connects, executes database/attendance.sql.
    3. If MySQL credentials fail (e.g. password required), falls back to SQLite.
    """
    global ACTIVE_DB_TYPE
    sql_path = Path(__file__).resolve().parent.parent / "database" / "attendance.sql"

    # Step 1: Try MySQL
    try:
        conn = try_mysql_connection(select_db=False)
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        conn.close()

        # Connect to the created database and check tables
        conn = try_mysql_connection(select_db=True)
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'students';")
            students_exist = cursor.fetchone()
            if not students_exist and sql_path.exists():
                with open(sql_path, "r", encoding="utf-8") as f:
                    sql_script = f.read()
                for stmt in sql_script.split(";"):
                    cleaned = stmt.strip()
                    if cleaned:
                        cursor.execute(cleaned)
                print(f"[Database] Successfully initialized MySQL database '{DB_NAME}' from attendance.sql!")
            else:
                print(f"[Database] Connected to MySQL '{DB_NAME}'. Tables verified.")

            cursor.execute("""
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'attendance'
                  AND column_name = 'subject_id'
            """)
            if cursor.fetchone()["column_count"] == 0:
                cursor.execute("""
                    ALTER TABLE attendance
                    ADD COLUMN subject_id VARCHAR(30) NOT NULL DEFAULT 'SUB001'
                    AFTER student_id
                """)

            cursor.execute("""
                SELECT index_name,
                       GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')
                           AS indexed_columns
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = 'attendance'
                  AND non_unique = 0
                GROUP BY index_name
            """)
            unique_indexes = cursor.fetchall()
            legacy_indexes = [
                row["index_name"] for row in unique_indexes
                if row["indexed_columns"] == "student_id,attendance_date"
            ]
            for index_name in legacy_indexes:
                escaped_name = index_name.replace("`", "``")
                cursor.execute(f"ALTER TABLE attendance DROP INDEX `{escaped_name}`")

            has_subject_date_index = any(
                row["indexed_columns"] == "student_id,subject_id,attendance_date"
                for row in unique_indexes
            )
            if not has_subject_date_index:
                cursor.execute("""
                    ALTER TABLE attendance
                    ADD UNIQUE KEY unique_student_subject_date
                        (student_id, subject_id, attendance_date)
                """)
        conn.close()
        ACTIVE_DB_TYPE = "mysql"
        return True, "MySQL database initialized and ready."

    except Exception as err:
        print(f"[Database Notice] MySQL connection not ready ({err}).")
        print(f"[Database Notice] Automatically using SQLite fallback at: {SQLITE_DB_PATH}")
        ACTIVE_DB_TYPE = "sqlite"

        # Initialize SQLite database
        SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        # Create students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                roll_number TEXT NOT NULL UNIQUE,
                class_name TEXT NOT NULL,
                section TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create subjects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id TEXT NOT NULL UNIQUE,
                subject_code TEXT NOT NULL,
                subject_name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                section TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create attendance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                subject_id TEXT NOT NULL DEFAULT 'SUB001',
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
            );
        """)
        conn.commit()

        # Check if subject_id column exists in attendance table; if not, add it
        cursor.execute("PRAGMA table_info(attendance);")
        att_cols = [col[1] for col in cursor.fetchall()]
        if "subject_id" not in att_cols:
            cursor.execute("ALTER TABLE attendance ADD COLUMN subject_id TEXT DEFAULT 'SUB001';")
            conn.commit()

        # Ensure any records with NULL subject_id are updated to 'SUB001'
        cursor.execute("UPDATE attendance SET subject_id = 'SUB001' WHERE subject_id IS NULL OR subject_id = '';")
        conn.commit()

        # Older SQLite databases enforced one attendance record per student and
        # date, which incorrectly prevents attendance in multiple subjects.
        cursor.execute("PRAGMA index_list(attendance);")
        attendance_indexes = cursor.fetchall()
        rebuild_attendance = False
        legacy_unique_indexes = []
        for index in attendance_indexes:
            if not index[2]:
                continue
            escaped_name = index[1].replace('"', '""')
            cursor.execute(f'PRAGMA index_info("{escaped_name}");')
            indexed_columns = [column[2] for column in cursor.fetchall()]
            if indexed_columns == ["student_id", "attendance_date"]:
                if index[3] == "u":
                    rebuild_attendance = True
                else:
                    legacy_unique_indexes.append(index[1])

        if rebuild_attendance:
            cursor.execute("DROP TABLE IF EXISTS attendance_schema_migration;")
            cursor.execute("""
                CREATE TABLE attendance_schema_migration (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL DEFAULT 'SUB001',
                    attendance_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
                );
            """)
            cursor.execute("""
                INSERT INTO attendance_schema_migration
                    (id, student_id, subject_id, attendance_date, status, created_at)
                SELECT id, student_id, COALESCE(NULLIF(subject_id, ''), 'SUB001'),
                       attendance_date, status, created_at
                FROM attendance;
            """)
            cursor.execute("DROP TABLE attendance;")
            cursor.execute(
                "ALTER TABLE attendance_schema_migration RENAME TO attendance;"
            )

        for index_name in legacy_unique_indexes:
            escaped_name = index_name.replace('"', '""')
            cursor.execute(f'DROP INDEX "{escaped_name}";')

        # Ensure unique index on (student_id, subject_id, attendance_date)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_student_subject_date 
            ON attendance(student_id, subject_id, attendance_date);
        """)
        conn.commit()

        # Seed initial subjects if none exist
        cursor.execute("SELECT COUNT(*) FROM subjects;")
        sub_count = cursor.fetchone()[0]
        if sub_count == 0:
            sample_subjects = [
                ('SUB001', 'MATH101', 'Mathematics', 'CSE-AI/ML', 'D'),
                ('SUB002', 'PHY101',  'Physics',     'CSE-AI/ML', 'D'),
                ('SUB003', 'DBMS101', 'Database Management Systems', 'CSE-AI/ML', 'D'),
                ('SUB004', 'DM101',   'Discrete Mathematics',        'CSE-AI/ML', 'D')
            ]
            cursor.executemany(
                "INSERT INTO subjects (subject_id, subject_code, subject_name, class_name, section) VALUES (?, ?, ?, ?, ?)",
                sample_subjects
            )
            conn.commit()
            print("[Database] Seeded initial subjects into subjects table.")

        # Check if sample students exist; if empty, insert initial records
        cursor.execute("SELECT COUNT(*) FROM students;")
        count = cursor.fetchone()[0]
        if count == 0:
            sample_students = [
                ('S001', 'Aarav Sharma', '21CS01', 'CSE-AI/ML', 'D'),
                ('S002', 'Bhavna Patel', '21CS02', 'CSE-AI/ML', 'D'),
                ('S003', 'Chirag Reddy', '21CS03', 'CSE-AI/ML', 'D'),
                ('S004', 'Divya Nair',   '21CS04', 'CSE-AI/ML', 'D'),
                ('S005', 'Eshaan Khan',  '21CS05', 'CSE-AI/ML', 'D'),
                ('S006', 'Farhan Ali',   '21CS06', 'CSE-AI/ML', 'D'),
                ('S007', 'Gayatri Joshi','21CS07', 'CSE-AI/ML', 'D'),
                ('S008', 'Harshitha V',  '21CS08', 'CSE-AI/ML', 'D'),
                ('S009', 'Ishan Gupta',  '21CS09', 'CSE-AI/ML', 'D'),
                ('S010', 'Juhi Mehta',   '21CS10', 'CSE-AI/ML', 'D')
            ]
            cursor.executemany(
                "INSERT INTO students (student_id, name, roll_number, class_name, section) VALUES (?, ?, ?, ?, ?)",
                sample_students
            )

            # Sample attendance for Mathematics (SUB001) and Physics (SUB002)
            sample_attendance = [
                # 2026-09-22 - Mathematics
                ('S001', 'SUB001', '2026-09-22', 'Present'), ('S002', 'SUB001', '2026-09-22', 'Present'),
                ('S003', 'SUB001', '2026-09-22', 'Present'), ('S004', 'SUB001', '2026-09-22', 'Present'),
                ('S005', 'SUB001', '2026-09-22', 'Absent'),  ('S006', 'SUB001', '2026-09-22', 'Present'),
                ('S007', 'SUB001', '2026-09-22', 'Present'), ('S008', 'SUB001', '2026-09-22', 'Absent'),
                ('S009', 'SUB001', '2026-09-22', 'Present'), ('S010', 'SUB001', '2026-09-22', 'Present'),
                # 2026-09-22 - Physics
                ('S001', 'SUB002', '2026-09-22', 'Present'), ('S002', 'SUB002', '2026-09-22', 'Present'),
                ('S003', 'SUB002', '2026-09-22', 'Present'), ('S004', 'SUB002', '2026-09-22', 'Absent'),
                ('S005', 'SUB002', '2026-09-22', 'Present'), ('S006', 'SUB002', '2026-09-22', 'Present'),
                ('S007', 'SUB002', '2026-09-22', 'Absent'),  ('S008', 'SUB002', '2026-09-22', 'Absent'),
                ('S009', 'SUB002', '2026-09-22', 'Present'), ('S010', 'SUB002', '2026-09-22', 'Present'),
                # 2026-09-25 - Mathematics
                ('S001', 'SUB001', '2026-09-25', 'Present'), ('S002', 'SUB001', '2026-09-25', 'Absent'),
                ('S003', 'SUB001', '2026-09-25', 'Present'), ('S004', 'SUB001', '2026-09-25', 'Present'),
                ('S005', 'SUB001', '2026-09-25', 'Absent'),  ('S006', 'SUB001', '2026-09-25', 'Absent'),
                ('S007', 'SUB001', '2026-09-25', 'Present'), ('S008', 'SUB001', '2026-09-25', 'Absent'),
                ('S009', 'SUB001', '2026-09-25', 'Absent'),  ('S010', 'SUB001', '2026-09-25', 'Present'),
                # 2026-09-26 - Mathematics
                ('S001', 'SUB001', '2026-09-26', 'Present'), ('S002', 'SUB001', '2026-09-26', 'Present'),
                ('S003', 'SUB001', '2026-09-26', 'Absent'),  ('S004', 'SUB001', '2026-09-26', 'Present'),
                ('S005', 'SUB001', '2026-09-26', 'Present'), ('S006', 'SUB001', '2026-09-26', 'Present'),
                ('S007', 'SUB001', '2026-09-26', 'Present'), ('S008', 'SUB001', '2026-09-26', 'Absent'),
                ('S009', 'SUB001', '2026-09-26', 'Absent'),  ('S010', 'SUB001', '2026-09-26', 'Present'),
            ]
            cursor.executemany(
                "INSERT INTO attendance (student_id, subject_id, attendance_date, status) VALUES (?, ?, ?, ?)",
                sample_attendance
            )
            conn.commit()
            print("[Database] Initialized SQLite database with sample students and attendance records.")

        conn.close()
        return True, "SQLite database initialized (fallback active)."


def fetch_all(query, params=None):
    """
    Executes a SELECT query and returns all matching rows as a list of dicts.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if ACTIVE_DB_TYPE == "sqlite":
            query = query.replace("%s", "?")
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        else:
            cursor.execute(query, params or ())
            return cursor.fetchall()
    finally:
        conn.close()


def fetch_one(query, params=None):
    """
    Executes a SELECT query and returns the first matching row as a dict.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if ACTIVE_DB_TYPE == "sqlite":
            query = query.replace("%s", "?")
            cursor.execute(query, params or ())
            row = cursor.fetchone()
            return dict(row) if row else None
        else:
            cursor.execute(query, params or ())
            return cursor.fetchone()
    finally:
        conn.close()


def execute_query(query, params=None):
    """
    Executes an INSERT, UPDATE, or DELETE query and returns the last inserted ID or affected row count.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if ACTIVE_DB_TYPE == "sqlite":
            query = query.replace("%s", "?")
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.lastrowid or cursor.rowcount
        else:
            cursor.execute(query, params or ())
            return cursor.lastrowid or cursor.rowcount
    finally:
        conn.close()


def get_db_status():
    """Returns metadata about the active database engine."""
    return {
        "engine": ACTIVE_DB_TYPE,
        "database": DB_NAME if ACTIVE_DB_TYPE == "mysql" else str(SQLITE_DB_PATH),
        "host": DB_HOST if ACTIVE_DB_TYPE == "mysql" else "local file",
        "user": DB_USER if ACTIVE_DB_TYPE == "mysql" else "sqlite"
    }


if __name__ == "__main__":
    success, msg = init_db()
    print("Database init result:", success, msg)
    students = fetch_all("SELECT * FROM students LIMIT 3")
    print(f"Sample students ({len(students)} rows):", students)
    status = get_db_status()
    print("Active DB Status:", status)
