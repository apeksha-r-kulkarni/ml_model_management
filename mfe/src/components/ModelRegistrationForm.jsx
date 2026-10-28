import React, { useState, useRef, useEffect } from 'react';
import { MultiSelect } from 'primereact/multiselect';
import { modelService } from '../services/modelService';

const DEPLOYMENT_POINT_RULES = {
  'Speech': ['LID', 'ASR', 'Diarization', 'Speaker Identification'],
  'NER': ['Text Pipeline'],
  'File Classifier': ['UIS'],
};

export default function ModelRegistrationForm({ initialData }) {
  const [formData, setFormData] = useState({
    model_name: initialData?.model_name || '',
    model_type: initialData?.model_type || '',
    language: initialData?.language || '',
    new_language: '',
    environment: initialData?.environment || '',
    new_environment: '',
    architecture: '',
    new_architecture: '',
    framework: '',
    accuracy: '',
    priority: '',
    is_deployable: false,
    remarks: ''
  });

  const [selectedDeploymentPoints, setSelectedDeploymentPoints] = useState(() => {
    if (initialData?.deployment_points?.length) return initialData.deployment_points;
    if (initialData?.model_type === 'NER') return ['Text Pipeline'];
    if (initialData?.model_type === 'File Classifier') return ['UIS'];
    return [];
  });

  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // Detection state
  const [detectionInfo, setDetectionInfo] = useState(null);
  const [detectedFramework, setDetectedFramework] = useState('');
  
  // Master data lists
  const [architectures, setArchitectures] = useState([]);
  const [languages, setLanguages] = useState(['Kannada', 'Hindi', 'English']);
  const [environments, setEnvironments] = useState(['Indoor', 'Outdoor']);

  // Inline add new toggle state
  const [addingNewLang, setAddingNewLang] = useState(false);
  const [addingNewEnv, setAddingNewEnv] = useState(false);
  const [uploadMode, setUploadMode] = useState('file');

  const fileInputRef = useRef(null);

  useEffect(() => {
    const loadMetadata = async () => {
      try {
        const archRes = await modelService.getArchitectures();
        if (archRes && archRes.success) setArchitectures(archRes.architectures);

        const langRes = await modelService.getLanguages();
        if (langRes && langRes.success && langRes.languages.length > 0) {
          setLanguages(langRes.languages);
        }

        const envRes = await modelService.getEnvironments();
        if (envRes && envRes.success && envRes.environments.length > 0) {
          setEnvironments(envRes.environments);
        }
      } catch (err) {
        console.error("Failed to load metadata", err);
      }
    };
    loadMetadata();
  }, []);

  useEffect(() => {
    if (initialData) {
      const validDps = DEPLOYMENT_POINT_RULES[initialData.model_type] || [];
      let initialDps = (initialData.deployment_points || []).filter(dp => validDps.includes(dp));
      
      if (!initialDps.length) {
        if (initialData.model_type === 'NER') initialDps = ['Text Pipeline'];
        if (initialData.model_type === 'File Classifier') initialDps = ['UIS'];
      }

      setFormData(prev => ({
        ...prev,
        model_name: initialData.model_name || prev.model_name,
        model_type: initialData.model_type || prev.model_type,
        language: initialData.model_type === 'Speech' ? (initialData.language || '') : '',
        environment: initialData.model_type === 'Speech' ? (initialData.environment || '') : '',
      }));
      setSelectedDeploymentPoints(initialDps);
    }
  }, [initialData]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    if (name === 'model_type') {
      let autoDps = [];
      if (value === 'NER') autoDps = ['Text Pipeline'];
      if (value === 'File Classifier') autoDps = ['UIS'];

      setSelectedDeploymentPoints(autoDps);

      setFormData(prev => ({
        ...prev,
        model_type: value,
        language: '',
        new_language: '',
        environment: '',
        new_environment: ''
      }));
      setAddingNewLang(false);
      setAddingNewEnv(false);
      return;
    }

    if (name === 'language') {
      if (value === '__ADD_NEW__') {
        setAddingNewLang(true);
        setFormData(prev => ({ ...prev, language: '__ADD_NEW__', new_language: '' }));
      } else {
        setAddingNewLang(false);
        setFormData(prev => ({ ...prev, language: value, new_language: '' }));
      }
      return;
    }

    if (name === 'environment') {
      if (value === '__ADD_NEW__') {
        setAddingNewEnv(true);
        setFormData(prev => ({ ...prev, environment: '__ADD_NEW__', new_environment: '' }));
      } else {
        setAddingNewEnv(false);
        setFormData(prev => ({ ...prev, environment: value, new_environment: '' }));
      }
      return;
    }

    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleAddNewLangSave = () => {
    const val = formData.new_language.trim();
    if (!val) return;

    if (languages.some(l => l.toLowerCase() === val.toLowerCase())) {
      setError(`Language "${val}" already exists.`);
      return;
    }

    setLanguages(prev => [...prev, val]);
    setFormData(prev => ({ ...prev, language: val, new_language: '' }));
    setAddingNewLang(false);
    setError(null);
  };

  const handleAddNewEnvSave = () => {
    const val = formData.new_environment.trim();
    if (!val) return;

    if (environments.some(e => e.toLowerCase() === val.toLowerCase())) {
      setError(`Environment "${val}" already exists.`);
      return;
    }

    setEnvironments(prev => [...prev, val]);
    setFormData(prev => ({ ...prev, environment: val, new_environment: '' }));
    setAddingNewEnv(false);
    setError(null);
  };

  const handleFileChange = async (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFiles = Array.from(e.target.files);
      setFile(selectedFiles);
      setDetectionInfo(null);
      setDetectedFramework('');
      setFormData(prev => ({ ...prev, framework: '' }));

      // Build small formData with config/meta files to inspect
      const inspectData = new FormData();
      let hasInspectionFiles = false;

      selectedFiles.forEach(f => {
        const path = f.webkitRelativePath || f.name;
        const lower = path.toLowerCase();
        // Send small configuration and metadata files
        if (lower.endsWith('meta.json') || lower.endsWith('config.cfg') || lower.endsWith('config.json') || lower.endsWith('saved_model.pb') || lower.endsWith('.onnx') || lower.endsWith('.pt') || lower.endsWith('.h5') || lower.endsWith('.hdf5')) {
          inspectData.append('model_files', f);
          inspectData.append('model_paths', path);
          hasInspectionFiles = true;
        }
      });

      if (hasInspectionFiles) {
        try {
          const res = await modelService.inspectArtifact(inspectData);
          if (res && res.success && res.detection) {
            const det = res.detection;
            setDetectionInfo(det);

            if (det.detected && det.supported) {
              setDetectedFramework(det.framework || '');

              // Auto-set model_type to NER if not pre-locked
              if (det.model_type) {
                setFormData(prev => ({
                  ...prev,
                  model_type: prev.model_type || det.model_type,
                  architecture: det.architecture || prev.architecture
                }));

                // Auto-configure deployment points for NER
                if (det.model_type === 'NER') {
                  setSelectedDeploymentPoints(['Text Pipeline']);
                }
              }

              // If architecture detected, ensure it's in the dropdown options
              if (det.architecture) {
                setArchitectures(prev => prev.includes(det.architecture) ? prev : [...prev, det.architecture]);
                setFormData(prev => ({
                  ...prev,
                  architecture: det.architecture
                }));
              }
            } else if (det.detected && !det.supported) {
              setDetectedFramework(det.framework || '');
            }
          }
        } catch (inspectErr) {
          console.error("Artifact inspection failed:", inspectErr);
        }
      }
    } else {
      setFile(null);
      setDetectionInfo(null);
      setDetectedFramework('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Validation
    if (!formData.model_name.trim()) {
      setError("Model Name is required.");
      return;
    }

    if (!formData.model_type) {
      setError("Model Type is required.");
      return;
    }

    if (formData.model_type === 'Speech') {
      const finalLang = formData.language === '__ADD_NEW__' ? formData.new_language.trim() : formData.language.trim();
      if (!finalLang) {
        setError("Language is required for Speech models.");
        return;
      }
      const finalEnv = formData.environment === '__ADD_NEW__' ? formData.new_environment.trim() : formData.environment.trim();
      if (!finalEnv) {
        setError("Environment is required for Speech models.");
        return;
      }
    }

    if (formData.accuracy !== '') {
      const acc = parseFloat(formData.accuracy);
      if (isNaN(acc) || acc < 0 || acc > 100) {
        setError("Accuracy must be a number between 0 and 100.");
        return;
      }
    }

    if (!file || file.length === 0) {
      setError("Model file or folder is required.");
      return;
    }

    const finalFramework = detectedFramework || formData.framework;
    if (!finalFramework) {
      setError("Framework must be selected when detection fails.");
      return;
    }

    setLoading(true);

    try {
      const submitData = new FormData();
      submitData.append('model_name', formData.model_name.trim());
      submitData.append('model_type', formData.model_type);
      if (finalFramework) {
        submitData.append('framework', finalFramework);
      }

      if (formData.model_type === 'Speech') {
        const finalLang = formData.language === '__ADD_NEW__' ? formData.new_language.trim() : formData.language.trim();
        const finalEnv = formData.environment === '__ADD_NEW__' ? formData.new_environment.trim() : formData.environment.trim();
        submitData.append('language', finalLang);
        submitData.append('environment', finalEnv);
      }

      submitData.append('accuracy', formData.accuracy);
      submitData.append('priority', formData.priority);
      submitData.append('is_deployable', formData.is_deployable ? 'true' : 'false');
      
      // Filter out stale deployment points before submitting
      const allowedDps = DEPLOYMENT_POINT_RULES[formData.model_type] || [];
      const validSubmittedDps = selectedDeploymentPoints.filter(dp => allowedDps.includes(dp));
      
      validSubmittedDps.forEach(dp => {
        submitData.append('deployment_points', dp);
      });
      submitData.append('remarks', formData.remarks);
      
      const finalArch = formData.architecture === '__ADD_NEW__' ? formData.new_architecture : formData.architecture;
      submitData.append('architecture', finalArch);

      file.forEach(f => {
        submitData.append('model_files', f);
        submitData.append('model_paths', f.webkitRelativePath || f.name);
      });

      await modelService.registerModel(submitData);
      
      setSuccess("Model version uploaded and registered successfully.");
      
      // Reset form
      setFormData({
        model_name: '',
        model_type: '',
        language: '',
        new_language: '',
        environment: '',
        new_environment: '',
        architecture: '',
        new_architecture: '',
        framework: '',
        accuracy: '',
        priority: '',
        is_deployable: false,
        remarks: ''
      });
      setSelectedDeploymentPoints([]);
      setAddingNewLang(false);
      setAddingNewEnv(false);
      setFile(null);
      setDetectionInfo(null);
      setDetectedFramework('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      setError(err.message || "Failed to register model.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white shadow-sm rounded-lg border border-gray-200 p-6 mb-6">
      <h2 className="text-xl font-bold text-gray-800 mb-4">
        {initialData?.model_name ? `Register New Version for "${initialData.model_name}"` : 'Register New Model'}
      </h2>
      
      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 border border-red-200 rounded-md text-sm">
          {error}
        </div>
      )}
      
      {success && (
        <div className="mb-4 p-3 bg-green-50 text-green-700 border border-green-200 rounded-md text-sm">
          {success}
        </div>
      )}

      {detectionInfo && (
        <div className={`mb-4 p-3 rounded-md border text-sm ${
          detectionInfo.detected && detectionInfo.supported
            ? 'bg-blue-50 text-blue-800 border-blue-200'
            : detectionInfo.detected && !detectionInfo.supported
              ? 'bg-amber-50 text-amber-800 border-amber-200'
              : 'bg-gray-50 text-gray-700 border-gray-200'
        }`}>
          <div className="flex items-center space-x-2">
            <span className="font-bold">
              {detectionInfo.detected && detectionInfo.supported ? '✓ Framework & Architecture Detected' :
               detectionInfo.detected && !detectionInfo.supported ? '⚠️ Unsupported Model / Framework' :
               'ℹ Artifact Inspection'}
            </span>
            {detectionInfo.framework && (
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-white border shadow-2xs">
                {detectionInfo.framework}
              </span>
            )}
            {detectionInfo.architecture && (
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-white border shadow-2xs">
                Arch: {detectionInfo.architecture}
              </span>
            )}
          </div>
          <p className="mt-1 text-xs">{detectionInfo.reason}</p>
        </div>
      )}

      <form className="grid grid-cols-1 md:grid-cols-2 gap-4" onSubmit={handleSubmit}>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Model Name (Identity):</label>
          <input 
            type="text" 
            name="model_name"
            value={formData.model_name}
            onChange={handleChange}
            disabled={!!initialData?.model_name}
            className={`w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500 ${initialData?.model_name ? 'bg-gray-100 cursor-not-allowed' : ''}`}
            placeholder="e.g. SpeechCommandModel" 
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Model Type:</label>
          <select 
            name="model_type"
            value={formData.model_type}
            onChange={handleChange}
            disabled={!!initialData?.model_type}
            className={`w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500 ${initialData?.model_type ? 'bg-gray-100 cursor-not-allowed' : ''}`}
          >
            <option value="">Select...</option>
            <option value="Speech">Speech</option>
            <option value="NER">NER</option>
            <option value="File Classifier">File Classifier</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Framework *:</label>
          {detectedFramework ? (
            <input 
              type="text" 
              value={detectedFramework} 
              disabled 
              className="w-full p-2 border border-gray-300 rounded bg-gray-100 cursor-not-allowed" 
            />
          ) : (
            <select
              name="framework"
              value={formData.framework}
              onChange={handleChange}
              className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select Framework...</option>
              <option value="spaCy">spaCy</option>
              <option value="Hugging Face">Hugging Face</option>
            </select>
          )}
        </div>

        {/* Dynamic Fields for Speech */}
        {formData.model_type === 'Speech' && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Language *:</label>
              <select
                name="language"
                value={formData.language}
                onChange={handleChange}
                className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select Language...</option>
                {languages.map(lang => (
                  <option key={lang} value={lang}>{lang}</option>
                ))}
                <option value="__ADD_NEW__">+ Add New Language</option>
              </select>
              
              {addingNewLang && (
                <div className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded-md">
                  <label className="block text-xs font-semibold text-gray-600 mb-1">New Language Name:</label>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      name="new_language"
                      value={formData.new_language}
                      onChange={handleChange}
                      placeholder="e.g. Tamil"
                      className="flex-1 p-1.5 text-sm border border-gray-300 rounded"
                    />
                    <button
                      type="button"
                      onClick={handleAddNewLangSave}
                      className="px-3 py-1.5 bg-blue-600 text-white text-xs font-semibold rounded hover:bg-blue-700"
                    >
                      Add
                    </button>
                    <button
                      type="button"
                      onClick={() => { setAddingNewLang(false); setFormData(p => ({ ...p, language: '', new_language: '' })); }}
                      className="px-3 py-1.5 bg-gray-200 text-gray-700 text-xs font-semibold rounded hover:bg-gray-300"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Environment *:</label>
              <select
                name="environment"
                value={formData.environment}
                onChange={handleChange}
                className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select Environment...</option>
                {environments.map(env => (
                  <option key={env} value={env}>{env}</option>
                ))}
                <option value="__ADD_NEW__">+ Add New Environment</option>
              </select>

              {addingNewEnv && (
                <div className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded-md">
                  <label className="block text-xs font-semibold text-gray-600 mb-1">New Environment Name:</label>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      name="new_environment"
                      value={formData.new_environment}
                      onChange={handleChange}
                      placeholder="e.g. In-Vehicle"
                      className="flex-1 p-1.5 text-sm border border-gray-300 rounded"
                    />
                    <button
                      type="button"
                      onClick={handleAddNewEnvSave}
                      className="px-3 py-1.5 bg-blue-600 text-white text-xs font-semibold rounded hover:bg-blue-700"
                    >
                      Add
                    </button>
                    <button
                      type="button"
                      onClick={() => { setAddingNewEnv(false); setFormData(p => ({ ...p, environment: '', new_environment: '' })); }}
                      className="px-3 py-1.5 bg-gray-200 text-gray-700 text-xs font-semibold rounded hover:bg-gray-300"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Architecture:</label>
          <select 
            name="architecture"
            value={formData.architecture}
            onChange={handleChange}
            className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Select...</option>
            {architectures.map(arch => (
              <option key={arch} value={arch}>{arch}</option>
            ))}
            <option value="__ADD_NEW__">+ Add New Architecture</option>
          </select>
          {formData.architecture === '__ADD_NEW__' && (
            <input 
              type="text" 
              name="new_architecture"
              value={formData.new_architecture}
              onChange={handleChange}
              placeholder="Enter new architecture" 
              className="mt-2 w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" 
            />
          )}
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Accuracy (0-100):</label>
          <input 
            type="number" 
            name="accuracy"
            value={formData.accuracy}
            onChange={handleChange}
            step="0.01" 
            min="0"
            max="100"
            className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" 
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Priority:</label>
          <input 
            type="number" 
            name="priority"
            value={formData.priority}
            onChange={handleChange}
            className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" 
            placeholder="e.g. 1" 
          />
        </div>
        
        {formData.model_type && DEPLOYMENT_POINT_RULES[formData.model_type] && (
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Deployment Points:
            </label>
            <MultiSelect
              value={selectedDeploymentPoints}
              options={DEPLOYMENT_POINT_RULES[formData.model_type].map(dp => ({ label: dp, value: dp }))}
              onChange={(e) => setSelectedDeploymentPoints(e.value || [])}
              optionLabel="label"
              placeholder="Select Deployment Points..."
              display="chip"
              disabled={formData.model_type === 'NER' || formData.model_type === 'File Classifier'}
              className="w-full border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        )}

        <div className="md:col-span-2">
          <label className="flex items-center space-x-2 text-sm font-medium text-gray-700 cursor-pointer w-fit">
            <input 
              type="checkbox" 
              name="is_deployable"
              checked={formData.is_deployable}
              onChange={handleChange}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" 
            />
            <span>Is Deployable Ready?</span>
          </label>
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Remarks:</label>
          <textarea 
            name="remarks"
            value={formData.remarks}
            onChange={handleChange}
            className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" 
            rows="3"
          ></textarea>
        </div>
        
        <div className="md:col-span-2 mb-2">
          <span className="block text-sm font-medium text-gray-700 mb-1">Upload Mode:</span>
          <label className="mr-4 inline-flex items-center">
            <input type="radio" value="file" checked={uploadMode === 'file'} onChange={() => { setUploadMode('file'); setFile(null); if(fileInputRef.current) fileInputRef.current.value = ''; }} className="mr-1" />
            Single File (.pt, .onnx)
          </label>
          <label className="inline-flex items-center">
            <input type="radio" value="folder" checked={uploadMode === 'folder'} onChange={() => { setUploadMode('folder'); setFile(null); if(fileInputRef.current) fileInputRef.current.value = ''; }} className="mr-1" />
            Folder (multiple files)
          </label>
        </div>
        
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {uploadMode === 'folder' ? 'Model Folder (containing .pt/.onnx and configs):' : 'Model File (.pt, .onnx):'}
          </label>
          {uploadMode === 'folder' ? (
            <input 
              type="file" 
              webkitdirectory="true"
              directory="true"
              multiple
              onChange={handleFileChange}
              ref={fileInputRef}
              className="w-full p-2 border border-gray-300 rounded bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500" 
            />
          ) : (
            <input 
              type="file" 
              accept=".pt,.onnx"
              onChange={handleFileChange}
              ref={fileInputRef}
              className="w-full p-2 border border-gray-300 rounded bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500" 
            />
          )}
        </div>

        <div className="md:col-span-2 mt-2">
          <button 
            type="submit" 
            disabled={loading}
            className={`px-4 py-2 font-medium rounded-md transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
              ${loading 
                ? 'bg-blue-400 cursor-not-allowed text-white' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
          >
            {loading ? 'Uploading & Registering...' : 'Upload & Register'}
          </button>
        </div>
      </form>
    </div>
  );
}

