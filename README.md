# UnCRACKables
This repository is for the working of website, of an app, processing the data provided for turtles and their hatching variablities. This project will help conserving OLIVE RIDLEY TURTLES, starting from the hatching of the turtles, to them reaching the ocean safely. 
<div align="center">

# 🐢 TurtleWay (UnCRACKables)
### AI-Driven Precision Light Curfew & Coastal Conservation Engine for Olive Ridley Turtles

[![Expo SDK 58](https://img.shields.io/badge/Expo-SDK_58-black?style=for-the-badge&logo=expo)](https://expo.dev/)
[![React Native](https://img.shields.io/badge/React_Native-0.88-61DAFB?style=for-the-badge&logo=react)](https://reactnative.dev/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![Supabase](https://img.shields.io/badge/Supabase-Backend-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

<p align="center">
  Protecting Olive Ridley hatchlings from hatching to the ocean by dynamically predicting emergence windows and mitigating <b>Artificial Light at Night (ALAN)</b> and thermal stress.
</p>

[Key Features](#-key-features) •
[Architecture](#-system-architecture) •
[Installation & Setup](#-getting-started) •
[AI & Biophysical Engine](#-biophysical--actuarial-engine) •
[Tech Stack](#-tech-stack)

</div>

---

## 🌊 The Mission

Every year, millions of **Olive Ridley sea turtles** (*Lepidochelys olivacea*) arrive on nesting beaches (such as Rushikulya and Gahirmatha in Odisha) for mass nesting (*arribada*). However, hatchlings face critical threats:
1. **Phototaxis Disorientation (ALAN):** Artificial light from coastal resorts, street lamps, and highways lures hatchlings inland away from the moonlit ocean, causing fatal dehydration, exhaustion, or predation.
2. **Thermal Shock & Lethal Sand Temperatures:** Fluctuating nest temperatures can alter incubation periods, warp sex ratios, or result in lethal clutch mortality.

**TurtleWay** replaces static, disruptive, months-long blanket curfews with an **AI-driven precision curfew system**. By pairing real-time sand telemetry at nesting depth (54 cm) with NASA VIIRS satellite night-light imagery, TurtleWay calculates dynamic hatching windows and triggers targeted 72–96 hour coastal light curfews only when and where hatchlings emerge.

---

## 🚀 Key Features

- **Dynamic Hatch Date Prediction (Arrhenius & Machine Learning):** Evaluates daily cumulative sand thermal units at 54 cm clutch depth via Open-Meteo telemetry to dynamically recalculate incubation duration instead of relying on a static 50-day average.
- **Actuarial Risk Scoring & Alert Tiers:** Evaluates daily lux exposure, thermal stress deviation from pivotal temperature ($29.0^\circ\text{C}$), and emergence proximity to categorize threats into actionable Green, Yellow, and Red tiers.
- **NASA Black Marble & Near-Real-Time VIIRS Mapping:** Folium-based geospatial visualizer layering NASA GIBS Black Marble and daily VIIRS Day/Night Band scans with coastal borders to detect active lighting hotspots.
- **TurtleWay Mobile Field App:** Cross-platform Expo/React Native mobile application for beach rangers and volunteers to report nests, log GPS coordinates, and monitor active curfews offline and online.

---

## 🏗️ System Architecture

```text
  [Field Rangers / Volunteers]
               │
               ▼  (GPS, Lay Date, Nest ID)
    ┌─────────────────────┐
    │  TurtleWay Mobile   │ (Expo / React Native / Supabase)
    └──────────┬──────────┘
               │ Coordinates & Nest Data
               ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                   Turtle-Guard Telemetry Engine                 │
 ├────────────────────────────────┬────────────────────────────────┤
 │   Open-Meteo API Integration   │      NASA EOSDIS GIBS API      │
 │  • 54cm Nest Sand Temperature  │  • VIIRS Black Marble Tiles    │
 │  • Ambient coastal conditions  │  • Daily Day/Night Band Scan   │
 └────────────────┬───────────────┴────────────────┬───────────────┘
                  │                                │
                  ▼                                ▼
 ┌──────────────────────────────────┐   ┌──────────────────────────┐
 │   Stage 1: Thermal Kinetics      │   │ Folium Night Lights Map  │
 │   Arrhenius / RF Incubation Est. │   │ (`night_lights_map.html`)│
 └────────────────┬─────────────────┘   └──────────────────────────┘
                  │
                  ▼
 ┌──────────────────────────────────┐
 │  Stage 2: Actuarial Threat Model │
 │  Z-score Sigmoid Risk Equation   │
 └────────────────┬─────────────────┘
                  │
                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │               Traffic-Light Curfew Routing                      │
 │  🟢 GREEN : Safe underground (Nominal conditions)              │
 │  🟡 YELLOW: Standby advisory (Hatching in 72–96 hrs)            │
 │  🔴 RED   : Mandatory Light Curfew (Dim beachfront lights)      │
 └─────────────────────────────────────────────────────────────────┘
