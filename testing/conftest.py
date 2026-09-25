"""
conftest.py
===========
Pytest configuration for the `testing/` package.

Adds `registration/` to sys.path automatically so every test module can
import `registry.*` without needing to manipulate sys.path themselves.

Run all tests:
    cd ml_model_management
    python -m pytest testing/ -v

Run a single file:
    python -m pytest testing/test_views.py -v
"""

import sys
import os

REGISTRATION_DIR = os.path.join(os.path.dirname(__file__), "..", "registration")
_abs = os.path.abspath(REGISTRATION_DIR)
if _abs not in sys.path:
    sys.path.insert(0, _abs)
