import os
import sys

# Add your src/ directory so autodoc can import your package
sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "..", "..", "src")))


project = "saferoad"
copyright = "2025, SafeStruct"
author = "Mura Sahin"

version = "0.1"
release = "0.1"


extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
]

# Autodoc / autosummary defaults
autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}


html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
