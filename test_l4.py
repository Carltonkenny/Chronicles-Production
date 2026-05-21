import socket,httpx,json,time
addr=socket.getaddrinfo("00bd7a4138571.notebooksn.jarvislabs.net",443,socket.AF_INET)
url="https://00bd7a4138571.notebooksn.jarvislabs.net"

r=httpx.get(url+"/health",timeout=10)
d=r.json()
print("HEALTH:", d["status"])
print("GPU:", d["gpu"]["name"])
print("VRAM free:", d["gpu"]["vram_free_gb"], "GB")
print("Ready:", d["model_ready"])

print()
print("Generating 5s clip via L4...")
t0=time.time()
r=httpx.post(url+"/generate_clip",json={"prompt":"A cinematic shot of a blacksmith striking an anvil at dawn, sparks flying, warm forge fire, photorealistic, 35mm wide shot","duration_s":5,"seed":42},timeout=600)
dt=time.time()-t0
if r.status_code==200:
    print("SUCCESS!", len(r.content)//1024, "KB video in", int(dt), "s")
else:
    print("FAILED:", r.status_code, r.text[:300])
