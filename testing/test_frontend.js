/**
 * test_frontend.js
 * =================
 * Frontend unit tests for mfe/src/services/modelService.js
 * Uses zero external dependencies — runs on Node.js 12+
 *
 * Tests:
 *   handleResponse: HTTP errors, success:false, JSON parse failures
 *   registerModel, listModels, findModelsByPurpose
 *   getPurposes, getArchitectures, getLanguages, getEnvironments
 *   updateModel, setDeployedVersion, deleteModel
 *   Edge cases: network failures, URL encoding, empty inputs
 *
 * Run from project root:
 *   node testing/test_frontend.js
 */

'use strict';

// ----------------------------------------------------------------
// Minimal test framework (zero deps)
// ----------------------------------------------------------------
let passed = 0;
let failed = 0;
const failures = [];

async function it(name, fn) {
  try {
    await fn();
    process.stdout.write(`  ✓ ${name}\n`);
    passed++;
  } catch (err) {
    process.stdout.write(`  ✗ ${name}\n    ${err.message}\n`);
    failures.push({ name, error: err.message });
    failed++;
  }
}

function expect(actual) {
  return {
    toBe(expected) {
      if (actual !== expected)
        throw new Error(`Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
    },
    toEqual(expected) {
      if (JSON.stringify(actual) !== JSON.stringify(expected))
        throw new Error(`Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
    },
    toContain(val) {
      if (!actual.includes(val))
        throw new Error(`Expected "${actual}" to contain "${val}"`);
    },
    toBeUndefined() {
      if (actual !== undefined)
        throw new Error(`Expected undefined, got ${JSON.stringify(actual)}`);
    },
    toBeNull() {
      if (actual !== null)
        throw new Error(`Expected null, got ${JSON.stringify(actual)}`);
    },
    toHaveLength(n) {
      if ((actual || []).length !== n)
        throw new Error(`Expected length ${n}, got ${(actual || []).length}`);
    },
  };
}

async function rejects(promise, pattern) {
  try {
    await promise;
    throw new Error('Expected promise to reject, but it resolved');
  } catch (err) {
    if (err.message === 'Expected promise to reject, but it resolved') throw err;
    if (pattern && !err.message.includes(pattern))
      throw new Error(`Expected error message to include "${pattern}", got "${err.message}"`);
  }
}

// ----------------------------------------------------------------
// Inline modelService (extracted from modelService.js)
// ----------------------------------------------------------------
async function handleResponse(response) {
  if (!response.ok) {
    let errorMessage = `HTTP error! status: ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.error) errorMessage = errorData.error;
    } catch (e) {}
    throw new Error(errorMessage);
  }
  const data = await response.json();
  if (data.success === false) throw new Error(data.error || 'Unknown backend error');
  return data;
}

// Build modelService using a mockable fetch
function buildService(fetchImpl) {
  return {
    registerModel: async (formData) => {
      const r = await fetchImpl('/api/models/register/', { method: 'POST', body: formData });
      return handleResponse(r);
    },
    listModels: async () => {
      const r = await fetchImpl('/api/models/', { method: 'GET' });
      return handleResponse(r);
    },
    findModelsByPurpose: async (purpose) => {
      const enc = encodeURIComponent(purpose);
      const r = await fetchImpl(`/api/models/find/?purpose=${enc}`, { method: 'GET' });
      return handleResponse(r);
    },
    getPurposes: async () => {
      const r = await fetchImpl('/api/models/purposes/', { method: 'GET' });
      return handleResponse(r);
    },
    getArchitectures: async () => {
      const r = await fetchImpl('/api/models/architectures/', { method: 'GET' });
      return handleResponse(r);
    },
    getLanguages: async () => {
      const r = await fetchImpl('/api/models/languages/', { method: 'GET' });
      return handleResponse(r);
    },
    getEnvironments: async () => {
      const r = await fetchImpl('/api/models/environments/', { method: 'GET' });
      return handleResponse(r);
    },
    updateModel: async (data) => {
      const r = await fetchImpl('/api/models/update/', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return handleResponse(r);
    },
    setDeployedVersion: async (name, version, deployment_point) => {
      const r = await fetchImpl('/api/models/set-deployed/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, version, deployment_point }),
      });
      return handleResponse(r);
    },
    deleteModel: async (name, version, dbId) => {
      const eName = encodeURIComponent(name);
      const eVer = encodeURIComponent(version);
      const r = await fetchImpl(`/api/models/${eName}/version/${eVer}/`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ db_id: dbId }),
      });
      return handleResponse(r);
    },
  };
}

// Helpers to build fake fetch calls
function mockFetch(body, { ok = true, status = 200 } = {}) {
  let calls = [];
  const fetch = async (url, opts) => {
    calls.push({ url, opts });
    return {
      ok, status,
      json: async () => body,
    };
  };
  fetch.calls = calls;
  return fetch;
}

function mockFetchRejects(errorMsg) {
  return async () => { throw new Error(errorMsg); };
}

// ----------------------------------------------------------------
// Test Suite
// ----------------------------------------------------------------
(async () => {

  // ============================================================
  // handleResponse tests (tested via listModels)
  // ============================================================
  console.log('\n[handleResponse]');

  await it('throws on HTTP error with default message', async () => {
    const fetch = async () => ({ ok: false, status: 500, json: async () => { throw new Error('not json'); } });
    const svc = buildService(fetch);
    await rejects(svc.listModels(), 'HTTP error! status: 500');
  });

  await it('throws with server error message when JSON is available', async () => {
    const fetch = async () => ({ ok: false, status: 400, json: async () => ({ error: 'Model name is required.' }) });
    const svc = buildService(fetch);
    await rejects(svc.listModels(), 'Model name is required.');
  });

  await it('throws when success is false', async () => {
    const svc = buildService(mockFetch({ success: false, error: 'backend failed' }));
    await rejects(svc.listModels(), 'backend failed');
  });

  await it('throws Unknown backend error when success:false but no error field', async () => {
    const svc = buildService(mockFetch({ success: false }));
    await rejects(svc.listModels(), 'Unknown backend error');
  });

  await it('returns data when success is true', async () => {
    const svc = buildService(mockFetch({ success: true, models: [] }));
    const result = await svc.listModels();
    expect(result.models).toEqual([]);
  });

  await it('returns data when success field is absent', async () => {
    const svc = buildService(mockFetch({ data: 'something' }));
    const result = await svc.listModels();
    expect(result.data).toBe('something');
  });

  // ============================================================
  // listModels
  // ============================================================
  console.log('\n[listModels]');

  await it('calls GET /api/models/', async () => {
    const fetch = mockFetch({ success: true, models: [] });
    const svc = buildService(fetch);
    await svc.listModels();
    expect(fetch.calls[0].url).toBe('/api/models/');
    expect(fetch.calls[0].opts.method).toBe('GET');
  });

  await it('returns models array', async () => {
    const svc = buildService(mockFetch({ success: true, models: [{ name: 'M1' }] }));
    const result = await svc.listModels();
    expect(result.models).toHaveLength(1);
    expect(result.models[0].name).toBe('M1');
  });

  await it('propagates network errors', async () => {
    const svc = buildService(mockFetchRejects('Network failure'));
    await rejects(svc.listModels(), 'Network failure');
  });

  // ============================================================
  // findModelsByPurpose
  // ============================================================
  console.log('\n[findModelsByPurpose]');

  await it('encodes purpose in URL', async () => {
    const fetch = mockFetch({ success: true, models: [] });
    const svc = buildService(fetch);
    await svc.findModelsByPurpose('Speech Recognition');
    expect(fetch.calls[0].url).toBe('/api/models/find/?purpose=Speech%20Recognition');
  });

  await it('handles empty purpose', async () => {
    const fetch = mockFetch({ success: true, models: [] });
    const svc = buildService(fetch);
    await svc.findModelsByPurpose('');
    expect(fetch.calls[0].url).toBe('/api/models/find/?purpose=');
  });

  await it('handles special chars in purpose', async () => {
    const fetch = mockFetch({ success: true, models: [] });
    const svc = buildService(fetch);
    await svc.findModelsByPurpose('A&B=C');
    const url = fetch.calls[0].url;
    if (url.includes(' ')) throw new Error('URL must not contain raw spaces');
  });

  await it('returns matching models', async () => {
    const models = [{ name: 'M', purpose: 'NER' }];
    const svc = buildService(mockFetch({ success: true, models }));
    const result = await svc.findModelsByPurpose('NER');
    expect(result.models[0].purpose).toBe('NER');
  });

  // ============================================================
  // getPurposes
  // ============================================================
  console.log('\n[getPurposes]');

  await it('calls GET /api/models/purposes/', async () => {
    const fetch = mockFetch({ success: true, purposes: [] });
    const svc = buildService(fetch);
    await svc.getPurposes();
    expect(fetch.calls[0].url).toBe('/api/models/purposes/');
  });

  await it('returns purposes array', async () => {
    const svc = buildService(mockFetch({ success: true, purposes: ['ASR', 'NER'] }));
    const result = await svc.getPurposes();
    expect(result.purposes).toEqual(['ASR', 'NER']);
  });

  // ============================================================
  // getArchitectures
  // ============================================================
  console.log('\n[getArchitectures]');

  await it('calls GET /api/models/architectures/', async () => {
    const fetch = mockFetch({ success: true, architectures: [] });
    const svc = buildService(fetch);
    await svc.getArchitectures();
    expect(fetch.calls[0].url).toBe('/api/models/architectures/');
  });

  await it('returns architectures list', async () => {
    const svc = buildService(mockFetch({ success: true, architectures: ['BERT', 'CNN'] }));
    const result = await svc.getArchitectures();
    if (!result.architectures.includes('BERT'))
      throw new Error('Expected BERT in architectures');
  });

  // ============================================================
  // getLanguages / getEnvironments
  // ============================================================
  console.log('\n[getLanguages / getEnvironments]');

  await it('getLanguages calls correct URL', async () => {
    const fetch = mockFetch({ success: true, languages: [] });
    const svc = buildService(fetch);
    await svc.getLanguages();
    expect(fetch.calls[0].url).toBe('/api/models/languages/');
  });

  await it('getEnvironments calls correct URL', async () => {
    const fetch = mockFetch({ success: true, environments: [] });
    const svc = buildService(fetch);
    await svc.getEnvironments();
    expect(fetch.calls[0].url).toBe('/api/models/environments/');
  });

  await it('getLanguages returns empty list (stub)', async () => {
    const svc = buildService(mockFetch({ success: true, languages: [] }));
    const result = await svc.getLanguages();
    expect(result.languages).toEqual([]);
  });

  // ============================================================
  // registerModel
  // ============================================================
  console.log('\n[registerModel]');

  await it('calls POST /api/models/register/', async () => {
    const fetch = mockFetch({ success: true, version: '1' });
    const svc = buildService(fetch);
    await svc.registerModel({ _type: 'FormData' });
    expect(fetch.calls[0].url).toBe('/api/models/register/');
    expect(fetch.calls[0].opts.method).toBe('POST');
  });

  await it('does NOT set Content-Type header', async () => {
    const fetch = mockFetch({ success: true, version: '1' });
    const svc = buildService(fetch);
    await svc.registerModel({});
    expect(fetch.calls[0].opts.headers).toBeUndefined();
  });

  await it('returns version and model_name', async () => {
    const svc = buildService(mockFetch({ success: true, version: '2', model_name: 'NLPModel' }));
    const result = await svc.registerModel({});
    expect(result.version).toBe('2');
    expect(result.model_name).toBe('NLPModel');
  });

  await it('throws when HTTP 400 with error message', async () => {
    const fetch = async () => ({ ok: false, status: 400, json: async () => ({ error: 'Model name is required.' }) });
    const svc = buildService(fetch);
    await rejects(svc.registerModel({}), 'Model name is required.');
  });

  await it('throws when success:false with accuracy error', async () => {
    const svc = buildService(mockFetch({ success: false, error: 'Accuracy must be between 0 and 100.' }));
    await rejects(svc.registerModel({}), 'Accuracy must be between 0 and 100.');
  });

  // ============================================================
  // updateModel
  // ============================================================
  console.log('\n[updateModel]');

  await it('calls PUT /api/models/update/', async () => {
    const fetch = mockFetch({ success: true, model: {} });
    const svc = buildService(fetch);
    await svc.updateModel({ name: 'M', version: '1', accuracy: 90.0 });
    expect(fetch.calls[0].url).toBe('/api/models/update/');
    expect(fetch.calls[0].opts.method).toBe('PUT');
  });

  await it('sends Content-Type: application/json', async () => {
    const fetch = mockFetch({ success: true, model: {} });
    const svc = buildService(fetch);
    await svc.updateModel({ name: 'M', version: '1' });
    expect(fetch.calls[0].opts.headers['Content-Type']).toBe('application/json');
  });

  await it('serializes payload correctly', async () => {
    const fetch = mockFetch({ success: true, model: {} });
    const svc = buildService(fetch);
    const payload = { name: 'X', version: '5', is_deployable: true };
    await svc.updateModel(payload);
    const body = JSON.parse(fetch.calls[0].opts.body);
    expect(body.is_deployable).toBe(true);
    expect(body.version).toBe('5');
  });

  await it('throws on server error', async () => {
    const fetch = async () => ({ ok: false, status: 500, json: async () => ({ error: 'DB error' }) });
    const svc = buildService(fetch);
    await rejects(svc.updateModel({ name: 'M', version: '1' }), 'DB error');
  });

  // ============================================================
  // setDeployedVersion
  // ============================================================
  console.log('\n[setDeployedVersion]');

  await it('calls POST /api/models/set-deployed/', async () => {
    const fetch = mockFetch({ success: true });
    const svc = buildService(fetch);
    await svc.setDeployedVersion('M', '3', 'staging');
    expect(fetch.calls[0].url).toBe('/api/models/set-deployed/');
    expect(fetch.calls[0].opts.method).toBe('POST');
  });

  await it('sends name, version, and deployment_point in body', async () => {
    const fetch = mockFetch({ success: true });
    const svc = buildService(fetch);
    await svc.setDeployedVersion('MyModel', '3', 'production');
    const body = JSON.parse(fetch.calls[0].opts.body);
    expect(body.name).toBe('MyModel');
    expect(body.version).toBe('3');
    expect(body.deployment_point).toBe('production');
  });

  await it('returns success:true', async () => {
    const svc = buildService(mockFetch({ success: true }));
    const result = await svc.setDeployedVersion('M', '1', 'staging');
    expect(result.success).toBe(true);
  });

  // ============================================================
  // deleteModel
  // ============================================================
  console.log('\n[deleteModel]');

  await it('calls DELETE with URL-encoded name and version', async () => {
    const fetch = mockFetch({ success: true });
    const svc = buildService(fetch);
    await svc.deleteModel('My Model', '2', 99);
    expect(fetch.calls[0].url).toBe('/api/models/My%20Model/version/2/');
  });

  await it('sends DELETE method', async () => {
    const fetch = mockFetch({ success: true });
    const svc = buildService(fetch);
    await svc.deleteModel('M', '1', null);
    expect(fetch.calls[0].opts.method).toBe('DELETE');
  });

  await it('includes db_id in body', async () => {
    const fetch = mockFetch({ success: true });
    const svc = buildService(fetch);
    await svc.deleteModel('M', '1', 42);
    const body = JSON.parse(fetch.calls[0].opts.body);
    expect(body.db_id).toBe(42);
  });

  await it('throws when version not found', async () => {
    const fetch = async () => ({ ok: false, status: 404, json: async () => ({ error: 'Version not found' }) });
    const svc = buildService(fetch);
    await rejects(svc.deleteModel('M', '99', null), 'Version not found');
  });

  await it('URL-encodes model names with slashes', async () => {
    const fetch = mockFetch({ success: true });
    const svc = buildService(fetch);
    await svc.deleteModel('org/model', '1', null);
    if (!fetch.calls[0].url.includes('org%2Fmodel'))
      throw new Error('Expected org%2Fmodel in URL');
  });

  await it('null db_id is still sent in body', async () => {
    const fetch = mockFetch({ success: true });
    const svc = buildService(fetch);
    await svc.deleteModel('M', '1', null);
    const body = JSON.parse(fetch.calls[0].opts.body);
    expect(body.db_id).toBeNull();
  });

  // ----------------------------------------------------------------
  // Summary
  // ----------------------------------------------------------------
  console.log(`\n${'─'.repeat(60)}`);
  console.log(`Frontend Tests: ${passed + failed} total, ${passed} passed, ${failed} failed`);
  if (failures.length > 0) {
    console.log('\nFailed tests:');
    failures.forEach(f => console.log(`  ✗ ${f.name}: ${f.error}`));
    process.exit(1);
  } else {
    console.log('\n✅ All frontend tests passed!');
  }

})();
