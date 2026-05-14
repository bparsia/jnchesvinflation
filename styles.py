"""Shared Streamlit styling helpers."""
import re
import streamlit as st

_BJT_CSS_INJECTED = False

_BJP_CSS = """
<style>
.bjp-note {
    font-family: Georgia, 'Times New Roman', serif;
    font-style: italic;
    background-color: #fdf8f0;
    border-left: 4px solid #c9953a;
    padding: 1rem 1.25rem;
    margin: 1rem 0 1rem 0;
    border-radius: 0 6px 6px 0;
    color: #3d2e10;
    line-height: 1.75;
}
.bjp-note h3 {
    font-style: italic;
    font-weight: bold;
    font-size: 1.15em;
    margin: 0 0 0.5em 0;
    color: #6b4c10;
}
.bjp-note a { color: #8b6914; }
.bjp-note p { margin: 0.5em 0; }
</style>
"""


def inject_bjp_css() -> None:
    st.html(_BJP_CSS)


def bjp(text: str) -> None:
    """Render user editorial text in a distinctive italic serif callout block.

    IMPORTANT: only the page author (bjp) should pass content to this function.
    Claude must never write or suggest text to go inside a bjp() call.
    """
    t = text.strip()
    t = re.sub(r'^#{1,3} (.+)$', r'<h3>\1</h3>', t, flags=re.MULTILINE)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\*(.+?)\*', r'<em>\1</em>', t)
    t = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', t)
    paras = re.split(r'\n\s*\n', t)
    html = "".join(
        p.strip() if p.strip().startswith("<h") else f"<p>{p.strip()}</p>"
        for p in paras if p.strip()
    )
    st.markdown(f'<div class="bjp-note">{html}</div>', unsafe_allow_html=True)
