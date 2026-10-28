import React, { useState, useEffect, useMemo } from 'react';
import { modelService } from '../../services/modelService';

export default function DeploymentHistoryModal({ 
  isOpen, 
  onClose, 
  initialModelName = '', 
  initialDeploymentPoint = '',
  availableModels = [] 
}) {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedModel, setSelectedModel] = useState(initialModelName || '');
  const [selectedDeploymentPoint, setSelectedDeploymentPoint] = useState(initialDeploymentPoint || '');
  const [selectedAction, setSelectedAction] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');

  useEffect(() => {
    if (isOpen) {
      setSelectedModel(initialModelName || '');
      setSelectedDeploymentPoint(initialDeploymentPoint || '');
      fetchHistory(initialModelName || '', initialDeploymentPoint || '');
    }
  }, [isOpen, initialModelName, initialDeploymentPoint]);

  const fetchHistory = async (modelFilter, deploymentPointFilter) => {
    setLoading(true);
    setError(null);
    try {
      const res = await modelService.getAuditHistory(
        modelFilter || undefined,
        deploymentPointFilter || undefined
      );
      setAudits(res?.audits || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch deployment audit history');
    } finally {
      setLoading(false);
    }
  };

  const handleModelChange = (e) => {
    const val = e.target.value;
    setSelectedModel(val);
    fetchHistory(val, selectedDeploymentPoint);
  };

  const handleDeploymentPointChange = (e) => {
    const val = e.target.value;
    setSelectedDeploymentPoint(val);
    fetchHistory(selectedModel, val);
  };

  const filteredAudits = useMemo(() => {
    return audits.filter(item => {
      if (selectedAction !== 'All' && item.action !== selectedAction) return false;
      if (selectedStatus !== 'All' && item.status !== selectedStatus) return false;
      return true;
    });
  }, [audits, selectedAction, selectedStatus]);

  if (!isOpen) return null;

  const formatTimestamp = (ts) => {
    if (!ts) return 'N/A';
    try {
      const d = new Date(typeof ts === 'number' ? ts : Number(ts));
      return isNaN(d.getTime()) ? String(ts) : d.toLocaleString();
    } catch {
      return String(ts);
    }
  };

  const getActionBadge = (action) => {
    switch (action) {
      case 'deploy':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800">Deploy Request</span>;
      case 'runtime_status':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-purple-100 text-purple-800">Runtime Status</span>;
      case 'rollback':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800">Rollback</span>;
      case 'reset':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-800">Reset</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-700">{action || 'Event'}</span>;
    }
  };

  const getStatusBadge = (status) => {
    if (status === 'success') {
      return <span className="px-2 py-0.5 rounded text-xs font-bold bg-green-100 text-green-800">SUCCESS</span>;
    }
    return <span className="px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-800">FAILURE</span>;
  };

  const renderDetails = (item) => {
    const isSuccess = item.status === 'success';

    if (isSuccess) {
      let text = 'Completed successfully';
      if (item.action === 'rollback') {
        if (item.previous_version != null && item.requested_version != null) {
          text = `Rolled back from v${item.previous_version} to v${item.requested_version}`;
        } else if (item.requested_version != null) {
          text = `Rolled back to v${item.requested_version}`;
        } else {
          text = item.error_message || 'Rolled back successfully';
        }
      } else if (item.action === 'deploy') {
        text = 'Completed successfully';
      } else if (item.error_message) {
        text = item.error_message;
      }

      const isTechnical = Boolean(item.error_message && item.action === 'runtime_status');
      return (
        <span className={`text-green-700 text-[11px] block ${isTechnical ? 'font-mono' : ''}`}>
          {text}
        </span>
      );
    }

    const failText = item.error_message || (
      item.action === 'rollback'
        ? 'Rollback failed'
        : item.action === 'deploy'
        ? 'Deployment request failed'
        : 'Operation failed'
    );

    return (
      <span className="text-red-700 font-mono text-[11px] block">
        {failText}
      </span>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-5xl w-full shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-gray-200 flex justify-between items-center bg-gray-50">
          <div>
            <h2 className="text-xl font-bold text-gray-900 flex items-center space-x-2">
              <span>🕒</span>
              <span>Deployment Audit History</span>
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Persistent record of all model deployment requests, runtime confirmations, and rollbacks.
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => fetchHistory(selectedModel, selectedDeploymentPoint)}
              disabled={loading}
              className="px-3 py-1.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold rounded-md shadow-sm transition-colors"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-gray-200 text-gray-500 font-bold"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Filters Bar */}
        <div className="p-4 bg-white border-b border-gray-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Model Filter</label>
            <select
              value={selectedModel}
              onChange={handleModelChange}
              className="w-full p-2 border border-gray-300 rounded-md text-xs font-medium focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Registered Models</option>
              {availableModels.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Deployment Point</label>
            <select
              value={selectedDeploymentPoint}
              onChange={handleDeploymentPointChange}
              className="w-full p-2 border border-gray-300 rounded-md text-xs font-medium focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Deployment Points</option>
              <option value="Text Pipeline">Text Pipeline</option>
              <option value="ASR">ASR</option>
              <option value="LID">LID</option>
              <option value="Diarization">Diarization</option>
              <option value="Speaker Identification">Speaker Identification</option>
              <option value="UIS">UIS</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Action</label>
            <select
              value={selectedAction}
              onChange={(e) => setSelectedAction(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md text-xs font-medium focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="All">All Actions</option>
              <option value="deploy">Deployment Requests</option>
              <option value="runtime_status">Runtime Status</option>
              <option value="rollback">Rollbacks</option>
              <option value="reset">Resets</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Status</label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md text-xs font-medium focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="All">All Statuses</option>
              <option value="success">Success Only</option>
              <option value="failure">Failure Only</option>
            </select>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <div className="py-16 text-center text-gray-500">
              <div className="animate-spin inline-block w-6 h-6 border-2 border-current border-t-transparent text-blue-600 rounded-full mb-2"></div>
              <p className="text-sm">Loading audit events from PostgreSQL...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-50 text-red-700 rounded-md border border-red-200 text-sm">
              {error}
            </div>
          ) : filteredAudits.length === 0 ? (
            <div className="py-16 text-center text-gray-500">
              <p className="text-sm font-medium">No deployment audit events found matching the selected filters.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border border-gray-200 rounded-lg overflow-hidden">
                <thead className="bg-gray-100 text-gray-700 uppercase font-semibold">
                  <tr>
                    <th className="py-3 px-3">Timestamp</th>
                    <th className="py-3 px-3">Model</th>
                    <th className="py-3 px-3">Version</th>
                    <th className="py-3 px-3">Deployment Point</th>
                    <th className="py-3 px-3">Action</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3">Active In Service</th>
                    <th className="py-3 px-3">Details / Errors</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {filteredAudits.map((item, idx) => {
                    const activeModelStr = item.active_model_name 
                      ? `${item.active_model_name} ${item.active_model_version ? `v${item.active_model_version}` : ''}`
                      : '-';

                    return (
                      <tr key={item.id || idx} className="hover:bg-gray-50">
                        <td className="py-2.5 px-3 text-gray-600 whitespace-nowrap font-mono">
                          {formatTimestamp(item.timestamp)}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-gray-900">
                          {item.model_name || '-'}
                        </td>
                        <td className="py-2.5 px-3 font-medium text-gray-700">
                          {item.requested_version ? `v${item.requested_version}` : (item.previous_version ? `v${item.previous_version}` : '-')}
                        </td>
                        <td className="py-2.5 px-3 text-gray-700">
                          {item.deployment_point || '-'}
                        </td>
                        <td className="py-2.5 px-3">
                          {getActionBadge(item.action)}
                        </td>
                        <td className="py-2.5 px-3">
                          {getStatusBadge(item.status)}
                        </td>
                        <td className="py-2.5 px-3 font-medium text-blue-900 whitespace-nowrap">
                          {activeModelStr !== '-' ? (
                            <span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-mono text-[11px]">
                              {activeModelStr}
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-gray-600 max-w-xs break-words">
                          {renderDetails(item)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50 flex justify-between items-center text-xs text-gray-500">
          <span>
            Total events: <strong className="text-gray-700">{filteredAudits.length}</strong>
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold rounded-md transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
