import { supabase } from "./supabase";

export async function signUpWithEmail(
  email: string,
  password: string,
  details: { fullName: string; role: string },
) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    // Kept on the account, so if email confirmation delays the first login
    // the setup screen can still be pre-filled with what was typed here.
    options: { data: { full_name: details.fullName, role: details.role } },
  });
  if (error) throw error;
  return data;
}

export async function signInWithEmail(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });
  if (error) throw error;
  return data;
}

export async function signInWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.origin },
  });
  if (error) throw error;
  return data;
}

export async function signOut() {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

export async function getSession() {
  const { data } = await supabase.auth.getSession();
  return data.session;
}

/**
 * Turns a sign-in failure into something a student can act on.
 *
 * When the browser cannot reach Supabase at all, fetch() rejects with a bare
 * "Load failed" (Safari) or "Failed to fetch" (Chrome), which says nothing
 * about what to do.
 */
export function describeAuthError(err: unknown): string {
  const message = err instanceof Error ? err.message : "";

  if (/load failed|failed to fetch|networkerror|network request failed/i.test(message)) {
    return "Could not reach the sign-in service. Check your connection and try again.";
  }

  return message || "Something went wrong";
}
