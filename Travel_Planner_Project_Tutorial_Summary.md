# AI Travel Itinerary Planner - Tutorial Summary

This document provides a comprehensive, detailed breakdown of how the tutorial structures, builds, and deploys the **AI Travel Itinerary Planner** project, including its application logic, GCP infrastructure, and complete **ELK Stack (Elasticsearch, Logstash, Kibana) + Filebeat** logging architecture on Kubernetes.

---

## 1. Application Overview & Tech Stack

### Purpose
The **AI Travel Itinerary Planner** is an interactive web application where a user provides a destination city and their personal travel interests (e.g., historical sites, food, nature). The application uses a Large Language Model (LLM) to generate a customized, structured, bulleted day-trip travel itinerary.

### Tech Stack
* **UI Framework:** Streamlit (`app.py`, port `8501`)
* **LLM Orchestration:** LangChain Core (`langchain_groq`, `ChatPromptTemplate`)
* **LLM Provider:** Groq Cloud (`llama-3.3-70b-versatile`, temperature = `0.3`)
* **Configuration:** Python `python-dotenv` for loading environment variables
* **Logging Utility:** Python standard `logging` configured to write daily logs to `logs/log_YYYY-MM-DD.log`
* **Custom Error Handling:** `CustomException` capturing script name, line number, and error messages via `sys`
* **Package Management:** Standard `setup.py` enabling editable local installations (`pip install -e .`)

---

## 2. Application Architecture & Code Structure

```text
03-Travel-Planner/
├── archive/                            # Original tutorial source code & YAMLs
│   ├── app.py                          # Streamlit user interface
│   ├── setup.py                        # Package setup for src module
│   ├── requirements.txt                # Python dependencies
│   ├── Dockerfile                      # Containerization definition
│   ├── k8s-deployment.yaml             # Kubernetes Deployment & LoadBalancer Service
│   ├── elasticsearch.yaml              # Elasticsearch Deployment, PVC, and Service
│   ├── logstash.yaml                   # Logstash ConfigMap, Deployment, and Service
│   ├── filebeat.yaml                   # Filebeat ConfigMap, DaemonSet, RBAC
│   ├── kibana.yaml                     # Kibana Deployment and Service
│   └── src/
│       ├── config/
│       │   └── config.py               # Loads GROQ_API_KEY from environment
│       ├── chains/
│       │   └── itinerary_chain.py      # Groq LLM invocation & prompt template
│       ├── core/
│       │   └── planner.py              # TravelPlanner state class (city, interests, messages)
│       └── utils/
│           ├── logger.py               # Custom file logger
│           └── custom_exception.py     # Custom error wrapper with traceback
```

### Component Breakdown
1. **`src/config/config.py`**:
   Loads `GROQ_API_KEY` from the system environment or local `.env`.
2. **`src/chains/itinerary_chain.py`**:
   Initializes `ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.3)`. Formats system prompt:
   `"You are a helpful travel assistant. Create a day trip itinerary for {city} based on user's interest : {interests}. Provide a brief, bulleted itinerary"`.
3. **`src/core/planner.py`**:
   Encapsulates the planning workflow in a `TravelPlanner` class:
   * `set_city(city)`: Saves city and appends a `HumanMessage`.
   * `set_interests(interests_str)`: Splits comma-separated interests and appends a `HumanMessage`.
   * `create_itineary()`: Calls `generate_itineary(...)`, stores response, logs completion, and returns output.
4. **`app.py`**:
   Streamlit frontend with form input (`st.text_input` for city and interests). On submission, triggers `TravelPlanner` and renders formatted markdown output.

---

## 3. Infrastructure & Deployment (Tutorial Setup)

### Cloud Infrastructure
* **Cloud Provider:** Google Cloud Platform (GCP) Compute Engine
* **VM Instance Specs:**
  * **Series / Preset:** `E2 Standard` (4 vCPU, 16 GB RAM, 256 GB boot disk)
  * **OS Image:** Ubuntu 24.04 LTS
  * **Firewall Rules:** Inbound HTTP (80), HTTPS (443), Custom TCP (8501, 5601, 9200)

