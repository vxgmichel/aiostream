import sphinx_rtd_theme

VERSION = open('../setup.py').read().split("version='")[1].split("'")[0]

project = 'aiostream'
version = VERSION
author = 'Vincent Michel'
copyright = u'2016, Vincent Michel'

master_doc = 'index'
highlight_language = 'python3'
extensions = ['sphinx.ext.autodoc']

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
html_context = {
    'display_github': True,
    'github_user': 'vxgmichel',
    'github_repo': 'aiostream',
    'github_version': "master",
    'conf_py_path': "/docs/",
    'source_suffix': '.rst'}

suppress_warnings = ['image.nonlocal_uri']
