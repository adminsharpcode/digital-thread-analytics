# Execution recording

`digital_thread_walkthrough.mp4` and `.gif` show one pass through the running
application:

1. The dashboard loads — deployment status, candidate comparison and per-feature
   drift, all read from the ledger at request time
2. A worn-tool reading is loaded (215 min tool wear, 64.5 Nm torque, quality L)
3. The model returns 83.36 % failure probability, with the derived features that
   explain it and the deployment version and model digest that produced it
4. "Trace this prediction back to raw data" walks the provenance chain
5. The view is flipped to impact analysis and back

To reproduce it live: `python run.py pipeline` then `python run.py serve`, and
open <http://127.0.0.1:8000>.
