/**
 * Student Attendance Analyzer Using Set Theory
 * ---------------------------------------------
 * Main Frontend Logic (Vanilla JavaScript)
 * Handles API calls, dynamic table generation, set operations display,
 * interactive Venn diagram rendering, and Excel export downloads.
 */

// Use Flask directly when the static frontend is opened outside its server.
const isLocalFrontend = window.location.protocol === "file:" ||
  (["localhost", "127.0.0.1"].includes(window.location.hostname) && window.location.port !== "5000");
const API_BASE = isLocalFrontend ? "http://127.0.0.1:5000/api" : "/api";

// ============================================================================
// 1. NOTIFICATIONS & TOAST SYSTEM
// ============================================================================

function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const icon = type === "success" ? "✓" : type === "error" ? "⚠" : "ℹ";
  toast.innerHTML = `<strong>${icon}</strong> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease-out";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ============================================================================
// 2. SYSTEM STATUS & NAVBAR INITIALIZATION
// ============================================================================

async function updateSystemStatus() {
  const statusElem = document.getElementById("db-status-info");
  try {
    const res = await fetch(`${API_BASE}/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (statusElem && data.database) {
      const engineName = data.database.engine === "mysql" ? "MySQL" : "SQLite";
      statusElem.textContent = `${engineName} (Connected) | ${data.total_students} Students`;
      statusElem.style.color = "";
    }
  } catch (err) {
    console.warn("Status check failed:", err);
    if (statusElem) {
      statusElem.textContent = "Server Offline";
      statusElem.style.color = "#dc2626";
    }
  }
}

// ============================================================================
// 3. MODAL DIALOG & SIDEBAR HELPERS
// ============================================================================

function initSidebarToggle() {
  const toggleBtn = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("app-sidebar");
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("open");
      sidebar.classList.toggle("collapsed");
    });
  }
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("active");
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("active");
}

// ============================================================================
// 4. MODULE: DASHBOARD (index.html)
// ============================================================================

async function loadDashboard() {
  const metricsContainer = document.getElementById("dashboard-metrics");
  if (!metricsContainer) return;

  try {
    const res = await fetch(`${API_BASE}/dashboard`);
    if (!res.ok) throw new Error("Dashboard API error");
    const data = await res.json();
    const m = data.metrics;

    const setElem = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setElem("stat-total-students", m.total_students);
    setElem("stat-present-today", m.present_today);
    setElem("stat-absent-today", m.absent_today);
    setElem("stat-eligible", m.students_above_75);
    setElem("stat-defaulters", m.defaulters_below_75);
    setElem("stat-overall-pct", `${m.overall_avg_percentage}%`);

    const dateLabel = document.getElementById("dashboard-date-label");
    if (dateLabel) {
      dateLabel.textContent = `Latest Record Date: ${m.latest_date} (${m.total_working_days} working days recorded)`;
    }

    renderTrendChart(data.trends);
  } catch (err) {
    console.error("Dashboard error:", err);
    showToast("Failed to load dashboard metrics.", "error");
  }
}

function renderTrendChart(trends) {
  const canvas = document.getElementById("attendanceChart");
  if (!canvas || !trends || trends.length === 0) return;

  if (window.Chart) {
    const labels = trends.map(t => t.attendance_date);
    const presentData = trends.map(t => t.present_count);
    const absentData = trends.map(t => t.absent_count);

    new Chart(canvas, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Present",
            data: presentData,
            backgroundColor: "#22c55e",
            borderRadius: 4
          },
          {
            label: "Absent",
            data: absentData,
            backgroundColor: "#ef4444",
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: "top" }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0 }
          }
        }
      }
    });
  }
}

// ============================================================================
// 5. MODULE: STUDENT MANAGEMENT (students.html)
// ============================================================================

let allStudents = [];

