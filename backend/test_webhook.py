import requests

r = requests.post('http://127.0.0.1:8000/api/v1/bolna/webhook', json={'id':'test-call','agent_id':'abc'})
print(r.status_code, r.text)
