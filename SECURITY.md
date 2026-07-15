# Security Policy

## Reporting a vulnerability

If you discover a security issue, please **do not open a public issue**. Instead, report it privately via GitHub's [private vulnerability reporting](https://github.com/mostafamohamedAyoussef/Open-Source-Creators/security/advisories/new), or contact the maintainer through their [GitHub profile](https://github.com/mostafamohamedAyoussef).

Please include:

- A description of the issue and its impact
- Steps to reproduce
- Any relevant logs or proof-of-concept

We will acknowledge your report as soon as possible and keep you updated on the fix.

## Scope

This project is a static directory site plus a Python data pipeline. Areas of interest include:

- The GitHub crawler and token handling in `scripts/collector.py` (tokens are supplied via environment variables and never committed)
- HTML output escaping in `scripts/site_generator.py` and `app.js`
- The GitHub Actions workflow and Vercel build

## Supported versions

The `main` branch is the only supported version; it is deployed continuously.