async function loadStudents() {
  const tableBody = document.getElementById("students-table-body");
  if (!tableBody) return;

  const searchInput = document.getElementById("student-search");
  const classFilter = document.getElementById("class-filter");

  const queryParams = new URLSearchParams();
  if (searchInput && searchInput.value.trim()) queryParams.set("search", searchInput.value.trim());
  if (classFilter && classFilter.value.trim()) queryParams.set("class_name", classFilter.value.trim());

  try {
    const res = await fetch(`${API_BASE}/students?${queryParams.toString()}`);
    if (!res.ok) throw new Error("Failed to load student directory");
    const data = await res.json();
    allStudents = data.students || [];

    const countElem = document.getElementById("student-count-display");
    if (countElem) countElem.textContent = `Showing ${allStudents.length} student(s)`;

    if (allStudents.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: #64748b;">No students found. Click "+ Add New Student" to enroll.</td></tr>`;
      return;
    }

    tableBody.innerHTML = allStudents.map((s, idx) => `
      <tr>
        <td><strong>#${idx + 1}</strong></td>
        <td><code>${escapeHtml(s.student_id)}</code></td>
        <td><strong>${escapeHtml(s.name)}</strong></td>
        <td>${escapeHtml(s.roll_number)}</td>
        <td><span class="badge badge-neutral">${escapeHtml(s.class_name)}</span></td>
        <td>${escapeHtml(s.section)}</td>
        <td>
          <div style="display: flex; gap: 0.35rem;">
            <button class="btn btn-info btn-sm" onclick="openViewStudentModal('${escapeHtml(s.student_id)}')">👁 View</button>
            <button class="btn btn-secondary btn-sm" onclick="openEditStudentModal('${escapeHtml(s.student_id)}')">✏ Edit</button>
            <button class="btn btn-danger btn-sm" onclick="deleteStudent('${escapeHtml(s.student_id)}')">🗑 Delete</button>
          </div>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Load students error:", err);
    const countElem = document.getElementById("student-count-display");
    if (countElem) countElem.textContent = "Unable to load student directory.";
    tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: #dc2626;">Unable to load student data. Please check the backend/database connection.</td></tr>`;
    showToast("Unable to load student data.", "error");
  }
}

function openAddStudentModal() {
  const form = document.getElementById("student-form");
  if (form) form.reset();
  const errBox = document.getElementById("student-modal-error");
  if (errBox) { errBox.style.display = "none"; errBox.textContent = ""; }
  
  const title = document.getElementById("student-modal-title");
  if (title) title.textContent = "Add New Student";
  
  const idInput = document.getElementById("form-student-id");
  if (idInput) {
    idInput.disabled = false;
    idInput.value = "";
  }
  
  const mode = document.getElementById("form-action-mode");
  if (mode) mode.value = "add";
  
  const btn = document.getElementById("btn-save-student");
  if (btn) { btn.disabled = false; btn.textContent = "Save Student"; }
  
  openModal("student-modal");
}

function openEditStudentModal(studentId) {
  const student = allStudents.find(s => s.student_id === studentId);
  if (!student) return;

  const errBox = document.getElementById("student-modal-error");
  if (errBox) { errBox.style.display = "none"; errBox.textContent = ""; }

  const title = document.getElementById("student-modal-title");
  if (title) title.textContent = `Edit Student: ${student.name}`;

  const idInput = document.getElementById("form-student-id");
  if (idInput) {
    idInput.value = student.student_id;
    idInput.disabled = true; // Primary ID cannot be modified in edit
  }

  document.getElementById("form-name").value = student.name;
  document.getElementById("form-roll").value = student.roll_number;
  document.getElementById("form-class").value = student.class_name;
  document.getElementById("form-section").value = student.section;
  document.getElementById("form-action-mode").value = "edit";

  const btn = document.getElementById("btn-save-student");
  if (btn) { btn.disabled = false; btn.textContent = "Update Student"; }

  openModal("student-modal");
}

async function openViewStudentModal(studentId) {
  const modalBody = document.getElementById("view-student-body");
  const modalTitle = document.getElementById("view-student-title");
  if (!modalBody) return;

  modalBody.innerHTML = `<div style="text-align:center; padding: 2rem;">Loading student profile...</div>`;
  openModal("view-student-modal");

  try {
    const res = await fetch(`${API_BASE}/students/${studentId}`);
    if (!res.ok) throw new Error("Student not found");
    const data = await res.json();
    const s = data.student;
    const summaries = data.subject_summary || [];

    if (modalTitle) modalTitle.textContent = `${s.name} (${s.student_id})`;

    const rowsHtml = summaries.map(sub => `
      <tr>
        <td><code>${escapeHtml(sub.subject_code)}</code></td>
        <td><strong>${escapeHtml(sub.subject_name)}</strong></td>
        <td style="text-align:center;">${sub.total_classes}</td>
        <td style="text-align:center; color:#15803d; font-weight:600;">${sub.present}</td>
        <td style="text-align:center; color:#b91c1c; font-weight:600;">${sub.absent}</td>
        <td style="text-align:center;">
          <span class="badge ${sub.percentage >= 75 ? 'badge-present' : 'badge-absent'}">${sub.percentage}%</span>
        </td>
      </tr>
    `).join("");

    modalBody.innerHTML = `
      <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:1rem; margin-bottom:1.25rem;">
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; font-size:0.88rem;">
          <div><strong>Student ID:</strong> <code>${escapeHtml(s.student_id)}</code></div>
          <div><strong>Roll Number:</strong> ${escapeHtml(s.roll_number)}</div>
          <div><strong>Class:</strong> ${escapeHtml(s.class_name)}</div>
          <div><strong>Section:</strong> ${escapeHtml(s.section)}</div>
          <div style="grid-column: span 2; margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center;">
            <span><strong>Overall Cumulative Attendance:</strong></span>
            <span class="badge ${data.overall_percentage >= 75 ? 'badge-present' : 'badge-absent'}" style="font-size:0.95rem; padding:0.3rem 0.75rem;">
              ${data.overall_percentage}% (${data.total_present}/${data.total_classes} classes)
            </span>
          </div>
        </div>
      </div>

      <h4 style="margin: 0 0 0.5rem 0; font-size:0.95rem; color:#1e293b;">Subject Attendance Breakdown</h4>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Subject</th>
              <th style="text-align:center;">Total</th>
              <th style="text-align:center;">Present</th>
              <th style="text-align:center;">Absent</th>
              <th style="text-align:center;">Percentage</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml.length > 0 ? rowsHtml : '<tr><td colspan="6" style="text-align:center; padding:1.5rem;">No attendance recorded yet for this student.</td></tr>'}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    console.error("View student error:", err);
    modalBody.innerHTML = `<div style="color:#dc2626; text-align:center; padding:2rem;">Failed to load student details.</div>`;
  }
}

async function handleStudentFormSubmit(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }

  const errBox = document.getElementById("student-modal-error");
  if (errBox) { errBox.style.display = "none"; errBox.textContent = ""; }

  const mode = document.getElementById("form-action-mode").value;
  const student_id = document.getElementById("form-student-id").value.trim().toUpperCase();
  const name = document.getElementById("form-name").value.trim();
  const roll_number = document.getElementById("form-roll").value.trim().toUpperCase();
  const class_name = document.getElementById("form-class").value.trim();
  const section = document.getElementById("form-section").value.trim().toUpperCase();

  // Validate required fields
  if (!student_id || !name || !roll_number || !class_name || !section) {
    const msg = "All fields (Student ID, Name, Roll No, Class, Section) are required.";
    if (errBox) { errBox.textContent = msg; errBox.style.display = "block"; }
    showToast(msg, "error");
    return;
  }

  const btn = document.getElementById("btn-save-student");
  if (btn) {
    btn.disabled = true;
    btn.textContent = mode === "add" ? "Saving Student..." : "Updating Student...";
  }

  const payload = { student_id, name, roll_number, class_name, section };

  try {
    let res;
    if (mode === "add") {
      res = await fetch(`${API_BASE}/students`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    } else {
      res = await fetch(`${API_BASE}/students/${student_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    }

    const result = await res.json();
    if (!res.ok) {
      const errorMsg = result.error || "Failed to save student record.";
      if (errBox) { errBox.textContent = errorMsg; errBox.style.display = "block"; }
      showToast(errorMsg, "error");
      if (btn) {
        btn.disabled = false;
        btn.textContent = mode === "add" ? "Save Student" : "Update Student";
      }
      return;
    }

    showToast(result.message || "Student added successfully.", "success");
    closeModal("student-modal");

    // Automatically refresh student directory table immediately
    if (document.getElementById("students-table-body")) {
      loadStudents();
    }
    await populateStudentDropdowns();
    if (document.getElementById("dashboard-metrics")) {
      loadDashboard();
    }
    updateSystemStatus();
    populateClassFilters();
  } catch (err) {
    console.error("Student form error:", err);
    const networkMsg = "Network or database connection error while saving student.";
    if (errBox) { errBox.textContent = networkMsg; errBox.style.display = "block"; }
    showToast(networkMsg, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = mode === "add" ? "Save Student" : "Update Student";
    }
  }
}

async function loadSampleCollegeData() {
  if (!confirm("Load standard student cohort with attendance history for demo/testing?")) return;
  try {
    const res = await fetch(`${API_BASE}/students/sample-data`, { method: "POST" });
    const data = await res.json();
    showToast(data.message || "Sample college data loaded!", "success");
    if (document.getElementById("students-table-body")) loadStudents();
    if (document.getElementById("dashboard-metrics")) loadDashboard();
    updateSystemStatus();
    populateClassFilters();
  } catch (err) {
    console.error("Load sample error:", err);
    showToast("Error loading sample data.", "error");
  }
}

async function deleteStudent(studentId) {
  if (!confirm(`Are you sure you want to delete student ${studentId}? This will also delete their attendance records.`)) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/students/${studentId}`, { method: "DELETE" });
    const result = await res.json();
    if (!res.ok) {
      showToast(result.error || "Failed to delete student.", "error");
      return;
    }

    showToast(result.message || "Student deleted successfully.", "success");
    loadStudents();
    populateStudentDropdowns();
    updateSystemStatus();
  } catch (err) {
    console.error("Delete student error:", err);
    showToast("Error deleting student.", "error");
  }
}

// ============================================================================
// 6. MODULE: SUBJECT MANAGEMENT (subjects.html)
// ============================================================================

let allSubjects = [];

async function loadSubjects() {
  const tableBody = document.getElementById("subjects-table-body");
  if (!tableBody) return;

  const searchInput = document.getElementById("subject-search");
  const classFilter = document.getElementById("subject-class-filter");

  const queryParams = new URLSearchParams();
  if (searchInput && searchInput.value.trim()) queryParams.set("search", searchInput.value.trim());
  if (classFilter && classFilter.value.trim()) queryParams.set("class_name", classFilter.value.trim());

  try {
    const res = await fetch(`${API_BASE}/subjects?${queryParams.toString()}`);
    if (!res.ok) throw new Error("Failed to load subjects");
    const data = await res.json();
    allSubjects = data.subjects || [];

    const countElem = document.getElementById("subject-count-display");
    if (countElem) countElem.textContent = `Showing ${allSubjects.length} subject(s)`;

    if (allSubjects.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: #64748b;">No subjects found. Click "+ Add Subject" to create one.</td></tr>`;
      return;
    }

    tableBody.innerHTML = allSubjects.map((sub, idx) => `
      <tr>
        <td><strong>#${idx + 1}</strong></td>
        <td><code>${escapeHtml(sub.subject_id)}</code></td>
        <td><span class="badge badge-eligible">${escapeHtml(sub.subject_code)}</span></td>
        <td><strong>${escapeHtml(sub.subject_name)}</strong></td>
        <td><span class="badge badge-neutral">${escapeHtml(sub.class_name)}</span></td>
        <td>${escapeHtml(sub.section)}</td>
        <td>
          <div style="display: flex; gap: 0.35rem;">
            <button class="btn btn-secondary btn-sm" onclick="openEditSubjectModal('${escapeHtml(sub.subject_id)}')">✏ Edit</button>
            <button class="btn btn-danger btn-sm" onclick="deleteSubject('${escapeHtml(sub.subject_id)}')">🗑 Delete</button>
          </div>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Load subjects error:", err);
    const countElem = document.getElementById("subject-count-display");
    if (countElem) countElem.textContent = "Unable to load subjects.";
    tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: #dc2626;">Unable to load subjects from database.</td></tr>`;
    showToast("Failed to load subjects.", "error");
  }
}

