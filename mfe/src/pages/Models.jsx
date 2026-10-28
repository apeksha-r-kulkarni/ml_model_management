import React, { useState, useEffect, useMemo, useRef } from 'react';
import { modelService } from '../services/modelService';
import ModelCard from '../components/models/ModelCard';
import DeploymentHistoryModal from '../components/models/DeploymentHistoryModal';

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
  const itemsPerPage = 6;

  // Edit/Delete modal state
  const [editingModel, setEditingModel] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updateLoading, setUpdateLoading] = useState(false);
  const [updateError, setUpdateError] = useState(null);
  
  const [deletingModel, setDeletingModel] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  // Model-first Deployment Selection state
  const [deploySelectedModel, setDeploySelectedModel] = useState('');
  const [deploySelectedPoint, setDeploySelectedPoint] = useState('Text Pipeline');
  const [deploySelectedVersion, setDeploySelectedVersion] = useState('');
  const [deployActionLoading, setDeployActionLoading] = useState(false);
  const [deployActionMsg, setDeployActionMsg] = useState(null);
  const [pendingDeployment, setPendingDeployment] = useState(null);

  // Deployment Audit History modal state
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [historySelectedModel, setHistorySelectedModel] = useState('');

  const handleOpenHistory = (modelName = '') => {
    setHistorySelectedModel(modelName);
    setHistoryModalOpen(true);
  };

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
  const allDeploymentPoints = [
    'ASR',
    'Diarization',
    'LID',
    'Speaker Identification',
    'Text Pipeline',
    'UIS'
  ];

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
        valA = parseInt(aLatest.version, 10) || 0;
        valB = parseInt(bLatest.version, 10) || 0;
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
      name: editingModel.name,
      version: editingModel.version,
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

  // Calculate selected model's versions, eligible versions, and default version
  const selectedModelObj = groupedIdentities[deploySelectedModel] || null;
  const selectedModelVersions = useMemo(() => {
    return selectedModelObj ? (selectedModelObj.all_versions || []) : [];
  }, [selectedModelObj]);
  
  // Eligible versions for selected deployment point
  const eligibleVersions = useMemo(() => {
    if (!selectedModelObj) return [];
    return selectedModelVersions.filter(v => 
      v.is_deployable && (v.deployment_points || []).includes(deploySelectedPoint)
    );
  }, [selectedModelObj, selectedModelVersions, deploySelectedPoint]);

  // Model's designated default version for this deployment point
  const modelDefaultVersion = selectedModelObj?.default_versions?.[deploySelectedPoint] || '';
  const currentlyDeployedVersion = selectedModelObj?.currently_deployed?.[deploySelectedPoint] || '';
  const pendingVersion = (pendingDeployment && pendingDeployment.model === deploySelectedModel && pendingDeployment.point === deploySelectedPoint)
    ? pendingDeployment.version
    : (selectedModelObj?.pending_deployments?.[deploySelectedPoint] || '');

  // Track previous model and deployment point to only auto-preselect on selection change
  const prevSelectionRef = useRef({ model: '', point: '' });
  useEffect(() => {
    const hasChanged = prevSelectionRef.current.model !== deploySelectedModel || prevSelectionRef.current.point !== deploySelectedPoint;
    prevSelectionRef.current = { model: deploySelectedModel, point: deploySelectedPoint };

    if (hasChanged) {
      if (deploySelectedModel && currentlyDeployedVersion) {
        setDeploySelectedVersion(String(currentlyDeployedVersion));
      } else if (deploySelectedModel && modelDefaultVersion) {
        setDeploySelectedVersion(String(modelDefaultVersion));
      } else if (eligibleVersions.length > 0) {
        setDeploySelectedVersion(String(eligibleVersions[0].version));
      } else {
        setDeploySelectedVersion('');
      }
    }
  }, [deploySelectedModel, deploySelectedPoint, currentlyDeployedVersion, modelDefaultVersion, eligibleVersions]);

  // Poll deployment status and automatic rollback when a deployment is pending
  useEffect(() => {
    if (!pendingDeployment) return;
    const { model, point, version, requestTime } = pendingDeployment;
    let isCancelled = false;
    let attempts = 0;
    const maxAttempts = 300; // 600s / 10 minutes polling window (comfortably covers slow large model downloads ~5m + RAM load)

    const poll = async () => {
      if (isCancelled) return;
      attempts += 1;
      try {
        const auditData = await modelService.getAuditHistory(model, point);
        if (isCancelled) return;
        const audits = auditData?.audits || [];

        // Check audits with timestamps within or after the deployment request window (-3000ms for clock variance)
        const recentAudits = audits.filter(a => {
          const ts = typeof a.timestamp === 'number' ? a.timestamp : 0;
          return ts >= requestTime - 3000;
        });

        // 1. Confirmed automatic rollback
        const rollbackEvent = recentAudits.find(a => 
          a.action === 'rollback' && a.status === 'success'
        );
        if (rollbackEvent) {
          const targetV = rollbackEvent.requested_version;
          if (!isCancelled) {
            setPendingDeployment(null);
            setDeployActionMsg({
              type: 'warning',
              text: `Deployment of ${model} v${version} failed. Automatically rolled back to v${targetV}.`
            });
            if (targetV != null) {
              setDeploySelectedVersion(String(targetV));
            }
            await fetchModels();
          }
          return;
        }

        // 2. Confirmed runtime success
        const successEvent = recentAudits.find(a => 
          a.action === 'runtime_status' && a.status === 'success' && String(a.requested_version) === String(version)
        );
        if (successEvent) {
          if (!isCancelled) {
            setPendingDeployment(null);
            setDeployActionMsg({
              type: 'success',
              text: `Successfully deployed and activated '${model}' v${version} on '${point}'`
            });
            await fetchModels();
          }
          return;
        }

        // 3. Fallback: check if backend model registry already shows rollback
        if (attempts >= 3) {
          const listRes = await modelService.listModels();
          if (isCancelled) return;
          const targetModel = (listRes?.models || []).find(m => m.name === model);
          const activeVer = targetModel?.currently_deployed?.[point];
          const isStillPending = targetModel?.pending_deployments?.[point] === String(version);
          if (!isStillPending && activeVer && String(activeVer) !== String(version)) {
            setPendingDeployment(null);
            setDeployActionMsg({
              type: 'warning',
              text: `Deployment of ${model} v${version} failed. Automatically rolled back to v${activeVer}.`
            });
            setDeploySelectedVersion(String(activeVer));
            await fetchModels();
            return;
          }
        }

        // 4. Confirmed rollback failure (no previous version available for rollback)
        const failedRollback = recentAudits.find(a => 
          a.action === 'rollback' && a.status === 'failure'
        );
        if (failedRollback) {
          if (!isCancelled) {
            setPendingDeployment(null);
            const listRes = await modelService.listModels();
            const activeModel = (listRes?.models || []).find(m => m.currently_deployed?.[point]);
            const activeVer = activeModel?.currently_deployed?.[point];

            let msg = `Deployment of ${model} v${version} failed. No previous valid version is available for rollback.`;
            if (activeModel && activeVer) {
              msg += ` Active model: '${activeModel.name}' v${activeVer} remains in service.`;
            } else {
              msg += ` No model is currently active for '${point}'.`;
            }

            setDeployActionMsg({
              type: 'error',
              text: msg
            });
            await fetchModels();
          }
          return;
        }

        const failureEvent = recentAudits.find(a => 
          a.action === 'runtime_status' && a.status === 'failure' && String(a.requested_version) === String(version)
        );
        if (failureEvent && attempts >= 4) {
          if (!isCancelled) {
            setPendingDeployment(null);
            const listRes = await modelService.listModels();
            const activeModel = (listRes?.models || []).find(m => m.currently_deployed?.[point]);
            const activeVer = activeModel?.currently_deployed?.[point];

            let msg = `Deployment of ${model} v${version} failed: ${failureEvent.error_message || 'Pipeline load failure'}.`;
            if (activeModel && activeVer) {
              msg += ` Active model: '${activeModel.name}' v${activeVer} remains in service.`;
            } else {
              msg += ` No model is currently active for '${point}'.`;
            }
            setDeployActionMsg({
              type: 'error',
              text: msg
            });
            await fetchModels();
          }
          return;
        }

        // 5. Timeout after maxAttempts (600s / 10 minutes)
        if (attempts >= maxAttempts) {
          if (!isCancelled) {
            setPendingDeployment(null);
            setDeployActionMsg({
              type: 'info',
              text: `Deployment request for '${model}' v${version} was sent to registry. Pipeline runtime confirmation timed out after 10 minutes. If model artifact download or memory loading is still underway, activation will complete in the background.`
            });
            await fetchModels();
          }
          return;
        }
      } catch {
        // ignore transient poll errors
      }
    };

    const intervalId = setInterval(poll, 2000);
    poll();

    return () => {
      isCancelled = true;
      clearInterval(intervalId);
    };
  }, [pendingDeployment]);

  const handleDeploySelection = async () => {
    if (!deploySelectedModel || !deploySelectedPoint) return;
    setDeployActionLoading(true);
    setDeployActionMsg(null);
    try {
      // If version is selected, send that version; if empty, omit version so backend resolves default
      const targetVer = deploySelectedVersion ? Number(deploySelectedVersion) : undefined;
      const res = await modelService.setDeployedVersion(
        deploySelectedModel, 
        targetVer, 
        deploySelectedPoint
      );
      const effectiveVer = res.version || targetVer;

      setPendingDeployment({
        model: deploySelectedModel,
        point: deploySelectedPoint,
        version: effectiveVer,
        requestTime: Date.now()
      });

      setDeployActionMsg({
        type: 'info',
        text: `Deployment requested for '${deploySelectedModel}' v${effectiveVer} to '${deploySelectedPoint}'. Waiting for pipeline confirmation...`
      });
      await fetchModels();
    } catch (err) {
      setDeployActionMsg({ type: 'error', text: err.message || 'Deployment failed' });
    } finally {
      setDeployActionLoading(false);
    }
  };

  const handleResetSelection = async () => {
    if (!deploySelectedModel || !deploySelectedPoint) return;
    setPendingDeployment(null);
    setDeployActionLoading(true);
    setDeployActionMsg(null);
    try {
      await modelService.resetDeployedVersion(deploySelectedModel, deploySelectedPoint);
      setDeployActionMsg({ type: 'success', text: `Successfully reset active deployment for '${deploySelectedModel}' on '${deploySelectedPoint}'` });
      await fetchModels();
    } catch (err) {
      setDeployActionMsg({ type: 'error', text: err.message || 'Reset failed' });
    } finally {
      setDeployActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-12 text-center text-gray-500 bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="animate-pulse flex flex-col items-center">
          <div className="h-8 w-8 bg-blue-400 rounded-full mb-4"></div>
          <p>Loading model inventory...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto p-6 bg-red-50 text-red-700 rounded-md border border-red-200 shadow-sm">
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
            onClick={() => handleOpenHistory('')}
            className="px-4 py-2.5 bg-indigo-50 text-indigo-700 font-semibold rounded-lg shadow-sm border border-indigo-200 hover:bg-indigo-100 transition-colors flex items-center space-x-2"
            title="View persistent deployment audit history"
          >
            <span>🕒</span>
            <span>Deployment History</span>
          </button>
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

      {/* Model-First Deployment Selection Bar */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 p-5 rounded-xl shadow-sm space-y-3">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <h2 className="text-sm font-bold uppercase tracking-wider text-blue-900 flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
            <span>Deploy Model to Pipeline</span>
          </h2>
          <span className="text-xs text-blue-700 font-medium">
            Step 1: Select Model &rarr; Step 2: Choose Deployment Point &rarr; Step 3: Verify Version &rarr; Click Deploy
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
          {/* Step 1: Select Model */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">1. Select Registered Model</label>
            <select
              value={deploySelectedModel}
              onChange={(e) => setDeploySelectedModel(e.target.value)}
              className="w-full p-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-900 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">-- Choose a Model --</option>
              {Object.keys(groupedIdentities).map(mName => (
                <option key={mName} value={mName}>{mName}</option>
              ))}
            </select>
          </div>

          {/* Step 2: Deployment Point */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">2. Deployment Point</label>
            <select
              value={deploySelectedPoint}
              onChange={(e) => setDeploySelectedPoint(e.target.value)}
              className="w-full p-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-900 focus:ring-blue-500 focus:border-blue-500"
            >
              {allDeploymentPoints.map(dp => (
                <option key={dp} value={dp}>{dp}</option>
              ))}
            </select>
          </div>

          {/* Step 3: Select Version */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="block text-xs font-semibold text-gray-700 uppercase">3. Model Version</label>
              <div className="flex items-center space-x-1">
                {currentlyDeployedVersion && (
                  <span className="text-[10px] font-bold text-green-700 bg-green-100 px-1.5 py-0.2 rounded" title="Currently deployed to pipeline">
                    Active: v{currentlyDeployedVersion}
                  </span>
                )}
                {pendingVersion && (
                  <span className="text-[10px] font-bold text-amber-800 bg-amber-100 px-1.5 py-0.2 rounded animate-pulse" title="Deployment requested; awaiting runtime confirmation">
                    Pending: v{pendingVersion}
                  </span>
                )}
                {modelDefaultVersion && (
                  <span className="text-[10px] font-bold text-blue-700 bg-blue-100 px-1.5 py-0.2 rounded" title="Designated default version">
                    Default: v{modelDefaultVersion}
                  </span>
                )}
              </div>
            </div>
            <select
              disabled={!deploySelectedModel}
              value={deploySelectedVersion}
              onChange={(e) => setDeploySelectedVersion(e.target.value)}
              className="w-full p-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-900 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
            >
              {!deploySelectedModel ? (
                <option value="">Select model first...</option>
              ) : selectedModelVersions.length === 0 ? (
                <option value="">No versions available</option>
              ) : (
                selectedModelVersions.map(v => {
                  const isEligible = v.is_deployable && (v.deployment_points || []).includes(deploySelectedPoint);
                  const isCurDeployed = currentlyDeployedVersion && String(currentlyDeployedVersion) === String(v.version);
                  const isPending = pendingVersion && String(pendingVersion) === String(v.version);
                  const isDef = modelDefaultVersion && String(modelDefaultVersion) === String(v.version);
                  let label = `v${v.version}`;
                  if (isCurDeployed) label += " (Currently Deployed)";
                  else if (isPending) label += " (Deployment Pending)";
                  else if (isDef) label += " (Default Available)";
                  else if (isEligible) label += " (Deployable)";
                  else label += " (Non-Deployable / Ineligible)";
                  return (
                    <option key={v.version} value={v.version} disabled={!isEligible}>
                      {label}
                    </option>
                  );
                })
              )}
            </select>
          </div>

          {/* Action Button */}
          <div className="flex space-x-2">
            <button
              onClick={handleDeploySelection}
              disabled={
                deployActionLoading || 
                Boolean(pendingDeployment) ||
                !deploySelectedModel || 
                eligibleVersions.length === 0
              }
              className={`flex-1 py-2 px-3 text-sm font-semibold rounded-md shadow-sm transition-colors text-white ${
                deployActionLoading || Boolean(pendingDeployment) || !deploySelectedModel || eligibleVersions.length === 0
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
              title={
                !deploySelectedModel 
                  ? "Select a model first" 
                  : eligibleVersions.length === 0 
                  ? `Model '${deploySelectedModel}' has no eligible versions for '${deploySelectedPoint}'` 
                  : `Deploy selected version to ${deploySelectedPoint}`
              }
            >
              {deployActionLoading || Boolean(pendingDeployment) ? 'Deploying...' : 'Deploy'}
            </button>
            {currentlyDeployedVersion && (
              <button
                onClick={handleResetSelection}
                disabled={deployActionLoading || Boolean(pendingDeployment)}
                className="py-2 px-3 text-sm font-semibold rounded-md shadow-sm bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 transition-colors disabled:opacity-50"
                title={`Reset active deployment for '${deploySelectedPoint}'`}
              >
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Status / Error Message */}
        {deployActionMsg && (
          <div className={`p-2.5 rounded text-xs font-semibold flex items-center justify-between ${
            deployActionMsg.type === 'success' 
              ? 'bg-green-100 text-green-800 border border-green-200' 
              : deployActionMsg.type === 'warning'
              ? 'bg-amber-100 text-amber-800 border border-amber-200'
              : deployActionMsg.type === 'info'
              ? 'bg-blue-100 text-blue-800 border border-blue-200'
              : 'bg-red-100 text-red-800 border border-red-200'
          }`}>
            <span>{deployActionMsg.text}</span>
            {pendingDeployment && (
              <span className="text-[10px] font-normal text-blue-600 ml-2 animate-pulse whitespace-nowrap">
                Waiting for pipeline activation (download & memory load in progress)...
              </span>
            )}
          </div>
        )}

        {deploySelectedModel && eligibleVersions.length === 0 && (
          <p className="text-xs text-amber-800 font-medium bg-amber-50 p-2 rounded border border-amber-200">
            Warning: Model <strong>&apos;{deploySelectedModel}&apos;</strong> does not have any versions configured with <code>is_deployable=true</code> and assigned to <strong>&apos;{deploySelectedPoint}&apos;</strong>.
          </p>
        )}
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
              onViewHistory={handleOpenHistory}
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

      {/* Deployment Audit History Modal */}
      <DeploymentHistoryModal
        isOpen={historyModalOpen}
        onClose={() => setHistoryModalOpen(false)}
        initialModelName={historySelectedModel}
        availableModels={Object.keys(groupedIdentities)}
      />
    </div>
  );
}

