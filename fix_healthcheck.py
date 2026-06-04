with open('/home/ubuntu/store-intelligence-system/docker-compose.yml', 'r') as f:
    content = f.read()

old = '''    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:3000 >/dev/null"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - store-net

  prometheus:'''

new = '''    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:80/health >/dev/null"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - store-net

  prometheus:'''

if old in content:
    content = content.replace(old, new)
    with open('/home/ubuntu/store-intelligence-system/docker-compose.yml', 'w') as f:
        f.write(content)
    print("Fixed")
else:
    print("Pattern not found - check manually")
