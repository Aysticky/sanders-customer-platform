#!/usr/bin/env python3
"""
Wrapper script to work around Python 3.13 module import issues with CDK.
Ensures constructs._jsii is properly importable.
"""
import os
import sys

# Add site-packages to path explicitly for Python 3.13 compatibility
venv_site_packages = os.path.join(os.path.dirname(__file__), '..', '.venv', 'Lib', 'site-packages')
if venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

# Import app as a module
