# 🟡 The Backrooms: Isolation Protocol

A 3D first-person survival horror game built from scratch in Python using **Raylib (`pyray`)** and **CFFI**. Navigate an eerie, infinite-feeling maze, evade lethal entities, locate key items, and restore power to escape.

---

## 🎮 Game Overview

You are trapped in the non-Euclidean corridors of The Backrooms. Your objective is not just to survive, but to master your escape route, complete tasks under extreme pressure, and climb the competitive survival ranks.

### Core Mechanics
* **Two-Phase Objective:**
  1. Venture deep into the maze to find the glowing **Energy Fuse**.
  2. Locate the **Breaker Box** beside the exit gate and press `[E]` to restore power.
  3. Step into the green gate to escape.
* **Smart Monster Spawning:** Entities do not instantly spawn camp you. They materialize into the world only after you step into their territory, triggering on-screen directional threat alarms (`AHEAD`, `BEHIND`, `LEFT`, `RIGHT`).
* **Competitive ELO & Ranks:** Features a persistent ranked ladder that saves locally. Win runs to gain rating (+ELO) with bonuses for sub-minute clears and avoiding lockers. Deaths deduct rating (-ELO).
* **Smooth Physics & Collision:** Circle-to-AABB wall collision sliding prevents players and monsters from getting glued to corners or wedged into walls.
* **Survival Elements:** 
  * Sprinting with stamina depletion.
  * Crouching / sneak mode to silence footsteps and recover stamina faster.
  * Interactive lockers to break pursuit line-of-sight.
  * Real-time off-screen threat direction indicators.
  * Procedural footstep audio generated via mathematical wave buffers.

---

## 👾 The Entities

| Entity | Behavior | Danger Level |
| :--- | :--- | :--- |
| **Shadow Stalker** | A tall, dark entity that steadily glides toward you with disruptive screen glitches. | ⚠️ Moderate (Persistent) |
| **The Dasher** | A hunched, erratic stalker that alternates between slow roaming and terrifying bursts of high-speed rushes. | 🚨 Extremely High (Sudden Death) |

---

## 🏆 Competitive Rank Tiers

Your progress is automatically saved to `player_elo.txt` across play sessions.

| Tier | ELO Threshold | Badge Color |
| :---: | :---: | :---: |
| **BRONZE** | `0 – 399` | DARKBROWN |
| **SILVER** | `400 – 799` | Lightgray |
| **GOLD** | `800 – 1,199` | Gold |
| **DIAMOND** | `1,200 – 1,599` | Sky Blue |
| **MYTHIC** | `1,600 – 1,999` | Purple |
| **LEGENDARY** | `2,000 – 2,499` | Red |
| **MASTER** | `2,500+` | Yellow |

---

## ⌨️ Controls

| Key | Action |
| :---: | :--- |
| `W` `A` `S` `D` | Move character |
| `Mouse` | First-person look / aim |
| `Left Shift` | Sprint (consumes stamina) |
| `Left Ctrl` | Crouch / Sneak (quieter footsteps, faster stamina regen) |
| `E` | Interact (Enter/Exit lockers, flip breaker) |
| `Enter` | Start game from Main Menu |
| `Space` | Quick Rematch (after win or death) |
| `M` | Return to Main Menu (after match ends) |

---

## 🚀 Installation & Running

### Prerequisites
* Python 3.8+
* A working graphics environment supporting OpenGL

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/your-username/MyFirst3DGame.git](https://github.com/your-username/MyFirst3DGame.git)
   cd MyFirst3DGame# MyFirst3DGame