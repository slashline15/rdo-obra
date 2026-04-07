import {
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { apiGet, apiLogin } from "./api";
import { AuthContext } from "./auth-context";

interface User {
  id: number;
  nome: string;
  telefone: string;
  role: string;
  obra_id: number | null;
  email: string | null;
  nivel_acesso: number;
  pode_aprovar_diario: boolean;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    try {
      const u = await apiGet<User>("/auth/me");
      setUser(u);
    } catch {
      setUser(null);
      localStorage.removeItem("token");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (localStorage.getItem("token")) {
      fetchMe();
    } else {
      setLoading(false);
    }
  }, [fetchMe]);

  const login = async (username: string, password: string) => {
    await apiLogin(username, password);
    await fetchMe();
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  const level = user?.nivel_acesso ?? 99;
  const canApproveDiario = !!user?.pode_aprovar_diario || level === 1;
  const isAdmin = level === 1;
  const isEngenheiro = level <= 2;

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAdmin, isEngenheiro, canApproveDiario }}>
      {children}
    </AuthContext.Provider>
  );
}
