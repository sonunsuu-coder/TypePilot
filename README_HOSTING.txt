TypePilot - Hosting Package
===========================

This app includes a SQLite lesson database and a small Python API server.
It must run on a Python web host; a static-only host (such as plain Netlify
Drop or GitHub Pages) cannot serve the lesson API by itself.

Run on Windows
--------------
1. Install Python 3.10 or newer.
2. Extract this ZIP.
3. Double-click run_local.bat, or run: python local_server.py
4. Open http://127.0.0.1:8765/ in a browser.

Deploy online
-------------
Use a Python web service host such as Render, Railway, or a Python VPS.
For a service configured from this package, use:
  Build command: pip install -r requirements.txt
  Start command: python local_server.py

The server listens on 0.0.0.0 and uses the PORT environment variable supplied
by the host. Keep tgurudb.db and Data/api-cache alongside the app files.
The app calls /api/ on its current host.

Notes
-----
- Lesson rows are read from tgurudb.db.
- Data/api-cache contains bundled offline responses for guest dashboard views.
- User accounts, synced performance, and cloud saves are not included.
