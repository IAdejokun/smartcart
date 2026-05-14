import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { ShoppingCartIcon, ChartBarIcon } from "@heroicons/react/24/outline";
import { useAuthStore } from "../../store/authStore";
import { useCart } from "../../hooks/useCart";
import { CartDrawer } from "../cart/CartDrawer";
import { useState } from "react";
import { cn } from "../../lib/cn";

export function Shell() {
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const { data: cart } = useCart();
  const navigate = useNavigate();
  const [cartOpen, setCartOpen] = useState(false);

  const itemCount = cart?.item_count ?? 0;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-30 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-4">
          <Link
            to="/"
            className="flex items-center gap-2 font-semibold text-lg"
          >
            <span className="w-8 h-8 rounded-lg bg-brand-600 text-white grid place-items-center">
              S
            </span>
            <span className="hidden sm:inline">SmartCart</span>
            <span className="hidden sm:inline text-xs px-1.5 py-0.5 bg-accent-500/10 text-accent-600 rounded font-medium">
              AI
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            <NavItem to="/shop">Shop</NavItem>
            {user && (
              <NavItem to="/dashboard">
                <span className="flex items-center gap-1.5">
                  <ChartBarIcon className="w-4 h-4" />
                  Dashboard
                </span>
              </NavItem>
            )}
          </nav>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCartOpen(true)}
              className="relative p-2 rounded-lg hover:bg-gray-100 transition"
              aria-label={`Cart (${itemCount} items)`}
            >
              <ShoppingCartIcon className="w-5 h-5" />
              {itemCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 bg-accent-500 text-white text-xs font-medium rounded-full w-5 h-5 grid place-items-center">
                  {itemCount}
                </span>
              )}
            </button>

            {user ? (
              <button
                onClick={() => {
                  clearAuth();
                  navigate("/");
                }}
                className="text-sm text-gray-600 hover:text-gray-900 px-3 py-2"
              >
                Sign out
              </button>
            ) : (
              <Link
                to="/login"
                className="text-sm bg-brand-600 hover:bg-brand-700 text-white px-3 py-2 rounded-lg font-medium transition"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <CartDrawer open={cartOpen} onClose={() => setCartOpen(false)} />
    </div>
  );
}

function NavItem({
  to,
  end,
  children,
}: {
  to: string;
  end?: boolean;
  children: React.ReactNode;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          "px-3 py-2 rounded-lg text-sm font-medium transition",
          isActive
            ? "bg-brand-50 text-brand-700"
            : "text-gray-600 hover:bg-gray-100",
        )
      }
    >
      {children}
    </NavLink>
  );
}
