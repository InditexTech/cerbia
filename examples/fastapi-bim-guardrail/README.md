<!--
SPDX-FileCopyrightText: 2026 Jose Manuel Caamaño González (jmcaamanog)
SPDX-FileCopyrightText: 2026 INDUSTRIA DE DISEÑO TEXTIL S.A. (INDITEX S.A.)

SPDX-License-Identifier: Apache-2.0
-->

# FastAPI BIM Common Data Environment (CDE) Guardrail

This example demonstrates how to integrate **CerbIA** as a bidirectional security gate middleware in a **FastAPI** application for an AI assistant operating within an **International Retail BIM Common Data Environment (CDE)**.

In multi-tenant, multi-package construction and store roll-out projects (e.g., international store fit-outs), multiple subcontractors, engineering firms, and BIM coordinators query project knowledge bases, federated IFC models, and technical specifications. This example secures both **inbound user queries** and **outbound LLM responses**.

---

## 🏗️ BIM Work Breakdown Structure (WBS) Matrix

International store construction projects segregate management packages (commercial tenders and procurement) from BIM technical modeling disciplines:

| Package Code | Package Name (ES / EN) | Discipline Code | Discipline Name (ES / EN) |
| :--- | :--- | :---: | :--- |
| `000GRL` | GESTIÓN PROYECTO / PROJECT MANAGEMENT | `000` | GESTIÓN / MANAGEMENT |
| `000GRL` | GESTIÓN OBRA / CONSTRUCTION MANAGEMENT | `000` | GESTIÓN / MANAGEMENT |
| `000GRL` | GESTIÓN PROYECTO / PROJECT MANAGEMENT | `CRD` | COORDINACIÓN / COORDINATION |
| `010EXI` | ESTADO ACTUAL / EXISTING CONDITIONS | `ARQ` | ARQUITECTURA / ARCHITECTURE |
| `020CON` | CONSULTING / CONSULTANCY | `ARQ` | ARQUITECTURA / ARCHITECTURE |
| `100OBR` | OBRA IN SITU / IN SITU CONSTRUCTION | `OBR` | OBRA IN SITU / IN SITU CONSTRUCTION |
| `110CAM` | CARPINTERÍA METÁLICA / METALWORK | `FAC` | FACHADA / FACADE |
| `120PAU` | PUERTAS AUTOMÁTICAS / AUTOMATIC DOORS | `FAC` | FACHADA / FACADE |
| `130ENV` | ENVOLVENTE / ENVELOPE | `ENV` | ENVOLVENTE / ENVELOPE |
| `150MOA` | MOBILIARIO ALMACENES / STOCKROOM FURNITURE | `MOA` | MOBILIARIO ALMACENES / STOCKROOM FURNITURE |
| `170CMD` | CARPINTERÍA MADERA / WOOD JOINERY | `CMD` | CARPINTERÍA MADERA / WOOD JOINERY |
| `200CLI` | CLIMATIZACIÓN / AIR CONDITION | `CLI` | CLIMATIZACIÓN / AIR CONDITION |
| `200CLI` | CLIMATIZACIÓN / AIR CONDITION | `HUM` | CONTROL DE HUMOS / SMOKE CONTROL |
| `300PCI` | INSTAL. PCI / FIRE ENGINEERING | `HUM` | CONTROL DE HUMOS / SMOKE CONTROL |
| `110CAM` | CARPINTERÍA METÁLICA / METALWORK | `HUM` | CONTROL DE HUMOS / SMOKE CONTROL |
| `130ENV` | ENVOLVENTE / ENVELOPE | `HUM` | CONTROL DE HUMOS / SMOKE CONTROL |
| `300PCI` | INSTAL. PCI / FIRE ENGINEERING | `PCI` | INSTAL. PCI / FIRE ENGINEERING |
| `400FNT` | FONTANERÍA Y SANEAMIENTO / PLUMBING AND DRAINAGE | `FNT` | FONTANERÍA Y SANEAMIENTO / PLUMBING AND DRAINAGE |
| `500ELE` | ELECTRICIDAD / ELECTRICITY | `ELE` | ELECTRICIDAD / ELECTRICITY |
| `510IL1` | ILUMINACIÓN APARATOS IMAGEN / SALES AREA LIGHTING | `ALU` | ILUMINACIÓN APARATOS IMAGEN / SALES AREA LIGHTING |
| `510IL2` | ILUMINACIÓN LINEAL / LINEAR LIGHTING | `ALU` | ILUMINACIÓN LINEAL / LINEAR LIGHTING |
| `540RED` | INFRAESTRUCTURAS DE RED / NETWORK INFRASTRUCTURE | `RED` | INFRAESTRUCTURAS DE RED / NETWORK INFRASTRUCTURE |
| `600ATH` | ANTENAS ANTIHURTO / ANTITHEFT ANTENNA | `ATH` | ANTENAS ANTIHURTO / ANTITHEFT ANTENNA |
| `610CTV` | CCTV | `CTV` | CCTV |
| `620SON` | SONIDO / SOUND | `SON` | SONIDO / SOUND |
| `630VIS` | VISUALES / VISUALS | `VIS` | VISUALES / VISUALS |
| `700EYA` | ESCALERAS Y ASCENSORES / STAIRS AND ELEVATORS | `EYA` | ESCALERAS Y ASCENSORES / STAIRS AND ELEVATORS |
| `900MET` | ESTRUCTURA METÁLICA / METALLIC STRUCTURE | `EST` | ESTRUCTURA / STRUCTURE |
| `000GRL` | GEOMETRÍA ESTRUCTURA / STRUCTURE GEOMETRY | `EST` | ESTRUCTURA / STRUCTURE |

