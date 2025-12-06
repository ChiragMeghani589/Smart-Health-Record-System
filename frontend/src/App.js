import React, { useState, useEffect } from "react";
import { Routes, Route, Navigate, useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { API_BASE_URL } from "./config";

// -------- Protected Route Wrapper --------
function ProtectedRoute({ token, children }) {
  if (!token) {
    return <Navigate to="/auth" replace />;
  }
  return children;
}

// -------- Auth Page (Login / Signup) --------
function AuthPage({ token, setToken, setUserEmail }) {
  const [authMode, setAuthMode] = useState("login"); // "login" or "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loadingAuth, setLoadingAuth] = useState(false);
  const [keepLoggedIn, setKeepLoggedIn] = useState(false);
  const navigate = useNavigate();

  const handleAuth = async () => {
    if (!email || !password) {
      alert("Please enter email and password");
      return;
    }

    try {
      setLoadingAuth(true);
      if (authMode === "signup") {
        await axios.post(`${API_BASE_URL}/signup`, { email, password });
        alert("Signup successful. You can now log in.");
        setAuthMode("login");
      } else {
          const res = await axios.post(`${API_BASE_URL}/login`, { email, password });
          const { token, email: userEmailFromApi } = res.data;

          setToken(token);
          setUserEmail(userEmailFromApi);

          if (keepLoggedIn) {
            localStorage.setItem("shr_token", token);
            localStorage.setItem("shr_email", userEmailFromApi);
          } else {
            localStorage.removeItem("shr_token");
            localStorage.removeItem("shr_email");
          }

          alert("Logged in successfully");
          navigate("/dashboard");
        }   
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.error || "Auth failed");
    } finally {
      setLoadingAuth(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", justifyContent: "center", alignItems: "center", background: "#f5f5f5" }}>
      <div style={{ background: "white", padding: "30px", borderRadius: "10px", boxShadow: "0 2px 8px rgba(0,0,0,0.1)", width: "380px" }}>
        <h2 style={{ marginTop: 0, marginBottom: "10px" }}>
          {authMode === "login" ? "Login" : "Sign Up"}
        </h2>
        <p style={{ fontSize: "0.9rem", color: "#666", marginBottom: "20px" }}>
          Smart Health Record Search Engine
        </p>

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ padding: "8px 10px", marginBottom: "10px", width: "100%", boxSizing: "border-box" }}
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ padding: "8px 10px", marginBottom: "15px", width: "100%", boxSizing: "border-box" }}
        />

        <div style={{ marginBottom: "10px", fontSize: "0.85rem" }}>
          <label>
            <input
              type="checkbox"
              checked={keepLoggedIn}
              onChange={(e) => setKeepLoggedIn(e.target.checked)}
              style={{ marginRight: "5px" }}
            />
              Keep me logged in
          </label>
        </div>

        <button
          onClick={handleAuth}
          style={{ padding: "8px 12px", width: "100%", marginBottom: "10px" }}
          disabled={loadingAuth}
        >
          {loadingAuth ? "Please wait..." : authMode === "login" ? "Login" : "Sign Up"}
        </button>

        <button
          onClick={() => setAuthMode(authMode === "login" ? "signup" : "login")}
          style={{ padding: "6px 10px", width: "100%", fontSize: "0.9rem" }}
        >
          Switch to {authMode === "login" ? "Sign Up" : "Login"}
        </button>
      </div>
    </div>
  );
}

// -------- Dashboard Page --------
function DashboardPage({ userEmail, onLogout }) {
  return (
    <div style={{ padding: "30px", maxWidth: "1000px", margin: "auto", fontFamily: "system-ui, sans-serif" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ marginBottom: "5px" }}>Smart Health Record Search Engine</h1>
          <p style={{ color: "#555", marginTop: 0 }}>Welcome, {userEmail}</p>
        </div>
        <button onClick={onLogout} style={{ padding: "6px 12px" }}>Logout</button>
      </header>

      <hr style={{ margin: "20px 0" }} />

      <h2>Dashboard</h2>
      <p style={{ color: "#666" }}>Choose an action:</p>

      <div style={{ display: "flex", gap: "20px", marginTop: "20px", flexWrap: "wrap" }}>
        <DashboardCard
          title="Upload Records"
          description="Upload new medical record PDFs to index for search."
          to="/upload"
        />
        <DashboardCard
          title="Search Records"
          description="Search across uploaded medical records using natural language."
          to="/search"
        />
      </div>
    </div>
  );
}

