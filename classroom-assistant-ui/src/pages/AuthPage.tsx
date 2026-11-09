import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import {
  describeAuthError,
  signUpWithEmail,
  signInWithEmail,
  signInWithGoogle,
} from "@/lib/auth";
import { useAuth } from "@/lib/AuthContext";
import { setupProfile } from "@/lib/api";
import AuthShell from "@/components/AuthShell";
import Button from "@/components/ui/Button";
import Notice from "@/components/ui/Notice";
import { Field, Select, TextInput } from "@/components/ui/form";

export default function AuthPage() {
  const { session, loading } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("student");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  // Already signed in, so there is nothing to do here.
  if (!loading && session) {
    return <Navigate to="/" replace />;
  }

  const signingUp = mode === "signup";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setNotice("");
    setSubmitting(true);

    try {
      if (signingUp) {
        const data = await signUpWithEmail(email, password, { fullName, role });

        // With email confirmation enabled, signUp returns a user but no
        // session — there is no token yet, so the profile cannot be created.
        // The user confirms, logs in, and the setup screen pre-fills the
        // name and role typed here.
        if (!data.session) {
          setNotice(
            "Account created. Check your email to confirm it, then log in.",
          );
          setMode("login");
          return;
        }

        try {
          await setupProfile(role, fullName, inviteCode);
        } catch {
          // The account exists and is signed in, so do not strand it here.
          // The app notices there is no profile and shows the setup screen,
          // pre-filled with what was typed, so the student can try again
          // (a wrong invite code is the usual reason).
        }
      } else {
        await signInWithEmail(email, password);
      }

      navigate("/");
    } catch (err) {
      setError(describeAuthError(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogle() {
    setError("");

    try {
      await signInWithGoogle();
    } catch (err) {
      setError(describeAuthError(err));
    }
  }

  function switchMode() {
    setMode(signingUp ? "login" : "signup");
    setError("");
    setNotice("");
  }

  return (
    <AuthShell
      title={signingUp ? "Create your account" : "Log in"}
      description={
        signingUp
          ? "Students sign up here. Teachers and TAs need an invite code."
          : "Welcome back. Pick up where you left off."
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Email">
          {(id) => (
            <TextInput
              id={id}
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          )}
        </Field>

        <Field
          label="Password"
          hint={signingUp ? "At least 6 characters." : undefined}
        >
          {(id) => (
            <TextInput
              id={id}
              type="password"
              autoComplete={signingUp ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={signingUp ? 6 : undefined}
              required
            />
          )}
        </Field>

        {signingUp && (
          <>
            <Field label="Full name">
              {(id) => (
                <TextInput
                  id={id}
                  autoComplete="name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  maxLength={100}
                  required
                />
              )}
            </Field>

            <Field label="I am a">
              {(id) => (
                <Select
                  id={id}
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                >
                  <option value="student">Student</option>
                  <option value="teacher">Teacher</option>
                  <option value="ta">TA</option>
                </Select>
              )}
            </Field>

            {role !== "student" && (
              <Field
                label="Invite code"
                hint="Your instructor can give you this code."
              >
                {(id) => (
                  <TextInput
                    id={id}
                    value={inviteCode}
                    onChange={(e) => setInviteCode(e.target.value)}
                    required
                  />
                )}
              </Field>
            )}
          </>
        )}

        {error && <Notice tone="error">{error}</Notice>}
        {notice && <Notice tone="ok">{notice}</Notice>}

        <Button
          type="submit"
          variant="primary"
          loading={submitting}
          className="w-full"
        >
          {signingUp ? "Create account" : "Log in"}
        </Button>
      </form>

      <div className="my-5 flex items-center gap-3 text-meta text-ink-3">
        <span className="h-px flex-1 bg-rule" />
        or
        <span className="h-px flex-1 bg-rule" />
      </div>

      <Button onClick={handleGoogle} className="w-full">
        Continue with Google
      </Button>

      <p className="mt-6 text-ui text-ink-2">
        {signingUp ? "Already have an account?" : "New here?"}{" "}
        <button
          type="button"
          onClick={switchMode}
          className="font-medium text-blue underline underline-offset-2"
        >
          {signingUp ? "Log in" : "Create an account"}
        </button>
      </p>
    </AuthShell>
  );
}