---

## 🛡️ Security Architecture: Threat Model & Guardrails

```
                           ┌──────────────────────────────────────────┐
                           │               USER PROMPT                │
                           └────────────────────┬─────────────────────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │      INPUT GATE       │
                                    │  (CerbIA SecurityGate)│
                                    └───────────┬───────────┘
                           SAFE                 │            UNSAFE
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼                                                             ▼
    ┌───────────────────────────┐                                ┌───────────────────────────┐
    │     LLM INFERENCE         │                                │    HTTP 400 BAD REQUEST   │
    │  System Prompt Injected   │                                │  Blocked before execution │
    │    with Canary Token      │                                └───────────────────────────┘
    └────────────┬──────────────┘
                 │
                 ▼
    ┌───────────────────────────┐
    │       OUTPUT GATE         │
    │  (Canary Leak Detection)  │
    └────────────┬──────────────┘
SAFE             │            UNSAFE (Leaked Canary or PII)
┌────────────────┴─────────────────────────────┐
▼                                              ▼
┌───────────────────────────┐     ┌───────────────────────────┐
│     HTTP 200 OK           │     │  HTTP 422 UNPROCESSABLE   │
│ Verified Technical Answer │     │ Exfiltration Prevented    │
└───────────────────────────┘     └───────────────────────────┘
```

### The 4 Real-World Protection Scenarios:
1. **Scope Override / Prompt Injection**: A contractor attempts jailbreaking the AI to bypass BEP rules, override coordination clearance or approve structural alterations without Lead Engineer sign-off.
   - *Protected by*: `PromptInjectionScanner` & `KeywordScanner`.
2. **Confidential Tender Budget Protection (Canary Tokens)**: An adversary attempts extracting confidential unit rates, budget margins (PEM), or system prompts. CerbIA injects unique canary tokens into system prompts and scans responses before delivery.
   - *Protected by*: `CanaryLeakScanner`.
3. **Subcontractor Personal Data (PII)**: Daily site incident reports containing unredacted Spanish DNI, passport numbers, personal phones or emails of field workers.
   - *Protected by*: `PiiScanner`.
4. **Malicious URLs**: Submittal document links or external URLs with untrusted/suspicious TLDs (`.xyz`, phishing domains).
   - *Protected by*: `MaliciousUrlScanner`.

---

## 🚀 Running the Example

### 1. Execute Automated Scenarios

Run the complete 5-scenario test suite in memory:

```bash
python examples/fastapi-bim-guardrail/test_scenarios.py
```

### 2. Run the Live FastAPI Server

Start the API service with Uvicorn:

```bash
uvicorn examples.fastapi-bim-guardrail.app:app --reload
```

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

---

## 📁 File Structure

* `bim_matrix.py`: Complete typed data model of the retail store BIM WBS matrix.
* `config.cerbia.yaml`: Declarative CerbIA gate configuration.
* `app.py`: FastAPI server implementing input and output gates.
* `test_scenarios.py`: Automated test runner covering legitimate and adversarial scenarios.
* `README.md`: This technical specification.
