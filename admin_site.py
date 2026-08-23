from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

from backend.local_api import ensure_api_server


SITE_HOST = "127.0.0.1"
SITE_PORT = 8780
API_BASE_URL = os.getenv("EZYM_MAILER_ADMIN_API_BASE_URL", "http://127.0.0.1:8765")
BOOTSTRAP_API = os.getenv("EZYM_MAILER_BOOTSTRAP_API", "1").strip().lower() not in {"0", "false", "no", "off"}


app = FastAPI(
    title="EzyMailer CRM Dashboard",
    version="4.0.0",
    docs_url=None,
    redoc_url=None,
)


@app.on_event("startup")
def _startup() -> None:
    if BOOTSTRAP_API:
        ensure_api_server()


@app.get("/health")
def health() -> dict[str, object]:
    return {"ok": True, "service": "ezymailer-admin-site", "backend_api": API_BASE_URL}


def _html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <title>EzyMailer CRM Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
  <script crossorigin src="https://unpkg.com/@emotion/react@11.11.4/dist/emotion-react.umd.min.js"></script>
  <script crossorigin src="https://unpkg.com/@emotion/styled@11.11.0/dist/emotion-styled.umd.min.js"></script>
  <script crossorigin src="https://unpkg.com/@mui/material@5.16.6/umd/material-ui.development.js"></script>
  <script src="https://unpkg.com/@babel/standalone@7.25.6/babel.min.js"></script>
  <style>
    html, body, #root { width: 100%; height: 100%; margin: 0; }
    body {
      overflow-x: hidden;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 8% 8%, rgba(25,118,210,0.18), transparent 20%),
        radial-gradient(circle at 92% 0%, rgba(124,58,237,0.12), transparent 18%),
        linear-gradient(180deg, #09111d 0%, #0a0f18 100%);
    }
    * { box-sizing: border-box; }
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-thumb { background: rgba(148,163,184,0.28); border-radius: 999px; }
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel">
    const {
      AppBar, Toolbar, Box, Button, IconButton, Typography, Drawer, CssBaseline,
      ThemeProvider, createTheme, useMediaQuery, Stack, Paper, Grid, Card,
      CardContent, Chip, TextField, MenuItem, FormControl, InputLabel, Select,
      Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
      TablePagination, Avatar, Divider, List, ListItemButton, ListItemText,
      Menu, Snackbar, Alert, Switch, FormControlLabel, GlobalStyles, Dialog,
      DialogTitle, DialogContent, DialogActions
    } = MaterialUI;

    const CONFIGURED_API_BASE = "__API_BASE__";
    const API_BASE = (() => {
      if (CONFIGURED_API_BASE && !CONFIGURED_API_BASE.includes("127.0.0.1") && !CONFIGURED_API_BASE.includes("localhost") && !CONFIGURED_API_BASE.includes("0.0.0.0")) {
        return CONFIGURED_API_BASE;
      }
      return `${window.location.protocol}//${window.location.hostname}:8765`;
    })();
    const STORAGE_KEY = "ezymailer_admin_auth";
    const FP_KEY = "ezymailer_admin_device_fp";
    const THEME_KEY = "ezymailer_admin_theme";
    const drawerWidth = 300;

    const fmt = (value) => (value === null || value === undefined || value === "" ? "" : String(value));
    const formatDate = (value) => {
      if (!value) return "";
      const dt = new Date(value);
      return Number.isNaN(dt.getTime()) ? String(value) : dt.toLocaleString();
    };
    const parseDate = (value) => {
      const text = String(value || "").trim();
      if (!text) return null;
      const dt = new Date(text);
      return Number.isNaN(dt.getTime()) ? null : dt;
    };
    const dayKey = (date) => date.toISOString().slice(0, 10);
    const isExpired = (user) => {
      const dt = parseDate(user?.login_valid_until);
      return !!dt && dt.getTime() < Date.now();
    };
    const isRealtimeOnline = (user) => {
      if (typeof user?.online_status === "boolean") return user.online_status;
      if (!user?.is_active) return false;
      if (isExpired(user)) return false;
      const dt = parseDate(user?.last_login_at);
      if (!dt) return false;
      return (Date.now() - dt.getTime()) <= 15 * 60 * 1000;
    };

    function safeJson(text) {
      try { return JSON.parse(text); } catch { return null; }
    }

    function extractApiMessage(payload, fallback = "Request failed") {
      const candidates = [
        payload?.detail,
        payload?.message,
        payload?.error,
        payload?.raw,
      ];
      for (const candidate of candidates) {
        if (!candidate) continue;
        if (typeof candidate === "string") return candidate;
        if (typeof candidate === "object") {
          const nested = candidate.message || candidate.detail || candidate.error || candidate.reason;
          if (nested) return String(nested);
          try {
            return JSON.stringify(candidate);
          } catch {
            return fallback;
          }
        }
      }
      if (typeof payload === "string") return payload;
      return fallback;
    }

    function useLocalStorageState(key, fallback) {
      const [value, setValue] = React.useState(() => {
        try {
          const stored = localStorage.getItem(key);
          return stored ? JSON.parse(stored) : fallback;
        } catch {
          return fallback;
        }
      });
      React.useEffect(() => {
        localStorage.setItem(key, JSON.stringify(value));
      }, [key, value]);
      return [value, setValue];
    }

    function getFingerprint() {
      let fp = localStorage.getItem(FP_KEY);
      if (!fp) {
        fp = crypto?.randomUUID ? crypto.randomUUID() : `fp-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        localStorage.setItem(FP_KEY, fp);
      }
      return fp;
    }

    async function request(auth, path, options = {}, useAuth = true) {
      const headers = { ...(options.headers || {}) };
      if (useAuth && auth?.access_token) headers.Authorization = `Bearer ${auth.access_token}`;
      if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
      const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
      const raw = await response.text();
      const payload = raw ? (safeJson(raw) || { raw }) : {};
      if (response.status === 401 && typeof window.__ezymailerLogout === "function") {
        window.__ezymailerLogout(extractApiMessage(payload, "Session expired"));
      }
      if (!response.ok) {
        const message = extractApiMessage(payload, `Request failed (${response.status})`);
        const error = new Error(message);
        error.status = response.status;
        error.payload = payload;
        throw error;
      }
      return payload;
    }

    function App() {
      const [mode, setMode] = React.useState(localStorage.getItem(THEME_KEY) || "dark");
      const theme = React.useMemo(() => createTheme({
        palette: {
          mode,
          primary: { main: "#1976d2" },
          secondary: { main: "#7c3aed" },
          background: {
            default: mode === "dark" ? "#09111d" : "#f5f7fb",
            paper: mode === "dark" ? "#111827" : "#ffffff",
          },
        },
        shape: { borderRadius: 8 },
        typography: {
          fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
        components: {
          MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
          MuiTableCell: { styleOverrides: { root: { whiteSpace: "nowrap" } } },
        },
      }), [mode]);
      const isDesktop = useMediaQuery(theme.breakpoints.up("md"));
      const [mobileOpen, setMobileOpen] = React.useState(false);
      const [auth, setAuth] = useLocalStorageState(STORAGE_KEY, null);
      const [users, setUsers] = React.useState([]);
      const [activity, setActivity] = React.useState([]);
      const [history, setHistory] = React.useState([]);
      const [cronJobs, setCronJobs] = React.useState([]);
      const [selectedUser, setSelectedUser] = React.useState(null);
      const [page, setPage] = React.useState(0);
      const [rowsPerPage, setRowsPerPage] = React.useState(10);
      const [expiredPage, setExpiredPage] = React.useState(0);
      const [expiredRowsPerPage, setExpiredRowsPerPage] = React.useState(10);
      const [activityPage, setActivityPage] = React.useState(0);
      const [activityRowsPerPage, setActivityRowsPerPage] = React.useState(10);
      const [historyPage, setHistoryPage] = React.useState(0);
      const [historyRowsPerPage, setHistoryRowsPerPage] = React.useState(10);
      const [statSearch, setStatSearch] = React.useState("");
      const [statPage, setStatPage] = React.useState(0);
      const [statRowsPerPage, setStatRowsPerPage] = React.useState(10);
      const [statDialogOpen, setStatDialogOpen] = React.useState(false);
      const [statDialogKey, setStatDialogKey] = React.useState("total");
      const [search, setSearch] = React.useState("");
      const [filter, setFilter] = React.useState("all");
      const [expiredSearch, setExpiredSearch] = React.useState("");
      const [activitySearch, setActivitySearch] = React.useState("");
      const [historySearch, setHistorySearch] = React.useState("");
      const [activeSection, setActiveSection] = React.useState("overview");
      const [menuAnchor, setMenuAnchor] = React.useState(null);
      const [menuUser, setMenuUser] = React.useState(null);
      const [editorOpen, setEditorOpen] = React.useState(false);
      const [createOpen, setCreateOpen] = React.useState(false);
      const [detailOpen, setDetailOpen] = React.useState(false);
      const [detailLoading, setDetailLoading] = React.useState(false);
      const [detailData, setDetailData] = React.useState(null);
      const [loading, setLoading] = React.useState(false);
      const [message, setMessage] = React.useState({ open: false, severity: "info", text: "" });
      const [loginConflict, setLoginConflict] = React.useState(null);
      const [loginSubmitting, setLoginSubmitting] = React.useState(false);
      const [loginForm, setLoginForm] = React.useState({ username: "", password: "" });
      const [form, setForm] = React.useState({
        id: "",
        username: "",
        display_name: "",
        role: "user",
        login_valid_until: "",
        loginRestriction: "keep",
        password: "",
      });
      const blankForm = React.useCallback(() => ({
        id: "",
        username: "",
        display_name: "",
        role: "user",
        login_valid_until: "",
        loginRestriction: "keep",
        password: "",
      }), []);

      React.useEffect(() => {
        localStorage.setItem(THEME_KEY, mode);
      }, [mode]);

      const logoutCurrentSession = React.useCallback((reason = "Logged out") => {
        setAuth(null);
        setUsers([]);
        setActivity([]);
        setHistory([]);
        setSelectedUser(null);
        setDetailData(null);
        setDetailOpen(false);
        setStatDialogOpen(false);
        setEditorOpen(false);
        setCreateOpen(false);
        notify(reason, "warning");
      }, []);

      React.useEffect(() => {
        window.__ezymailerLogout = logoutCurrentSession;
        return () => {
          if (window.__ezymailerLogout === logoutCurrentSession) delete window.__ezymailerLogout;
        };
      }, [logoutCurrentSession]);

      React.useEffect(() => {
        if (auth?.access_token) refreshAll(auth);
      }, []);

      React.useEffect(() => {
        if (selectedUser) {
          setForm({
            id: selectedUser.id || "",
            username: selectedUser.username || "",
            display_name: selectedUser.display_name || "",
            role: selectedUser.role || "user",
            login_valid_until: selectedUser.login_valid_until ? String(selectedUser.login_valid_until).slice(0, 16) : "",
            loginRestriction: "keep",
            password: "",
          });
        }
      }, [selectedUser]);

      const notify = (text, severity = "info") => setMessage({ open: true, severity, text });
      const closeMessage = () => setMessage((m) => ({ ...m, open: false }));

      async function refreshUsers(authValue = auth) {
        const payload = await request(authValue, "/api/admin/users");
        setUsers(Array.isArray(payload.users) ? payload.users : []);
      }
      async function refreshActivity(authValue = auth) {
        const payload = await request(authValue, "/api/admin/activity?limit=200");
        setActivity(Array.isArray(payload.activity) ? payload.activity : []);
      }
      async function refreshHistory(authValue = auth) {
        const payload = await request(authValue, "/api/admin/login-history?limit=200");
        setHistory(Array.isArray(payload.history) ? payload.history : []);
      }
      async function refreshCronJobs(authValue = auth) {
        const payload = await request(authValue, "/api/admin/cron-jobs");
        setCronJobs(Array.isArray(payload.cron_jobs) ? payload.cron_jobs : []);
      }
      async function refreshAll(authValue = auth) {
        if (!authValue?.access_token) return;
        setLoading(true);
        try {
          await Promise.all([refreshUsers(authValue), refreshActivity(authValue), refreshHistory(authValue), refreshCronJobs(authValue)]);
        } catch (error) {
          notify(error.message || String(error), "error");
        } finally {
          setLoading(false);
        }
      }

      const loadAuthLogin = async (forceLogoutOtherDevice = false) => {
        const username = loginForm.username.trim();
        const password = loginForm.password;
        if (!username || !password) {
          notify("Username and password are required.", "warning");
          return;
        }
        setLoginSubmitting(true);
        try {
          const response = await fetch(`${API_BASE}/api/admin/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              username,
              password,
              device_fingerprint: getFingerprint(),
              device_name: navigator.userAgent,
              force_logout_other_device: forceLogoutOtherDevice,
            }),
          });
          const raw = await response.text();
          const payload = raw ? (safeJson(raw) || { raw }) : {};
          if (!response.ok) {
            const message = extractApiMessage(payload, "Login failed");
            if (response.status === 409) {
              const conflict = payload?.detail && typeof payload.detail === "object"
                ? payload.detail
                : payload;
              setLoginConflict(conflict);
              notify(extractApiMessage(conflict, message), "warning");
              return;
            }
            throw new Error(message);
          }
          setLoginConflict(null);
          setAuth(payload);
          notify("Admin login successful", "success");
          await refreshAll(payload);
        } catch (error) {
          notify(extractApiMessage(error?.payload || {}, error?.message || "Login failed"), "error");
        } finally {
          setLoginSubmitting(false);
        }
      };

      const filteredUsers = React.useMemo(() => {
        const q = search.trim().toLowerCase();
        return users.filter((user) => {
          const haystack = [user.username, user.display_name, user.role, user.device_name, user.device_fingerprint, user.last_login_ip].join(" ").toLowerCase();
          if (q && !haystack.includes(q)) return false;
          if (filter === "active" && !user.is_active) return false;
          if (filter === "inactive" && user.is_active) return false;
          if (filter === "admin" && String(user.role || "").toLowerCase() !== "admin") return false;
          if (filter === "expired" && !isExpired(user)) return false;
          return true;
        });
      }, [users, search, filter]);

      const pagedUsers = React.useMemo(() => filteredUsers.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage), [filteredUsers, page, rowsPerPage]);
      const expiredUsers = React.useMemo(() => users.filter((u) => isExpired(u)), [users]);
      const filteredExpiredUsers = React.useMemo(() => {
        const q = expiredSearch.trim().toLowerCase();
        return expiredUsers.filter((user) => {
          const haystack = [user.username, user.display_name, user.role, user.device_name, user.device_fingerprint, user.last_login_ip].join(" ").toLowerCase();
          return !q || haystack.includes(q);
        });
      }, [expiredUsers, expiredSearch]);
      const pagedExpiredUsers = React.useMemo(() => filteredExpiredUsers.slice(expiredPage * expiredRowsPerPage, expiredPage * expiredRowsPerPage + expiredRowsPerPage), [filteredExpiredUsers, expiredPage, expiredRowsPerPage]);
      const filteredActivity = React.useMemo(() => {
        const q = activitySearch.trim().toLowerCase();
        return activity.filter((row) => {
          const haystack = [row.username, row.category, row.action, row.details_json, row.ip_address, row.location_label].join(" ").toLowerCase();
          return !q || haystack.includes(q);
        });
      }, [activity, activitySearch]);
      const pagedActivity = React.useMemo(() => filteredActivity.slice(activityPage * activityRowsPerPage, activityPage * activityRowsPerPage + activityRowsPerPage), [filteredActivity, activityPage, activityRowsPerPage]);
      const filteredHistory = React.useMemo(() => {
        const q = historySearch.trim().toLowerCase();
        return history.filter((row) => {
          const haystack = [row.username, row.ip_address, row.device_name, row.device_fingerprint, row.user_agent, row.success ? "success" : "failed"].join(" ").toLowerCase();
          return !q || haystack.includes(q);
        });
      }, [history, historySearch]);
      const pagedHistory = React.useMemo(() => filteredHistory.slice(historyPage * historyRowsPerPage, historyPage * historyRowsPerPage + historyRowsPerPage), [filteredHistory, historyPage, historyRowsPerPage]);
      const stats = React.useMemo(() => ({
        total: users.length,
        active: users.filter((u) => !!u.is_active).length,
        expired: users.filter((u) => isExpired(u)).length,
        admins: users.filter((u) => String(u.role || "").toLowerCase() === "admin").length,
        deviceOnline: users.filter((u) => isRealtimeOnline(u)).length,
        failures: history.filter((h) => !h.success).length,
      }), [users, history]);
      const days = React.useMemo(() => {
        const arr = [];
        for (let i = 6; i >= 0; i -= 1) {
          const date = new Date(Date.now() - i * 86400000);
          arr.push({ key: dayKey(date), label: date.toLocaleDateString(undefined, { month: "short", day: "numeric" }) });
        }
        return arr;
      }, []);
      const trendValues = React.useMemo(() => days.map(({ key }) => history.filter((row) => {
        const created = row.created_at ? new Date(row.created_at) : null;
        return created && !Number.isNaN(created.getTime()) && dayKey(created) === key;
      }).length), [days, history]);
      const breakdown = React.useMemo(() => ([
        { label: "Active", value: stats.active },
        { label: "Inactive", value: users.filter((u) => !u.is_active).length },
        { label: "Expired", value: stats.expired },
        { label: "Admins", value: stats.admins },
      ]), [stats, users]);
      const summaryCards = React.useMemo(() => ([
        {
          key: "total",
          label: "Total Users",
          value: stats.total,
          hint: "All users loaded from the admin API.",
          tone: "#42a5f5",
        },
        {
          key: "active",
          label: "Active Users",
          value: stats.active,
          hint: "Users currently allowed to sign in.",
          tone: "#22c55e",
        },
        {
          key: "expired",
          label: "Expired Validity",
          value: stats.expired,
          hint: "Users whose login validity expired.",
          tone: "#f59e0b",
        },
        {
          key: "admins",
          label: "Admin Users",
          value: stats.admins,
          hint: "Users with admin permissions.",
          tone: "#a855f7",
        },
        {
          key: "deviceOnline",
          label: "Device Online",
          value: stats.deviceOnline,
          hint: "Check realtime users.",
          tone: "#38bdf8",
        },
      ]), [stats]);
      const statViews = React.useMemo(() => ({
        total: {
          title: "Total Users",
          description: "All users loaded from the admin API.",
          rows: users,
        },
        active: {
          title: "Active Users",
          description: "Users currently allowed to sign in.",
          rows: users.filter((u) => !!u.is_active),
        },
        expired: {
          title: "Expired Validity",
          description: "Users whose login validity expired.",
          rows: users.filter((u) => isExpired(u)),
        },
        admins: {
          title: "Admin Users",
          description: "Users with admin permissions.",
          rows: users.filter((u) => String(u.role || "").toLowerCase() === "admin"),
        },
        deviceOnline: {
          title: "Device Online",
          description: "Users currently online based on recent authenticated activity.",
          rows: users.filter((u) => isRealtimeOnline(u)),
        },
      }), [users]);
      const currentStatView = statViews[statDialogKey] || statViews.total;
      const statRows = React.useMemo(() => {
        const q = statSearch.trim().toLowerCase();
        return (currentStatView.rows || []).filter((user) => {
          const haystack = [user.username, user.display_name, user.role, user.device_name, user.device_fingerprint, user.last_login_ip].join(" ").toLowerCase();
          return !q || haystack.includes(q);
        });
      }, [currentStatView, statSearch]);
      const pagedStatRows = React.useMemo(() => statRows.slice(statPage * statRowsPerPage, statPage * statRowsPerPage + statRowsPerPage), [statRows, statPage, statRowsPerPage]);
      const openStatDialog = (key) => {
        setStatDialogKey(key);
        setStatPage(0);
        setStatSearch("");
        setStatDialogOpen(true);
      };

      const buildUserPayload = (source = form) => {
        const payload = {
          username: source.username.trim(),
          display_name: source.display_name.trim(),
          role: source.role || "user",
          login_valid_until: source.login_valid_until ? new Date(source.login_valid_until).toISOString() : null,
        };
        if (source.password.trim()) payload.reset_password = source.password.trim();
        if (source.loginRestriction === "any") payload.clear_device_binding = true;
        if (source.loginRestriction === "disable") payload.is_active = false;
        return payload;
      };

      const openCreateUser = () => {
        setSelectedUser(null);
        setForm(blankForm());
        setCreateOpen(true);
        setEditorOpen(true);
      };

      const openEditor = (user) => {
        setSelectedUser(user);
        setForm({
          id: user.id || "",
          username: user.username || "",
          display_name: user.display_name || "",
          role: user.role || "user",
          login_valid_until: user.login_valid_until ? String(user.login_valid_until).slice(0, 16) : "",
          loginRestriction: "keep",
          password: "",
        });
        setCreateOpen(false);
        setEditorOpen(true);
      };

      const openDetails = async (user) => {
        setSelectedUser(user);
        setDetailOpen(true);
        setDetailLoading(true);
        setDetailData(null);
        try {
          const payload = await request(auth, `/api/admin/users/${user.id}/details`);
          setDetailData(payload);
        } catch (error) {
          notify(error.message || String(error), "error");
          setDetailOpen(false);
        } finally {
          setDetailLoading(false);
        }
      };

      const runDetailAction = async (action, body = null) => {
        if (!detailData?.user?.id) return notify("No user selected", "warning");
        await doAction(detailData.user, action, body);
        await openDetails(detailData.user);
      };

      const submitUser = async () => {
        if (!auth?.access_token) return notify("Sign in as admin first", "warning");
        const payload = buildUserPayload();
        if (selectedUser?.id) {
          await request(auth, `/api/admin/users/${selectedUser.id}`, { method: "PATCH", body: JSON.stringify(payload) });
          notify("User updated", "success");
        } else {
          if (!form.password.trim()) return notify("Password is required for new users", "warning");
          await request(auth, "/api/users", {
            method: "POST",
            body: JSON.stringify({
              username: payload.username,
              password: form.password.trim(),
              role: payload.role,
              display_name: payload.display_name,
              is_active: payload.is_active !== false,
              login_valid_until: payload.login_valid_until || null,
            }),
          });
          notify("User created", "success");
        }
        setEditorOpen(false);
        setCreateOpen(false);
        await refreshUsers();
      };

      const doAction = async (targetUser, action, body = null) => {
        if (!auth?.access_token || !targetUser?.id) return notify("Select a user first", "warning");
        await request(auth, `/api/admin/users/${targetUser.id}${action}`, {
          method: "POST",
          body: body ? JSON.stringify(body) : undefined,
        });
        notify("User updated", "success");
        await refreshUsers();
      };

      const handleMenu = async (action) => {
        setMenuAnchor(null);
        if (!menuUser) return;
        setSelectedUser(menuUser);
        if (action === "details") return openDetails(menuUser);
        if (action === "edit") return openEditor(menuUser);
        if (action === "activate") return doAction(menuUser, "/activate");
        if (action === "deactivate") return doAction(menuUser, "/deactivate");
        if (action === "admin") return request(auth, `/api/admin/users/${menuUser.id}`, {
          method: "PATCH",
          body: JSON.stringify({ role: "admin" }),
        }).then(async () => {
          notify("User updated", "success");
          await refreshUsers();
        });
        if (action === "user") return request(auth, `/api/admin/users/${menuUser.id}`, {
          method: "PATCH",
          body: JSON.stringify({ role: "user" }),
        }).then(async () => {
          notify("User updated", "success");
          await refreshUsers();
        });
        if (action === "any-device") return request(auth, `/api/admin/users/${menuUser.id}`, {
          method: "PATCH",
          body: JSON.stringify({ clear_device_binding: true }),
        }).then(async () => {
          notify("User updated", "success");
          await refreshUsers();
        });
        if (action === "keep-device") return request(auth, `/api/admin/users/${menuUser.id}`, {
          method: "PATCH",
          body: JSON.stringify({}),
        }).then(async () => {
          notify("User updated", "success");
          await refreshUsers();
        });
        if (action === "valid-30") return request(auth, `/api/admin/users/${menuUser.id}`, {
          method: "PATCH",
          body: JSON.stringify({ login_valid_until: new Date(Date.now() + 30 * 86400000).toISOString() }),
        }).then(async () => {
          notify("User updated", "success");
          await refreshUsers();
        });
        if (action === "valid-90") return request(auth, `/api/admin/users/${menuUser.id}`, {
          method: "PATCH",
          body: JSON.stringify({ login_valid_until: new Date(Date.now() + 90 * 86400000).toISOString() }),
        }).then(async () => {
          notify("User updated", "success");
          await refreshUsers();
        });
        if (action === "clear-validity") return request(auth, `/api/admin/users/${menuUser.id}`, {
          method: "PATCH",
          body: JSON.stringify({ login_valid_until: null }),
        }).then(async () => {
          notify("User updated", "success");
          await refreshUsers();
        });
        if (action === "reset-password") {
          const password = window.prompt(`Enter new password for ${menuUser.username}`) || "";
          if (!password) return notify("Password is required", "warning");
          return doAction(menuUser, "/reset-password", { password });
        }
        if (action === "reset-device") return doAction(menuUser, "/reset-device");
      };

      const chartLegendItem = (color, label) => (
        <Stack key={label} direction="row" spacing={1} alignItems="center">
          <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: color }} />
          <Typography variant="caption" color="text.secondary">{label}</Typography>
        </Stack>
      );

      function MiniChart({ title, subtitle, legend, children }) {
        return (
          <Paper elevation={0} sx={{
            p: 2.5,
            borderRadius: 2,
            bgcolor: "background.paper",
            border: "1px solid",
            borderColor: "divider",
            boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
            minHeight: 320,
          }}>
            <Stack spacing={1.25}>
              <Box>
                <Typography variant="h6" fontWeight={900}>{title}</Typography>
                <Typography variant="body2" color="text.secondary">{subtitle}</Typography>
              </Box>
              <Box sx={{ width: "100%", overflow: "hidden" }}>{children}</Box>
              <Stack direction="row" spacing={1.5} flexWrap="wrap">{legend}</Stack>
            </Stack>
          </Paper>
        );
      }

      function LineChart({ values, labels, color = "#42a5f5" }) {
        const width = 760;
        const height = 240;
        const pad = { top: 24, right: 24, bottom: 48, left: 42 };
        const innerW = width - pad.left - pad.right;
        const innerH = height - pad.top - pad.bottom;
        const max = Math.max(1, ...values);
        const stepX = values.length > 1 ? innerW / (values.length - 1) : innerW;
        const points = values.map((value, index) => ({
          x: pad.left + (values.length > 1 ? index * stepX : innerW / 2),
          y: pad.top + innerH - (value / max) * innerH,
        }));
        const area = [`M ${pad.left} ${pad.top + innerH}`, ...points.map((p) => `L ${p.x} ${p.y}`), `L ${pad.left + innerW} ${pad.top + innerH}`, "Z"].join(" ");
        const line = points.map((p, index) => `${index === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
        return (
          <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="240" preserveAspectRatio="none">
            <defs>
              <linearGradient id="lineGrad" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity="0.34" />
                <stop offset="100%" stopColor={color} stopOpacity="0.02" />
              </linearGradient>
            </defs>
            {[0, 1, 2, 3].map((i) => {
              const y = pad.top + (innerH / 3) * i;
              return <line key={i} x1={pad.left} y1={y} x2={pad.left + innerW} y2={y} stroke="rgba(148,163,184,0.16)" strokeDasharray="4 6" />;
            })}
            <path d={area} fill="url(#lineGrad)" />
            <path d={line} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
            {points.map((p, index) => <circle key={index} cx={p.x} cy={p.y} r="5" fill={color} stroke="rgba(15,23,42,0.96)" strokeWidth="3" />)}
            {labels.map((label, index) => {
              const p = points[index];
              return <text key={label} x={p.x} y={height - 16} textAnchor="middle" fill="rgba(185,199,224,0.82)" fontSize="12">{label}</text>;
            })}
          </svg>
        );
      }

      function BarChart({ items }) {
        const width = 760;
        const height = 240;
        const pad = { top: 20, right: 24, bottom: 24, left: 120 };
        const innerW = width - pad.left - pad.right;
        const innerH = height - pad.top - pad.bottom;
        const rowH = innerH / items.length;
        const max = Math.max(1, ...items.map((item) => item.value));
        const colors = ["#42a5f5", "#22c55e", "#f59e0b", "#a855f7"];
        return (
          <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="240" preserveAspectRatio="none">
            {items.map((item, index) => {
              const y = pad.top + index * rowH + 8;
              const barH = Math.max(18, rowH - 16);
              const barW = Math.max(6, (item.value / max) * innerW);
              return (
                <g key={item.label}>
                  <text x={pad.left - 10} y={y + barH - 2} textAnchor="end" fill="rgba(185,199,224,0.86)" fontSize="13">{item.label}</text>
                  <rect x={pad.left} y={y} width={innerW} height={barH} rx="10" fill="rgba(255,255,255,0.06)" />
                  <rect x={pad.left} y={y} width={barW} height={barH} rx="10" fill={colors[index % colors.length]} opacity="0.92" />
                  <text x={pad.left + Math.min(innerW - 8, barW + 10)} y={y + barH - 2} fill="rgba(255,255,255,0.96)" fontSize="13" fontWeight="700">{item.value}</text>
                </g>
              );
            })}
          </svg>
        );
      }

      const renderPageHeader = (title, description, actions = []) => (
        <Stack
          direction={{ xs: "column", lg: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "stretch", lg: "center" }}
          spacing={2}
        >
          <Box>
            <Typography variant="h5" fontWeight={900}>{title}</Typography>
            <Typography color="text.secondary">{description}</Typography>
          </Box>
          <Stack direction="row" spacing={1.25} flexWrap="wrap" justifyContent={{ xs: "flex-start", lg: "flex-end" }}>
            {actions}
          </Stack>
        </Stack>
      );

      const renderOverviewPage = () => (
        <Stack spacing={2.5}>
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: {
                xs: "1fr",
                sm: "repeat(2, minmax(0, 1fr))",
                lg: "repeat(5, minmax(0, 1fr))",
              },
            }}
          >
            {summaryCards.map((item) => (
              <Paper
                key={item.key}
                component="button"
                type="button"
                onClick={() => openStatDialog(item.key)}
                sx={{
                  p: 2.5,
                  minHeight: 210,
                  height: "100%",
                  borderRadius: 2,
                  bgcolor: "background.paper",
                  border: "1px solid",
                  borderColor: "divider",
                  textAlign: "left",
                  cursor: "pointer",
                  color: "inherit",
                  transition: "transform 140ms ease, border-color 140ms ease, box-shadow 140ms ease",
                  "&:hover": {
                    transform: "translateY(-2px)",
                    borderColor: item.tone,
                    boxShadow: `0 14px 32px rgba(0,0,0,0.18)`,
                  },
                  "&:focus-visible": {
                    outline: "none",
                    borderColor: item.tone,
                    boxShadow: `0 0 0 3px ${item.tone}33`,
                  },
                }}
              >
                <Stack spacing={1}>
                  <Typography variant="overline" color="text.secondary" letterSpacing={2}>{item.label}</Typography>
                  <Typography variant="h3" fontWeight={900} sx={{ mt: 1 }}>{item.value}</Typography>
                  <Typography color="text.secondary" sx={{ mt: 2 }}>{item.hint}</Typography>
                  <Chip
                    size="small"
                    label="Open list"
                    sx={{
                      alignSelf: "flex-start",
                      mt: 2,
                      bgcolor: `${item.tone}22`,
                      color: item.tone,
                      fontWeight: 800,
                    }}
                  />
                </Stack>
              </Paper>
            ))}
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={12} lg={8}>
              <MiniChart
                title="Login Trend"
                subtitle="Login activity for the last 7 days, grouped from the login history table."
                legend={[
                  chartLegendItem("#42a5f5", "Login attempts"),
                  chartLegendItem("#22c55e", "Success / failure grouped from history"),
                ]}
              >
                <LineChart values={trendValues} labels={days.map((d) => d.label)} />
              </MiniChart>
            </Grid>
            <Grid item xs={12} lg={4}>
              <MiniChart
                title="User Breakdown"
                subtitle="Current status mix across active, inactive, expired, and admin accounts."
                legend={breakdown.map((item, index) => chartLegendItem(["#42a5f5", "#22c55e", "#f59e0b", "#a855f7"][index], `${item.label} ${item.value}`))}
              >
                <BarChart items={breakdown} />
              </MiniChart>
            </Grid>
          </Grid>
        </Stack>
      );

      const renderUsersPage = () => (
        <Stack spacing={2.5}>
          {renderPageHeader(
            "Users",
            "Search, paginate, and manage permissions, login restrictions, device binding, and validity.",
            [
              <Button key="refresh" variant="outlined" onClick={() => refreshUsers(auth)}>Refresh Users</Button>,
              <Button key="create" variant="contained" onClick={openCreateUser}>Create User</Button>,
            ],
          )}

          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <TextField label="Search username, name, role, device..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} fullWidth />
            <FormControl sx={{ minWidth: 180 }}>
              <InputLabel>Filter</InputLabel>
              <Select label="Filter" value={filter} onChange={(e) => { setFilter(e.target.value); setPage(0); }}>
                <MenuItem value="all">All users</MenuItem>
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="inactive">Inactive</MenuItem>
                <MenuItem value="admin">Admins</MenuItem>
                <MenuItem value="expired">Expired validity</MenuItem>
              </Select>
            </FormControl>
            <FormControl sx={{ minWidth: 140 }}>
              <InputLabel>Rows</InputLabel>
              <Select label="Rows" value={rowsPerPage} onChange={(e) => { setRowsPerPage(Number(e.target.value)); setPage(0); }}>
                {[5, 10, 20, 50].map((n) => <MenuItem key={n} value={n}>{n} / page</MenuItem>)}
              </Select>
            </FormControl>
          </Stack>

          <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, borderColor: "divider", overflowX: "auto" }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  {["ID", "Username", "Name", "Permission", "Status", "Validity", "Last Login", "Emails Sent", "Actions"].map((head) => (
                    <TableCell key={head} sx={{ fontWeight: 900 }}>{head}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {pagedUsers.map((user) => (
                  <TableRow key={user.id} hover selected={selectedUser?.id === user.id}>
                    <TableCell>{user.id}</TableCell>
                    <TableCell>{fmt(user.username)}</TableCell>
                    <TableCell>{fmt(user.display_name)}</TableCell>
                    <TableCell><Chip size="small" label={fmt(user.role)} color={String(user.role || "").toLowerCase() === "admin" ? "secondary" : "default"} /></TableCell>
                    <TableCell><Chip size="small" label={user.is_active ? "Active" : "Inactive"} color={user.is_active ? "success" : "error"} /></TableCell>
                    <TableCell>{formatDate(user.login_valid_until)}</TableCell>
                    <TableCell>{`${formatDate(user.last_login_at)} ${fmt(user.last_login_ip)}`}</TableCell>
                    <TableCell>{Number(user.sent_email_count || 0).toLocaleString()}</TableCell>
                    <TableCell>
                      <Button size="small" variant="outlined" onClick={(event) => { setMenuAnchor(event.currentTarget); setMenuUser(user); setSelectedUser(user); }}>⋮</Button>
                    </TableCell>
                  </TableRow>
                ))}
                {!pagedUsers.length && (
                  <TableRow>
                    <TableCell colSpan={9}>
                      <Typography color="text.secondary">No users found for the current search and filter.</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={filteredUsers.length}
            page={page}
            onPageChange={(_, nextPage) => setPage(nextPage)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => { setRowsPerPage(Number(e.target.value)); setPage(0); }}
            rowsPerPageOptions={[5, 10, 20, 50]}
          />
        </Stack>
      );

      const renderExpiredPage = () => (
        <Stack spacing={2.5}>
          {renderPageHeader(
            "Validity Expired",
            "Accounts whose login validity is already expired.",
            [<Button key="refresh" variant="outlined" onClick={() => refreshUsers(auth)}>Refresh Expired</Button>],
          )}

          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <TextField label="Search username, name, role, device..." value={expiredSearch} onChange={(e) => { setExpiredSearch(e.target.value); setExpiredPage(0); }} fullWidth />
            <FormControl sx={{ minWidth: 140 }}>
              <InputLabel>Rows</InputLabel>
              <Select label="Rows" value={expiredRowsPerPage} onChange={(e) => { setExpiredRowsPerPage(Number(e.target.value)); setExpiredPage(0); }}>
                {[5, 10, 20, 50].map((n) => <MenuItem key={n} value={n}>{n} / page</MenuItem>)}
              </Select>
            </FormControl>
          </Stack>

          <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, borderColor: "divider", overflowX: "auto" }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  {["ID", "Username", "Name", "Permission", "Status", "Validity", "Last Login", "Emails Sent", "Actions"].map((head) => (
                    <TableCell key={head} sx={{ fontWeight: 900 }}>{head}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {pagedExpiredUsers.map((user) => (
                  <TableRow key={user.id} hover selected={selectedUser?.id === user.id}>
                    <TableCell>{user.id}</TableCell>
                    <TableCell>{fmt(user.username)}</TableCell>
                    <TableCell>{fmt(user.display_name)}</TableCell>
                    <TableCell><Chip size="small" label={fmt(user.role)} color={String(user.role || "").toLowerCase() === "admin" ? "secondary" : "default"} /></TableCell>
                    <TableCell><Chip size="small" label={user.is_active ? "Active" : "Inactive"} color={user.is_active ? "success" : "error"} /></TableCell>
                    <TableCell>{formatDate(user.login_valid_until)}</TableCell>
                    <TableCell>{`${formatDate(user.last_login_at)} ${fmt(user.last_login_ip)}`}</TableCell>
                    <TableCell>{Number(user.sent_email_count || 0).toLocaleString()}</TableCell>
                    <TableCell>
                      <Button size="small" variant="outlined" onClick={(event) => { setMenuAnchor(event.currentTarget); setMenuUser(user); setSelectedUser(user); }}>⋮</Button>
                    </TableCell>
                  </TableRow>
                ))}
                {!pagedExpiredUsers.length && (
                  <TableRow>
                    <TableCell colSpan={9}>
                      <Typography color="text.secondary">No expired users match the search.</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={filteredExpiredUsers.length}
            page={expiredPage}
            onPageChange={(_, nextPage) => setExpiredPage(nextPage)}
            rowsPerPage={expiredRowsPerPage}
            onRowsPerPageChange={(e) => { setExpiredRowsPerPage(Number(e.target.value)); setExpiredPage(0); }}
            rowsPerPageOptions={[5, 10, 20, 50]}
          />
        </Stack>
      );

      const renderActivityPage = () => (
        <Stack spacing={2.5}>
          {renderPageHeader(
            "Activity",
            "Recent backend activity across all accounts.",
            [<Button key="refresh" variant="outlined" onClick={() => refreshActivity(auth)}>Refresh Activity</Button>],
          )}

          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <TextField label="Search username, category, action, IP, or location..." value={activitySearch} onChange={(e) => { setActivitySearch(e.target.value); setActivityPage(0); }} fullWidth />
            <FormControl sx={{ minWidth: 140 }}>
              <InputLabel>Rows</InputLabel>
              <Select label="Rows" value={activityRowsPerPage} onChange={(e) => { setActivityRowsPerPage(Number(e.target.value)); setActivityPage(0); }}>
                {[5, 10, 20, 50].map((n) => <MenuItem key={n} value={n}>{n} / page</MenuItem>)}
              </Select>
            </FormControl>
          </Stack>

          <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, overflowX: "auto" }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  {["ID", "Username", "Category", "Action", "Details", "IP", "Location", "Created"].map((head) => <TableCell key={head} sx={{ fontWeight: 900 }}>{head}</TableCell>)}
                </TableRow>
              </TableHead>
              <TableBody>
                {pagedActivity.map((row) => (
                  <TableRow key={row.id} hover>
                    <TableCell>{row.id}</TableCell>
                    <TableCell>{fmt(row.username)}</TableCell>
                    <TableCell>{fmt(row.category)}</TableCell>
                    <TableCell>{fmt(row.action)}</TableCell>
                    <TableCell>{fmt(row.details_json)}</TableCell>
                    <TableCell>{fmt(row.ip_address)}</TableCell>
                    <TableCell>{fmt(row.location_label)}</TableCell>
                    <TableCell>{formatDate(row.created_at)}</TableCell>
                  </TableRow>
                ))}
                {!pagedActivity.length && (
                  <TableRow>
                    <TableCell colSpan={8}>
                      <Typography color="text.secondary">No activity rows match the search.</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={filteredActivity.length}
            page={activityPage}
            onPageChange={(_, nextPage) => setActivityPage(nextPage)}
            rowsPerPage={activityRowsPerPage}
            onRowsPerPageChange={(e) => { setActivityRowsPerPage(Number(e.target.value)); setActivityPage(0); }}
            rowsPerPageOptions={[5, 10, 20, 50]}
          />
        </Stack>
      );

      const renderHistoryPage = () => (
        <Stack spacing={2.5}>
          {renderPageHeader(
            "Login History",
            "Login attempts, device fingerprints, and access decisions.",
            [<Button key="refresh" variant="outlined" onClick={() => refreshHistory(auth)}>Refresh History</Button>],
          )}

          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <TextField label="Search username, IP, device, agent, or success..." value={historySearch} onChange={(e) => { setHistorySearch(e.target.value); setHistoryPage(0); }} fullWidth />
            <FormControl sx={{ minWidth: 140 }}>
              <InputLabel>Rows</InputLabel>
              <Select label="Rows" value={historyRowsPerPage} onChange={(e) => { setHistoryRowsPerPage(Number(e.target.value)); setHistoryPage(0); }}>
                {[5, 10, 20, 50].map((n) => <MenuItem key={n} value={n}>{n} / page</MenuItem>)}
              </Select>
            </FormControl>
          </Stack>

          <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, overflowX: "auto" }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  {["ID", "User ID", "Username", "Success", "IP", "Device Fingerprint", "Device Name", "Agent", "Created"].map((head) => <TableCell key={head} sx={{ fontWeight: 900 }}>{head}</TableCell>)}
                </TableRow>
              </TableHead>
              <TableBody>
                {pagedHistory.map((row) => (
                  <TableRow key={row.id} hover>
                    <TableCell>{row.id}</TableCell>
                    <TableCell>{row.user_id}</TableCell>
                    <TableCell>{fmt(row.username)}</TableCell>
                    <TableCell><Chip size="small" label={row.success ? "Success" : "Failed"} color={row.success ? "success" : "error"} /></TableCell>
                    <TableCell>{fmt(row.ip_address)}</TableCell>
                    <TableCell>{fmt(row.device_fingerprint)}</TableCell>
                    <TableCell>{fmt(row.device_name)}</TableCell>
                    <TableCell>{fmt(row.user_agent)}</TableCell>
                    <TableCell>{formatDate(row.created_at)}</TableCell>
                  </TableRow>
                ))}
                {!pagedHistory.length && (
                  <TableRow>
                    <TableCell colSpan={9}>
                      <Typography color="text.secondary">No login history rows match the search.</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={filteredHistory.length}
            page={historyPage}
            onPageChange={(_, nextPage) => setHistoryPage(nextPage)}
            rowsPerPage={historyRowsPerPage}
            onRowsPerPageChange={(e) => { setHistoryRowsPerPage(Number(e.target.value)); setHistoryPage(0); }}
            rowsPerPageOptions={[5, 10, 20, 50]}
          />
        </Stack>
      );

      const renderCronJobsPage = () => (
        <Stack spacing={2.5}>
          {renderPageHeader(
            "Cron Jobs",
            "Scheduled maintenance jobs and their latest synchronization status.",
            [<Button key="refresh" variant="outlined" onClick={() => refreshCronJobs(auth)}>Refresh Cron Jobs</Button>],
          )}

          <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, overflowX: "auto" }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  {["Job", "Schedule", "Status", "Last Run", "Last Synced", "Next Run", "Result"].map((head) => (
                    <TableCell key={head} sx={{ fontWeight: 900 }}>{head}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {cronJobs.map((job) => (
                  <TableRow key={job.job_key} hover>
                    <TableCell>{fmt(job.job_name)}</TableCell>
                    <TableCell>{fmt(job.schedule_label)}</TableCell>
                    <TableCell><Chip size="small" label={fmt(job.status)} color={job.status === "Completed" ? "success" : "default"} /></TableCell>
                    <TableCell>{formatDate(job.last_run_at) || "Not run yet"}</TableCell>
                    <TableCell>{formatDate(job.last_sync_at) || "Not synced yet"}</TableCell>
                    <TableCell>{formatDate(job.next_run_at) || "Not scheduled"}</TableCell>
                    <TableCell>{fmt(job.last_result)}</TableCell>
                  </TableRow>
                ))}
                {!cronJobs.length && (
                  <TableRow>
                    <TableCell colSpan={7}><Typography color="text.secondary">No cron jobs configured.</Typography></TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Stack>
      );

      const renderActiveSection = () => {
        if (activeSection === "users") return renderUsersPage();
        if (activeSection === "expired") return renderExpiredPage();
        if (activeSection === "activity") return renderActivityPage();
        if (activeSection === "history") return renderHistoryPage();
        if (activeSection === "cron-jobs") return renderCronJobsPage();
        return renderOverviewPage();
      };

      if (!auth?.access_token) {
        return (
          <ThemeProvider theme={theme}>
            <CssBaseline />
            <GlobalStyles styles={{
              body: {
                background: mode === "dark"
                  ? "radial-gradient(circle at 8% 8%, rgba(25,118,210,0.18), transparent 20%), radial-gradient(circle at 92% 0%, rgba(124,58,237,0.12), transparent 18%), linear-gradient(180deg, #09111d 0%, #0a0f18 100%)"
                  : "linear-gradient(180deg, #f6f8fc 0%, #edf2fb 100%)",
              },
            }} />
            <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
              <Paper sx={{
                width: "min(960px, 100%)",
                overflow: "hidden",
                borderRadius: 2,
                border: "1px solid",
                borderColor: "divider",
                boxShadow: "0 28px 80px rgba(0,0,0,0.28)",
              }}>
                <Grid container>
                  <Grid item xs={12} sx={{ p: 4 }}>
                    <Stack spacing={3}>
                      <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={2}>
                        <Box>
                          <Typography variant="h5" fontWeight={900}>Admin Login</Typography>
                          <Typography color="text.secondary">Sign in to open the server-side admin site.</Typography>
                        </Box>
                        <FormControlLabel control={<Switch checked={mode === "dark"} onChange={() => setMode((m) => m === "dark" ? "light" : "dark")} />} label={mode === "dark" ? "Dark" : "Light"} />
                      </Stack>
                      <TextField label="Username" value={loginForm.username} onChange={(e) => setLoginForm((prev) => ({ ...prev, username: e.target.value }))} fullWidth />
                      <TextField label="Password" type="password" value={loginForm.password} onChange={(e) => setLoginForm((prev) => ({ ...prev, password: e.target.value }))} fullWidth />
                      <Stack direction="row" spacing={1.5}>
                        <Button variant="contained" onClick={() => loadAuthLogin(false)} disabled={loginSubmitting}>
                          {loginSubmitting ? "Signing In..." : "Sign In"}
                        </Button>
                        <Button variant="outlined" onClick={() => notify("Use your current authorized credentials.", "info")}>Help</Button>
                      </Stack>
                    </Stack>
                  </Grid>
                </Grid>
              </Paper>
            </Box>
            <Dialog open={!!loginConflict} onClose={() => setLoginConflict(null)} maxWidth="sm" fullWidth>
              <DialogTitle>Already logged in on another device</DialogTitle>
              <DialogContent>
                <Typography color="text.secondary">
                  {extractApiMessage(loginConflict, "You are already logged in on another device. Do you want to log out from the other device and continue?")}
                </Typography>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setLoginConflict(null)} variant="outlined">
                  No
                </Button>
                <Button
                  onClick={() => {
                    setLoginConflict(null);
                    loadAuthLogin(true);
                  }}
                  variant="contained"
                >
                  Yes, log out other device
                </Button>
              </DialogActions>
            </Dialog>
            <Snackbar open={message.open} autoHideDuration={3500} onClose={closeMessage}>
              <Alert severity={message.severity} onClose={closeMessage} variant="filled">{message.text}</Alert>
            </Snackbar>
          </ThemeProvider>
        );
      }

      const sidebar = (
        <Box sx={{ p: 2.25, height: "100%", display: "flex", flexDirection: "column" }}>
          <Paper sx={{ p: 1.5, borderRadius: 2, bgcolor: "background.paper", border: "1px solid", borderColor: "divider" }}>
            <List dense>
              {[
                ["overview", "Overview"],
                ["users", "Users"],
                ["expired", "Validity Expired"],
                ["activity", "Activity"],
                ["history", "Login History"],
                ["cron-jobs", "Cron Jobs"],
              ].map(([key, label]) => (
                <ListItemButton
                  key={key}
                  selected={activeSection === key}
                  onClick={() => {
                    setActiveSection(key);
                    if (!isDesktop) setMobileOpen(false);
                  }}
                  sx={{ borderRadius: 1.5, mb: 1 }}
                >
                  <ListItemText primary={label} primaryTypographyProps={{ fontWeight: 700 }} />
                </ListItemButton>
              ))}
            </List>
          </Paper>
        </Box>
      );

      return (
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <GlobalStyles styles={{
            body: {
              background: mode === "dark"
                ? "radial-gradient(circle at 8% 8%, rgba(25,118,210,0.18), transparent 20%), radial-gradient(circle at 92% 0%, rgba(124,58,237,0.12), transparent 18%), linear-gradient(180deg, #09111d 0%, #0a0f18 100%)"
                : "linear-gradient(180deg, #f6f8fc 0%, #edf2fb 100%)",
            },
          }} />
          <Box sx={{ display: "flex", minHeight: "100vh" }}>
            <AppBar position="fixed" elevation={0} sx={{ zIndex: (t) => t.zIndex.drawer + 1, borderBottom: "1px solid", borderColor: "divider", bgcolor: "background.paper", color: "text.primary" }}>
              <Toolbar sx={{ gap: 1.5 }}>
                {!isDesktop && (
                  <IconButton edge="start" onClick={() => setMobileOpen(true)} sx={{ mr: 1 }}>
                    <Box component="span" sx={{ fontSize: 22 }}>☰</Box>
                  </IconButton>
                )}
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h6" fontWeight={900}>CRM Dashboard</Typography>
                  <Typography variant="caption" color="text.secondary">Users, permissions, validity, login restrictions, charts, and activity.</Typography>
                </Box>
                <FormControlLabel
                  control={<Switch checked={mode === "dark"} onChange={() => setMode((m) => m === "dark" ? "light" : "dark")} />}
                  label={mode === "dark" ? "Dark" : "Light"}
                />
                <Button variant="outlined" onClick={() => refreshAll(auth)}>Refresh All</Button>
                <Button variant="contained" color="inherit" onClick={() => logoutCurrentSession("Logged out")}>Logout</Button>
              </Toolbar>
            </AppBar>

            <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
              <Drawer
                variant={isDesktop ? "permanent" : "temporary"}
                open={isDesktop ? true : mobileOpen}
                onClose={() => setMobileOpen(false)}
                ModalProps={{ keepMounted: true }}
                sx={{
                  "& .MuiDrawer-paper": {
                    width: drawerWidth,
                    boxSizing: "border-box",
                    borderRight: "1px solid",
                    borderColor: "divider",
                    bgcolor: "background.default",
                    ...(isDesktop ? { top: 64, height: "calc(100vh - 64px)" } : {}),
                  },
                }}
              >
                <Toolbar />
                {sidebar}
              </Drawer>
            </Box>

            <Box component="main" sx={{ flexGrow: 1, p: { xs: 1.5, sm: 2, md: 3 }, width: { md: `calc(100% - ${drawerWidth}px)` } }}>
              <Toolbar />
              <Stack spacing={2.5}>
                {renderActiveSection()}
              </Stack>
            </Box>

            <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={() => setMenuAnchor(null)}>
              {[
                ["details", "View details"],
                ["edit", "Edit user"],
                ["activate", "Activate", menuUser && !menuUser.is_active],
                ["deactivate", "Deactivate", menuUser && !!menuUser.is_active],
                ["admin", "Set Admin", menuUser && String(menuUser.role || "").toLowerCase() !== "admin"],
                ["user", "Set User", menuUser && String(menuUser.role || "").toLowerCase() === "admin"],
                ["any-device", "Allow any device", menuUser && !!(menuUser.device_fingerprint || menuUser.device_name)],
                ["keep-device", "Keep current device", menuUser && !(menuUser.device_fingerprint || menuUser.device_name)],
                ["valid-30", "Validity +30d"],
                ["valid-90", "Validity +90d"],
                ["clear-validity", "Clear validity", menuUser && !!menuUser.login_valid_until],
                ["reset-password", "Reset password"],
                ["reset-device", "Reset device", menuUser && !!(menuUser.device_fingerprint || menuUser.device_name)],
              ].filter(([, , visible = true]) => visible).map(([value, label]) => <MenuItem key={value} onClick={() => handleMenu(value)}>{label}</MenuItem>)}
            </Menu>

            <Dialog fullScreen open={detailOpen} onClose={() => setDetailOpen(false)}>
              <Box sx={{ bgcolor: "background.default", minHeight: "100vh" }}>
                <Box sx={{ px: { xs: 2, md: 3 }, py: 2, borderBottom: "1px solid", borderColor: "divider", position: "sticky", top: 0, zIndex: 2, bgcolor: "background.paper" }}>
                  <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" alignItems={{ xs: "flex-start", md: "center" }} spacing={2}>
                    <Box>
                      <Typography variant="h5" fontWeight={900}>User Details</Typography>
                      <Typography color="text.secondary">
                        {detailData?.user ? `${detailData.user.username} · Full access history, device binding, and login records.` : "Loading selected user information."}
                      </Typography>
                      {detailData?.user && (
                        <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap">
                          <Chip
                            size="small"
                            label={detailData.online_status_label || (detailData.online_status ? "Online" : "Offline")}
                            color={detailData.online_status ? "success" : "error"}
                            sx={{ fontWeight: 800 }}
                          />
                          <Chip
                            size="small"
                            label={detailData.user.is_active ? "Active account" : "Inactive account"}
                            color={detailData.user.is_active ? "success" : "default"}
                            variant="outlined"
                          />
                        </Stack>
                      )}
                    </Box>
                    <Stack direction="row" spacing={1.5} flexWrap="wrap">
                      <Button variant="outlined" onClick={() => detailData?.user && openDetails(detailData.user)} disabled={detailLoading}>Refresh</Button>
                      <Button variant="outlined" onClick={() => detailData?.user && openEditor(detailData.user)} disabled={detailLoading || !detailData?.user}>Edit User</Button>
                      <Button
                        variant="outlined"
                        color={detailData?.user?.is_active ? "error" : "success"}
                        onClick={() => detailData?.user && runDetailAction(detailData.user.is_active ? "/deactivate" : "/activate")}
                        disabled={detailLoading || !detailData?.user}
                      >
                        {detailData?.user?.is_active ? "Deactivate" : "Activate"}
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={() => {
                          if (!detailData?.user) return;
                          const password = window.prompt(`Enter new password for ${detailData.user.username}`) || "";
                          if (!password) return;
                          runDetailAction("/reset-password", { password });
                        }}
                        disabled={detailLoading || !detailData?.user}
                      >
                        Reset Password
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={() => detailData?.user && runDetailAction("/reset-device")}
                        disabled={detailLoading || !detailData?.user}
                      >
                        Reset Device
                      </Button>
                      <Button variant="contained" onClick={() => setDetailOpen(false)}>Close</Button>
                    </Stack>
                  </Stack>
                </Box>

                <Box sx={{ p: { xs: 2, md: 3 } }}>
                  {detailLoading && (
                    <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
                      <Typography fontWeight={800}>Loading user details...</Typography>
                    </Paper>
                  )}

                  {!detailLoading && detailData?.user && (
                    <Stack spacing={2.5}>
                      <Grid container spacing={2}>
                        {[
                          ["Username", detailData.user.username],
                          ["Display Name", detailData.user.display_name || "No display name"],
                          ["Role", detailData.user.role],
                          ["Status", detailData.user.is_active ? "Active" : "Inactive"],
                          ["Online Status", detailData.online_status ? "Online" : "Offline"],
                          ["Emails Sent", Number(detailData.user.sent_email_count || 0).toLocaleString()],
                          ["Validity", formatDate(detailData.user.login_valid_until) || "No expiry set"],
                          ["Last Login", `${formatDate(detailData.user.last_login_at)} ${fmt(detailData.user.last_login_ip)}`],
                        ].map(([label, value]) => (
                          <Grid item xs={12} sm={6} lg={4} key={label}>
                            <Paper variant="outlined" sx={{ p: 2, borderRadius: 1.5, height: "100%" }}>
                              <Typography variant="caption" color="text.secondary">{label}</Typography>
                              <Typography fontWeight={800} sx={{ mt: 0.5 }}>{value}</Typography>
                            </Paper>
                          </Grid>
                        ))}
                      </Grid>

                      <Paper variant="outlined" sx={{ p: 2, borderRadius: 1.5 }}>
                        <Typography variant="h6" fontWeight={900}>Daily Email Sent Count</Typography>
                        <TableContainer sx={{ maxHeight: 320, overflow: "auto", mt: 1.5 }}>
                          <Table stickyHeader size="small">
                            <TableHead>
                              <TableRow>
                                {["Date", "Emails Sent"].map((head) => (
                                  <TableCell key={head} sx={{ fontWeight: 900 }}>{head}</TableCell>
                                ))}
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {(detailData.sent_email_daily || []).map((row) => (
                                <TableRow key={String(row.sent_date)} hover>
                                  <TableCell>{formatDate(row.sent_date)}</TableCell>
                                  <TableCell>{Number(row.sent_count || 0).toLocaleString()}</TableCell>
                                </TableRow>
                              ))}
                              {!(detailData.sent_email_daily || []).length && (
                                <TableRow>
                                  <TableCell colSpan={2}>
                                    <Typography color="text.secondary">No emails sent yet.</Typography>
                                  </TableCell>
                                </TableRow>
                              )}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </Paper>

                      <Grid container spacing={2}>
                        <Grid item xs={12} lg={4}>
                          <Paper variant="outlined" sx={{ p: 2, borderRadius: 1.5, height: "100%" }}>
                            <Typography variant="h6" fontWeight={900}>Current Device</Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                              The fingerprint below is used as the stable MAC / device ID in this browser-based setup.
                            </Typography>
                            <Stack spacing={1.25} sx={{ mt: 2 }}>
                              {[
                                ["MAC / Device ID", detailData.current_device?.mac_id || detailData.current_device?.device_fingerprint || "Not bound"],
                                ["Device Name", detailData.current_device?.device_name || "Not bound"],
                                ["Last Login Device", detailData.current_device?.last_login_device || "Not bound"],
                                ["IP", detailData.current_device?.device_ip || "Not bound"],
                                ["Bound At", formatDate(detailData.current_device?.device_bound_at) || "Not bound"],
                              ].map(([label, value]) => (
                                <Paper key={label} variant="outlined" sx={{ p: 1.5, borderRadius: 1.5 }}>
                                  <Typography variant="caption" color="text.secondary">{label}</Typography>
                                  <Typography fontWeight={700}>{value}</Typography>
                                </Paper>
                              ))}
                            </Stack>
                          </Paper>
                        </Grid>

                        <Grid item xs={12} lg={8}>
                          <Paper variant="outlined" sx={{ p: 2, borderRadius: 1.5, height: "100%" }}>
                            <Typography variant="h6" fontWeight={900}>Device Registered History</Typography>
                            <Typography color="text.secondary" sx={{ mb: 2 }}>
                              Grouped from successful login events by fingerprint and device name.
                            </Typography>
                            <TableContainer sx={{ maxHeight: 320, overflow: "auto" }}>
                              <Table stickyHeader size="small">
                                <TableHead>
                                  <TableRow>
                                    {["Device", "Fingerprint", "First Seen", "Last Seen", "Logins", "IP"].map((head) => (
                                      <TableCell key={head} sx={{ fontWeight: 900 }}>{head}</TableCell>
                                    ))}
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {(detailData.device_history || []).map((row) => (
                                    <TableRow key={row.key} hover>
                                      <TableCell>{row.device_name || "Unknown"}</TableCell>
                                      <TableCell>{row.device_fingerprint || "Not available"}</TableCell>
                                      <TableCell>{formatDate(row.first_seen_at)}</TableCell>
                                      <TableCell>{formatDate(row.last_seen_at)}</TableCell>
                                      <TableCell>{row.login_count}</TableCell>
                                      <TableCell>{row.ip_address || ""}</TableCell>
                                    </TableRow>
                                  ))}
                                  {!(detailData.device_history || []).length && (
                                    <TableRow>
                                      <TableCell colSpan={6}>
                                        <Typography color="text.secondary">No registered devices found for this user yet.</Typography>
                                      </TableCell>
                                    </TableRow>
                                  )}
                                </TableBody>
                              </Table>
                            </TableContainer>
                          </Paper>
                        </Grid>
                      </Grid>

                      <Grid container spacing={2}>
                        <Grid item xs={12} lg={6}>
                          <Paper variant="outlined" sx={{ p: 2, borderRadius: 1.5, height: "100%" }}>
                            <Typography variant="h6" fontWeight={900}>Recent Login History</Typography>
                            <TableContainer sx={{ maxHeight: 360, overflow: "auto", mt: 1.5 }}>
                              <Table stickyHeader size="small">
                                <TableHead>
                                  <TableRow>
                                    {["Success", "IP", "Device", "Created"].map((head) => (
                                      <TableCell key={head} sx={{ fontWeight: 900 }}>{head}</TableCell>
                                    ))}
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {(detailData.login_history || []).slice(0, 20).map((row) => (
                                    <TableRow key={row.id} hover>
                                      <TableCell>
                                        <Chip size="small" label={row.success ? "Success" : "Failed"} color={row.success ? "success" : "error"} />
                                      </TableCell>
                                      <TableCell>{fmt(row.ip_address)}</TableCell>
                                      <TableCell>{fmt(row.device_name || row.device_fingerprint)}</TableCell>
                                      <TableCell>{formatDate(row.created_at)}</TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </TableContainer>
                          </Paper>
                        </Grid>

                        <Grid item xs={12} lg={6}>
                          <Paper variant="outlined" sx={{ p: 2, borderRadius: 1.5, height: "100%" }}>
                            <Typography variant="h6" fontWeight={900}>Recent Activity</Typography>
                            <TableContainer sx={{ maxHeight: 360, overflow: "auto", mt: 1.5 }}>
                              <Table stickyHeader size="small">
                                <TableHead>
                                  <TableRow>
                                    {["Category", "Action", "Details", "Created"].map((head) => (
                                      <TableCell key={head} sx={{ fontWeight: 900 }}>{head}</TableCell>
                                    ))}
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {(detailData.activity || []).slice(0, 20).map((row) => (
                                    <TableRow key={row.id} hover>
                                      <TableCell>{fmt(row.category)}</TableCell>
                                      <TableCell>{fmt(row.action)}</TableCell>
                                      <TableCell>{fmt(row.details_json)}</TableCell>
                                      <TableCell>{formatDate(row.created_at)}</TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </TableContainer>
                          </Paper>
                        </Grid>
                      </Grid>
                    </Stack>
                  )}
                </Box>
              </Box>
            </Dialog>

            <Dialog fullScreen open={statDialogOpen} onClose={() => setStatDialogOpen(false)}>
              <Box sx={{ bgcolor: "background.default", minHeight: "100vh" }}>
                <Box sx={{ px: { xs: 2, md: 3 }, py: 2, borderBottom: "1px solid", borderColor: "divider", position: "sticky", top: 0, zIndex: 2, bgcolor: "background.paper" }}>
                  <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" alignItems={{ xs: "flex-start", md: "center" }} spacing={2}>
                    <Box>
                      <Typography variant="h5" fontWeight={900}>{currentStatView.title}</Typography>
                      <Typography color="text.secondary">{currentStatView.description}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {statRows.length} matching users
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={1.5} flexWrap="wrap">
                      <Button variant="outlined" onClick={() => refreshUsers(auth)} disabled={loading}>Refresh Users</Button>
                      <Button variant="contained" onClick={() => setStatDialogOpen(false)}>Close</Button>
                    </Stack>
                  </Stack>
                </Box>

                <Box sx={{ p: { xs: 2, md: 3 } }}>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mb: 2 }}>
                    <TextField
                      label="Search username, name, role, device..."
                      value={statSearch}
                      onChange={(e) => { setStatSearch(e.target.value); setStatPage(0); }}
                      fullWidth
                    />
                    <FormControl sx={{ minWidth: 140 }}>
                      <InputLabel>Rows</InputLabel>
                      <Select
                        label="Rows"
                        value={statRowsPerPage}
                        onChange={(e) => { setStatRowsPerPage(Number(e.target.value)); setStatPage(0); }}
                      >
                        {[5, 10, 20, 50].map((n) => <MenuItem key={n} value={n}>{n} / page</MenuItem>)}
                      </Select>
                    </FormControl>
                  </Stack>

                  <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, overflowX: "auto" }}>
                    <Table stickyHeader size="small">
                      <TableHead>
                        <TableRow>
                          {["ID", "Username", "Name", "Role", "Status", "Validity", "Last Login", "Emails Sent", "Online"].map((head) => (
                            <TableCell key={head} sx={{ fontWeight: 900 }}>{head}</TableCell>
                          ))}
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {pagedStatRows.map((user) => (
                          <TableRow key={user.id} hover selected={selectedUser?.id === user.id}>
                            <TableCell>{user.id}</TableCell>
                            <TableCell>{fmt(user.username)}</TableCell>
                            <TableCell>{fmt(user.display_name)}</TableCell>
                            <TableCell>
                              <Chip
                                size="small"
                                label={fmt(user.role)}
                                color={String(user.role || "").toLowerCase() === "admin" ? "secondary" : "default"}
                              />
                            </TableCell>
                            <TableCell>
                              <Chip
                                size="small"
                                label={user.is_active ? "Active" : "Inactive"}
                                color={user.is_active ? "success" : "error"}
                              />
                            </TableCell>
                            <TableCell>{formatDate(user.login_valid_until)}</TableCell>
                            <TableCell>{`${formatDate(user.last_login_at)} ${fmt(user.last_login_ip)}`}</TableCell>
                            <TableCell>{Number(user.sent_email_count || 0).toLocaleString()}</TableCell>
                            <TableCell>
                              <Chip
                                size="small"
                                label={isRealtimeOnline(user) ? "Online" : "Offline"}
                                color={isRealtimeOnline(user) ? "success" : "default"}
                                variant={isRealtimeOnline(user) ? "filled" : "outlined"}
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                        {!pagedStatRows.length && (
                          <TableRow>
                            <TableCell colSpan={9}>
                              <Typography color="text.secondary">No users match the current search.</Typography>
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  <TablePagination
                    component="div"
                    count={statRows.length}
                    page={statPage}
                    onPageChange={(_, nextPage) => setStatPage(nextPage)}
                    rowsPerPage={statRowsPerPage}
                    onRowsPerPageChange={(e) => { setStatRowsPerPage(Number(e.target.value)); setStatPage(0); }}
                    rowsPerPageOptions={[5, 10, 20, 50]}
                  />
                </Box>
              </Box>
            </Dialog>

            <Dialog open={editorOpen} onClose={() => setEditorOpen(false)} fullWidth maxWidth="md">
              <DialogTitle sx={{ fontWeight: 900 }}>
                {createOpen ? "Create User" : "Edit User"}
              </DialogTitle>
              <DialogContent dividers>
                <Stack spacing={2} sx={{ pt: 1 }}>
                  <TextField label="Selected User ID" value={form.id} InputProps={{ readOnly: true }} />
                  <Grid container spacing={1.5}>
                    <Grid item xs={12} md={6}>
                      <TextField label="Username" value={form.username} onChange={(e) => setForm((prev) => ({ ...prev, username: e.target.value }))} fullWidth />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField label="Display Name" value={form.display_name} onChange={(e) => setForm((prev) => ({ ...prev, display_name: e.target.value }))} fullWidth />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <FormControl fullWidth>
                        <InputLabel>Role</InputLabel>
                        <Select label="Role" value={form.role} onChange={(e) => setForm((prev) => ({ ...prev, role: e.target.value }))}>
                          <MenuItem value="user">User</MenuItem>
                          <MenuItem value="admin">Admin</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <FormControl fullWidth>
                        <InputLabel>Login Restriction</InputLabel>
                        <Select label="Login Restriction" value={form.loginRestriction} onChange={(e) => setForm((prev) => ({ ...prev, loginRestriction: e.target.value }))}>
                          <MenuItem value="keep">Keep current device binding</MenuItem>
                          <MenuItem value="any">Allow any device</MenuItem>
                          <MenuItem value="disable">Disable login</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField
                        label="Validity Until"
                        type="datetime-local"
                        value={form.login_valid_until}
                        onChange={(e) => setForm((prev) => ({ ...prev, login_valid_until: e.target.value }))}
                        InputLabelProps={{ shrink: true }}
                        helperText="Optional. Choose a date and time or leave blank."
                        fullWidth
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField label="New Password" type="password" value={form.password} onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))} fullWidth />
                    </Grid>
                  </Grid>
                </Stack>
              </DialogContent>
              <DialogActions sx={{ p: 2 }}>
                <Button onClick={() => setEditorOpen(false)}>Cancel</Button>
                <Button variant="contained" onClick={submitUser}>{createOpen ? "Create User" : "Save Changes"}</Button>
              </DialogActions>
            </Dialog>

            <Snackbar open={message.open} autoHideDuration={3500} onClose={closeMessage}>
              <Alert severity={message.severity} onClose={closeMessage} variant="filled">{message.text}</Alert>
            </Snackbar>
          </Box>
        </ThemeProvider>
      );
    }

    ReactDOM.createRoot(document.getElementById("root")).render(<App />);
  </script>
</body>
</html>""".replace("__API_BASE__", API_BASE_URL)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(
        _html(),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host=SITE_HOST, port=SITE_PORT)