function openAddSubjectModal() {
  const form = document.getElementById("subject-form");
  if (form) form.reset();
  const errBox = document.getElementById("subject-modal-error");
  if (errBox) { errBox.style.display = "none"; errBox.textContent = ""; }

  const title = document.getElementById("subject-modal-title");
  if (title) title.textContent = "Add New Subject";

  const idInput = document.getElementById("form-subject-id");
  if (idInput) { idInput.disabled = false; idInput.value = ""; }

  const mode = document.getElementById("form-subject-mode");
  if (mode) mode.value = "add";

  const btn = document.getElementById("btn-save-subject");
  if (btn) { btn.disabled = false; btn.textContent = "Save Subject"; }

  openModal("subject-modal");
}

function openEditSubjectModal(subjectId) {
  const subject = allSubjects.find(s => s.subject_id === subjectId);
  if (!subject) return;

  const errBox = document.getElementById("subject-modal-error");
  if (errBox) { errBox.style.display = "none"; errBox.textContent = ""; }

  const title = document.getElementById("subject-modal-title");
  if (title) title.textContent = `Edit Subject: ${subject.subject_name}`;

  const idInput = document.getElementById("form-subject-id");
  if (idInput) {
    idInput.value = subject.subject_id;
    idInput.disabled = true; // Primary ID cannot be modified in edit
  }

  document.getElementById("form-subject-code").value = subject.subject_code;
  document.getElementById("form-subject-name").value = subject.subject_name;
  document.getElementById("form-subject-class").value = subject.class_name;
  document.getElementById("form-subject-section").value = subject.section;
  document.getElementById("form-subject-mode").value = "edit";

  const btn = document.getElementById("btn-save-subject");
  if (btn) { btn.disabled = false; btn.textContent = "Update Subject"; }

  openModal("subject-modal");
}

async function handleSubjectFormSubmit(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }

  const errBox = document.getElementById("subject-modal-error");
  if (errBox) { errBox.style.display = "none"; errBox.textContent = ""; }

  const mode = document.getElementById("form-subject-mode").value;
  const subject_id = document.getElementById("form-subject-id").value.trim().toUpperCase();
  const subject_code = document.getElementById("form-subject-code").value.trim().toUpperCase();
  const subject_name = document.getElementById("form-subject-name").value.trim();
  const class_name = document.getElementById("form-subject-class").value.trim();
  const section = document.getElementById("form-subject-section").value.trim().toUpperCase();

  if (!subject_id || !subject_code || !subject_name || !class_name || !section) {
    const msg = "All fields (Subject ID, Code, Name, Class, Section) are required.";
    if (errBox) { errBox.textContent = msg; errBox.style.display = "block"; }
    showToast(msg, "error");
    return;
  }

  const btn = document.getElementById("btn-save-subject");
  if (btn) {
    btn.disabled = true;
    btn.textContent = mode === "add" ? "Saving..." : "Updating...";
  }

  const payload = { subject_id, subject_code, subject_name, class_name, section };

  try {
    let res;
    if (mode === "add") {
      res = await fetch(`${API_BASE}/subjects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    } else {
      res = await fetch(`${API_BASE}/subjects/${subject_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    }

    const result = await res.json();
    if (!res.ok) {
      const errorMsg = result.error || "Failed to save subject.";
      if (errBox) { errBox.textContent = errorMsg; errBox.style.display = "block"; }
      showToast(errorMsg, "error");
      if (btn) {
        btn.disabled = false;
        btn.textContent = mode === "add" ? "Save Subject" : "Update Subject";
      }
      return;
    }

    showToast(result.message || "Subject saved successfully.", "success");
    closeModal("subject-modal");

    if (document.getElementById("subjects-table-body")) {
      loadSubjects();
    }
    populateSubjectDropdowns();
  } catch (err) {
    console.error("Subject form error:", err);
    const networkMsg = "Network or database error while saving subject.";
    if (errBox) { errBox.textContent = networkMsg; errBox.style.display = "block"; }
    showToast(networkMsg, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = mode === "add" ? "Save Subject" : "Update Subject";
    }
  }
}

async function deleteSubject(subjectId) {
  if (!confirm(`Are you sure you want to delete subject ${subjectId}? This will remove associated attendance records.`)) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/subjects/${subjectId}`, { method: "DELETE" });
    const result = await res.json();
    if (!res.ok) {
      showToast(result.error || "Failed to delete subject.", "error");
      return;
    }

    showToast(result.message || "Subject deleted successfully.", "success");
    loadSubjects();
    populateSubjectDropdowns();
  } catch (err) {
    console.error("Delete subject error:", err);
    showToast("Error deleting subject.", "error");
  }
}

// ============================================================================
// 7. MODULE: ATTENDANCE RECORDING (attendance.html)
// ============================================================================

let currentAttendanceRecords = [];

async function loadAttendanceSheet() {
  const datePicker = document.getElementById("attendance-date-picker");
  const subjectSelect = document.getElementById("attendance-subject-select");
  const classFilter = document.getElementById("attendance-class-filter");
  const sectionFilter = document.getElementById("attendance-section-filter");
  const tableBody = document.getElementById("attendance-table-body");
  if (!tableBody) return;

  const dateVal = datePicker ? datePicker.value : "";
  const subjectVal = subjectSelect ? subjectSelect.value : "";
  const classVal = classFilter ? classFilter.value : "";
  const sectionVal = sectionFilter ? sectionFilter.value : "";

  const params = new URLSearchParams();
  if (dateVal) params.set("date", dateVal);
  if (subjectVal) params.set("subject_id", subjectVal);
  if (classVal) params.set("class_name", classVal);
  if (sectionVal) params.set("section", sectionVal);

  tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem;">Loading attendance roster...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE}/attendance?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to load attendance roster");
    const data = await res.json();
    currentAttendanceRecords = data.records || [];

    // Sync date picker if empty
    if (datePicker && !datePicker.value && data.date) {
      datePicker.value = data.date;
    }

    // Update daily counter badges
    const setElem = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };
    setElem("sheet-total-count", data.total_students);
    setElem("sheet-present-count", data.present_count);
    setElem("sheet-absent-count", data.absent_count);

    if (currentAttendanceRecords.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem; color: #64748b;">No students found for the selected filters.</td></tr>`;
      return;
    }

    tableBody.innerHTML = currentAttendanceRecords.map((r, idx) => {
      const isPresent = r.status === "Present";
      const isAbsent = r.status === "Absent";

      return `
        <tr id="row-${escapeHtml(r.student_id)}">
          <td><strong>#${idx + 1}</strong></td>
          <td><code>${escapeHtml(r.student_id)}</code></td>
          <td><strong>${escapeHtml(r.name)}</strong></td>
          <td>${escapeHtml(r.roll_number)}</td>
          <td><span class="badge badge-neutral">${escapeHtml(r.class_name)}-${escapeHtml(r.section)}</span></td>
          <td>
            <div class="status-toggle-group">
              <button type="button" 
                      class="status-toggle-btn ${isPresent ? 'active-present' : ''}" 
                      id="btn-pres-${escapeHtml(r.student_id)}"
                      onclick="setStudentStatus('${escapeHtml(r.student_id)}', 'Present')">
                ✓ Present
              </button>
              <button type="button" 
                      class="status-toggle-btn ${isAbsent ? 'active-absent' : ''}" 
                      id="btn-abs-${escapeHtml(r.student_id)}"
                      onclick="setStudentStatus('${escapeHtml(r.student_id)}', 'Absent')">
                ✕ Absent
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Load attendance error:", err);
    tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem; color: #dc2626;">Failed to load attendance roster from database.</td></tr>`;
    showToast("Failed to load attendance roster.", "error");
  }
}

function setStudentStatus(studentId, newStatus) {
  const item = currentAttendanceRecords.find(r => r.student_id === studentId);
  if (item) {
    item.status = newStatus;
  }
  const btnPres = document.getElementById(`btn-pres-${studentId}`);
  const btnAbs = document.getElementById(`btn-abs-${studentId}`);
  if (btnPres && btnAbs) {
    if (newStatus === "Present") {
      btnPres.className = "status-toggle-btn active-present";
      btnAbs.className = "status-toggle-btn";
    } else if (newStatus === "Absent") {
      btnPres.className = "status-toggle-btn";
      btnAbs.className = "status-toggle-btn active-absent";
    }
  }

  // Update summary counts locally
  const presCount = currentAttendanceRecords.filter(r => r.status === "Present").length;
  const absCount = currentAttendanceRecords.filter(r => r.status === "Absent").length;
  const pEl = document.getElementById("sheet-present-count");
  const aEl = document.getElementById("sheet-absent-count");
  if (pEl) pEl.textContent = presCount;
  if (aEl) aEl.textContent = absCount;
}

function markAll(status) {
  currentAttendanceRecords.forEach(r => {
    r.status = status;
    const btnPres = document.getElementById(`btn-pres-${r.student_id}`);
    const btnAbs = document.getElementById(`btn-abs-${r.student_id}`);
    if (btnPres && btnAbs) {
      if (status === "Present") {
        btnPres.className = "status-toggle-btn active-present";
        btnAbs.className = "status-toggle-btn";
      } else {
        btnPres.className = "status-toggle-btn";
        btnAbs.className = "status-toggle-btn active-absent";
      }
    }
  });

  const pEl = document.getElementById("sheet-present-count");
  const aEl = document.getElementById("sheet-absent-count");
  if (pEl) pEl.textContent = status === "Present" ? currentAttendanceRecords.length : 0;
  if (aEl) aEl.textContent = status === "Absent" ? currentAttendanceRecords.length : 0;

  showToast(`Marked all students as ${status}. Click "Save Attendance" to commit.`, "info");
}

async function saveAttendanceBatch() {
  const datePicker = document.getElementById("attendance-date-picker");
  const subjectSelect = document.getElementById("attendance-subject-select");
  const attendanceDate = datePicker ? datePicker.value : "";
  const subjectId = subjectSelect ? subjectSelect.value : "";

  if (!attendanceDate) {
    showToast("Please choose an attendance date.", "error");
    return;
  }

  if (!subjectId) {
    showToast("Please select a subject from the list.", "error");
    return;
  }

  const recordsToSave = currentAttendanceRecords
    .filter(r => r.status === "Present" || r.status === "Absent")
    .map(r => ({
      student_id: r.student_id,
      status: r.status
    }));

  if (recordsToSave.length === 0) {
    showToast("Please mark Present or Absent for at least one student.", "error");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/attendance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        date: attendanceDate,
        subject_id: subjectId,
        records: recordsToSave
      })
    });

    const result = await res.json();
    if (!res.ok) {
      showToast(result.error || "Failed to save attendance.", "error");
      return;
    }

    showToast("Attendance saved successfully.", "success");
    loadAttendanceSheet();
  } catch (err) {
    console.error("Save attendance error:", err);
    showToast("Error saving attendance to database.", "error");
  }
}

