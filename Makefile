.PHONY: dev api web demo

dev:
	@trap 'kill 0' INT TERM EXIT; $(MAKE) api & $(MAKE) web & wait

api:
	cd backend && (test -d .venv || python3 -m venv .venv) && . .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload

web:
	cd frontend && npm install && npm run dev

demo:
	cd backend && (test -d .venv || python3 -m venv .venv) && . .venv/bin/activate && pip install -r requirements.txt && python -m app.analysis.demo
