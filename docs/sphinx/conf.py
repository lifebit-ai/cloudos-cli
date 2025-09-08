# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import os
import sys
# Ensure project root is on the path so `cloudos_cli` can be imported
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------

project = 'CloudOS CLI'
copyright = '2025, Lifebit AI'
author = 'Lifebit AI'

# The full version, including alpha/beta/rc tags
release = '1.0.0'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_click',
    'myst_parser',
    'sphinx.ext.autosectionlabel',
]

# Automatically generate summary pages from the autosummary directives
autosummary_generate = True

# Default autodoc options to include more content by default
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'inherited-members': True,
}

# Avoid importing heavy or unavailable dependencies during docs build
autodoc_mock_imports = [
    # Keep network/DS libs mocked to avoid heavy imports during docs
    'requests', 'urllib3', 'pandas', 'numpy', 'responses', 'mock',
]

# Render type hints in the description rather than the signature (cleaner)
autodoc_typehints = 'description'

# Support Markdown via MyST
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

myst_enable_extensions = [
    'colon_fence',
    'deflist',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# Use a modern, clean theme popular with developers
html_theme = 'furo'

# Basic theme options for a polished look
# No custom logos yet; defaults look good
html_theme_options = {}

# Title shown in the browser tab
html_title = 'CloudOS CLI Documentation'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
