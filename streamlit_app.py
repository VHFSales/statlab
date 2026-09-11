"""Streamlit Community Cloud entry point for StatLab.

Streamlit Cloud looks for a main file at the repository root by default. This thin
launcher makes the project importable and delegates to the real UI module in
app/ui/streamlit_app.py, so the app runs identically locally and in the cloud.

Local run (from the repo root):
    streamlit run streamlit_app.py
"""

import os
import sys

# Ensure the repository root is importable (so `app`, `statistics`, ... resolve).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ui.streamlit_app import main  # noqa: E402

# Streamlit runs this file as the top-level script (name == "__main__"); calling
# main() once here drives the whole app.
main()