// ============================================================================
// 8. MODULE: SET THEORY & DYNAMIC VENN DIAGRAM (analysis.html)
// ============================================================================

let currentAnalysisData = null;

function toggleAnalysisMode() {
  const modeSelect = document.getElementById("analysis-mode-select");
  const compBox = document.getElementById("comparison-subject-box");
  if (modeSelect && compBox) {
    compBox.style.display = modeSelect.value === "comparison" ? "block" : "none";
  }
  loadSetTheoryAnalysis();
}

async function loadSetTheoryAnalysis() {
  const subjectSelect = document.getElementById("analysis-subject-select");
  const modeSelect = document.getElementById("analysis-mode-select");
  const subject2Select = document.getElementById("analysis-subject2-select");
  const datePicker = document.getElementById("analysis-date-picker");
  const classSelect = document.getElementById("analysis-class-filter");
  const sectionSelect = document.getElementById("analysis-section-filter");
  if (!subjectSelect) return;

  const subjectVal = subjectSelect.value;
  const modeVal = modeSelect ? modeSelect.value : "single";
  const subject2Val = subject2Select ? subject2Select.value : "";
  const dateVal = datePicker ? datePicker.value : "";
  const classVal = classSelect ? classSelect.value : "";
  const sectionVal = sectionSelect ? sectionSelect.value : "";

  const params = new URLSearchParams();
  if (subjectVal) params.set("subject_id", subjectVal);
  if (modeVal) params.set("mode", modeVal);
  if (modeVal === "comparison" && subject2Val) params.set("subject2_id", subject2Val);
  if (dateVal) params.set("date", dateVal);
  if (classVal) params.set("class_name", classVal);
  if (sectionVal) params.set("section", sectionVal);

  try {
    const res = await fetch(`${API_BASE}/analysis?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to load Set Theory analysis");
    currentAnalysisData = await res.json();
    const sets = currentAnalysisData.sets;

    // Update Evaluated Date Picker if empty
    if (datePicker && !datePicker.value && currentAnalysisData.selected_date) {
      datePicker.value = currentAnalysisData.selected_date;
    }

    // Update Summary Statistics Cards (Section 10)
    const setElem = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setElem("stat-u-count", currentAnalysisData.universal_count);
    if (currentAnalysisData.mode === "single") {
      setElem("stat-a-count", currentAnalysisData.present_count);
      setElem("stat-b-count", currentAnalysisData.absent_count);
      setElem("stat-pct", `${currentAnalysisData.attendance_percentage}%`);
      const aDesc = document.getElementById("stat-a-desc");
      const bDesc = document.getElementById("stat-b-desc");
      if (aDesc) aDesc.textContent = "Present Students (A)";
      if (bDesc) bDesc.textContent = "Absent Students (B)";
    } else {
      setElem("stat-a-count", currentAnalysisData.subject1_present);
      setElem("stat-b-count", currentAnalysisData.subject2_present);
      const either = currentAnalysisData.either_present || 0;
      const u = currentAnalysisData.universal_count || 1;
      setElem("stat-pct", `${roundNumber((either / u) * 100, 2)}%`);
      const aDesc = document.getElementById("stat-a-desc");
      const bDesc = document.getElementById("stat-b-desc");
      if (aDesc) aDesc.textContent = `Present in ${currentAnalysisData.subject1 ? currentAnalysisData.subject1.subject_code : 'Sub 1'}`;
      if (bDesc) bDesc.textContent = `Present in ${currentAnalysisData.subject2 ? currentAnalysisData.subject2.subject_code : 'Sub 2'}`;
    }

    // Update Set Cards
    updateSetCard("set-u", sets.U);
    updateSetCard("set-a", sets.A);
    updateSetCard("set-b", sets.B);
    updateSetCard("set-union", sets.union);
    updateSetCard("set-intersection", sets.intersection);
    updateSetCard("set-a-minus-b", sets.diff_A_minus_B);
    updateSetCard("set-b-minus-a", sets.diff_B_minus_A);
    updateSetCard("set-comp-a", sets.complement_A || sets.diff_B_minus_A);
    updateSetCard("set-comp-b", sets.complement_B || sets.diff_A_minus_B);

    // Update Dynamic Venn Diagram
    renderVennDiagram(currentAnalysisData);

    // Default inspect Present set A or Union
    if (sets.A && sets.A.students) {
      displaySetDetails("A", sets.A.label, sets.A.students);
    }
  } catch (err) {
    console.error("Set theory analysis error:", err);
    showToast("Failed to load Set Theory analysis.", "error");
  }
}

function updateSetCard(cardId, setData) {
  const card = document.getElementById(cardId);
  if (!card || !setData) return;

  const countBadge = card.querySelector(".set-count-badge");
  if (countBadge) countBadge.textContent = `n = ${setData.count}`;

  const titleElem = card.querySelector(".set-title");
  if (titleElem && setData.label) titleElem.textContent = setData.label;

  const descElem = card.querySelector(".set-desc");
  if (descElem && setData.description) descElem.textContent = setData.description;

  const elementsPreview = card.querySelector(".set-elements-preview");
  if (elementsPreview) {
    if (!setData.students || setData.students.length === 0) {
      elementsPreview.textContent = "∅ (Empty Set)";
    } else {
      const ids = setData.students.map(s => s.student_id).join(", ");
      elementsPreview.textContent = `{ ${ids} }`;
    }
  }
}

function renderVennDiagram(data) {
  const venn = data.venn_diagram;
  if (!venn) return;

  // ── Read counts ──────────────────────────────────────────────────────────
  const nOnlyA     = venn.only_A        ? venn.only_A.count        : 0;
  const nInter     = venn.intersection  ? venn.intersection.count  : 0;
  const nOnlyB     = venn.only_B        ? venn.only_B.count        : 0;
  const nNeither   = venn.neither       ? venn.neither.count       : 0;
  const nA         = nOnlyA + nInter;   // |A|
  const nB         = nOnlyB + nInter;   // |B|
  const nU         = data.universal_count || (nA + nB - nInter + nNeither) || 1;

  // ── Update count text nodes ───────────────────────────────────────────────
  const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  setText("venn-text-only-a",      nOnlyA);
  setText("venn-text-intersection", nInter);
  setText("venn-text-only-b",      nOnlyB);

  // Use the equal-circle layout from the reference; counts remain data-driven.
  const rA = 125;
  const rB = 125;
  const cxA = 220;
  const cxB = 360;
  const labelXA = 180;
  const labelXB = 400;
  const interXMid = 290;
  const circleY = 150;

  // ── Animate the SVG elements ──────────────────────────────────────────────
  function setAttr(id, attrs) {
    const el = document.getElementById(id);
    if (!el) return;
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  }

  setAttr("venn-circle-a", { cx: cxA, cy: circleY, r: rA });
  setAttr("venn-circle-b", { cx: cxB, cy: circleY, r: rB });
  setAttr("venn-inter-fill", { cx: cxB, cy: circleY, r: rB });
  setAttr("venn-clip-circle-a", { cx: cxA, cy: circleY, r: rA });
  setAttr("venn-mask-exclude-a", { cx: cxA, cy: circleY, r: rA });
  setAttr("venn-mask-exclude-b", { cx: cxB, cy: circleY, r: rB });
  setAttr("venn-mask-neither-exclude-a", { cx: cxA, cy: circleY, r: rA });
  setAttr("venn-mask-neither-exclude-b", { cx: cxB, cy: circleY, r: rB });
  setAttr("venn-highlight-only-a", { cx: cxA, cy: circleY, r: rA });
  setAttr("venn-highlight-only-b", { cx: cxB, cy: circleY, r: rB });
  setAttr("venn-highlight-intersection", { cx: cxB, cy: circleY, r: rB });
  setAttr("venn-highlight-neither", { x: 15, y: 12, width: 550, height: 276 });

  // Reposition count labels
  setAttr("venn-text-only-a",       { x: labelXA });
  setAttr("venn-sublabel-a",        { x: labelXA });
  setAttr("venn-text-intersection", { x: interXMid });
  setAttr("venn-sublabel-inter",    { x: interXMid });
  setAttr("venn-text-only-b",       { x: labelXB });
  setAttr("venn-sublabel-b",        { x: labelXB });

  // ── Update human-readable labels ─────────────────────────────────────────
  const subA = document.getElementById("venn-sublabel-a");
  const subInter = document.getElementById("venn-sublabel-inter");
  const subB = document.getElementById("venn-sublabel-b");
  const legendInter = document.getElementById("legend-text-inter");

  if (data.mode === "comparison") {
    const s1 = data.subject1 ? data.subject1.subject_code : "Sub A";
    const s2 = data.subject2 ? data.subject2.subject_code : "Sub B";
    if (subA) subA.textContent = "Only A";
    if (subInter) subInter.textContent = "A \u2229 B";
    if (subB) subB.textContent = "Only B";
    if (legendInter) legendInter.textContent = `A \u2229 B: ${s1} and ${s2}`;
    const modeLabel = document.getElementById("venn-mode-label");
    if (modeLabel) modeLabel.textContent = `${s1} vs ${s2} \u2014 Multi-Subject Comparison`;
  } else {
    if (subA) subA.textContent = `Present`;
    if (subInter) subInter.textContent = `A \u2229 B (\u2205)`;
    if (subB) subB.textContent = `Absent`;
    if (legendInter) legendInter.textContent = "A \u2229 B: Empty Set (\u2205)";
    const modeLabel = document.getElementById("venn-mode-label");
    if (modeLabel) modeLabel.textContent = "Single-subject attendance";
  }

  // ── Set Relation Badges ──────────────────────────────────────────────────
  const strip = document.getElementById("set-relation-strip");
  if (!strip) return;

  if (data.mode !== "comparison") {
    // In single mode A ∩ B = ∅ always (present vs absent)
    strip.innerHTML = `
      <span class="rel-badge rel-true">A \u222a B = U \u2714</span>
      <span class="rel-badge rel-true">A \u2229 B = \u2205 \u2714</span>
      <span class="rel-badge rel-info">n(A) = ${nA} &nbsp;|&nbsp; n(B) = ${nB} &nbsp;|&nbsp; n(U) = ${nU}</span>
    `;
    return;
  }

  // Comparison mode — compute all set relations
  const relations = [];

  // A = B (equal sets)
  const isEqual = nOnlyA === 0 && nOnlyB === 0 && nInter > 0;
  relations.push({ label: `A = B`, val: isEqual });

  // A \u2282 B (proper subset)
  const isASubB = nOnlyA === 0 && nInter > 0 && nOnlyB > 0;
  relations.push({ label: `A \u2282 B`, val: isASubB });

  // B \u2282 A (proper subset)
  const isBSubA = nOnlyB === 0 && nInter > 0 && nOnlyA > 0;
  relations.push({ label: `B \u2282 A`, val: isBSubA });

  // Disjoint
  const isDisjoint = nInter === 0;
  relations.push({ label: `A \u2229 B = \u2205 (Disjoint)`, val: isDisjoint });

  // Overlapping (non-empty intersection, neither is subset of other)
  const isOverlapping = nInter > 0 && !isEqual && !isASubB && !isBSubA;
  relations.push({ label: `A \u2229 B \u2260 \u2205 (Overlap)`, val: isOverlapping });

  // Union = U?
  const isUnionU = (nOnlyA + nInter + nOnlyB) >= nU;
  relations.push({ label: `A \u222a B = U`, val: isUnionU });

  // Cardinality info
  const s1code = data.subject1 ? data.subject1.subject_code : "A";
  const s2code = data.subject2 ? data.subject2.subject_code : "B";

  strip.innerHTML = relations.map(r =>
    `<span class="rel-badge ${r.val ? 'rel-true' : 'rel-false'}">${r.label} ${r.val ? '\u2714' : '\u2718'}</span>`
  ).join("") +
  `<span class="rel-badge rel-info">n(${s1code})=${nA} &nbsp;n(${s2code})=${nB} &nbsp;n(\u2229)=${nInter} &nbsp;n(U)=${nU}</span>`;
}

function selectVennRegion(regionKey) {
  if (!currentAnalysisData) return;
  const venn = currentAnalysisData.venn_diagram;
  if (!venn) return;

  if (regionKey === "only_A" && venn.only_A) {
    displaySetDetails("A", venn.only_A.label, venn.only_A.students);
  } else if (regionKey === "intersection" && venn.intersection) {
    displaySetDetails("intersection", venn.intersection.label, venn.intersection.students);
  } else if (regionKey === "only_B" && venn.only_B) {
    displaySetDetails("B", venn.only_B.label, venn.only_B.students);
  } else if (regionKey === "neither" && venn.neither) {
    displaySetDetails("neither", venn.neither.label, venn.neither.students);
  }
}

function highlightVennSelection(key) {
  const regionMap = {
    "U": ["universe", "only-a", "intersection", "only-b", "neither"],
    "A": ["only-a", "intersection"],
    "B": ["only-b", "intersection"],
    "union": ["only-a", "intersection", "only-b"],
    "intersection": ["intersection"],
    "A-B": ["only-a"],
    "only_A": ["only-a"],
    "B-A": ["only-b"],
    "only_B": ["only-b"],
    "A'": ["only-b", "neither"],
    "B'": ["only-a", "neither"],
    "neither": ["neither"]
  };
  const selected = new Set(regionMap[key] || []);
  const vennRegionIds = {
    "universe": "venn-highlight-universe",
    "only-a": "venn-highlight-only-a",
    "intersection": "venn-highlight-intersection",
    "only-b": "venn-highlight-only-b",
    "neither": "venn-highlight-neither"
  };

  Object.entries(vennRegionIds).forEach(([region, id]) => {
    const element = document.getElementById(id);
    if (element) element.classList.toggle("active", selected.has(region));
  });
}

function displaySetDetails(key, title, studentList) {
  const titleElem = document.getElementById("set-details-title");
  const countElem = document.getElementById("set-details-count");
  const bodyElem = document.getElementById("set-details-table-body");
  highlightVennSelection(key);

  // Highlight active set card
  document.querySelectorAll(".set-card").forEach(c => {
    c.style.borderColor = "#e2e8f0";
    c.style.boxShadow = "none";
  });
  if (key) {
    const cardMap = {
      "U": "set-u", "A": "set-a", "B": "set-b",
      "union": "set-union", "intersection": "set-intersection",
      "A-B": "set-a-minus-b", "only_A": "set-a-minus-b",
      "B-A": "set-b-minus-a", "only_B": "set-b-minus-a",
      "A'": "set-comp-a", "B'": "set-comp-b"
    };
    const cardId = cardMap[key];
    if (cardId) {
      const card = document.getElementById(cardId);
      if (card) {
        card.style.borderColor = "#1d4ed8";
        card.style.boxShadow = "0 0 0 2px rgba(29, 78, 216, 0.25)";
      }
    }
  }

  if (titleElem) titleElem.textContent = title || "Set Inspection";
  if (countElem) countElem.textContent = `${studentList ? studentList.length : 0} Student(s)`;

  if (bodyElem) {
    if (!studentList || studentList.length === 0) {
      bodyElem.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem; color: #64748b;">No students in this set (Set is Empty ∅).</td></tr>`;
    } else {
      bodyElem.innerHTML = studentList.map((s, idx) => `
        <tr>
          <td><strong>#${idx + 1}</strong></td>
          <td><code>${escapeHtml(s.student_id)}</code></td>
          <td><strong>${escapeHtml(s.name)}</strong></td>
          <td>${escapeHtml(s.roll_number)}</td>
          <td><span class="badge badge-neutral">${escapeHtml(s.class_name)}-${escapeHtml(s.section)}</span></td>
          <td>
            <button class="btn btn-info btn-sm" onclick="openViewStudentModal('${escapeHtml(s.student_id)}')">Profile</button>
          </td>
        </tr>
      `).join("");
    }
  }
}

