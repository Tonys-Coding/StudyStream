import { useState } from "react";
import { useAuth } from "@/lib/AuthContext";
import { useProfile } from "@/lib/ProfileContext";
import { setupProfile, getMe } from "@/lib/api";
import { signOut } from "@/lib/auth";
import AuthShell from "@/components/AuthShell";
import Button from "@/components/ui/Button";
import Notice from "@/components/ui/Notice";
import { Field, Select, TextInput } from "@/components/ui/form";

/** Shown to a signed-in account that has no profile yet. */
export default function ProfileSetupPage() {
  const { session } = useAuth();
  const { applyProfile } = useProfile();

  // Whatever was typed at sign-up is kept on the account.
  const meta = session?.user.user_metadata ?? {};

  const [fullName, setFullName] = useState<string>(
    typeof meta.full_name === "string" ? meta.full_name : "",
  );
  const [role, setRole] = useState<string>(
    typeof meta.role === "string" ? meta.role : "student",
  );
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await setupProfile(role, fullName, inviteCode);
      applyProfile(await getMe());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell
      title="Finish setting up"
      description={`Signed in as ${session?.user.email}. Tell us who you are to continue.`}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
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

        {error && <Notice tone="error">{error}</Notice>}

        <Button
          type="submit"
          variant="primary"
          loading={submitting}
          className="w-full"
        >
          Continue
        </Button>
      </form>

      <Button variant="ghost" onClick={() => signOut()} className="mt-3 w-full">
        Sign out
      </Button>
    </AuthShell>
  );
}
