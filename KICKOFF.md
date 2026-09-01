# Kickoff prompt

How to use this. Make an empty folder, drop `ROADMAP.md` into it, open a coding agent such as Claude Code in that folder, and paste everything below the line. The working name is driftwatch. Rename it if you like, but keep the name consistent across the prompt, the roadmap and the repo.

---

You are helping me build driftwatch, an open-source tool that screens satellite conjunctions in low Earth orbit and shows how geomagnetic storms change collision risk. I am a comfortable software developer and new to orbital mechanics. I want to learn the physics as we build, so explain your choices briefly as you make them. We are starting Phase 1 of a five-phase roadmap in ROADMAP.md. Read it before doing anything else.

## What we are building in Phase 1

A Python package plus a small web viewer that does four things. It fetches the public satellite catalogue from CelesTrak, stores dated snapshots locally, propagates every object to a chosen time with SGP4, and renders the result on a 3D globe in the browser with a time slider and simple filters for Starlink, other constellations, debris and altitude bands.

## Constraints and conventions

- Python 3.11 or newer, managed with uv. Use the sgp4 library for propagation, skyfield or astropy for frame conversions, numpy and pandas for data, and parquet files for storage. No database in this phase.
- The web viewer is a static Vite project using globe.gl, which sits on three.js. It reads a JSON or binary file exported by the Python side. No backend server in this phase.
- Be polite to CelesTrak. Cache every download, fetch each group at most every two hours, set a descriptive User-Agent, and never loop over their API.
- Tests with pytest. Propagation must be checked against the official SGP4 verification cases that ship with the sgp4 library, and frame conversions against a skyfield reference for a handful of objects.
- Small commits with clear messages. A README that a stranger could follow. Type hints and docstrings on public functions.
- British spelling in docs and comments.
- Performance matters in the viewer. Around 30,000 points must move smoothly, so use typed arrays and instanced points rather than one mesh per object.

## Acceptance criteria for Phase 1

1. `uv run driftwatch fetch` downloads the active catalogue plus the Starlink and debris groups and writes a dated parquet snapshot under `data/snapshots/`.
2. `uv run driftwatch propagate --at 2026-09-01T12:00:00Z` produces positions and velocities for every object in the latest snapshot, in both the TEME frame and an Earth-fixed frame, and exports a compact file for the viewer.
3. The viewer opens locally, shows all objects on the globe, colours them by category, lets me scrub time across at least 24 hours, and shows an object's name, altitude and category on hover.
4. Tests pass, and a short docs page explains what a TLE is, what SGP4 does, and what the known accuracy limits of the public catalogue are.

## How to work

Before writing code, give me a short plan with the module layout, the data schema and any decisions you want me to make. Then build in the order fetch, store, propagate, export, viewer, and stop for review at each step. Ask me when a choice affects later phases, the storage schema for example, otherwise decide and move on. Keep the physics honest. If something is an approximation, say so in the code and in the docs.
