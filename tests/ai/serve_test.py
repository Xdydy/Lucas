import requests
resp = requests.post("http://localhost:8081/w1", json={"a": "Alice"})
print(resp.text)