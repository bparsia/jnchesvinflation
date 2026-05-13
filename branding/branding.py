"""UCUCommons branding helpers for Streamlit apps."""

from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).parent / "assets"

SITE_URL = "https://ucucommons.org"

BLURB = """
---

### About UCU Commons

This tool is published by [UCU Commons](https://ucucommons.org), an independent platform
for UCU members providing data, analysis, and resources to support democratic participation
in the union.

*Built with [Streamlit](https://streamlit.io).*
"""


def apply_branding(*, page_title: str, page_icon: str | None = None) -> None:
    """Call before any other st.* calls (after set_page_config).

    Sets the sidebar logo linking to ucucommons.org.
    ``page_title`` is used only for documentation; set_page_config must be
    called by the caller so layout and other options remain flexible.
    """
    logo_path = str(_ASSETS / "ucuc-logo-large.png")
    icon_path = str(_ASSETS / "ucuc-6.png")

    st.logo(
        logo_path,
        link=SITE_URL,
        icon_image=icon_path,
        size="large",
    )
