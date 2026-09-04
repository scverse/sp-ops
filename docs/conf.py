"""Sphinx configuration for the sp-ops specification."""

from datetime import datetime

project = "sp-ops"
author = "scverse"
copyright = f"{datetime.now():%Y}, {author}"
release = "0.2.0-draft"
version = release

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinxcontrib.bibtex",
    "sphinxcontrib.mermaid",
    "sphinx.ext.intersphinx",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}

myst_heading_anchors = 4
myst_enable_extensions = [
    "attrs_inline",
    "colon_fence",
    "deflist",
    "fieldlist",
    "html_admonition",
    "substitution",
    "tasklist",
]
myst_url_schemes = ("http", "https", "mailto")
myst_fence_as_directive = ["mermaid"]

bibtex_bibfiles = ["references.bib"]
bibtex_reference_style = "author_year"
bibtex_default_style = "unsrt"

copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

intersphinx_mapping = {
    "spatialdata": ("https://spatialdata.scverse.org/en/stable/", None),
    "anndata": ("https://anndata.readthedocs.io/en/stable/", None),
    "geopandas": ("https://geopandas.org/en/stable/", None),
    "xarray": ("https://docs.xarray.dev/en/stable/", None),
}

html_theme = "sphinx_book_theme"
html_title = "sp-ops specification"
html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
html_theme_options = {
    "repository_url": "https://github.com/scverse/sp-ops",
    "use_repository_button": True,
    "use_edit_page_button": True,
    "use_issues_button": True,
    "path_to_docs": "docs",
    "repository_branch": "main",
    "navigation_with_keys": True,
    "show_toc_level": 3,
    "home_page_in_toc": True,
}
html_context = {
    "github_user": "scverse",
    "github_repo": "sp-ops",
    "github_version": "main",
    "doc_path": "docs",
}

pygments_style = "default"
nitpicky = False
