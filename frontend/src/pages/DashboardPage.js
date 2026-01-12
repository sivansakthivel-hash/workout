import { useState, useEffect } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, TrendingUp, Calendar, LogOut } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DashboardPage = ({ onLogout }) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [marking, setMarking] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get(`${API}/dashboard`);
      setDashboardData(response.data);
    } catch (error) {
      console.error("Failed to fetch dashboard data", error);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkWorkout = async () => {
    setMarking(true);
    setMessage("");

    try {
      const response = await axios.post(`${API}/mark-workout`);
      
      if (response.data.success) {
        setMessage("Workout marked successfully!");
        await fetchDashboardData();
      } else {
        setMessage(response.data.message);
      }
    } catch (error) {
      setMessage(error.response?.data?.detail || "Failed to mark workout");
    } finally {
      setMarking(false);
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${API}/logout`);
      onLogout();
    } catch (error) {
      console.error("Logout failed", error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100">
        <div className="text-blue-600 text-xl font-medium">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 px-4 py-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <img
              src="https://customer-assets.emergentagent.com/job_streakfit/artifacts/crhibsea_HashAgile.png"
              alt="HashAgile Logo"
              className="h-10"
              data-testid="dashboard-logo"
            />
            <div>
              <h1 className="text-2xl font-bold text-blue-900" data-testid="user-name">
                Hi, {dashboardData?.name}!
              </h1>
              <p className="text-sm text-blue-600" data-testid="today-date">
                {new Date(dashboardData?.today_date).toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={handleLogout}
            className="border-blue-300 text-blue-600 hover:bg-blue-50"
            data-testid="logout-button"
          >
            <LogOut className="h-5 w-5" />
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <Card className="shadow-lg border-blue-200" data-testid="streak-card">
            <CardHeader className="pb-3">
              <CardDescription className="text-blue-700 flex items-center gap-1">
                <TrendingUp className="h-4 w-4" />
                Current Streak
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-blue-900" data-testid="streak-count">
                {dashboardData?.current_streak}
              </div>
              <div className="text-sm text-blue-600 mt-1">days</div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-blue-200" data-testid="total-days-card">
            <CardHeader className="pb-3">
              <CardDescription className="text-blue-700 flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                Total Days
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-blue-900" data-testid="total-days-count">
                {dashboardData?.total_workout_days}
              </div>
              <div className="text-sm text-blue-600 mt-1">workouts</div>
            </CardContent>
          </Card>
        </div>

        {/* Mark Workout Card */}
        <Card className="shadow-xl border-blue-200 mb-6" data-testid="mark-workout-card">
          <CardHeader>
            <CardTitle className="text-blue-900">Today's Workout</CardTitle>
            <CardDescription>
              {dashboardData?.today_marked
                ? "You've completed your workout today!"
                : "Mark your workout once completed"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={handleMarkWorkout}
              disabled={marking || dashboardData?.today_marked}
              data-testid="mark-workout-button"
              className="w-full h-16 text-lg font-semibold bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {dashboardData?.today_marked ? (
                <>
                  <CheckCircle2 className="mr-2 h-6 w-6" />
                  Workout Completed
                </>
              ) : marking ? (
                "Marking..."
              ) : (
                <>
                  <CheckCircle2 className="mr-2 h-6 w-6" />
                  Mark Today as Done
                </>
              )}
            </Button>

            {message && (
              <div
                className={`text-center p-3 rounded-md ${
                  message.includes("success")
                    ? "bg-green-50 text-green-700"
                    : "bg-blue-50 text-blue-700"
                }`}
                data-testid="workout-message"
              >
                {message}
              </div>
            )}

            {dashboardData?.last_workout_date && (
              <div className="text-center text-sm text-blue-600" data-testid="last-workout-date">
                Last workout:{" "}
                {new Date(dashboardData.last_workout_date).toLocaleDateString()}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Workout History */}
        <Card className="shadow-lg border-blue-200" data-testid="workout-history-card">
          <CardHeader>
            <CardTitle className="text-blue-900">Recent Workouts</CardTitle>
            <CardDescription>Your workout history</CardDescription>
          </CardHeader>
          <CardContent>
            {dashboardData?.workout_history?.length > 0 ? (
              <div className="space-y-3">
                {dashboardData.workout_history.map((workout, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200"
                    data-testid={`workout-history-item-${index}`}
                  >
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                      <span className="font-medium text-blue-900">
                        {new Date(workout.date).toLocaleDateString('en-US', {
                          weekday: 'short',
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric'
                        })}
                      </span>
                    </div>
                    <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                      {workout.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-blue-600" data-testid="no-workouts-message">
                No workouts yet. Start your streak today!
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DashboardPage;
