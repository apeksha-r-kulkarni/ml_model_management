import React, { useState } from 'react';
import ModelVersionList from './ModelVersionList';
import { modelService } from '../../services/modelService';

export default function ModelCard({ name, modelInfo, versions, onEdit, onDelete, onAddNewVersion, onRefresh }) {
  const [expanded, setExpanded] = useState(false);
  const [deployLoading, setDeployLoading] = useState(false);
  
  // Array is pre-sorted descending by version
  const latest = versions[0] || {};
  const currentlyDeployedVer = latest.currently_deployed_version;
  const currentlyDeployedModel = versions.find(v => v.version === currentlyDeployedVer);

  const handleSetDeployed = async (verNum) => {
    setDeployLoading(true);
    try {
      await modelService.setDeployedVersion(name, verNum);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(`Failed to set deployed version: ${err.message}`);
    } finally {
      setDeployLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden transition-all hover:shadow-md">
      <div className="p-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
          <div>
            <div className="flex items-center space-x-3">
              <h3 className="text-xl font-bold text-gray-900">{name}</h3>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                {modelInfo?.model_type || 'Unknown'}
              </span>
            </div>
            {modelInfo?.purpose && (
              <p className="text-xs text-gray-500 mt-1">
                Purpose: <span className="font-medium text-gray-700">{modelInfo.purpose}</span>
              </p>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <button 
              onClick={() => onAddNewVersion({
                model_name: name,
                model_type: modelInfo?.model_type,
                language: latest.language,
                environment: latest.environment,
                deployment_points: latest.deployment_points
              })}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-md transition-colors shadow-sm"
            >
              + Add New Version
            </button>
            <button 
              onClick={() => setExpanded(!expanded)}
              className="px-4 py-2 bg-blue-50 text-blue-700 text-sm font-semibold rounded-md hover:bg-blue-100 transition-colors border border-blue-100"
            >
              {expanded ? 'Hide Versions' : 'View Versions'}
            </button>
          </div>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-gray-50 p-4 rounded-lg border border-gray-100">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Latest Version</p>
            <p className="text-sm font-bold text-gray-900">v{latest.version}</p>
          </div>

          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Currently Deployed</p>
            <span className="text-xs text-gray-400 font-medium">N/A (Not Tracked)</span>
          </div>

          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Accuracy / Priority</p>
            <p className="text-sm font-medium text-gray-900">
              {latest.accuracy || '0.0'}% {latest.priority !== null && latest.priority !== undefined ? `(P${latest.priority})` : ''}
            </p>
          </div>

          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Deployable</p>
            <p className={`text-sm font-bold ${latest.is_deployable ? 'text-green-700' : 'text-gray-600'}`}>
              {latest.is_deployable ? 'Yes' : 'No'}
            </p>
          </div>
        </div>

        {/* Speech metadata row if applicable */}
        {modelInfo?.model_type === 'Speech' && (latest.language || latest.environment) && (
          <div className="mt-3 text-xs text-gray-600 flex items-center space-x-4 bg-blue-50/50 p-2.5 rounded border border-blue-100/60">
            {latest.language && (
              <div><span className="font-semibold text-gray-700">Language:</span> {latest.language}</div>
            )}
            {latest.environment && (
              <div><span className="font-semibold text-gray-700">Environment:</span> {latest.environment}</div>
            )}
          </div>
        )}
        
        {latest.deployment_points && latest.deployment_points.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Deployment Points:</span>
              <div className="flex flex-wrap gap-1.5">
                {latest.deployment_points.map((dp, idx) => (
                  <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs font-medium rounded border border-gray-200">
                    {dp}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {expanded && (
        <div className="border-t border-gray-200 bg-white p-6 pt-4">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center">
              <span className="w-2 h-2 rounded-full bg-blue-500 mr-2"></span>
              Version History ({versions.length})
            </h4>
          </div>
          <ModelVersionList 
            versions={versions} 
            currentlyDeployedVersion={currentlyDeployedVer}
            onEdit={onEdit} 
            onDelete={onDelete} 
            onSetDeployed={handleSetDeployed}
          />
        </div>
      )}
    </div>
  );
}