function DashboardCard({ title, description, to }) {
  return (
    <Link
      to={to}
      style={{
        textDecoration: "none",
        color: "inherit",
        flex: "0 0 280px"
      }}
    >
      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: "10px",
          padding: "20px",
          height: "150px",
          boxShadow: "0 2px 5px rgba(0,0,0,0.05)",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "white",
        }}
      >
        <h3 style={{ marginTop: 0 }}>{title}</h3>
        <p style={{ fontSize: "0.9rem", color: "#666" }}>{description}</p>
        <span style={{ fontSize: "0.85rem", color: "#007bff" }}>Go →</span>
      </div>
    </Link>
  );
}

// -------- Upload Page --------
function UploadPage({ token }) {
  const [file, setFile] = useState(null);
  const [patientId, setPatientId] = useState("");
  const [loadingUpload, setLoadingUpload] = useState(false);
  const navigate = useNavigate();

  const axiosConfig = {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  };

  const handleUpload = async () => {
    if (!file) {
      alert("Please select a file");
      return;
    }

    if (!patientId.trim()) {
      alert("Please enter a Patient ID");
      return;
    }

    try {
      setLoadingUpload(true);
      const formData = new FormData();
      formData.append("file", file);
      formData.append("patient_id", patientId.trim());

      await axios.post(`${API_BASE_URL}/upload-record`, formData, axiosConfig);
      alert("Uploaded and indexed!");
      setFile(null);
      setPatientId("");
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.error || "Upload failed");
    } finally {
      setLoadingUpload(false);
    }
  };

  return (
    <PageLayout title="Upload Medical Record" showBack onBack={() => navigate("/dashboard")}>
      <div style={{ marginTop: "10px" }}>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <input
          type="text"
          placeholder="Patient ID"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          style={{ marginLeft: "10px", padding: "4px 8px" }}
        />
        <button
          onClick={handleUpload}
          style={{ marginLeft: "10px", padding: "6px 12px" }}
          disabled={loadingUpload}
        >
          {loadingUpload ? "Uploading..." : "Upload"}
        </button>
      </div>
    </PageLayout>
  );
}

