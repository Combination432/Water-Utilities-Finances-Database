import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export default function UtilityList() {
  const [utilities, setUtilities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stateFilter, setStateFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchUtilities();
  }, [stateFilter]);

  const fetchUtilities = async () => {
    try {
      const params = new URLSearchParams();
      if (stateFilter) params.append('state', stateFilter);

      const response = await fetch(`http://localhost:8000/api/utilities?${params}`);
      const data = await response.json();
      setUtilities(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching utilities:', error);
      setLoading(false);
    }
  };

  const filteredUtilities = utilities.filter(utility =>
    utility.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-gray-600">Loading utilities...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Water Utilities Database</h1>
        <div className="text-gray-600">{utilities.length} utilities found</div>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search by name
            </label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Enter utility name..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by state
            </label>
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All States</option>
              <option value="CA">California</option>
              <option value="TX">Texas</option>
              <option value="FL">Florida</option>
              <option value="NY">New York</option>
              <option value="PA">Pennsylvania</option>
              <option value="IL">Illinois</option>
              <option value="OH">Ohio</option>
              <option value="GA">Georgia</option>
              <option value="NC">North Carolina</option>
              <option value="MI">Michigan</option>
            </select>
          </div>
        </div>
      </div>

      {/* Utilities Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left py-3 px-4 font-semibold text-gray-700">Utility Name</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700">State</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700">Population</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700">Years of Data</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUtilities.length === 0 ? (
              <tr>
                <td colSpan="5" className="text-center py-8 text-gray-500">
                  No utilities found. {searchTerm && "Try a different search term."}
                </td>
              </tr>
            ) : (
              filteredUtilities.map((utility) => (
                <tr key={utility.id} className="border-t hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium">
                    {utility.name}
                  </td>
                  <td className="py-3 px-4">
                    <span className="inline-block px-2 py-1 text-xs font-semibold rounded bg-blue-100 text-blue-800">
                      {utility.state}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right text-gray-600">
                    {utility.population_served ? utility.population_served.toLocaleString() : 'N/A'}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className={`inline-block px-2 py-1 text-xs font-semibold rounded ${
                      utility.years_of_data >= 5 ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {utility.years_of_data} years
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <Link
                      to={`/utility/${utility.id}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      View Details →
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
