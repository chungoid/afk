import sys
import logging

from orchestrator.run_pipeline import main

def run():
    try:
        return main()
    except Exception as e:
        logging.exception("Unhandled exception in run_pipeline")
        return 1

if __name__ == "__main__":
    sys.exit(run())