// -------- Search Page --------
function SearchPage({ token }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [loadingSearch, setLoadingSearch] = useState(false);

  const [recordToUpdate, setRecordToUpdate] = useState(null);
  const [newPatientId, setNewPatientId] = useState("");
  const [newFile, setNewFile] = useState(null);

  const navigate = useNavigate();

  const axiosConfig = {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  };

  const handleSearch = async () => {
    if (!query.trim()) {
      alert("Please enter a query");
      return;
    }

    try {
      setLoadingSearch(true);
      const body = { query, top_k: 5 };
      const res = await axios.post(`${API_BASE_URL}/search-records`, body, axiosConfig);
      setResults(res.data.results || []);
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.error || "Search failed");
    } finally {
      setLoadingSearch(false);
    }
  };

  const viewRecord = async (id) => {
    try {
      const res = await axios.get(`${API_BASE_URL}/record/${id}`, axiosConfig);
      setSelectedRecord(res.data.record);
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.error || "Failed to load record");
    }
  };

  const handleDelete = async (id) => {
    const confirmDelete = window.confirm("Are you sure you want to delete this record?");
    if (!confirmDelete) return;
    try {
      await axios.delete(`${API_BASE_URL}/record/${id}`, axiosConfig);
      setResults((prev) => prev.filter((r) => r.record_id !== id));
      if (selectedRecord && selectedRecord.id === id) {
        setSelectedRecord(null);
      }
      alert("Record deleted successfully");
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.error || "Failed to delete record");
    }
  };

  return (
    <PageLayout title="Search Records" showBack onBack={() => navigate("/dashboard")}>
      <div style={{ marginBottom: "20px" }}>
        <input
          type="text"
          placeholder="e.g. diabetic patient on metformin"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              if (!loadingSearch) {
                handleSearch();
              }
            }
          }}
          style={{ width: "400px", padding: "4px 8px" }}
        />

        <button
          onClick={handleSearch}
          style={{ marginLeft: "10px", padding: "6px 12px" }}
          disabled={loadingSearch}
        >
          {loadingSearch ? "Searching..." : "Search"}
        </button>
      </div>

      <div>
        <h3>Results</h3>
        {results.length === 0 && <p style={{ color: "#777" }}>No results yet. Try a search.</p>}
        {results.map((r, idx) => (
          <div
            key={idx}
            style={{
              border: "1px solid #ccc",
              padding: "15px",
              marginBottom: "10px",
              borderRadius: "5px",
              background: "#fafafa",
            }}
          >
            <strong>Patient ID:</strong> {r.patient_id} <br />
            <strong>File:</strong> {r.file_name} <br />
            <strong>Snippet:</strong> {r.snippet} <br />
            <button
              onClick={() => viewRecord(r.record_id)}
              style={{ marginTop: "10px", padding: "6px 12px", marginRight: "10px" }}
            >
              View Full Record
            </button>
            <button
              onClick={() => handleDelete(r.record_id)}
              style={{ marginTop: "10px", padding: "6px 12px", backgroundColor: "#e74c3c", color: "white", border: "none", borderRadius: "4px", marginRight: "10px" }}
            >
              Delete
            </button>
            <button
              onClick={() => setRecordToUpdate(r)}
              style={{
                marginTop: "10px",
                padding: "6px 12px",
                backgroundColor: "#f1c40f",
                color: "black",
                border: "none",
                borderRadius: "4px",
              }}
            >
              Update
            </button>
          </div>
        ))}
      </div>

      {/* Full Record Modal */}
      {selectedRecord && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            zIndex: 10,
          }}
          onClick={() => setSelectedRecord(null)}
        >
          <div
            style={{
              background: "white",
              padding: "20px",
              width: "650px",
              borderRadius: "8px",
              maxHeight: "90%",
              overflow: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2>{selectedRecord.file_name}</h2>
            <p><strong>Patient ID:</strong> {selectedRecord.patient_id}</p>

            <h3>Summary</h3>
            <p>{selectedRecord.summary || "No summary generated."}</p>

            <h3>Full Text</h3>
            <p style={{ whiteSpace: "pre-wrap" }}>{selectedRecord.full_text}</p>

            <button
              onClick={() => setSelectedRecord(null)}
              style={{ marginTop: "10px", padding: "6px 12px" }}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* ✅ UPDATE RECORD MODAL */}
      {recordToUpdate && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            zIndex: 11,
          }}
          onClick={() => setRecordToUpdate(null)}
        >
          <div
            style={{
              background: "white",
              padding: "20px",
              width: "450px",
              borderRadius: "8px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2>Update Record</h2>

            <label>New Patient ID</label>
            <input
              type="text"
              value={newPatientId}
              onChange={(e) => setNewPatientId(e.target.value)}
              style={{
                width: "100%",
                padding: "6px 10px",
                marginBottom: "10px",
              }}
            />

            <label>Replace PDF (optional)</label>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setNewFile(e.target.files[0])}
              style={{ marginBottom: "20px" }}
            />

            <button
              onClick={async () => {
                const formData = new FormData();
                if (newPatientId.trim()) formData.append("patient_id", newPatientId.trim());
                if (newFile) formData.append("file", newFile);

                try {
                  await axios.put(
                    `${API_BASE_URL}/record/${recordToUpdate.record_id}`,
                    formData,
                    axiosConfig
                  );
                  alert("Record updated!");
                  setRecordToUpdate(null);
                  setNewFile(null);
                  setNewPatientId("");
                  setResults([]); // optional: clear results
                } catch (err) {
                  console.error(err);
                  alert(err.response?.data?.error || "Update failed");
                }
              }}
              style={{ padding: "6px 12px", marginRight: "10px" }}
            >
              Save
            </button>

            <button
              onClick={() => setRecordToUpdate(null)}
              style={{ padding: "6px 12px" }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </PageLayout>
  );
}


// -------- Simple Layout Wrapper for pages --------
function PageLayout({ title, children, showBack, onBack }) {
  return (
    <div style={{ padding: "30px", maxWidth: "1000px", margin: "auto", fontFamily: "system-ui, sans-serif" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
        <h1 style={{ marginBottom: 0, fontSize: "1.4rem" }}>{title}</h1>
        {showBack && (
          <button onClick={onBack} style={{ padding: "6px 12px" }}>
            ← Back to Dashboard
          </button>
        )}
      </header>
      <hr style={{ marginBottom: "20px" }} />
      {children}
    </div>
  );
}

// -------- Main App --------
function App() {
  const [token, setToken] = useState(() => localStorage.getItem("shr_token"));
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem("shr_email"));

  const handleLogout = () => {
    setToken(null);
    setUserEmail(null);
    localStorage.removeItem("shr_token");
    localStorage.removeItem("shr_email");
  };

  return (
    <Routes>
      <Route
        path="/auth"
        element={
          <AuthPage
            token={token}
            setToken={setToken}
            setUserEmail={setUserEmail}
          />
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute token={token}>
            <DashboardPage userEmail={userEmail} onLogout={handleLogout} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/upload"
        element={
          <ProtectedRoute token={token}>
            <UploadPage token={token} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/search"
        element={
          <ProtectedRoute token={token}>
            <SearchPage token={token} />
          </ProtectedRoute>
        }
      />
      {/* Default route */}
      <Route path="*" element={<Navigate to="/auth" replace />} />
    </Routes>
  );
}

export default App;