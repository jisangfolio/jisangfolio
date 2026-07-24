<!-- source: internal KETI MLOps handoff document (author's own work) — SANITIZED + technical-only extract for public corpus -->
<!-- title: On-prem MLOps Pipeline (KETI) — technical reference -->
<!-- vendor: self / on-prem -->
<!-- topic: on-prem MLOps pipeline — Triton serving, MLflow registry, Gitea Actions CI, Prometheus/Grafana observability, ONNX, model governance, MLOps maturity -->
<!-- note: internal IPs/hostnames, credentials, colleague & external names, partner orgs, project budget removed/generalized; job-hunt/interview meta sections dropped; technical content preserved verbatim. -->

# On-prem MLOps Pipeline (KETI) — Technical Reference

This document describes an on-premise MLOps pipeline operated on a single GPU server that serves deep-learning models (e.g., a 3D U-Net urban-cooling surrogate and a PINN model provided by a partner university). The scope is **model serving and the surrounding MLOps infrastructure** — ONNX export → Triton serving → MLflow registry → Gitea Actions CI → Prometheus/Grafana observability — not model-architecture design.

**Stack:** NVIDIA Triton (inference serving), MLflow (experiment tracking + model registry), Gitea + Gitea Actions (self-hosted git + CI), Prometheus + Grafana (metrics/observability), Docker Compose (orchestration), all operated under a restricted non-root account (NOPASSWD sudo allowlist).

---

## 이번 업데이트 변경점 (2026-07-24 현행화 — 리뷰용 요약)

1. **§2 신설**: 2026-07-24 라이브 재점검 스냅샷 + 정정표 **CORR 12~19** — 본문 곳곳의 "§2 참조" 깨진 상호참조 복구.
2. **호스트(CORR 12)**: 2026-07-09 재부팅 확인(커널 6.8.0-111 → **6.8.0-134**). NVML mismatch **재발**(모듈 580.159.03 vs 라이브러리 580.173.02, 무인 업그레이드) — §4.1.1.
3. **MLflow(CORR 13)**: 등록모델 9개/버전 **14개**로 정정(6/19 기록 "12개"는 오산 — `ecotron_flow_v2_0608`이 v1~v3 3버전). `external_models_ingest` 런 11개. hot 2종 버전 태그 `status=received` 명시 — §5.2.5·§7.4.4·§8.2·§12.5.
4. **fan-out 정정(CORR 14)**: 6/18 "5개 모델 각각 v2 retire+v3 deploy"는 부정확 — **flow_v2만 v3 도달**, thermal 4종은 v1 유지 — §6.5A.6.
5. **포털 2차 개편(CORR 15)**: 2026-07-14~15 집중 16커밋 — 6페이지 `pages/` → **5뷰 `views/`**(st.navigation), 버전 비교·아티팩트 파일트리·라이프사이클 전환 버튼 신규, 추론=실사용 REST 클라이언트화, 온보딩 배너 철거 — §6.10.10 신설.
6. **드리프트(CORR 16)**: current 합성 → **실제 추론 입력 적재 구조**(2026-07-21, `build_current.py` + 포털 opt-in 체크박스). 단 2026-07-24 실측 로그는 **시드 1,400행뿐·실요청 유입 0건** — §6.11.7 신설.
7. **Grafana(CORR 17)**: 7패널 제목을 API 실측으로 확정(기존 [확인 필요] 해소) — §6.4.
8. **파일 인덱스(CORR 18)**: Postman 컬렉션 개명·확장(8폴더/28리퀘스트), WBS 파일 이동, 벤치마킹 문서 `비교\발표물\` 이동, 6/1 백업 스냅샷 부재, mlops-tools `docs/` 삭제(6/17) 반영 — §16.1.
9. **reference_features.csv(CORR 19)**: "양쪽 커밋 단일 진실" 서술 정정 — 실제는 mlops-tools에만 커밋(03bb499), cooling-project `data/`는 untracked — §6.11.2.
10. cooling_unet 실서빙 ONNX **5/14 빌드 유지 재확인**(md5 `39bba09b…`) — 레지스트리 v4 ↔ 서빙 갭 지속 — §5.2.6.
11. 성숙도 **L0~1 유지**(자동 재학습 트리거 여전히 전무) — §10.5.
12. 편집 정리: `[모델개발 대학]([모델개발 대학])` 류 마스킹 잔재 링크 표기 정정, 관련 검증 태그 2026-07-24 갱신.

---

## 2. 현재 검증 상태 (2026-07-24 라이브 점검) _[휘발성]_

> 2026-06-19 이후 첫 전면 라이브 재점검(근거: `docker ps`, Triton `/v2/repository/index`, MLflow REST API, Prometheus/Grafana API, 서버 SSH 실측). 본문 각처의 "§2 참조"는 이 섹션을 가리킨다(본 추출본에는 §2가 없었으나 2026-07-24 갱신에서 신설). 이 문서에 없는 §1·§3·§13~§15·§17~§18 참조는 내부 원본 기준의 상호참조다.

### 2.1 가동 컨테이너 — 9개 (변동 없음, `docker ps` 실측)

| 컨테이너 | 이미지 | 상태(2026-07-24) |
|---|---|---|
| triton-server | nvcr.io/nvidia/tritonserver:25.07-py3 | Up 2 weeks (healthy) — 28000/28001/28002 |
| mlflow | ghcr.io/mlflow/mlflow:v2.18.0 | Up 10 days — 5000 |
| gitea | gitea/gitea:latest (1.26.1) | Up 2 weeks — 3000/222 |
| act_runner | gitea/act_runner:latest | Up 2 weeks |
| prometheus | prom/prometheus:latest | Up 2 weeks — 9090 |
| grafana | grafana/grafana-oss:latest (13.0.1) | Up 2 weeks — 3001 |
| trainer | pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime | Up 10 days |
| mlops-portal | python:3.11-slim | **Up 3 days** (7/21 재배포) — 8510 |
| evidently-ui | python:3.11-slim | **Up 3 days** (7/21 재배포) — 8511 |

- 호스트는 **2026-07-09 재부팅**됨 — "2주/10일/3일" 가동시간 편차는 재부팅·재배포 시점 차이.

### 2.2 서빙·레지스트리 스냅샷

- Triton: **10개 모델 전부 READY**(`POST /v2/repository/index` 실측) — 목록은 6/19와 동일. Triton core 2.59.1.
- MLflow: 실험 2개(`cooling-project-3d-unet` 런 4개, `external_models_ingest` 런 **11개**), 등록모델 **9개 / 버전 14개**(CORR 13), 전 버전 `current_stage=None`(태그 기반 거버넌스 유지).
- `cooling-project-unet` v4=deployed 태그 유지, **실서빙 ONNX는 여전히 5/14 빌드**(md5 `39bba09b…` 2026-07-24 재확인 — §5.2.6).
- hot 분할 2종(`ecotron_thermal_{f,s}_hot_v2_0608`)은 v1 `status=received` + `manifest_validation_status=demo_only` + `triton_loaded=true` — 검증 미완 상태의 서빙 지속.

### 2.3 관측

- Prometheus 타겟 2개(self·triton) **up**, 알림 룰 **0개** 유지. Grafana 13.0.1, 대시보드 1개(uid `triton-main`, "Triton Inference Server", **7패널 제목 실측 확정** — §6.4 CORR 17).

### 2.4 호스트·드라이버 (CORR 12)

- 커널 `6.8.0-134-generic`(7/9 재부팅으로 상승 — 6/19의 예상치 '6.8.0-124'보다 더 진행된 버전).
- **NVML mismatch 재발**: 로드된 커널 모듈 `580.159.03` vs 설치 NVML 라이브러리 `580.173.02`(무인 업그레이드, 2026-07-24 06:38경 `nvidia-cdi-refresh.service` 재실패 로그) → 호스트 `nvidia-smi` 재실패. **컨테이너 GPU는 정상**(Triton healthy·10모델 READY) — 6/19과 동일한 "호스트 CLI만 깨짐" 패턴.
- 디스크: `/` 30GB/59GB(53%, 6/1 대비 +3GB), `/srv/triton` 1.2GB(3%) 불변.

### 2.5 정정표 (2026-06-19 → 2026-07-24, CORR 12~19)

| CORR | 항목 | 6/19 기록 | 2026-07-24 실측 |
|---|---|---|---|
| 12 | 호스트 커널/드라이버 | 모듈 580.126.20 vs lib 580.159.03, 재부팅 보류 | 7/9 재부팅(6.8.0-134) 후 **mismatch 재발**(모듈 580.159.03 vs lib 580.173.02) |
| 13 | MLflow 버전 수 | "9모델/버전 12개" | **9모델/버전 14개** — flow_v2가 v1~v3 3버전 보유(6/19 기록은 오산) |
| 14 | 6/18 fan-out | "5개 모델 각각 v2→v3 전이" | **flow_v2만 v3 도달**, thermal 4종 v1 유지(hot 2종 status=received) |
| 15 | 포털 구조 | 6페이지 `pages/` | **5뷰 `views/`**(7/14~15 개편 — §6.10.10), 온보딩 배너 철거, 버전비교·아티팩트트리·라이프사이클 버튼 신규 |
| 16 | 드리프트 current | 합성(sample+이동) | **실입력 적재 구조**(7/21) — 단 로그는 시드 1,400행·실요청 0건(§6.11.7) |
| 17 | Grafana 패널 | 7패널, 제목 [확인 필요] | 패널 제목 7종 실측 확정(§6.4) |
| 18 | 파일 인덱스 | WBS/Postman/백업 경로 | 다수 이동·개명·삭제(§16.1 갱신) |
| 19 | reference_features.csv | "양쪽 커밋 단일 진실" | mlops-tools만 커밋(03bb499)·cooling-project는 untracked·서버본 상이(§6.11.2) |

### 2.6 미확인 [확인 필요]

- Gitea Actions 런 이력(6/19 이후): gitea 컨테이너에 sqlite3 부재 + 1.26.1 Actions REST 미지원으로 미조회. 워크플로 보유 리포(cooling-project·ecotron-pinn)에 6/18 이후 push가 없어 신규 런은 없을 것으로 추정 — 단정 금지.
- MLflow artifacts 총량(6/19 ≈280M) 재측정 안 함.
- Grafana 패널별 PromQL 원문 미덤프(제목만 확정).

---

## 4. 인프라 환경 (GPU 서버 / Docker / 권한)

> 이 섹션은 박지상이 운영한 **단일 GPU 서버 위의 MLOps 스택**과, 그가 받은 **제한된 권한 안에서 그 스택을 운영·자동화한 설계 패턴**을 기록한다. 핵심 차별점은 §4.8 — "root도 docker 그룹도 없는 계정으로 어떻게 풀 MLOps 파이프라인을 굴렸는가"이다. (라이브 상태 수치는 §2 현재 검증 상태(최신 2026-07-24) 참조; §17 시크릿은 내부 원본에만 존재.)

---

### 4.1 GPU 서버 — 하드웨어 (실측, 2026-06-01)

| 항목 | 값 |
|---|---|
| Hostname | `gpu-server-01` |
| 외부 IP | `<gpu-server>` (사내 IP) |
| 내부/공인 IP | **[확인 필요]** (공인 IP 노출은 [선임연구원B] 선임과 협의 예정 상태) |
| OS | Ubuntu 24.04.4 LTS (Noble Numbat) |
| 커널 | `Linux 6.8.0-111-generic x86_64` (원문 6/1 스냅샷). **정정(CORR 12): 2026-07-09 재부팅으로 현재 `6.8.0-134-generic` 가동** — 4.1.1 참조 _[휘발성·2026-07-24 검증]_ |
| CPU | **Intel Xeon Silver 4510** (Emerald Rapids 세대) — 2소켓 × 12코어 × 2스레드 = 48 vCPU. `lscpu` 실측 2026-06-19 (원문 "Sapphire Rapids 추정"을 SKU 확정으로 정정) |
| RAM | 251 GB total (`free -g`), 사용 7GB / 가용 244GB (6/1 시점 한산) |
| GPU | NVIDIA **L40S 46GB VRAM** (배경 문서 기준) |

- (a) **왜:** 폐쇄망 + 단일 고용량 GPU(L40S 46GB) + 251GB RAM이라 학습·서빙·관측을 한 서버에 몰아넣는 것이 합리적이었다. 분산 클러스터(K8s)가 아니라 단일 노드 Docker Compose를 택한 근거가 바로 이 하드웨어 규모(노드 1대)다.

#### 4.1.1 GPU 드라이버 / NVML mismatch 현황 (정정 — 2026-06-19 검증)

원문(6/1)은 "host `nvidia-smi` 호출 시 `Driver/library version mismatch` 발생, NVML 580.159 보고, 호스트 드라이버 재정합 미수행"으로만 기록했다. 2026-06-19 직접 점검 결과 원인이 특정됐다:

- **로드된 커널 모듈 = 580.126.20** (2026-05-07 부팅 시점 버전) **vs 설치된 NVML 라이브러리 = 580.159.03** (2026-05-21 업그레이드분, 미재부팅) → 호스트 `nvidia-smi`가 NVML mismatch로 실패.
- **컨테이너 내부 GPU는 정상.** Triton·trainer가 L40S를 정상 사용하며 `torch.cuda.is_available()=True`. 즉 **추론·학습 경로는 무영향**이고, 깨진 건 호스트 CLI 한정.
- `nvidia-cdi-refresh.service` **failed** → CDI 디바이스 스펙이 갱신되지 않아 **신규 GPU 컨테이너 기동 시 위험**(기존 가동 컨테이너는 안전).
- **재부팅이 근본 해결**이나, 재부팅은 NOPASSWD 권한 밖(full-sudo/콘솔 필요)이라 미수행. 재부팅 시 커널이 `6.8.0-124`로 상승할 것으로 예상.
- (a) **왜 안 고쳤나(정직):** 재부팅 권한이 없고(§4.7), 서빙 무중단이 우선이라 "고쳐야 하지만 권한·리스크 때문에 보류"한 알려진 부채다. 임의로 드라이버를 만지면 가동 중 컨테이너의 GPU가 끊길 위험이 있었다.

**[2026-07-24 재검증 — 재부팅 발생 & mismatch 재발 (CORR 12)]**

- **2026-07-09 재부팅됨**(주체·경위 [확인 필요] — 인프라팀 추정). 커널 `6.8.0-134-generic`로 상승, 재부팅 시점엔 모듈·라이브러리가 `580.159.03`으로 정합됐던 것으로 추정.
- 그러나 이후 **무인 업그레이드가 `nvidia-driver-580-server-open 580.173.02`를 설치**(2026-07-24 06:38경 `nvidia-cdi-refresh.service` 재실패 로그) → **mismatch 재발**: 로드된 커널 모듈 `580.159.03` vs NVML 라이브러리 `580.173.02`. 호스트 `nvidia-smi` 다시 실패.
- **컨테이너 GPU는 여전히 정상**(Triton healthy, 10모델 READY) — 6/19과 동일하게 피해는 호스트 CLI·신규 GPU 컨테이너 기동 리스크(CDI 미갱신)에 한정.
- **교훈(정직)**: "재부팅이 근본 해결"은 부분만 유효했다 — **재부팅과 무인 드라이버 업그레이드가 동기화되지 않는 한 mismatch는 재생산**된다. 근본 대응은 (a) 드라이버 업그레이드 직후 재부팅 운영 절차 합의 또는 (b) nvidia 패키지의 unattended-upgrades 제외 설정이나, 둘 다 인프라팀 권한 영역([확인 필요]). _[휘발성·2026-07-24 검증]_

---

### 4.2 디스크 마운트

| 마운트 | 디바이스 | 크기 | 사용 |
|---|---|---|---|
| `/` (루트) | `/dev/mapper/ubuntu--vg-ubuntu--lv` | 59 GB | 27GB used / 30GB avail (48%) → **2026-07-24: 30GB used / 27GB avail (53%)** |
| `/srv/triton` | `/dev/mapper/ubuntu--vg-lv--models` | 50 GB | 1.2GB used / 49GB avail (3%) |
| `/home/<user>/data` | **[확인 필요]** (학습 데이터 11GB 위치) | | |

- (a) **왜:** Triton 모델 저장소를 **별도 LV(`ubuntu--vg-lv--models`, 50GB)** 로 분리한 것은 모델 아티팩트 증가가 루트 파일시스템(59GB, 이미 48% 사용)을 잠식하지 않게 하려는 인프라팀의 설계로 보인다. 박지상의 mlops 스택과 Triton 저장소가 디스크 레벨에서도 분리돼 있다.

---

### 4.3 GPU 서버 — 디렉토리 구조 (확인됨)

```
/srv/triton/                       (인프라팀 관리 추정 — root 소유)
  ├── compose/                     (Triton 별도 compose, 본인 미관리)
  ├── model_repository/            (Triton 모델 저장소, container에는 ro mount)
  │   ├── cooling_unet/1/{model.onnx, config.pbtxt}
  │   ├── ecotron_flow/1/{...}
  │   ├── ecotron_thermal_f/1/{...}
  │   ├── ecotron_thermal_s/1/{...}
  │   └── resnet50/1/{...}
  │   └── (+ 6/8 추가된 v2 분할 모델 5종 — 4.3.1 참조)
  └── logs/                        (Triton 로그 — container에 rw mount)

/home/<user>/mlops/                (박지상 관리 stack, <user> 소유)
  ├── act_runner/                  (Gitea Actions runner data + config.yaml)
  ├── compose/
  │   └── docker-compose.yml       (mlflow/grafana/prometheus/gitea/trainer/act_runner
  │                                 + 6월 추가: mlops-portal, evidently-ui)
  ├── gitea/                       (Gitea data: /data 마운트)
  ├── grafana/
  │   ├── provisioning/
  │   │   ├── dashboards/default.yml
  │   │   └── datasources/prometheus.yml
  │   └── dashboards/triton.json
  ├── mlflow/
  │   ├── artifacts/{1,2}/         (experiment id 별)
  │   └── db/mlflow.db (현재 544KB), mlflow.db.v3-backup (808KB)
  ├── prometheus/prometheus.yml
  └── trainer/workspace/           (학습 코드 + 결과)

/home/<user>/data/cooling_project/coolling_hdf5_data_new/   (학습 데이터, trainer에 ro 마운트)
```

- **소유권 경계가 핵심:** `/srv/triton/*` 는 **root 소유 = 인프라팀 영역(본인 미관리)**, `/home/<user>/mlops/*` 는 **<user> 소유 = 박지상 관리 영역**. 박지상은 Triton compose를 직접 만지지 않고 `triton-net`(external)으로만 연결한다(§4.4).
- (a) **왜:** 조직 구조상 Triton 서버는 인프라팀이 root로 운영하고, 박지상은 비-root 사용자로 자기 mlops 스택만 책임진다. 이 경계 때문에 §4.8의 우회 패턴들이 전부 "남의 영역을 안 건드리고 내 권한 안에서 해결"하는 형태로 설계됐다.

#### 4.3.1 모델 저장소 현황 (정정 — 2026-06-19 검증)

원문(6/1)은 model_repository에 **5개**(cooling_unet, ecotron_flow, ecotron_thermal_f, ecotron_thermal_s, resnet50)만 기록. 2026-06-19 점검 결과 **10개로 증가**(2026-06-08 v2 분할 5종 추가):

- 추가분: `ecotron_flow_v2_0608`, `ecotron_thermal_f_cold_v2_0608`, `ecotron_thermal_f_hot_v2_0608`, `ecotron_thermal_s_cold_v2_0608`, `ecotron_thermal_s_hot_v2_0608` (thermal을 cold/hot로 분할한 5종).
- 전부 **GPU(L40S, `gpus[0]`)에 로드·READY**.
- **v2 분할의 설계 의도:** 출력 텐서명을 `outputs`로 통일·변경하여, 과거 v1에서 발생하던 `linear_6` 차원 mismatch를 회피. (모델 자체 세부는 §7 모델&거버넌스, 차원 mismatch 트러블은 §9 트러블슈팅 로그 참조.)
- _[휘발성·2026-06-19 검증 — 모델 개수/READY 상태는 §2 현재 검증 상태 참조]_

---

### 4.4 네트워크 구성

| 네트워크 | 종류 | 멤버 컨테이너 |
|---|---|---|
| `compose_mlops-net` | bridge (compose 생성) | prometheus, grafana, gitea, mlflow, trainer, act_runner (+ 6월: mlops-portal, evidently-ui) |
| `triton-net` | external (Triton 측 compose가 생성) | triton-server, prometheus(브릿지) |

- compose 프로젝트명 = `compose` (디렉토리명) → 네트워크 prefix `compose_`.
- Triton은 **별도 compose 프로젝트**라, stack 내부 컨테이너에서 `triton-server` **호스트명으로 접근**. **prometheus만 양쪽 net 모두 join**(메트릭을 수집하려면 triton-net에도 붙어야 하므로).
- (a) **왜 external network인가:** 박지상 stack과 인프라팀 Triton stack이 서로 다른 compose 프로젝트로 분리돼 있으므로(§4.3 소유권 경계), 두 스택을 잇는 유일한 방법이 **external 네트워크 공유**다. prometheus가 양쪽에 발을 걸쳐 Triton 메트릭을 mlops-net 쪽 Grafana로 흘려보낸다.

---

### 4.5 외부 노출 포트 매핑 (실측 `docker ps`)

| 서비스 | 호스트 포트 | 컨테이너 포트 | 메모 |
|---|---|---|---|
| Triton HTTP | 28000 | 8000 | `POST /v2/models/<name>/infer` (클라이언트 baseUrl = `<gpu-server>:28000`) |
| Triton gRPC | 28001 | 8001 | |
| Triton metrics | 28002 | 8002 | Prometheus가 `/metrics` 수집 |
| MLflow | 5000 | 5000 | UI + API + 아티팩트 프록시 |
| Grafana | 3001 | 3000 | 초기 자격증명 `[credential stored separately]`, `GF_AUTH_ANONYMOUS_ENABLED=true`(Viewer) |
| Prometheus | 9090 | 9090 | |
| Gitea HTTP | 3000 | 3000 | |
| Gitea SSH | 222 | 22 | |
| act_runner | 없음 | 없음 | 외부 노출 X (gitea로 polling) |
| **mlops-portal** (Streamlit) | **8510** | **8501** | 6월 추가, HTTP 200·~24h 가동. 모델 업로드/리스트/모니터링/거버넌스/추론/드리프트 6페이지 _[휘발성·2026-06-19 검증]_ |
| **evidently-ui** | **8511** | **8001** | 6월 추가(PoC), HTTP 200·~24h 가동. 드리프트 대시보드 _[휘발성·2026-06-19 검증]_ |

- **Triton 포트 주의:** 28000/28001/28002 매핑은 Triton 측 `.env`가 compose 기본값(8000대)을 **오버라이드**한 결과다. `MODEL_CONTROL_MODE=explicit`. 클라이언트/Postman은 반드시 `<gpu-server>:28000`을 써야 함(8000 아님).
- **정정(6/1→6/19):** 원문 표에는 9개 서비스만 있었고 mlops-portal(8510)·evidently-ui(8511) 두 줄이 없었다. 6월에 Streamlit 포털(§5/§7 연계)과 Evidently 드리프트(PoC, §7)가 추가 노출됨.
- (a) **왜 28000대로 오버라이드:** 한 서버에 여러 8000대 포트를 쓰는 서비스가 공존하므로 Triton을 28000대 비충돌 대역으로 밀어, 포트 충돌 없이 단일 노드에 모든 서비스를 적재.

---

### 4.6 환경 변수 / .env

- `MLFLOW_TRACKING_URI=http://mlflow:5000` (trainer 컨테이너 내부) — **컨테이너 이름으로 해석**(같은 네트워크 내 DNS).
- `MLFLOW_TRACKING_URI=http://<gpu-server>:5000` (외부 호스트에서).
- **Gitea:** `GITEA__actions__ENABLED=true` (Actions 켜는 키).
- **act_runner:** `GITEA_INSTANCE_URL=http://gitea:3000`, `GITEA_RUNNER_NAME=gpu-runner`, `GITEA_RUNNER_LABELS=ubuntu-latest:docker://python:3.11-bookworm,ubuntu-22.04:docker://python:3.11-bookworm`, `CONFIG_FILE=/data/config.yaml`, `GITEA_RUNNER_REGISTRATION_TOKEN=[credential stored separately]`.
- 별도 `.env` 파일 사용 여부: **[확인 필요]** — 현재 mlops compose는 env를 inline으로 두고 있음. (단, Triton compose 쪽은 `.env`로 포트를 오버라이드함 — §4.5.)
- (a) **왜 컨테이너명 vs IP 이원화:** 컨테이너 내부에서는 같은 bridge net의 DNS(`mlflow`)로, 호스트 외부에서는 사내 IP(`<gpu-server>`)로 접근해야 하므로 추적 URI를 두 형태로 둔다. runner 라벨에 `python:3.11-bookworm` 이미지를 박은 것은 CI job이 이 이미지 위에서 돌도록 고정한 것.

---

### 4.7 sudo 권한 (NOPASSWD 정확 목록, 실측 `sudo -n -l`)

`<user>` 계정의 그룹 = `<user>, systemd-journal, deployers, developers, triton` (**`docker` 그룹 없음** → 맨 `docker` 명령은 socket 권한 거부, 항상 `sudo` 필수).

NOPASSWD로 허용된 명령(이것**만** 비번 없이 가능):

```
/usr/bin/docker ps
/usr/bin/docker ps *
/usr/bin/docker exec *
/usr/bin/docker logs *
/usr/bin/docker stats
/usr/bin/docker inspect *
/usr/bin/docker compose -f * ps
/usr/bin/docker compose -f * logs *
/usr/bin/docker compose -f * exec *
/usr/bin/docker compose ps
/usr/bin/docker compose logs *
/usr/bin/docker compose exec *
/usr/bin/docker compose up -d
/usr/bin/docker compose up -d *
/usr/bin/docker compose down
/usr/bin/docker compose restart
/usr/bin/docker compose restart *
/usr/bin/docker compose pull
/usr/bin/docker compose pull *
/bin/systemctl status *
/bin/systemctl restart app-*
/bin/systemctl reload app-*
```

**비번 필요 (NOPASSWD 미허용)** — 실제 작업에서 막혔던 것:

- `docker network ls`, `docker network inspect` (네트워크 직접 관리)
- `docker compose config` (compose 파싱 검증) → `docker compose -f * ps`로 우회(§4.8)
- `docker run` / `docker compose run` (임의 단발 실행)
- `reboot` / `poweroff` / `systemctl reboot` → **재부팅은 full-sudo/콘솔 필요**(§4.1.1 드라이버 mismatch가 못 고쳐진 직접 원인)
- `apt`, `cat /etc/...` 등 일반 시스템 명령

- (a) **왜 이 목록이 중요한가:** 박지상이 받은 권한은 **"읽기·재기동·exec은 되지만, 생성(run)·네트워크·임의 시스템·재부팅은 안 되는"** 의도적으로 좁혀진 운영 권한이다. allowlist가 `docker exec *`와 `docker compose up -d|restart`까지만 열려 있다는 사실이 §4.8 우회 패턴 전부의 전제다. `systemctl restart app-*`처럼 **접두사 와일드카드로만 제한**된 점도 주목 — 인프라팀이 "app-" 네임스페이스 서비스만 만지게 허용했다.

---

### 4.8 권한 제약 우회 설계 패턴 (★ 핵심 차별점 — '제한된 권한 환경 운영' 스토리)

> 박지상의 가장 차별적인 역량이 여기 있다. 일반적인 MLOps 튜토리얼은 root/docker 그룹을 전제로 한다. 박지상은 **그 전제가 깨진 환경**(§4.7)에서 동일한 결과(학습 트리거·배포·검증·관측)를 내기 위해 **명령 표면을 우회 설계**했다. 아래 표의 각 행은 "막힌 명령 → 허용된 명령으로 같은 효과를 내는 대체 경로"다.

| 문제 (막힌 것) | 우회 설계 (허용된 표면으로) | 설계 근거 |
|---|---|---|
| `docker run`/`docker compose run` 불가 → 학습을 **단발 컨테이너로 못 띄움** | **idle 컨테이너 상주(trainer) + `docker exec` 트리거** — trainer를 항상 켜두고(`compose up -d`로 기동), 학습은 `sudo docker exec trainer python train.py ...`로 주입 | `docker exec *`는 NOPASSWD 허용. "새 컨테이너를 만들 권한"이 없으니 "이미 있는 컨테이너 안에서 프로세스를 실행"하는 패턴으로 전환. GPU도 trainer가 기동 시점에 이미 잡고 있어 재할당 불필요 |
| `docker compose config` (파싱 검증) 불가 → 배포 전 **compose 문법 검증 못 함** | `docker compose -f docker-compose.yml ps` — 같은 파일을 파싱하므로 **문법 오류면 ps 단계에서 에러**가 나 검출 가능 | `compose -f * ps`는 허용. 검증 전용 서브커맨드(`config`)가 막혔으므로, **파일을 읽기만 하는 다른 허용 서브커맨드로 파싱을 강제**해 같은 신호(에러/정상)를 얻음. CI(§6)의 배포 단계에서도 동일 원리 사용 |
| Docker 네트워크 직접 관리(`network ls/inspect`) 불가 → **실제 네트워크 이름·멤버 확인 못 함** | `sudo docker inspect <container>` 로 컨테이너의 `NetworkSettings`에서 소속 네트워크(`compose_mlops-net` 등) 역추적. 네트워크 생성은 **compose alias에 위임**(compose가 prefix 붙여 자동 생성) | `inspect *`는 허용, `network *`는 불허. "네트워크를 조회"하는 대신 "컨테이너를 조회해 네트워크를 알아냄". 생성은 애초에 compose가 선언적으로 처리하게 해 수동 `network create` 자체를 제거 |
| host `cat`으로 **컨테이너 내부 설정 파일 못 읽음** (`cat /etc/...` 류 미허용) | `sudo docker exec <c> cat /path` — exec이 허용되므로 **컨테이너 안에서 cat 실행** | `docker exec *` 허용을 "파일 읽기"로 재활용. config.pbtxt 등 컨테이너 내부 파일 점검을 호스트 권한 없이 수행 |
| **재부팅 불가** (§4.1.1 드라이버 mismatch) | 우회 **불가** — full-sudo/콘솔 필요. → 리스크를 **문서화·격리**하고 컨테이너 추론 정상 동작을 근거로 무중단 유지 | 모든 제약이 우회 가능한 건 아니라는 정직한 한계. "신규 GPU 컨테이너 기동 위험"을 알고 보류한 의사결정 |

**설계 철학(왜 이렇게까지 했나):**
박지상은 권한을 더 달라고 요청해 환경을 바꾸기보다, **주어진 allowlist 표면에 자동화를 맞췄다.** 이유는 (1) 조직 보안 정책상 권한 확대가 어렵고(폐쇄망·타팀 소유), (2) **최소권한을 유지한 채로 동작하는 시스템이 더 안전·재현 가능**하기 때문이다. 그 결과 학습/배포/검증/관측 모두가 `docker exec`·`compose up -d|restart`·`inspect` 라는 **3~4개 동사만으로** 동작하는, 권한 표면이 좁고 감사하기 쉬운 파이프라인이 됐다.

  - 한 줄 요약: *"root·docker 그룹 없는 NOPASSWD allowlist 환경에서, idle 컨테이너+`docker exec` 학습 트리거, `compose ps`를 이용한 compose 파싱 검증, `docker inspect` 기반 네트워크 역추적 등 **권한 제약 우회 패턴을 설계**해 풀 MLOps 파이프라인을 무중단 운영했다."*
  - 면접 STAR: **S**=폐쇄망 GPU 서버, 비-root 계정·좁은 sudo allowlist. **T**=학습·서빙·배포·관측 자동화. **C**=`run`/`config`/`network`/`reboot` 전부 막힘. **A**=막힌 동사를 허용된 동사로 대체하는 우회 4종 설계(위 표). **R**=권한 확대 없이 파이프라인 가동, 권한 표면이 좁아 감사·재현 용이.
  - 차별화 포인트: 이건 "튜토리얼대로 따라한" 경험이 아니라 **제약을 전제로 재설계한** 경험이다. "권한이 없어서 못 했다"가 아니라 "권한이 없어도 되게 만들었다".
  - 정직 규율: 이 우회 설계는 박지상 본인의 운영 설계다(Claude Code는 점검·문서화 보조). 단, 재부팅처럼 우회 불가한 한계도 함께 말해 과장하지 말 것.

---

### 4.9 이전 이력 (WSL2 → GPU 서버, 2026.05)

- **이전 환경:** Windows 11, RTX 5060 Ti, WSL2 Docker. MLflow/Triton/Gitea/Prometheus/Grafana 모두 WSL2 안에서 운영.
- **이전(마이그레이션) 결정 사유:** GPU 성능, 폐쇄망 정책, 팀 공유.
- **이전 절차(요지):**
  1. compose 파일 + 설정 파일을 GPU 서버로 복사
  2. 4개 도구(MLflow, Prometheus, Grafana, Gitea)를 단일 `docker-compose.yml`로 통합 기동
  3. Triton 별도 compose는 인프라팀이 운영, `triton-net` external로 연결
  4. 학습 데이터 약 **11 GB (HDF5 291건)** 을 GPU 서버 `/home/<user>/data/cooling_project/`로 전송 — 전송 방식: **[확인 필요]** (scp 또는 rsync 추정)
- **검증:** 5개 도구 docker-compose 단일 기동 후, **Triton 메트릭이 Prometheus에 정상 적재되는지 확인**(GPU 메모리 사용량 쿼리로 확인).
- (a) **왜 옮겼나:** 단일 개발 PC(WSL2/RTX 5060 Ti)는 팀 공유·폐쇄망 요건·GPU 성능을 못 채웠다. L40S 서버로 옮기며 **"내 노트북 데모"에서 "팀이 공유하는 서버 스택"으로 격상**한 것이 이 마이그레이션의 본질.

---

### 4.10 라이브 상태 요약 (정정 반영 — 2026-06-19, 상세는 §2 참조) _[휘발성]_

원문(6/1) 대비 2026-06-19 직접 점검에서 바뀐 인프라 사실만 모은다(상세·근거는 각 하위 섹션 및 §2):

| 항목 | 원문 6/1 | 현재 2026-06-19 |
|---|---|---|
| 가동 컨테이너 수 | 7개 | **9개** (+`mlops-portal`, +`evidently-ui`) |
| Triton 서빙 모델 | 5개 | **10개** (6/8 v2 cold/hot 분할 5종 추가, 전부 GPU READY) |
| 외부 포트 매핑 | 9서비스 | **+2** (8510 portal, 8511 evidently-ui) |
| 호스트 GPU 드라이버 | "mismatch, 미정합" | **NVML 580.159.03 vs 커널모듈 580.126.20** mismatch 확정, 컨테이너 GPU는 정상, 재부팅 권한 밖이라 보류 |

- **2026-07-24 재점검**: 컨테이너 9개·Triton 10모델 READY **유지**. 변화분 — 2026-07-09 재부팅(커널 6.8.0-134), NVML mismatch **재발**(모듈 580.159.03 vs lib 580.173.02, §4.1.1), 포털·Evidently 7/21 재배포. 상세는 §2(2026-07-24 스냅샷). _[휘발성]_
- (a) **왜 별도 요약:** 6/1 원문은 라이브 상태를 사실로 박아뒀으나, 이 값들은 시간에 따라 변한다. 면접/서류에서 인용 시 **반드시 검증 일자와 함께** 말하고, 설계·결정(§4.3~4.8)과 라이브 수치를 구분할 것.

---

## 5. 구현 컴포넌트 ① — 추론 서빙·실험관리 (Triton, MLflow)

> **이 섹션의 위상**: Triton(추론 서빙)과 MLflow(실험관리·모델 레지스트리)는 박지상이 **직접 구성하고 운영한 가장 깊은(Deep) 영역**이다. 다른 곳의 Claude는 박지상이 "MLOps를 했다"는 추상적 주장 대신, **이 두 컴포넌트의 기동 인자·config·API 호출까지 손으로 만졌다**는 구체성을 이 섹션에서 인용하라. 면접 STAR의 'Action'과 기술 심화 질문의 1차 방어선이 여기다.

---

### 5.1 NVIDIA Triton Inference Server

#### 5.1.1 이미지 / 버전

- 이미지: `nvcr.io/nvidia/tritonserver:25.07-py3`
- 배경 문서엔 "25.08"로 적혀 있었으나 **실측은 25.07** — 문서 오류를 본인이 컨테이너에서 직접 확인해 정정함.
- **(a) 근거**: 버전 명세를 문서 신뢰가 아니라 런타임 실측으로 검증하는 습관. (b) **활용**: "배포된 서빙 스택의 버전을 추측이 아니라 실측으로 관리한다"는 정직성·운영 감각의 사례로 인용 가능.

#### 5.1.2 기동 명령 (`Args` 실측)

```
tritonserver
  --model-repository=/models
  --model-control-mode=explicit          ← 중요: POLL 아님
  --repository-poll-secs=30
  --strict-model-config=false
  --exit-on-error=false
  --log-verbose=1
  --log-file=/logs/triton.log
  --allow-metrics=true
  --allow-gpu-metrics=true
  --metrics-port=8002
  --http-port=8000
  --grpc-port=8001
```

- **핵심 인자 `--model-control-mode=explicit`**
  - POLL 모드는 `model_repository`의 파일 변화를 보고 자동 로드하지만, **EXPLICIT은 API로 명시 호출해야** 모델이 올라간다 (`POST /v2/repository/models/<name>/load`).
  - **(a) 근거**: CI에서 ONNX를 자동 배포할 때 이 차이가 결정적이다 — **파일 복사만으로는 모델이 안 붙는다.** 그래서 §6 CI(`onnx_deploy.yml`)의 마지막 단계가 반드시 `load` API 호출 + READY 폴링으로 설계되어 있다. POLL이었으면 불필요했을, 그러나 의도적으로 EXPLICIT을 택해 "무엇이 언제 로드되는지를 사람이/CI가 명시적으로 통제"하는 거버넌스 우위를 얻었다.
  - (b) **활용**: "배포 파이프라인을 설계할 때 서버의 model-control-mode 동작 차이를 이해하고 그에 맞춰 CI 단계를 구성했다"는 식으로, 단순 스크립트가 아니라 **시스템 동작을 이해한 통합**을 보여주는 면접 답변.
- `--repository-poll-secs=30`: EXPLICIT 모드에서도 잔존하는 값(POLL 폴백 주기). 실효는 EXPLICIT 우선.
- `--strict-model-config=false`: ONNX 메타데이터로 일부 config 자동 추론 허용.
- `--exit-on-error=false`: 한 모델 로드 실패가 서버 전체를 죽이지 않도록 — 다중 모델 서빙의 가용성 보호.
- `--allow-metrics=true --allow-gpu-metrics=true --metrics-port=8002`: Prometheus 수집을 위한 메트릭 노출(§6 관측 연계).

#### 5.1.3 컨테이너 마운트 (실측)

| 호스트 경로 | 컨테이너 경로 | 모드 | 의미 |
|---|---|---|---|
| `/srv/triton/model_repository` | `/models` | **ro** (read-only) | 모델 저장소를 읽기 전용으로 마운트 → 런타임이 모델 파일을 변조 못 함 |
| `/srv/triton/logs` | `/logs` | rw | 로그만 쓰기 가능 |

- **(a) 근거**: 모델 저장소를 **ro**로 둔 것은 의도적이다 — 서빙 컨테이너가 모델 바이너리를 못 바꾸게 막고, 배포는 오직 호스트측 파일 교체 + load API라는 통제된 경로로만 일어나게 한다. (b) **활용**: "최소 권한(least privilege) 원칙을 마운트 수준에서 적용했다"는 보안·거버넌스 의식 사례.

#### 5.1.4 model_repository 구조 — 원문 5개 → **현재 10개** _[휘발성·2026-06-19 검증, §2 참조]_

원문(2026-06-01) 스냅샷의 구조:

```
/models/
  ├── cooling_unet/1/{model.onnx, config.pbtxt}
  ├── ecotron_flow/1/{...}
  ├── ecotron_thermal_f/1/{...}
  ├── ecotron_thermal_s/1/{...}
  └── resnet50/1/{...}
```

(원문 시점 총 5개 모델, 각 1버전.)

**정정 (CORR 1) — 현재 서빙 모델은 10개**: 2026-06-08에 ecotron PINN의 v2 분할 5종이 추가되어, 2026-06-19 GPU 서버 직접 점검 기준 **10개 모델 전부 GPU(L40S, `gpus[0]`)에 로드·READY** 상태다. 추가된 5종:

| v2 추가 모델 (6/8) | 설명 |
|---|---|
| `ecotron_flow_v2_0608` | 유동 PINN v2 |
| `ecotron_thermal_f_cold_v2_0608` | 유체 열, cold 분할 |
| `ecotron_thermal_f_hot_v2_0608` | 유체 열, hot 분할 |
| `ecotron_thermal_s_cold_v2_0608` | 고체 열, cold 분할 |
| `ecotron_thermal_s_hot_v2_0608` | 고체 열, hot 분할 |

- **v2 분할의 기술적 사유 (CORR 1 연계)**: v1 PINN은 출력 텐서명이 `linear_6`였는데(아래 5.1.6 config 참조), v2 분할 모델은 **출력 텐서명을 `outputs`로 바꿔** 과거 v1에서 발생했던 `linear_6` 차원 mismatch를 회피했다. cold/hot으로 나눈 것은 온도 영역을 분할 학습해 각 영역 정확도를 높이려는 도메인 설계(§11 U-Ecotron PINN 사례 참조).
- **(a) 근거**: 텐서명/차원 mismatch라는 실제 서빙 트러블을 모델 export 단계의 출력명 변경으로 해소 — 서빙과 모델 정의의 인터페이스(텐서 contract)를 이해한 조치. (b) **활용**: "PINN 모델 v2 분할 배포 시 출력 텐서 이름 규약을 정비해 Triton 로딩 mismatch를 제거했다"는 트러블슈팅 STAR(§9 연계).
- **정직 규율**: cold/hot 분할 모델 일부는 MLflow에서 `demo_only`로 태깅되어 있다(아래 5.2.5, CORR 8). 즉 **10개가 모두 운영 품질로 검증된 것은 아니다** — "10개 서빙"은 '로드·READY' 사실이고, '운영 검증 완료'와는 구분해 표현해야 한다.

#### 5.1.5 config.pbtxt — 모델별 실측 (전부 보존)

**`cooling_unet`** (본 과제 핵심, U-Net):

```protobuf
name: "cooling_unet"
platform: "onnxruntime_onnx"
max_batch_size: 4

input [
  { name: "coordinates", data_type: TYPE_FP32, dims: [4, 128, 128, 20] },
  { name: "features",    data_type: TYPE_FP32, dims: [5] }
]
output [
  { name: "cooling_effect", data_type: TYPE_FP32, dims: [1, 128, 128, 20] }
]
instance_group [ { count: 1, kind: KIND_GPU, gpus: [0] } ]
dynamic_batching {
  preferred_batch_size: [1, 2]
  max_queue_delay_microseconds: 100
}
```

**`ecotron_flow`** (PINN, 유동):

```protobuf
name: "ecotron_flow"
platform: "onnxruntime_onnx"
# PINN: 가변 길이 N개 포인트 입력 — 일반 batch 아님
max_batch_size: 0
input  [ { name: "xyz",      data_type: TYPE_FP32, dims: [-1, 3] } ]
output [ { name: "linear_6", data_type: TYPE_FP32, dims: [-1, 4] } ]  # u, v, w, p
instance_group [ { count: 1, kind: KIND_GPU, gpus: [0] } ]
```

**`ecotron_thermal_f`** (PINN, 유체 온도):

```protobuf
name: "ecotron_thermal_f"
platform: "onnxruntime_onnx"
max_batch_size: 0
input  [ { name: "xyz",      data_type: TYPE_FP32, dims: [-1, 3] } ]
output [ { name: "linear_6", data_type: TYPE_FP32, dims: [-1, 1] } ]  # θ_f (무차원, T/273.15 - 1)
instance_group [ { count: 1, kind: KIND_GPU, gpus: [0] } ]
```

**`ecotron_thermal_s`** (PINN, 고체 온도):

```protobuf
name: "ecotron_thermal_s"
platform: "onnxruntime_onnx"
max_batch_size: 0
input  [ { name: "xyz",      data_type: TYPE_FP32, dims: [-1, 3] } ]
output [ { name: "linear_6", data_type: TYPE_FP32, dims: [-1, 1] } ]  # θ_s
instance_group [ { count: 1, kind: KIND_GPU, gpus: [0] } ]
```

**`resnet50`** (데모용):

```protobuf
name: "resnet50"
platform: "onnxruntime_onnx"
max_batch_size: 128
input  [ { name: "data",                  data_type: TYPE_FP32, format: FORMAT_NCHW, dims: [3, 224, 224] } ]
output [ { name: "resnetv17_dense0_fwd",  data_type: TYPE_FP32, dims: [1000] } ]
```

- `resnet50`은 ONNX Model Zoo 표준 모델로, Triton 데모/벤치마크용이며 **본 과제 모델이 아니다.** 정직하게: 이건 박지상이 학습시킨 모델이 아니라 서빙 스택 검증용으로 올린 표준 모델이다.

**config 설계에서 읽어낼 수 있는 사실 (활용 포인트)**
- `cooling_unet` 입력은 좌표 격자 `[4,128,128,20]`(4채널 3D 격자 + 시간/높이축 20) + 운전조건 스칼라 `features[5]`, 출력은 냉각효과 격자 `[1,128,128,20]` — **3D U-Net 회귀** 구조가 config에 그대로 드러난다.
- PINN 3종은 **`max_batch_size: 0` + 첫 차원 `-1`** 으로, "N개의 임의 좌표점을 한 번에 평가"하는 PINN 추론 패턴을 표현. 일반 이미지 배치와 의미가 다르다.
- v1 PINN 출력명이 전부 `linear_6`(PyTorch 마지막 Linear 레이어 자동명)이었던 것이 v2에서 `outputs`로 정비된 배경(5.1.4 참조).

#### 5.1.6 Dynamic Batching 설정 사유

- **`cooling_unet`만** `dynamic_batching` 사용: `preferred_batch_size: [1, 2]`, `max_queue_delay_microseconds: 100`.
- 이 수치 선택 사유: **[기억 안 남 — 실제 부하 측정으로 튜닝한 게 아니라 안전값으로 추정]**
- PINN(ecotron 3종/분할 포함)은 입력 자체가 가변길이 N개 점이라 일반 batch 의미가 달라, `max_batch_size: 0` + 첫 차원 `-1`(dynamic)로 둔다 → dynamic_batching 미사용.
- (b) **활용**: 이 항목은 "정량 성과를 부풀리지 않는다"는 정직성의 견본이다. 다른 Claude는 배칭 수치를 성과로 과장하지 말고, "배칭은 적용했으나 튜닝은 미완"으로 정확히 인용하라(§12 정량 성과, §18 TODO 연계).

#### 5.1.7 모델 교체 방식 (load / unload API)

- `--model-control-mode=explicit`이므로 live reload는 **API 호출 필수**:
  - 로드: `POST http://<host>:28000/v2/repository/models/<name>/load`
  - 언로드: `POST http://<host>:28000/v2/repository/models/<name>/unload`
- 절차: 새 ONNX를 `/srv/triton/model_repository/<name>/<ver>/model.onnx`에 배치 → `load` API 호출 → READY 확인.
- 호스트 model_repo 권한: root 소유로 추정, `<user>` 직접 쓰기 가능 여부 **[확인 필요]** — 현재까지 model 추가는 인프라팀 협조 또는 별도 채널로 수행.
- **(a) 근거 / CI 연계**: 이 load/unload 패턴이 그대로 §6의 `onnx_deploy.yml` 워크플로 골격이다(validate → config 확인 → repo 복사 → `/v2/repository/models/<m>/load` → READY 폴링 → 메타). 즉 "수동 운영 절차를 그대로 CI 단계로 코드화"한 것. (b) **활용**: "수동 배포 절차를 이해하고 그것을 CI로 자동화했다"는 자동화 내러티브의 핵심 근거.

#### 5.1.8 추론 호출 (HTTP, 예시)

```bash
# 모델 메타데이터 조회
curl http://<gpu-server>:28000/v2/models/ecotron_thermal_f

# 추론 (POST)
curl -X POST http://<gpu-server>:28000/v2/models/ecotron_thermal_f/infer \
  -H 'Content-Type: application/json' \
  -d '{
        "inputs": [
          { "name": "xyz", "shape": [N, 3], "datatype": "FP32",
            "data": [[x1,y1,z1], [x2,y2,z2], ...] }
        ]
      }'
```

- KServe v2 추론 프로토콜(HTTP/REST) 사용. 외부 노출 포트는 `28000`(HTTP), `28001`(gRPC), `28002`(metrics)로 호스트 매핑(컨테이너 내부 8000/8001/8002).
- (b) **활용**: "표준 KServe v2 추론 API로 모델을 호출해봤다"는 인터페이스 친숙도 — Postman/curl 예시를 그대로 시연 가능.

#### 5.1.9 Postman 컬렉션

- (구, 6/1 시점) `KETI_Triton.postman_collection.json` — 13 requests, 6 folders (model 메타데이터 / health / load / infer 등 폴더 구성). 위치: `ONNX_simplefied_PINN\` 하위.
- **정정(CORR 18 · 2026-07-24 실측)**: 현재는 **바탕화면 루트로 이동·개명** — `KETI Triton (GPU 서버 <gpu-server>).postman_collection.json` (실제 파일명에는 서버 IP가 포함되어 있어 여기선 마스킹 표기). **8 folders / 28 requests**로 확장 — U-Ecotron v2_0608(parametric cold/hot) 폴더 등 추가. 구 경로에는 파일 없음. _[휘발성·2026-07-24 검증]_

#### 5.1.10 메트릭 (`:28002/metrics`)

- Prometheus가 **15초 주기**로 수집(§6 관측 연계). 드라이버 NVML mismatch(§4·§9, CORR 7)와 **무관하게 `nv_gpu_*` 메트릭은 정상 수집됨** _[휘발성·2026-06-19 검증, §2 참조]_.
- 주요 메트릭 키:
  - `nv_inference_request_success`, `nv_inference_request_failure`
  - `nv_inference_compute_input_duration_us`, `nv_inference_compute_infer_duration_us`, `nv_inference_compute_output_duration_us`
  - `nv_inference_queue_duration_us`
  - `nv_inference_count`, `nv_inference_exec_count`
  - `nv_gpu_utilization`, `nv_gpu_memory_used_bytes`, `nv_gpu_power_usage`
  - `nv_inference_pending_request_count`
- (b) **활용**: "추론 지연을 input/infer/output/queue 단계별로 분해해 관측했다"는 점은 단순 헬스체크를 넘어선 관측 설계 — 메트릭 키를 그대로 인용해 깊이를 증명하라.

---

### 5.2 MLflow (실험관리 · 모델 레지스트리)

#### 5.2.1 이미지 / 버전

- 이미지: `ghcr.io/mlflow/mlflow:v2.18.0`
- **사유 — MLflow 3.x에서 의도적 다운그레이드**: 3.x의 같은 출처(same-origin) 정책 미들웨어 버그가 same-origin 요청을 차단해, **UI에서 모델/실행 삭제가 안 되는** 문제가 있었다. 2.18.0으로 내려 픽스(트러블슈팅 §9 참조).
- **(a) 근거**: 최신 버전이 항상 정답이 아니라는 판단 — 실제 동작 결함을 재현·진단하고 버전 결정을 내린 사례. (b) **활용**: "신규 버전의 회귀(regression)를 발견하고 안정 버전으로 의사결정했다"는 운영 판단력 STAR(§8 의사결정 이력 연계).

#### 5.2.2 기동 명령 (실측)

```
server
  --backend-store-uri sqlite:////mlflow/db/mlflow.db
  --artifacts-destination /mlflow/artifacts
  --serve-artifacts                       # ← 아티팩트 프록시 모드
  --host 0.0.0.0
  --port 5000
```

#### 5.2.3 URI / 저장

- Tracking URI: `http://<gpu-server>:5000` (외부), `http://mlflow:5000` (compose 내부).
- Backend Store: **SQLite** — 컨테이너 `/mlflow/db/mlflow.db` ← 호스트 `/home/<user>/mlops/mlflow/db/mlflow.db` (원문 시점 544 KB).
  - **정직 규율 (CORR 8 연계)**: 백엔드는 PostgreSQL이 아니라 **SQLite**다 — 단일 사용자·소규모 PoC 규모임을 정확히 표현할 것. "프로덕션급 트래킹 서버"로 과장 금지.
- Artifact root: 컨테이너 `/mlflow/artifacts` ← 호스트 `/home/<user>/mlops/mlflow/artifacts`
  - 하위: `1/` (experiment id 1, cooling-project-unet 학습 run들), `2/` (experiment id 2, `external_models_ingest`).
- 백업 파일 존재: `mlflow.db.v3-backup` (808 KB, 2026-05-11) — 3.x → 2.x 다운그레이드 시 보존(5.2.1과 연결되는 다운그레이드 증거).

#### 5.2.4 `--serve-artifacts` 모드 의미

- 클라이언트가 직접 S3/MinIO에 PUT 하지 않고 **MLflow 서버를 프록시로** 사용 → 클라이언트 측 자격증명 불필요, **폐쇄망 친화적**.
- 아티팩트 URI는 `mlflow-artifacts:/<exp>/<run_id>/artifacts/...` 형태(실측 cooling-project-unet v4 source 참조).
- **(a) 근거**: KETI 환경은 폐쇄망 + MinIO 제외 결정(라이선스, §8)이라 객체 스토리지 자격증명을 클라이언트에 뿌리지 않는 프록시 모드가 최적이었다. (b) **활용**: "폐쇄망 제약과 라이선스 제약을 동시에 만족하는 아티팩트 저장 전략을 선택했다"는 제약 하 설계 사례.

#### 5.2.5 등록 모델 (Registry) — 원문 vs 현재 정정 (CORR 8)

**원문(2026-06-01 실측 API 응답 기준)** 의 레지스트리:

| 모델 | 모델 레벨 tag | 버전 | 버전 tag |
|---|---|---|---|
| `cooling-project-unet` | source=internal, model_type=U-Net, domain=cooling_project | v4 | status=deployed, deployed_at=2026-05-20, notes=... |
| | | v3 | status=retired, retired_at=2026-05-26 |
| | | v2 | status=retired, retired_at=2026-05-26 |
| | | v1 | status=retired, retired_at=2026-05-26 |
| `ecotron_flow` | source=ecotron, model_type=PINN, domain=fluid, physics=Navier-Stokes, received_at=2026-05-15, contact="[외부개발팀]" | v1 | status=deployed, received_at=2026-05-15, validated_at=2026-05-18, deployed_at=2026-05-18, notes |
| `ecotron_thermal_f` | source=ecotron, model_type=PINN, domain=thermal, physics=유체 내 열전달, ... | v1 | (위와 동일 패턴) |
| `ecotron_thermal_s` | source=ecotron, model_type=PINN, domain=thermal, physics=고체 내 열전도, ... | v1 | (동일 패턴) |

**정정 (CORR 8) — 2026-06-19 GPU 서버 직접 점검 기준** _[휘발성·2026-06-19 검증, §2 참조]_:

- 등록 모델 **9개 / 버전 14개** (원문의 5모델보다 확장 — ecotron v2 분할 등록분 반영). **정정(CORR 13 · 2026-07-24 API 재실측)**: 6/19 기록 "버전 12개"는 오산 — `ecotron_flow_v2_0608`이 CI 재배포로 **v1(6/8, retired)→v2(6/17, retired)→v3(6/18, deployed)** 3버전을 보유해 총 14개다(cooling 4 + ecotron v1 3종 3 + flow_v2 3 + thermal v2 4종 4).
- **v2 등록분 태그 확장(2026-07-24 실측)**: v2 계열엔 `framework=onnx`, `project`, **`opset=18`**, `scenario=cold/hot`, `delivery_batch=2026-06-08`, `manifest_validation_status` 태그가 추가돼 있다 — cooling 계열(export opset 17, §5.2.7)과 달리 **ecotron v2 ONNX는 opset 18**로 태깅됨.
- **전 버전 `current_stage=None`**: MLflow 표준 스테이지(Staging/Production)를 **쓰지 않고**, 위 표처럼 **태그 기반 거버넌스**(`status=deployed/retired`, `deployed_at`, `validated_at`, `received_at`, `contact`, `model_type`, `domain`, `physics` 등)로 모델 라이프사이클을 관리한다.
  - **(a) 근거**: 표준 스테이지는 단순 3단계라 외부 수령 모델(received/validated)·PINN 도메인 메타·물리 이슈 노트 등 풍부한 거버넌스 정보를 담기 어렵다 → 태그 스키마를 직접 설계해 거버넌스를 표현. (b) **활용**: "MLflow 기본 스테이지 대신 태그 기반 거버넌스 스키마를 직접 설계·운영했다"는 모델 거버넌스 심화 사례(§7 연계).
- **`demo_only` 모델이 서빙 중**: `ecotron_thermal_f_hot_v2_0608`, `ecotron_thermal_s_hot_v2_0608` 등 일부 hot 분할 모델은 `manifest_validation_status=demo_only`로 태깅되고, **노트에 "inlet 대비 약 14℃ 하회" 물리 이슈**가 기록돼 있다. 그럼에도 `triton_loaded=true`로 Triton에 서빙 중이다.
  - **정직 규율(중요)**: 따라서 "10개 모델을 서빙 중"이라고 말할 때, 그중 일부는 **검증 미완(demo_only)** 임을 함께 밝혀야 한다. 물리적으로 의심스러운(inlet 대비 ~14℃ 하회) 결과를 가진 모델이 데모 목적으로 올라가 있는 것이다 — 성과로 포장 금지(§7·§11 연계).

**Experiments (CORR 8)**
- exp `1`: `cooling-project-3d-unet` (cooling-project-unet 학습; Windows 시점 4개 run + GPU 서버 학습).
- exp `2`: `external_models_ingest` (외부 ONNX 등록용 dummy run 보관).
- 현재 실험 **2개**, 학습 런 **4개** (Test R² ≈ 0.95). `external_models_ingest`엔 런 **11개**(외부 ONNX ingest·CI deploy dummy run 누적) _[휘발성·2026-07-24 검증]_.

#### 5.2.6 cooling_unet 실서빙 모델 — 레지스트리 ≠ 실제 서빙 (CORR 2) _[중요]_

- **MLflow 레지스트리상 최신**: `cooling-project-unet` **v4** (2026-05-20 재학습, **Test R² ≈ 0.95**) — `status=deployed`로 태깅됨.
- **그러나 실제 Triton에 서빙되는 ONNX = 2026-05-14 빌드** (md5 `39bba09b…`). v4를 ONNX로 재export·재배포하지 않았기 때문에, 서빙되는 것은 **5/14 모델 (5월14일 빌드, 14본 중 5번째 등으로 '5/14' 표기)** 이다.
  - 2026-06-16에 `onnx_deploy.yml` 워크플로가 돌긴 했으나(§6), 그것은 **같은 5/14 파일을 재복사**한 것 — 새 모델 export가 아니었다.
- **2026-07-24 재확인**: 서빙 파일 md5 `39bba09b…`(15,667,315 B, 서버 파일 mtime 6/16 재복사본) **그대로** — v4 재export 여전히 미수행, 레지스트리↔서빙 갭 유지. _[휘발성·2026-07-24 검증]_
- **(a) 근거 / 정직 규율(최중요)**: 이것은 **"레지스트리의 deployed 태그 = 실제 서빙 바이너리"가 아니라는 갭**을 정직하게 드러내는 핵심 사실이다. 다른 Claude는 절대 "v4(R²0.95)가 서빙 중"이라고 말하면 안 된다. 정확한 진술은:
  > "MLflow에는 v4(5/20 재학습, R²≈0.95)가 등록·deployed 태깅되어 있으나, **Triton 실서빙 바이너리는 5/14 빌드 ONNX**다. v4 ONNX 재export/재배포가 누락되어 레지스트리와 서빙 간 드리프트가 존재한다."

#### 5.2.7 ONNX export opset 정정 (CORR 3)

- ONNX export의 **opset = 17** (`export_onnx.py` 실측). 원문의 "opset 14"는 **부정확**.
- opset 선택 사유는 **[확인 필요]** (왜 17을 택했는지 근거는 미확정).
- (b) **활용**: 수치는 정정값(17)을 쓰되, 근거가 미확정인 부분은 [확인 필요]로 정직하게 남길 것.

#### 5.2.8 클라이언트 코드 패턴

- **학습 측**: `mlflow.set_tracking_uri(...)`, `mlflow.start_run()`, `mlflow.log_params`, `mlflow.log_metric`, `mlflow.pytorch.log_model(..., registered_model_name="cooling-project-unet")`.
- **거버넌스 측**: `MlflowClient(tracking_uri=...).set_registered_model_tag(...)`, `set_model_version_tag(...)`, `create_model_version(name, source="runs:/<id>/model", run_id=...)`.
- **(a) 근거**: 학습 로깅과 거버넌스 태깅을 **분리된 코드 경로**로 구성 — 학습 스크립트(`log_to_mlflow.py`)와 거버넌스 스크립트(`scripts/governance/register_model.py`)가 다른 책임을 진다. (b) **활용**: "MLflow Python 클라이언트로 로깅·레지스트리·태깅을 직접 코드로 다뤘다"는 SDK 친숙도 — 단순 UI 사용자가 아니라 API 레벨 통합자임을 보여줌.

---

### 5.3 이 섹션에서 Claude가 끌어다 쓸 핵심 (요약)

| 주제 | 한 줄 활용 | 정직 경계 |
|---|---|---|
| Triton EXPLICIT 모드 ↔ CI load API | "서버 동작을 이해하고 CI 배포 단계를 설계했다" | 자동 재학습 트리거는 없음(§6) |
| config.pbtxt 직접 작성(5종) | "모델 입출력 텐서 contract를 직접 정의" | resnet50은 데모 모델 |
| dynamic_batching | "배칭 적용 경험 있음" | 부하 튜닝 아님([기억 안 남]), 안전값 |
| MLflow 3.x→2.18 다운그레이드 | "버전 회귀를 진단·결정" | — |
| 태그 기반 거버넌스(stage=None) | "표준 스테이지 대신 태그 스키마 직접 설계" | demo_only 모델 서빙 중 |
| 레지스트리 v4(R²0.95) ↔ 서빙 5/14 | "재export 누락 갭을 점검으로 발견" | **v4가 서빙 중이라고 말하지 말 것** |
| SQLite 백엔드 | "폐쇄망 PoC 트래킹 운영" | 프로덕션급 아님 |

> **STAR 템플릿 (이 섹션 기반)**
> - **S**: 폐쇄망 GPU 서버에 자체 호스팅 모델 서빙·실험관리 스택이 필요. (T) Triton + MLflow를 직접 구성·운영.
> - **A**: Triton을 `--model-control-mode=explicit`로 띄우고 model_repository를 ro 마운트로 보호, 모델별 config.pbtxt(U-Net/PINN 3종/데모)를 직접 작성, load/unload API로 모델 교체. MLflow는 3.x 삭제 버그를 진단해 2.18로 다운그레이드, `--serve-artifacts` 프록시 모드 + SQLite로 폐쇄망 트래킹 구성, 표준 스테이지 대신 태그 기반 거버넌스 스키마 설계.
> - **R**: 10개 모델 GPU 서빙(READY) _[휘발성·2026-06-19]_, Prometheus 단계별 추론 메트릭 관측 연계. **정직 단서**: 레지스트리 v4와 서빙 5/14 바이너리 간 갭, demo_only 모델 서빙, 배칭 미튜닝을 스스로 식별 → 개선 과제로 인지(§18).

---

## 6. 구현 컴포넌트 ② — CI·관측·학습 (Gitea Actions, Prometheus+Grafana, Trainer, Runner)

> 이 섹션은 §5(서빙·실험관리)에 이어 MLOps 스택의 **CI/CD · 관측(Observability) · 학습 자동화** 레이어를 다룬다. 원문(2026-06-01 스냅샷)의 모든 설정 블록·명령·수치를 보존하되, 2026-06-19 GPU 서버 직접 점검에서 드러난 변화(CI 워크플로 2종 추가, ONNX Deploy 실제 성공, validator 인라인 이원화, Streamlit/Evidently 신규 컨테이너, 모니터링 타깃 상태)를 정정 반영했다. 라이브 상태는 _[휘발성]_ 로 표기했으니 인용 전 §2 현재 검증 상태(2026-06-19) 확인 권장.
>

---

### 6.1 Gitea + Gitea Actions (사내 Git + CI 엔진)

**이미지 / 버전**
- `gitea/gitea:latest` (점검 시점 빌드 **1.26.1**)
- (a) 근거: 사내(에어갭에 가까운 GPU 서버) 환경에서 GitHub 의존 없이 Git 호스팅 + CI를 한 컨테이너로 끝내기 위해 Gitea 선택. Actions가 GitHub Actions 워크플로 문법과 호환되어 학습 비용이 낮음.

**데이터 저장**
- 호스트 `/home/<user>/mlops/gitea` → 컨테이너 `/data` (rw)
- SQLite DB: 컨테이너 `/data/gitea/gitea.db`
- 백업: **[확인 필요]** (정기 백업 정책 없음 추정)

**등록 저장소** (리포 구성은 §5·§7과 교차)
- `<org>/cooling-project` — 모델 코드 (`train.py`, `src/`, `export_onnx.py`, `.gitea/workflows/ci.yml`, `test_triton.py`, `log_to_mlflow.py` 등)
- `<org>/mlops-tools` — 거버넌스 도구 (`docs/governance.md`, `scripts/governance/register_model.py`, README, `.gitignore`)
  - **정정(CORR 11):** 원문 6/1 이후 `mlops-tools`가 크게 확장됨 — `services/portal/`(Streamlit 6페이지 포털), `scripts/drift/`(Evidently 드리프트 빌드 도구 `build_reference.py`·`build_workspace.py`), `scripts/ci/onnx_validate.py`(canonical validator)가 추가됨. 즉 mlops-tools = "거버넌스 + 드리프트 도구 + Streamlit 포털"로 역할 확대. (자세한 포털/드리프트는 §6.6, 거버넌스는 §7.)

**사용자 / 권한**
- 유일 admin: `<user>` (email: <user>@keti.re.kr, ID=1)
- 비밀번호 정책: 최소 8자 (admin `user change-password` 명령에서 거부됨으로 검증)
- 현재 비밀번호: 박지상 본인이 UI에서 변경 — **[credential stored separately]**

**Gitea Actions 활성화**
- env `GITEA__actions__ENABLED=true` (compose env)
- 등록 토큰 생성: `gitea actions generate-runner-token` (admin CLI, **인스턴스 전역 토큰**)

---

### 6.2 act_runner (CI 실행기 컨테이너)

**컨테이너 정의**
- 이미지: `gitea/act_runner:latest` (**v0.6.1**)
- 컨테이너명: `act_runner`
- 마운트:
  - `/home/<user>/mlops/act_runner:/data` (rw)
  - `/var/run/docker.sock:/var/run/docker.sock` (rw) — **호스트 도커 데몬 제어용**
- 외부 포트: 없음 (gitea로 **polling**)
- 네트워크: `compose_mlops-net` (compose가 `mlops-net` alias로 부여)
- env:
  - `GITEA_INSTANCE_URL=http://gitea:3000`
  - `GITEA_RUNNER_REGISTRATION_TOKEN=<one-time>` — **[credential stored separately]** (일회성 등록 토큰)
  - `GITEA_RUNNER_NAME=gpu-runner`
  - `GITEA_RUNNER_LABELS=ubuntu-latest:docker://python:3.11-bookworm,ubuntu-22.04:docker://python:3.11-bookworm`
  - `CONFIG_FILE=/data/config.yaml`

**Runner config (`/home/<user>/mlops/act_runner/config.yaml`, 실측 — 전체 보존)**
```yaml
log:
  level: info
runner:
  capacity: 1
  timeout: 30m
  labels:
    - "ubuntu-latest:docker://python:3.11-bookworm"
    - "ubuntu-22.04:docker://python:3.11-bookworm"
cache:
  enabled: false
container:
  network: compose_mlops-net          # ← 잡 컨테이너가 'gitea' 호스트명 해석
  privileged: false
  valid_volumes: []                   # ← 잡이 임의 호스트 마운트 못함 (의도적 제약)
```
- (a) 근거 — 설계 의도 정리:
  - `capacity: 1` → 동시 1잡 (GPU 서버 자원 보호).
  - `container.network: compose_mlops-net` → 잡 컨테이너가 `gitea`/`mlflow`/`triton-server` 같은 서비스 호스트명을 DNS로 해석 가능. (ci.yml에서 `gitea:3000`으로 clone 가능한 이유.)
  - `privileged: false` + `valid_volumes: []` → 잡이 임의 호스트 디렉토리를 마운트하지 못하게 막은 **의도적 보안 제약**. (※ 후술하듯 ONNX Deploy 워크플로는 이 제약을 풀어 `/srv/triton/model_repository`만 화이트리스트로 허용해야 동작 — CORR 9, §6.5 참조.)
  - `cache: enabled: false` → 캐시 미사용(단순화).

**호스트 vs 컨테이너 모드**
- 현재: **컨테이너 모드** — docker.sock 마운트, 잡마다 호스트 도커 데몬을 통해 job 컨테이너 spawn. 라벨이 `docker://image` 매핑.
- 과거 WSL2 시절엔 host 모드 시도했었다가 컨테이너 모드로 정착. **[정확한 시퀀스 확인 필요]**

---

### 6.3 CI 워크플로 ① — `ci.yml` (push 자동 lint + py_compile)

**`.gitea/workflows/ci.yml` 전체 (현재, glibc 호환 — 실측, 2026-06-19에도 동일)**
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      # Runner 라벨 ubuntu-latest → python:3.11-bookworm (glibc) 매핑.
      # python3 / pip / git 모두 이미지에 포함되어 별도 설치 불필요.
      - name: Checkout code
        run: |
          git clone http://token:${{ gitea.token }}@gitea:3000/${{ gitea.repository }}.git .
          git checkout ${{ gitea.sha }}

      - name: Python version
        run: python3 --version

      - name: Install flake8
        run: python3 -m pip install --quiet flake8

      - name: Lint with flake8 (syntax errors only)
        run: |
          python3 -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=mlruns,results,coolling_hdf5_data_new,.git

      - name: Check Python syntax
        run: |
          python3 -m py_compile export_onnx.py
          python3 -m py_compile test_triton.py
          python3 -m py_compile log_to_mlflow.py
```

**Lint 규칙 (`--select=E9,F63,F7,F82`) — 각 코드의 의미**

| 코드 | 의미 |
|---|---|
| `E9` | 문법 오류 (런타임 IndentationError, SyntaxError 등) |
| `F63` | assertion 트라이클 (`assert (a, b)` 형태 등) |
| `F7` | 구문 오류 (pyflakes) |
| `F82` | 정의되지 않은 이름 (`__all__`에 없는 이름 등) |

- → **lint full이 아닌 "터질 게 명백한 것만" 체크** — 스타일(라인 길이·import 순서 등)은 의도적으로 패스.
- (a) 근거: 1인 PoC에서 스타일 게이트는 마찰만 키움. "실제로 실행 시 터지는 치명 오류만 차단"하는 실용적 게이트 설계.

**Lint 대상 / 제외**
- 대상: `.` 전체
- 제외(`--exclude`): `mlruns`, `results`, `coolling_hdf5_data_new`(오타 그대로 — 데이터 폴더), `.git`

**`Check Python syntax` 단계** — `export_onnx.py`, `test_triton.py`, `log_to_mlflow.py` 3개를 `py_compile`로 컴파일 가능성만 확인.

#### glibc 전환 (2026-05-26)
- 과거: Alpine runner + `apk add python3 py3-pip`
- 문제: ONNX 검증 패키지(`onnxruntime`)는 **musl 휠 없음** → Alpine에 설치 실패. 추후 ONNX 검증 자동화로 가는 길이 막힘.
- 변경: 잡 컨테이너 이미지를 `python:3.11-bookworm`(Debian, glibc, ~1GB)로 매핑.
- 효과: `python3`, `pip`, `git` 모두 이미지에 포함 → ci.yml에서 `apk add` 단계 제거. 검증 잡 통과(`action_run` id 4, status=1).
- (a) 근거: 이게 핵심 의사결정 — **미래의 ONNX 검증 자동화(onnxruntime 설치 필요)를 위해 미리 glibc 베이스로 전환**. Alpine(musl)은 onnxruntime 휠 부재로 막다른 길. → 이 전환이 §6.5의 `onnx_validate.yml`/`onnx_deploy.yml`가 가능하게 한 전제다.

#### 14분 hang 이슈 (과거, WSL2 시절)
- 증상: 잡이 checkout 단계에서 **14분 hang** → timeout.
- 원인: 프라이빗 저장소 clone 인증 처리. `actions/checkout` 액션이 인증 토큰을 제대로 처리 못함.
- 해결: `actions/checkout` 대신 직접 `git clone http://token:${{ gitea.token }}@gitea:3000/${{ gitea.repository }}.git .` (URL에 토큰 임베드).
- 결과: 4초 이내 완료. 타임아웃을 보수적으로 5분 → 10분(현재 `timeout-minutes: 10`)으로 설정.
- (a) 근거: Gitea Actions에서 GitHub의 `actions/checkout` 마켓플레이스 액션이 사내 프라이빗 인증과 안 맞음 → raw `git clone`으로 우회. 이 패턴이 이후 모든 워크플로(ci/validate/deploy)의 checkout 표준이 됨.

---

### 6.4 Prometheus + Grafana (관측 레이어)

**Prometheus**
- 이미지: `prom/prometheus:latest`
- 외부 포트 **9090**
- 데이터 볼륨: `prometheus_data` (named volume)
- 보관 기간: **30일** (`--storage.tsdb.retention.time=30d`)
- `--web.enable-admin-api`
- `prometheus.yml` (실측 — 전체 보존):
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "triton"
    static_configs:
      - targets: ["triton-server:8002"]
    metrics_path: "/metrics"
```
- `triton-net`을 external network로 join → 컨테이너 이름으로 직접 접근.
- **정정(CORR 10) — 2026-06-19 라이브 점검:** Prometheus 타깃 **2개(self=prometheus, triton)** 모두 **up**. 알림 룰 **0개**. `node-exporter`/`cadvisor` **없음**(호스트·컨테이너 시스템 메트릭 미수집 — Triton 자체 메트릭만 수집). _[휘발성·2026-06-19 검증, §2 참조]_
  - 중요한 부수 사실: §4/§9의 GPU 드라이버 NVML mismatch(호스트 `nvidia-smi` 실패)와 **무관하게** Triton의 `nv_gpu_*` 메트릭은 정상 수집됨 — Triton이 컨테이너 내부에서 직접 GPU를 읽어 메트릭을 export하기 때문. _[휘발성]_
- (a) 근거: scrape_config가 self + triton 2개뿐인 건 "Triton 서빙 GPU 메트릭 관측"이라는 단일 목적에 맞춘 최소 구성. node-exporter/cadvisor를 안 깐 건 PoC 범위 한정.

**Grafana**
- 이미지: `grafana/grafana-oss:latest` (점검 시점 버전 **13.0.1** — CORR 10) _[휘발성]_
- 외부 포트 **3001 → 컨테이너 3000**
- env: 기본 자격증명 **[credential stored separately]**, `GF_SECURITY_ALLOW_EMBEDDING=true`, `GF_AUTH_ANONYMOUS_ENABLED=true`, `GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer`
  - (a) 근거: `ALLOW_EMBEDDING=true` + 익명 Viewer 허용 → **Streamlit 포털의 iframe 임베드**(§6.6의 3_Triton_모니터링 페이지가 Grafana 패널을 iframe으로 박음)를 위한 설정. 즉 Grafana 노출 설정이 포털 통합을 전제로 잡혀 있음.
- 프로비저닝 IaC (코드로 데이터소스·대시보드 자동 등록 — 전체 보존):
  - `provisioning/datasources/prometheus.yml`:
    ```yaml
    apiVersion: 1
    datasources:
      - name: Prometheus
        uid: prometheus
        type: prometheus
        access: proxy
        url: http://prometheus:9090
        isDefault: true
        editable: true
    ```
  - `provisioning/dashboards/default.yml`:
    ```yaml
    apiVersion: 1
    providers:
      - name: default
        orgId: 1
        folder: ""
        type: file
        disableDeletion: false
        editable: true
        options:
          path: /var/lib/grafana/dashboards
    ```
  - 대시보드 파일: `/var/lib/grafana/dashboards/triton.json`

**7패널 커스텀 대시보드 (Triton 25.07 메트릭에 맞춰 설계)**
- 2026-06-19 점검: `triton.json` **로드 확인**, **7패널** Triton 대시보드 (CORR 10). _[휘발성]_
- **정정(CORR 17) — 2026-07-24 Grafana API(`/api/dashboards/uid/triton-main`) 실측으로 패널 제목 확정** (기존 [확인 필요] 해소). 대시보드 uid `triton-main`, 제목 "Triton Inference Server", 7패널:
  1. Inference Requests / sec
  2. Compute Time (ms, p50/p99 est.)
  3. Cumulative Inference Count
  4. GPU Utilization
  5. GPU Memory Used (GB)
  6. GPU Power (W)
  7. Pending Requests
  - 과거 후보 목록에 있던 "평균 queue 시간" 패널은 실제 대시보드에 **없음**. 각 패널의 PromQL 원문은 여전히 **[확인 필요]**(쿼리 필드 미덤프) — 지어내지 말 것. _[휘발성·2026-07-24 검증]_

**알림 설정**: **없음** (Alertmanager 미설치). 2026-06-19 재확인 — Prometheus 알림 룰 **0개**(CORR 10). **2026-07-24 재확인 — 여전히 0개.**

**모니터링 검증 방식 (정직 규율 — 중요)**
- 정식 부하 테스트 **아님**. "수집 파이프라인 정상 동작 확인" 목적.
- 추론 트리거 시 GPU 전력/사용률 메트릭이 즉시 반영되는 것을 **육안 확인**.

---

### 6.5 CI 워크플로 ② — ONNX 검증·배포 자동화 (정정 CORR 9, 신규)

> 원문 6/1 스냅샷에는 `ci.yml` **하나뿐**이었으나, 2026-06-19 리포 점검 결과 `.gitea/workflows/`에 **`onnx_validate.yml`** 과 **`onnx_deploy.yml`** 2종이 추가됨(파일 실측). §6.3의 glibc 전환이 바로 이 두 워크플로(둘 다 onnxruntime 설치 필요)를 가능케 한 포석이었다.

**현 CI 구성 (3개 워크플로):**

| 워크플로 | 트리거 | 역할 |
|---|---|---|
| `ci.yml` | **push/PR (자동)** | flake8 치명오류 lint + 핵심 3스크립트 py_compile |
| `onnx_validate.yml` | **workflow_dispatch (수동)** | ONNX 파일 3단계 검증 |
| `onnx_deploy.yml` | **workflow_dispatch (수동)** | 검증 → config 확인 → repo 복사 → Triton load API → READY 폴링 → MLflow 거버넌스 갱신 |

- **자동 재학습/재배포 트리거(스케줄·태그·레지스트리 이벤트)는 없음** — validate/deploy는 모두 수동(`workflow_dispatch`). (정직: "이벤트 기반 자동 파이프라인"으로 과장 금지.)

#### `onnx_validate.yml` (수동, 실측)
- 입력: `onnx_path`(기본 `results/cooling_unet.onnx`), `batch`(기본 `2`)
- 잡: `python:3.11-bookworm`에서 `pip install onnx onnxruntime numpy` → `python3 .gitea/scripts/onnx_validate.py <path> --batch <n>` 실행.

#### `onnx_validate.py` 검증기 (3단계, 실측)
1. `onnx.checker.check_model` — 구조/스펙 검증 (ir_version·opset·producer 출력)
2. **dynamic shape 확인** — 입력에 동적 batch dim(None/symbol)이 있는지. 기본 `--require-dynamic-batch=True`(동적 dim 없으면 FAIL), `--no-require-dynamic-batch`로 해제 가능.
3. **onnxruntime 더미 추론** — CPUExecutionProvider로 랜덤 입력 추론, 출력 finite/min/max 검사(non-finite면 FAIL).
- Exit code: 0=PASS(green), 1=FAIL(red).
- (a) 근거: "구조 OK → 동적 배치 OK → 실제 로드·실행 OK"의 3단 게이트로 Triton 배포 전에 깨질 모델을 거름. 동적 batch 강제는 Triton dynamic batching(§5 교차) 전제.

#### validator 인라인 이원화 (CORR 9 — drift 위험, 정직 명시)
- canonical 위치: **`<org>/mlops-tools` → `scripts/ci/onnx_validate.py`**.
- 그러나 **`mlops-tools`가 org private** 이라 CI 잡 컨테이너가 cross-repo clone 불가 → `cooling-project` 리포에 **`.gitea/scripts/onnx_validate.py` 인라인 사본**을 둠(파일 docstring에 "한시적 인라인 사본, 변경 시 양쪽 동기화" 명시).
- → **두 사본 간 drift(동기화 누락) 위험**이 구조적으로 존재. (이건 최근 커밋 이력 `62c510e Revert: 인라인 사본 유지(조직 visibility=private라 cross-repo clone 불가)`와도 일치 — §9/§18 교차.)

#### `onnx_deploy.yml` (수동, 실측 — 전체 단계 보존)
- env: `TRITON_BASE=http://<gpu-server>:28000`, `REPO_MOUNT=/triton-repo`, `MLFLOW_TRACKING_URI=http://mlflow:5000`
- 잡 컨테이너 `python:3.11-bookworm` + **volume `/srv/triton/model_repository:/triton-repo`** (→ act_runner의 `valid_volumes` 화이트리스트에 이 경로가 허용돼야 동작; §6.2 의도적 제약과 연결).
- 입력: `model_name`(기본 `cooling_unet`), `onnx_path`(기본 `results/cooling_unet.onnx`), `version`(기본 `1`), `skip_validate`(기본 false), `mlflow_name`(기본 `cooling-project-unet`), `skip_mlflow`(기본 false)
- 단계 (순서대로):
  1. **Checkout** — raw `git clone http://token:…@gitea:3000/…`(14분 hang 회피 패턴 재사용)
  2. `pip install onnx onnxruntime numpy requests`
  3. **Show input** — 파일 존재·바이트 크기 출력
  4. **Validate ONNX** (`skip_validate != true`일 때) — 인라인 `onnx_validate.py --batch 1` 재사용
  5. **Check config.pbtxt exists** — `${REPO_MOUNT}/<model>/config.pbtxt` 없으면 FAIL("config.pbtxt를 먼저 등록해야 함") — Triton EXPLICIT 모드 전제(§5 교차)
  6. **Copy ONNX to model repository** — `<repo>/<model>/<version>/model.onnx`로 복사
  7. **Triton load API call** — `POST {TRITON_BASE}/v2/repository/models/<model>/load`, HTTP 200 아니면 실패
  8. **Wait for READY** — `GET /v2/models/<model>/ready`를 2초 간격 최대 20회(=40초) 폴링, 200이면 성공·아니면 FAIL
  9. **Show deployed model metadata** — `GET /v2/models/<model>` JSON 출력
  10. **Update MLflow governance** (`skip_mlflow != true`일 때) — `pip install mlflow==2.18.0` 후 `.gitea/scripts/mlflow_update.py --name <model> --mlflow-name <mlflow_name> --onnx-path <path> --notes "CI deploy (gitea run #…, sha …)"`
- (a) 근거: Triton의 EXPLICIT model_control_mode(§5)를 활용해 **"검증 → 배치 → load API → READY 확인 → 거버넌스 기록"** 전체 배포 체인을 워크플로 하나로 묶음. `mlflow_update.py`는 CI deploy 끝에 MLflow 거버넌스를 자동 갱신(커밋 `3ad026f`).
- **실제 성공 실행 확인 (CORR 9):** ONNX Deploy 워크플로가 **2026-06-16 06:56에 끝까지 1회 성공 실행됨**. _[휘발성·2026-06-19 검증, §2 참조]_
  - 단, **정직 단서(§5/§7 교차):** 이 6/16 실행은 신규 모델 배포가 아니라 **기존 2026-05-14 빌드 cooling_unet ONNX(md5 39bba09b…)의 재복사**였음. MLflow엔 `cooling-project-unet v4`(5/20 재학습, Test R²≈0.95)가 있으나 ONNX 재export·재배포는 안 됨 → **실서빙 모델은 여전히 5/14 빌드**. "최신 학습 모델이 자동 배포된다"고 오해하면 안 됨.

---

### 6.5A `mlflow_update.py` — CI 끝단 거버넌스 자동 갱신 (동시-deployed-1개 원칙)

> §6.5 ONNX Deploy 워크플로의 마지막 단계로 추가된 거버넌스 자동 갱신 스크립트. **"한 시점에 한 모델당 deployed 1개"** 원칙을 코드로 강제. §7.5 v2 스키마 격상의 직접 산출물.

#### 6.5A.1 동작 4단계

`mlops-tools/scripts/ci/mlflow_update.py` (cooling-project-3d-unet `.gitea/scripts/`, ecotron-pinn `.gitea/scripts/` 양쪽에 인라인 사본 — §8.9 validator 이원화 패턴과 동일):

1. **이전 deployed retire**: `client.search_model_versions("name='X'")` 순회 → 기존 `status=deployed` 모두 `status=retired` + `retired_at=ISO 8601 now` + notes append (500자 cap, 기존 notes 유지)
2. **artifact 업로드**: `external_models_ingest` experiment에 ONNX 파일을 `mlflow.log_artifact()` — 새 run 생성, run_id 확보
3. **새 model_version 생성**: `client.create_model_version(name=mlflow_name, source=f"runs:/{run_id}/model", run_id=run_id)` — MLflow 자동 v 번호 증가
4. **deployed 마크**: 새 버전에 `status=deployed`, `deployed_at=<now ISO 8601>`, `notes=CI deploy (gitea run #X, sha Y)` 태그 박음

#### 6.5A.2 핵심 인자 분리

```python
parser.add_argument("--name", required=True,
    help="Triton 모델 이름 (예: cooling_unet)")
parser.add_argument("--mlflow-name", default="",
    help="MLflow Registered Model 이름 (Triton 이름과 다를 때만)")
```

- **`--name`** = Triton 모델 이름 (snake_case: `cooling_unet`, `flow`)
- **`--mlflow-name`** = MLflow Registered Model 이름 (kebab-case: `cooling-project-unet`) — 미지정 시 `name` 사용
- cooling-project-3d-unet의 경우: Triton `cooling_unet` ↔ MLflow `cooling-project-unet` 매핑 = `--mlflow-name=cooling-project-unet` 명시
- ecotron-pinn의 경우: 양쪽 동일하므로 `--mlflow-name` 생략 가능

#### 6.5A.3 사전 조건 (의도된 제약)

- **Registered Model 자체는 사전 등록 필수** — CI가 자동 생성 안 함
- 이유: 단일 등록 경로(포털 `1_모델_업로드.py` 또는 CLI `register_external_model`) 유지 = source/contact/model_type 누락 방지
- 사전 등록 없으면 `mlflow_update.py` 가 명시적 에러 (`mlflow.exceptions.RestException`)

#### 6.5A.4 의도된 부작용 (긍정적)

- MLflow UI에서 한 모델의 lifecycle 흐름이 **하나의 deployed → 여러 retired**로 시각화됨
- "현재 무엇이 떠있나" 가 tag 한 조회로 즉답: `client.search_model_versions("name='X' and tags.status='deployed'")`
- 거버넌스 정합성을 "사람이 mark_deployed/retired 호출 잊었나" 걱정 안 해도 됨

#### 6.5A.5 CI 워크플로 끝단 호출 형태

```yaml
# .gitea/workflows/onnx_deploy.yml 마지막 step
- name: Update MLflow governance
  if: success()
  run: |
    python3 .gitea/scripts/mlflow_update.py \
      --name ${{ inputs.model_name }} \
      --mlflow-name ${{ inputs.mlflow_name || inputs.model_name }} \
      --onnx-path /srv/triton/model_repository/${{ inputs.model_name }}/${{ inputs.version }}/model.onnx
```

#### 6.5A.6 검증 이력

- **2026-06-18 ecotron-pinn fan-out**: 5개 모델 dispatch 실행. **정정(CORR 14 · 2026-07-24 레지스트리 API 실측)**: 기존 기록 "각 모델당 v2 retire + v3 deploy 자동 전이 검증 완료"는 **`ecotron_flow_v2_0608`에만 해당** — v1(6/8 등록→6/17 retired) → v2(6/17→6/18 retired) → v3(6/18 deployed) 전이가 실측된다. **thermal cold/hot 4종은 v1 그대로**(cold 2종 v1=deployed, hot 2종 v1=`status=received`·demo_only)로, fan-out으로 새 버전이 생성되지 않았다. retire→deploy 자동 전이 검증 자체는 flow_v2 기준으로 유효하나 "5개 모델 각각 전이"는 부정확 — 과장 금지.
- **2026-06-19 cooling-project-unet**: workflow 도는 동안 별도 모델로 retire+deploy 갱신 확인

"CI 끝단에서 거버넌스 정합성(동시 deployed 1개·timestamp ISO 8601·notes append·run artifact 추적)을 코드로 강제하는 `mlflow_update.py`를 설계했다 — §7.5 v2 스키마의 정합성을 CI가 직접 보장하는 첫 사례."

---

### 6.6 Streamlit 포털 + Evidently 드리프트 (신규 컨테이너, CORR 4·5 — 휘발성 PoC)

> 원문 6/1엔 없던 컴포넌트. 2026-06-19 점검에서 GPU 서버 compose에 **신규 2개 서비스가 추가**되어 가동 중. 둘 다 **PoC/런타임 설치 패턴**이고, **단독 Dockerfile은 mlops-tools 리포에 있으나 compose 서비스 정의는 서버측 compose에만 추가됨**(리포에 완전 박제 안 됨) → 라이브 상태 _[휘발성]_.
>
> **[2026-07-24 갱신]**: 서버 compose에 포털·Evidently가 **정식 서비스(`portal`, `evidently_ui`) + named volume 5종**(portal_pip_cache·evidently_pip_cache·drift_workspace·prometheus_data·grafana_data)으로 등재됨. 리포의 Dockerfile은 **빌드 시 의존성 박제형**(python:3.11-slim + `pip install -r requirements.txt`)으로 개정됐으나, **서버 가동 컨테이너는 여전히 runtime `pip install` 패턴**(pip 캐시 볼륨으로 보완, 이미지 python:3.11-slim — Dockerfile 빌드 이미지 미적용). 드리프트 데이터는 bind mount → **named volume(`drift_workspace`)** 로 이동. 포털·Evidently는 7/21 재배포(코드 = 7/14~15 개편분 + 7/21 드리프트 전환분, §6.10.10·§6.11.7). _[휘발성·2026-07-24 검증]_

**가동 컨테이너 변화 (CORR 6):** 원문 6/1엔 **7개**였으나 2026-06-19엔 **9개**(+`mlops-portal`, +`evidently-ui`). _[휘발성·2026-06-19 검증, §2 참조]_

#### Streamlit 포털 (`mlops-portal`, CORR 4)
- 가동: 컨테이너 `mlops-portal`, 포트 **8510 → 8501**, HTTP 200, uptime ~24h. _[휘발성·2026-06-19 검증]_ (2026-07-24 기준: 7/21 재배포 후 ~3일 가동, HTTP 200)
- 코드: `<org>/mlops-tools` 리포 `services/portal/`, **6페이지** (→ **2026-07-14~15 대개편으로 5뷰 구조로 재편 — §6.10.10 참조.** 아래는 6/19 시점 기록):
  1. **모델 업로드** — 검증 → Triton load → MLflow 등록
  2. **모델 리스트** — Model Card 편집
  3. **Triton 모니터링** — health + metrics + **Grafana iframe**(§6.4의 embedding 허용 설정이 이걸 위함)
  4. **거버넌스 트렌드** — MLflow tag 기반 Plotly 차트(§7 거버넌스 태그 교차)
  5. **추론 테스트** — shape 자동감지 입력 UI(§5 텐서 정의 교차)
  6. **드리프트** — Evidently iframe + reference 재생성
- 패턴: **런타임 `pip install` PoC 패턴**(이미지 빌드 시 의존성 박제가 아니라 컨테이너 기동 후 설치). 단독 Dockerfile은 있으나 **compose 서비스 정의는 서버측 compose에만 추가됨**(리포 미박제).
- (a) 근거: 선임/회의 피드백의 "UI 도입"(MEMORY: WBS 규칙) 흐름과 맞물려, MLflow/Triton/Grafana/Evidently를 한 화면에서 다루는 운영 포털을 PoC로 구축. 런타임 pip install은 빠른 반복(PoC) 우선.

#### Evidently 드리프트 (`evidently-ui`, CORR 5 — PoC)
- 가동: 컨테이너 `evidently-ui`, 포트 **8511 → 8001**, HTTP 200, uptime ~24h. _[휘발성·2026-06-19 검증]_
- **reference = 실제 데이터** — HDF5 metadata `attrs`에서 5개 feature 추출(커밋 `9d8bcd7`로 dummy → real 전환).
- **그러나 current = 합성** — `reference.sample()` + 점진적 이동(synthetic). → 즉 "실측 reference vs 합성 current"의 PoC. **실제 운영 트래픽 드리프트가 아님**(정직 핵심).
- 스냅샷 **7개 전부 2026-06-18 06:30에 1회 수동 생성**(cron/CI 없음 → 자동 드리프트 모니터링 아님).
- `reference_features.csv`는 **cooling-project 리포에 미커밋(untracked)**.
- 드리프트 빌드 도구: `mlops-tools/scripts/drift/build_reference.py`·`build_workspace.py`.
- (a) 근거: 데이터 드리프트 관측을 Evidently로 PoC 도입. reference를 dummy에서 실제 HDF5 attrs 기반으로 끌어올린 게 진척(`9d8bcd7`). 단 current가 합성·스냅샷 수동 1회라 "관측 파이프라인의 형태"까지가 현 단계.
- **[2026-07-21 격상]**: current가 합성 → **실제 추론 입력 적재 구조**로 전환됨 — §6.11.7 참조(단 2026-07-24 기준 실요청 유입 0건·시드만 존재).

---

### 6.7 PyTorch Trainer 컨테이너 (학습 자동화)

**이미지 / 마운트**
- `pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime`
- 컨테이너명 `trainer`
- runtime: `nvidia`, GPU 1개 점유 (`NVIDIA_VISIBLE_DEVICES=all`)
- 마운트:
  - `/home/<user>/mlops/trainer/workspace:/workspace` (rw, 학습 코드 + 결과)
  - `/home/<user>/data/cooling_project/coolling_hdf5_data_new:/data:ro` (학습 데이터 **11GB**)
- working_dir: `/workspace`
- env (실측):
  - `MLFLOW_TRACKING_URI=http://mlflow:5000`
  - `PYTHONIOENCODING=utf-8`, `PYTHONUNBUFFERED=1`
  - `NVIDIA_VISIBLE_DEVICES=all`, `NVIDIA_DRIVER_CAPABILITIES=compute,utility`
  - `PYTORCH_VERSION=2.5.1`
- **참고(§4/§9 교차):** 호스트 `nvidia-smi`는 NVML mismatch로 실패하지만, **컨테이너 내부 GPU는 정상**(trainer가 L40S 사용, `torch.cuda.is_available()=True`). _[휘발성]_

**idle + `docker exec` 트리거 패턴**
- `command: ["tail", "-f", "/dev/null"]` → 컨테이너 항상 떠있음(idle).
- 학습 시작 방법:
  ```
  ssh <gpu-server> "sudo docker exec -d trainer bash /workspace/_run_train.sh"
  ```
- `_run_train.sh` (요지 — 보존):
  ```sh
  export PATH=/opt/conda/bin:$PATH
  export MLFLOW_TRACKING_URI=http://mlflow:5000
  python -u train.py --data-dir /data --output-dir /workspace/results \
    > /tmp/train_run.log 2>&1
  ```
- 사유: `docker run`/`compose run`이 **NOPASSWD에 없어서** 매번 새 컨테이너를 못 띄움 → **idle 컨테이너 + `docker exec`로 우회**.
- (a) 근거: GPU 서버에서 박지상에게 부여된 sudo가 NOPASSWD 화이트리스트(특정 compose 명령만) 한정이라(§4/§14 교차), `docker run`을 매번 못 침 → "항상 떠있는 컨테이너에 exec로 잡 주입"이 권한 제약을 우회하는 현실적 설계.

**MLflow 자동 기록 흐름** (§5 MLflow와 교차)
- `train.py` 안에서 MLflow 클라이언트가 `MLFLOW_TRACKING_URI` env로 자동 접속.
- 메트릭 / 파라미터 / 아티팩트 / 모델을 `registered_model_name="cooling-project-unet"`로 자동 등록.
- → MLflow `--serve-artifacts`가 받아서 호스트 `/home/<user>/mlops/mlflow/artifacts/`에 저장.
- **정정 참고(CORR 8, §7 교차):** 현재 MLflow 실험 2개(`cooling-project-3d-unet`, `external_models_ingest`), 학습 런 4개(Test R²≈0.95), 등록모델 9개/버전 14개(CORR 13). 전 버전 `current_stage=None`(표준 스테이지 미사용 — 태그 기반 거버넌스). 백엔드 SQLite. _[휘발성·2026-07-24 검증, §2 참조]_

---

### 6.8 act_runner 재설치 작업 (2026-05-26)

**기존 상태**
- 컨테이너 자체가 없는 상태(`docker ps`에 act_runner 없음). 과거 WSL2 시절의 runner가 GPU 서버 이전 시 누락됨.

**재설치 절차 (수행한 그대로 — 전체 보존)**
1. 등록 토큰 발급: `sudo docker exec -u git gitea gitea actions generate-runner-token`
2. Triton 컨테이너의 네트워크 이름 확인: `compose_mlops-net` (compose 프로젝트 prefix)
3. `/home/<user>/mlops/act_runner/config.yaml` 작성 (라벨 매핑 + `container.network=compose_mlops-net`)
4. `docker-compose.yml`에 act_runner 서비스 추가 (백업 후 `awk` 대신 `head/tail`로 안전 삽입, `docker compose -f ... ps`로 파싱 검증)
5. `sudo docker compose up -d act_runner` (NOPASSWD 허용 명령)
6. 로그 확인: `Runner registered successfully` + `runner: gpu-runner, with version: v0.6.1, with labels: [ubuntu-latest ubuntu-22.04]`
7. `ci.yml`을 glibc 호환으로 갱신 (Alpine `apk` 단계 제거) + 푸시 → run 통과 확인 (`action_run` id 4, status=1)

**검증**
- gitea DB(`/data/gitea/gitea.db`)에서 `SELECT id,status FROM action_run ORDER BY id DESC` 로 직접 확인. status=1 (Success).
- (gitea Actions REST API는 이 버전에서 `/actions/runs`가 **404** — DB 직접 조회로 대체.)
- (a) 근거: compose YAML 수정 시 `awk` 대신 `head/tail`로 안전 삽입 + `compose ps`로 파싱 검증한 건 "프로덕션 compose를 깨뜨리지 않으려는" 신중한 절차. Actions REST API 404를 SQLite 직접 조회로 우회한 건 도구 한계를 우회하는 실무 감각.

---

- **CI/CD 서사:** "Gitea + self-hosted act_runner로 사내 CI를 구성. push 시 flake8 치명오류 lint + py_compile(`ci.yml`), 수동 트리거로 ONNX 3단 검증(`onnx_validate.yml`)과 검증→Triton load API→READY 폴링→MLflow 거버넌스 갱신을 잇는 배포(`onnx_deploy.yml`)를 구축. ONNX Deploy는 2026-06-16 end-to-end 1회 성공." — 단 자동 재학습 트리거 부재, 6/16은 동일 파일 재복사, validator 인라인 이원화(drift 위험)는 솔직히.
- **관측 서사:** "Prometheus(triton 타깃 scrape, 30d retention) + Grafana(IaC provisioning, 7패널 Triton 대시보드, 익명 임베드)로 GPU 추론 메트릭 수집·시각화. Streamlit 포털에 Grafana iframe 통합." — "부하 테스트"가 아니라 "메트릭 수집 검증", 알림 룰 0개·시스템 메트릭 미수집은 사실대로.
- **학습 자동화 서사:** "GPU 트레이너 컨테이너(PyTorch 2.5.1+CUDA12.1)를 idle+docker exec 패턴으로 운영(제한된 NOPASSWD sudo 우회), train.py가 MLflow에 메트릭·모델 자동 등록."
- **표현 규율 재확인(§13):** 단독→주도 / 데이터 확장→통합 / 부하테스트→메트릭 수집 검증 / 바이브코딩 표현 금지. 스크립트류(ci.yml, onnx_validate.py 등)는 AI 도구(Claude Code) 보조로 작성했음을 구분(§4.2 산출물 표 교차).

> **교차참조:** Triton 서빙·MLflow 레지스트리는 §5, 모델·거버넌스 태그는 §7, 의사결정 이력(glibc 전환·EXPLICIT 모드 등)은 §8, 트러블슈팅(14분 hang·NVML mismatch·validator drift)은 §9, 성숙도/한계는 §10·§18, 시크릿(자격증명 raw)은 §17. **포털 6페이지 글로벌 패턴 매핑은 §6.10, 드리프트 실데이터 전환은 §6.11 참조.**

---

### 6.10 Streamlit 포털 6페이지 — 글로벌 플랫폼 패턴 매핑 (2026-06-17~18 격상)

> §6.6에서 "신규 PoC 컨테이너 추가"로 한 단락만 다뤘던 mlops-portal을 격상해 6페이지 풀스펙으로 작동. **[선임연구원A] 선임 "글로벌 플랫폼 사이클 사례조사" 피드백에 대한 답을 별도 doc 작성 대신 포털 자체로 갈음**. HF Hub + HF Spaces + SageMaker Pipeline + Vertex Monitoring + Grafana embed + Prometheus 클라이언트 6종 패턴을 한 UI에 묶었다. _[휘발성·2026-06-19 검증]_

#### 6.10.1 페이지 책임 표

| # | 페이지 파일 | 핵심 동작 | 외부 통합 |
|---|---|---|---|
| Home | `Home.py` | 스택 헬스 3 metric (MLflow 모델수 + deployed 버전수 + Triton READY) | MLflow + Triton |
| 1 | `1_모델_업로드.py` | 3-stage 원클릭 (검증→Triton load→MLflow register) — source_type=external 시 contact 필수 | onnx_validate + Triton load + `register_external_model` |
| 2 | `2_모델_리스트.py` | Model Card 마크다운 인라인 편집, v2 준수율 표시, 키워드·source·status 검색·필터 | MLflow tag + description |
| 3 | `3_Triton_모니터링.py` | `nv_inference_*` 직접 파싱(prometheus_client) + Grafana d-solo 4패널 iframe | Triton metrics + Grafana embed |
| 4 | `4_거버넌스_트렌드.py` | status / source_type / domain / model_type 분포 + 라이프사이클 타임라인 | MLflow tag 전용 (Plotly 4종 차트) |
| 5 | `5_추론_테스트.py` | `/v2/models/<m>` 스키마 자동 감지 → 입력 위젯 자동 생성 → v2 protocol POST | Triton HTTP |
| 6 | `6_드리프트.py` | Evidently UI iframe + reference 분포 요약 + 재생성 트리거 (subprocess) | Evidently + subprocess |

#### 6.10.2 글로벌 플랫폼 차용 패턴 매핑 (선임 사례조사 피드백 응답)

| 패턴 | 출처 플랫폼 | 우리 적용 페이지 |
|---|---|---|
| Model Card 마크다운 인라인 편집·렌더링 | **Hugging Face Hub** | 페이지 2 |
| 모델 선택 → 입력 위젯 자동 생성 → JSON 결과 | **HF Spaces** | 페이지 5 |
| 업로드 → 검증 → 배포 → 등록 단일 트리거 | **SageMaker Pipeline** | 페이지 1 |
| DataDriftPreset 임베드 | **Vertex AI Model Monitoring** | 페이지 6 |
| `d-solo` URL iframe (대시보드 1패널 단독 임베드) | **Grafana 공식 임베드 가이드** | 페이지 3 |
| Prometheus exposition 직접 파싱 | **prometheus_client (공식 SDK)** | 페이지 3 |

#### 6.10.3 핵심 설계 결정

- **이중 URL 분리** — `TRITON_BASE`(컨테이너 내부 docker DNS, `http://triton:8000`) vs `TRITON_PUBLIC_URL`(브라우저 노출 호스트 IP, `http://<gpu-server>:28000`) 한 `config.py`에서 분리. mlflow도 동일 패턴(`MLFLOW_TRACKING_URI` vs `MLFLOW_PUBLIC_URL`).
- **포털이 `/srv/triton/model_repository`에 직접 쓰기** — Argo/Pipeline 경유 안 함. 9 모델 규모에 맞춤. `/data/hdf5` 학습 데이터도 read-only 마운트.
- **mlops-tools 루트를 Dockerfile 빌드 컨텍스트로** → `services/portal`이 `scripts/{governance,ci,drift}` 모두 직접 import (sys.path 추가)
- **MLflow 클라이언트 == 2.18.0 핀** — 2.22+ SDK의 prompt 필터(`mlflow.prompt.is_prompt != true` 자동 부착)가 2.18 서버 호환 안 됨. 디버깅 끝에 발견.

#### 6.10.4 GPU 서버 배포

- **컨테이너**: `mlops-portal` (python:3.11-slim 기반, 런타임 pip install PoC 패턴)
- **포트**: host `8510` → container `8501`
- **네트워크**: `mlops-net` + `triton-net` 양쪽 attach
- **마운트**: mlops-tools 코드 (read-only) + `/srv/triton/model_repository` (read-write) + `/data/hdf5` (read-only) + `/data/drift` (Evidently workspace 공유)
- **compose 서비스 정의는 서버측 `/home/<user>/mlops/compose/docker-compose.yml`에만 추가됨** — repo에 박제 안 됨 _[휘발성, §18.7 신규 TODO]_

#### 6.10.5 운영 자동화

PowerShell `redeploy-portal` 함수 — 로컬 git push → `ssh <gpu-server>` → `git pull` → `sudo docker compose restart portal` 한 줄 wrapping. 사용자 PS profile에 등록(`Set-ExecutionPolicy CurrentUser RemoteSigned` 후 `$PROFILE`에 함수 박음). 일주일에 두세 번 편집 패턴에 맞춤 (cron 폴링 거부).

#### 6.10.6 포지셔닝 — 선임 피드백 응답으로서

- [선임연구원A] 선임 6월 피드백: "타 AI 글로벌 플랫폼에서 모델관리·CI/CD·파이프라인을 어떻게 하는지 사례 조사 + 우리 안 제시"
- **별도 사례조사 doc 작성을 의식적으로 거부**, 대신 포털을 그 답으로 갈음
- 6.10.2 표가 사례조사 결과 본문 = "벤치마킹한 6개 패턴을 KETI 규모에 맞춰 6페이지로 압축 구현"
- 회의 발표 시 포털 시연 = 사례조사 결과 발표

"별도 사례조사 문서 작성을 거부하고 **HF Hub + HF Spaces + SageMaker + Vertex + Grafana + Prometheus 6종 글로벌 패턴을 한 Streamlit 포털(6페이지)로 압축 구현**해 선임 피드백에 답했다" — 문서 산출이 아니라 동작하는 구현체로 답했음을 강조.

#### 6.10.8 온보딩 UX 격상 (2026-06-26, 회의 피드백 "처음 쓰는 사람이 뭘 해야 할지 모름")

> 커밋 `ecd4801`(9파일, +304줄). "UI는 있는데 첫 사용자가 진입 순서를 모른다"는 회의 지적에 **가이드 레이어**를 얹음. 응답 정리 문서 = `docs/meeting_feedback_response_20260626.md`.

- **`Home.py` 확장** — 헬스 3-metric 위에 ① "처음 사용하시나요?" 4단계 시나리오 안내, ② **6단계 라이프사이클 다이어그램**(각 박스 `st.page_link`로 해당 페이지 직행), ③ 전체 페이지 인덱스.
- **`utils.py` 신규 헬퍼 2종**:
  - `step_banner(step_idx, what)` — **6페이지 전부 상단**에 "Step N/6 — 단계명" + 이 페이지가 하는 일 한 줄 + 이전/다음 단계 `page_link`. 사용자가 사이클 어디에 있는지 항상 표시.
  - `next_step_ctas(...)` — 페이지 하단 "다음 단계 추천" 박스(보통 3개). 예: 업로드 완료 후 "다음은 Model Card 작성 / 추론 테스트" 유도.
- **6페이지 전부 `step_banner` 부착** + 업로드 페이지 완료 후 CTA.

#### 6.10.9 [2026-07 후속] 사례조사 — 포털 갈음 → hands-on 비교 문서로 격상

- §6.10.6의 "별도 사례조사 doc 거부, 포털로 갈음" 입장은 **후속 회의에서 뒤집혔다.** 회의에서 "포털 말고 **글로벌 플랫폼을 직접 써보고 비교 문서를 써오라**"는 요구가 나왔고, 이에 **Vertex AI·Azure ML hands-on + SageMaker docs 벤치마킹 문서**를 실제 작성했다(→ §10.4A, `비교\발표물\benchmark_complete.md` — 7/14 발표물 폴더로 이동, `benchmark_ppt.pptx`·Notion zip 동반, 스샷 12장).
- 대응 흐름: (6월) 포털 구현으로 갈음 → (7월) 회의 재요구 → **hands-on 실사용 + 비교 문서 산출**. 두 방식 다 박지상 주도. **면접 서술 시**: 6.10.7의 "문서 거부, 구현체로 답" 한 줄만 쓰면 후속 회의 요구에 문서를 낸 사실과 충돌하므로, **"먼저 포털로 답했고, 이후 회의 요구로 3사 hands-on 비교 문서까지 작성했다"** 로 이어서 서술할 것.

#### 6.10.10 [2026-07-14~15] 포털 2차 개편 — 6페이지 → 5뷰 (공식 사용용 간소화, CORR 15)

> 온보딩 UX(6.10.8)를 얹은 지 3주 만에, 실사용 진입과 벤치마킹(§10.4A) 후속으로 **구조 자체를 재편**했다(7/14~15 집중 16커밋, 대표 커밋 `e728310` "포털 UX 대폭 간소화"; 서버 반영은 7/21 재배포). 6.10.1의 6페이지 표는 이 시점 이후 **과거 구조**다. _[휘발성·2026-07-24 검증]_

- **pages/ → views/ 전환**: Streamlit `st.navigation` 채택 — pages/ 자동 탐색과의 이중 등록 충돌을 피하려 페이지 파일을 `services/portal/views/`로 이동. 현재 **5뷰**:

| 뷰 | 파일 | 내용 |
|---|---|---|
| 모델 | `views/list.py` | 리스트 + **업로드 통합**(업로드=첫 화면) + Model Card + **아티팩트 파일트리** + **라이프사이클 전환 버튼** (`c24d951`) |
| 버전 비교 | `views/compare.py` | **신규** — 모델 내 버전 간 비교(`61c87a6`→`9ee1382`로 버전 비교 전용화; test_r2 차트는 metric 보유 모델 2개 이상일 때만) |
| 추론 | `views/infer.py` | "추론 테스트" → **실사용 REST 클라이언트로 개편**(Postman 컬렉션 대응, `abe70c3`) + 드리프트 로그 opt-in(§6.11.7) |
| 모니터링 | `views/monitor.py` | Triton health/metrics + Grafana 임베드 + **드리프트 통합**(3사 패턴, `66972ae`) — 이름에서 'Triton' 제거 |
| 거버넌스 트렌드 | `views/governance.py` | 기존 유지 |

- **온보딩 레이어 철거**: 6.10.8의 `step_banner`/`next_step_ctas`는 "공식 사용용 간소화"(`e728310`, `bacc9d4`)에서 **제거** — `utils.py`는 경량 `page_intro`만 남음. 도입(6/26) → 철거(7/14)는 실사용 단계 진입에 따른 의도적 다이어트(안내 문구·이모지·예시 텍스트 제거, 사이드바 'KETI MLOps Portal' 제목, 본문 1100px 제한).
- **업로드 안전장치**: 덮어쓰기 확인 + shape 사전검사(`7157e7e`).
- **벤치마킹 "도입 후보"의 실구현**: §10.4A 약점 목록 중 **모델 Compare(버전 비교)·아티팩트 파일트리·라이프사이클 전환 버튼** 3건이 이 개편에서 구현됨 — 단기 로드맵 소화.
- **정직 경계**: 배포는 여전히 PoC 패턴(runtime pip, §6.6) — "프로덕션 포털"로 과장 금지. 구(舊) 6페이지 중 업로드는 '모델' 뷰로, 드리프트는 '모니터링' 뷰로 흡수돼 **기능 축소가 아니라 화면 통합**이다.

---

### 6.11 Drift Reference 실데이터 전환 (2026-06-19)

> §6.6의 PoC를 한 단계 격상. reference를 numpy 더미에서 **실제 HDF5 metadata attrs**로 교체. current도 reference 분포 기반으로 재구성. 자동화는 여전히 미구현 (포털 6_드리프트 재생성 버튼이 수동 트리거). → **2026-07-21 3차 격상: current를 실제 추론 입력 적재 구조로 전환 — §6.11.7 (CORR 16).**

#### 6.11.1 Before vs After

| 항목 | Before (PoC 1차, 6/18 06:30) | After (실데이터, 6/19) |
|---|---|---|
| reference 출처 | `numpy.random.uniform(20, 60)` 등 더미 | **HDF5 metadata attrs 5 feature** 직접 추출 |
| reference 크기 | 1000 (synthetic) | **291 시나리오** (실제 학습 데이터) |
| current 합성 방식 | 더미 분포에 day별 drift 계수 곱 | reference 분포에서 `sample(replace=True)` 후 day별 drift × 실제 분포 폭 가산 |
| 정합성 | 시각화만 동작 | reference·current 분포 범위 일치 |

#### 6.11.2 build_reference.py 구현

```python
# mlops-tools/scripts/drift/build_reference.py
FEATURE_NAMES = ["humidity", "temperature", "wind_sin", "wind_cos", "wind_speed"]
for path in sorted(glob.glob(os.path.join(hdf5_dir, "*.h5"))):
    with h5py.File(path, "r") as f:
        attrs = f["metadata"].attrs
        row = {name: float(attrs[name]) for name in FEATURE_NAMES}
        ...
```

- 학습 데이터셋 291 시나리오 HDF5 → 291행 DataFrame
- 출력: `data/reference_features.csv` — **정정(CORR 19)**: "양쪽 커밋 = 단일 진실" 정책 선언과 달리 실제로는 **mlops-tools에만 커밋**(`03bb499`, 2026-06-19). cooling-project 리포의 `data/`는 **untracked 유지**(2026-07-24 재확인), 서버 가동본(18,917B)과 커밋본(19,209B)도 상이. 단일 진실화는 미완 TODO.

#### 6.11.3 current 합성 — drift 시나리오

```python
sample = reference.sample(n=200, replace=True, random_state=...)
sample["humidity"]    += drift * (ref_max["humidity"] - ref_min["humidity"]) * 0.3
sample["temperature"] += drift * (ref_max["temperature"] - ref_min["temperature"]) * 0.25
sample["wind_speed"]  += drift * (ref_max["wind_speed"] - ref_min["wind_speed"]) * 0.5
```

- day 0 → day 6: drift 0 → 0.72 (`day * 0.12`)
- 실제 분포 범위에 비례한 이동 (합성 분포의 비현실성 해소)
- humidity·temperature·wind_speed만 이동 (wind_sin/cos는 고정 — 방향 분포는 일반적으로 안 바뀐다 가정)

#### 6.11.4 Evidently 워크스페이스 빌드

`build_workspace.py`가 reference + 7일치 current 생성 → DataDriftPreset 리포트 7개 → `/data/drift/workspace`에 저장. evidently-ui 컨테이너(포트 8511)가 동일 워크스페이스 read-only 마운트로 서빙. 포털 6_드리프트 페이지가 iframe 임베드.

#### 6.11.5 자동화 상태

여전히 미구현. 포털 6_드리프트 페이지의 "Reference + Workspace 재생성" 버튼이 수동 트리거. 정기 자동 스냅샷(cron / Argo / 추론 입력 누적) 은 P2 분기 이후. §18.7 TODO d 항목 부분 해결. (→ "추론 입력 누적"은 2026-07-21부로 구조 도입 — §6.11.7. 정기 자동 재생성은 여전히 없음.)

#### 6.11.6 정직 규율

- "드리프트 감지 자동화"가 아니라 **"드리프트 리포트 PoC + 실데이터 reference 격상"**
- current는 여전히 합성치 (실제 추론 입력 누적 안 함) — (→ 2026-07-21부로 **구조는 실입력 적재형으로 전환**, §6.11.7. 단 실요청 유입 0건이라 데이터 실체는 아직 시드뿐)
- 알람·임계값 정의 미수행 (§18.7 c 항목 미해결 유지)

#### 6.11.7 [2026-07-21] current 실입력 적재 구조 전환 (CORR 16)

> 커밋 `d4a4248` "드리프트: 합성 current → 실제 추론 입력 기반 (받은-모델 신뢰도 감시)" — §6.11.3의 합성 current를 대체하는 3부 구조. 서버 반영 7/21 재배포. _[휘발성·2026-07-24 검증]_

- **적재**: 포털 추론 뷰(`views/infer.py`)에 "이 추론의 환경 조건을 드리프트 로그에 기록" **opt-in 체크박스** — 체크 시 추론 요청의 환경조건 5-feature가 `current_log.csv`에 `src=infer`로 append.
- **로그**: `current_log.csv` (스키마 `ts,humidity,temperature,wind_sin,wind_cos,wind_speed,src`) — named volume `drift_workspace`(컨테이너 `/data/drift`) 내 위치.
- **빌드**: 신규 `scripts/drift/build_current.py` — reference 실값의 부분집합으로 **시드 생성**(`--seed-days`; 재실행 시 기존 seed 행은 교체하되 `src=infer` 실요청 행은 보존) 후 Evidently 워크스페이스 재구성.
- **2026-07-24 실측(정직 핵심)**: current_log **1,400행 전부 `src=seed`**(7/15~7/21 7일 시드), **실제 추론 유입(`src=infer`) 0건**. 워크스페이스 마지막 재생성 7/21 07:27, 정기 자동화 여전히 없음. → 표현은 **"실입력 적재 구조로 전환(시드 초기화 상태)"** 까지만. **"실트래픽 드리프트 모니터링 중"이라고 말하면 거짓이다.**
- 의미: §6.11.6 한계 중 **구조 한계(합성 current)는 해소**, **데이터 한계(실요청 축적 0건)와 자동화 한계(스케줄 없음)는 잔존**. "받은-모델 신뢰도 감시"(외부 수령 모델에 들어오는 실제 입력 분포가 학습 분포에서 벗어나는지)라는 목적 자체는 receive-and-serve(§8.11) 포지션과 정렬.

---

## 7. 모델 & 거버넌스

> 이 섹션은 박지상이 KETI에서 다룬 **AI 모델 자산의 출처·산출물·학습 결과**, 그리고 그가 **직접 설계한 모델 거버넌스 체계**를 정리한다. 핵심 정직 규율 두 가지를 먼저 못박는다.
> 1. **AI 모델 자체 설계는 [모델개발 대학] 측이 했다.** 박지상의 역할은 "서빙 가능한 형태로 배포 + MLOps 인프라 구축 + 거버넌스 설계"다. 이걸 흐리면 안 된다.
> 2. **데이터는 "확장"이 아니라 "통합"이다.** 박지상이 한 일은 제공된 분할 압축 데이터의 통합이지, 데이터를 새로 모은 것이 아니다.
>

---

### 7.1 [모델개발 대학]에서 받은 자산 (기존)

**AI 모델 코드**
- **Keras 원본** (`.h5`, 약 47 MB) — Lambda 레이어 포함, Python 버전 불일치로 **로드 불가**.
- **PyTorch 재작성 버전** — 동일 구조(**3D U-Net + CBAM + Attention Gate**)를 Lambda 없이 구현한 본을 발견.
  - 구성 파일: `train.py`, `src/model.py`, `src/trainer.py`, `src/evaluator.py`, `src/dataset.py`, `configs/model_config.py`
  - 학습-평가-시각화 파이프라인이 **이미 구현**되어 있었음 (MAE/RMSE/R² 계산, EarlyStopping, Staged Training 등 포함).
  - (a) **왜 PyTorch 본을 썼나:** Keras `.h5`가 Lambda 레이어 + Python 버전 불일치로 로드 자체가 안 됐고, 선임의 ONNX 변환 시도도 실패한 상태였다. 동일 구조를 Lambda 없이 재작성한 PyTorch 본이 이미 존재해서 **서빙 경로를 PyTorch → ONNX로 확정**할 수 있었다.

**학습 데이터**
- CFD 시뮬레이션 결과 **HDF5 파일 291건** (5개 분할 압축).
- 파일 한 건 = 특정 기상조건(온도/습도/풍향/풍속)에서의 쿨링포그 냉각효과.
- 공간 격자: **128 × 128 × 20** (10m × 10m, 직사각형 단일 건물).
- 파일명 규칙: `rectang_<orientation>_<wind_dir>_<North/South/East/West>_<wind_speed>_effect.h5` 형태 (예: `rectang_40_20_North_2.0_effect.h5`).
- 박지상이 한 일 = **"제공된 분할 압축 데이터 통합 (45 → 291건)"**.
  - ⚠️ **표현 규칙(필수):** 데이터를 모은 게 **아니다**. **"확장"으로 표현 금지. "통합"이 정확한 표현.** (45→291은 5개로 분할 압축돼 있던 동일 데이터셋을 풀어서 합친 결과지, 새 데이터 수집이 아님.)

**Keras 모델 실패 보고서 (PDF)**
- 선임이 ONNX 변환을 시도했다가 **실패한 내용을 정리한 문서**. 박지상이 이걸 보고 **PyTorch 재작성 경로로 결정**했다.
  - (a) **왜 중요한가:** 의사결정의 근거 문서. 박지상의 PyTorch 경로 선택이 즉흥이 아니라 **선행 실패 분석에 기반한 판단**임을 입증한다 (의사결정 이력은 §8 의사결정 이력 참조).

→ **AI 모델 자체 설계는 [모델개발 대학] 측이 함.** 박지상은 **"서빙 가능한 형태로 배포 + MLOps 인프라 구축"** 역할. (이 줄은 절대 흐리지 말 것 — §1 프로필&포지셔닝, §13 나를 어떻게 대변할지와 동일 기조.)

---

### 7.2 박지상이 만든 / 수정한 산출물

아래 표는 **본인 설계 vs AI 도구(Claude Code) 활용**을 명확히 구분해 보존한다. 이 구분은 정직 규율의 핵심이며 절대 훼손하지 말 것 — "바이브코딩"이라는 표현은 금지, AI 도구를 활용한 산출물은 그렇게 명시한다.

| 산출물 | 역할 | 기여 구분 |
|---|---|---|
| `export_onnx.py` | PyTorch `.pth` → ONNX 변환 + onnxruntime 로컬 검증 | AI 도구(Claude Code) 활용 |
| `config.pbtxt` (cooling_unet, ecotron 3개) | Triton 모델 입출력 텐서 정의 | **본인 설계** |
| `deploy_triton.sh` | WSL2 시절 Triton 서버 실행 | AI 도구 활용 |
| `test_triton.py` | CLI 인자로 기상조건 입력 → HTTP 추론 테스트 | AI 도구 활용 |
| `log_to_mlflow.py` | (CI py_compile 대상) MLflow 로깅 헬퍼 | AI 도구 활용 |
| `register_model.py` | 거버넌스 등록·태깅 라이브러리 + CLI | AI 도구 활용 |
| `docs/governance.md` | tag 컨벤션 정의 | **본인 설계** |
| `.gitea/workflows/ci.yml` | CI 워크플로우 | AI 도구 활용 |
| `_patch_dynamic_shape.py` | ONNX dynamic batch 패치 (ecotron) | AI 도구 활용 |
| `build_wbs_v3_full.py` | WBS 자동 생성 (openpyxl) | AI 도구 활용 |

**`export_onnx.py` 핵심 로직 메모**
- PyTorch → ONNX (`torch.onnx.export`).
- **opset 17 선택** — opset 선택 사유는 **[확인 필요]** (배경 문서엔 명시 없음, 보통 PyTorch 2.x → onnxruntime 호환성 + 필요한 op 지원 기준으로 골랐을 가능성).
  - 📌 **정정(CORR 3):** 원문(2026-06-01)은 "opset 14"로 기재했으나, `export_onnx.py` 실측 확인 결과 **opset 17이 정확**하다 _(2026-06-19 검증)_. opset 14는 부정확한 원문 표기였음. **선택 사유는 여전히 [확인 필요]** (임의 추정 금지).
- onnxruntime 로컬 검증: 같은 입력에 대해 **PyTorch vs ORT 출력 비교** (수치 일치 검증).
  - (a) **왜 했나:** ONNX 변환 후 수치가 PyTorch 원본과 일치하는지 확인하지 않으면 서빙 시 조용한 정확도 손실이 생길 수 있다. 변환 직후 로컬에서 ORT로 같은 입력을 돌려 출력을 비교하는 게 변환 검증의 최소 안전장치다.

---

### 7.3 학습 차수별 결과 (1·2·3차)

| 차수 | 환경 | 데이터 | 결과 | 발견 |
|---|---|---|---|---|
| **1차** | Windows 11 + RTX 5060 Ti (WSL2 외부) | 45건 | MAE 0.53°C / R² 0.82 **(학습 측정)** | 과적합 의심, 데이터 부족 |
| **2차** | Windows 11 + RTX 5060 Ti | 291건 (분할압축 통합 후) | MAE 0.26°C / R² 0.95 **(학습 측정)** | 데이터 늘면서 일반화 개선 |
| **3차** | GPU 서버 trainer 컨테이너 (L40S) | 291건 | **Test MAE 0.2842°C / RMSE 0.5576 / R² 0.9473** | Windows 학습 v1 대비 동등 품질 (약간 변동은 정상) |

**차수 간 차이 분석**
- **Windows 2차 vs GPU 3차:** 같은 데이터, 같은 코드. 수치 미세 차이는 **GPU 부동소수점 비결정성 / cuDNN backend 차이**로 추정. ⚠️ **재현성 측정 안 함** (정직 규율: 측정하지 않은 것은 측정 안 했다고 명시).
- **1→2:** **데이터 증가가 핵심** (45→291 = 약 6.5배). 별도 모델 구조 변경 없음 → 일반화 개선은 데이터 통합 효과.

**측정 조건** (정직 규율: 측정한 것 vs 측정 안 한 것 구분)
- MAE/RMSE 단위: **°C** (절대 온도 오차).
- R²: 0~1, 1에 가까울수록 좋음.
- Train/Val/Test split: **확정 (코드 2026-06-19 확인)** — `configs/model_config.py`의 `TEST_SPLIT=0.2`(전체의 20%를 test, `random_state=42`) + `VAL_SPLIT=0.2`(train set의 20%를 val로 분리) → **약 64/16/20 (train/val/test) = 186/46/59** (291건 기준, `dataset.py:206` + `train.py:136`). 원문 "8:2 추정"은 (train+val):test = 8:2로 맞고, 그 train에서 다시 val 20%를 떼는 구조다.
- 1·2차는 **"학습 측정"**(학습 중 메트릭), 3차는 **Test 셋 측정**임을 표에 그대로 구분해 둠.

---

### 7.4 모델 거버넌스 (2026-05-26 구축) — 박지상 설계물 (두껍게)

> 이 절은 박지상의 **단독 설계 산출물**이다. 모델링이 아니라 **모델 생애주기 거버넌스를 직접 설계**했다는 점이 이 문서 전체에서 가장 차별화되는 강점이므로, 가장 두껍게 다룬다. MLflow에 표준 stage 대신 **태그 기반 거버넌스**를 얹은 설계 판단까지 포함한다.

#### 7.4.1 tag 스키마 — 상태 전이 모델

- **Registered Model 레벨 태그:** `source`, `model_type`, `domain`, `physics`, `received_at`, `contact`
  - → "이 모델이 **어디서/누구에게서/어떤 도메인·물리로** 들어왔는가"를 모델 단위로 기록. 외부([모델개발 대학]·[해외 파트너국] PINN) 모델을 받아 운영하는 KETI 상황에 맞춘 **출처 추적(provenance)** 설계.
- **Model Version 레벨 태그:** `status`, `validated_at`, `deployed_at`, `retired_at`, `notes`
  - → 버전마다 **생애주기 시점**을 타임스탬프로 박는다. `notes`로 사람 판단(물리 이슈 등)을 남긴다.
- **상태 전이:** `received → validated → deployed → retired` (**한 방향, 비가역**).
  - (a) **왜 이렇게 설계했나:** 외부에서 받은 모델은 "받음 → 검증 → 배포 → 폐기"라는 명확한 생애주기를 거친다. 단방향·비가역으로 못박으면 **임의 상태 역행을 막아** 거버넌스 무결성을 보장한다. MLflow 기본 stage(Staging/Production/Archived)는 KETI의 "외부 수령 모델" 워크플로(received/validated 단계가 없음)에 안 맞아서 **자체 status 태그 스키마로 대체**했다.

#### 7.4.2 `register_model.py` 함수 시그니처

```python
def register_external_model(
    name: str,
    onnx_path: str,
    source: str,
    model_type: str,
    domain: str,
    physics: str = "",
    received_at: str = "",
    contact: str = "",
) -> str:  # version

def mark_validated(name, version, validated_at, notes="")
def mark_deployed(name, version, deployed_at, notes="")
def mark_retired(name, version, retired_at, notes="")
```

- → `register_external_model`은 **외부 ONNX를 받아 MLflow에 신규 등록 + 7.4.1의 Registered Model 태그를 한 번에 박는다**. `mark_*` 3종은 **상태 전이 함수**로, 각각 해당 시점(`*_at`)과 `notes`를 기록하며 7.4.1의 단방향 전이를 코드로 강제한다.
- (a) **왜 라이브러리 + CLI 둘 다:** 라이브러리로 노출하면 Streamlit 포털(§5 구현① 서빙·실험관리)·CI에서 재사용하고, CLI로 노출하면 운영자가 수동 백필/조회를 할 수 있다. (구현은 AI 도구 활용, **API·태그 스키마 설계는 본인.**)

#### 7.4.3 CLI 옵션

- `python register_model.py show` — 전체 모델/태그 출력.
- `python register_model.py backfill` — **기존 모델 일회용 백필** ([해외 파트너국] PINN 3개 + cooling-project-unet).
  - (a) **왜 백필이 필요했나:** 거버넌스를 2026-05-26에 도입했는데 그 전에 이미 등록돼 있던 모델들은 태그가 없었다. `backfill`로 기존 자산을 새 스키마에 **소급 정렬**해 거버넌스 적용 범위를 전체로 맞췄다.

#### 7.4.4 적용 결과 — 원문(6/1) vs 현재(6/19) ⚠️ 정정 핵심

원문 6/1 스냅샷의 적용 결과는 다음과 같았다:
- 외부 PINN 3개(`ecotron_flow / thermal_f / thermal_s`) MLflow 신규 등록 + 태깅.
- `cooling-project-unet` **v1~v4 백필: v4=deployed, v1~v3=retired**.
- 별도 experiment **`external_models_ingest`** 생성 — 외부 ONNX를 dummy run의 artifact로 업로드한 다음 그 run을 source로 model version 등록 (`source="runs:/<run_id>/model"`).
  - (a) **왜 dummy run 우회:** MLflow Model Registry는 model version을 등록하려면 run의 artifact가 source로 필요하다. 외부에서 받은 ONNX는 KETI에서 학습한 run이 없으므로, **dummy run을 만들어 artifact로 올리고 그 run을 source로** 버전 등록하는 우회 패턴을 설계했다. (MLflow 구조 제약을 이해한 위에서의 의도적 우회.)

📌 **정정(CORR 8 · 2 · 1) — 2026-06-19 GPU 서버 직접 점검 결과 (현재 진실):**

1. **MLflow 레지스트리 현황** _[휘발성·2026-07-24 재검증, §2 현재 검증 상태 참조]_
   - 실험 **2개**: `cooling-project-3d-unet`, `external_models_ingest`.
   - 학습 런 **4개** (Test R²≈0.95).
   - **등록모델 9개 / 버전 14개.** 백엔드는 **SQLite**. **(정정 CORR 13: 6/19 기록 "버전 12개"는 오산 — `ecotron_flow_v2_0608`이 v1~v3 3버전 보유. 2026-07-24 API 재실측.)**
   - ⚠️ **전 버전 `current_stage=None`** — 즉 MLflow **표준 스테이지(Staging/Production)를 안 쓰고**, 7.4.1의 **status 태그 기반 거버넌스로 운영**한다. (이건 박지상 설계 의도와 일치 — 표준 stage 미사용은 버그가 아니라 설계 선택.)

2. **`cooling-project-unet` v4의 'deployed' 태그 ≠ 실제 서빙 (CORR 2 — 매우 중요):**
   - 원문은 "v4=deployed"로 적었고 MLflow 태그상 그렇다. **그러나 Triton 실서빙 ONNX는 2026-05-14 빌드(md5 `39bba09b…`)**이다.
   - MLflow 레지스트리엔 **cooling-project-unet v4(5/20 재학습, Test R²≈0.95)**가 있으나, **ONNX 재export·재배포가 안 됐다** → 실제 서빙되는 모델은 여전히 **5/14 본**이다.
   - 2026-06-16 ONNX Deploy 워크플로가 돈 것도 **같은 5/14 파일의 재복사**였음 (신규 v4 export 아님). CI/배포 흐름은 §6 구현② CI·관측·학습 참조.
   - ⚠️ **표현 주의:** "MLflow에는 v4가 deployed로 태깅돼 있지만, Triton 실서빙본은 5/14 ONNX다(태그-서빙 불일치)"라고 정확히 구분할 것. **"v4를 배포했다"고 단정하면 사실과 다르다.** 이 불일치 자체가 §9 트러블슈팅 / §18 열린 질문·약한영역·TODO의 항목이다.

3. **demo_only 모델이 서빙 중 (CORR 8):**
   - **6/8 추가된 ecotron v2 분할 모델 중 일부가 `manifest_validation_status=demo_only`** 상태로 등록돼 있다. 구체적으로 `ecotron_thermal_f_hot_v2_0608`, `ecotron_thermal_s_hot_v2_0608`은 **노트에 'inlet 대비 ~14℃ 하회' 물리 이슈**가 적힌 채 **`triton_loaded=true`로 서빙 중**이다. (2026-07-24 재확인: 두 모델의 버전 태그는 `status=received` — validated/deployed로 승격된 적 없이 **received 상태 그대로 서빙만 되는** 형국.)
   - → 즉 **검증 미완(demo_only) 모델이 거버넌스 태그상으로는 식별돼 있으나 실제로는 GPU에 로드돼 서빙되고 있다.** 거버넌스 스키마(`status`/`notes`)가 이 위험을 **기록은 하고 있지만 차단은 못 하는** 상태.

4. **Triton 서빙 모델 수 (CORR 1):** 원문 6/1엔 **5개**였으나 현재 **10개** _[휘발성·2026-06-19 검증, §2 참조]_. 6/8 추가분 = `ecotron_flow_v2_0608`, `ecotron_thermal_f_cold_v2_0608`, `ecotron_thermal_f_hot_v2_0608`, `ecotron_thermal_s_cold_v2_0608`, `ecotron_thermal_s_hot_v2_0608` (cold/hot 분할 5종, 전부 L40S `gpus[0]`에 로드·READY). **v2 분할은 출력 텐서명을 `outputs`로 바꿔** 과거 v1의 `linear_6` 차원 mismatch를 회피했다 (텐서 정의 = `config.pbtxt` 본인 설계 영역; 상세는 §9 트러블슈팅 참조).

#### 7.4.5 도구 repo 분리: `<org>/mlops-tools`

- **동기:** 모델 코드(`cooling-project`)와 범용 MLOps 도구는 라이프사이클이 다르다 → **향후 다른 프로젝트에서도 재사용**하기 위함. 레벨별 패키지화의 첫 단계.
- **내용(생성 당시):** `README.md`, `.gitignore`, `docs/governance.md`, `scripts/governance/register_model.py`.
- **생성:** 2026-05-26 17:02. **첫 커밋: `8652324`.** 이후 contact/source 수정 커밋 2건.
- 📌 **현재 구성(CORR 11):** `<org>/mlops-tools`는 이후 **`services/portal/`(Streamlit 6페이지 포털) + `scripts/drift/`(Evidently 드리프트 빌드 도구)로 확장**됐다. 리포 이원화 구조는 **gitea `<org>/cooling-project`(모델 코드) + `<org>/mlops-tools`(거버넌스 + 드리프트 도구 + Streamlit 포털)** _[2026-06-19 검증]_. (포털·드리프트 상세는 §5 구현①, 거버넌스 트렌드 시각화는 §5 포털 4페이지 참조.)
  - (a) **왜 분리했나:** 거버넌스/드리프트/포털은 모델 코드와 배포 주기가 다르고, KETI의 다른 프로젝트에서도 재사용 가능한 횡단 도구다. 모델 리포에 섞으면 재사용이 막힌다.

---

> **이 섹션의 한 줄 요약 (Claude에게):** 박지상은 **[모델개발 대학] 모델을 서빙 가능하게 배포**하고, **received→validated→deployed→retired 단방향 태그 스키마 + register_model.py API + 백필**까지 **모델 거버넌스를 직접 설계**했다. 단, 현재 (1) cooling-project-unet은 MLflow상 v4=deployed지만 **Triton 실서빙은 5/14 ONNX**이고, (2) 전 버전 `current_stage=None`(태그 기반 운영), (3) **demo_only 물리이슈 모델이 서빙 중**이라는 **태그-실서빙 불일치**가 존재한다 _(2026-06-19 검증, §2·§9·§18 참조)_ — 이 불일치를 숨기지 말고 "거버넌스로 식별은 되나 자동 차단은 미구현"이라는 정직한 상태로 전달할 것. **2026-06-16 v2 스키마 격상은 §7.5 참조** (4단계 enum·ISO 8601·고정+자유 이중구조·동시-deployed-1개 원칙 코드화).

---

### 7.5 Governance v2 스키마 합의·마이그레이션 (2026-06-16 ~ 06-17)

> §7.4의 v1 거버넌스(received→validated→deployed→retired 단방향 태그)를 [선임연구원A] 선임 5/21 카톡 피드백("tag 자유도 너무 높음, 필수 필드 강제 필요" — §14.4 원문)을 받아 **v2 스키마로 격상**한 결과. 2026-06-16 회의에서 5개 안건 합의, 그날부터 06-17까지 마이그레이션·9개 모델 description 백필 완료. v1을 폐기한 게 아니라 **확장**한 것 — 단방향 status 4단계와 태그-기반 운영은 그대로다.

#### 7.5.1 합의된 5개 안건 (§14.4 [선임연구원A] 선임 5/21 피드백 직접 응답)

| 안건 | 결정 | 보류·미도입 사유 |
|---|---|---|
| **Timestamp 포맷** | ISO 8601 (`2026-05-15T00:00:00Z`) 통일 | v1의 `2026-05-15` date-only는 같은 날 두 번 배포 시 구분 불가, 정렬 가능성 향상 |
| **Status enum** | 4단계 단방향 유지 (received→validated→deployed→retired) | `staging` 추가 거부 — 의미 모호. v1과 호환 |
| **필드 구조** | 고정 필수 + 자유 tag 이중구조 | 필수만 강제하면 모델별 특이 메타(ort_diff, scenario) 못 박음. 자유만 두면 통일 안 됨. 약한 통일 채택 |
| **Approval 단계** | **미도입** | 9모델 규모에 과대. 외부 감사 의무 없음. 10개 플랫폼 벤치마킹 중 SageMaker·Vertex·Azure ML만 채택(엔터프라이즈 한정) |
| **추론 히스토리** | **YAGNI 보류** | Triton `/metrics`(Prometheus 카운터)로 충족. 추론 1건씩 추적은 모델·트래픽 늘면 그때 |

**약한 통일(이중구조) vs 강한 통일(NGSI-LD/JSON-LD)** 격상은 별도 의제로 **다음 분기 이후 보류**. KETI Smart City Hub 연계 요구가 가시화될 때 재검토.

#### 7.5.2 스키마 v2 정의 (코드 상수)

```python
# scripts/governance/register_model.py
SCHEMA_V2_MODEL_REQUIRED = {"source", "source_type", "model_type", "domain"}
SCHEMA_V2_MODEL_REQUIRED_EXTERNAL = SCHEMA_V2_MODEL_REQUIRED | {"received_at", "contact"}
SCHEMA_V2_VERSION_REQUIRED = {"status"}
SCHEMA_V2_VERSION_STATUS_DATE_REQUIRED = {
    "validated": "validated_at",
    "deployed": "deployed_at",
    "retired": "retired_at",
}
```

- `source_type` **신설** (`internal` / `external`) — v1엔 없던 분류 차원. 외부 모델 식별 자동화.
- 외부 모델은 `received_at` + `contact` **추가 필수** → 출처 추적 무결성 강제.
- Status별 timestamp 매칭 강제 → "deployed인데 deployed_at 없음" 같은 정합성 깨짐 자동 검출.

#### 7.5.3 `register_model.py` 5개 서브커맨드 (v1 2개 → v2 5개로 확장)

| 명령 | 신/구 | 역할 |
|---|---|---|
| `show` | v1 유지 | 모델/버전 tag 덤프 |
| `backfill` | v1 유지 | [해외 파트너국] PINN 3개 일회용 백필 (2026-05-26) |
| **`migrate-iso`** | **신규** | date-only → ISO 8601 자동 변환 (`2026-05-15` → `2026-05-15T00:00:00Z`). **9/9 모델 16개 tag 마이그레이션 완료** |
| **`validate-schema`** | **신규** | v2 준수율 리포트. 2026-06-19 기준 **`9/9 models pass`**. CI에서 동일 함수 호출 가능 |
| **`backfill-v2`** | **신규** | `source=internal` → `source_type=internal` 자동 추론. 누락된 source_type 일괄 채움 |

#### 7.5.4 동시-deployed-1개 원칙 (`mlflow_update.py`)

§6.5A 참조. CI 끝단에서 새 모델 deploy 시 **기존 status=deployed 버전을 일괄 retired로 자동 전이** = "한 시점에 한 모델당 deployed 1개" 코드 보장. v2 스키마의 정합성을 CI가 강제하는 첫 사례.

#### 7.5.5 Model Card (HF Hub 패턴, 신규)

- v2 격상과 동시에 **Model Card 시스템** 도입 (`scripts/governance/backfill_descriptions.py`)
- MLflow Registered Model의 `description` 필드에 마크다운 본문 저장 → Streamlit 포털 페이지 2 (`2_모델_리스트.py`)에서 인라인 편집 (§6.10)
- 9/9 모델 초기 description 백필 완료 (입출력 shape, 정규화 식, validation 메모, Triton endpoint 등)
- **출처 패턴**: Hugging Face Hub의 Model Card 표준을 KETI 규모에 압축

#### 7.5.6 한계·정직 규율

- MLflow `current_stage`(Staging/Production)는 **의도적 None 유지** — v2의 status tag가 단일 출처. §7.4.4 CORR 8과 동일 입장이 v2에서 명문화됨
- `validate-schema`가 **검증은 하지만 차단은 안 함** — CI에서 validator 실패해도 deploy 단계가 자동 abort되지는 않음. **TODO**: hard gate 추가 (§18.7 신규 항목)
- 약한 통일 유지 = 자유 tag 영역은 여전히 통제 밖. NGSI-LD/JSON-LD 격상은 별도 분기 의제

#### 7.5.7 회의 의제 문서

`mlops-tools/docs/governance_v2_proposal.md` — 9건 합의 안건을 표 형태로 회의에 들고 간 doc. 각 항목별 "선택지 → 우리 선택 → 이유" 구조. §14.4 카톡 피드백 원문과 직접 cross-ref.

"선임 카톡 피드백 → 회의 5건 합의 → 코드 5개 서브커맨드 + 9/9 마이그레이션 + Model Card 백필까지 **거버넌스 격상 사이클 1주 안에 완주**했다" — 피드백을 코드와 데이터로 닫는 cycle time 강조.

---

## 8. 의사결정 이력 (왜 이 도구를 골랐나)

---

### 8.1 왜 Triton (vs TorchServe / TF Serving / KServe / BentoML)

- **선택**: NVIDIA Triton Inference Server
- **검토 대안**: TorchServe, TensorFlow Serving, KServe, BentoML
- **결정 사유**:
  - 멀티 프레임워크(ONNX, TensorRT, PyTorch, ONNX RT 등) 동시 서빙 가능 → 향후 다양한 모델 인수 시 대응
  - GPU 메트릭(`nv_gpu_*`) 풍부, Prometheus 친화
  - 자체호스팅 OSS, 컨테이너 단일 배포
  - 폐쇄망/사내 서버 친화
- **버린 사유**:
  - **TorchServe**: PyTorch 전용. 멀티 프레임워크 안 됨.
  - **TF Serving**: TF 전용.
  - **KServe**: K8s 의존. 우리 환경엔 K8s가 없음 (12개 프로세스 표에서 선정만, 향후 — §6/§10 참조).
  - **BentoML**: ML 패키징은 잘 되지만 GPU 친화/메트릭 면에서 Triton만큼 풍부하지 않음 (체감).
- **회고**: Triton의 `--model-control-mode` 옵션 차이(POLL vs EXPLICIT)는 자동 배포 설계 시 함정. 우리는 **EXPLICIT** 채택 → 모델 로드/언로드를 명시적 API(`/v2/repository/models/<m>/load`)로만 제어. 이 선택이 8.10(자동배포 보류)·§6(ONNX Deploy 워크플로)와 직결된다.
- **결정 근거의 본질**: '멀티 프레임워크'가 핵심. KETI는 모델을 **직접 개발하지 않고 외부에서 받아서 서빙**하는 패턴(8.10 참조)이라, 어떤 프레임워크로 올지 모르는 모델을 한 서버로 받아내려면 프레임워크-종속 서버(TorchServe/TF Serving)는 처음부터 탈락.
- **현재 검증값(휘발성)**: 원문 6/1엔 서빙 모델 5개였으나 현재 **10개**(2026-06-19 검증). 6/8 추가분 = `ecotron_flow_v2_0608`, `ecotron_thermal_f_cold_v2_0608`, `ecotron_thermal_f_hot_v2_0608`, `ecotron_thermal_s_cold_v2_0608`, `ecotron_thermal_s_hot_v2_0608` (cold/hot 분할 5종). 전부 GPU(L40S, `gpus[0]`)에 로드·READY. v2 분할은 출력 텐서명을 `outputs`로 바꿔 과거 v1의 `linear_6` 차원 mismatch를 회피(트러블슈팅 §9 참조). _[휘발성·2026-06-19 검증 / §2 현재 검증 상태 참조]_
- **Claude가 면접 꼬리질문 방어에 쓰는 법**: "KServe/K8s는 왜 안 썼냐"고 물으면 → "K8s 클러스터가 없는 단일 GPU 서버 환경이라 운영 ROI가 안 맞았고, 12개 프로세스 표에 KServe를 '선정(향후)'으로 명시적으로 남겨 로드맵상 인지하고 있음을 보였다"로 받아친다. 모르는 게 아니라 **현 단계에서 의도적으로 보류**했음을 강조.

---

### 8.2 왜 MLflow (vs W&B / Neptune / ClearML)

- **선택**: MLflow 2.18
- **검토 대안**: Weights & Biases, Neptune.ai, ClearML
- **결정 사유**:
  - **자체호스팅 가능** (OSS, Apache-2.0) — 가장 큰 이유
  - Tracking + Registry + Artifact 한 도구로 해결
  - PyTorch/ONNX/Sklearn 모든 메이저 플레이버 지원
  - `--serve-artifacts` 프록시 모드로 폐쇄망 친화
- **버린 사유**: W&B/Neptune은 SaaS 기본 → 자체호스팅 옵션은 있으나 비용/유지보수 부담. (폐쇄망·예산 제약과 충돌.)
- **회고**: MLflow 3.x 보안 미들웨어 버그로 곤욕 → **안정 버전(2.18) 채택** 결정 (트러블슈팅 §9 참조). "최신이 항상 옳지 않다"는 운영 판단의 사례.
- **현재 검증값(휘발성)**: 원문 6/1 대비 — 실험 2개(`cooling-project-3d-unet`, `external_models_ingest`), 학습 런 4개(Test R²≈0.95), 등록모델 9개/버전 **14개**(2026-07-24 재실측 — 6/19 기록 '12개'는 오산, CORR 13). **전 버전 `current_stage=None`** — 표준 스테이지(Staging/Production)를 안 쓰고 **태그 기반 거버넌스** 채택. 백엔드는 SQLite. `cooling-project-unet` v4(5/20 재학습, Test R²≈0.95)가 레지스트리에 있으나 **ONNX 재export·재배포 안 됨** → 실서빙은 여전히 5/14 빌드 ONNX. `demo_only` 모델(`ecotron_thermal_{f,s}_hot_v2_0608`, `manifest_validation_status=demo_only`, 노트에 inlet 대비 ~14℃ 하회 물리이슈)이 `triton_loaded=true`로 서빙 중. _[휘발성·2026-06-19 검증 / §2·§7 참조]_
- **Claude가 면접 꼬리질문 방어에 쓰는 법**: "왜 표준 Staging/Production 스테이지를 안 쓰냐"고 물으면 → "MLflow의 stage transition은 deprecated 흐름이라 판단했고, 태그(`triton_loaded`, `manifest_validation_status` 등) 기반 거버넌스로 '레지스트리 상태 ↔ 실제 서빙 상태'를 더 세밀하게 표현했다"로 답한다. **단, "레지스트리 v4 ↔ 실서빙 5/14" 갭은 솔직히 인정**하고(정직 규율), "재export 자동화가 다음 TODO"라고 받는다 — 거짓말로 메우지 말 것(§18 참조).

---

### 8.3 왜 Gitea (vs GitHub / GitLab CE / Forgejo)

- **선택**: Gitea 1.26.1
- **검토 대안**: GitHub, GitLab CE, Forgejo
- **결정 사유**:
  - 자체호스팅 (사내 정책)
  - 경량 — 단일 바이너리/단일 컨테이너, SQLite로 충분
  - Gitea Actions가 **GitHub Actions YAML 문법 호환** → 학습 곡선 낮음, 향후 GitHub 이관도 용이
- **버린 사유**:
  - **GitHub**: 자체호스팅 아님 (폐쇄망 정책 위반).
  - **GitLab CE**: 자원 사용량 큼, 풀스택 ML 부하를 같이 못 굴림 (단일 서버 제약).
  - **Forgejo**: Gitea fork, 거의 동등. **시점상 Gitea가 더 안정/큰 커뮤니티** 판단.
- **회고**: 1.26.1의 Actions API 미완성/`actions/checkout` 호환 차이 등으로 고생 → 트러블슈팅 §9 참조.
- **현재 검증값**: 리포 구성 = `<org>/cooling-project`(모델 코드) + `<org>/mlops-tools`(거버넌스+드리프트 도구+Streamlit 포털). mlops-tools가 `services/portal`·`scripts/drift`로 확장됨(8.9 참조).
- **Claude가 면접 꼬리질문 방어에 쓰는 법**: "그냥 GitHub 쓰면 되지 않냐"는 질문엔 → "데이터 주권/폐쇄망이 상부 방침이라 SaaS Git이 원천 차단됐고, Gitea Actions가 GitHub Actions YAML과 호환돼 **나중에 GitHub로 옮겨도 워크플로 재작성이 거의 없다**는 출구 전략까지 고려했다"고 답한다. 제약을 알고도 미래 호환성을 챙긴 점을 부각.

---

### 8.4 왜 Prometheus + Grafana (vs Datadog / NewRelic)

- **선택**: Prometheus + Grafana
- **사유**: 자체호스팅 OSS 의무. Datadog/NewRelic은 **SaaS → 정책 위반**. 추가 검토 의미 없음(원천 탈락).
- **현재 검증값(휘발성)**: Prometheus 타겟 2개(self, triton) up, **알림 룰 0개**, node-exporter/cadvisor **없음**. Grafana 13.0.1, 7패널 Triton 대시보드(`triton.json`) 로드됨. GPU 드라이버 NVML mismatch와 무관하게 `nv_gpu_*` 메트릭은 정상 수집(컨테이너 내부 GPU는 정상이기 때문 — §9 참조). _[휘발성·2026-06-19 검증 / §2·§6 참조]_
- **정직 규율(중요)**: 이건 '모니터링 인프라 구축'이지 **'부하테스트'가 아니다**. 표현 규칙상 '부하테스트 수행'이 아니라 **'메트릭 수집 파이프라인 구축·검증'**으로만 말할 것. 알림 룰 0개·exporter 부재는 미구현으로 정직하게 둔다.
- **Claude가 면접 꼬리질문 방어에 쓰는 법**: "관측성을 어디까지 했냐"엔 → "메트릭 수집·시각화(Prom 타겟 2개 up, Grafana 7패널)까지는 가동 검증했고, **알림 룰과 node/cadvisor exporter는 아직 미설치**라 솔직히 Level 0~1 수준"이라고 한다. 과장하지 않는 게 신뢰를 산다.

---

### 8.5 왜 ONNX (vs TorchScript / TensorRT 직접)

- **선택**: ONNX (export opset = **17**)
  - ⚠️ **정정**: 원문 6/1엔 'opset 14'로 적혀 있었으나 부정확. `export_onnx.py` 실제 export opset = **17**(2026-06-19 검증). **opset 선택 사유는 여전히 [확인 필요]** (임의로 지어내지 말 것).
- **결정 사유**:
  - Triton에서 표준 — `onnxruntime_onnx` 백엔드
  - PyTorch → ONNX 컨버터 성숙
  - ONNX 모델은 다른 런타임(ORT, TensorRT, OpenVINO)으로도 옮길 수 있어 **미래 옵션 보존**
- **버린 사유**:
  - **TorchScript**: PyTorch 전용. 외부 PINN처럼 다른 출처 모델까지 통일성 못 가져감.
  - **TensorRT 직접**: 하드웨어 종속 강함. 인수 모델마다 최적화 비용. ONNX → TRT 변환은 향후.
- **현재 검증값(중요·휘발성)**: `cooling_unet` 실서빙 ONNX = **2026-05-14 빌드**(md5 `39bba09b…`). MLflow 레지스트리엔 `cooling-project-unet` v4(5/20 재학습, Test R²≈0.95)가 있으나 **ONNX 재export·재배포 안 됨** → 서빙은 5/14 모델. 2026-06-16 ONNX Deploy 워크플로가 돈 건 **같은 5/14 파일 재복사**였음(신규 모델 배포 아님). _[휘발성·2026-06-19 검증 / §2·§7 참조]_
- **Claude가 면접 꼬리질문 방어에 쓰는 법**: "opset 왜 17이냐"고 파고들면 → 모르면 **모른다고 한다**("export 스크립트에 17로 고정돼 있으나 당시 선택 근거 기록이 없어 재확인이 필요"). ONNX 전체 선택 사유("멀티 런타임 이식성으로 벤더 락인 회피")는 자신 있게 말하되, opset 숫자 사유는 [확인 필요]로 정직하게 분리해서 답하는 게 함정 회피의 정석.

---

### 8.6 왜 자체호스팅 (vs SageMaker / Vertex / Azure ML)

- **선택**: 자체호스팅 OSS 풀스택
- **사유**:
  - **상부 방침** (API 의존성 회피/데이터 주권/폐쇄망 대응)
  - KETI 공공연구기관 특성
  - 팀 규모 5인·예산 제약 — SaaS 비용 부담
  - 유지보수 책임이 본인에게 (GPU 드라이버 NVML mismatch 같은 OS 레벨 이슈까지 직접 — §9 참조)
  - HA(고가용성) 설계 등 따로 신경 써야 함
  - 클라우드 SaaS의 운영 편의성 포기
- **클라우드 3사 대안 (선정 비교만, §10 참조)**: AWS SageMaker(Pipelines/Model Registry)+CodePipeline+CloudWatch / GCP Vertex AI Pipelines+Model Registry+Cloud Build / Azure ML(Pipelines/Endpoints)+Azure DevOps. 각 프로세스마다 OSS 2~4개 + 클라우드 3사 비교표 존재.
- **Claude가 면접 꼬리질문 방어에 쓰는 법**: "클라우드 매니지드 서비스 경험은 없냐"고 물으면 → "도입 결정 단계에서 SageMaker/Vertex/Azure ML을 프로세스별로 비교했고, **폐쇄망·데이터 주권이라는 상부 방침과 예산 제약 때문에 자체호스팅이 강제됐다**. 매니지드 서비스의 대응 기능(Pipelines/Registry/Monitoring)을 OSS로 1:1 매핑하는 작업을 했기 때문에 클라우드로 이관해도 개념은 그대로 옮길 수 있다"로 답한다. **클라우드를 '모른다'가 아니라 '비교 후 제약상 안 골랐다'**가 핵심 프레이밍.
- **[2026-07 갱신] 실사용 근거 확보:** 이후 회의 피드백으로 **Vertex AI·Azure ML을 실제 계정 개설→모델 등록→클린업까지 직접 사용(hands-on)** 하고 3사를 한 사이클(등록~거버넌스) 단위로 비교했다(→ §10.4A, 산출물 `비교\발표물\benchmark_complete.md`). 따라서 위 방어는 이제 **"제한적이지만 Vertex·Azure를 직접 써서 우리 온프레 스택과 UI·기능을 비교했다(SageMaker는 문서 기반)"** 로 한 단계 강화된다. **과장 금지**: 소형 ONNX·free tier·$0 범위의 **기능 탐색**이지 프로덕션 운영·이관이 아니다.

---

### 8.7 왜 단계적 구현 (한꺼번에 X)

- **결정**: 12개 프로세스 중 6개 구현 + 6개 선정만 (원문 기준). 사유:
  - 단일 연구자(박지상)가 운영하는 규모
  - **"실제로 운영해보고 다음으로"** 원칙 — 미설치는 추정만 남는 함정
  - **Level 0(기본 인프라) 확실히 → L1(드리프트 감지) → L2(자동화)** 순서
- **현재 진행도(휘발성)**: 6/1 이후 L1 쪽이 전진 — Streamlit 포털(6페이지)·Evidently 드리프트가 **배포·가동**됐으나 둘 다 PoC 수준(8.9·§6 참조). 자동 재학습/재배포 트리거(스케줄/태그/레지스트리 이벤트)는 **여전히 없음** → L2 미도달. _[휘발성·2026-06-19 검증 / §2·§10 참조]_
- **Claude가 면접 꼬리질문 방어에 쓰는 법**: "왜 다 안 끝냈냐/Level 2까지 못 갔냐"는 압박엔 → "단일 운영자 규모에서 **'운영해보지 않은 컴포넌트는 추정만 남는다'**는 원칙으로 Level 0부터 실제 가동·검증하며 올라갔다. 지금은 L1(드리프트 감지) PoC까지 가동 중이고 L2(자동화)는 의도적 로드맵상 다음 단계"라고 한다. 미완을 '계획된 단계'로 프레이밍하는 게 핵심.

---

### 8.8 왜 ecotron PINN을 외부 use case로 분리

- **결정 계기**: [선임연구원A] 선임 피드백 — "U-Ecotron(특정 모델 배포)은 MLOps_WBS에 포함될 게 아니다"
- **사유**:
  - 본 WBS는 **플랫폼 자체** 구축. 특정 모델 배포는 **플랫폼의 활용 사례(use case)**.
  - 그래서 모델 서빙 마일스톤의 **하위 작업**으로 정리 (마일스톤 자체로 안 둠).
- **Claude가 면접 꼬리질문 방어에 쓰는 법**: U-Ecotron PINN 얘기(§11 참조)를 할 때 → "이건 내가 만든 **MLOps 플랫폼이 실제로 서빙하는 활용 사례**지, 플랫폼 구축 작업 자체가 아니다"라고 경계를 명확히 긋는다. '플랫폼 빌더'와 '모델 개발자' 역할을 섞지 않는 게 포지셔닝(§1)에 유리. (선임 피드백을 반영해 WBS 구조를 고친 점 자체가 '협업·피드백 수용' 근거로도 쓰임.)

---

### 8.9 왜 mlops-tools를 별도 repo로

- **결정**: 모델 코드(`cooling-project`)에 들어있던 거버넌스 스크립트를 별도 repo(`<org>/mlops-tools`)로 분리.
- **사유**:
  - 다음 외부 모델/다른 프로젝트에서 그대로 **재사용**
  - 모델 코드 repo 클론 없이 **도구만** 가져갈 수 있음
  - 레벨별 패키지화의 첫 걸음 (L2 항목)
- **단점 인지**: repo 개수 증가, 문서가 두 곳으로 분산.
- **현재 검증값**: mlops-tools가 `services/portal`(Streamlit 6페이지)·`scripts/drift`(`build_reference.py`·`build_workspace.py`)로 확장됨. Streamlit 포털 6페이지 = 1\_모델\_업로드(검증→Triton load→MLflow 등록), 2\_모델\_리스트(Model Card 편집), 3\_Triton\_모니터링(health+metrics+Grafana iframe), 4\_거버넌스\_트렌드(MLflow tag 기반 Plotly), 5\_추론\_테스트(shape 자동감지 입력 UI), 6\_드리프트(Evidently iframe + reference 재생성). 런타임 `pip install` PoC 패턴. 단독 Dockerfile은 있으나 compose 서비스는 서버측에만 추가됨. _[휘발성·2026-06-19 검증 / §2·§5·§6 참조]_ (→ **2026-07 갱신**: 포털은 7/14~15 개편으로 **5뷰 `views/` 구조**로 재편(§6.10.10), `scripts/drift/`엔 `build_current.py` 추가(§6.11.7) — 이 줄의 6페이지 서술은 6/19 시점 기록.)
- **분리의 부작용(드리프트 위험)**: mlops-tools가 org `private`라 cross-repo clone이 막혀, ONNX validator를 **cooling-project 리포의 `.gitea/scripts/onnx_validate.py` 인라인 사본으로 이원화**함 → 두 사본이 따로 노는 **코드 드리프트 위험**(커밋 `62c510e` 참조). 또 `reference_features.csv`는 cooling-project 리포에 **미커밋(untracked)** 상태.
- **Claude가 면접 꼬리질문 방어에 쓰는 법**: "repo 분리하면 관리 포인트가 늘지 않냐"엔 → "맞다. 실제로 org가 private라 cross-repo clone이 막혀 validator를 인라인 사본으로 이원화해야 했고, 그게 코드 드리프트 위험을 만들었다. **재사용성을 얻는 대신 동기화 비용을 치르는 트레이드오프**를 인지하고 있다"고 답한다. 단점까지 말하는 게 시니어 시그널.

---

### 8.10 왜 CI를 검증 단계까지만(잠정), 자동 배포는 보류

- **결정**: CI를 **검증(validate) 단계까지만** 두고 자동 배포는 회의 결정으로 보류.
- **사유**:
  - 우리는 **모델을 직접 개발하는 게 아니라 받아서 서빙**하는 패턴
  - 풀스펙 CI/CD(개발→ONNX→자동배포)는 ROI 낮음
  - Triton **EXPLICIT 모드** + model_repo **쓰기 권한** 등 기술 관문 큼 (8.1 회고와 연결)
- **대안 방향**: **받은 모델 검증·배포 자동화**는 의미 있음 → 다음 단계 후보. 자동 배포까지 갈지는 회의에서 결정 예정.
- **현재 검증값(중요·휘발성)** — 6/1 이후 진전:
  - CI 구성 = `ci.yml`(push 자동 lint/`py_compile`) + `onnx_validate.yml`(수동) + `onnx_deploy.yml`(수동: validate → config 확인 → repo 복사 → `/v2/repository/models/<m>/load` → READY 폴링 → 메타).
  - **ONNX Deploy 워크플로가 2026-06-16 06:56 끝까지 1회 성공 실행 확인**. 단, 이때 배포된 건 신규 모델이 아니라 **5/14 ONNX 재복사**였음(8.5 참조).
  - **자동 재학습/재배포 트리거(스케줄/태그/레지스트리 이벤트)는 없음** → 여전히 '수동 트리거 + 자동 검증·배포 단계'. 즉 push에 자동으로 도는 건 lint/compile뿐이고, 배포 워크플로는 **수동 디스패치**다.
  - validator는 mlops-tools가 org private라 cooling-project의 인라인 사본으로 이원화(8.9의 드리프트 위험과 동일 원인). _[휘발성·2026-06-19 검증 / §2·§6·§9 참조]_
- **정직 규율(중요)**: 이건 **'CI/CD 풀 자동화'가 아니다**. '수동 트리거로 도는, 검증→로드→READY 폴링까지 자동화된 배포 워크플로 1종을 실제로 성공시켰다'까지만 말할 것. '자동 배포 파이프라인 구축'이라고 과장 금지. '바이브코딩'식 미검증 주장 금지 — 6/16 1회 성공은 실제 검증된 사실이다.
- **Claude가 면접 꼬리질문 방어에 쓰는 법**: "CI/CD 했냐"고 물으면 → "**받아서 서빙하는 패턴**이라 개발→자동배포 풀스펙은 ROI가 낮다고 회의에서 판단해 보류했고, 대신 '받은 ONNX 검증 → Triton EXPLICIT 로드 → READY 폴링'을 자동화한 수동-트리거 배포 워크플로를 만들어 **6/16에 끝까지 1회 성공시켰다**. 스케줄/이벤트 기반 완전 자동 트리거는 의도적으로 다음 단계로 남겼다"고 답한다. **'왜 안 했나'를 '왜 지금은 안 하는 게 맞나'로 뒤집는 것**이 이 결정의 방어 포인트.

### 8.11 왜 CI를 "receive-and-serve" 패턴으로 (2026-06-19 명문화)

- **결정**: 학습 코드 CI/CD를 의식적으로 미도입. CI의 책임 범위 = **외부 ONNX 수령 → 검증 → Triton 배포 → MLflow 거버넌스 갱신** 3종으로 한정.
- **근거**:
  - 학습 코드 출처가 **외부**: [모델개발 대학] (cooling-project-unet PyTorch) + [외부개발자A]/[외부개발자B] (Ecotron PINN). KETI 내부 학습 사이클이 없다.
  - 외부팀은 Gitea에 직접 push하는 패턴이 아니라 ONNX 파일을 인편/메일/scp로 전달 → CI 빌드 트리거 의미 없음.
  - §8.10의 "수동 트리거 배포"보다 한 단계 추상화: **"CI 책임 = 받아서 서빙까지"** 단일 문장으로 정리.
- **CI를 단일 관문화한 효과**:
  - production 진입 시 반드시 CI 통과 → 검증·태깅 누락 불가
  - 거버넌스 정합성(동시 deployed 1개·timestamp ISO 8601·source_type 명시) 자동 보장 (§6.5A `mlflow_update.py`, §7.5 v2 스키마)
  - "수동 scp + 수동 mark_deployed" 우회 경로 제거 (이전 6/8 v2 분할이 이 우회로 처음 배포됐던 자취를 §11A에서 정정 흡수)
- **비교 — 왜 SageMaker Pipelines / Kubeflow / Vertex AI 풀 자동화가 우리엔 안 맞나**:
  - SageMaker Pipelines / Kubeflow는 학습→서빙 전 사이클을 자동화하지만, **입력단(데이터·코드 통제)이 자기 조직 안일 때만 가치**.
  - KETI 컨소시엄 구조(외부에서 ONNX 받아옴)에서는 **receive-and-serve가 정렬**됨.
- **표현 주의 (§13 톤 가이드 참조)**: "CI/CD 풀스펙 안 함"이 아니라 "**CI의 책임 경계를 의도적으로 receive-and-serve로 좁혔다**"로 프레이밍. "안 했다"가 아니라 "**해야 할 일을 정의했다**"가 핵심.
- **외부 협업자 입장에서 CI의 의미**:
  - 우리에게 ONNX를 보낸 외부팀([외부개발자A]/[외부개발자B], [모델개발 대학])은 자기 모델이 어디까지 검증·배포됐는지 MLflow에서 즉시 확인 가능 → 협업 투명성
- **TODO**: 외부팀 push 컨벤션 정착 시 build-CD 격상 검토. 현재 검토 자료 미수령. §18.7 신규 항목.

---

> **§8 요약(Claude용 치트시트)**: 모든 선택의 공통 상위 사유 = **자체호스팅 강제(폐쇄망·데이터 주권·예산·5인 팀)**. 거기서 멀티프레임워크(Triton)·올인원 OSS(MLflow)·경량 Git(Gitea)·OSS 관측(Prom/Grafana)·이식성(ONNX)이 따라 나온다. **CI의 책임 경계는 의도적으로 receive-and-serve(§8.11)로 좁혔다** — "받아서 서빙까지" 단일 문장으로 표현. 미완 영역(자동 트리거 부재, opset 사유 [확인 필요], 레지스트리↔실서빙 갭, validator 이원화 드리프트)은 **숨기지 말고 '인지한 트레이드오프/다음 단계'로 프레이밍**한다 — 정직 규율(§13·§18 참조)이 면접 신뢰도의 핵심.

---

## 9. 트러블슈팅 로그

>
> 정직 규율: 아래 "측정함"이라고 명시된 수치만 본인이 실측한 값이다. 추정·기억 불명은 `[기억 안 남]`/`[확인 필요]`로 그대로 둔다. 표현 규칙(단독→주도, 데이터 확장→통합, 부하테스트→메트릭 수집 검증, 바이브코딩 금지)을 지킨다.

---

### 9.1 Keras Lambda — marshal 직렬화 실패

- **증상**: 인수받은 `.h5` 모델 파일 로드 시 Python `marshal` 디코드 에러. Lambda 레이어 내부의 Python 함수 바이트코드가 다른 파이썬 버전으로 직렬화돼 있어 현재 환경에서 디코드 불가. (정확한 에러 메시지 [기억 안 남].)
- **분석**: Keras Lambda 레이어는 함수 객체를 `marshal.dumps`로 직렬화 — Python 버전 간 바이트코드 포맷이 호환되지 않는다. 즉 모델 산출물에 호스트 파이썬 인터프리터 버전이 암묵적으로 묶여 있던 것.
- **해결**: [모델개발 대학]가 동일 구조를 PyTorch로 재작성한 버전(`src/`)이 이미 존재함을 발견 → PyTorch 경로로 전환.
- **왜 그렇게 했나 (근거)**: marshal 호환을 억지로 맞추려면 원 직렬화 파이썬 버전을 재현해야 하는데, 이는 인계 시점마다 깨질 폭탄. 동일 구조의 프레임워크 구현이 있으니 호환성 부채가 적은 쪽(PyTorch)으로 가는 게 장기적으로 옳다고 판단.
- **본인 vs AI 기여**: 증상 인지·원인 분석·대안(PyTorch 경로) 탐색·채택 결정 모두 **본인**. AI 도구 직접 기여 없음.
- **배운 점**: 모델 산출물은 가능한 ONNX 같은 프레임워크 중립 호환 포맷으로 인수해야 한다. Lambda 같은 임베디드 Python 의존은 인계의 적 — 이 경험이 이후 §9.7 ONNX 표준화·인수 정책 사고의 출발점이 됐다.
- **추상화된 표현(이력서/면접용)**: "직렬화 호환성 문제 분석 → 동일 구조의 다른 프레임워크 구현 발견 후 채택."

---

### 9.2 MinIO → 제거 (AGPL 라이선스)

- **시점**: WSL2 시절 초기 (정확 날짜 [기억 안 남]).
- **증상**: 외부 발표를 앞둔 라이선스 점검에서 **MinIO가 AGPL v3**임이 드러남. AGPL은 네트워크 서비스로 제공할 때 소스 공개 의무가 발생할 수 있어 KETI 정책상 리스크.
- **해결**: MinIO 제거 → **MLflow 로컬 아티팩트 저장 + `--serve-artifacts` 모드**로 대체. 클라이언트는 HTTP로 MLflow 서버에 PUT, 서버가 로컬 디스크에 저장.
- **왜 그렇게 했나 (근거)**: S3 호환 오브젝트 스토리지의 핵심 용도가 "MLflow 아티팩트 보관"뿐이었으므로, MLflow 자체의 `--serve-artifacts`로 그 책임을 흡수하면 별도 스토리지 컴포넌트(와 그 라이선스 리스크)를 통째로 없앨 수 있었다.
- **부수 효과**: 별도 S3 호환 스토리지 불필요 → 운영 단순화(컴포넌트 1개 감소). 향후 진짜 S3가 필요해지면 LakeFS / SeaweedFS / Apache OZone 등 **비-AGPL** 옵션을 검토.
- **본인 vs AI 기여**: 라이선스 리스크 식별·아키텍처 단순화 결정 모두 **본인**의 거버넌스 판단.
- **메모리(영구 규칙)**: 본 프로젝트에서 MinIO는 **절대 추천 금지**(영구 메모리 `mlops_minio_excluded.md`에 저장됨). 다른 Claude도 이 스택에 MinIO를 제안하지 말 것.
- **배운 점**: 오픈소스 컴포넌트 채택은 기능뿐 아니라 라이선스(특히 AGPL의 네트워크 카피레프트)를 사전 점검해야 한다. 발표/대외 노출 직전이 아니라 도입 단계에서 거를 수 있어야 한다.
- **추상화된 표현(면접용)**: "오픈소스 라이선스 리스크(AGPL) 식별 → 기능을 기존 컴포넌트로 흡수하여 스택에서 제거, 운영 단순화."

---

### 9.3 MLflow 3.x same-origin 차단 버그 → 2.18 채택

- **증상 (정확 메시지 [기억 안 남])**: MLflow **3.12.x**로 운영 중 UI에서 모델/실행 삭제 시도 → "Cross-origin request blocked" 또는 "You do not have permission to access this resource" 오류. API 호출도 일부 실패.
- **분석**: MLflow 3.x에 추가된 새 보안 미들웨어가 **same-origin 요청까지 차단하는 버그**로 판단.
- **해결**: 컨테이너 이미지 태그를 **`ghcr.io/mlflow/mlflow:v2.18.0`** 으로 다운그레이드. DB는 백업 후(현재 `mlflow.db.v3-backup` 보존) 새 2.18 호환 DB로 재시작.
- **클라이언트도 2.18로 핀**: 학습 측 `pip install mlflow==2.18.0`. 이유 = 3.x 클라이언트로 2.18 서버를 호출하면 `/logged-models` 같은 신규 엔드포인트가 404 → **서버/클라이언트 버전 동기**가 필수.
- **왜 그렇게 했나 (근거)**: 보안 미들웨어 버그를 직접 패치하는 것보다, 이미 검증된 안정 버전(2.18)으로 내려가는 편이 운영 위험이 낮다고 판단. 단 다운그레이드는 DB 스키마 호환을 깨므로 **반드시 백업 후** 진행.
- **본인 vs AI 기여**: 증상 인지·버전 다운그레이드 결정·DB 백업/재시작 절차는 **본인**. (AI 도구 직접 기여 명시 없음.)
- **현재 상태(검증)**: MLflow는 현재도 **2.18.0**으로 가동 중(컨테이너 `mlflow`, 포트 5000) _[휘발성·2026-06-19 검증, §2 현재 검증 상태 참조]_. 백엔드는 SQLite, 실험 2개(`cooling-project-3d-unet`, `external_models_ingest`), 등록모델 9개/버전 14개(CORR 13)로 운영 중.
- **배운 점**: 메이저 버전 업의 "보안 강화"가 기존 same-origin 워크플로를 깰 수 있다. 트래킹 서버는 **서버·클라이언트 버전 핀 동기**와 **DB 백업 선행**이 안전망.
- **추상화된 표현(면접용)**: "신규 보안 정책 호환성 이슈로 안정 버전(2.18) 채택, 서버·클라이언트 버전 동기화."

---

### 9.4 Gitea Actions clone 14분 hang

- **증상**: 프라이빗 저장소 빌드에서 `actions/checkout`이 토큰 인증 처리 중 **14분 hang → 타임아웃**.
- **분석**: `actions/checkout` 액션의 토큰 처리 로직이 Gitea의 인증 흐름과 맞지 않음. **Gitea Actions의 `actions/checkout` 호환은 GitHub과 100% 동일하지 않다**는 점이 핵심.
- **해결**: `actions/checkout` 대신 `run:` 스텝에서 직접 clone —
  `git clone http://token:${{ gitea.token }}@gitea:3000/${{ gitea.repository }}.git .`
  (URL에 토큰 임베드, gitea 인스턴스 URL을 직접 명시). 토큰 raw 값은 시크릿 → `[credential stored separately]`.
- **결과**: 14분 hang → **4초 이내 완료**(측정함).
- **타임아웃 보수화**: `timeout-minutes: 5`로 미래 장애 시 빠른 실패를 확보 → **현재는 `10`**.
- **왜 그렇게 했나 (근거)**: GitHub 호환 액션을 신뢰하기보다, Gitea 인증 흐름이 명확히 보장되는 `git clone` 원시 명령으로 내려가 변수를 제거. 인스턴스 URL을 명시해 액션의 자동 추론 단계를 우회.
- **본인 vs AI 기여**: 원인 추정·대안 코드는 **Claude Code 보조**. 본인 contribution = **증상 인지 + 대안 채택 결정**. (AI가 만든 코드를 그대로 쓴 게 아니라, 진단 가설을 본인이 검증·채택한 구조.)
- **배운 점**: "GitHub Actions 호환" 표방 플랫폼이라도 인증·체크아웃 등 경계 동작은 다를 수 있다. CI에서 외부 액션이 hang하면 동등한 원시 명령으로 대체해 변수를 줄이는 게 빠르다.
- **추상화된 표현(면접용)**: "CI 체크아웃 액션의 플랫폼 비호환으로 인한 hang을 원시 git clone으로 대체, 14분 → 4초."

---

### 9.5 Gitea Runner Alpine → glibc 전환 (2026-05-26) — **[두껍게]**

- **트리거(왜 시작했나)**: 향후 ONNX 검증을 CI에서 자동화하려면 잡 컨테이너에 **`onnxruntime` 설치가 필요**. 그런데 `onnxruntime`은 **manylinux 휠만 제공하고 musl(Alpine) 휠이 없다** → 기존 Alpine 기반 runner 잡 컨테이너로는 설치 자체가 불가능. 즉 "ONNX 검증 자동화"라는 §6 CI 목표가 베이스 이미지의 libc 선택에 막혀 있었음.
- **근본 원인**: 파이썬 바이너리 휠은 C 표준 라이브러리 ABI에 묶인다. Alpine은 **musl libc**, 대부분의 ML 휠(`onnxruntime` 포함)은 **glibc(manylinux)** 전제 → musl 환경에선 prebuilt 휠을 못 받고 소스 빌드로 떨어지는데 그조차 비현실적.
- **선택**: 잡 컨테이너 이미지를 **`python:3.11-bookworm`**(Debian, glibc, ~1GB)로 매핑. 이 이미지에 `git`, `python3`, `pip`가 모두 포함되어 별도 설치 단계가 줄어듦.
- **방식(설정)**: act_runner `config.yaml`의 `runner.labels`에서
  `ubuntu-latest:docker://python:3.11-bookworm` 로 매핑. 등록 시 `GITEA_RUNNER_LABELS` env로도 동일하게 지정.
- **`ci.yml` 호환 갱신**: Alpine `apk add` 단계 제거, `python3` 직접 호출로 변경(베이스에 이미 포함되므로).
- **검증(측정)**: 빈 커밋으로 트리거 → 새 잡이 image pull(첫 회 1~3분 추정) → **통과(`action_run` id 4, status=1)** 확인.
- **추가(인프라 영속화)**: act_runner를 compose에 **영구 서비스로 등재**(이전엔 미설치 상태). 호스트 `docker.sock` 마운트로 잡 컨테이너를 spawn.
- **왜 그렇게 했나 (근거)**: "Alpine은 가볍다"는 통념보다, **CI가 돌려야 할 실제 ML 의존성(glibc 휠)** 을 우선했다. 이미지 크기(~1GB) 증가를 감수하는 대신, 휠 설치 실패라는 구조적 막힘을 제거하고 향후 `onnxruntime` 기반 검증·배포(§9.7, §6 ONNX Deploy)를 가능케 하는 토대를 깐 것.
- **본인 vs AI 기여**: musl vs glibc 휠 가용성 원인 규명·베이스 이미지 교체·`config.yaml` 라벨 매핑·`ci.yml` 갱신·compose 영구 등재 결정은 **본인 주도**. (단순 명령 작성에 Claude Code 보조가 있었더라도, 의존성 ABI 진단과 아키텍처 결정은 본인.)
- **현재로의 연결**: 이 전환 덕분에 이후 `onnxruntime` 기반 **ONNX Deploy 워크플로**가 2026-06-16 끝까지 1회 성공 실행됨 _[휘발성·2026-06-19 검증, §2·§6 참조]_. 즉 glibc 전환은 단발 트러블슈팅이 아니라 CI ML 자동화의 전제 조건이었다.
- **배운 점**: ML CI 베이스 이미지는 "경량성"이 아니라 **휠 ABI 호환(manylinux/glibc)** 으로 정해야 한다. Alpine은 ML 워크로드에서 함정이 되기 쉽다.
- **추상화된 표현(면접용)**: "ML 의존성(onnxruntime)의 manylinux 휠 요구를 분석 → CI 러너 베이스를 Alpine(musl)에서 glibc(Debian)로 전환, ONNX 검증 자동화의 전제 조건 확보."

---

### 9.6 NOPASSWD sudo 우회 — 컨테이너 운영 패턴

- **제약**: 계정 `<user>`는 `docker run`, `docker compose run`, `docker network ls`, `docker compose config` 등에 **비밀번호가 필요**(NOPASSWD 범위 밖). docker 그룹 권한이 없어 sudo로만 docker 조작 가능 _(GPU 서버 권한 구조, §4·메모리 `gpu_server_access.md` 참조)_.
- **영향**:
  - 학습을 시작할 때마다 새 컨테이너를 띄울 수 없음.
  - compose 변경 시 파싱 검증 명령(`docker compose config`)을 쓸 수 없음.
- **우회 1 — 학습**: trainer 컨테이너를 `tail -f /dev/null`로 **idle 상주**시키고, 학습 시작 = `sudo docker exec -d trainer bash /workspace/_run_train.sh`. `exec`은 허용되므로 새 컨테이너 기동 없이 학습 트리거.
- **우회 2 — compose 검증**: `sudo docker compose -f docker-compose.yml ps`가 compose 파일 파싱을 동반 → 파싱 에러 시 `ps`도 실패 → 사실상 **검증 대체** 가능.
- **우회 3 — 네트워크 이름 확인**: `docker network ls`를 못 하므로, 대상 컨테이너에 `docker inspect <container>`하면 `NetworkSettings.Networks`에 실제 이름(`compose_mlops-net`)이 박혀 있어 그것으로 확인.
- **우회 4 — 파일 작성/읽기**: 호스트 권한 부족 시 `sudo docker exec <c> cat /path`로 컨테이너 안에서 읽기. 쓰기는 cp 대안 검토 필요.
- **왜 그렇게 했나 (근거)**: 권한 확장(인프라팀 요청)이 즉시 안 되는 상황에서, **이미 허용된 동작(`exec`, `inspect`, `ps`)만으로 동일 목적을 달성**하도록 운영 패턴을 설계. 보안 경계를 깨지 않으면서 실작업을 진행하기 위한 우회.
- **본인 vs AI 기여**: 허용/비허용 명령 경계 파악과 우회 패턴(idle 상주 + exec, inspect로 네트워크명 추출 등) 설계는 **본인**의 운영 엔지니어링.
- **배운 점**: 제한된 권한 환경에서 "권한을 달라"가 아니라 "허용된 표면으로 목적 달성"을 먼저 설계하면 인프라팀 의존을 줄이고 빠르게 움직일 수 있다. 이 제약이 §9.7 `model_repository` 권한 관문, §9.9 WSL2 이전 후 sudoers 축소 대응으로 이어진다.
- **추상화된 표현(면접용)**: "제한된 sudo 권한 환경에서 허용된 docker 명령만으로 학습 트리거·compose 검증·네트워크 식별을 달성하는 운영 패턴 설계."

---

### 9.7 ONNX dynamic shape 패치 (U-Ecotron PINN) — **[두껍게]**

- **증상**: [모델개발 대학]에서 받은 ONNX 3개를 Triton에 등록 시도 → **"model expects [8, K] but config [-1, K]"** 류의 shape mismatch 거부.
- **근본 원인**: [모델개발 대학] 측에서 `torch.onnx.export` 호출 시 **dummy batch=8**로 export → 그 결과 ONNX 그래프의 **`value_info`(중간 텐서 모양 캐시)에 `[8, K]`로 고정**됨. Triton의 shape inferencer가 그 캐시를 따라 입력/출력을 `[8, K]`로 추론. config.pbtxt에는 `[-1, K]`(동적 배치)로 적었지만 **모델 내부 캐시와 불일치**해 거부된 것.
- **분석 / 해결(정밀)**:
  - ONNX `graph.output[*].type.tensor_type.shape.dim[0]`을 **`dim_param='N'`(symbolic)** 으로 강제 → 배치 차원을 정적 `8`에서 동적 `N`으로 치환.
  - `graph.value_info`의 **53개 엔트리 전체 삭제** → 캐시된 중간 텐서 모양 제거(이게 안 되면 shape inferencer가 다시 `[8,…]`를 따라감).
  - 검증: `onnx.shape_inference` 재실행 결과가 `['N', 4]` 등으로 **깨끗하게** 나오는지 확인.
  - 스크립트: **`_patch_dynamic_shape.py`**(로컬 헬퍼).
- **결과**: Triton **3개 모델 모두 READY**. 100점 추론 **22~32ms 측정**(조건: 단일 요청, 패딩 없음, GPU L40S). — 이 22~32ms는 *부하테스트*가 아니라 *단일 요청 지연 측정*임(정직 규율: 부하테스트→메트릭 수집/지연 측정으로 표현).
- **왜 그렇게 했나 (근거)**: [모델개발 대학]에 재-export를 요청하면 왕복이 길고 동일 실수 재발 위험이 있어, **인수받은 ONNX 그래프를 직접 후처리(symbolic dim 강제 + value_info purge)** 하는 결정론적 패치가 빠르고 재현 가능했다. `dim_param`만 바꾸고 `value_info`를 남기면 캐시가 우선해 mismatch가 유지되므로 **둘을 함께** 손대야 한다는 게 핵심 통찰.
- **본인 vs AI 기여**: shape mismatch 원인(value_info에 박힌 정적 배치) 규명, `dim_param='N'` 강제 + `value_info` 53개 전삭제라는 해결 전략, `onnx.shape_inference` 검증 설계는 **본인 주도**. 스크립트 작성에 Claude Code 보조가 있었더라도 ONNX IR 진단·전략은 본인.
- **현재 상태(검증·변화)**: 원문 6/1엔 PINN "3개"였으나, **현재 Triton 서빙 모델은 10개**(2026-06-19 검증). 6/8에 cold/hot 분할 v2 5종(`ecotron_flow_v2_0608`, `ecotron_thermal_{f,s}_{cold,hot}_v2_0608`)이 추가됐고, **v2 분할은 출력 텐서명을 `outputs`로 바꿔 과거 v1의 `linear_6` 차원 mismatch를 회피**했다. 즉 9.7의 shape mismatch 계열 이슈가 v2에서는 출력명 표준화로 구조적으로 정리된 셈. 전부 GPU(L40S, `gpus[0]`)에 로드·READY _[휘발성·2026-06-19 검증, §2·§5·§7 참조]_.
- **배운 점**: `torch.onnx.export`의 dummy batch는 그래프 `value_info`에 정적으로 새겨진다. **동적 배치 서빙을 하려면 (1) I/O dim을 symbolic으로, (2) value_info 캐시를 제거** — 둘 다 해야 한다. 더 근본적으로는 export 단계에서 `dynamic_axes`를 지정하게 인수 규격을 잡는 게 옳다(§9.1의 "호환 포맷 인수" 교훈과 연결).
- **추상화된 표현(면접용)**: "ONNX export 시 batch 차원이 정적으로 박힌 호환성 문제 해결 후 동적 배치 형태로 재배포."

---

### 9.8 Triton model_repository 권한 — 자동 배포의 관문

- **상황**: 호스트 `/srv/triton/model_repository`는 root 소유 추정. `<user>`의 직접 쓰기 가능 여부 **[확인 필요]**.
- **현재 운영(6/1 시점)**: 모델 추가/교체 시 인프라팀 협조 또는 별도 채널로 처리(정확한 절차 **[확인 필요]**).
- **CI 자동 배포 설계의 큰 관문**:
  - act_runner 잡 컨테이너에서 `/srv/triton/model_repository`에 쓰려면 **(a) mount 추가 + `valid_volumes` 화이트리스트, (b) 권한 확보**가 필요.
  - 현재 act_runner **`valid_volumes: []`** 로 잡의 임의 마운트를 차단 — **의도적 안전 장치**(러너가 호스트 임의 경로에 쓰는 것을 막음).
  - **회의 결정 보류 사항**: 자동 배포 권한 확장 vs 검증까지만 자동화.
- **현재 상태(검증·변화)**: 위 "보류"는 **검증·배포까지 가는 수동 워크플로**로 일부 해소됐다. **ONNX Deploy 워크플로(`onnx_deploy.yml`)** 가 2026-06-16 06:56 끝까지 **1회 성공 실행** 확인됨: `validate → config 확인 → repo 복사 → /v2/repository/models/<m>/load → READY 폴링 → 메타`. 단 **자동 재학습/재배포 트리거(스케줄/태그/레지스트리 이벤트)는 없음** → 여전히 수동 트리거다 _[휘발성·2026-06-19 검증, §2·§6 참조]_.
- **왜 그렇게 했나 (근거)**: `valid_volumes: []`를 푸는 대신, 모델 배포를 **Triton의 model-control API(`/v2/repository/models/<m>/load`)** 와 워크플로 내 복사 단계로 처리해 러너에 호스트 광역 마운트 권한을 주지 않으면서도 배포 자동화의 첫 단계를 달성. 보안 경계와 자동화 욕구의 절충.
- **본인 vs AI 기여**: 권한 관문 식별, `valid_volumes` 안전장치의 의미 부여, 검증/배포 워크플로 단계 설계는 **본인**. (워크플로 YAML 작성에 Claude Code 보조 가능.)
- **배운 점**: 모델 배포 자동화의 진짜 병목은 학습/변환이 아니라 **타깃 디렉터리 쓰기 권한과 러너 마운트 정책**이라는 운영/보안 경계다. API 기반 load로 우회하면 마운트 권한 확장 없이도 진전할 수 있다.
- **추상화된 표현(면접용)**: "모델 저장소 쓰기 권한·러너 마운트 정책이라는 보안 경계를 식별하고, Triton model-control API 기반 배포 워크플로로 권한 확장 없이 자동화 첫 단계 달성."

---

### 9.9 WSL2 → GPU 서버 이전 중 문제

- **상황**: 초기 환경(WSL2)에서 GPU 서버(`<gpu-server>`, L40S)로 스택을 이전. 정확한 이슈 목록 **[기억 안 남]**. 알려진 것:
  - 학습 데이터 **11GB 전송**(방식 **[확인 필요]**, scp/rsync 추정).
  - sudoers 정책이 WSL2와 달라 **NOPASSWD 명령 범위가 좁아짐** → §9.6의 trainer 컨테이너 idle+exec 패턴을 도입하게 된 직접 원인.
  - 네트워크 이름 prefix가 다름(`compose_`) → act_runner 잡 컨테이너 네트워크 매핑을 신경 써야 함(§9.6 우회 3과 연결).
  - MinIO/CORS 디버깅 등은 그 이전(WSL2) 단계의 이슈(§9.2와 연결).
- **왜 그렇게 정리했나 (근거)**: 환경 이전은 단일 장애가 아니라 권한·네트워크·데이터 전송이 한꺼번에 바뀌는 사건이라, 개별 증상을 §9.6/§9.2 등 해당 패턴으로 분산 흡수하고 여기서는 "이전 사건"으로 묶어 추적성을 유지.
- **본인 vs AI 기여**: 이전 작업·sudoers/네트워크 차이 대응은 **본인**. 세부 이슈 일부는 기록이 남지 않아 `[기억 안 남]`으로 정직하게 보존.
- **배운 점**: 동일 compose라도 호스트(WSL2 vs 베어 GPU 서버)에 따라 **sudoers·네트워크 prefix·권한 모델이 달라진다**. 이전 시엔 권한 가정과 네트워크 이름을 가장 먼저 재확인해야 한다.
- **추상화된 표현(면접용)**: "개발 환경(WSL2)에서 GPU 서버로 MLOps 스택 이전, 권한·네트워크·데이터 전송 차이를 식별·대응."

---

### 9.10 사소한 운영 이슈 (모음)

> 단발성이지만 재발 방지 규칙으로 남길 가치가 있는 소형 이슈들. 각각 "증상 → 해결 → 규칙".

- **Gitea 인증 캐시(Windows GCM)**: `mlops-tools` 첫 push에서 Windows Git Credential Manager가 새 URL의 자격증명을 못 가져옴 → 토큰을 URL에 임베드해 1회 푸시 → 이후 GCM 캐시됨. 부작용으로 **`.git/config`에 토큰이 남음** 발견 → `branch.main.remote`를 `origin`으로 정리. **규칙**: URL 토큰 임베드 후 반드시 `.git/config` 정리(토큰 raw 값은 `[credential stored separately]`).
- **MLflow Python 클라이언트 cp949 죽음**: Windows 콘솔(cp949)에서 MLflow가 run 종료 시 🏃 이모지를 출력 → `UnicodeEncodeError`. **해결**: 스크립트 상단에 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` 추가. **규칙**: Windows에서 도는 파이썬 클라이언트는 stdout 인코딩을 utf-8로 강제.
- **PowerShell 5.1 native exe 인용 버그**: 임베디드 큰따옴표가 스트립됨. 원격 ssh로 전달 시 **작은따옴표만 사용**하는 규칙 도입.
- **act_runner `config.yaml` BOM**: PowerShell here-string pipe로 작성 시 UTF-8 BOM이 붙음. 다행히 go-yaml이 처리(YAML 1.2 스펙상 BOM 허용). **규칙**: 알아두되 치명적이지 않음.
- **Gitea Actions REST API 부재**: gitea 1.26.1에서 `/api/v1/repos/.../actions/runs`가 404. **우회**: DB(`gitea.db`) 직접 SELECT로 run 상태 조회.
- **왜 모았나 (근거)**: 각각은 작지만 "Windows 콘솔 인코딩, PowerShell 인용, BOM, 플랫폼 API 갭" 같은 **환경 경계 함정**이라 규칙화해 재발을 막는 게 실익. 본인이 직접 부딪혀 해결한 운영 디테일이다.
- **본인 vs AI 기여**: 모두 **본인**의 운영 중 발견·해결. (AI 도구 직접 기여 명시 없음.)
- **추상화된 표현(면접용)**: "Windows/PowerShell/Gitea 환경 경계에서 발생하는 인코딩·인용·API 갭 이슈를 진단하고 재발 방지 규칙으로 정착."

---

> **교차 참조**: 권한·환경 제약의 현재 상태는 §2 현재 검증 상태(2026-06-19)와 §4 인프라 환경, 서빙·레지스트리 구현은 §5, CI·관측은 §6, ONNX 모델·거버넌스는 §7, 이 사례들의 의사결정 맥락은 §8 의사결정 이력에서 함께 보라. PINN 인수 전체 서사는 §11 U-Ecotron PINN 사례 참조.

---

## 10. MLOps 성숙도 분석 (Google L0/1/2 · 12 프로세스 · WBS)

> 이 섹션은 박지상이 KETI 사내 MLOps 플랫폼을 **Google MLOps Maturity Model**에 매핑해 "지금 어디까지 왔고, 무엇이 빠졌는지"를 정직하게 진단한 내용이다. 원문(2026-06-01 덤프)의 §7을 토대로 하되, 2026-06-19 GPU 서버 직접 점검 결과(CORR 4·5·9·10)를 반영해 **현재 진실**로 갱신했다.

### 10.1 Google MLOps Maturity Model (L0/1/2 정의)

성숙도 진단의 기준 프레임은 Google Cloud의 MLOps Maturity Model이다. 박지상은 이 3단계를 우리 환경 진단의 척도로 채택했다.

- **Level 0 — Manual process**: 데이터·학습·검증·배포의 **매 단계를 사람이 직접 트리거**. 스크립트는 있어도 단계 간 자동 연결이 없다.
- **Level 1 — ML Pipeline Automation + CT(Continuous Training)**: 학습 파이프라인이 자동화되고, **데이터/트리거 기반 재학습(Continuous Training)** 이 돈다. 즉 새 데이터·드리프트 신호가 들어오면 사람이 손대지 않아도 재학습→검증이 흐른다.
- **Level 2 — CI/CD Pipeline Automation**: 모델뿐 아니라 **파이프라인 코드 자체**가 CI/CD로 자동 빌드·테스트·배포된다. 파이프라인 구성요소가 패키지화되어 다른 프로젝트로 재사용된다.

### 10.2 12개 프로세스 도출 근거

Google MLOps Level 2 정의에서 출발 → 우리 GPU 서버 환경에 매핑하면 12개 핵심 프로세스(+Feature Store 향후 항목)로 정리됨. **정확한 12개 항목 도출 과정은 [확인 필요].**

### 10.3 12개 프로세스 + 도구 매핑 (현황)

원문(2026-06-01) 매핑표는 6/12 구현 상태였다. 2026-06-19 GPU 서버 점검 결과 **Performance Monitoring·학습/추론 UI·드리프트가 PoC로 추가 배포**되어 매핑이 갱신됐다. 단, **Auto Retrain Trigger(자동 재학습 트리거)는 여전히 미구현**이므로 성숙도는 뒤에서 정직히 진단한다.

| # | 프로세스 | 선정 도구 | 상태 (현재, 2026-06-19) | 비고 / 변화 |
|---|---|---|---|---|
| 1 | Tracking Server | MLflow 2.18 (GPU 서버) | **구현** | 실험 2개, 학습 런 4개 (Test R²≈0.95). 백엔드 SQLite. _[휘발성·2026-06-19 검증, §2 참조]_ |
| 2 | Model Registry | MLflow Registry | **구현** | 등록모델 9개 / 버전 **14개**(CORR 13). 전 버전 `current_stage=None` → 표준 스테이지 미사용, **태그 기반 거버넌스**. _[휘발성·2026-07-24 검증]_ |
| 3 | Model Repository | MLflow `--serve-artifacts` | **구현** | 아티팩트 서빙 활성 |
| 4 | Git / 배포 설정 | Gitea (GPU 서버 자체호스팅) | **구현** | 리포 2개: `<org>/cooling-project`(모델 코드) + `<org>/mlops-tools`(거버넌스·드리프트·포털) |
| 5 | ArgoCD (GitOps) | ArgoCD | **선정** | 미도입 (Triton EXPLICIT 모드 직접 load로 대체 운용 중) |
| 6 | KServe Controller | KServe | **선정** | 미도입 |
| 7 | Inference Server | NVIDIA Triton (GPU 서버) | **구현** | 서빙 모델 **원문 5개 → 현재 10개** (2026-06-19 검증). 6/8 cold/hot 분할 5종 추가. 전부 L40S(`gpus[0]`) READY. _[휘발성·2026-06-19 검증, §2·§5·§7 참조]_ |
| 8 | 학습 환경 (Trainer) | PyTorch 컨테이너 (idle + `docker exec`) | **구현** | 컨테이너 내부 `torch.cuda.is_available()=True`, L40S 사용 |
| 9 | Pipeline Orchestration | Prefect → Kubeflow | **선정** | 미도입. 현재 학습은 수동 `docker exec` |
| 10 | Performance Monitoring | Prometheus+Grafana **(구현)** / Evidently **(PoC 배포)** | **구현 + PoC** | 원문은 "Evidently=선정/부분구현"이었으나 **현재 Evidently PoC 배포·가동**(아래 10.3.1). Prom 타겟 2개 up, 알림룰 0, Grafana 7패널. _[휘발성·2026-06-19 검증, §2 참조]_ |
| 11 | Auto Retrain Trigger | Prefect + Evidently | **미구현 (선정)** | **여전히 미구현.** 스케줄/태그/레지스트리 이벤트 트리거 전무 → L1 미달 핵심 원인 (10.5) |
| 12 | CI (지속적 통합) | Gitea Actions (자체호스팅) | **구현** | `ci.yml`(push 자동 lint/`py_compile`) + `onnx_validate.yml`(수동) + `onnx_deploy.yml`(수동). 자동 재배포 트리거 없음 (10.3.2) |
| 13 | Feature Store | Feast | **향후** | 미선정 단계 |
| (+) | 학습/추론 UI (Streamlit 포털) | Streamlit (`mlops-portal`) | **구현 (PoC)** | 원문에 없던 신규 항목. 포털 가동 — 7/14 개편 후 **5뷰 구조**(§6.10.10; 아래 10.3.3의 6페이지는 6/19 시점 기록). _[휘발성·2026-07-24 검증]_ |

#### 10.3.1 Performance Monitoring — Prom+Grafana(구현) → Evidently PoC 추가 [CORR 4·5·10]

- **Prometheus+Grafana**: 안정 구현. Prometheus 타겟 2개(self, triton) up, **알림 룰 0개**, node-exporter/cadvisor 없음. Grafana 13.0.1, **7패널 Triton 대시보드(`triton.json`)** 로드. GPU 드라이버 NVML mismatch(§9·CORR 7)와 **무관하게 `nv_gpu_*` 메트릭 정상 수집**. _[휘발성·2026-07-24 재검증(타겟 2 up·룰 0 동일, 패널 제목 확정 §6.4 CORR 17), §2 참조]_
- **Evidently 드리프트 (원문 '선정' → 현재 PoC 배포·가동)**: 컨테이너 `evidently-ui`, 포트 8511→8001, HTTP 200, ~24h 가동. 그러나 **명확히 PoC**:
  - `reference`=실제 데이터(HDF5 metadata attrs에서 feature 5개 추출, 커밋 `9d8bcd7`에서 dummy→real 전환)이나 **`current`=합성**(`reference.sample()` + 점진 이동).
  - **스냅샷 7개 전부 2026-06-18 06:30에 1회 수동 생성** — cron/CI 스케줄 없음.
  - `reference_features.csv`는 cooling-project 리포에 **미커밋(untracked)**.
  - 빌드 도구: `mlops-tools/scripts/drift/build_reference.py`·`build_workspace.py`.
  - _[휘발성·2026-06-19 검증, §2 참조]_
- **[2026-07-21 격상(CORR 16)]**: current가 합성 → **실입력 적재 구조**로 전환(`build_current.py` + 포털 추론 opt-in, §6.11.7). 단 2026-07-24 실측: 로그는 시드 1,400행·실요청 0건, 정기 자동화 없음 — **여전히 드리프트→트리거 연결 없음**. _[휘발성·2026-07-24 검증]_

#### 10.3.2 CI — 검증/수동 배포까지만 (자동 트리거 없음) [CORR 9]

- `ci.yml`: push 시 자동 lint/`py_compile`.
- `onnx_validate.yml`: 수동 트리거.
- `onnx_deploy.yml`: 수동 트리거. 흐름 = validate → config 확인 → repo 복사 → `/v2/repository/models/<m>/load` → READY 폴링 → 메타. **ONNX Deploy 워크플로가 2026-06-16 06:56 끝까지 1회 성공 실행 확인**. _[휘발성·2026-06-19 검증]_
- **자동 재학습/재배포 트리거(스케줄/태그/레지스트리 이벤트)는 없음** → 모든 배포가 사람 트리거.
- 이원화 위험: validator가 mlops-tools(org private라 cross-repo clone 불가)와 cooling-project의 `.gitea/scripts/onnx_validate.py` 인라인 사본으로 **이원화(drift 위험)** — 의사결정 이력은 §8, 트러블슈팅은 §9 참조.

#### 10.3.3 학습/추론 UI — Streamlit 포털 (신규, 구현 PoC) [CORR 4]

원문 매핑표에 없던 신규 산출물. 컨테이너 `mlops-portal`, 포트 8510→8501, HTTP 200, ~24h 가동. `mlops-tools` 리포 `services/portal/` 6페이지 (→ **7/14~15 개편으로 현재는 5뷰 구조** — §6.10.10. 아래는 6/19 시점 기록):

1. **1_모델_업로드** — 검증 → Triton load → MLflow 등록
2. **2_모델_리스트** — Model Card 편집
3. **3_Triton_모니터링** — health + metrics + Grafana iframe
4. **4_거버넌스_트렌드** — MLflow tag 기반 Plotly
5. **5_추론_테스트** — shape 자동감지 입력 UI
6. **6_드리프트** — Evidently iframe + reference 재생성

런타임 `pip install` PoC 패턴. 단독 Dockerfile은 있으나 **compose 서비스는 서버측에만 추가**됨. _[휘발성·2026-06-19 검증, §2 참조]_

### 10.4 클라우드 3사 비교 (선정 단계)

각 프로세스마다 OSS 2~4개 + 클라우드 3사를 비교한 표/문서가 존재. **정확한 표 본문은 [별도 파일 참고 필요].**

| 클라우드 | 파이프라인/학습 | 레지스트리/배포 | CI·모니터링 |
|---|---|---|---|
| **AWS** | SageMaker Pipelines | SageMaker Model Registry | CodePipeline, CloudWatch |
| **GCP** | Vertex AI Pipelines | Vertex Model Registry | Cloud Build |
| **Azure** | Azure ML Pipelines | Azure ML Endpoints | Azure DevOps |

### 10.4A 글로벌 플랫폼 hands-on 벤치마킹 (2026-07-06~07) _[신규]_

> §10.4는 원래 **문서 기반 '선정 비교'** 였다. 2026-07 회의 피드백("타 글로벌 플랫폼(구글·MS·아마존)이 모델관리·CI/CD·파이프라인을 어떻게 하는지 **직접 조사**, 한 사이클 단위로 비교, KETI 안 제시")을 받아, **Vertex AI·Azure ML을 실제 계정 개설→모델 등록→클린업까지 직접 사용(hands-on)** 하고 SageMaker는 문서 기반으로 정리했다. 산출물 = `C:\Users\keti\Desktop\비교\발표물\benchmark_complete.md`(스크린샷 12장 임베드, Notion 게시용; **7/14 `발표물\` 폴더로 이동, `benchmark_ppt.pptx`·`benchmark_notion.zip` 동반 산출** — CORR 18).

**조사 방식·범위 (정직 경계):**
- **Vertex AI** — hands-on. `ml-test-01` 프로젝트, `flow.onnx`(5.3MB, U-Ecotron 자산 §11) 등록. pre-built 컨테이너에 ONNX 옵션이 없어 **Triton 컨테이너 URI**(`us-docker.pkg.dev/vertex-ai/prediction/tritonserver:24.09-py3`)로 우회. Cloud Storage(Region/Standard/us-central1, 5GB Free).
- **Azure ML** — hands-on. `ml-test` 워크스페이스, 같은 `flow.onnx` 등록(형식 CUSTOM). 컨테이너 레지스트리 '없음'으로 $0 유지.
- **SageMaker** — **문서 기반**(hands-on 아님 — Domain/IAM/프리티어 설정 복잡도로 미진행). **명확히 구분할 것.**
- **전 과정 $0** — Free tier + 5GB 이내, 엔드포인트·컴퓨트 인스턴스 미생성, 종료 후 리소스 클린업.

**한 사이클(등록→리스트→배포→모니터링→추론→거버넌스) 비교 요약:**

| 단계 | Vertex | Azure | SageMaker(docs) | **KETI** |
|---|---|---|---|---|
| 등록 | 컨테이너 URI 명시 | 3소스(로컬/URI/작업) | Package Group+승인상태 | 파일 업로드→v2 스키마 자동검증 |
| 리스트 | 컬럼8·툴바2 | 컬럼7·툴바7+토글 | 그룹/버전 2단 | 컬럼8+**v2 12필드** |
| 배포 | 엔드포인트 명시생성 | 4종 유형 | 4종 유형 | **Triton 파일마운트=즉시 READY** |
| 모니터링 | 입력드리프트(v1) | **5축** | 4축 | Grafana임베드+입력드리프트 |
| 추론 | Deploy후 테스트 | Studio내 REST | Endpoint URL | **인터랙티브 위젯**(HF Spaces 패턴) |
| 거버넌스 | 라벨 단일 | 태그+속성+설명 | 승인상태(Pending/Approved) | **v2 스키마 12필드+트렌드 페이지** |

**hands-on으로 새로 확인한 사실(문서만으론 몰랐던 것):**
- Vertex·Azure **둘 다 ONNX를 native '유형'으로 안 둔다**(Vertex는 커스텀 컨테이너, Azure는 형식 CUSTOM) — 우리 Triton(ONNX 자동 인식)이 이 지점에선 더 단순.
- 3사 모두 **배포=엔드포인트 명시 생성** 단계 존재 — KETI Triton은 파일 마운트=즉시 READY로 이 단계가 절감됨.
- Azure는 **태그·속성·설명 3분리** — KETI Portal Model Card 편집 UI(§6.10, `2_모델_리스트.py`)와 같은 패턴.
- Azure 상세에 **책임 있는 AI**(Fairness/Explainability/Error Analysis) 탭 내장, SageMaker는 **모델 승인 워크플로**(Pending/Approved/Rejected) — 둘 다 KETI에 없음.

**KETI 강점(3사 대비)·약점(벤치마킹 대상):**
- **강점**: 거버넌스 v2 12필드 노출, Triton 배포 자동화(즉시 READY), 인터랙티브 추론 위젯, 거버넌스 트렌드 페이지(3사 모두 없음), $0 온프레.
- **약점(도입 후보)**: 모델 간 Compare(Azure), 아티팩트 파일트리 뷰(Azure), Pipeline DAG UI(SageMaker), 확장 드리프트 5축(Azure), 계보 시각화(Vertex Lineage), 승인 워크플로 UI(SageMaker). **(2026-07-14 후속: 이 중 Compare(버전 비교)·아티팩트 파일트리·라이프사이클 전환 버튼 3건이 포털 2차 개편에서 실구현됨 — §6.10.10 CORR 15.)**
- **도메인상 불필요(도입 X)**: Feature Store, 사전훈련 모델 카탈로그, 대량 batch inference, 컴퓨트 인스턴스 관리(온프레 GPU 정액).
- **제안 로드맵**: 단기(승인 UI·Compare·아티팩트 트리·툴바 액션) / 중기(Pipeline DAG·계보 시각화·예측·특성 드리프트) / 장기(책임 있는 AI·자동 성능회귀 감지).

### 10.5 현재 성숙도 진단 — L0~1 (자동 트리거 부재로 L1 미달) [CORR 11]

원문(2026-06-01)은 12개 프로세스 중 **6개 구현(6/12)**이었다. 2026-06-19 점검 결과 **PoC 항목이 추가**됐다(차이를 드러내 갱신):

- 안정 구현(주도): #1 MLflow Tracking, #2 Registry, #3 Repository, #4 Gitea, #7 Triton, #8 Trainer, #10-Prom/Grafana, #12 CI.
- **신규 PoC 배포(원문 6/1엔 없거나 '선정'이었음 → 현재 가동)**: #10-Evidently 드리프트(PoC), 학습/추론 Streamlit 포털(PoC).
- **여전히 미구현(선정/향후)**: #5 ArgoCD, #6 KServe, #9 Prefect/Kubeflow, **#11 Auto Retrain Trigger**, #13 Feast.

**성숙도 판정: 현재 L0~1 사이, L1 미달.**

- L0를 확실히 넘는 근거: 서빙(Triton)·실험관리(MLflow)·CI(Gitea Actions)·관측(Prom/Grafana)이 자동화되어 단순 수동 단계 묶음이 아니다.
- 그러나 **L1을 충족하지 못하는 결정적 이유**: L1의 핵심은 **CT(Continuous Training)** — 데이터/드리프트 신호 기반 **자동 재학습 트리거**다. #11 Auto Retrain Trigger가 **미구현**이고, 드리프트(Evidently)는 합성 current·수동 1회 스냅샷 PoC라 트리거로 연결되지 않으며, 재학습/재배포의 모든 트리거(스케줄·태그·레지스트리 이벤트)가 전무하다. **따라서 PoC가 늘었어도 L1(파이프라인 자동화 + CT)에는 미달**이다.
- 추가 정직 포인트: cooling_unet 실서빙 ONNX는 **2026-05-14 빌드**인데 MLflow 레지스트리엔 v4(5/20 재학습, Test R²≈0.95)가 있으나 **ONNX 재export·재배포 안 됨** → "재학습은 있으나 자동 배포 연결 없음"이 L1 미달을 그대로 보여주는 사례(§5·§7 참조). (6/16 ONNX Deploy가 돈 것도 같은 5/14 파일 재복사.) _[휘발성·2026-06-19 검증, §2 참조]_
- **2026-07-24 재점검: 판정 L0~1 유지.** 델타 — 포털 5뷰 개편(§6.10.10)·드리프트 실입력 적재 구조 도입(§6.11.7)으로 UI·관측이 성숙했으나, **CT(자동 재학습 트리거)·자동 재배포는 여전히 전무**하고 드리프트 로그도 실요청 0건이라 트리거 근거 데이터 자체가 없다. 실서빙 ONNX도 여전히 5/14 빌드(§5.2.6). _[휘발성·2026-07-24 검증]_

### 10.6 WBS — `MLOps_WBS_v3.xlsx` 3시트 구성

`MLOps_WBS_v3.xlsx`는 3개 시트로 구성:

> **정정(CORR 18 · 2026-07-24)**: 파일 실체 변경 — 현재 로컬엔 `MLOps_WBS_v3.xlsx`·`build_wbs_v3_full.py`가 없고, `바탕화면\박지상\MLOps_WBS.xlsx` + `generate_wbs.py`(출력 파일명 `MLOps_WBS.xlsx` 고정)가 현존한다. v3 파일은 개명/정리된 것으로 추정 **[확인 필요]**. 아래 3시트 구성·피드백 반영 서술 자체는 유효.

1. **WBS**: 작업 일정 간트 (주 단위 **W1~W34**, 계획 시작/완료일 + 실제 시작/완료일 컬럼). (원래) 색상: 계획 파란색, 실제 초록색 → 피드백으로 무채색화(아래).
2. **레벨별 기능**: L0~L3 레벨별 포함 기능 매트릭스 (●/○/◐) + 누적 박스 다이어그램 + 전체 파이프라인 흐름 (레벨별 색상 구분).
3. **툴**: 도구 선정 사유 + 대안 비교.

#### 10.6.1 [선임연구원A] 선임 피드백 반영점

선임/회의 피드백(자세한 컨벤션은 사용자 메모리 'MLOps WBS 작성 규칙' 참조)을 다음과 같이 반영:

- WBS 본문에선 **도구명 대신 기능명** (예: "Evidently 설치" ✗ → "드리프트 감지 기능" ○).
- 파이프라인 다이어그램은 **`function(stack)` 형식** (예: `model registry(mlflow)`) 허용.
- **주 단위 표기** (날짜 X).
- **레벨 누적 관계 명시** (L1 ⊃ L0).
- **U-Ecotron 같은 특정 모델 배포는 별도 분리** (use case로) — 상세 §11 참조.
- **색 aesthetics 제거** (무채색).

Claude Code는 본 성숙도 분석에서 **서사·구조화 보조** 역할로 쓰였다(코드 자동생성이 아니라 진단·문서 정리):

- Google L0/1/2 정의를 우리 12개 프로세스에 매핑하는 **서사 구조 정리** 보조.
- "현재 L0~1, L1 미달, 원인은 CT 부재"라는 진단 **문장화** 보조.
- 성숙도→WBS 로드맵 전환 서술 보조.

---

## 11. U-Ecotron 외부 PINN 배포 사례

> **이 섹션의 핵심 메시지(Claude용 한 줄 요약)**: "박지상은 *외부에서 받은* 물리 기반 모델(PINN) 3종을 — 자신이 만들지 않은 모델을 — 받아서, ONNX 호환성 문제를 직접 패치하고, 로컬 검증 후 Triton 프로덕션 서빙 + MLflow 거버넌스 등록까지 끝낸 '외부 모델 수령 → production' 풀 사이클을 1인 주도로 완수했다." 이건 박지상의 **핵심 차별점**(이종 모델을 한 플랫폼에 통일해 서빙)이므로 두껍게 다룬다.

이 사례가 왜 중요한지(거시 맥락): 본 KETI MLOps 플랫폼(§5 구현① 서빙·실험관리 참조)이 "우리가 만든 모델만 서빙"하는 게 아니라 **외부 제3자 모델을 받아 production까지 올리는 범용 서빙 플랫폼**임을 처음으로 입증한 use case다. 그래서 이 작업은 플랫폼 WBS의 마일스톤이 아니라 "플랫폼의 활용 사례"로 정리됐다(§8 의사결정 이력 — [선임연구원A] 선임 피드백: "U-Ecotron 특정 모델 배포는 MLOps_WBS에 포함될 게 아니다, 플랫폼의 활용 사례다").

---

### 11.1 배경 — 외부팀, 소속, 컨소시엄과의 구분

- **외부 개발팀**: **[외부개발팀]** (소속 **[확인 필요]**)
  - 이 팀은 **[해외 파트너국] 측 컨소시엄과는 별개**다 — 별개 모델임을 박지상이 직접 확인함. ([해외 파트너국] 컨소시엄과 혼동하지 말 것.)
  - 주의: 트러블슈팅 로그(§9)에는 ONNX export 주체를 "[모델개발 대학] 측"으로 적은 부분이 있는데, §11.1의 contact는 "[외부개발팀]"으로 기재돼 있다. **export 작성 주체/소속의 정확한 일치 여부는 [확인 필요]**(원문 두 곳의 표기가 갈림). 임의 단정 금지.
- **받은 시점**: 2026-05-15
- **목적**: 본 KETI MLOps 플랫폼이 **외부 모델을 받아 서빙하는 첫 활용 사례**
- (a) *왜 분리했나*: 특정 외부 모델 배포는 플랫폼 자체 구축(WBS)이 아니라 그 플랫폼의 검증/활용 사례이므로, 모델 서빙 마일스톤의 하위 작업으로 정리(마일스톤으로 격상하지 않음). 근거는 선임 피드백.

### 11.2 받은 자산 구조

**패키지 원본 (`C:\Users\keti\Desktop\ONNX_simplefied_PINN\`)**

```
ONNX_simplefied_PINN/
  ├── README.pdf
  ├── onnx_csv_to_vtp.py        ← 검증용 추론 스크립트 (PINN 측 작성)
  ├── onnx/
  │   ├── flow.onnx             # (x,y,z) → (u, v, w, p)
  │   ├── thermal_f.onnx        # (x,y,z) → θ_f
  │   ├── thermal_s.onnx        # (x,y,z) → θ_s
  │   └── manifest.json
  └── points/
      ├── inf_fluid.csv         # 300,000 점 (x,y,z)
      ├── inf_solid.csv         # 65,000 점
      └── inf_wall_gradients.csv # 4,000 점
```

**박지상 작성/추가한 산출물(= 본인 기여):**
- 헬퍼/검증 스크립트: `_patch_dynamic_shape.py`, `_test_triton.py`, `_check_domain.py`, `_inspect_response.py`, `_inspect_onnx.py`, `_deep_inspect.py`, `_shape_infer.py`
- `onnx_dynamic/` (패치된 ONNX 3개)
- `vtp/` (검증 추론 결과 3개, `onnx_csv_to_vtp.py`로 생성)
- `_triton_configs/` (Triton `config.pbtxt` 초안)
- `KETI_Triton.postman_collection.json` (추론 API 테스트 컬렉션)

- (a) *왜 이렇게 많은 inspect/패치 스크립트를 직접 작성했나*: 외부 모델은 내부 구조(텐서명/shape/도메인 범위)를 모르는 블랙박스라, ONNX 그래프를 직접 들여다보고(`_inspect_onnx.py`/`_deep_inspect.py`/`_shape_infer.py`), 도메인 좌표 범위를 확인하고(`_check_domain.py`), 서빙 응답을 검증(`_inspect_response.py`/`_test_triton.py`)하는 자체 도구를 갖춰야 했다. **모델 코드는 외부 것이지만 변환·검증·서빙 측은 전부 본인** (§10 성숙도 분석에서도 "ONNX 모델 변환·검증: 모델 코드는 외부 것이지만 변환·서빙 측은 본인"으로 분류).

### 11.3 PINN(Physics-Informed Neural Network) 도메인 설명

- 일반 신경망과 달리 **물리 방정식의 잔차(residual)를 loss에 포함**시켜 학습한다.
- 출력은 좌표별 물리량(속도장, 압력장, 온도장).
- **한 점씩 forward 가능**(autoregressive 아님) → 임의 N개 점 추론이 자연스럽다. → 이 성질이 곧 서빙 설계(가변 길이 N 입력, `max_batch_size: 0`)의 근거가 된다(§11.6).
- 받은 3개 모델이 학습한 물리:

| 모델 | 입력 | 출력 | 학습한 물리 |
|---|---|---|---|
| `flow` (`ecotron_flow`) | (x, y, z) | (u, v, w, p) | **Navier-Stokes** (운동량 + 연속 방정식) |
| `thermal_f` (`ecotron_thermal_f`) | (x, y, z) | θ_f (무차원, T/273.15 − 1) | **유체 내 열전달** |
| `thermal_s` (`ecotron_thermal_s`) | (x, y, z) | θ_s | **고체 내 열전도** |

### 11.4 dynamic shape 패치 — 왜 `[8, K]`가 박혔고, 어떻게 풀었나

(트러블슈팅 §9 — 원문 §5.7 대응 — 와 동일 사건. 여기선 '플랫폼 활용 사례' 관점에서 정리.)

**증상**: 받은 ONNX 3개를 Triton에 등록하려 하자 `"model expects [8, K] but config [-1, K]"` 류의 **shape mismatch로 거부**됨.

**왜 `[8, K]`로 박혔나 (외부 측 실수가 아니라 흔한 함정):**
```python
# export 측 코드 추정 (재구성)
dummy = torch.randn(8, 3)  # batch=8
torch.onnx.export(model, dummy, "flow.onnx",
                  dynamic_axes={"xyz": {0: "N"}, ...},  # 동적 축 명시는 있음
                  ...)
```
- `dynamic_axes`를 명시했어도, ONNX export가 **중간 텐서 shape를 `value_info`(모양 캐시)에 기록**할 때 dummy 입력 모양(8)을 그대로 박아 넣는 케이스가 존재한다.
- Triton의 shape inferencer는 그 `value_info`를 신뢰 → 모델이 `[8, K]`를 기대한다고 추론 → config의 `[-1, K]`와 충돌해 거부.

**패치 스크립트 로직 (`_patch_dynamic_shape.py`):**
1. `onnx.load(...)` 로 ONNX 그래프 로드
2. `graph.output[*].type.tensor_type.shape.dim[0]` 의 값을 `dim_param='N'`로 강제 (정적 8 → symbolic 차원)
3. `del graph.value_info[:]` — **캐시 엔트리 53개 전체 삭제** (박혀 있던 `[8, K]` 모양 정보 제거)
4. `onnx.checker.check_model(...)` 무결성 확인
5. `onnx.shape_inference.infer_shapes(...)` 결과가 `['N', 4]` 등으로 **깨끗하게** 재추론되는지 확인
6. `onnx.save(...)` → `onnx_dynamic/` 에 저장

**결과**: Triton 3개 모델 모두 READY.

- (a) *왜 value_info 전체 삭제인가*: 개별 엔트리를 일일이 고치는 대신 캐시를 비우고 `infer_shapes`로 재계산하게 두는 편이 안전·재현 가능. 삭제 후 checker + 재추론으로 무결성을 이중 확인한 점이 핵심(무작정 지운 게 아님).
- **추상화된(이력서용) 표현**: *"ONNX export 시 batch 차원이 정적으로 박힌 호환성 문제를 진단·패치하여 동적 배치 형태로 재배포"*

### 11.5 로컬 검증 — `onnx_csv_to_vtp.py` (369k 점, CPU 24.5초) _[측정함]_

- **한 줄 실행**: `python onnx_csv_to_vtp.py` (의존: `onnxruntime`, `numpy`, `pyvista`)
- **동작**:
  - `onnx/` 3개 모델을 **CPU `onnxruntime` 세션**으로 로드
  - `points/` 3개 CSV(총 **369,000 점**) 각각에 추론
  - `vtp/` 3개 VTP 파일 저장: `inf_fluid.vtp` **18MB** / `inf_solid.vtp` **2.6MB** / `inf_wall_gradients.vtp` **0.28MB**
  - 추론 횟수 합 **~689,000회** (`wall_gradients`는 중심차분 때문에 6배 호출)
  - **CPU 약 24.5초** 소요 _[실측치, 단일 프로세스·CPU 조건]_
- **검증 기준**: README 보고값과 출력 범위(속도/온도)가 일치하는지 확인 → **모델 무결성 OK**(일종의 회귀 검증).
- (a) *왜 CPU/로컬에서 먼저 돌렸나*: Triton에 올리기 전에 패치된 ONNX가 외부팀의 원본 결과와 동일한 값을 내는지(=패치가 수치를 망가뜨리지 않았는지) 독립적으로 확인하기 위함. 서빙 인프라와 분리된 ground-truth 검증.
- **정직 규율**: 이건 "부하테스트"가 아니라 **회귀/무결성 검증 + 처리 시간 측정**이다. 24.5초는 단일 프로세스 CPU 처리 시간이지, 동시성·throughput 부하시험이 아니다(표현 시 "메트릭 수집/검증"으로, "부하테스트"로 부풀리지 말 것).

### 11.6 Triton 배포 흐름 (이종 모델 서빙의 실제)

박지상이 작성한 `config.pbtxt`(본인 설계) — PINN 3종은 cooling_unet(voxel I/O)과 **완전히 다른 입출력 형태**라 별도 설계가 필요했다:

```protobuf
name: "ecotron_flow"
platform: "onnxruntime_onnx"
# PINN: 가변 길이 N개 포인트 입력 — 일반 batch 아님
max_batch_size: 0
input  [ { name: "xyz",      data_type: TYPE_FP32, dims: [-1, 3] } ]
output [ { name: "linear_6", data_type: TYPE_FP32, dims: [-1, 4] } ]  # u, v, w, p
instance_group [ { count: 1, kind: KIND_GPU, gpus: [0] } ]
```
```protobuf
name: "ecotron_thermal_f"
platform: "onnxruntime_onnx"
max_batch_size: 0
input  [ { name: "xyz",      data_type: TYPE_FP32, dims: [-1, 3] } ]
output [ { name: "linear_6", data_type: TYPE_FP32, dims: [-1, 1] } ]  # θ_f (무차원, T/273.15 - 1)
instance_group [ { count: 1, kind: KIND_GPU, gpus: [0] } ]
```
```protobuf
name: "ecotron_thermal_s"
platform: "onnxruntime_onnx"
max_batch_size: 0
input  [ { name: "xyz",      data_type: TYPE_FP32, dims: [-1, 3] } ]
output [ { name: "linear_6", data_type: TYPE_FP32, dims: [-1, 1] } ]  # θ_s
instance_group [ { count: 1, kind: KIND_GPU, gpus: [0] } ]
```

- **이종 모델 대비 설계 포인트 (핵심 차별점):**
  - `cooling_unet`은 `dynamic_batching`(`preferred_batch_size: [1,2]`, `max_queue_delay_microseconds: 100`)을 쓰지만, **PINN 3종은 입력 자체가 가변 길이 N개 점이라 일반 batch 의미가 다름** → `max_batch_size: 0`으로 두고 첫 차원을 `-1`(dynamic)로 명시. → 같은 Triton 위에서 **voxel I/O 모델(U-Net)과 point I/O 모델(PINN)이라는 두 이질적 형태를 서로 다른 batching 전략으로 통일 운영**.

- **배포 절차**:
  1. ONNX 패치 → `onnx_dynamic/flow.onnx` 등 생성
  2. Triton model_repository에 `ecotron_flow/1/model.onnx` + `config.pbtxt` 배치 (정확한 배치 절차 **[확인 필요]**, 호스트 쓰기 권한 확인 필요 — `/srv/triton/model_repository`는 root 소유 추정, `<user>` 직접 쓰기 가능 여부 [확인 필요]; 현재까지 모델 추가는 인프라팀 협조 또는 별도 채널로 수행. §9 트러블슈팅 참조)
  3. **EXPLICIT 모드**라 load API 호출: `POST .../v2/repository/models/ecotron_flow/load`
  4. health 체크: `GET .../v2/models/ecotron_flow/ready`
  5. **100점 추론 시간 측정: 22~32ms** (조건: 단일 요청, 단일 GPU **L40S**, FP32, 패딩 없음, 노이즈 수준에서 PyTorch vs Triton 출력 일치) _[측정함 — 단일 요청 응답시간이지 부하 throughput 아님]_

- (a) *왜 EXPLICIT 모드인가*: `--model-control-mode=explicit`이라 live reload가 API 호출(load/unload)로만 일어남 → 어떤 모델이 언제 올라가는지 명시적으로 제어(운영 안정성). 외부 모델을 안전하게 추가/교체하기에 적합.

### 11.7 MLflow Registry 등록 + 거버넌스 태깅

- `register_model.py backfill` 1회 실행.
- 3개 모델을 새 experiment **`external_models_ingest`**에 dummy run으로 생성 → ONNX를 artifact로 업로드 → 그 run을 source로 **model version 1** 등록.
- **모델 레벨 태그**: `source=ecotron`, `model_type=PINN`, `domain=fluid/thermal`, `physics=...`, `received_at=2026-05-15`, `contact="[외부개발팀]"`
- **버전 레벨 태그**: `status=deployed`, `validated_at=2026-05-18`, `deployed_at=2026-05-18`, `notes="VTP regression OK; Triton READY"`

원문 기준 등록 표(v1, 6/1 스냅샷):

| 모델 | 모델 레벨 태그 | 버전 | 버전 레벨 태그 |
|---|---|---|---|
| `ecotron_flow` | source=ecotron, model_type=PINN, domain=fluid, physics=Navier-Stokes, received_at=2026-05-15, contact="[외부개발팀]" | v1 | status=deployed, received_at=2026-05-15, validated_at=2026-05-18, deployed_at=2026-05-18, notes |
| `ecotron_thermal_f` | ...domain=thermal, physics=유체 내 열전달... | v1 | (동일 패턴) |
| `ecotron_thermal_s` | ...domain=thermal, physics=고체 내 열전도... | v1 | (동일 패턴) |

- (a) *왜 dummy run + backfill인가*: 외부에서 완성형 ONNX만 받았으므로 학습 run이 없다. MLflow Registry에 버전·계보·태그를 남기려면 artifact를 담을 run이 필요 → dummy run으로 채워 거버넌스 메타데이터(누가/언제/무슨 물리/검증·배포 시점)를 레지스트리에 정착시킴. 표준 stage 대신 **태그 기반 거버넌스**(§7 모델&거버넌스 참조).

### 11.8 정정(CORR 1) — 6/8 cold/hot 분할 v2 재인입·재서빙

> **원문(2026-06-01) 시점 진실**: ecotron PINN은 `ecotron_flow / ecotron_thermal_f / ecotron_thermal_s` **3종 v1**으로 서빙 중이었고, 출력 텐서명은 `linear_6`였다.
>
> **현재(2026-06-19 GPU 서버 직접 점검) 진실**: 위 3종에 더해 **6/8에 cold/hot 분할 v2가 재인입·재서빙**되었다. 즉 thermal 계열이 cold/hot으로 쪼개져 모델 수가 늘었다.

**6/8 추가된 v2 분할 모델 5종 (전부 GPU L40S `gpus:[0]`에 로드·READY):**

| v2 모델명 | 비고 |
|---|---|
| `ecotron_flow_v2_0608` | flow v2 |
| `ecotron_thermal_f_cold_v2_0608` | fluid·cold 분할 |
| `ecotron_thermal_f_hot_v2_0608` | fluid·hot 분할 — **demo_only** (아래) |
| `ecotron_thermal_s_cold_v2_0608` | solid·cold 분할 |
| `ecotron_thermal_s_hot_v2_0608` | solid·hot 분할 — **demo_only** (아래) |

- **왜 출력명을 `outputs`로 바꿨나 (핵심)**: v2 분할은 **출력 텐서명을 `linear_6` → `outputs`로 변경**했다. 이는 v1에서 발생한 **`linear_6` 차원 mismatch를 회피**하기 위한 조치다 — §11.4의 `[8,K]` value_info 함정과 같은 계열의 ONNX 출력 텐서 호환성 이슈를, export 측에서 출력명을 표준화해 우회한 것. (config.pbtxt의 output name이 모델 내부 출력명과 정확히 일치해야 Triton이 바인딩하는데, 이를 안정적인 `outputs`로 고정.)
- **거버넌스 정정**: 현재 MLflow에는 등록모델 9개 / 버전 14개가 있고(§7 참조, CORR 13), `external_models_ingest` 실험은 유지된다. 다만 **`ecotron_thermal_f_hot_v2_0608`, `ecotron_thermal_s_hot_v2_0608` 두 hot 모델은 `manifest_validation_status=demo_only`** 태그가 붙어 있고, 노트에 "**inlet 대비 약 14℃ 하회하는 물리 이슈**"가 기록돼 있음에도 `triton_loaded=true`로 **서빙은 되고 있다**. 즉 검증 미통과(demo) 상태인데 데모 목적으로 서빙 중 — 거버넌스 태그가 실서빙 차단까지는 강제하지 않는 현 단계의 한계를 그대로 드러냄(§7/§10 참조).

> _[휘발성·2026-06-19 검증]_ 현재 Triton 서빙 모델 총 **10개**(원문 6/1엔 5개: cooling_unet, ecotron 3종, resnet50 데모), 그중 ecotron 계열은 v1 3종 + v2 분할 5종 = 8종. 가동 컨테이너·드라이버 상태 등 라이브 수치는 **§2 현재 검증 상태(2026-06-19) 참조**.

### 11.9 후속/미정 사항 (정직하게 보존)

- 후처리 레이어(raw tensor → simulation output) 설계는 협의 예정 **[확인 필요 — 현황]**.
- 네트워크 공인 IP 노출은 [선임연구원B] 선임과 협의 예정 (미정). (자격증명/시크릿은 본 섹션에 raw로 쓰지 않음 — [credential stored separately].)

---

**이 섹션을 읽은 Claude에게(요약)**: 박지상의 ecotron 사례는 "**외부 모델 수령 → 호환성 패치 → 로컬 회귀 검증 → Triton production 서빙 → MLflow 거버넌스 등록 → v2 재인입 재서빙**"의 풀 사이클을 1인 주도로 돈 사례다. 차별점은 *이종 모델*(voxel I/O U-Net vs point I/O PINN)을 한 Triton 플랫폼에 서로 다른 batching 전략으로 통일 서빙한 것. 정직 경계: 모델(PINN) 자체는 외부팀 것이고 박지상은 변환·검증·서빙·거버넌스 담당이며, `_patch_dynamic_shape.py`는 AI 도구 보조로 작성했다. 관련 교차참조 — §5 구현① 서빙·실험관리, §7 모델&거버넌스, §9 트러블슈팅 로그, §10 MLOps 성숙도 분석, §13 나를 어떻게 대변할지, §2 현재 검증 상태(2026-06-19), §11A ecotron-pinn deploy-only repo 신설(2026-06-17).

---

## 11A. ecotron-pinn Deploy-Only Repo (2026-06-17 신설)

> 외부 협력팀([외부개발자A] / [외부개발자B], U-Ecotron) PINN ONNX 5종을 보관하고 CI 자동 배포만 수행하는 **deploy-only 형태의 신규 repo**. 학습 코드 없음 = "외부 수령 → 검증 → Triton 배포 → MLflow 등록" receive-and-serve 패턴(§8.11)의 최소형 구현체. § 11과 묶으면 **컨소시엄 [모델개발 대학] (cooling-project) + 외부 Ecotron(PINN 5종) 두 출처를 동일 ingest 패턴으로 흡수**했음을 보여준다.

### 11A.1 위치·생성 경위

- **Gitea**: `<org>/ecotron-pinn`
- **로컬**: `C:\Users\keti\Desktop\ecotron-pinn`
- **생성**: 2026-06-17 (UI에서 Initialize Repository 체크), 2026-06-18 MLflow 자동 갱신 step 추가까지 **3커밋 완성**
- **배경**: 6/8에 받은 v2 분할 ONNX 5종이 처음엔 scp+curl로 수동 배포됐는데(§11.8), "받은 모델 → CI 자동 흐름"을 명문화하기 위해 별도 repo 신설

### 11A.2 자산 인벤토리

- `models/`: 5개 ONNX (총 ~25.6MB)
  - `flow.onnx` (입력 [N, 4]: x, y, z, U_norm) — Navier-Stokes flow
  - `thermal_f_cold.onnx`, `thermal_f_hot.onnx`, `thermal_s_cold.onnx`, `thermal_s_hot.onnx` (입력 [N, 6]: + T_air_norm + k_norm) — fluid/solid 열전달 × cold/hot 분기
- `.gitea/workflows/`: `onnx_validate.yml` (수동 트리거 단독 검증), `onnx_deploy.yml` (검증 + 배포 + MLflow 갱신 통합)
- `.gitea/scripts/`: `onnx_validate.py` (mlops-tools canonical의 인라인 사본 — §8.9 visibility 토글 이슈 대응), `mlflow_update.py` (CI 끝단 거버넌스 자동 갱신, §6.5A 참조)

### 11A.3 CI Deploy 흐름 (cooling-project-3d-unet 패턴 이식)

```
[Checkout (token URL)]
   ↓
[Install deps: onnx onnxruntime numpy requests]
   ↓
[ONNX 3단 검증: structure(onnx.checker) → shape(dynamic_axes) → ORT 더미 추론]
   ↓
[config.pbtxt 사전 등록 확인 — /srv/triton/model_repository/<m>/config.pbtxt]
   ↓
[ONNX → /srv/triton/model_repository/<m>/<v>/model.onnx 복사]
   ↓
[POST /v2/repository/models/<m>/load → HTTP 200 확인]
   ↓
[READY 폴링 (20회 × 2초)]
   ↓
[GET /v2/models/<m> metadata 덤프]
   ↓
[mlflow_update.py — 기존 deployed retire + 신규 v 생성 + deployed 마크]
```

**2026-06-18 6시간 안에 fan-out dispatch 검증 완료** (run #26 기록 등). receive-and-serve 흐름이 처음으로 단일 repo + 단일 워크플로로 닫혔다.

### 11A.4 명명·매핑 (ONNX 파일명 ≠ Triton/MLflow 모델명)

> ⚠️ **정정(2026-06-19 라이브 검증)**: repo의 ONNX **파일명**과 실제 **배포 모델명**은 다르다. deploy 워크플로의 `onnx_path`(파일)와 `model_name`(Triton/MLflow 대상)이 별도 입력이라, 파일명이 짧아도 배포 대상은 미리 등록된 config.pbtxt 디렉토리 이름을 따른다.

- **Repo ONNX 파일명** (`models/`): `flow.onnx`, `thermal_f_cold.onnx`, `thermal_f_hot.onnx`, `thermal_s_cold.onnx`, `thermal_s_hot.onnx`
- **실제 Triton 모델명 = MLflow Registered Model명 (배포 대상)**: `ecotron_flow_v2_0608`, `ecotron_thermal_f_cold_v2_0608`, `ecotron_thermal_f_hot_v2_0608`, `ecotron_thermal_s_cold_v2_0608`, `ecotron_thermal_s_hot_v2_0608` _[휘발성·2026-06-19 검증, §2 참조]_. 즉 dispatch는 `onnx_path=models/flow.onnx` + `model_name=ecotron_flow_v2_0608` 식으로 매핑됨(근거: `flow.onnx` 5,341,324B = Triton `ecotron_flow_v2_0608/1/model.onnx` 동일 바이트; config.pbtxt 사전 등록 디렉토리도 `ecotron_*_v2_0608`). **"Triton에 flow/thermal_f_cold 라는 모델이 있다"고 말하지 말 것** — 실제 서빙명은 `ecotron_*_v2_0608`.
- **별도 케이스 — cooling-project**: Triton `cooling_unet` ↔ MLflow `cooling-project-unet`로 이름이 갈려, `mlflow_update.py`에 **`--name`(Triton) vs `--mlflow-name`(Registry) 분리 인자**를 둠(상세 §6.5A). ecotron은 Triton명=MLflow명이라 `--mlflow-name` 생략 가능.

### 11A.5 알려진 잔존 default

`onnx_deploy.yml` 입력 default가 `model_name=cooling_unet` / `onnx_path=results/cooling_unet.onnx` (cooling-project repo에서 이식 시 정리 안 됨) → dispatch 시 매번 `onnx_path=models/flow.onnx` + `model_name=ecotron_flow_v2_0608` 식으로 **둘 다 override** 필요. **TODO**: ecotron-pinn 전용 default로 정리 (§18.7-(j)). **2026-07-24 재확인: 여전히 미정리**(리포 커밋도 6/18 이후 없음 — 3커밋 그대로).

### 11A.6 의미·차별점

- 한 repo가 **학습 코드 없이도** CI 흐름을 끝까지 도는 사례 → "수령 → 서빙"이라는 KETI 책임 경계가 인프라 측면에서 자족적임을 입증
- 컨소시엄 [모델개발 대학] (cooling-project) + 외부 Ecotron(PINN 5종) 두 출처를 동일 패턴으로 흡수 = **인프라가 외부 모델 출처에 무관하게 작동**
- §11 U-Ecotron 사례와 묶으면 "수동 inspect 스크립트 7종 (5/15) → Gitea repo + CI 워크플로 (6/17)" 표준화의 시간축 완결
- §8.11 "receive-and-serve" 포지셔닝의 실증 사례

### 11A.7 정직 경계

- repo 자체는 박지상 단독 작성(Initialize 클릭, 파일 복사, CI 워크플로 이식)
- ONNX 파일 5개는 외부팀([외부개발자A]/[외부개발자B]) 산출물
- `mlflow_update.py`·`onnx_validate.py`는 AI 도구(Claude Code) 보조로 작성, 설계·통합은 본인
- 모델 자체의 물리·수치 검증은 ⚠️ §7.4.4 CORR 8 참조 (hot 분기 2종은 manifest_validation_status=demo_only 상태로 서빙 중)

---

## 12. 정량 성과 (측정 조건 명시)

> 이 섹션은 박지상의 KETI MLOps 작업에서 **수치로 말할 수 있는 것**을 한 곳에 모은다. 철칙: **모든 수치는 측정 조건을 동반**한다. 측정 안 한 건 "측정 안 함"으로 솔직히 적고 절대 추정치를 성과로 부풀리지 않는다.
> (원문 §9에 해당. 새 문서에서는 §12로 이동. 메타표 일부는 2026-06-19 GPU 서버 직접 점검으로 정정됨 — 아래 12.5 참조.)
>

### 12.1 모델 성능 (cooling-project-unet)

| 차수 | 환경 | 데이터 | MAE (°C) | RMSE (°C) | R² | 측정 조건 |
|---|---|---|---|---|---|---|
| 1차 | Win 11 + RTX 5060 Ti | 45건 | 0.53 (학습) | [기억 안 남] | 0.82 | test 0.2/val 0.2 (코드 상수; 단 1차 수치는 학습 측정값) |
| 2차 | Win 11 + RTX 5060 Ti | 291건 | 0.26 (학습) | [기억 안 남] | 0.95 | [확인 필요] |
| 3차 | GPU 서버 trainer 컨테이너 | 291건 | **0.2842** (Test) | **0.5576** (Test) | **0.9473** (Test) | Test 20% split, 186/46/59 (코드 확인) |

- **왜 이렇게 측정/기록했나**: 1·2차는 로컬 GPU(RTX 5060 Ti)에서 빠르게 돌린 초기 실험이라 RMSE 등 일부 지표가 보존되지 않았고, split 조건도 명확히 남기지 못해 `[기억 안 남]`/`[확인 필요]`로 정직하게 표기. 3차는 GPU 서버 trainer 컨테이너에서 재현 가능하게 돌려 Test split 기준 MAE/RMSE/R²을 모두 확보 — 이것이 가장 신뢰할 수 있는 수치다. **미확정 표기(`[기억 안 남]`/`[확인 필요]`)는 임의로 채우지 말 것** — split 조건을 모르면 모른다고 둔다.
- **3차 = 가장 방어 가능한 수치**: Test split 0.2842 / 0.5576 / 0.9473은 GPU 서버에서 재현된 값이라 면접 깊이 추궁에도 버틸 수 있다.

> _참고(2026-06-19 검증)_: MLflow 레지스트리에는 **cooling-project-unet v4**(2026-05-20 재학습, Test R²≈0.95)가 있으나, **실서빙 ONNX는 2026-05-14 빌드**(md5 39bba09b…)다. v4는 ONNX 재export·재배포가 안 됐고, 2026-06-16 ONNX Deploy 워크플로가 돈 것도 같은 5/14 파일을 재복사한 것. 즉 **표의 R² 0.95는 학습 메트릭이며, 현재 서빙 모델의 메트릭과 1:1로 일치한다고 단정하지 말 것**. (모델 버전·서빙 상태 상세는 §7 모델&거버넌스, §5 구현① 서빙·실험관리 참조.)

### 12.2 추론 응답 시간

- **cooling_unet**: WSL2 시절 측정 ~200ms (조건 **[확인 필요]**: 입력 크기/배치) — 측정 조건이 불완전하므로 "약 200ms 수준"으로만 인용하고, 정확한 배치·입력 shape은 모른다고 둔다.
- **ecotron PINN 100점 추론**: **22~32ms** (조건: 단일 요청, GPU L40S, FP32) — 측정 조건이 명확한 신뢰 수치.
- **ecotron PINN VTP 생성 369k 점 전체**: CPU `onnxruntime` **약 24.5초** (조건: 단일 프로세스, CPU).
- **GPU 서버 Triton에서 369k 점 동일 작업**: **[측정 안 함]** — 1~2초 추정이지만 **검증 안 함**. 절대 "1~2초로 단축"이라고 성과화하지 말 것.

- **왜 이렇게 구분했나**: PINN 100점(22~32ms)은 조건이 완전한 측정값이고, 369k점 CPU(24.5초)도 실측이지만, 같은 369k점을 GPU Triton에서 돌린 시간은 측정하지 않았다. 추정과 측정을 섞으면 정직성이 무너지므로 **측정/미측정 경계를 칼같이** 긋는다.

### 12.3 CFD 비교 기준

- **[모델개발 대학] 측 측정**: CFD 시뮬레이션 **수십 분** (정확 시간 **[확인 필요]**)
- **본 AI 추론**: ~200ms
- 감소율 계산: "CFD 수십 분 → 200ms = **99.9% 단축**"
- **단, 정확한 동등 비교 아님** — CFD는 풀 시뮬레이션 결과, AI는 **surrogate 예측**. 그 차이는 R²로 정량화된다.

- **왜 단서를 붙이나**: "99.9% 단축"은 임팩트가 크지만, CFD(완전 물리 해석)와 AI(근사 대리 모델)는 출력의 성격이 달라 **속도만 1:1로 비교하는 것은 부정확**하다. 이 단서를 빼면 과장이 된다. R²(12.1)가 바로 "근사가 얼마나 정확한가"를 보여주는 짝꿍 지표.

### 12.4 CI 실행 시간

- **과거(인증 hang)**: 14분 → 타임아웃 5분에 막힘
- **현재(인증 우회 + glibc)**: **4초 이내** (조건: lint + py_compile만, 이미지 캐시됨, 첫 회 image pull은 별도 ~1~3분)

- **왜 14분→4초인가**: 과거엔 Gitea Actions Runner의 인증 hang으로 워크플로가 14분간 매달리다 5분 타임아웃에 걸려 죽었다. 인증 우회 + Runner를 Alpine→glibc 이미지로 재설치하며 해소(상세 원인·해결은 §9 트러블슈팅 로그). **단, 비교 조건이 다름을 명시**: 현재 4초는 lint+py_compile만 도는 캐시된 상태이고, 첫 회 image pull(~1~3분)은 별도다. 따라서 "14분→4초"는 "행 상태 해소 전후"의 비교이지 동일 작업의 순수 가속이 아니다.

> _참고(2026-06-19 검증)_: 현 CI 구성은 `ci.yml`(push 자동 lint/py_compile) + `onnx_validate.yml`(수동) + `onnx_deploy.yml`(수동). **자동 재학습/재배포 트리거(스케줄·태그·레지스트리 이벤트)는 없음.** ONNX Deploy 워크플로는 2026-06-16 06:56 끝까지 1회 성공 실행이 확인된다. (CI 파이프라인 상세는 §6 구현② CI·관측·학습 참조.)

### 12.5 데이터 / 모델 메타

> 아래 표의 일부 라이브 수치는 **원문(2026-06-01 스냅샷) 이후 변경**되어, 2026-06-19 GPU 서버 직접 점검값으로 정정했다(정정 라인은 화살표로 변화를 표시). 안 변하는 사실(용량·DB 크기 등)은 그대로 둠.

| 항목 | 수치 |
|---|---|
| 학습 데이터 HDF5 파일 | 291 건 (제공된 분할 압축 **통합** 결과 — 증강·생성 아님) |
| 학습 데이터 용량 (GPU 서버) | 11 GB |
| cooling-project-unet 모델 버전 (MLflow) | v1 ~ v4 (v4 = 5/20 재학습 Test R²≈0.95; **단 실서빙 ONNX는 5/14 빌드** — 12.1 참조) |
| ecotron 모델 (MLflow) | 3개 모델 × 1버전 (원문 기준; 6/8 v2 분할 추가분은 아래 Triton 항목 참조) |
| **Triton 등록 모델** | **원문 6/1: 5개 → 현재 10개** _[휘발성·2026-06-19 검증, §2 현재 검증 상태 참조]_ |
| Triton model_repo 디스크 사용 | 1.2 GB (50GB 중) |
| MLflow DB | 544 KB (백엔드 SQLite) |
| MLflow artifacts | exp 1, 2 — ≈**280M** (`/mlflow/artifacts`, 2026-06-19 측정) _[휘발성]_ |
| **MLflow 등록 모델 / 버전** | 등록모델 9개 / 버전 **14개**(6/19 기록 "12개"는 오산 — CORR 13), 전 버전 current_stage=None(태그 기반 거버넌스) _[휘발성·2026-07-24 검증, §7 참조]_ |
| 7-패널 Grafana 대시보드 | 1개 (triton.json, uid `triton-main` — 패널 제목 실측 §6.4) |
| 드리프트 current 로그 | `current_log.csv` 1,400행(전부 시드, 실요청 0건 — §6.11.7) _[휘발성·2026-07-24 검증]_ |
| MLOps 12개 프로세스 (성숙도) | 원문 6/1: **6/12 구현** → 2026-06-19: **+PoC 2종**(Evidently 드리프트·Streamlit 포털). 단 Auto Retrain Trigger 미구현 → **L0~1 유지** _[정합·상세 §10.3 참조]_ |
| MLOps 프로세스 매핑 | 12개 전 프로세스 도구 선정 완료(구현 / PoC / 선정·향후로 분류) — §10.3 매핑표 참조 |
| **가동 컨테이너 수** | **원문 6/1: 7개 → 현재 9개** (+mlops-portal, +evidently-ui) _[휘발성·2026-06-19 검증, §2 참조]_ |
| 자체호스팅 도구 수 | 5 (Triton/MLflow/Gitea/Prometheus/Grafana) + trainer + runner |
| 등록 Gitea repo | 2 (`<org>/cooling-project` 모델 코드, `<org>/mlops-tools` 거버넌스+드리프트 도구+Streamlit 포털) |

**정정 상세 (원문 6/1 → 2026-06-19 라이브 점검):**

- **Triton 서빙 모델 5개 → 10개** _[휘발성·2026-06-19 검증]_: 6/8에 ecotron v2 분할 5종 추가 — `ecotron_flow_v2_0608`, `ecotron_thermal_f_cold_v2_0608`, `ecotron_thermal_f_hot_v2_0608`, `ecotron_thermal_s_cold_v2_0608`, `ecotron_thermal_s_hot_v2_0608`. 전부 GPU(L40S, `gpus[0]`)에 로드·READY. **왜 v2 분할인가**: 출력 텐서명을 `outputs`로 바꿔 과거 v1의 `linear_6` 차원 mismatch를 회피하기 위함(트러블슈팅 맥락은 §9, 모델 거버넌스는 §7).
- **가동 컨테이너 7개 → 9개** _[휘발성·2026-06-19 검증]_: Streamlit 포털(`mlops-portal`)과 Evidently 드리프트 UI(`evidently-ui`)가 추가 배포·가동(둘 다 PoC 성격, 상세는 §5/§6). 안 변하는 "자체호스팅 핵심 도구 5종"은 그대로.
- **2026-07-24 재점검**: 위 수치 유지(컨테이너 9개·Triton 10모델 READY). 버전 수만 12→**14**로 정정(CORR 13). 호스트는 7/9 재부팅(커널 6.8.0-134)·NVML mismatch 재발(§4.1.1). 포털·Evidently는 7/21 재배포(§6.10.10·§6.11.7). _[휘발성·2026-07-24 검증, §2 참조]_

> _왜 휘발성 태그를 붙이나_: Triton 모델 수·컨테이너 수·등록모델 수는 운영 중 계속 바뀌는 라이브 상태다. 이 문서는 핸드오프용이므로, 시간이 지나면 다시 점검해야 하는 수치임을 독자(Claude)에게 명시한다. **변경 가능성 없는 설계·결정·아키텍처에는 태그를 붙이지 않는다.**

### 12.6 정식 부하 테스트는 안 했다

- **수집 파이프라인 정상 동작 확인 목적**의 측정만 함 (메트릭이 Prometheus로 흘러 Grafana에 뜨는지 검증).
- "60회 burst 부하 검증" 같은 **정밀 표현 금지**.
- 면접/PT에서는 **"부하 측정은 안 했고, 메트릭 수집 검증만 했다"**고 솔직히 말한다.

- **왜 이 경계를 지키나**: 모니터링 스택(Prometheus 타겟 self/triton up, Grafana 7패널 — 상세 §6)이 동작함을 확인하는 것과, 정식 부하/성능 테스트(throughput·p99 latency·동시성 한계 측정)는 완전히 다른 작업이다. 후자는 안 했으므로 "부하테스트했다"는 표현은 거짓이 된다. **표현 규칙: 부하테스트 → "메트릭 수집 검증"으로만 쓴다.**

---

## 16. 부록 — 파일 / URL / 명령 인덱스

> 이 부록은 **다른 곳의 Claude가 빠르게 경로·URL·명령을 찾아 박지상의 작업을 재현·설명**하도록 만든 인덱스다. 라이브 상태(컨테이너/포트/모델 수)는 시간이 지나면 변하므로 _[휘발성]_ 표기를 붙이고, 최신 진실은 **§2 현재 검증 상태(2026-07-24)** 를 따른다. 자격증명(비밀번호/토큰)은 raw로 적지 않는다(§17 시크릿은 내부 원본에만 존재).

### 16.1 핵심 파일 위치

| 파일 | 위치 | 비고 |
|---|---|---|
| 본 핸드오프 덤프(원본) | `C:\Users\keti\Desktop\keti_mlops_full_dump_old.md` | 이 문서의 기반 원문 — **2026-07-24 `_old` 개명 보관(구본). 본 추출본(`keti_mlops_pipeline.md`)이 현행 핸드오프 문서** (CORR 18) |
| 6/1 백업 스냅샷 | `C:\Users\keti\Desktop\keti_mlops_full_dump.2026-06-01.orig.bak.md` | 정정 전 원문(2026-06-01), 이력 추적용 — **2026-07-24 확인: 현존하지 않음(삭제/미생성 [확인 필요])** |
| WBS 빌더 | `C:\Users\keti\Desktop\박지상\generate_wbs.py` | **정정(CORR 18)**: 기재됐던 `build_wbs_v3_full.py`는 현존하지 않음 — 현존 빌더는 `generate_wbs.py`(출력 `MLOps_WBS.xlsx` 고정) |
| WBS 산출물 | `C:\Users\keti\Desktop\박지상\MLOps_WBS.xlsx` | **정정(CORR 18)**: `MLOps_WBS_v3.xlsx`는 현존하지 않음(개명/정리 추정 [확인 필요]). Downloads에 구버전 사본 다수 |
| 거버넌스 도구(로컬 클론) | `C:\Users\keti\Desktop\mlops-tools\` | gitea `<org>/mlops-tools` 로컬 작업본 |
| 거버넌스 컨벤션 | `C:\Users\keti\Desktop\mlops-tools\docs\governance.md` | 라이프사이클 태그·메타 정의 — **정정(CORR 18): `docs/` 디렉터리는 2026-06-17 커밋 `1c45416`로 삭제됨**(`governance.md`·`governance_v2_proposal.md`·`registry_schema_benchmark.md` 포함). 현재는 git 이력으로만 존재(`git show 1c45416^:docs/governance.md`로 복구 가능). `register_model.py` 주석·README에 참조 잔존(dangling). docs/에 남은 파일은 `meeting_feedback_response_20260626.md`뿐 |
| 등록 스크립트 | `C:\Users\keti\Desktop\mlops-tools\scripts\governance\register_model.py` | MLflow tag 기반 등록/조회 CLI |
| **Streamlit 포털 진입점** | `C:\Users\keti\Desktop\mlops-tools\services\portal\Home.py` | 포털 메인 — 6페이지 멀티페이지 앱(아래 16.4) _[휘발성]_ |
| 포털 뷰 디렉터리 | `C:\Users\keti\Desktop\mlops-tools\services\portal\views\` | **정정(CORR 15·18)**: 7/14 개편으로 `pages\` 6페이지 → **`views\` 5뷰**(list·compare·infer·monitor·governance) + 루트 헬퍼(`upload_form.py`·`drift_section.py`) — §6.10.10 _[휘발성·2026-07-24 검증]_ |
| 포털 단독 Dockerfile | `C:\Users\keti\Desktop\mlops-tools\services\portal\Dockerfile` | **갱신**: 빌드 시 의존성 박제형으로 개정(python:3.11-slim + `pip install -r requirements.txt`, 빌드 컨텍스트=리포 루트). 단 서버 가동은 여전히 runtime pip 패턴(§6.6). compose 서비스 정의는 서버측에만 존재 _[휘발성]_ |
| **드리프트 빌드 도구** | `C:\Users\keti\Desktop\mlops-tools\scripts\drift\build_reference.py` | reference(실제, HDF5 metadata attrs 5 feature 추출) 생성 — 커밋 `9d8bcd7`에서 dummy→real 전환 _[휘발성]_ |
| 드리프트 워크스페이스 빌더 | `C:\Users\keti\Desktop\mlops-tools\scripts\drift\build_workspace.py` | Evidently UI 워크스페이스/스냅샷 구성(합성 current — 7/21부로 build_current.py로 대체 흐름) _[휘발성]_ |
| **드리프트 current 빌더** | `C:\Users\keti\Desktop\mlops-tools\scripts\drift\build_current.py` | **신규(7/21, CORR 16)**: 실입력 `current_log.csv` + 시드 → 워크스페이스 재구성 — §6.11.7 _[휘발성]_ |
| cooling-project 모델 코드 | `C:\Users\keti\Desktop\cooling-project-3d-unet\` | gitea `<org>/cooling-project` 로컬 작업본 |
| ci.yml | `C:\Users\keti\Desktop\cooling-project-3d-unet\.gitea\workflows\ci.yml` | push 자동 lint/py_compile |
| onnx_validate.yml | `C:\Users\keti\Desktop\cooling-project-3d-unet\.gitea\workflows\onnx_validate.yml` | 수동 ONNX 검증 워크플로 |
| onnx_deploy.yml | `C:\Users\keti\Desktop\cooling-project-3d-unet\.gitea\workflows\onnx_deploy.yml` | 수동 배포(validate→config확인→복사→load→READY 폴링→메타) |
| ONNX 검증기(인라인 사본) | `C:\Users\keti\Desktop\cooling-project-3d-unet\.gitea\scripts\onnx_validate.py` | mlops-tools가 org private라 cross-repo clone 불가 → cooling-project에 인라인 이원화(drift 위험, §9 참조) |
| MLflow 갱신 스크립트 | `C:\Users\keti\Desktop\cooling-project-3d-unet\.gitea\scripts\mlflow_update.py` | CI deploy 끝 MLflow 자동 갱신 단계(커밋 `3ad026f`) |
| ONNX export 스크립트 | `C:\Users\keti\Desktop\cooling-project-3d-unet\export_onnx.py` | **opset=17** (원문 6/1의 'opset 14'는 부정확). opset 선택 사유는 여전히 **[확인 필요]** |
| U-Ecotron 패키지 | `C:\Users\keti\Desktop\ONNX_simplefied_PINN\` | §11 U-Ecotron PINN 사례 |
| Postman 컬렉션 | `C:\Users\keti\Desktop\KETI Triton (GPU 서버 <gpu-server>).postman_collection.json` | **정정(CORR 18)**: 바탕화면 루트로 이동·개명(실 파일명에 서버 IP 포함 — 공개 표기는 마스킹), **8폴더/28리퀘스트**로 확장. 구 위치(`ONNX_simplefied_PINN\`)엔 없음 _[휘발성·2026-07-24 검증]_ |
| 벤치마킹 문서 | `C:\Users\keti\Desktop\비교\발표물\benchmark_complete.md` | §10.4A 산출물 — 7/14 `발표물\`로 이동, `benchmark_ppt.pptx`·`benchmark_notion.zip` 동반 (CORR 18) |
| Triton compose | `/srv/triton/compose/` (GPU 서버) | 인프라팀 관리, 박지상 미관리 |
| MLOps stack compose | `/home/<user>/mlops/compose/docker-compose.yml` (GPU 서버) | mlops 스택 정의. 포털/Evidently compose 서비스는 서버측 이 파일에 추가됨 _[휘발성]_ |
| Gitea 데이터 | `/home/<user>/mlops/gitea/` (GPU 서버) | |
| MLflow DB | `/home/<user>/mlops/mlflow/db/mlflow.db` (GPU 서버) | 백엔드 **SQLite** |
| MLflow artifacts | `/home/<user>/mlops/mlflow/artifacts/` (GPU 서버) | 로컬 디스크 저장(MinIO 제외, §8·MEMORY) |

> **근거**: 단일 운영자 폐쇄망에서 "어디에 무엇이 있는지"를 한 표로 고정해 두면 운영 인계·재현 비용이 급감한다. 로컬 클론(`C:\Users\keti\Desktop\...`)과 서버 경로(`/home/<user>/mlops/...`, `/srv/triton/...`)를 한곳에 묶어 cross-machine 작업을 추적 가능하게 했다.

### 16.2 주요 URL _[휘발성·2026-07-24 검증 — 전 서비스 HTTP 200 재확인]_ (가동 상태는 §2 참조)

| 서비스 | URL | 자격증명 | 비고 |
|---|---|---|---|
| MLflow UI | `http://<gpu-server>:5000` | — | 실험 2개·등록모델 9개/버전 14개(§7, CORR 13) |
| Gitea | `http://<gpu-server>:3000` | `[credential stored separately]` | |
| Grafana | `http://<gpu-server>:3001` | `[credential stored separately]` | 13.0.1, Triton 7패널 대시보드(`triton.json`) |
| Prometheus | `http://<gpu-server>:9090` | — | 타겟 2개(self, triton) up, 알림 룰 0 |
| Triton HTTP | `http://<gpu-server>:28000` | — | |
| Triton gRPC | `<gpu-server>:28001` | — | |
| Triton metrics | `http://<gpu-server>:28002/metrics` | — | `nv_gpu_*` 정상 수집 |
| **Streamlit 거버넌스 포털** | `http://<gpu-server>:8510` | — | 컨테이너 `mlops-portal`, 8510→8501, HTTP 200 — 7/21 재배포(5뷰 개편판, §6.10.10) _[휘발성·2026-07-24 검증]_ |
| **Evidently 드리프트 UI** | `http://<gpu-server>:8511` | — | 컨테이너 `evidently-ui`, 8511→8001, HTTP 200, PoC — 7/21 재배포 _[휘발성·2026-07-24 검증]_ |
| cooling-project repo | `http://<gpu-server>:3000/<org>/cooling-project` | `[credential stored separately]` | 모델 코드 |
| mlops-tools repo | `http://<gpu-server>:3000/<org>/mlops-tools` | `[credential stored separately]` | 거버넌스 + 드리프트 도구 + Streamlit 포털 |

> **정정 반영(CORR 4·11)**: 원문 6/1에는 포털·Evidently UI가 없었으나, 2026-06-19 점검 기준 포털(8510)·Evidently UI(8511)가 배포·가동 중이다. mlops-tools 리포가 `services/portal`·`scripts/drift`로 확장되었다.
> **시크릿 처리**: Gitea·Grafana 자격증명 raw 값은 **§17**에만 존재. 이 부록에서는 절대 노출하지 않는다.
> **근거**: 포트 매핑(8510→8501, 8511→8001)을 명시해 호스트 노출 포트와 컨테이너 내부 포트를 구분 — 폐쇄망 reverse-proxy/방화벽 설정 시 즉시 참조.

### 16.3 자주 쓰는 명령

```bash
# SSH 접속
ssh <gpu-server>

# 컨테이너 상태 (현재 9개 가동: +mlops-portal, +evidently-ui)  [휘발성·2026-07-24 재확인]
ssh <gpu-server> "sudo docker ps"

# 학습 시작 (trainer 컨테이너 내부 GPU=L40S 사용)
ssh <gpu-server> "sudo docker exec -d trainer bash /workspace/_run_train.sh"

# 학습 로그
ssh <gpu-server> "sudo docker exec trainer tail -f /tmp/train_run.log"

# 거버넌스 조회 (MLflow tag 기반)
cd C:\Users\keti\Desktop\mlops-tools
python scripts\governance\register_model.py show

# Runner 로그
ssh <gpu-server> "sudo docker logs act_runner --tail 30"

# Triton 모델 메타
curl http://<gpu-server>:28000/v2/models/ecotron_thermal_f

# Triton 모델 reload (EXPLICIT 모드)
curl -X POST http://<gpu-server>:28000/v2/repository/models/<name>/load

# 드리프트 reference 재생성 (실제 HDF5 metadata 기반)  [휘발성]
cd C:\Users\keti\Desktop\mlops-tools
python scripts\drift\build_reference.py
python scripts\drift\build_workspace.py

# 드리프트 current 재구성 (실입력 로그 + 시드, 7/21 신규 — §6.11.7)  [휘발성·2026-07-24]
python scripts\drift\build_current.py <reference_csv> <workspace_dir> --current-log <current_log.csv> --seed-days 7

# 드리프트 current 로그 확인 (서버, named volume 내부)  [휘발성·2026-07-24]
ssh <gpu-server> "sudo docker exec mlops-portal sh -c 'wc -l /data/drift/current_log.csv; cut -d, -f7 /data/drift/current_log.csv | sort | uniq -c'"

# Streamlit 거버넌스 포털 로컬 실행  [휘발성]
cd C:\Users\keti\Desktop\mlops-tools\services\portal
streamlit run Home.py
```

> **정정 반영(CORR 4·5·6)**: `docker ps`는 원문 6/1엔 컨테이너 7개였으나 현재 9개(+`mlops-portal`, +`evidently-ui`, 2026-06-19 검증). 드리프트 빌드 명령(`build_reference.py`/`build_workspace.py`)과 Streamlit 실행 명령(`streamlit run Home.py`)을 추가했다.
> **근거**: `docker` 명령에 전부 `sudo`가 붙는 이유는 박지상 계정이 docker 그룹 밖이라 sudo 필요(§4·MEMORY GPU 서버 접속). Triton reload가 `POST .../load`인 이유는 EXPLICIT 모델 제어 모드라서 — 자동 폴링이 아니라 명시적 load 호출이 필요(§5).

### 16.4 Streamlit 포털 페이지 인덱스 _[휘발성·2026-06-19 검증 → 2026-07-24 정정]_

> **정정(CORR 15)**: 7/14~15 개편으로 실제 구조는 `services/portal/views/` **5뷰**(모델 `list.py` / 버전 비교 `compare.py` / 추론 `infer.py` / 모니터링 `monitor.py` / 거버넌스 트렌드 `governance.py`) — §6.10.10 참조. 아래 6페이지 표는 **6/19 시점 기록**으로 보존한다(업로드→'모델' 뷰 통합, 드리프트→'모니터링' 뷰 통합).

mlops-tools `services/portal/pages/` 의 6페이지(구 구조). 모두 PoC 단계(런타임 `pip install` 패턴, compose 서비스는 서버측에만 추가됨).

| 페이지 파일 | 기능 |
|---|---|
| `1_모델_업로드.py` | 모델 업로드 → 검증 → Triton load → MLflow 등록 |
| `2_모델_리스트.py` | 등록 모델 리스트 + Model Card 편집 |
| `3_Triton_모니터링.py` | Triton health + metrics + Grafana iframe 임베드 |
| `4_거버넌스_트렌드.py` | MLflow tag 기반 거버넌스 트렌드(Plotly) |
| `5_추론_테스트.py` | shape 자동감지 입력 UI로 추론 테스트 |
| `6_드리프트.py` | Evidently iframe 임베드 + reference 재생성 |

> **근거**: 셀프서비스 포털을 "업로드→검증→배포→모니터링→드리프트"의 라이프사이클 순서로 페이지를 구성해, 단일 운영자가 GUI로 거버넌스 전 과정을 수행하도록 설계. iframe으로 Grafana/Evidently를 한 화면에 모아 도구 통합 UX를 단순화.

---
