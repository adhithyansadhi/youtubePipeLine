import base64

with open("client_secret.json", "rb") as f:
    print(base64.b64encode(f.read()).decode())