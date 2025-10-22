import requests

resp = requests.post("http://localhost:8080/w1", json={"a": "Hello from w1"})
res = resp.text
print(res)