VERSION = (
    open("../aiostream/__init__.py").read().split('__version__ = "')[1].split('"')[0]
)

project = "aiostream"
version = VERSION
author = "Vincent Michel"
copyright = "2016, Vincent Michel"

master_doc = "index"
highlight_language = "python"
extensions = ["sphinx.ext.autodoc"]

html_theme = "sphinx_rtd_theme"
html_context = {
    "display_github": True,
    "github_user": "vxgmichel",
    "github_repo": "aiostream",
    "github_version": "master",
    "conf_py_path": "/docs/",
    "source_suffix": ".rst",
}

suppress_warnings = ["image.nonlocal_uri"]
