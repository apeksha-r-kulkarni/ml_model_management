import React from 'react';

export default function ModelVersionList({ versions, currentlyDeployed, onEdit, onDelete, onSetDeployed }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm bg-white">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-gray-100/80 border-b border-gray-200 text-xs text-gray-600 uppercase tracking-wider">
            <th className="p-3.5 font-semibold">Version</th>
            <th className="p-3.5 font-semibold">Status</th>
            <th className="p-3.5 font-semibold">Architecture</th>
            <th className="p-3.5 font-semibold">Language/Env</th>
            <th className="p-3.5 font-semibold">Accuracy</th>
            <th className="p-3.5 font-semibold">Priority</th>
            <th className="p-3.5 font-semibold">Deployable</th>
            <th className="p-3.5 font-semibold">Deployment Points</th>
            <th className="p-3.5 font-semibold">Remarks</th>
            <th className="p-3.5 font-semibold text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 text-sm">
          {versions.map((v, idx) => {
            const isLatest = idx === 0;

            return (
              <tr key={v.id || idx} className="hover:bg-blue-50/30 transition-colors">
                <td className="p-3.5 font-bold text-gray-900 whitespace-nowrap">
                  v{v.version}
                </td>
                <td className="p-3.5 whitespace-nowrap space-x-1">
                  {isLatest && (
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-800">
                      LATEST
                    </span>
                  )}
                  {v.is_deployable && (
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-gray-100 text-gray-500 border border-gray-200">
                      DEPLOYABLE
                    </span>
                  )}
                </td>
                <td className="p-3.5 text-gray-700">{v.architecture || '-'}</td>
                <td className="p-3.5 text-gray-700 text-xs">
                  {v.language || v.environment ? (
                    <span>
                      {v.language && <span className="font-medium text-gray-900">{v.language}</span>}
                      {v.language && v.environment && ' / '}
                      {v.environment && <span className="text-gray-600">{v.environment}</span>}
                    </span>
                  ) : '-'}
                </td>
                <td className="p-3.5 text-gray-700 font-mono text-xs">{v.accuracy || '0.0'}</td>
                <td className="p-3.5 text-gray-700">{v.priority ?? '-'}</td>
                <td className="p-3.5">
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${v.is_deployable ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                    {v.is_deployable ? 'Yes' : 'No'}
                  </span>
                </td>
                <td className="p-3.5 text-gray-600 text-xs">
                  {v.deployment_points && v.deployment_points.length > 0 ? (
                    <div className="flex flex-col space-y-1">
                      {v.deployment_points.map(dp => {
                        const isDpDeployed = currentlyDeployed && currentlyDeployed[dp] === v.version;
                        if (isDpDeployed) {
                           return (
                             <span key={dp} className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-600 text-white shadow-sm inline-block w-max">
                               DEPLOYED: {dp}
                             </span>
                           );
                        } else {
                           return (
                             <span key={dp} className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-50 text-gray-500 border border-gray-100 inline-block w-max">
                               {dp}
                             </span>
                           );
                        }
                      })}
                    </div>
                  ) : '-'}
                </td>
                <td className="p-3.5 text-gray-600 text-xs max-w-[150px] truncate" title={v.remarks}>
                  {v.remarks || '-'}
                </td>
                <td className="p-3.5 text-right space-x-3 whitespace-nowrap">
                  <button 
                    onClick={() => onEdit(v)} 
                    className="text-blue-600 hover:text-blue-800 font-medium text-xs border border-transparent hover:border-blue-200 px-2 py-1 rounded transition-colors"
                  >
                    Edit
                  </button>
                  <button 
                    onClick={() => onDelete(v)} 
                    className="text-red-600 hover:text-red-800 font-medium text-xs border border-transparent hover:border-red-200 px-2 py-1 rounded transition-colors"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

