import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCurrentUser } from "../../api/auth";
import { useAuthStore } from "../../store/authStore";

interface RouteGuardProps {
  children: React.ReactNode;
}

export function RouteGuard({ children }: RouteGuardProps) {
  const location = useLocation();
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);

  // Refetch user on every guard mount — keeps `user` fresh, validates the token
  const { data, isLoading, isError } = useQuery({
    queryKey: ["currentUser"],
    queryFn: getCurrentUser,
    enabled: Boolean(accessToken),
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 min — refetch only when stale
  });

  useEffect(() => {
    if (data) setUser(data);
  }, [data, setUser]);

  if (!accessToken) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">Loading…</div>
      </div>
    );
  }

  if (isError) {
    // /me failed — token is invalid or backend is unreachable. Bounce to login.
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
