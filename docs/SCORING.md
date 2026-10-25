# Scoring, Ranking, and Reliability Formulas

## 1. Reliability Score Model

The reliability score $R \in [0.0, 1.0]$ measures the confidence that a passenger will successfully complete the entire multi-leg journey without cancellation, missed connection, or stranding.

$$R = \prod_{i=1}^{L} \text{LegReliability}(leg_i) \times \prod_{j=1}^{L-1} \text{TransferSafety}(transfer_j)$$

### 1.1 Leg Reliability ($\text{LegReliability}$)
For each leg $i$ with status $S_i$ and waitlist position $W_i$:
- **Confirmed (`CNF`)**: $1.00$
- **Reservation Against Cancellation (`RAC`)**: $0.85$
- **Waitlisted (`WL`)**: $0.20 + 0.65 \times P_{\text{confirm}}(W_i, \text{class}, \text{days})$ (calculated via ML or heuristic)
- **Official Timetable (No status reported / Unreserved)**: $0.75$
- **Community Timetable (Bus/GTFS)**: $0.70$
- **Unknown Status**: $0.50$ (honest penalty for unverified availability)

### 1.2 Transfer Safety ($\text{TransferSafety}$)
For each connection between leg $j$ and $j+1$:
- **Buffer minutes** $B$:
  - $B < 30$ min: **Infeasible** (discarded in RAPTOR unless intra-platform cross-walk)
  - $30 \le B < 45$ min: $0.75$ (tight transfer penalty)
  - $45 \le B \le 120$ min: $1.00$ (optimal transfer window)
  - $120 < B \le 240$ min: $0.90$ (excessive layover fatigue)
  - $B > 240$ min: $0.70$
- **Late-Night Transfer Penalty**:
  - If a transfer occurs between 23:00 and 04:30 at an unstaffed or small bus stand: penalty factor $0.80$.
- **Station Change**:
  - If transfer requires cross-town transit (e.g., Kacheguda to Secunderabad): buffer required increases to $\ge 75$ min; penalty factor $0.85$.

---

## 2. Ranking Profiles

Itineraries are categorized into 4 distinct user tabs:

1. **Best Balance (Default)**:
   $$Score = w_{\text{cost}} \cdot (1 - \hat{C}) + w_{\text{time}} \cdot (1 - \hat{T}) + w_{\text{rel}} \cdot R - w_{\text{transfers}} \cdot \frac{N_{\text{transfers}}}{2}$$
   Default weights: $w_{\text{cost}} = 0.35$, $w_{\text{time}} = 0.35$, $w_{\text{rel}} = 0.20$, $w_{\text{transfers}} = 0.10$.
   ($\hat{C}$ and $\hat{T}$ are min-max normalized across returned Pareto candidates).

2. **Cheapest**:
   Sorted strictly by known fare ascending. Itineraries with unverified fares are ranked with an asterisk.

3. **Fastest**:
   Sorted strictly by total elapsed trip time (departure to final arrival).

4. **Most Reliable**:
   Sorted strictly by $R$ descending. Prioritizes confirmed legs, ample daytime buffers, and fewer changes.

---

## 3. Waitlist Confirmation Chance Categories
- **High**: $P_{\text{confirm}} \ge 0.75$
- **Medium**: $0.40 \le P_{\text{confirm}} < 0.75$
- **Low**: $P_{\text{confirm}} < 0.40$
Always labeled with the explicit tag **"estimate"** on the UI.
