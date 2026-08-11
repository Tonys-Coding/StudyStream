import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { signUpWithEmail, signInWithEmail, signInWithGoogle } from "@/lib/auth";
import { setupProfile } from "@/lib/api";

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("student");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setNotice("");
    setSubmitting(true);

    try {
      if (mode === "signup") {
        const data = await signUpWithEmail(email, password);

        // With email confirmation enabled, signUp returns a user but no
        // session — there is no token yet, so the profile cannot be created.
        // The user has to confirm and log in first.
        if (!data.session) {
          setNotice(
            "Account created. Check your email to confirm it, then log in.",
          );
          setMode("login");
          return;
        }

        await setupProfile(role, fullName);
      } else {
        await signInWithEmail(email, password);
      }

      navigate("/study");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-24 p-6 bg-surface border border-border rounded-xl">
      <h1 className="font-display text-xl font-semibold text-primary mb-4">
        {mode === "login" ? "Log in" : "Sign up"}
      </h1>

      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="email"
          placeholder="Email"
          className="w-full border border-border rounded-lg px-3 py-2"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          className="w-full border border-border rounded-lg px-3 py-2"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {mode === "signup" && (
          <>
            <input
              type="text"
              placeholder="Full name"
              className="w-full border border-border rounded-lg px-3 py-2"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
            <select
              className="w-full border border-border rounded-lg px-3 py-2"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
              <option value="ta">TA</option>
            </select>
          </>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}
        {notice && <p className="text-sm text-on-surface-variant">{notice}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-primary text-white rounded-full py-2.5 font-medium disabled:opacity-50"
        >
          {submitting ? "Working…" : mode === "login" ? "Log in" : "Sign up"}
        </button>
      </form>

      <button
        onClick={() => signInWithGoogle()}
        className="w-full mt-3 border border-border rounded-full py-2.5 font-medium"
      >
        Continue with Google
      </button>

      <p className="text-sm text-center mt-4">
        {mode === "login" ? "Need an account?" : "Already have one?"}{" "}
        <button
          type="button"
          className="text-primary font-medium"
          onClick={() => {
            setMode(mode === "login" ? "signup" : "login");
            setError("");
            setNotice("");
          }}
        >
          {mode === "login" ? "Sign up" : "Log in"}
        </button>
      </p>
    </div>
  );
}
