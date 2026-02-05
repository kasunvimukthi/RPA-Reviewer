## Overview
I have designed and implemented a **Strict RPA Code Reviewer** that provides clear **Pass / Fail** compliance metrics.

## Components
- **Backend (FastAPI)**: Analyzes UiPath projects and calculates compliance statistics.
- **Frontend (React + Vite)**: Displays a premium dashboard with a summary header and detailed tables.

## Verification

### 1. Run Backend
```bash
python -m rpa_reviewer.server
```
### 2. Run Frontend
```bash
cd ui
npm run dev
```
### 3. Usage
- Open the Web UI.
- Select required Categories.
- Click **Analyze Project.**

- View Results:
  - **Header:** Shows Passed count, Failed count, and Overall Compliance Percentage.
  - **Detailed Reports:** Displays checkpoint tables for each review Area.

**Logic**

**Pass Count:** Number of checkpoints marked as Pass

**Fail Count:** Number of checkpoints marked as Fail

**Percentage Calculation:**
```code
(Passed / (Passed + Failed)) * 100
```
**Note:** N/A results are ignored in all calculations.

```code
If you want this **even more minimal** (single paragraph style, no sub-headings at all), tell me and I’ll rewrite it exactly like that 👍
