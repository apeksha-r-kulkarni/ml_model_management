import React, { useState } from 'react';
import ModelVersionList from './ModelVersionList';
import { modelService } from '../../services/modelService';

export default function ModelCard({ name, modelInfo, versions, onEdit, onDelete, onAddNewVersion, onRefresh }) {
  const [expanded, setExpanded] = useState(false);
  const [deployLoading, setDeployLoading] = useState(false);
  
  // Array is pre-sorted descending by version
  const latest = versions[0] || {};
  const currentlyDeployed = modelInfo?.currently_deployed || {};

  const handleSetDeployed = async (verNum, dp) => {
    setDeployLoading(true);
    try {
      await modelService.setDeployedVersion(name, verNum, dp);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(`Failed to set deployed version: ${err.message}`);
    } finally {
      setDeployLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-full overflow-hidden transition-all hover:shadow-md">
      <div className="p-6 flex flex-col flex-1">
        <div className="flex flex-col sm:flex-row justify-between items-start gap-4 mb-4">
          <div className="flex-1 min-w-0 pr-4">
            <div className="flex items-start space-x-3">
              <h3 className="text-xl font-bold text-gray-900 line-clamp-2 break-all" title={name}>{name}</h3>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 flex-shrink-0 mt-0.5">
                {modelInfo?.model_type || 'Unknown'}
              </span>
            </div>
            <div className="text-xs mt-1 text-gray-500 line-clamp-2">
              Purpose: <span className="font-medium text-gray-700 break-words">{modelInfo?.purpose || 'N/A'}</span>
            </div>
          </div>
          
          <div className="flex items-center space-x-2 flex-shrink-0">
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
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-gray-50 p-4 rounded-lg border border-gray-100 flex-shrink-0">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Latest Version</p>
            <p className="text-sm font-bold text-gray-900 truncate">v{latest.version}</p>
          </div>

          <div className="flex flex-col">
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Currently Deployed</p>
            <div className="flex-1 overflow-y-auto max-h-[48px] pr-1">
              {Object.keys(currentlyDeployed).length > 0 ? (
                <div className="flex flex-col space-y-1 mt-1">
                  {Object.entries(currentlyDeployed).map(([dp, ver]) => (
                    <div key={dp} className="flex items-center space-x-2">
                      <span className="text-xs text-gray-600 font-medium truncate max-w-[80px]">{dp}:</span>
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-green-100 text-green-800 flex-shrink-0">
                        v{ver}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-xs text-gray-400 font-medium block mt-1">Not deployed</span>
              )}
            </div>
          </div>

          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Accuracy / Priority</p>
            <p className="text-sm font-medium text-gray-900 truncate">
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

        {/* Speech metadata row - only renders when applicable */}
        {modelInfo?.model_type === 'Speech' && (latest.language || latest.environment) && (
          <div className="mt-3 text-xs flex items-center space-x-4 p-2.5 rounded border bg-blue-50/50 border-blue-100/60 text-gray-600 flex-shrink-0">
            {latest.language && (
              <div><span className="font-semibold text-gray-700">Language:</span> {latest.language}</div>
            )}
            {latest.environment && (
              <div><span className="font-semibold text-gray-700">Environment:</span> {latest.environment}</div>
            )}
          </div>
        )}
        
        {/* Spacer to push deployment points down if other cards in row are taller */}
        <div className="flex-1"></div>

        {/* Deployment points row - always visible, pushed to bottom for alignment */}
        <div className="mt-3 pt-3 border-t border-gray-100 flex items-start justify-between flex-shrink-0 mt-auto">
          <div className="flex items-start space-x-2 overflow-hidden w-full">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold mt-0.5 flex-shrink-0">Deployment Points:</span>
            <div className="flex flex-wrap gap-1.5 overflow-y-auto max-h-[36px] flex-1">
              {latest.deployment_points && latest.deployment_points.length > 0 ? (
                latest.deployment_points.map((dp, idx) => (
                  <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs font-medium rounded border border-gray-200">
                    {dp}
                  </span>
                ))
              ) : (
                <span className="text-xs text-gray-400 font-medium italic mt-0.5">None configured</span>
              )}
            </div>
          </div>
        </div>
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
            currentlyDeployed={currentlyDeployed}
            onEdit={onEdit} 
            onDelete={onDelete} 
            onSetDeployed={handleSetDeployed}
          />
        </div>
      )}
    </div>
  );
}

