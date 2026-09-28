import requests

url = "http://127.0.0.1:8000/api/models/register/"
files = {'model': ('dummy.pt', b"dummy content")}
data = {
    'model_name': 'EntityRecognitionModel',
    'model_type': 'NER',
    'architecture': 'BERT',
    'accuracy': '99.5',
    'priority': '1',
    'is_deployable': 'true',
    'purpose': 'Extraction',
    'deployment_points': 'dev',
}

try:
    r = requests.post(url, files=files, data=data)
    print("Status code:", r.status_code)
    print("Response:", r.text)
except Exception as e:
    print("Request failed:", e)
