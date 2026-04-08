# **CDV Explorer**

_Modern decentralized software ecosystems evolve through crowdsourced improvement proposals (IPs) that are continuously shaped and autonomously implemented by independent actors. As a result, these ecosystems exhibit so-called **Community-Driven Variability (CDV)**, a novel paradigm that extends beyond traditional variability-intensive systems. This page allows to explore the proposal space of such ecosystems by providing interactive visualizations and insights about their evolution, authorship, classification, conformity, and inter-proposal relationships._

<div align="center">
  <img width="100%" src="./assets/thumb.png" alt="CDV Explorer Homepage" />
  
</div>

</br>

<div align="center">
  <strong>
    👋 <a href="#introduction">Introduction</a> &nbsp;&nbsp;| &nbsp;&nbsp; 
    🚀 <a href="#setup">Setup</a> &nbsp;&nbsp;|&nbsp;&nbsp; 
    🛠️ <a href="#developer-notes">Developer Notes</a> 
  </strong>
</div>

</br>

<div align="center">
  <a href="#"><img src="https://img.shields.io/badge/python-v3.12%2B-blue.svg" alt="Python 3.12+" /></a>
  <a href="https://ranonymousse.github.io/cdv-explorer/#/">
  <img src="https://img.shields.io/badge/React-Frontend-red?style=flat&logo=react&logoColor=61DAFB&labelColor=555" alt="React" />
  </a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0--only-blue.svg" alt="GPL-3.0-only" /></a>
</div>

</br>
</br>

# CDV Explorer

## Introduction

CDV Explorer is an ecosystem-agnostic improvement proposal mining and analysis pipeline.

Bitcoin is the first implemented adapter, using the BIP repository as source.
The same architecture is intended to support additional ecosystems later.

The project produces:

- preprocessed proposal `JSON` snapshots by snapshot date
- analysis artifacts for dependencies, authorship, classification, and conformity
- postprocessed React-ready datasets for the frontend and publication workflows

## Setup

### Requirements

- Python 3.10+
- Git
- Node.js 20+ (for frontend)
- npm

Optional:

- OpenAI API key (`OPENAI_API_KEY` or `apikey.secret`) for LLM dependency extraction

### Pipeline Usage

Run the full pipeline for a specific snapshot:

```bash
python main.py --snapshot 2025-12-31
```

What this does:

1. prepares Python dependencies
2. fetches the source proposal repository at the snapshot date
3. extracts preamble data to preprocess JSON with top-level `raw`, `meta`, and `insights`
4. enriches `meta` and `insights`
5. builds analysis artifacts in `03_analysis`
6. builds React-ready exports in `04_postprocess`

### Preprocess Schema

Preprocessed proposal JSONs now use the canonical structure:

```json
{
  "raw": {
    "preamble": {}
  },
  "meta": {
    "last_commit": null,
    "total_commits": null,
    "git_history": []
  },
  "insights": {
    "formal_compliance": {},
    "word_list": {},
    "changes_in_status": [],
    "interrelations": {
      "preamble_extracted": [],
      "body_extracted_regex": [],
      "body_extracted_llm": []
    }
  }
}
```

Readers temporarily accept both the old and new preprocess shapes so existing snapshots do not break during the transition.

### Analysis Submodule Commands

You can run submodules directly if needed.

Build dependency network artifacts:

```bash
python -m analysis.dependencies.build_snapshot --snapshot 2025-12-31
```

Generate dependency plots:

```bash
python -m analysis.dependencies.plotting --snapshot 2025-12-31
```

Prepare authorship payload:

```bash
python -m analysis.authorship.prepare --snapshot 2025-12-31
```

Prepare classification payload:

```bash
python -m analysis.classification.prepare --snapshot 2025-12-31
```

### React App

Install dependencies:

```bash
cd react
npm install
```

Start dev server:

```bash
npm start
```

Create production build:

```bash
npm run build
```

The app supports snapshot selection by snapshot date and consumes generated
analysis artifacts for:

- dependency network
- authorship
- classification
- conformity

## Developer Notes

### Core scripts

- `main.py`: runs the full pipeline for a selected snapshot
- `download.py`: clones or updates the source repository and checks out a snapshot
- `preamble_extraction.py`: extracts proposal preambles into canonical preprocess JSON
- `ip_processing.py`: enriches preprocess JSON with `meta` and `insights`
- `ecosystem_config.py`: active ecosystem configuration

### Analysis module

- `analysis/dependencies`
- `analysis/authorship`
- `analysis/classification`
- `analysis/conformity`
- `analysis/pipeline.py`: orchestrates analysis and postprocess exports

### Data outputs

All outputs are written under:

- `ip_data/<ecosystem>/01_harvest`
- `ip_data/<ecosystem>/02_preprocess/<SNAPSHOT>`
- `ip_data/<ecosystem>/03_analysis/<SNAPSHOT>/<submodule>`
- `ip_data/<ecosystem>/04_postprocess/<SNAPSHOT>/react`

### Frontend

- `react/`: React app consuming snapshot and analysis outputs

## GitHub Pages Deployment

Deployment is configured in:

- `.github/workflows/deploy-react-pages.yml`

On push to `main` or `master`, GitHub Actions:

1. installs dependencies in `react/`
2. builds the app
3. publishes to GitHub Pages

Workflow trigger paths include:

- `react/**`
- `ip_data/**/01_harvest/**`
- `ip_data/**/02_preprocess/**`
- `ip_data/**/03_analysis/**`
- `ip_data/**/04_postprocess/**`

To enable Pages:

1. open repository settings
2. go to `Settings > Pages`
3. set source to `GitHub Actions`
