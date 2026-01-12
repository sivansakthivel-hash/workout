import { useState } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const LoginPage = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [name, setName] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    // Validate inputs
    if (!name.trim()) {
      setError("Name is required");
      setLoading(false);
      return;
    }

    if (pin.length !== 4 || !/^\d{4}$/.test(pin)) {
      setError("PIN must be exactly 4 digits");
      setLoading(false);
      return;
    }

    try {
      const endpoint = isLogin ? "/login" : "/register";
      const response = await axios.post(`${API}${endpoint}`, { name, pin });

      if (response.data.success) {
        onAuthSuccess();
      }
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-blue-50 px-4 py-8">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <img
            src="https://customer-assets.emergentagent.com/job_streakfit/artifacts/crhibsea_HashAgile.png"
            alt="HashAgile Logo"
            className="h-12 mx-auto mb-4"
            data-testid="logo-image"
          />
          <h1 className="text-3xl font-bold text-blue-900 mb-2" data-testid="app-title">
            Workout Streak Tracker
          </h1>
          <p className="text-blue-600" data-testid="app-subtitle">
            Track your daily progress
          </p>
        </div>

        <Card className="shadow-xl border-blue-200" data-testid="auth-card">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-2xl text-center text-blue-900" data-testid="card-title">
              {isLogin ? "Welcome Back" : "Create Account"}
            </CardTitle>
            <CardDescription className="text-center" data-testid="card-description">
              {isLogin
                ? "Login to continue your streak"
                : "Start your fitness journey today"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-blue-900">
                  Name
                </Label>
                <Input
                  id="name"
                  data-testid="name-input"
                  type="text"
                  placeholder="Enter your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="h-12 text-lg border-blue-300 focus:border-blue-500"
                  disabled={loading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="pin" className="text-blue-900">
                  4-Digit PIN
                </Label>
                <Input
                  id="pin"
                  data-testid="pin-input"
                  type="password"
                  placeholder="Enter 4-digit PIN"
                  value={pin}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, "").slice(0, 4);
                    setPin(value);
                  }}
                  maxLength={4}
                  className="h-12 text-lg text-center tracking-widest border-blue-300 focus:border-blue-500"
                  disabled={loading}
                />
              </div>

              {error && (
                <div
                  className="text-red-600 text-sm text-center bg-red-50 p-3 rounded-md"
                  data-testid="error-message"
                >
                  {error}
                </div>
              )}

              <Button
                type="submit"
                data-testid="submit-button"
                className="w-full h-14 text-lg font-semibold bg-blue-600 hover:bg-blue-700 transition-colors"
                disabled={loading}
              >
                {loading ? "Processing..." : isLogin ? "Login" : "Register"}
              </Button>

              <div className="text-center pt-2">
                <button
                  type="button"
                  data-testid="toggle-auth-button"
                  onClick={() => {
                    setIsLogin(!isLogin);
                    setError("");
                  }}
                  className="text-blue-600 hover:text-blue-800 font-medium transition-colors"
                  disabled={loading}
                >
                  {isLogin
                    ? "Don't have an account? Register"
                    : "Already have an account? Login"}
                </button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default LoginPage;
