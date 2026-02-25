// import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { ProjectDetail } from './pages/projects/ProjectDetail';
import { NewProject } from './pages/projects/NewProject';
import { Deployments } from './pages/Deployments';
import { Monitoring } from './pages/Monitoring';
import { Settings } from './pages/Settings';
import { LogsPage } from './pages/Logs';
import { DragBuild } from './pages/DragBuild';
import { CostAnalysis } from './pages/CostAnalysis';

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/projects/new" element={<NewProject />} />
              <Route path="/projects/:id" element={<ProjectDetail />} />
              <Route path="/deployments" element={<Deployments />} />
              <Route path="/monitoring" element={<Monitoring />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/logs" element={<LogsPage />} />
              <Route path="/drag-build" element={<DragBuild />} />
              <Route path="/cost-analysis" element={<CostAnalysis />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
