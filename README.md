# Sagar–Pahar AI Travel Agent
backend/ = FastAPI + SQLAlchemy + LangGraph agent + RAG · frontend/ = Next.js (TypeScript)
1. (optional) `docker compose up -d` for PostgreSQL+pgvector, then set DATABASE_URL in backend/.env (SQLite is the default).
2. Backend: see backend/README.md  →  http://localhost:8000/docs
3. Frontend: `cd frontend && npm install && npm run dev`  →  http://localhost:3000
Prototype notes: seeded demo data, simulated payments, rules from news reports (re-verify officially). The LLM is optional: set ANTHROPIC_API_KEY to enable structured request parsing; all prices/rules/availability always come from deterministic code.
