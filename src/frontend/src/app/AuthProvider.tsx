import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { advanceSessionGeneration, api, ApiError, errorMessage, sessionExpiredEvent } from "../shared/api/client";
import type { User } from "../shared/api/types";
type AuthState = {
  status: "loading";
  user: null;
} | {
  status: "anonymous";
  user: null;
} | {
  status: "authenticated";
  user: User;
} | {
  status: "error";
  user: null;
  message: string;
};
type AuthContextValue = AuthState & {
  setUser: (user: User | null) => void;
  retry: () => void;
};
const AuthContext = createContext<AuthContextValue | null>(null);
export function AuthProvider({ children }: {
  children: ReactNode;
}) {
  const [state, setState] = useState<AuthState>({ status: "loading", user: null });
  const restore = useRef<AbortController | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    function expired() {
      advanceSessionGeneration();
      restore.current?.abort();
      setState({ status: "anonymous", user: null });
    }
    window.addEventListener(sessionExpiredEvent, expired);
    return () => window.removeEventListener(sessionExpiredEvent, expired);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    restore.current = controller;
    setState({ status: "loading", user: null });
    api<User>("/auth/me", { signal: controller.signal })
      .then((user) => {
        if (!controller.signal.aborted)
          setState({ status: "authenticated", user });
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted)
          return;
        setState(reason instanceof ApiError && reason.status === 401
          ? { status: "anonymous", user: null }
          : { status: "error", user: null, message: errorMessage(reason) });
      });
    return () => controller.abort();
  }, [attempt]);
  const setUser = (user: User | null) => {
    advanceSessionGeneration();
    restore.current?.abort();
    setState(user ? { status: "authenticated", user } : { status: "anonymous", user: null });
  };
  return <AuthContext.Provider value={{ ...state, setUser, retry: () => setAttempt((value) => value + 1) }}>
    {children}
  </AuthContext.Provider>;
}
export function useApp(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context)
    throw new Error("Authentication context is unavailable");
  return context;
}
