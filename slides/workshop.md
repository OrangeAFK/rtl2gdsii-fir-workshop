# Workshop slides (~15)

Markdown outline — present as slides, whiteboard, or screen share.

---

## 1. Title

**From RTL to Silicon in 90 Minutes**  
Two chips. One fails. We find out why.

---

## 2. Destination

RTL → Synthesis → Floorplan → Place → CTS → Route → STA → Signoff (GDSII)

Today’s emotional arc: **confidence → shock → investigation → fix → relief**

---

## 3. The design

8-tap direct-form FIR  
Signed 8-bit data · coeffs `{2,4,8,16,16,8,4,2}`

Not a production DSP core — deliberately “wrong” structure so the critical path is legible.

---

## 4. Dataflow (Impl A)

`x_in` → shift register → × coeffs → **ripple sum** → `y_out`

Critical path ≈ 8 multiplies’ products feeding a long add chain.

---

## 5. Prediction Q1

We will constrain this at a clock that looks generous for 8-bit logic.

**Does anyone want to bet it stays fine all the way to GDS?**

---

## 6. Synthesis

Maps RTL → gates using the sky130 library.  
Produces area report + first timing estimate.

Wire delay is mostly **not real yet**.

---

## 7. Floorplan + placement

Core area · IO ring · standard-cell rows · utilization

Healthy target today: **45%** density.

---

## 8. Side experiment

Same netlist @ **85%** density.

Watch congestion / legalization.  
Then **reset to 45%** — this failure is not the main story.

---

## 9. Prediction Q2 / Q3

Utilization push: what do you expect?  
CTS: why ~40 cells you never wrote?

---

## 10. Routing

Legal wires + vias across the metal stack.  
A clean route does **not** mean the chip meets timing.

---

## 11. The reveal

Same `report_checks` command as after synthesis.  
Now with **SPEF** (extracted parasitics).

WNS / TNS go negative.

---

## 12. Root cause

Worst path = the same 8-term add chain — with real wire RC.

**Interview:** Why can post-route STA disagree with synthesis STA?

---

## 13. The fix (Impl B)

One pipeline register: two 4-term sums, then add.

Trade-off: **+1 cycle latency**, same steady-state throughput.

Other fixes (discuss): resize/buffer, restructure tree.

---

## 14. Signoff

DRC ≠ LVS ≠ STA  
A design can pass one and fail another.

Final GDS: this is what you made.

---

## 15. Concept map + interview lightning

Critical path · utilization · congestion · CTS / skew · SPEF · WNS/TNS · timing closure · DRC/LVS · GDSII

Repo: re-run at your pace · golden reports if your laptop stalls.
