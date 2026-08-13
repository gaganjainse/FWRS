"""Vercel serverless entrypoint for the FWRS web dashboard.

FWRS's web app (ui/web/app.py) is a stateless Flask app: it reads the committed
CSV datasets at request time and runs the LP solver in-memory — no database, no
writes, no filesystem state. This adapter exposes that WSGI app to Vercel's
Python runtime. Verified locally: GET / -> 200, POST / -> 200 with allocations.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)  # data/restaurants.csv + data/ngos.csv load relative to repo root

from ui.web.app import app  # noqa: E402  (WSGI object for @vercel/python)