### Manual Host Setup Steps on the VM
1. **Docker Engine:** Installed manually via standard Docker APT repositories; systemd enabled.
2. **Minikube:** Downloaded Linux x86_64 binary and started via `minikube start --driver=docker`.
3. **kubectl:** Installed via Snap (`sudo snap install kubectl --classic`).
4. **Local Repository Sync:** Cloned repository on the VM using personal GitHub token (`data-guru0/TESTING-9`).

### Application Deployment
1. Point VM's Docker client to Minikube: `eval $(minikube docker-env)`.
2. Build image locally inside Minikube: `docker build -t streamlit-app:latest .`
3. Raw secret creation:
   ```bash
   kubectl create secret generic llmops-secrets --from-literal=GROQ_API_KEY="<RAW_KEY>"
   ```
4. Apply Kubernetes manifests: `kubectl apply -f k8s-deployment.yaml`.
5. Expose application:
   ```bash
   kubectl port-forward svc/streamlit-service 8501:80 --address 0.0.0.0
   ```
   Accessed via VM's Public IP on port `8501`.

---

## 4. The Logging Architecture: ELK Stack + Filebeat

The core AIOps focus of this project is enterprise centralized log management using the **ELK Stack (Elasticsearch, Logstash, Kibana)** combined with **Filebeat** as the log shipper.

```text
[ Kubernetes Pods / Nodes ]
   (Writes logs to /var/log/containers/*.log)
            │
            ▼
    [ Filebeat DaemonSet ]
   (Harvests logs, enriches with K8s & host metadata)
            │ Beats Protocol (Port 5044)
            ▼
     [ Logstash Service ]
   (Filters, parses, transforms log data)
            │ HTTP (Port 9200)
            ▼
   [ Elasticsearch Service ]
   (Indexes logs into filebeat-YYYY.MM.DD, stores in 2Gi PVC)
            │
            ▼
     [ Kibana Dashboard ]
   (Visualizes logs, search index pattern filebeat-*, filters)
```

### Detailed Component Roles:

#### 1. Filebeat (Log Collector & Shipper) — `filebeat.yaml`
* **Kind:** Kubernetes `DaemonSet` (runs exactly 1 pod per Kubernetes worker node).
* **Namespace:** `logging`.
* **Privileges & RBAC:** Runs as root (`runAsUser: 0`, `hostNetwork: true`), with dedicated `ClusterRole`, `ClusterRoleBinding`, and `ServiceAccount` allowing read/list/watch access to `namespaces`, `pods`, and `nodes`.
* **Input Volume Mounts:** Mounts `/var/log` and `/var/lib/docker/containers` from the host node to scrape all container logs (`/var/log/containers/*.log`).
* **Processors:**
  * `add_kubernetes_metadata`: Automatically enriches each log line with the Kubernetes Pod name, namespace, container name, and labels.
  * `add_cloud_metadata` & `add_host_metadata`: Enriches logs with VM host information.
* **Output:** Forwards processed logs over TCP port `5044` to `logstash.logging.svc.cluster.local:5044`.

#### 2. Logstash (Log Processing & Filtering) — `logstash.yaml`
* **Kind:** Kubernetes `Deployment` + ClusterIP `Service`.
* **Namespace:** `logging`.
* **Port:** Container port `5044`.
* **Pipeline Configuration (`ConfigMap`):**
  * **Input:** `beats { port => 5044 }`
  * **Filter:** (Extensible for parsing JSON logs, grok patterns, or date filters)
  * **Output:** Sends to `elasticsearch.logging.svc.cluster.local:9200`, creating daily dynamic indices:
    `index => "filebeat-%{+YYYY.MM.dd}"`

#### 3. Elasticsearch (Log Storage & Indexing Engine) — `elasticsearch.yaml`
* **Kind:** Kubernetes `Deployment` + ClusterIP `Service` on port `9200`.
* **Namespace:** `logging`.
* **Storage:** 2 GB `PersistentVolumeClaim` (`elasticsearch-pvc`).
* **Config:** Single-node cluster (`discovery.type: single-node`), disabled basic auth (`xpack.security.enabled: false`), JVM heap allocated at `512m` (`ES_JAVA_OPTS: "-Xms512m -Xmx512m"`).
* **Role:** Acts as the high-speed search database where all logs are indexed and stored.

