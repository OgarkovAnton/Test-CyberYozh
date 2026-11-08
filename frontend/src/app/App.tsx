import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "../shared/auth/AuthContext";
import { LoginPage } from "../features/auth/LoginPage";
import { RegisterPage } from "../features/auth/RegisterPage";
import { TaskListPage } from "../features/tasks/TaskListPage";
import { TaskDetailPage } from "../features/tasks/TaskDetailPage";
import { AppLayout } from "./AppLayout";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="shell muted">Loading…</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <AppLayout />
          </Protected>
        }
      >
        <Route index element={<TaskListPage />} />
        <Route path="tasks/:taskId" element={<TaskDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
