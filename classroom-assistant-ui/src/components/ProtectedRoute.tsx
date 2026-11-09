import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/lib/AuthContext";
import { ProfileProvider, useProfile } from "@/lib/ProfileContext";
import { signOut } from "@/lib/auth";
import ProfileSetupPage from "@/pages/ProfileSetupPage";
import AuthShell from "@/components/AuthShell";
import Button from "@/components/ui/Button";
import Notice from "@/components/ui/Notice";
import Skeleton from "@/components/ui/Skeleton";

export default function ProtectedRoute() {
  const { session, loading } = useAuth();

  if (loading) {
    return <Splash />;
  }

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  return (
    <ProfileProvider>
      <ProfileGate />
    </ProfileProvider>
  );
}

/** What shows while the session or profile is loading. */
function Splash() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper">
      <div className="w-64 space-y-3" role="status" aria-label="Loading">
        <Skeleton className="h-6 w-40" />
        <Skeleton />
        <Skeleton className="w-3/4" />
      </div>
    </div>
  );
}

/**
 * A signed-in account with no profile row cannot use the app: the backend has
 * no role for it. That happens when sign-up worked but the profile step did
 * not, or when email confirmation delayed the first login. Instead of
 * leaving the account stranded, ask for the missing details here.
 */
function ProfileGate() {
  const { profile, loading, error, refresh } = useProfile();

  if (loading) {
    return <Splash />;
  }

  if (error) {
    return (
      <AuthShell title="Could not load your account">
        <Notice tone="error">{error}</Notice>
        <div className="mt-4 flex gap-2">
          <Button variant="primary" onClick={refresh} className="flex-1">
            Try again
          </Button>
          <Button onClick={() => signOut()} className="flex-1">
            Sign out
          </Button>
        </div>
      </AuthShell>
    );
  }

  if (!profile?.has_profile) {
    return <ProfileSetupPage />;
  }

  return <Outlet />;
}
