.PHONY: install run offline test sql dashboard
install:   ; pip install -r requirements.txt
run:       ; python -m agrimarket.pipeline
offline:   ; python -m agrimarket.pipeline --skip-download
test:      ; python -m pytest -q
sql:       ; python sql/run_sql.py
dashboard: ; streamlit run dashboard/app.py
