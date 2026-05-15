"""Shared Streamlit styling helpers."""
import re
import streamlit as st

_DIV = ("font-family: Georgia, 'Times New Roman', serif; "
        'background-color: #fdf8f0; border-left: 4px solid #c9953a; '
        'padding: 1rem 1.25rem; margin: 1rem 0 1rem 0; '
        'border-radius: 0 6px 6px 0; color: #3d2e10; line-height: 1.75;')
_H1  = ('font-weight: bold; font-size: 1.4em; '
        'margin: 0.75em 0 0.5em 0; color: #6b4c10;')
_H2  = ('font-weight: bold; font-size: 1.2em; '
        'margin: 0.5em 0 0.4em 0; color: #6b4c10;')
_H3  = ('font-weight: bold; font-size: 1.05em; '
        'margin: 0.4em 0 0.3em 0; color: #6b4c10;')
_P   = 'margin: 0.5em 0;'
_LI  = 'margin: 0.25em 0;'
_UL  = 'margin: 0.5em 0 0.5em 1.5em; padding: 0;'
_OL  = 'margin: 0.5em 0 0.5em 1.5em; padding: 0;'
_A   = 'color: #8b6914;'


def inject_bjp_css() -> None:
    """No-op — styles are now fully inline. Kept for import compatibility."""


def _inline(t: str) -> str:
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\*(.+?)\*', r'<em>\1</em>', t)
    t = re.sub(r'\[(.+?)\]\((.+?)\)', rf'<a href="\2" style="{_A}">\1</a>', t)
    return t


def bjp(text: str) -> None:
    """Render user editorial text in a distinctive serif callout block.

    IMPORTANT: only the page author (bjp) should pass content to this function.
    Claude must never write or suggest text to go inside a bjp() call.
    """
    blocks = re.split(r'\n\s*\n', text.strip())
    parts = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Header
        if re.match(r'^#{1,3} ', block):
            def _hdr(m):
                level = len(m.group(1))
                style = {1: _H1, 2: _H2, 3: _H3}[level]
                tag = f'h{level + 1}'  # # -> h2, ## -> h3, ### -> h4
                return f'<{tag} style="{style}">{m.group(2)}</{tag}>'
            parts.append(re.sub(r'^(#{1,3}) (.+)$', _hdr, block, flags=re.MULTILINE))
            continue

        lines = [l for l in block.splitlines() if l.strip()]

        # Unordered list — lines starting with "* " or "- "
        _ul = re.compile(r'^[*-] (.+)$')
        if lines and all(_ul.match(l.strip()) for l in lines):
            items = ''.join(
                f'<li style="{_LI}">{_inline(_ul.match(l.strip()).group(1))}</li>'
                for l in lines
            )
            parts.append(f'<ul style="{_UL}">{items}</ul>')
            continue

        # Ordered list — lines starting with "1. " etc.
        _ol = re.compile(r'^\d+\. (.+)$')
        if lines and all(_ol.match(l.strip()) for l in lines):
            items = ''.join(
                f'<li style="{_LI}">{_inline(_ol.match(l.strip()).group(1))}</li>'
                for l in lines
            )
            parts.append(f'<ol style="{_OL}">{items}</ol>')
            continue

        # Paragraph
        parts.append(f'<p style="{_P}">{_inline(" ".join(l.strip() for l in lines))}</p>')

    st.html(f'<div style="{_DIV}">{"".join(parts)}</div>')
