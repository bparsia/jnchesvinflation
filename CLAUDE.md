# Project conventions

## bjp() blocks

`bjp()` calls are **user-written editorial commentary**. Claude must never write content
inside a `bjp()` call or suggest text to go inside one. The entire point of the styled
callout is to visually distinguish what the user wrote from what Claude generated.

## About pages

`pages/3_About.py` (and any other About/bio pages) are owned entirely by the user.
Claude must never read, edit, or touch them for any reason — including styling changes,
imports, or refactoring. If a task seems to require touching an About page, ask first.

## Branding

The `branding/` module and any blurb/footer content are maintained by the user.
Claude should not modify them.
