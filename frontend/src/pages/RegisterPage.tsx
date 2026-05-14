import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  register as registerApi,
  login as loginApi,
  getCurrentUser,
} from "../api/auth";
import { useAuthStore } from "../store/authStore";
import { getErrorMessage } from "../lib/errors";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(128),
});
type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register: registerField,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    setSubmitError(null);
    try {
      await registerApi(data.email, data.password);
      // Auto-login immediately after registration
      const tokens = await loginApi(data.email, data.password);
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await getCurrentUser();
      setUser(user);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      setSubmitError(getErrorMessage(err, "Registration failed. Try again."));
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 py-12">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        <h1 className="text-2xl font-semibold mb-1">Create your account</h1>
        <p className="text-gray-500 text-sm mb-6">
          Sign up to start training the recommendation agent on your
          preferences.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-gray-700 mb-1.5 block">
              Email
            </span>
            <input
              type="email"
              autoComplete="email"
              {...registerField("email")}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none"
            />
            {errors.email && (
              <span className="text-xs text-red-600 mt-1 block">
                {errors.email.message}
              </span>
            )}
          </label>

          <label className="block">
            <span className="text-sm font-medium text-gray-700 mb-1.5 block">
              Password
            </span>
            <input
              type="password"
              autoComplete="new-password"
              {...registerField("password")}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none"
            />
            {errors.password && (
              <span className="text-xs text-red-600 mt-1 block">
                {errors.password.message}
              </span>
            )}
          </label>

          {submitError && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {submitError}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition"
          >
            {isSubmitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="text-sm text-gray-500 mt-6 text-center">
          Already have an account?{" "}
          <Link
            to="/login"
            className="text-brand-600 hover:underline font-medium"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
