import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useAuth } from "./AuthContext";
import { getMe, type Profile } from "./api";

interface ProfileContextType {
  /** Null until loaded, and for an account that has not finished setup. */
  profile: Profile | null;
  loading: boolean;
  error: string;
  refresh: () => void;
  /** Use a profile you already have, e.g. right after creating it. */
  applyProfile: (profile: Profile) => void;
}

const ProfileContext = createContext<ProfileContextType>({
  profile: null,
  loading: true,
  error: "",
  refresh: () => {},
  applyProfile: () => {},
});

interface Loaded {
  userId: string;
  profile: Profile | null;
  error: string;
}

export function ProfileProvider({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const userId = session?.user.id ?? null;

  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    if (!userId) return;

    let cancelled = false;

    getMe()
      .then((profile) => {
        if (!cancelled) setLoaded({ userId, profile, error: "" });
      })
      .catch((err) => {
        if (cancelled) return;
        setLoaded({
          userId,
          profile: null,
          error: err instanceof Error ? err.message : "Could not load your profile.",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [userId, refreshToken]);

  const refresh = useCallback(() => setRefreshToken((t) => t + 1), []);

  const applyProfile = useCallback(
    (profile: Profile) => {
      if (userId) setLoaded({ userId, profile, error: "" });
    },
    [userId],
  );

  // Derived rather than stored, so the effect never has to set a flag just to
  // say "loading". A result for a different user (after sign-out and back in)
  // does not count.
  const current = loaded && loaded.userId === userId ? loaded : null;

  return (
    <ProfileContext.Provider
      value={{
        profile: current?.profile ?? null,
        loading: userId !== null && current === null,
        error: current?.error ?? "",
        refresh,
        applyProfile,
      }}
    >
      {children}
    </ProfileContext.Provider>
  );
}

// Same arrangement as AuthContext: the hook lives beside its provider.
// eslint-disable-next-line react-refresh/only-export-components
export function useProfile() {
  return useContext(ProfileContext);
}
