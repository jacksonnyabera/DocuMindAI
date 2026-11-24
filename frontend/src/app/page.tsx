"use client";

import { FormEvent, useEffect, useState } from "react";

type Profile = {
  user_id: string;
  organization_id: string;
  full_name: string;
  email: string;
  role: string;
};

type SessionResponse = {
  authenticated: boolean;
  profile: Profile | null;
};

type AuthMode = "login" | "register";

export default function Home() {
  const [mode, setMode] = useState<AuthMode>("login");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [organizationName, setOrganizationName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSession() {
      try {
        const response = await fetch("/api/auth/session", {
          cache: "no-store",
        });

        const data = (await response.json()) as SessionResponse;

        if (data.authenticated && data.profile) {
          setProfile(data.profile);
        }
      } catch {
        setError("Unable to connect. Please refresh the page.");
      } finally {
        setLoading(false);
      }
    }

    void loadSession();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      let response: Response;

      if (mode === "register") {
        response = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            organization_name: organizationName,
            full_name: fullName,
            email,
            password,
          }),
        });
      } else {
        const form = new URLSearchParams();
        form.set("username", email);
        form.set("password", password);

        response = await fetch("/api/auth/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: form.toString(),
        });
      }

      const data = await response.json();

      if (!response.ok) {
        const detail = data.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : "Authentication failed. Please check your details.",
        );
      }

      setProfile(data as Profile);
      setPassword("");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    setProfile(null);
    setMode("login");
    setPassword("");
  }

  if (loading) {
    return (
      <main className="loading-screen">
        <div className="loading-mark">D</div>
        <p>Preparing your workspace...</p>
      </main>
    );
  }

  if (profile) {
    return (
      <main className="dashboard">
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-mark">D</div>
            <span>DocuMind<span className="brand-ai">AI</span></span>
          </div>

          <div className="workspace-label">WORKSPACE</div>
          <nav className="navigation">
            <div className="nav-item active">▦ <span>Overview</span></div>
            <div className="nav-item">▤ <span>Documents</span></div>
            <div className="nav-item">⌕ <span>Search</span></div>
            <div className="nav-item">✧ <span>AI Assistant</span></div>
          </nav>

          <div className="sidebar-bottom">
            <div className="user-avatar">
              {profile.full_name.charAt(0).toUpperCase()}
            </div>
            <div className="user-details">
              <strong>{profile.full_name}</strong>
              <span>{profile.email}</span>
            </div>
            <button
              className="logout-button"
              onClick={handleLogout}
              aria-label="Log out"
              title="Log out"
            >
              ↗
            </button>
          </div>
        </aside>

        <section className="dashboard-main">
          <header className="topbar">
            <span className="breadcrumb">Workspace / Overview</span>
            <div className="status-pill">
              <span className="status-dot" />
              Workspace active
            </div>
          </header>

          <div className="dashboard-content">
            <div className="welcome-row">
              <div>
                <p className="eyebrow">YOUR INTELLIGENT WORKSPACE</p>
                <h1>Welcome back, {profile.full_name.split(" ")[0]}.</h1>
                <p className="subtitle">
                  Your knowledge workspace is ready. What would you like to do?
                </p>
              </div>
              <div className="welcome-icon">✧</div>
            </div>

            <div className="feature-grid">
              <article className="feature-card">
                <div className="feature-icon green-icon">▤</div>
                <h2>Documents</h2>
                <p>Upload and organize your PDF documents in one secure place.</p>
                <span className="coming-label">Next integration</span>
              </article>

              <article className="feature-card">
                <div className="feature-icon blue-icon">⌕</div>
                <h2>Semantic Search</h2>
                <p>Find relevant information across your documents using AI.</p>
                <span className="coming-label">Next integration</span>
              </article>

              <article className="feature-card">
                <div className="feature-icon purple-icon">✧</div>
                <h2>AI Assistant</h2>
                <p>Ask questions and receive answers grounded in your documents.</p>
                <span className="coming-label">Next integration</span>
              </article>
            </div>

            <section className="workspace-panel">
              <div>
                <p className="eyebrow">ACCOUNT</p>
                <h2>Your workspace is connected</h2>
                <p>
                  Signed in as {profile.email}. Your documents and queries
                  will be scoped to your organization.
                </p>
              </div>
              <div className="account-role">{profile.role}</div>
            </section>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="auth-layout">
      <section className="auth-brand-panel">
        <div className="brand brand-light">
          <div className="brand-mark">D</div>
          <span>DocuMind<span className="brand-ai">AI</span></span>
        </div>

        <div className="brand-message">
          <div className="decorative-orbit">✧</div>
          <p className="eyebrow">KNOWLEDGE, CONNECTED</p>
          <h1>Your documents.<br />A smarter way to think.</h1>
          <p className="brand-description">
            Turn your documents into knowledge you can search, understand,
            and use with AI.
          </p>
        </div>

        <div className="brand-footer">
          <span>Intelligent document understanding</span>
          <span>© 2026 DocuMindAI</span>
        </div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-form-container">
          <div className="mobile-brand brand">
            <div className="brand-mark">D</div>
            <span>DocuMind<span className="brand-ai">AI</span></span>
          </div>

          <p className="eyebrow">
            {mode === "login" ? "WELCOME BACK" : "GET STARTED"}
          </p>

          <h2>
            {mode === "login" ? "Sign in to your workspace" : "Create your workspace"}
          </h2>

          <p className="form-subtitle">
            {mode === "login"
              ? "Enter your account details to continue."
              : "Set up your organization and owner account."}
          </p>

          <div className="auth-tabs">
            <button
              className={mode === "login" ? "auth-tab selected" : "auth-tab"}
              onClick={() => {
                setMode("login");
                setError("");
              }}
              type="button"
            >
              Sign in
            </button>
            <button
              className={mode === "register" ? "auth-tab selected" : "auth-tab"}
              onClick={() => {
                setMode("register");
                setError("");
              }}
              type="button"
            >
              Create account
            </button>
          </div>

          <form onSubmit={handleSubmit} className="auth-form">
            {mode === "register" && (
              <>
                <label htmlFor="organization">Organization name</label>
                <input
                  id="organization"
                  type="text"
                  placeholder="Your company or team"
                  value={organizationName}
                  onChange={(event) => setOrganizationName(event.target.value)}
                  minLength={2}
                  maxLength={255}
                  required
                />

                <label htmlFor="fullName">Full name</label>
                <input
                  id="fullName"
                  type="text"
                  placeholder="Your full name"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  minLength={2}
                  maxLength={255}
                  required
                />
              </>
            )}

            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />

            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="At least 8 characters"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={8}
              maxLength={128}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
            />

            {error && <div className="error-message" role="alert">{error}</div>}

            <button className="submit-button" type="submit" disabled={submitting}>
              {submitting
                ? "Please wait..."
                : mode === "login"
                  ? "Sign in to DocuMindAI"
                  : "Create workspace"}
              <span>→</span>
            </button>
          </form>

          <p className="security-note">
            <span>⌑</span> Secure authentication · Private organization workspace
          </p>
        </div>
      </section>
    </main>
  );
}
