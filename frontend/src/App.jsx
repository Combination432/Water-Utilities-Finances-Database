import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import UtilityList from './components/UtilityList';
import UtilityDetail from './components/UtilityDetail';
import ForecastView from './components/ForecastView';
import './App.css';

function App() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    // Fetch basic stats
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/stats');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-blue-600 text-white shadow-lg">
          <div className="container mx-auto px-4 py-4">
            <div className="flex justify-between items-center">
              <div>
                <h1 className="text-2xl font-bold">Water Utilities Financial Analysis</h1>
                <p className="text-blue-100 text-sm">
                  {stats ? `${stats.utilities} utilities • ${stats.reports} reports • ${stats.line_items.toLocaleString()} line items` : 'Loading...'}
                </p>
              </div>
              <nav className="flex gap-4">
                <Link to="/" className="px-4 py-2 bg-blue-500 rounded hover:bg-blue-700 transition">
                  Dashboard
                </Link>
                <Link to="/utilities" className="px-4 py-2 bg-blue-500 rounded hover:bg-blue-700 transition">
                  Utilities
                </Link>
              </nav>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/utilities" element={<UtilityList />} />
            <Route path="/utility/:id" element={<UtilityDetail />} />
            <Route path="/forecast/:id" element={<ForecastView />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="bg-gray-800 text-white mt-12">
          <div className="container mx-auto px-4 py-6 text-center">
            <p>Water Utilities Financial Analysis Platform • Zero-Cost Open Source</p>
            <p className="text-gray-400 text-sm mt-2">
              Data from EMMA (Municipal Securities Rulemaking Board) • Free Public Data
            </p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
