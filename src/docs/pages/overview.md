# What is COLLIDE?

COLLIDE is an AI-powered platform for finding the best sites to build **behind-the-meter (BTM) natural gas data centers** in Texas and the Southwest — without waiting years for a grid interconnection.

## The problem

Hyperscale AI data centers need 50–500 MW of power running 24/7. Connecting to the grid used to be the obvious path, but interconnection queues now stretch **3 to 7 years**. The alternative is generating power on-site with natural gas. But picking a good site means evaluating three things at once:

- **Land viability** — zoning, fiber proximity, water access, lease structures
- **Gas supply reliability** — pipeline age, failure risk, curtailment history
- **Power economics** — is generating your own gas power cheaper than buying from the grid here?

Right now, developers evaluate these in silos over weeks. A site that passes the land check might fail on gas reliability. One that looks great on economics might have pipeline issues that only surface later.

## What COLLIDE does

COLLIDE scores every candidate site across all three dimensions **simultaneously**. Click any point on the map and within seconds you get:

- Land, gas, and power sub-scores (each 0–1)
- A TOPSIS-weighted composite score
- 20-year NPV estimate (P10 / P50 / P90)
- An AI-written narrative explaining the tradeoffs
- Web-enriched context from live zoning and infrastructure news

## Who it's for

- **Site selection teams** evaluating Texas and Southwest data center locations
- **Energy analysts** stress-testing BTM economics under different gas price scenarios
- **Infrastructure investors** comparing risk across a shortlist of parcels

## Quick start

1. Open the app — the live ticker at the bottom shows the current market regime
2. Click any point on the map, or right-click a predefined candidate site
3. The scorecard panel slides in from the right with the full breakdown
4. Open the AI Analyst (⚡ top-right) and ask: *"What if Waha gas spikes 40%?"*

## By the numbers

| | |
|---|---|
| Data sources | 10 public APIs |
| Scoring dimensions | 3 (land · gas · power) |
| AI agent intents | 5 (stress test · compare · timing · explain · configure) |
| LMP forecast horizon | 72 hours (P10 / P50 / P90) |
| Candidate markets | ERCOT · WECC (CAISO) |
| Background refresh | 5 min (regime), 30 min (news), 1 hr (forecast) |
