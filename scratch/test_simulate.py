"""Quick test script for the /engine/simulate POST endpoint."""
import urllib.request
import json

body = json.dumps({
    "rainfall_mm_h": [2, 5, 10, 25, 40, 35, 20, 8, 3, 1],
    "half_life_days": 10,
}).encode()

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/engine/simulate",
    data=body,
    headers={"Content-Type": "application/json"},
)

r = urllib.request.urlopen(req)
data = json.loads(r.read())

print(f"Timesteps: {data['timesteps']}")
print(f"Peak SWI:  {data['peak_swi_mm']} mm")
print(f"SWI:       {data['swi_series']}")
print(f"Runoff:    {data['runoff_series']}")
print(f"Alerts:    {[a['status'] for a in data['alerts']]}")
