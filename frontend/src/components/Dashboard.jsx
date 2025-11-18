import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function Dashboard() {
  const [topUtilities, setTopUtilities] = useState([]);
  const [revenueData, setRevenueData] = useState([]);
  const [stateDistribution, setStateDistribution] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // Fetch top utilities by revenue
      const topResponse = await fetch('http://localhost:8000/api/utilities/top?limit=10');
      const topData = await topResponse.json();
      setTopUtilities(topData);

      // Fetch aggregate revenue trend
      const trendResponse = await fetch('http://localhost:8000/api/analytics/revenue-trend');
      const trendData = await trendResponse.json();
      setRevenueData(trendData);

      // Fetch state distribution
      const stateResponse = await fetch('http://localhost:8000/api/analytics/by-state');
      const stateData = await stateResponse.json();
      setStateDistribution(stateData);

      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-gray-600">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-gray-500 text-sm font-medium">Total Utilities</div>
          <div className="text-3xl font-bold text-blue-600">{topUtilities.length > 0 ? '700+' : '0'}</div>
          <div className="text-xs text-gray-400 mt-1">From EMMA database</div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-gray-500 text-sm font-medium">Years of Data</div>
          <div className="text-3xl font-bold text-green-600">10</div>
          <div className="text-xs text-gray-400 mt-1">Historical financial data</div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-gray-500 text-sm font-medium">Total Reports</div>
          <div className="text-3xl font-bold text-purple-600">8,000+</div>
          <div className="text-xs text-gray-400 mt-1">CAFRs analyzed</div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-gray-500 text-sm font-medium">Data Points</div>
          <div className="text-3xl font-bold text-orange-600">25,000+</div>
          <div className="text-xs text-gray-400 mt-1">Line items extracted</div>
        </div>
      </div>

      {/* Top Utilities */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Top 10 Utilities by Revenue (FY2023)</h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3 px-4">Utility</th>
                <th className="text-left py-3 px-4">State</th>
                <th className="text-right py-3 px-4">Revenue</th>
                <th className="text-right py-3 px-4">Operating Margin</th>
                <th className="text-right py-3 px-4">Debt-to-Assets</th>
                <th className="text-right py-3 px-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {topUtilities.map((utility, idx) => (
                <tr key={idx} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium">{utility.name}</td>
                  <td className="py-3 px-4">{utility.state}</td>
                  <td className="py-3 px-4 text-right">${(utility.revenue / 1000000).toFixed(0)}M</td>
                  <td className="py-3 px-4 text-right">{utility.operating_margin.toFixed(1)}%</td>
                  <td className="py-3 px-4 text-right">{utility.debt_ratio.toFixed(1)}%</td>
                  <td className="py-3 px-4 text-right">
                    <Link
                      to={`/utility/${utility.id}`}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Revenue Trend Chart */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Aggregate Revenue Trend</h2>

        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={revenueData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="year" />
            <YAxis />
            <Tooltip formatter={(value) => `$${(value / 1000000000).toFixed(2)}B`} />
            <Legend />
            <Line type="monotone" dataKey="total_revenue" stroke="#2563eb" name="Total Revenue" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* State Distribution */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Utilities by State (Top 10)</h2>

        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={stateDistribution}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="state" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" fill="#10b981" name="Number of Utilities" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
