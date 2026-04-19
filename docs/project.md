AI-driven behind-the-meter data center site selection using natural gas power in Texas & the Southwest

MASTER PROBLEM STATEMENT
Hyperscale and AI-workload data centers require co-located power at scale — increasingly sourced from behind-the-meter (BTM) natural gas generation to bypass grid interconnection queues. But siting these facilities involves three interlocking constraints that are currently evaluated in silos: (1) land parcels with viable lease structures, zoning, and proximity to fiber and water; (2) natural gas distribution infrastructure with sufficient capacity and acceptable failure-probability profiles; and (3) wholesale electricity market economics that determine whether BTM gas generation is cost-competitive versus grid power at any given site and time.
Build an AI siting platform that jointly scores candidate sites across all three dimensions, surfacing a ranked set of locations with quantified risk and cost estimates for each constraint layer — and enabling a developer to understand the sensitivity of site rankings to changes in gas price, LMP spreads, and land cost. Teams may tackle all three sub-problems together as a full-stack siting engine, or select any single sub-problem as a standalone deliverable.
Sub-problem A  Land & lease viability scoring for BTM data center parcels
PROBLEM STATEMENT
Data center developers need large contiguous parcels (50–500+ acres) with appropriate zoning, proximity to dark fiber routes, cooling water access, and favorable lease or acquisition structures — but evaluating these factors across thousands of candidate parcels in Texas and the Southwest is manual and slow. Build an AI scoring model that ingests public land, zoning, infrastructure, and utility territory data to rank parcels by BTM data center suitability, flagging sites where lease complexity, environmental constraints, or infrastructure gaps would require significant de-risking investment.
PUBLIC DATA SOURCES
•      BLM General Land Office Records & Texas GLO Parcel Data — Public land ownership, parcel boundaries, acreage, and lease status for Texas and federal lands across AZ/NM. Downloadable via Texas GLO GIS portal and BLM's GeoBOB dataset.
•      HIFLD Critical Infrastructure — Fiber & Dark Fiber Routes — National telecommunications infrastructure geodatabase including long-haul fiber routes and colocation proximity, used for latency and connectivity scoring of candidate parcels.
•     EPA EnviroAtlas / USGS National Hydrography Dataset (NHD) — Water body proximity, watershed boundaries, and 100-year floodplain extents for cooling water availability assessment and environmental risk screening.
 
AI angle  Multi-criteria geospatial scoring model (weighted overlay or gradient boosting on parcel attributes). NLP pipeline to extract lease terms, encumbrances, and easement language from public deed records via county appraisal district APIs. Sensitivity analysis showing how parcel rank shifts under varying fiber proximity weights.
 
Sub-problem B  Natural gas supply reliability & pipeline risk scoring for BTM generation sites
PROBLEM STATEMENT
Behind-the-meter gas generation at data centers requires an uninterruptible gas supply — yet the Texas distribution network includes aging cast-iron and bare steel mains with elevated failure probability. Winter Storm Uri exposed how gas supply curtailments can cascade into power outages. Build an AI model that scores candidate BTM generator locations by gas supply reliability: combining pipeline segment failure probability, proximity to intrastate vs. interstate supply points, historical curtailment frequency, and system redundancy — producing a site-level 'gas reliability index' that informs infrastructure investment requirements and backup fuel sizing.
PUBLIC DATA SOURCES
•      PHMSA Gas Distribution Annual Report Data (Form PHMSA F 7100.1-1) — Operator-level mileage by material/vintage, leak causes, and incident counts. Downloadable CSV via PHMSA open data portal going back to 2004.
•     PHMSA Incident & Accident Database — Individual incident records with cause classification, pipe attributes, consequence severity, and GPS coordinates for all reportable gas distribution events nationally since 1970.
•     EIA Natural Gas Pipeline & Distribution Data (EIA-176 / EIA-757) — Annual system-level throughput, storage capacity, and curtailment event history by LDC (local distribution company), used to assess supply security at the utility territory level.
 
AI angle  Survival analysis on PHMSA incident records to produce segment-level failure probability. Graph-based supply security model encoding pipeline network topology to calculate redundancy scores and curtailment propagation risk. Output: gas reliability heatmap across Texas at the census tract level.
 
Sub-problem C  Wholesale power economics forecasting for BTM gas vs. grid power arbitrage on ERCOT & WECC
PROBLEM STATEMENT
A BTM gas generator is economically viable when the cost to generate (gas price + O&M + heat rate) is below the Localational Marginal Pricing (LMP) at the site's settlement point but this spread is volatile and highly locational. Build an AI model that forecasts the BTM generation spread (gas-to-power economics) at candidate data center sites across ERCOT and WECC 6–72 hours ahead, incorporating Henry Hub / Waha basis differentials, real-time LMP at nearby settlement points, and weather-driven demand events. The output should inform both site selection (which locations have the most durable positive spread) and real-time dispatch decisions (when to generate vs. import from the grid) for an operating data center.
PUBLIC DATA SOURCES
•      ERCOT Market Information System (MIS) API — Real-time and historical 15-minute LMP at all settlement points, DAM prices, fuel mix, and outage reports. Publicly accessible at mis.ercot.com.
•     CAISO / SPP / WAPA OASIS — WECC LMP Data — Publicly accessible hourly and 5-minute LMP across Western Interconnect nodes via each BA's OASIS portal, covering AZ, NM, and NV candidate markets.
•     EIA Natural Gas Spot Price Data (Henry Hub + Waha Basis) — Daily spot and forward gas prices at Waha Hub (West Texas) and Henry Hub via EIA's open data API — the primary fuel cost input for BTM generation economics in the Southwest.
 
AI angle  Temporal fusion transformer or multi-output LSTM jointly forecasting LMP and gas basis spread at candidate nodes. Regime detection model to classify market conditions (scarcity pricing, oversupply, high-wind curtailment) that shift the BTM economics threshold. Output: 72-hour spread forecast with confidence intervals per site.

INTEGRATION OPPORTUNITY:  FULL-STACK SITING ENGINE
→  Sub-problem A produces a ranked parcel shortlist with land cost and infrastructure gap estimates per site.
→  Sub-problem B overlays a gas reliability index on shortlisted parcels, filtering sites with unacceptable curtailment risk or those requiring costly pipeline reinforcement.
→  Sub-problem C models the long-run BTM spread at each surviving site, converting power economics into a net present value adjustment to land cost.
★  Combined output: a multi-dimensional site scorecard that lets a developer compare candidate parcels across land, gas, and power risk simultaneously — with a composite score and per-dimension drill-down.
 
Final Deliverables
Teams are expected to submit the following:
●	A GitHub repository containing the code, simulations, calculations, and documentation of the project
●	A 5-slide presentation summarizing the problem, approach, technical design, and key results
●	A 60–90 second short video or reel presenting the solution in a clear and engaging way

