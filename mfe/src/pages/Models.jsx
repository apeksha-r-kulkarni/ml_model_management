import React, { useState, useEffect, useMemo } from 'react';
import { modelService } from '../services/modelService';
import ModelCard from '../components/models/ModelCard';

export default function Models({ onAddNewVersion, onRegisterNew }) {
  const [allModels, setAllModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Search & Filter & Sort state
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('All');
  const [selectedDeploymentPoint, setSelectedDeploymentPoint] = useState('All');
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // Edit/Delete modal state
  const [editingModel, setEditingModel] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updateLoading, setUpdateLoading] = useState(false);
  const [updateError, setUpdateError] = useState(null);
  
  const [deletingModel, setDeletingModel] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const fetchModels = async () => {
    setLoading(true);
    try {
      const data = await modelService.listModels();
      setAllModels(data.models || []);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to list models');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  // Group raw rows into logical model identities
  const groupedIdentities = useMemo(() => {
    const map = {};
    allModels.forEach(m => {
      map[m.name] = m;
    });
    return map;
  }, [allModels]);

  // Available deployment points for filter dropdown
  const allDeploymentPoints = useMemo(() => {
    const set = new Set();
    allModels.forEach(m => {
      (m.all_versions || []).forEach(v => {
        if (Array.isArray(v.deployment_points)) {
          v.deployment_points.forEach(dp => set.add(dp));
        }
      });
    });
    return Array.from(set).sort();
  }, [allModels]);

  // Filtered & Sorted identities
  const filteredIdentities = useMemo(() => {
    let resultNames = Object.keys(groupedIdentities);

    // Search by model identity name
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase().trim();
      resultNames = resultNames.filter(name => name.toLowerCase().includes(term));
    }

    // Filter by Model Type
    if (selectedType !== 'All') {
      resultNames = resultNames.filter(name => {
        const model = groupedIdentities[name];
        return model.model_type === selectedType;
      });
    }

    // Filter by Deployment Point
    if (selectedDeploymentPoint !== 'All') {
      resultNames = resultNames.filter(name => {
        const latest = (groupedIdentities[name].all_versions || [])[0] || {};
        return latest.deployment_points && latest.deployment_points.includes(selectedDeploymentPoint);
      });
    }

    // Sort
    resultNames.sort((aName, bName) => {
      const aLatest = (groupedIdentities[aName].all_versions || [])[0] || {};
      const bLatest = (groupedIdentities[bName].all_versions || [])[0] || {};

      let valA, valB;
      if (sortBy === 'name') {
        valA = aName.toLowerCase();
        valB = bName.toLowerCase();
      } else if (sortBy === 'version') {
        valA = aLatest.version;
        valB = bLatest.version;
      } else if (sortBy === 'accuracy') {
        valA = aLatest.accuracy || 0;
        valB = bLatest.accuracy || 0;
      } else if (sortBy === 'priority') {
        valA = aLatest.priority ?? -1;
        valB = bLatest.priority ?? -1;
      }

      if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return resultNames;
  }, [groupedIdentities, searchTerm, selectedType, selectedDeploymentPoint, sortBy, sortOrder]);

  // Pagination calculations
  const totalPages = Math.ceil(filteredIdentities.length / itemsPerPage) || 1;
  const paginatedNames = useMemo(() => {
    const startIdx = (currentPage - 1) * itemsPerPage;
    return filteredIdentities.slice(startIdx, startIdx + itemsPerPage);
  }, [filteredIdentities, currentPage, itemsPerPage]);

  const handleOpenEdit = (m) => {
    setEditingModel(m);
    setEditForm({
      id: m.id,
      purpose: m.purpose || '',
      architecture: m.architecture || '',
      language: m.language || '',
      environment: m.environment || '',
      accuracy: m.accuracy || 0.0,
      priority: (m.priority !== null && m.priority !== undefined) ? m.priority : '',
      is_deployable: m.is_deployable || false,
      remarks: m.remarks || ''
    });
    setUpdateError(null);
  };

  const submitEdit = async (e) => {
    e.preventDefault();
    setUpdateLoading(true);
    const payload = {
      id: editForm.id,
      purpose: editForm.purpose,
      architecture: editForm.architecture,
      language: editForm.language,
      environment: editForm.environment,
      accuracy: parseFloat(editForm.accuracy) || 0.0,
      priority: editForm.priority !== '' ? parseInt(editForm.priority, 10) : null,
      is_deployable: editForm.is_deployable,
      remarks: editForm.remarks
    };
    try {
      await modelService.updateModel(payload);
      setEditingModel(null);
      fetchModels();
    } catch (err) {
      setUpdateError(err.message || "Failed to update model");
    } finally {
      setUpdateLoading(false);
    }
  };

  const submitDelete = async () => {
    setDeleteLoading(true);
    try {
      await modelService.deleteModel(deletingModel.name, deletingModel.version, deletingModel.id);
      setDeletingModel(null);
      fetchModels();
    } catch (err) {
      setDeleteError(err.message || "Failed to delete model version");
    } finally {
      setDeleteLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-12 text-center text-gray-500 bg-white rounded-lg border border-gray-200">
        <div className="animate-pulse flex flex-col items-center">
          <div className="h-8 w-8 bg-blue-400 rounded-full mb-4"></div>
          <p>Loading model inventory...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto p-6 bg-red-50 text-red-700 rounded-md border border-red-200">
        <h3 className="font-bold mb-2">Error loading models</h3>
        <p>{error}</p>
        <button onClick={fetchModels} className="mt-4 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-800 rounded transition-colors">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Models Inventory</h1>
          <p className="text-gray-500 mt-1">
            Total registered model identities: <span className="font-bold text-gray-700">{Object.keys(groupedIdentities).length}</span>
          </p>
        </div>
        
        <div className="flex items-center space-x-3">
          <button 
            onClick={onRegisterNew}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-sm transition-colors flex items-center space-x-2"
          >
            <span>+</span>
            <span>Register New Model</span>
          </button>
          <button 
            onClick={fetchModels} 
            className="px-4 py-2.5 bg-white text-gray-700 font-medium rounded-lg shadow-sm border border-gray-300 hover:bg-gray-50 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Controls Bar: Search, Filters, Sort */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Search */}
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Search Models</label>
          <input
            type="text"
            placeholder="Search by model name..."
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
            className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Model Type Filter */}
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Model Type</label>
          <select
            value={selectedType}
            onChange={(e) => { setSelectedType(e.target.value); setCurrentPage(1); }}
            className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="All">All Types</option>
            <option value="Speech">Speech</option>
            <option value="NER">NER</option>
            <option value="File Classifier">File Classifier</option>
          </select>
        </div>

        {/* Deployment Point Filter */}
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Deployment Point</label>
          <select
            value={selectedDeploymentPoint}
            onChange={(e) => { setSelectedDeploymentPoint(e.target.value); setCurrentPage(1); }}
            className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="All">All Deployment Points</option>
            {allDeploymentPoints.map(dp => (
              <option key={dp} value={dp}>{dp}</option>
            ))}
          </select>
        </div>

        {/* Sort Controls */}
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Sort By</label>
          <div className="flex space-x-2">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="name">Model Name</option>
              <option value="version">Latest Version</option>
              <option value="accuracy">Accuracy</option>
              <option value="priority">Priority</option>
            </select>
            <button
              onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
              className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-md text-xs border border-gray-300"
              title="Toggle Ascending/Descending"
            >
              {sortOrder === 'asc' ? '▲ ASC' : '▼ DESC'}
            </button>
          </div>
        </div>
      </div>

      {/* Model Cards List (Responsive Grid Layout: 2 columns on desktop) */}
      {filteredIdentities.length === 0 ? (
        <div className="p-12 text-center text-gray-500 bg-white rounded-xl border border-gray-200 shadow-sm">
          No models matched your search or filters.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {paginatedNames.map(name => (
            <ModelCard 
              key={name} 
              name={name} 
              modelInfo={groupedIdentities[name]}
              versions={groupedIdentities[name].all_versions || []} 
              onEdit={handleOpenEdit} 
              onDelete={setDeletingModel} 
              onAddNewVersion={onAddNewVersion}
              onRefresh={fetchModels}
            />
          ))}
        </div>
      )}


      {/* Pagination Bar */}
      {filteredIdentities.length > itemsPerPage && (
        <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-sm text-gray-600">
            Showing <span className="font-semibold">{((currentPage - 1) * itemsPerPage) + 1}</span> to <span className="font-semibold">{Math.min(currentPage * itemsPerPage, filteredIdentities.length)}</span> of <span className="font-semibold">{filteredIdentities.length}</span> models
          </p>

          <div className="flex space-x-2">
            <button
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              className={`px-4 py-2 text-sm font-medium rounded-md border ${currentPage === 1 ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
            >
              Previous
            </button>
            
            <div className="flex items-center space-x-1 px-2">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                <button
                  key={p}
                  onClick={() => setCurrentPage(p)}
                  className={`w-8 h-8 rounded-md text-xs font-bold ${currentPage === p ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                >
                  {p}
                </button>
              ))}
            </div>

            <button
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              className={`px-4 py-2 text-sm font-medium rounded-md border ${currentPage === totalPages ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingModel && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full shadow-xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-bold mb-1 text-gray-900">Edit Model Version</h3>
            <p className="text-sm text-gray-500 mb-6 font-medium">Updating: {editingModel.name} v{editingModel.version}</p>
            
            {updateError && <div className="mb-4 text-red-700 bg-red-50 border border-red-200 p-3 rounded-md text-sm">{updateError}</div>}
            
            <form onSubmit={submitEdit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Purpose:</label>
                <input type="text" name="purpose" value={editForm.purpose} onChange={e => setEditForm({...editForm, purpose: e.target.value})} className="w-full p-2.5 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Architecture:</label>
                <input type="text" name="architecture" value={editForm.architecture} onChange={e => setEditForm({...editForm, architecture: e.target.value})} className="w-full p-2.5 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Accuracy:</label>
                  <input type="number" step="0.01" name="accuracy" value={editForm.accuracy} onChange={e => setEditForm({...editForm, accuracy: e.target.value})} className="w-full p-2.5 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority:</label>
                  <input type="number" name="priority" value={editForm.priority} onChange={e => setEditForm({...editForm, priority: e.target.value})} className="w-full p-2.5 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Remarks:</label>
                <textarea rows="2" name="remarks" value={editForm.remarks} onChange={e => setEditForm({...editForm, remarks: e.target.value})} className="w-full p-2.5 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
              </div>
              <div className="pt-2">
                <label className="flex items-center space-x-3 text-sm font-medium text-gray-900 cursor-pointer w-fit">
                  <input type="checkbox" checked={editForm.is_deployable} onChange={e => setEditForm({...editForm, is_deployable: e.target.checked})} className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 h-5 w-5" />
                  <span>Mark as Deployable</span>
                </label>
              </div>
              <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-100">
                <button type="button" onClick={() => setEditingModel(null)} className="px-5 py-2.5 bg-white border border-gray-300 text-gray-700 font-medium rounded-md hover:bg-gray-50 transition-colors">Cancel</button>
                <button type="submit" disabled={updateLoading} className="px-5 py-2.5 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 transition-colors shadow-sm">{updateLoading ? 'Saving...' : 'Save Changes'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {deletingModel && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full shadow-xl">
            <h3 className="text-xl font-bold mb-2 text-red-600">Delete Version</h3>
            <p className="mb-4 text-gray-700">Are you sure you want to delete <span className="font-semibold">{deletingModel.name} v{deletingModel.version}</span>?</p>
            <p className="text-sm text-gray-500 mb-6 bg-gray-50 p-3 rounded">This will permanently remove this specific version from the registry. This action cannot be undone.</p>
            
            {deleteError && <div className="mb-4 text-red-700 bg-red-50 border border-red-200 p-3 rounded-md text-sm">{deleteError}</div>}
            
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
              <button type="button" onClick={() => setDeletingModel(null)} className="px-5 py-2.5 bg-white border border-gray-300 text-gray-700 font-medium rounded-md hover:bg-gray-50 transition-colors">Cancel</button>
              <button onClick={submitDelete} disabled={deleteLoading} className="px-5 py-2.5 bg-red-600 text-white font-medium rounded-md hover:bg-red-700 transition-colors shadow-sm">{deleteLoading ? 'Deleting...' : 'Confirm Delete'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

