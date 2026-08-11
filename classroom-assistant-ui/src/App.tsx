import { Navigate, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";
import AuthPage from "@/pages/AuthPage";
import WorkspaceView from "@/pages/WorkspaceView";
import DashboardPlaceholder from "@/pages/DashboardView";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Layout />}>
          <Route index element={<WorkspaceView />} />
          <Route path="dashboard" element={<DashboardPlaceholder />} />

          {/* The per-agent pages are now tabs inside the workspace */}
          <Route path="study" element={<Navigate to="/" replace />} />
          <Route path="quiz" element={<Navigate to="/" replace />} />
          <Route path="faq" element={<Navigate to="/" replace />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
