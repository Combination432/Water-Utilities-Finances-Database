import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function UtilityDetail() {
  const { id } = useParams();
  const [utility, setUtility] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchUtilityDetail();
  }, [id]);

  const fetchUtilityDetail = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/utility/${id}`);
      const data = await response.json();
      setUtility(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching utility details:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-gray-600">Loading utility details...</div>
      </div>
    );
  }

  if (!utility) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-gray-900">Utility not found</h2>
        <Link to="/utilities" className="text-blue-600 hover:text-blue-800 mt-4 inline-block">
          ← Back to utilities list
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-lg shadow">
        <Link to="/utilities" className="text-blue-600 hover:text-blue-800 mb-4 inline-block">
          ← Back to utilities
        </Link>

        <h1 className="text-3xl font-bold mt-2">{utility.utility_name}</h1>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
          <div>
            <div className="text-sm text-gray-500">State</div>
            <div className="text-lg font-semibold">{utility.state}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Type</div>
            <div className="text-lg font-semibold">{utility.utility_type || 'N/A'}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Population Served</div>
            <div className="text-lg font-semibold">
              {utility.population_served ? utility.population_served.toLocaleString() : 'N/A'}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Years of Data</div>
            <div className="text-lg font-semibold">{utility.financials?.length || 0} years</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b">
          <nav className="flex space-x-8 px-6">
            {['overview', 'financials', 'trends'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Latest Year Summary */}
              {utility.financials && utility.financials.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-600">Total Revenue (FY{utility.financials[0].fiscal_year})</div>
                    <div className="text-2xl font-bold text-blue-600">
                      ${(utility.financials[0].total_revenue / 1000000).toFixed(1)}M
                    </div>
                  </div>

                  <div className="bg-green-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-600">Total Expenses</div>
                    <div className="text-2xl font-bold text-green-600">
                      ${(utility.financials[0].total_expenses / 1000000).toFixed(1)}M
                    </div>
                  </div>

                  <div className="bg-purple-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-600">Operating Margin</div>
                    <div className="text-2xl font-bold text-purple-600">
                      {utility.financials[0].operating_margin.toFixed(1)}%
                    </div>
                  </div>

                  <div className="bg-orange-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-600">Debt-to-Assets</div>
                    <div className="text-2xl font-bold text-orange-600">
                      {utility.financials[0].debt_to_assets.toFixed(1)}%
                    </div>
                  </div>
                </div>
              )}

              {/* Growth Rates */}
              {utility.growth_rates && (
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-semibold mb-3">Growth Rates (5-Year CAGR)</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-gray-600">Revenue CAGR</div>
                      <div className="text-xl font-bold text-blue-600">
                        {utility.growth_rates.revenue_cagr.toFixed(2)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Expense CAGR</div>
                      <div className="text-xl font-bold text-red-600">
                        {utility.growth_rates.expense_cagr.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'financials' && (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4">Fiscal Year</th>
                    <th className="text-right py-3 px-4">Revenue</th>
                    <th className="text-right py-3 px-4">Expenses</th>
                    <th className="text-right py-3 px-4">Assets</th>
                    <th className="text-right py-3 px-4">Liabilities</th>
                    <th className="text-right py-3 px-4">Op. Margin</th>
                  </tr>
                </thead>
                <tbody>
                  {utility.financials?.map((year) => (
                    <tr key={year.fiscal_year} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4 font-medium">{year.fiscal_year}</td>
                      <td className="py-3 px-4 text-right">${(year.total_revenue / 1000000).toFixed(2)}M</td>
                      <td className="py-3 px-4 text-right">${(year.total_expenses / 1000000).toFixed(2)}M</td>
                      <td className="py-3 px-4 text-right">${(year.total_assets / 1000000).toFixed(2)}M</td>
                      <td className="py-3 px-4 text-right">${(year.total_liabilities / 1000000).toFixed(2)}M</td>
                      <td className="py-3 px-4 text-right">{year.operating_margin.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'trends' && (
            <div className="space-y-6">
              {/* Revenue & Expenses Chart */}
              <div>
                <h3 className="font-semibold mb-4">Revenue vs Expenses</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={utility.financials}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="fiscal_year" />
                    <YAxis />
                    <Tooltip formatter={(value) => `$${(value / 1000000).toFixed(1)}M`} />
                    <Legend />
                    <Line type="monotone" dataKey="total_revenue" stroke="#2563eb" name="Revenue" strokeWidth={2} />
                    <Line type="monotone" dataKey="total_expenses" stroke="#ef4444" name="Expenses" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Operating Margin Chart */}
              <div>
                <h3 className="font-semibold mb-4">Operating Margin Trend</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={utility.financials}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="fiscal_year" />
                    <YAxis />
                    <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
                    <Legend />
                    <Bar dataKey="operating_margin" fill="#10b981" name="Operating Margin %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
