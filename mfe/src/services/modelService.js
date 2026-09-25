async function handleResponse(response) {
  // 1. Detect HTTP failures (e.g. 404, 500)
  if (!response.ok) {
    // Attempt to parse JSON error message if provided
    let errorMessage = `HTTP error! status: ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.error) {
        errorMessage = errorData.error;
      }
    } catch (e) {
      // Ignore JSON parse errors for non-JSON responses
    }
    throw new Error(errorMessage);
  }

  // 2. Parse JSON response
  const data = await response.json();

  // 3. Detect internal success: false responses
  if (data.success === false) {
    throw new Error(data.error || 'Unknown backend error');
  }

  return data;
}

export const modelService = {
  // POST /api/models/register/
  registerModel: async (formData) => {
    const response = await fetch('/api/models/register/', {
      method: 'POST',
      body: formData,
      // Do NOT set Content-Type header! Browser auto-generates it with boundary
    });
    return handleResponse(response);
  },

  // GET /api/models/
  listModels: async () => {
    const response = await fetch('/api/models/', {
      method: 'GET',
    });
    return handleResponse(response);
  },

  // GET /api/models/find/?purpose={val}
  findModelsByPurpose: async (purpose) => {
    const encodedPurpose = encodeURIComponent(purpose);
    const response = await fetch(`/api/models/find/?purpose=${encodedPurpose}`, {
      method: 'GET',
    });
    return handleResponse(response);
  },

  // GET /api/models/purposes/
  getPurposes: async () => {
    const response = await fetch('/api/models/purposes/', {
      method: 'GET',
    });
    return handleResponse(response);
  },

  // GET /api/models/architectures/
  getArchitectures: async () => {
    const response = await fetch('/api/models/architectures/', {
      method: 'GET',
    });
    return handleResponse(response);
  },

  // GET /api/models/languages/
  getLanguages: async () => {
    const response = await fetch('/api/models/languages/', {
      method: 'GET',
    });
    return handleResponse(response);
  },

  // GET /api/models/environments/
  getEnvironments: async () => {
    const response = await fetch('/api/models/environments/', {
      method: 'GET',
    });
    return handleResponse(response);
  },


  // PUT /api/models/update/
  updateModel: async (data) => {
    const response = await fetch('/api/models/update/', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  // POST /api/models/set-deployed/
  setDeployedVersion: async (name, version) => {
    const response = await fetch('/api/models/set-deployed/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, version }),
    });
    return handleResponse(response);
  },

  // DELETE /api/models/{name}/version/{version}/
  deleteModel: async (name, version, dbId) => {
    const encodedName = encodeURIComponent(name);
    const encodedVersion = encodeURIComponent(version);
    const response = await fetch(`/api/models/${encodedName}/version/${encodedVersion}/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ db_id: dbId }),
    });
    return handleResponse(response);
  }
};

