# Project conventions

## bjp() blocks

`bjp()` calls in `pages/4_USS_Scenarios.py` are **user-written editorial commentary**.
Claude must never write content inside a `bjp()` call or suggest text to go inside one.
The entire point of the styled callout is to visually distinguish what the user wrote
from what Claude generated. Adding or editing `bjp()` content would defeat that purpose.
