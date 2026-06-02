# FIT4110 Lab 04 - Access Gate Docker Packaging

Service cua nhom: **Access Gate** cho Smart Campus Operations Platform.

Lab 04 chung minh service co the duoc dong goi bang Docker, chay lai tren may khac, va kiem thu lai bang Postman/Newman.

## Chuc nang API

- `GET /health`: kiem tra service va cau hinh URL tich hop.
- `POST /access-events`: ghi nhan su kien ra vao cong.
- `GET /access-events/latest`: lay cac su kien moi nhat, co the loc theo `gate_id`.
- `GET /access-events/{event_id}`: lay chi tiet mot su kien.

Payload mau:

```json
{
  "gate_id": "GATE-A01",
  "credential_id": "CARD-1001",
  "credential_type": "card",
  "person_id": "STU-2026-0001",
  "decision": "granted",
  "confidence": 0.95,
  "reason": "policy_pass",
  "timestamp": "2026-05-13T08:30:00+07:00"
}
```

## Chuan bi tich hop nhom khac

Lab 04 chua bat buoc ket noi that voi cac service khac. Repo da khai bao bien moi truong de sang Lab 05/plug-a-thon co the noi tiep:

- `CORE_SERVICE_URL`: hoi Core/Policy service xem credential co duoc vao khong.
- `CAMERA_SERVICE_URL`: lay thong tin camera/vision khi can xac thuc khuon mat hoac bien so.
- `NOTIFICATION_SERVICE_URL`: gui canh bao khi bi tu choi hoac su kien rui ro.

Trong Lab 04, cac URL nay chi la cau hinh va duoc hien thi trong `/health`.

## Cau truc chinh

```text
contracts/access-gate.openapi.yaml
postman/collections/FIT4110_lab04_access_gate.postman_collection.json
postman/environments/FIT4110_lab04_local.postman_environment.json
src/access_gate_app/main.py
Dockerfile
.dockerignore
.env.example
RUN_LOCAL.md
```

## Chay local khong Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn access_gate_app.main:app --app-dir src --host 0.0.0.0 --port 8000
```

Kiem tra:

```bash
curl http://localhost:8000/health
```

## Build va chay bang Docker

```bash
docker build -t fit4110/access-gate:lab04 .
docker run --rm --name fit4110-access-gate-lab04 -p 8000:8000 --env-file .env.example fit4110/access-gate:lab04
```

## Chay Newman

```bash
npm install
npm run test:local
```

Report sinh tai:

```text
reports/newman-lab04-local.xml
reports/newman-lab04-local.html
```

## Lenh nhanh

```bash
make install
make lint
make mock
make build
make run
make test-docker
make stop
```

## Dieu kien nop bai

- Dockerfile build duoc image.
- Container chay duoc va `/health` tra `200`.
- Service chay bang non-root user trong container.
- Co `.dockerignore`, `.env.example`, `RUN_LOCAL.md`.
- Co OpenAPI contract va Postman collection cho Access Gate.
- Newman pass tren container.
- Co evidence/report trong `reports/`.
