# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath('sphinxext'))
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('..'))
from github_link import make_linkcode_resolve

# -- Project information -----------------------------------------------------

project = 'PyPads'
copyright = '2020, Padre-Lab'
author = 'Padre-Lab, Thomas Weissgerber & Mehdi Ben Amor'

# The full version, including alpha/beta/rc tags
release = '0.1.20'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.autosummary', 'sphinx.ext.intersphinx', 'sphinx.ext.doctest',
              'sphinx.ext.napoleon', 'sphinx.ext.linkcode', 'sphinx-pydantic']

autodoc_default_options = {
    'members': None,
    'inherited-members': None
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# generate autosummary even if no references
autosummary_generate = True

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store','themes', 'templates']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_theme_path = ['themes']

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = 'pypads'

html_logo = 'files/imgpsh_fullsize_anim.png'

html_favicon = 'files/rtd.png'
# The following is used by sphinx.ext.linkcode to provide links to github
linkcode_resolve = make_linkcode_resolve('pypads',
                                         'https://github.com/padre-lab-eu/pypads/'
                                         'blob/{revision}/'
                                         '{package}/{path}#L{lineno}')


# Using the static custom css file
def setup(app):
    app.add_css_file('background.css')