#### 4. Kibana (Visualization & Analytics Dashboard) — `kibana.yaml`
* **Kind:** Kubernetes `Deployment` + `NodePort` Service (port `5601`, nodePort `30601`).
* **Namespace:** `logging`.
* **Backend Connection:** Points to `http://elasticsearch:9200`.
* **Configuration & Usage in Tutorial:**
  1. Port-forwarded or exposed via VM IP: `kubectl port-forward -n logging svc/kibana 5601:5601 --address 0.0.0.0`.
  2. Created Index Pattern: `filebeat-*` configured with timestamp `@timestamp`.
  3. Explored via **Analytics ➡️ Discover**: Filtered by `kubernetes.container.name` (e.g., `streamlit-container`, `kibana`, `filebeat`), container IDs, and host types to monitor application errors and system health.

---

## 5. Critical Deficiencies & Modernization Roadmap

The tutorial provides a solid conceptual foundation for ELK and Filebeat, but relies on several anti-patterns that must be modernized for an enterprise-ready implementation:

| Area | Tutorial Approach (Manual / Flawed) | Enterprise Standard (Our Target) |
| :--- | :--- | :--- |
| **Secrets Management** | Manual `kubectl create secret` with plaintext API keys in terminal | **SealedSecrets** encrypted in Git or Vault |
| **CI/CD Automation** | Manual `git clone`, manual `eval docker-env`, manual build | **Automated Jenkins CI/CD Pipeline** |
| **Container Registry** | Ephemeral local Minikube Docker daemon | **GitHub Container Registry (GHCR)** with versioned tags |
| **Network & Ingress** | Background terminal `kubectl port-forward` commands | Native **OrbStack LoadBalancer** & **Cloudflare Tunnels** |
| **Resource Efficiency** | Heavy Java-based ELK stack (~2.5GB+ RAM) on single node | Scaled resource requests/limits, lightweight Fluentbit / Vector options |
| **Code Structure** | Missing error fallbacks for Streamlit, basic prompt structure | Modular Streamlit UI with conversation state, health checks, and metrics |

---

## 6. Our Modernized Production Implementation ($0 Cost on Mac Mini)

We transformed the tutorial's manual, paid cloud approach into an automated, enterprise-grade GitOps architecture running locally on an Apple Silicon Mac Mini (OrbStack Kubernetes) for **$0.00**:

### Architecture Comparison

| Component | Tutorial Way (Paid / Manual) | Our Modernized Production Setup ($0 Cost) |
| :--- | :--- | :--- |
| **Host / Compute** | Paid GCP Compute Engine E2 VM ($70+/mo) | **Mac Mini** running **OrbStack Kubernetes** (Free, native performance) |
| **LLM & Guardrails** | Raw LLM prompt without safety layer | **Groq Free Tier** + **Meta Llama Prompt Guard** (`llama-prompt-guard-2-86m`) |
| **Secrets Management** | Plaintext keys passed in terminal | **Bitnami SealedSecrets** (`app-secret` & `git-secret`) encrypted in Git |
| **CI/CD Pipeline** | Manual SSH & manual docker builds | **Jenkins CI/CD** (`http://localhost:8081`) with local image cache pruning |
| **Container Registry** | Local Minikube daemon | **GitHub Container Registry (GHCR)** with `imagePullPolicy: Always` |
| **Port Routing** | Manual background `kubectl port-forward` | **Deterministic Port Allocation** (`:8083` App, `:8084` Kibana per `PORT_PLAN.md`) |
| **Centralized Logging** | Heavy default ELK configuration | Tuned **ELK 7.17 + Filebeat DaemonSet** with RBAC and 512MB JVM heap |
| **Observability** | Generic pod crashes | Direct **`SECURITY_ALERT`** log tracking in Kibana for intercepted jailbreak attacks |
| **Public Access** | Insecure plain HTTP on VM IP | **Cloudflare Tunnel (`cloudflared`)** for zero-trust HTTPS URLs |

### Production File Layout

