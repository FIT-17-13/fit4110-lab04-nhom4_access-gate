# RUN_LOCAL.md - Huong dan chay Access Gate Lab 04

## 1. Cai dependencies Newman/Prism/Spectral

```bash
npm install
```

## 2. Build Docker image

```bash
docker build -t fit4110/access-gate:lab04 .
```

## 3. Run container

```bash
docker run --rm --name fit4110-access-gate-lab04 -p 8000:8000 --env-file .env.example fit4110/access-gate:lab04
```

Mo terminal khac va kiem tra:

```bash
curl http://localhost:8000/health
```

Ket qua mong doi:

```json
{
  "status": "ok",
  "service": "access-gate",
  "version": "0.4.0",
  "integrations": {
    "core_service_url": "http://core:8000",
    "camera_service_url": "http://camera:8000",
    "notification_service_url": "http://notify:8000"
  }
}
```

## 4. Chay Newman tren container

```bash
npm run test:local
```

Report sinh tai:

```text
reports/newman-lab04-local.xml
reports/newman-lab04-local.html
```

## 5. Dung container

```bash
docker stop fit4110-access-gate-lab04
```

## Lenh nhanh

```bash
make build
make run
make test-docker
make stop
```
