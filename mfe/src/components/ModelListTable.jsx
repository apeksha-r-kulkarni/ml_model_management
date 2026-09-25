import React, { useState } from 'react';

export default function ModelListTable({ models, onListModels, onUpdateModel, onDeleteModel, loading, error, hasLoaded, operationType, searchQuery }) {
  // Update state
  const [editingModel, setEditingModel] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updateLoading, setUpdateLoading] = useState(false);
  const [updateError, setUpdateError] = useState(null);
  const [updateSuccess, setUpdateSuccess] = useState(null);

  // Delete state
  const [deletingModel, setDeletingModel] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [deleteSuccess, setDeleteSuccess] = useState(null);

  const openEdit = (m) => {
    setEditingModel(m);
    setEditForm({
      id: m.id,
      purpose: m.purpose || '',
      architecture: m.architecture || '',
      accuracy: m.accuracy || 0.0,
      priority: (m.priority !== null && m.priority !== undefined) ? m.priority : '',
      is_deployable: m.is_deployable || false
    });
    setUpdateError(null);
    setUpdateSuccess(null);
  };

  const closeEdit = () => {
    setEditingModel(null);
  };

  const handleEditChange = (e) => {
    const { name, value, type, checked } = e.target;
    setEditForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const submitEdit = async (e) => {
    e.preventDefault();
    setUpdateLoading(true);
    setUpdateError(null);
    setUpdateSuccess(null);

    const payload = {
      id: editForm.id,
      purpose: editForm.purpose,
      architecture: editForm.architecture,
      accuracy: parseFloat(editForm.accuracy) || 0.0,
      priority: editForm.priority !== '' ? parseInt(editForm.priority, 10) : null,
      is_deployable: editForm.is_deployable
    };

    try {
      await onUpdateModel(payload);
      setUpdateSuccess("Model updated successfully.");
      setTimeout(() => {
        closeEdit();
      }, 1500);
    } catch (err) {
      setUpdateError(err.message || "Failed to update model");
    } finally {
      setUpdateLoading(false);
    }
  };

  const openDelete = (m) => {
    setDeletingModel(m);
    setDeleteError(null);
    setDeleteSuccess(null);
  };

  const closeDelete = () => {
    if (!deleteLoading) {
      setDeletingModel(null);
    }
  };

  const submitDelete = async () => {
    setDeleteLoading(true);
    setDeleteError(null);
    setDeleteSuccess(null);
    try {
      await onDeleteModel(deletingModel.name, deletingModel.version, deletingModel.id);
      setDeleteSuccess("Model version deleted successfully.");
      setTimeout(() => {
        setDeletingModel(null);
      }, 1500);
    } catch (err) {
      setDeleteError(err.message || "Failed to delete model version");
    } finally {
      setDeleteLoading(false);
    }
  };

  // Group by name
  const grouped = {};
  (models || []).forEach(m => {
    if (!grouped[m.name]) grouped[m.name] = [];
    grouped[m.name].push(m);
  });

  let title = "Model Registry";
  if (operationType === 'LIST') {
    title = "All Models";
  } else if (operationType === 'SEARCH') {
    title = `Search Results for: "${searchQuery}"`;
  }

  return (
    <div className="bg-white shadow-sm rounded-lg border border-gray-200 p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-800">{title}</h2>
        <button 
          onClick={onListModels}
          disabled={loading}
          className={`px-4 py-2 font-medium rounded-md transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            ${loading ? 'bg-blue-400 cursor-not-allowed text-white' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
        >
          {loading ? 'Loading Models...' : 'List Models'}
        </button>
      </div>
      
      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 border border-red-200 rounded-md">
          {error}
        </div>
      )}

      {hasLoaded && models.length === 0 && !error && (
        <div className="p-4 text-center text-gray-500 border border-gray-200 rounded-lg bg-gray-50">
          No models found.
        </div>
      )}
      
      {hasLoaded && models.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-100 border-b border-gray-200">
                <th className="p-3 text-sm font-semibold text-gray-700 whitespace-nowrap">Version</th>
                <th className="p-3 text-sm font-semibold text-gray-700 whitespace-nowrap">Type</th>
                <th className="p-3 text-sm font-semibold text-gray-700 whitespace-nowrap">Architecture</th>
                <th className="p-3 text-sm font-semibold text-gray-700 whitespace-nowrap">Priority</th>
                <th className="p-3 text-sm font-semibold text-gray-700 whitespace-nowrap">Deployable</th>
                <th className="p-3 text-sm font-semibold text-gray-700 whitespace-nowrap">Accuracy</th>
                <th className="p-3 text-sm font-semibold text-gray-700 whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            
            {Object.keys(grouped).map((name) => (
              <tbody key={name} className="border-b-2 border-gray-300">
                <tr>
                  <td colSpan="7" className="p-3 font-bold bg-gray-50 text-gray-800">
                    {name}
                  </td>
                </tr>
                {grouped[name].map((m) => (
                  <tr key={m.id} className="border-t border-gray-200 hover:bg-gray-50 transition-colors">
                    <td className="p-3 text-sm">v{m.version}</td>
                    <td className="p-3 text-sm text-gray-600">{m.model_type || '-'}</td>
                    <td className="p-3 text-sm text-gray-600">{m.architecture || '-'}</td>
                    <td className="p-3 text-sm text-gray-600">{(m.priority !== null && m.priority !== undefined && m.priority !== "") ? m.priority : '-'}</td>
                    <td className="p-3 text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${m.is_deployable ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {m.is_deployable ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="p-3 text-sm text-gray-600">{m.accuracy || 0.0}</td>
                    <td className="p-3 text-sm flex gap-2">
                      <button 
                        onClick={() => openEdit(m)}
                        className="px-3 py-1 bg-white border border-gray-300 rounded text-blue-600 hover:bg-gray-100" 
                      >
                        Edit
                      </button>
                      <button 
                        onClick={() => openDelete(m)}
                        className="px-3 py-1 bg-red-50 border border-red-200 rounded text-red-600 hover:bg-red-100" 
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            ))}
          </table>
        </div>
      )}
      
      {!hasLoaded && !loading && !error && (
        <div className="p-4 text-center text-gray-500 border border-gray-200 rounded-lg bg-gray-50">
          Click List Models to view registered models.
        </div>
      )}

      {/* Edit Modal */}
      {editingModel && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full shadow-xl">
            <h3 className="text-xl font-bold mb-1 text-gray-800">Edit Model</h3>
            <p className="text-sm text-gray-500 mb-4 font-medium">Editing: {editingModel.name} v{editingModel.version}</p>
            
            {updateError && <div className="mb-4 text-red-700 bg-red-50 border border-red-200 p-3 rounded-md">{updateError}</div>}
            {updateSuccess && <div className="mb-4 text-green-700 bg-green-50 border border-green-200 p-3 rounded-md">{updateSuccess}</div>}

            <form onSubmit={submitEdit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Purpose:</label>
                <input type="text" name="purpose" value={editForm.purpose} onChange={handleEditChange} className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Architecture:</label>
                <input type="text" name="architecture" value={editForm.architecture} onChange={handleEditChange} className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Accuracy:</label>
                  <input type="number" step="0.01" name="accuracy" value={editForm.accuracy} onChange={handleEditChange} className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority:</label>
                  <input type="number" name="priority" value={editForm.priority} onChange={handleEditChange} className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
                </div>
              </div>
              <div>
                <label className="flex items-center space-x-2 text-sm font-medium text-gray-700 cursor-pointer w-fit">
                  <input type="checkbox" name="is_deployable" checked={editForm.is_deployable} onChange={handleEditChange} className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                  <span>Is Deployable Ready?</span>
                </label>
              </div>

              <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200">
                <button type="button" onClick={closeEdit} disabled={updateLoading} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:ring-2 focus:ring-gray-200 transition-colors">
                  Cancel
                </button>
                <button type="submit" disabled={updateLoading} className={`px-4 py-2 text-white font-medium rounded-md focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors ${updateLoading ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}>
                  {updateLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {deletingModel && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full shadow-xl">
            <h3 className="text-xl font-bold mb-4 text-red-600">Delete Model Version</h3>
            
            <div className="mb-4 text-gray-700">
              <p className="mb-2">Are you sure you want to delete this specific version?</p>
              <div className="bg-gray-50 border border-gray-200 p-3 rounded text-sm">
                <p><strong>Name:</strong> {deletingModel.name}</p>
                <p><strong>Version:</strong> v{deletingModel.version}</p>
              </div>
              <p className="mt-2 text-sm font-medium text-red-600">This action cannot be undone and deletes ONLY this version.</p>
            </div>

            {deleteError && <div className="mb-4 text-red-700 bg-red-50 border border-red-200 p-3 rounded-md">{deleteError}</div>}
            {deleteSuccess && <div className="mb-4 text-green-700 bg-green-50 border border-green-200 p-3 rounded-md">{deleteSuccess}</div>}

            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200">
              <button 
                type="button" 
                onClick={closeDelete} 
                disabled={deleteLoading} 
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:ring-2 focus:ring-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={submitDelete} 
                disabled={deleteLoading} 
                className={`px-4 py-2 text-white font-medium rounded-md focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors ${deleteLoading ? 'bg-red-400 cursor-not-allowed' : 'bg-red-600 hover:bg-red-700'}`}
              >
                {deleteLoading ? 'Deleting...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
