#!/bin/bash

# if ENVIRONMENT is development or dev or local 
if [ "$ENVIRONMENT" = "dev" ]; then
    # Use -Xfrozen_modules=off to prevent debugpy warnings about frozen modules
    python -Xfrozen_modules=off -m uvicorn src.main:app --host 0.0.0.0 --port ${AGENT_PORT} --reload
else
    NUM_WORKERS=${NUM_WORKERS:-1} # default to 1 worker if not present
    uvicorn src.main:app --workers ${NUM_WORKERS} --host 0.0.0.0 --port ${AGENT_PORT}
fi