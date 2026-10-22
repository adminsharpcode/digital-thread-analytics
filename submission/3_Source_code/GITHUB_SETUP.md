# Digital Thread Analytics — Online Repositories & Deployments

The source code, models, datasets, and live dashboard for this project are published and accessible online:

- **GitHub Repository:** [https://github.com/adminsharpcode/digital-thread-analytics](https://github.com/adminsharpcode/digital-thread-analytics)
- **Live Vercel Web Dashboard:** [https://digital-thread-analytics.vercel.app](https://digital-thread-analytics.vercel.app)

## Team Attribution
- **Vedant Nimkar** (`26MML0045`)
- **Durvesh Mahajan** (`26MML0055`)
- **Ayush Sharma** (`26MML0043`)
- **Shreyan Panda** (`26MML0022`)
- **Faculty Guide:** Dr. M. Rajasekhara Babu
- **Course:** Programming for Data Science (MACSE502)
- **School:** School of Computer Science and Engineering, VIT Vellore

## Repository Structure
```
digital-thread-analytics/
├── api/                  # Vercel Serverless entrypoint (FastAPI)
├── app/                  # Web dashboard UI & Lineage Explorer API
│   ├── main.py           # FastAPI application
│   └── static/           # HTML, CSS, JavaScript frontend
├── artifacts/            # Thread Ledger database, trained models & reports
│   ├── thread_ledger.db  # SQLite append-only graph ledger
│   ├── thread.html       # Self-contained interactive graph
│   └── models/           # Scikit-learn models (Random Forest, Logistic Regression)
├── baseline/             # Unthreaded comparison baseline
├── config/               # Unified lifecycle configuration (config.yaml)
├── pipeline/             # Stages 1 to 7 (Ingest, Clean, Features, Train, Eval, Serve, Monitor)
├── submission/           # All 5 submission dossiers (Manuscript, Diagrams, Code, Datasets, Videos)
├── thread/               # Lineage graph engine (ThreadLedger, Query, Context)
├── requirements.txt      # Production dependencies
├── run.py                # Command-line lifecycle runner
└── vercel.json           # Vercel deployment configuration
```
