import React, { createContext, useContext, useEffect, useState } from "react";
import { apiClient, setAuthToken } from "../api/client";
import { UserRole, UserSession } from "../types";

interface AuthContextType {
  user: UserSession | null;
  loading: boolean;
  error: string | null;
  loginDemo: (role: UserRole) => Promise<void>;
  logout: () => void;
  hasRole: (role: UserRole) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSession | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Attempt automatic local demo initialization if demo mode is enabled
    async function initAuth() {
      try {
        const config = await apiClient.getOIDCConfig();
        if (config.demo_mode) {
          const res = await apiClient.loginDemo("operator", "demo-operator");
          setAuthToken(res.access_token);
          const me = await apiClient.getMe();
          setUser(me);
        }
      } catch (err: any) {
        // Unauthenticated initial state
        setError(null);
      } finally {
        setLoading(false);
      }
    }
    initAuth();
  }, []);

  const loginDemo = async (role: UserRole) => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.loginDemo(role, `demo-${role}`);
      setAuthToken(res.access_token);
      const me = await apiClient.getMe();
      setUser(me);
    } catch (err: any) {
      setError(err.message || "Failed to login via demo mode");
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setAuthToken(null);
    setUser(null);
  };

  const hasRole = (minRole: UserRole): boolean => {
    if (!user) return false;
    const levels: Record<UserRole, number> = {
      viewer: 1,
      operator: 2,
      admin: 3,
    };
    return levels[user.effective_role] >= levels[minRole];
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        loginDemo,
        logout,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
