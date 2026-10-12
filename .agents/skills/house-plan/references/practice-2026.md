# Current proven practice (2026) for this house

Researched 2026-10-13. **[proven]** well established; **[emerging]** limited
evidence; **[secondary]** Iranian rule seen only in news, blog or commercial
pages — confirm with the official text. Most of this lands in the final stage
and in the engineers' work; the layout must leave room for it from sketch one.

## 1. Site and structure (can rule the site out)

- **Fault first.** The Mosha fault's central segment near Damavand is the most
  active (Mw 5.1, May 2020). Fault setbacks exist for Tehran but widths are
  not published; commission a site-specific fault and geotechnical study.
  [proven practice]
- **Regular, compact plan, no soft storey**: no all-glass or pilotis ground
  floor under heavy floors, no deep re-entrant corners, stacked walls and
  columns. The cheapest seismic resilience there is. [proven]
- **System**: RC frame or RC walls by default; ICF with ≥ 15 cm RC core fits
  well (insulation built in, needs a BHRC certificate); light steel framing
  (LSF) suits 1–2 storeys but needs exterior continuous insulation against
  stud thermal bridges; 3D panels only with a valid BHRC certificate; AAC
  (هبلکس) for infill and partitions only, with seismic gaps and ties.
- **Anchor everything non-structural**: partitions, water heaters, tanks,
  outdoor units, PV racks, tall furniture — non-structural losses often exceed
  structural ones in Iranian earthquakes. [proven]
- Base isolation is not cost-effective for a house. [emerging]

## 2. Envelope and energy

- **Mabhas 19, 5th edition (1404)** is mandatory since 19 Dey 1404 (the 4th is
  allowed until 29 Esfand 1405; never mix). Classes A–D, D minimum; target
  ≥ 900 checklist points, class C or B; the class plate goes on sheet 1.
  U-value tables (appendix 7) must come from the official PDF. [secondary]
- **Window-to-wall ratio ≤ 50 %** (ministry circular cited for the
  checklist) [secondary] — encoded as `IR19-WWR`. Most glass south with sized
  overhangs (`slope.md` §5); small, externally shaded east and west glass.
- **Passive-house principles as the target, not the certificate**:
  continuous exterior insulation, thermal-bridge-free junctions (slab edges,
  balconies, studs), a continuous airtight layer drawn on every section, a
  blower-door test. [proven]
- **Heat-recovery ventilation (MVHR)**: ≥ 75 % recovery at ≤ 0.45 Wh/m³,
  enthalpy core and frost protection for cold dry air, ePM1 / F7–F9 supply
  filters for Tehran's air, and commissioning with balancing — most failures
  are unbalanced systems. [proven]
- **Both grids are unreliable** (summer gas shortages, a four-tier household
  gas tariff with a higher tier for non-permanent homes, an electricity
  deficit): envelope first, then a hybrid heat pump + condensing boiler, or a
  heat pump with PV and battery. [proven principle]
- **PV**: 1405 guaranteed purchase 58,540 rial/kWh, 91,169 with ≥ 1.5 kWh
  storage per kW not charged from the grid; capacity ≤ 2 × the connection;
  20-year contracts. [secondary] Plan roof area, structure, a battery space
  and a conduit chase.

## 3. Water (severe crisis)

- Tehran had night-time pressure cuts to zero in 2025; households are urged
  to keep tank reserves. **Potable storage for 2–3 days**, pump, seismically
  anchored tanks. [proven]
- Roof rainwater to a separate tank for irrigation and WC flushing; greywater
  dual piping roughed-in even if treatment comes later (Mabhas 16 governs).
  Aerators, ≤ 6 L/min showers, 3/6 L dual-flush WCs, drip irrigation,
  xeriscape planting. [proven]

## 4. Health

- **Radon**: Tehran mean 54 Bq/m³, max 661, about 5 % of sites over 148.
  Sub-slab membrane plus a passive riser that can take a fan; test after
  occupancy against the WHO 100 Bq/m³. [proven]
- Filtered ventilation (PM2.5 was 5.6× the WHO guideline in 2025);
  daylight in every main room; acoustic separation of bedrooms from plant and
  kitchen; anti-vibration mounts for outdoor units. [proven]

## 5. Planning

- **Broken-plan living**: a kitchen that can be closed (pocket doors) with a
  ducted hood — fits Iranian cooking (`family.md`). [emerging]
- **Universal design**: ground-floor bedroom and accessible bath, step-free
  entry, doors ≥ 90 cm, blocking for grab bars, space reserved for a lift or
  stair-lift, a quiet home office. [proven]
- Covered outdoor rooms, mudroom and storage; empty conduits for EV
  charging, data and smart controls. [proven]
- **Fire**: interconnected smoke alarms in bedrooms and halls, a CO alarm
  near every gas appliance, a second escape route from upper bedrooms.
  [proven; Mabhas 3 residential clause not confirmed]

## 6. Digital delivery

- IFC (4.3 is ISO since 2024; this kit writes IFC4, which Bonsai and Unreal
  read) with information requirements in IDS 1.0; clash detection of
  structure, ducts, pipes and the radon riser. Iran's permit is still PDF/DWG
  through the electronic single window. [proven / secondary]

## Spec fields to add when the design reaches them

Energy class and checklist score; envelope U-values and continuous
insulation; airtight layer; MVHR efficiency, fan power, filter class; heating
primary and backup on different sources; PV kWp and battery; potable, rain
and greywater provisions; fault distance and site class; structural system
and its certificate; radon membrane and riser; smoke and CO alarm positions;
lift reserve; EV and data conduits.