```text
03-Travel-Planner/
├── app/
│   └── ui.py                        # Streamlit frontend with security alert banner
├── core/
│   ├── config.py                    # Environment & guardrail threshold configurations
│   └── planner.py                   # TravelPlanner workflow + Meta Llama Prompt Guard
├── utils/
│   ├── logger.py                    # Structured daily file & stdout logging
│   └── custom_exception.py          # Detailed traceback error wrapper
├── k8s/
│   ├── 00-namespace.yaml            # travel-planner and logging namespaces
│   ├── raw-app-secret.yaml          # Plaintext Groq API key (Git-ignored)
│   ├── raw-git-secret.yaml          # Plaintext GitHub PAT (Git-ignored)
│   ├── sealed-app-secret.yaml       # Bitnami encrypted Groq API key (Git-tracked)
│   ├── sealed-git-secret.yaml       # Bitnami encrypted GHCR PAT (Git-tracked)
│   ├── configmap.yaml               # Runtime model & threshold configurations
│   ├── deployment.yaml              # App pod deployment (1 replica, probes, GHCR pull)
│   ├── service.yaml                 # LoadBalancer on port 8083 -> 8501
│   ├── elasticsearch.yaml           # Elasticsearch single-node deployment & 2Gi PVC
│   ├── logstash.yaml                # Logstash pipeline (:5044 -> :9200)
│   ├── filebeat.yaml                # Filebeat DaemonSet with RBAC & metadata enrichment
│   └── kibana.yaml                  # Kibana dashboard LoadBalancer on port 8084 -> 5601
├── Dockerfile                       # Multi-stage container recipe (python:3.10-slim)
├── .dockerignore                    # Excludes k8s manifests, raw secrets, and local venvs
├── .gitignore                       # Protects raw secrets, pem certs, and .env
├── Jenkinsfile                      # Automated CI/CD (Build -> Push -> Clean Mac Cache -> Deploy)
├── requirements.txt                 # Pinned dependencies including langchain and groq
└── run.py                           # Local execution entrypoint
```

---

### Deep Dive: AI Security Guardrail Architecture (Meta Llama Prompt Guard)

The guardrail is an **in-process software interceptor** built directly into the main application. It acts as an automated security screener before any user input reaches the generative LLM.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        MAIN APPLICATION CODEBASE                       │
│                                                                        │
│  1. [Configuration] core/config.py & k8s/configmap.yaml                │
│     - Defines GUARD_MODEL ("meta-llama/llama-prompt-guard-2-86m")      │
│     - Defines GUARD_THRESHOLD (0.50 risk score cutoff)                 │
│                                                                        │
│  2. [Security Engine] core/planner.py                                  │
│     - check_prompt_safety() runs pre-flight attack check on Groq LPUs  │
│     - GuardrailException raised if score > 0.50                        │
│     - Emits structured "SECURITY_ALERT" log                            │
│                                                                        │
│  3. [Visual UI] app/ui.py                                              │
│     - Catches GuardrailException                                       │
│     - Displays bright red warning banner with threat percentage        │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (Logs to stdout)
┌────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILITY (ELK STACK)                       │
│                                                                        │
│  4. [Monitoring Dashboard] Kibana (Port :8084)                         │
│     - Filter: message: "SECURITY_ALERT" tracks attacks live            │
└────────────────────────────────────────────────────────────────────────┘
```

#### The 4 Layers of the Guardrail:
1. **Dynamic Configuration (`core/config.py` & `k8s/configmap.yaml`):**
   - Reads `GUARD_MODEL` and `GUARD_THRESHOLD` from environment variables injected by Kubernetes.
   - Allows operators to adjust sensitivity thresholds (e.g. from `0.50` to `0.30`) in production without rebuilding the Docker container.
2. **Backend Interceptor (`core/planner.py`):**
   - In `check_prompt_safety()`, sends the user's prompt to Groq's Prompt Guard model (~40ms latency).
   - If the attack probability score exceeds the threshold:
     - Emits a structured log: `SECURITY_ALERT | Guardrail: Meta-Llama-Guard | Risk_Score: 0.9996 ...`
     - Raises `GuardrailException`.
     - **Skips the generation LLM entirely** (saving token costs and preventing jailbreak execution).
3. **Frontend Alert Banner (`app/ui.py`):**
   - Intercepts `GuardrailException` in the Streamlit UI.
   - Renders a prominent red alert banner displaying the calculated threat score.
4. **Centralized Log Monitoring (ELK Stack + Kibana):**
   - Filebeat harvests the `SECURITY_ALERT` log line from the node, Logstash enriches it, and Elasticsearch indexes it.
   - Kibana (`http://localhost:8084`) allows SecOps to filter and visualize prompt injection attempts in real time.

