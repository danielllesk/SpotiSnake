import requests

BACKEND_URL = "https://spotisnake.onrender.com/test_cors"
ORIGIN = "http://localhost:8000"

def test_cors_headers():
    headers = {"Origin": ORIGIN}
    r = requests.get(BACKEND_URL, headers=headers)
    print("GET /test_cors status:", r.status_code)
    print("GET /test_cors Access-Control-Allow-Origin:", r.headers.get("Access-Control-Allow-Origin"))
    
    preflight_headers = {
        "Origin": ORIGIN,
        "Access-Control-Request-Method": "POST"
    }
    r2 = requests.options(BACKEND_URL, headers=preflight_headers)
    print("OPTIONS /test_cors status:", r2.status_code)
    print("OPTIONS /test_cors Access-Control-Allow-Origin:", r2.headers.get("Access-Control-Allow-Origin"))

if __name__ == "__main__":
    test_cors_headers() 