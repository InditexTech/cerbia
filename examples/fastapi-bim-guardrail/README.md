<!--
SPDX-FileCopyrightText: 2026 Jose Manuel Caamaño González (jmcaamanog)
SPDX-FileCopyrightText: 2026 INDUSTRIA DE DISEÑO TEXTIL S.A. (INDITEX S.A.)

SPDX-License-Identifier: Apache-2.0
-->

# FastAPI BIM Common Data Environment (CDE) Guardrail

This example demonstrates how to integrate **CerbIA** as a bidirectional security gate middleware in a **FastAPI** application for an AI assistant operating within a **BIM Common Data Environment (CDE)**.

In multi-tenant, multi-package construction and store roll-out projects, subcontractors, engineering firms, and BIM coordinators query project knowledge bases, federated IFC models, and technical specifications. This illustrative example demonstrates securing both **inbound user queries** and **outbound LLM responses** (with simulated model execution).

---

## 🏗️ BIM Work Breakdown Structure (WBS) Matrix

Construction projects segregate management packages (commercial tenders and procurement) from BIM technical modeling disciplines:

| Package Code | Package Name | Discipline Code | Discipline Name |
| :--- | :--- | :---: | :--- |
| `200HVAC` | HVAC & Mechanical Works | `HVAC` | Heating, Ventilation & Air Conditioning |

---

## 🛡️ Security Architecture: Threat Model & Guardrails

```mermaid
flowchart TD
    User([User Prompt]) --> InputGate[Input Gate: CerbIA SecurityGate]
    InputGate -- Safe --> LLM[LLM Inference\nSimulated Model Response]
    InputGate -- Unsafe --> Block400[HTTP 400 Bad Request\nBlocked before execution]
    LLM --> OutputGate[Output Gate: Canary & PII Scanners]
    OutputGate -- Safe --> Response200[HTTP 200 OK\nVerified BIM Technical Answer]
    OutputGate -- Unsafe --> Block422[HTTP 422 Unprocessable Content\nExfiltration Prevented]
```

### Protection Scenarios:
1. **Scope Override / Prompt Injection**: A contractor attempts jailbreaking the AI to bypass rules, override coordination clearances, or approve alterations without proper review.
   - *Protected by*: `PromptInjectionScanner` & `KeywordScanner`.
2. **Confidential Tender Budget Protection (Canary Tokens)**: An adversary attempts extracting confidential unit rates, budget margins, or system prompts. CerbIA injects unique canary tokens into system prompts and scans responses before delivery.
   - *Protected by*: `CanaryLeakScanner`.
3. **Subcontractor Personal Data (PII)**: Daily site incident reports containing unredacted Spanish DNI, passport numbers, personal phones, or emails.
   - *Protected by*: `PiiScanner`.
4. **Malicious URLs**: Submittal document links or external URLs with untrusted/suspicious TLDs (`.xyz`, phishing domains).
   - *Protected by*: `MaliciousUrlScanner`.

---

## 🚀 Running the Example

### 1. Execute Automated Pytest Suite

Run the test suite:

```bash
pytest examples/fastapi-bim-guardrail/test_scenarios.py
```

### 2. Run the Live FastAPI Server

Start the API service with Uvicorn:

```bash
uvicorn --app-dir examples/fastapi-bim-guardrail app:app --reload
```

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

---

## 📁 File Structure

* `bim_matrix.py`: Typed data model of the illustrative BIM WBS package and discipline.
* `app.py`: FastAPI server implementing input and output gates.
* `test_scenarios.py`: Pytest test suite validating input safety and output leak prevention.
* `README.md`: Technical documentation and setup instructions.
