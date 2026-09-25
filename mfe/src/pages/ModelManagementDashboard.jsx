import React, { useState, useEffect } from 'react';
import ModelRegistrationForm from '../components/ModelRegistrationForm';
import ModelSearchForm from '../components/ModelSearchForm';
import ModelListTable from '../components/ModelListTable';
import { modelService } from '../services/modelService';

export default function ModelManagementDashboard() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasLoaded, setHasLoaded] = useState(false);
  
  const [currentOperation, setCurrentOperation] = useState('NONE'); // 'NONE', 'LIST', 'SEARCH'
  const [currentSearchQuery, setCurrentSearchQuery] = useState('');

  const [purposes, setPurposes] = useState([]);
  const [purposesLoading, setPurposesLoading] = useState(false);
  const [purposesError, setPurposesError] = useState(null);

  useEffect(() => {
    async function loadPurposes() {
      setPurposesLoading(true);
      try {
        const data = await modelService.getPurposes();
        setPurposes(data.purposes || []);
      } catch (err) {
        setPurposesError(err.message || 'Failed to load purposes');
      } finally {
        setPurposesLoading(false);
      }
    }
    loadPurposes();
  }, []);

  const handleListModels = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await modelService.listModels();
      setModels(data.models || []);
      setCurrentOperation('LIST');
      setHasLoaded(true);
    } catch (err) {
      setError(err.message || 'Failed to list models');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (purpose) => {
    setLoading(true);
    setError(null);
    setCurrentSearchQuery(purpose);
    try {
      const data = await modelService.findModelsByPurpose(purpose);
      setModels(data.models || []);
      setCurrentOperation('SEARCH');
      setHasLoaded(true);
    } catch (err) {
      setError(err.message || 'Failed to search models');
    } finally {
      setLoading(false);
    }
  };

  const handleClearSearch = () => {
    setModels([]);
    setCurrentOperation('NONE');
    setCurrentSearchQuery('');
    setHasLoaded(false);
    setError(null);
  };

  const handleUpdateModel = async (updateData) => {
    const data = await modelService.updateModel(updateData);
    if (data && data.model) {
      setModels(prev => prev.map(m => m.id === data.model.id ? data.model : m));
    }
  };

  const handleDeleteModel = async (name, version, dbId) => {
    await modelService.deleteModel(name, version, dbId);
    setModels(prev => prev.filter(m => !(m.name === name && m.version === version && m.id === dbId)));
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8 font-sans text-gray-900">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-extrabold text-gray-900 mb-8 tracking-tight">ML Model Management</h1>
        
        <ModelRegistrationForm />
        
        <ModelSearchForm 
          onSearch={handleSearch} 
          onClear={handleClearSearch} 
          loading={loading && currentOperation === 'SEARCH'}
          purposes={purposes}
          purposesLoading={purposesLoading}
          purposesError={purposesError}
        />
        
        <ModelListTable 
          models={models} 
          onListModels={handleListModels} 
          onUpdateModel={handleUpdateModel}
          onDeleteModel={handleDeleteModel}
          loading={loading && currentOperation === 'LIST'}
          error={error}
          hasLoaded={hasLoaded}
          operationType={currentOperation}
          searchQuery={currentSearchQuery}
        />
        
      </div>
    </div>
  );
}
