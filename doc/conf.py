# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import datetime
import os
import sys
#sys.path.insert(0, os.path.abspath('..'))

import pywgrib2_xr as pywgrib2

# -- Project information -----------------------------------------------------

project = 'pywgrib2_xr'
copyright = '2019-{:d}, wgrib2 developers'.format(datetime.datetime.now().year)
author = 'George Trojan'

# The full version, including alpha/beta/rc tags
release = pywgrib2.__version__

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%Y-%m-%d'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
#    "nbsphinx",
#    "numpydoc",
    "IPython.sphinxext.ipython_directive",
    "IPython.sphinxext.ipython_console_highlighting",
    'sphinx.ext.viewcode',
    'matplotlib.sphinxext.plot_directive',
    'sphinxcontrib.programoutput',
#    "sphinx_gallery.gen_gallery",
]

autosummary_generate = True
autodoc_typehints = "none"

napoleon_use_param = True
napoleon_use_rtype = True

numpydoc_class_members_toctree = True
numpydoc_show_class_members = False

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
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_last_updated_fmt = today_fmt

# -- Options for nbsphinx output ---------------------------------------------
# https://nbsphinx.readthedocs.io/en/0.7.1/usage.html#extensions

#html_sourcelink_suffix = ''
#nbsphinx_execute_arguments = [
#    "--InlineBackend.figure_formats={'svg'}",
#    "--InlineBackend.rc={'figure.dpi': 96}",
#    ]
#nbsphinx_input_prompt = 'In [%s]:'

# Sometimes the savefig directory doesn't exist and needs to be created
# https://github.com/ipython/ipython/issues/8733
# becomes obsolete when we can pin ipython>=5.2; see doc/environment.yml
ipython_savefig_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_build", "html", "_static"
)
if not os.path.exists(ipython_savefig_dir):
    os.makedirs(ipython_savefig_dir)

ipython_warning_is_error: False

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/reference/", None),
    "xarray": ("https://xarray.pydata.org/en/stable/", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
    # "metpy": ("https://unidata.github.io/MetPy/latest/api/", None),
}

extlinks = {
    'doi': ('https://doi.org/%s', 'doi:'),
}