// ============================================================================
// 9. MODULE: ACADEMIC REPORTS & EXCEL EXPORT (reports.html)
// ============================================================================

async function switchReportTab(tabName) {
  document.querySelectorAll(".report-tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });

  document.querySelectorAll(".report-section").forEach(sec => sec.style.display = "none");

  const target = document.getElementById(`report-${tabName}`);
  if (target) target.style.display = "block";

  if (tabName === "academic") loadAcademicReport();
  else if (tabName === "individual") loadIndividualStudentReport();
  else if (tabName === "defaulters") loadDefaultersReport();
  else if (tabName === "daily") loadDailyReport();
}

async function loadAcademicReport() {
  const tbody = document.getElementById("academic-report-tbody");
  if (!tbody) return;

  const sFilter = document.getElementById("report-student-filter");
  const subFilter = document.getElementById("report-subject-filter");
  const classFilter = document.getElementById("report-class-filter");
  const secFilter = document.getElementById("report-section-filter");
  const fromFilter = document.getElementById("report-date-from");
  const toFilter = document.getElementById("report-date-to");

  const params = new URLSearchParams();
  if (sFilter && sFilter.value) params.set("student_id", sFilter.value);
  if (subFilter && subFilter.value) params.set("subject_id", subFilter.value);
  if (classFilter && classFilter.value) params.set("class_name", classFilter.value);
  if (secFilter && secFilter.value) params.set("section", secFilter.value);
  if (fromFilter && fromFilter.value) params.set("date_from", fromFilter.value);
  if (toFilter && toFilter.value) params.set("date_to", toFilter.value);

  tbody.innerHTML = `<tr><td colspan="12" style="text-align:center; padding: 2rem;">Generating report from database records...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE}/reports/academic?${params.toString()}`);
    if (!res.ok) throw new Error("Report fetch failed");
    const data = await res.json();
    const rows = data.report || [];

    const countElem = document.getElementById("academic-report-count");
    if (countElem) countElem.textContent = `Total Records: ${rows.length}`;

    if (rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="12" style="text-align:center; padding: 2rem; color: #64748b;">No attendance records found for the selected criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map((r, idx) => {
      const badge = r.is_eligible
        ? `<span class="badge badge-present">✓ Eligible</span>`
        : `<span class="badge badge-absent">⚠ Defaulter</span>`;

      return `
        <tr>
          <td><strong>#${idx + 1}</strong></td>
          <td><code>${escapeHtml(r.student_id)}</code></td>
          <td>${escapeHtml(r.roll_number)}</td>
          <td><strong>${escapeHtml(r.student_name)}</strong></td>
          <td><span class="badge badge-neutral">${escapeHtml(r.class_name)}</span></td>
          <td>${escapeHtml(r.section)}</td>
          <td><strong>${escapeHtml(r.subject_name)}</strong> <span style="font-size:0.75rem; color:#64748b;">(${escapeHtml(r.subject_code)})</span></td>
          <td style="text-align:center;">${r.total_classes}</td>
          <td style="text-align:center; color:#15803d; font-weight:600;">${r.present}</td>
          <td style="text-align:center; color:#b91c1c; font-weight:600;">${r.absent}</td>
          <td style="text-align:center; font-weight:700;">
            <span class="badge ${r.is_eligible ? 'badge-present' : 'badge-absent'}">${r.percentage}%</span>
          </td>
          <td style="text-align:center;">${badge}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Academic report error:", err);
    const countElem = document.getElementById("academic-report-count");
    if (countElem) countElem.textContent = "Unable to load report records.";
    tbody.innerHTML = `<tr><td colspan="12" style="text-align:center; padding: 2rem; color: #dc2626;">Unable to load attendance report.</td></tr>`;
    showToast("Failed to load report.", "error");
  }
}

function exportReportToExcel() {
  const sFilter = document.getElementById("report-student-filter");
  const subFilter = document.getElementById("report-subject-filter");
  const classFilter = document.getElementById("report-class-filter");
  const secFilter = document.getElementById("report-section-filter");
  const fromFilter = document.getElementById("report-date-from");
  const toFilter = document.getElementById("report-date-to");

  const params = new URLSearchParams();
  if (sFilter && sFilter.value) params.set("student_id", sFilter.value);
  if (subFilter && subFilter.value) params.set("subject_id", subFilter.value);
  if (classFilter && classFilter.value) params.set("class_name", classFilter.value);
  if (secFilter && secFilter.value) params.set("section", secFilter.value);
  if (fromFilter && fromFilter.value) params.set("date_from", fromFilter.value);
  if (toFilter && toFilter.value) params.set("date_to", toFilter.value);

  showToast("Generating genuine Excel workbook (.xlsx)...", "info");
  const downloadUrl = `${API_BASE}/reports/export-excel?${params.toString()}`;
  
  // Trigger automatic download
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.setAttribute("download", "Student_Attendance_Report.xlsx");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

async function loadIndividualStudentReport() {
  const select = document.getElementById("individual-student-select");
  const tbody = document.getElementById("individual-breakdown-tbody");
  if (!select || !tbody) return;

  const studentId = select.value;
  if (!studentId) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: #64748b;">Please select a student above to view report.</td></tr>`;
    return;
  }

  tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem;">Loading student summary...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE}/students/${studentId}`);
    if (!res.ok) throw new Error("Student not found");
    const data = await res.json();
    const s = data.student;
    const summaries = data.subject_summary || [];

    const nameEl = document.getElementById("ind-name");
    const metaEl = document.getElementById("ind-meta");
    const pctEl = document.getElementById("ind-overall-pct");

    if (nameEl) nameEl.textContent = s.name;
    if (metaEl) metaEl.textContent = `Student ID: ${s.student_id} | Roll No: ${s.roll_number} | Class: ${s.class_name} (${s.section})`;
    if (pctEl) {
      pctEl.textContent = `${data.overall_percentage}%`;
      pctEl.style.color = data.overall_percentage >= 75 ? "#15803d" : "#dc2626";
    }

    if (summaries.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: #64748b;">No subjects found.</td></tr>`;
      return;
    }

    tbody.innerHTML = summaries.map(sub => {
      const isEligible = sub.percentage >= 75;
      return `
        <tr>
          <td><code>${escapeHtml(sub.subject_code)}</code></td>
          <td><strong>${escapeHtml(sub.subject_name)}</strong></td>
          <td style="text-align:center;">${sub.total_classes}</td>
          <td style="text-align:center; color:#15803d; font-weight:600;">${sub.present}</td>
          <td style="text-align:center; color:#b91c1c; font-weight:600;">${sub.absent}</td>
          <td style="text-align:center; font-weight:700;">
            <span class="badge ${isEligible ? 'badge-present' : 'badge-absent'}">${sub.percentage}%</span>
          </td>
          <td style="text-align:center;">
            ${isEligible ? '<span class="badge badge-present">✓ Eligible</span>' : '<span class="badge badge-absent">⚠ Defaulter</span>'}
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Individual report error:", err);
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: #dc2626;">Failed to load student details.</td></tr>`;
  }
}

async function loadDefaultersReport() {
  const tbody = document.getElementById("defaulter-report-tbody");
  const countElem = document.getElementById("defaulter-count");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE}/reports/defaulters`);
    if (!res.ok) throw new Error("Defaulters fetch failed");
    const data = await res.json();
    const defaulters = data.defaulters || [];

    if (countElem) countElem.textContent = `${data.total_defaulters} Defaulter Record(s)`;

    if (defaulters.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 2rem; color: #15803d; font-weight:600;">🎉 Excellent! All students have achieved >= 75% attendance.</td></tr>`;
      return;
    }

    tbody.innerHTML = defaulters.map((s, idx) => `
      <tr>
        <td><strong>#${idx + 1}</strong></td>
        <td><code>${escapeHtml(s.student_id)}</code></td>
        <td><strong style="color: #b91c1c;">${escapeHtml(s.student_name || s.name)}</strong></td>
        <td>${escapeHtml(s.roll_number)}</td>
        <td>${escapeHtml(s.class_name)} (${escapeHtml(s.section)})</td>
        <td>${escapeHtml(s.subject_name || 'General')}</td>
        <td style="text-align:center;">${s.present || s.present_days} / ${s.total_classes || s.total_working_days}</td>
        <td style="text-align:center;"><span class="badge badge-defaulter">${s.percentage}%</span></td>
        <td style="text-align:center;"><span class="badge badge-absent">Debarment Risk</span></td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Defaulters report error:", err);
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 2rem; color: #dc2626;">Unable to load defaulters.</td></tr>`;
  }
}

async function loadDailyReport() {
  const tbody = document.getElementById("daily-report-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE}/reports/daily`);
    if (!res.ok) throw new Error("Daily report fetch failed");
    const data = await res.json();
    const rows = data.daily_reports || [];

    if (rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem; color: #64748b;">No attendance recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map((r, idx) => `
      <tr>
        <td><strong>#${idx + 1}</strong></td>
        <td><code>${escapeHtml(r.attendance_date)}</code></td>
        <td>${r.total_marked}</td>
        <td><span class="badge badge-present">${r.present_count} Present</span></td>
        <td><span class="badge badge-absent">${r.absent_count} Absent</span></td>
        <td><strong>${r.daily_percentage}%</strong></td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Daily report error:", err);
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem; color: #dc2626;">Unable to load daily logs.</td></tr>`;
  }
}

// ============================================================================
// 10. GLOBAL POPULATION HELPERS
// ============================================================================

async function populateClassFilters() {
  try {
    const res = await fetch(`${API_BASE}/classes`);
    if (!res.ok) return;
    const data = await res.json();
    const classes = data.classes || [];
    const classNames = [...new Set(classes.map(c => c.class_name))];
    const sections = [...new Set(classes.map(c => c.section))].sort();

    ["class-filter", "subject-class-filter", "attendance-class-filter", "analysis-class-filter", "report-class-filter"].forEach(id => {
      const select = document.getElementById(id);
      if (select && classNames.length > 0) {
        const currentVal = select.value;
        let html = '<option value="">All Classes</option>';
        classNames.forEach(cn => {
          html += `<option value="${escapeHtml(cn)}">${escapeHtml(cn)}</option>`;
        });
        select.innerHTML = html;
        if (currentVal) select.value = currentVal;
      }
    });

    ["attendance-section-filter", "analysis-section-filter", "report-section-filter"].forEach(id => {
      const select = document.getElementById(id);
      if (!select || sections.length === 0) return;
      const currentVal = select.value;
      select.innerHTML = '<option value="">All Sections</option>' + sections.map(section =>
        `<option value="${escapeHtml(section)}">${escapeHtml(section)}</option>`
      ).join("");
      if (currentVal) select.value = currentVal;
    });
  } catch (err) {
    console.warn("Class filters fetch error:", err);
  }
}

async function populateSubjectDropdowns() {
  try {
    const res = await fetch(`${API_BASE}/subjects`);
    if (!res.ok) return;
    const data = await res.json();
    const subjects = data.subjects || [];

    // 1. Attendance Subject Dropdown
    const attSelect = document.getElementById("attendance-subject-select");
    if (attSelect) {
      const currentVal = attSelect.value;
      attSelect.innerHTML = subjects.map(s => `
        <option value="${escapeHtml(s.subject_id)}">${escapeHtml(s.subject_name)} (${escapeHtml(s.subject_code)})</option>
      `).join("");
      if (currentVal && subjects.some(s => s.subject_id === currentVal)) {
        attSelect.value = currentVal;
      }
    }

    // 2. Set Theory Subject Selectors (Subject 1 and Subject 2)
    const anaSelect1 = document.getElementById("analysis-subject-select");
    const anaSelect2 = document.getElementById("analysis-subject2-select");
    if (anaSelect1) {
      const cur1 = anaSelect1.value;
      anaSelect1.innerHTML = subjects.map(s => `
        <option value="${escapeHtml(s.subject_id)}">${escapeHtml(s.subject_name)} (${escapeHtml(s.subject_code)})</option>
      `).join("");
      if (cur1 && subjects.some(s => s.subject_id === cur1)) anaSelect1.value = cur1;
    }
    if (anaSelect2) {
      const cur2 = anaSelect2.value;
      anaSelect2.innerHTML = subjects.map(s => `
        <option value="${escapeHtml(s.subject_id)}">${escapeHtml(s.subject_name)} (${escapeHtml(s.subject_code)})</option>
      `).join("");
      // Pick second subject by default if available
      if (cur2 && subjects.some(s => s.subject_id === cur2)) {
        anaSelect2.value = cur2;
      } else if (subjects.length > 1) {
        anaSelect2.value = subjects[1].subject_id;
      }
    }

    // 3. Reports Subject Filter
    const repSelect = document.getElementById("report-subject-filter");
    if (repSelect) {
      const curRep = repSelect.value;
      let html = '<option value="">All Subjects</option>';
      subjects.forEach(s => {
        html += `<option value="${escapeHtml(s.subject_id)}">${escapeHtml(s.subject_name)} (${escapeHtml(s.subject_code)})</option>`;
      });
      repSelect.innerHTML = html;
      if (curRep) repSelect.value = curRep;
    }
  } catch (err) {
    console.warn("Subject dropdowns fetch error:", err);
  }
}

async function populateStudentDropdowns() {
  try {
    const res = await fetch(`${API_BASE}/students`);
    if (!res.ok) return;
    const data = await res.json();
    const students = data.students || [];

    // Reports Student Filter
    const repStudent = document.getElementById("report-student-filter");
    if (repStudent) {
      const curVal = repStudent.value;
      let html = '<option value="">All Students</option>';
      students.forEach(s => {
        html += `<option value="${escapeHtml(s.student_id)}">${escapeHtml(s.name)} (${escapeHtml(s.roll_number)})</option>`;
      });
      repStudent.innerHTML = html;
      if (curVal) repStudent.value = curVal;
    }

    // Individual Student Report Selector
    const indStudent = document.getElementById("individual-student-select");
    if (indStudent) {
      const curVal = indStudent.value;
      let html = '<option value="">-- Choose a Student --</option>';
      students.forEach(s => {
        html += `<option value="${escapeHtml(s.student_id)}">${escapeHtml(s.name)} (${escapeHtml(s.roll_number)}) - ${escapeHtml(s.class_name)}</option>`;
      });
      indStudent.innerHTML = html;
      if (curVal) indStudent.value = curVal;
      else if (students.length > 0) indStudent.value = students[0].student_id;
    }
  } catch (err) {
    console.warn("Student dropdowns error:", err);
  }
}

// ============================================================================
// 11. UTILITY FUNCTIONS
// ============================================================================

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function roundNumber(num, dec = 2) {
  return Number(Math.round(num + 'e' + dec) + 'e-' + dec);
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// ============================================================================
// 12. GLOBAL DOM LOAD LISTENER
// ============================================================================

document.addEventListener("DOMContentLoaded", async () => {
  let portalUser;
  try {
    portalUser = JSON.parse(sessionStorage.getItem("attendancePortalUser") || "null");
  } catch {
    sessionStorage.removeItem("attendancePortalUser");
  }
  if (!portalUser || !["student", "admin"].includes(portalUser.role)) {
    window.location.replace("/");
    return;
  }

  // Determine display name based on role
  const portalName = portalUser.role === "admin" 
    ? "Harikrishnareddy" 
    : (portalUser.name || "Student");

  // 1. Topbar user greeting across all pages
  const greeting = document.querySelector(".user-greeting");
  if (greeting) {
    if (portalUser.role === "admin") {
      greeting.innerHTML = `Welcome: <span>Harikrishnareddy</span> (Admin)`;
    } else {
      greeting.innerHTML = `Welcome: <span>${escapeHtml(portalName)}</span> (Student)`;
    }
  }

  // 2. Dashboard hero title banner (index.html)
  const heroTitle = document.querySelector(".hero-title");
  if (heroTitle) {
    heroTitle.innerHTML = `Welcome, ${escapeHtml(portalName)} 👋`;
  }

  // 3. Dashboard hero subtitle
  const heroSubtitle = document.querySelector(".hero-subtitle");
  if (heroSubtitle && portalUser.role === "student") {
    heroSubtitle.textContent = `Access your student attendance records, subject-wise attendance summary, set-theoretic analytics, and academic eligibility reports.`;
  }

  // 4. Hero quick actions for student
  if (portalUser.role === "student") {
    const heroBadges = document.querySelectorAll(".hero-badge-btn");
    if (heroBadges.length > 1) {
      heroBadges[1].textContent = "📊 View Set Theory & Analytics \u2192";
      heroBadges[1].onclick = () => window.location.assign("/analysis");
    }
  }

  // Topbar sign out button
  const topbar = document.querySelector(".topbar-right");
  if (topbar) {
    const signOut = document.createElement("button");
    signOut.className = "portal-signout";
    signOut.type = "button";
    signOut.innerHTML = "<span>Sign out</span> \u2192";
    signOut.addEventListener("click", () => {
      sessionStorage.removeItem("attendancePortalUser");
      window.location.replace("/");
    });
    topbar.appendChild(signOut);
  }

  // Always update status badge & sidebar toggle
  updateSystemStatus();
  initSidebarToggle();

  // Populate dynamic dropdowns
  await populateClassFilters();
  await populateSubjectDropdowns();
  await populateStudentDropdowns();

  // 1. Students Page
  if (document.getElementById("students-table-body")) {
    loadStudents();
    const searchInput = document.getElementById("student-search");
    if (searchInput) searchInput.addEventListener("input", debounce(loadStudents, 300));
  }

  // 2. Subjects Page
  if (document.getElementById("subjects-table-body")) {
    loadSubjects();
    const searchSub = document.getElementById("subject-search");
    if (searchSub) searchSub.addEventListener("input", debounce(loadSubjects, 300));
  }

  // 3. Attendance Marking Page
  if (document.getElementById("attendance-table-body")) {
    // Default date picker to today
    const datePicker = document.getElementById("attendance-date-picker");
    if (datePicker && !datePicker.value) {
      datePicker.value = new Date().toISOString().split("T")[0];
    }
    loadAttendanceSheet();
  }

  // 4. Set Theory & Venn Diagram Page
  if (document.getElementById("venn-text-only-a") || document.getElementById("analysis-subject-select")) {
    const anaDatePicker = document.getElementById("analysis-date-picker");
    if (anaDatePicker && !anaDatePicker.value) {
      anaDatePicker.value = new Date().toISOString().split("T")[0];
    }
    loadSetTheoryAnalysis();
  }

  // 5. Academic Reports Page
  if (document.getElementById("academic-report-tbody")) {
    loadAcademicReport();
  }

  // 6. Dashboard Page
  if (document.getElementById("dashboard-metrics") && document.getElementById("stat-total-students")) {
    loadDashboard();
  }
});
