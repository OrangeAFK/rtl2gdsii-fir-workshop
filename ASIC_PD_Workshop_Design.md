# From RTL to Silicon in 90 Minutes
### A Discovery-Based ASIC Physical Design Workshop for Interview-Ready Students

---

## 0. TL;DR

| Decision | Choice | One-line reason |
|---|---|---|
| Design | **8-tap direct-form FIR filter**, signed 8-bit data, fixed coefficients | Combinational depth is a knob you can turn; MACs create a controllable critical path; familiar to DSP/RF folks without being a full DSP course |
| Flow | Yosys → OpenROAD (orchestrated by **OpenLane 2**) → Magic + KLayout | Only actively-maintained fully open stack with per-stage checkpoints and a real STA engine (OpenSTA inside OpenROAD) |
| PDK | **SkyWater 130nm (sky130_fd_sc_hd)** | Small enough to route fast on a laptop; still "real" fab-characterized cells and parasitics, not toy numbers |
| Narrative spine | Two implementations of the same filter: **Impl A (naive ripple-chain MAC)** looks fine at synthesis, **fails after routing** because of extracted parasitics → **Impl B (one pipeline stage)** fixes it | Produces the single most common ASIC interview trap organically: "synthesis-stage timing lied to me" |
| Secondary failure | Same placed design at 85% vs 45% utilization | Gives congestion/legalization a visual without touching the main timing thread |
| Setup | Docker image with **PDK and tool binaries pre-baked**, `docker compose up`, zero network calls during the session | Removes the #1 killer of hands-on EDA workshops: install/download time |

---

## 1. The Design Choice — and Why It's Not a RISC-V or an AES

You asked me to actually justify this, not default to the FIR because it's the one you already like. Here's the comparison I ran the candidates through, scored against what the workshop actually needs: a *controllable, comprehensible critical path*, a *believable engineered failure*, and a *runtime budget that survives a laptop with a coffee-shop Wi-Fi connection*.

| Candidate | Combinational depth control | Runtime on a laptop (sky130) | Failure-engineering potential | Interview relevance | Verdict |
|---|---|---|---|---|---|
| Counter | None — depth is ~1 gate regardless of width | Seconds | None; can't fail timing without absurd constraints | Low — nobody asks about counters | Reject: too trivial to generate a story |
| UART / SPI | Shift-register + small FSM; depth barely moves with parameter changes | Seconds | Weak — mostly control logic, little datapath to stress | Medium | Reject: good for a "your first synthesis run" demo, bad for a 90-minute narrative |
| **FIR filter** | **Directly proportional to tap count and adder-tree shape** — you choose the story | 1–3 min full flow at 8 taps | **Excellent** — ripple-vs-tree-vs-pipeline is a clean, real trade-off | High — MAC chains, pipelining, and "why did timing get worse after routing" are staple ASIC/DSP interview questions | **Selected** |
| AES (even 1 round) | Deep and *wide* — SBox logic explodes cell count | 10+ min, congestion-prone, risks eating the whole session on routing alone | Failures are real but *muddy*: hard to tell whether a violation is instructional or a Docker-resources problem | Medium-high, but overkill for "entry-level" prep | Reject: right design for a 3-hour workshop, wrong one for 90 minutes |
| Tiny RISC-V (even 2-stage) | Control-dominated (decode, hazards) rather than a single clean combinational story | Large gate count relative to runtime budget; PnR risks not finishing live | Failures tend to be about *control correctness*, not physical design per se | Very high in general, but the *physical design* lessons get diluted by CPU architecture lessons competing for attention | Reject for this workshop: it's the better choice for a "build a CPU" course, not a PD-concepts course |
| ALU | Depth is fixed once you pick an operation set; no natural way to make it grow | Seconds | Weak unless you bolt on a multiplier, at which point it's just a smaller FIR | Medium | Reject: doesn't offer more than the FIR does with less realism |
| Matrix multiplier | Same MAC-chain idea as FIR, but 2-D — harder to reason about "the" critical path, more parameters to explain before you reach the point | Minutes, congestion-prone at any interesting size | Good, but requires explaining a systolic array *before* the physical design story starts — extra cognitive load for no extra payoff over FIR | Medium-high | Reject: FIR gives the same lesson with a 1-D structure students already understand from the RTL basics they're assumed to know |

**Bottom line:** the FIR filter wins not because it's a nostalgic DSP structure, but because it is the smallest design where *the number of pipeline stages is a direct, turnable knob on the critical path* — which is exactly the knob the engineered failure needs. Every other candidate either can't fail on cue (counter, UART/SPI, ALU) or fails in a way that's dominated by something other than physical design (AES's cell count, RISC-V's control logic, matmul's 2-D indexing overhead).

One caveat worth stating plainly, because an interviewer might probe it: a *real* commercial FIR would almost never be built this way (production DSP cores use systolic/transposed forms and DSP-slice-style hardened multipliers). We are deliberately using an academically "wrong" direct-form ripple structure because its physical-design behavior is *legible* — you can point at the netlist and say "there's the problem" in a way you can't with an optimized structure. Say this out loud in the workshop; it defuses the "wait, is this how real chips are built?" question before it derails the room.

---

## 2. Pedagogical Philosophy

Three commitments drive every choice below:

**1. Nothing is taught before it's needed.** If a term would require a slide with no artifact behind it, it doesn't appear until an artifact produces it. You will not see "today we'll learn about clock skew" anywhere in this document — skew shows up because someone opens the CTS report and asks why there are 40 buffers they didn't write in the RTL.

**2. The room runs on a single spine, not a checklist.** RTL→synthesis→floorplan→placement→CTS→routing→signoff is real and we follow it, but the *emotional* arc is: *confidence → shock → investigation → fix → relief*. That arc is what makes the timing-closure lesson stick, and it only works if it's the spine of the whole 90 minutes, not a five-minute detour in the middle.

**3. Every stage answers the same six questions**, extending your proposed five with one addition (#6) that keeps the room's eyes on the actual goal of the workshop:

1. What is this stage trying to optimize?
2. What inputs did it receive?
3. What outputs did it produce?
4. What went wrong (if anything)?
5. How would this appear in an interview?
6. **What would you check first, and in what file, if this happened to you on the job?**

Question 6 matters because "know the concept" and "know where to look" are different skills, and #6 is the one that actually separates a prepared candidate from a memorizer in a live interview.

**On cognitive load:** by minute 40 (CTS), students have already seen a netlist, an area report, a floorplan, and a placement — that's a lot of new vocabulary. The workshop deliberately does *not* introduce new report formats during the emotionally loaded post-route STA section (minutes 56–70); it reuses the exact same timing-report format they saw at minute 20, so the *only* new variable in that moment is the number, not the format. This is why the timeline below runs post-synthesis STA and post-route STA through the identical `report_checks` command — same tool, same columns, different (worse) result. The contrast is the lesson; new syntax would dilute it.

---

## 3. Minute-by-Minute Timeline

| Time | Duration | Segment | Student action | Facilitator move |
|---|---|---|---|---|
| 0:00–0:05 | 5 min | Kickoff | Watch | Show the RTL→GDSII diagram once, name the destination ("two chips, one fails, we find out why"), confirm everyone's container is already up (done before the session — see §11) |
| 0:05–0:12 | 7 min | RTL walkthrough | Read `fir_naive.v` | Walk the direct-form dataflow diagram; ask **Prediction Q1** (below) before running anything |
| 0:12–0:20 | 8 min | Stage 1 — Synthesis | Run `./run_stage.sh synth` | Open `synth_stat.rpt` and the post-synth `report_checks`; the room sees comfortable-looking slack — **do not editorialize yet** |
| 0:20–0:30 | 10 min | Stage 2 — Floorplan + Placement (healthy density) | Run `./run_stage.sh floorplan place` | Open the OpenROAD GUI placement view; name core area, IO ring, `DEF`/`LEF`; ask **Prediction Q2** |
| 0:30–0:38 | 8 min | Side experiment — utilization | Re-run `place` with `PL_TARGET_DENSITY=0.85` | Show congestion heatmap side-by-side with the 0.45 run; discuss legalization warnings; **reset to 0.45** before continuing |
| 0:38–0:48 | 10 min | Stage 3 — CTS | Run `./run_stage.sh cts` | Open the clock-tree view; let someone ask "why are there 40+ new cells we didn't write?" before explaining anything |
| 0:48–0:56 | 8 min | Stage 4 — Routing | Run `./run_stage.sh route` | Open Magic/KLayout; zoom into one via stack; name metal layers |
| 0:56–1:04 | 8 min | **The reveal** | Run `./run_stage.sh sta --spef` | Same `report_checks` command as minute 20 — now WNS/TNS are negative. Let the room react before explaining |
| 1:04–1:10 | 6 min | Root-cause | Read `report_checks -path_delay max` | Trace the critical path start-to-end; establish it's the same 8-term add chain every time, just with real wire delay now |
| 1:10–1:20 | 10 min | Fix — Implementation B | Read `fir_pipelined.v` diff, run the pre-cached full flow | Show the one-line RTL change (a register splitting the 8-term chain into two 4-term chains); discuss latency-vs-throughput cost of that register |
| 1:20–1:26 | 6 min | Sign-off | Run `./run_stage.sh signoff` | Open final GDS; explain DRC/LVS as *independent* of STA — a design can meet timing and still be unmanufacturable |
| 1:26–1:30 | 4 min | Wrap | — | Recap concept map (§8), rapid interview Q&A, point at repo for self-paced re-runs |

---

## 4. Implementation Stages — Deep Dive

### Stage 0: RTL (minutes 5–12)
- **Optimizes:** nothing yet — this is the "know what you're building" stage.
- **Inputs:** `fir_naive.v`, a testbench, fixed coefficients `{2,4,8,16,16,8,4,2}`.
- **Outputs:** a mental model students will keep checking against for the next 80 minutes.
- **What goes wrong:** nothing — deliberately. The only failure so far is a *prediction* failure: most students guess a 20 ns clock is "obviously fine" for an 8-bit design. Let that guess stand; it's the thing that gets punctured at minute 56.
- **Interview framing:** "Walk me through this RTL" is a real interview opener. Practicing narrating dataflow out loud (registers → multiply → chained add → output register) is itself the skill being drilled here.

### Stage 1: Synthesis (minutes 12–20)
- **Optimizes:** mapping RTL to a technology-specific gate netlist, roughly balancing area and the synthesis tool's *estimate* of timing.
- **Inputs:** Verilog, `constraints.sdc` (clock period, I/O delays), the sky130 `.lib` files.
- **Outputs:** gate-level netlist, `synth_stat.rpt` (cell count, area), a first-pass timing report.
- **What goes wrong:** nothing visible yet — and that's the point. Synthesis-stage STA uses either no wire delay or a crude wire-load estimate; it cannot see the real routing that hasn't happened. The slack looks fine because the tool is, correctly, telling you what it can currently see.
- **Interview framing:** "Why would a design pass timing at synthesis and fail after place-and-route?" is one of the single most-asked entry-level PD questions. This stage plants the setup for that question three timeline-sections early, which is exactly the delayed-payoff structure you asked for.

### Stage 2: Floorplan + Placement (minutes 20–30, plus the 30–38 side experiment)
- **Optimizes:** legal, congestion-aware positions for every standard cell inside a core area sized for the chosen utilization target.
- **Inputs:** netlist, `.lef` (cell shapes/pins), target utilization, aspect ratio, IO pin constraints.
- **Outputs:** `.def` with cell placements, a placement/legalization report, a congestion map.
- **What goes wrong:** at 45% utilization, nothing — clean placement, legalization report says everything moved less than a cell width from its target. At 85%, the legalizer has to shove cells further from their optimal (global) location to find legal (non-overlapping) sites, and the congestion heatmap lights up in the areas around the wide accumulator/adder logic.
- **Interview framing:** "What's utilization and why not just run every design at 95%?" — a direct, common question this side experiment answers with a picture instead of a definition.

### Stage 3: CTS (minutes 38–48)
- **Optimizes:** clock latency and skew across every sequential element, by inserting buffers into a balanced (or useful-skew) clock tree.
- **Inputs:** placed `.def`, clock definition from the SDC, buffer/inverter cells from the library.
- **Outputs:** clock tree topology, a CTS report (skew, max latency, buffer count), updated `.def`.
- **What goes wrong:** nothing is "wrong" here either — but something *appears* that nobody wrote: 30–50 new clock buffer cells. This is the moment your prompt specifically asked for: **let a student ask "why are there buffers in my clock net?" before answering.** The answer — insertion delay and skew across ~90 flip-flops (64 shift-register bits + ~20 accumulator/output bits) is large enough that a single unbuffered clock net would arrive at wildly different times at different flops — is the entire concept of clock tree synthesis delivered as an answer to a question the room asked itself.
- **Interview framing:** "What is useful skew and why would you ever want it?" is a step beyond the basic skew definition and worth raising here for stronger students, without requiring everyone to master it.

### Stage 4: Routing (minutes 48–56)
- **Optimizes:** legal, DRC-clean wire connections between placed cells across the available metal stack.
- **Inputs:** placed+CTS'd `.def`, routing layer rules from the tech LEF.
- **Outputs:** fully routed `.def`/`.odb`, a routing report, later a `.spef` (parasitics) once extraction runs.
- **What goes wrong:** visually, usually nothing dramatic at this size and utilization — which is important. **Routing "succeeding" is what makes the next section land**: students need to see a clean, DRC-legal, seemingly complete chip *before* the STA reveal shows them it doesn't actually work at speed. If routing itself failed here, the timing failure at minute 56 would read as "well of course, routing was already broken" instead of "wait, everything *worked* and it *still* doesn't meet timing."
- **Interview framing:** vias and metal-layer stacking rules are a common "do you actually know what's under the hood" screening question; a 60-second zoom into KLayout answers it better than any slide.

### Stage 5: Post-route STA — the reveal (minutes 56–64)
- **Optimizes:** nothing — this is a signoff *check*, not an optimization.
- **Inputs:** routed netlist, extracted `.spef` (real resistance/capacitance from the actual wires just drawn), the same SDC as before.
- **Outputs:** `report_checks` — same command, same columns as minute 20, now showing negative WNS/TNS.
- **What goes wrong:** the intended failure. Real wire RC on the long ripple-carry chain — spread across the die by placement — adds enough delay that the marginal-but-positive slack from minute 20 becomes clearly negative.
- **Interview framing:** this *is* the question "explain the difference between synthesis-stage and post-route STA, and why you'd trust one over the other." Students who lived through the reveal will never forget the answer.

### Stage 6: Root-cause (minutes 64–70)
- **Optimizes:** understanding, not the chip.
- **Inputs:** the failing `report_checks -path_delay max` output.
- **Outputs:** a traced start-to-end path through all 8 MAC terms.
- **What goes wrong:** nothing new — this stage is about *reading* the failure from Stage 5, not producing a new one. This is deliberately a "quiet" stage after a "loud" one, matching the pacing principle that a shock moment needs a calm investigation moment right after it, not another surprise.
- **Interview framing:** "How do you debug a setup violation?" — the answer *is* this stage: open the timing report, find the worst path, trace it register-to-register, identify whether the fix is a cell resize, a buffer, a restructure, or a pipeline stage.

### Stage 7: The fix — Implementation B (minutes 70–80)
- **Optimizes:** the same objective (correct FIR output) with a restructured critical path.
- **Inputs:** `fir_pipelined.v` — one register added, splitting the 8-term ripple chain into two 4-term chains added together one cycle later.
- **Outputs:** a re-run flow (pre-cached so it completes in the room — see the Facilitator Calibration Checklist) showing positive slack even post-route.
- **What goes wrong:** nothing — this is the payoff stage. The discussion here is explicitly about *trade-offs*, not just "we fixed it": one cycle of added latency, same steady-state throughput (one sample per cycle once the pipeline is full).
- **Interview framing:** "Name three ways to fix a setup violation, and what each one costs you" — cell upsizing/buffering (area/power cost, no latency cost, limited effectiveness against structural depth), logic restructuring like a balanced adder tree (no latency cost, only helps if the logic is genuinely restructurable), and pipelining (guaranteed depth reduction, at a real latency cost). This workshop demonstrates the third and *discusses* the first two — see §15 for turning the first two into take-home exercises.

### Stage 8: Sign-off (minutes 80–86)
- **Optimizes:** manufacturability, independent of timing.
- **Inputs:** final routed design.
- **Outputs:** DRC report, LVS report, final GDSII.
- **What goes wrong:** nothing, by design — the point of this stage is precisely that DRC/LVS are *orthogonal* to STA. A design can be timing-clean and still fail here (bad density fill, antenna violations, a netlist/layout mismatch from a hand-edit) and vice versa.
- **Interview framing:** "What's the difference between DRC and LVS, and why do you need both if STA already passed?" — a question that trips up candidates who've only ever heard the terms in a list.

---

## 5. Engineered Failures — Full Specification

### Failure 1 (secondary, contained): Congestion from over-aggressive utilization
- **Setup:** identical placed netlist, `PL_TARGET_DENSITY` swept from 0.45 to 0.85.
- **What's observed:** OpenROAD's congestion heatmap shows hot regions around the adder/accumulator logic; the legalization report shows larger average cell displacement from the global placer's preferred locations.
- **Why it's realistic, not artificial:** this is exactly how real utilization/timing/power trade-off discussions start in industry — nobody sets utilization to 85% by accident, they push it there deliberately to save die area and then have to fight the congestion it causes. We are compressing a real trade-off conversation into an 8-minute side-by-side.
- **Resolution:** explicit — reset to 0.45 and move on. This failure is intentionally *not* carried through to routing; its job is to deliver one concept cleanly (congestion/legalization/utilization trade-off) without competing with the main timing narrative for the room's attention.

### Failure 2 (primary, the workshop's spine): Marginal timing that flips negative after routing
- **Setup:** Implementation A (naive ripple-chain 8-tap FIR) constrained at a clock period deliberately chosen so that **synthesis-stage STA shows small positive slack** (a comfortable-looking pass) while **post-route STA, using extracted SPEF parasitics, shows negative slack** on the same path.
- **Why marginal, not obviously broken:** an obviously-too-fast clock (say, one that already fails at synthesis) teaches nothing beyond "don't pick silly constraints." A *marginal* constraint teaches the actually dangerous lesson: **synthesis-stage timing is optimistic, and trusting it alone is a real failure mode professionals fall into.** The exact period must be tuned per tool/PDK version — see the Facilitator Calibration Checklist — but the target is "passes at minute 20 by a small, credible margin; fails at minute 56 by a clear, unambiguous margin."
- **Why it's realistic, not artificial:** every practicing PD engineer has a version of this story. Wire parasitics genuinely aren't known until real placement and routing exist; pre-route timing genuinely is an estimate. This isn't a rigged demo of a made-up phenomenon — it's the most common real gap between synthesis signoff and place-and-route signoff, just captured on a small enough design that it happens inside a workshop.
- **Resolution:** Implementation B, a one-register pipeline split, discussed above.

---

## 6. Reports and Artifacts — What to Open, and Why

| Artifact | Opened at | Key numbers to read | Numbers to explicitly ignore |
|---|---|---|---|
| `synth_stat.rpt` | Minute ~16 | Total cell count, area estimate | Exact cell-type breakdown (too much detail this early) |
| Post-synth `report_checks` | Minute ~18 | WNS, TNS, worst path endpoints | Absolute path delay in isolation — the *comparison* to the post-route number is what matters, not this number alone |
| `.def` (placement) | Minute ~24 | Core area, row structure, IO pin locations | Individual cell coordinates |
| Congestion heatmap | Minute ~34 | Hot vs. cool regions, correlation with wide accumulator logic | Exact GRC (global routing cell) overflow counts — qualitative reading is enough here |
| Legalization report | Minute ~36 | Average/maximum cell displacement | Per-cell displacement list |
| CTS report | Minute ~44 | Buffer count, max skew, max insertion delay | Which specific buffer cell type was chosen (library-specific detail, not conceptually load-bearing) |
| Routing report | Minute ~52 | DRC-clean confirmation, layer utilization | Exact track/via counts |
| `.spef` | Minute ~58 (referenced, not read directly) | Existence and size relative to the ideal-case estimate | Never read raw SPEF text live — it's not human-paced content; treat it as "the file that makes the next report honest" |
| Post-route `report_checks` | Minute ~58 | Same WNS/TNS/endpoints as the synth-stage version, now negative | — this is the one report students should be told explicitly to screenshot for their own notes |
| `report_checks -path_delay max` | Minute ~66 | Full path: startpoint, endpoint, each stage's incremental delay | Fanout/cap numbers per cell (real, but a distraction from the "it's the same 8-term chain every time" point) |
| DRC report | Minute ~82 | Violation count (should be zero) | — |
| LVS report | Minute ~83 | Match/mismatch status | — |
| Final GDSII | Minute ~84 | Visual sanity check in KLayout: does it look like a chip | Layer-by-layer geometry detail (that's a follow-on-workshop topic) |

---

## 7. Visualizations / GUI Views

| View | Tool | Shown at | What it's for |
|---|---|---|---|
| RTL dataflow diagram (static image) | Slide/whiteboard | Minute 8 | Give students a mental map to check every later stage against |
| Placement view | OpenROAD GUI | Minute 24 | Physical intuition for "core area," cell rows, IO ring |
| Congestion heatmap (0.45 vs 0.85 side-by-side) | OpenROAD GUI | Minute 34 | Visual, not numeric, understanding of congestion |
| Clock tree view | OpenROAD GUI | Minute 42 | See the buffer tree that "appeared" |
| Routed layout, via zoom | KLayout | Minute 52 | Ground the abstract "vias/metal layers" vocabulary in an actual picture |
| Critical path highlight | OpenROAD GUI (`report_checks` path highlighting) | Minute 66 | Watch the worst path light up across the whole chip, physically, not just as a table row |
| Final GDS | KLayout | Minute 84 | Closure — "this is what you actually made" |

---

## 8. Interview Concept Map

| Concept | Where it arises | One-line interview-ready framing |
|---|---|---|
| Synthesis reports / area | Stage 1 | "Cell count and estimated area from mapping RTL to a target library" |
| Critical path | Stage 1 / Stage 6 | "The longest register-to-register delay path, which sets the maximum clock frequency" |
| Floorplanning / utilization | Stage 2 | "The fraction of core area occupied by standard cells; trades die size against routability" |
| Congestion | Side experiment | "Local routing demand exceeding local routing supply, usually from pushing utilization too high" |
| Placement optimization / legalization | Stage 2 | "Moving cells to legal, non-overlapping row-aligned sites while minimizing wirelength/timing cost" |
| Fanout | CTS / general | "Number of loads a single driver must charge; drives buffer insertion and delay" |
| Buffer insertion | Stage 3 | "Adding repeaters to manage long wires, high fanout, or clock distribution" |
| Clock tree synthesis (CTS) | Stage 3 | "Building a distribution network that delivers the clock to every sequential element with controlled latency and skew" |
| Clock latency / skew | Stage 3 | "Latency = time from clock source to a flop; skew = the *difference* in latency between two flops" |
| Routing / vias / metal layers | Stage 4 | "Physical wires connecting placed cells, implemented across a stack of metal layers joined by vias" |
| Parasitics / extracted RC / SPEF | Stage 5 | "Real resistance and capacitance of the routed wires, extracted after routing, used for the most trustworthy timing signoff" |
| Setup / hold / slack | Stage 5 | "Setup: data must arrive before the clock edge minus setup time. Hold: data must not change too soon after the edge. Slack: margin (positive = met, negative = violated)" |
| WNS / TNS | Stage 5 | "Worst Negative Slack: single worst violation. Total Negative Slack: sum of all violations — severity vs. breadth" |
| Timing closure | Stage 5–7 | "The iterative process of resolving timing violations via resizing, buffering, restructuring, or pipelining" |
| DRC | Stage 8 | "Design Rule Check: does the layout obey the foundry's manufacturable geometry rules" |
| LVS | Stage 8 | "Layout Versus Schematic: does the extracted layout netlist actually match the intended netlist" |
| GDSII | Stage 8 | "The final layout geometry format sent to the foundry" |

---

## 9. Commands Participants Execute

```bash
# Minute 0 — sanity check (should already be running from pre-session setup)
docker compose ps

# Minute 12 — Stage 1: Synthesis
./run_stage.sh synth
cat reports/synth/synth_stat.rpt
cat reports/synth/report_checks.rpt

# Minute 20 — Stage 2: Floorplan + Placement (healthy density)
./run_stage.sh floorplan
./run_stage.sh place
openroad_gui reports/place/design.odb   # opens the placement view

# Minute 30 — side experiment: utilization sweep
PL_TARGET_DENSITY=0.85 ./run_stage.sh place --tag high_density
openroad_gui reports/place/high_density/design.odb   # compare congestion
./run_stage.sh place   # reset back to 0.45 for the rest of the flow

# Minute 38 — Stage 3: CTS
./run_stage.sh cts
cat reports/cts/cts_report.rpt
openroad_gui reports/cts/design.odb

# Minute 48 — Stage 4: Routing
./run_stage.sh route
klayout reports/route/design.gds

# Minute 56 — Stage 5: post-route STA (the reveal)
./run_stage.sh sta --spef
cat reports/sta/report_checks.rpt      # compare directly against minute-12's file

# Minute 64 — Stage 6: root-cause
./run_stage.sh sta --spef --path-report
cat reports/sta/worst_path.rpt

# Minute 70 — Stage 7: Implementation B
diff design/fir_naive.v design/fir_pipelined.v
./run_stage.sh all --design fir_pipelined   # pre-cached; see Facilitator Checklist
cat reports/fir_pipelined/sta/report_checks.rpt

# Minute 80 — Stage 8: sign-off
./run_stage.sh signoff --design fir_pipelined
cat reports/fir_pipelined/signoff/drc.rpt
cat reports/fir_pipelined/signoff/lvs.rpt
klayout reports/fir_pipelined/signoff/design.gds
```

---

## 10. Repository Structure

```
asic-pd-workshop/
├── README.md                     # 5-minute quickstart, one command to launch
├── docker-compose.yml
├── Dockerfile                    # builds the (rarely-rebuilt) pinned image
├── run_stage.sh                  # single entrypoint for every stage
├── design/
│   ├── fir_naive.v                # Implementation A
│   ├── fir_pipelined.v            # Implementation B
│   ├── constraints_a.sdc
│   ├── constraints_b.sdc
│   └── tb_fir.v                   # simple self-checking testbench
├── config/
│   ├── config_naive.json          # OpenLane config: naive design, 0.45 density
│   ├── config_naive_highdensity.json  # 0.85 density variant for the side experiment
│   └── config_pipelined.json
├── scripts/
│   ├── stages/                    # one script per stage, called by run_stage.sh
│   └── compare_reports.py         # diffs the synth-stage vs post-route report_checks side by side
├── reports/                       # generated at runtime, gitignored except a checked-in "golden" copy
│   └── golden/                    # pre-run reference outputs, in case a laptop underperforms live
├── slides/
│   └── workshop.md                # the ~15 slides that *do* exist (diagram, recap, Q&A prompts)
├── docs/
│   ├── facilitator_guide.md       # the calibration checklist from this document, expanded
│   └── student_prep.md            # what to read/know beforehand (Verilog + digital logic basics)
└── LICENSE
```

---

## 11. Docker / Toolchain Architecture

The single biggest risk to a 90-minute EDA workshop is time lost to environment setup — package downloads, PDK builds, version mismatches. The architecture here is built to make that risk structurally impossible during the session:

- **One pre-built, pinned image**, published to a registry (e.g. GHCR) ahead of time, containing: Yosys, OpenROAD, OpenSTA (bundled inside OpenROAD), Magic, KLayout, and OpenLane 2, plus the **sky130 PDK already installed via `open_pdks`** — not downloaded at container start.
- **`docker compose up`** starts a single service exposing a VNC or noVNC port for the OpenROAD/KLayout GUIs, so students only need a browser tab, not a local X server.
- **No network calls during the session.** Anything the flow would normally fetch (PDK, cell libraries) is baked into the image layer. This also means the workshop runs identically on conference Wi-Fi as it does at home.
- **Version pinning everywhere** — Yosys commit hash, OpenROAD release tag, OpenLane 2 version, PDK version — recorded in the Dockerfile and in `README.md`, so "it worked differently on my laptop" is never a valid excuse mid-session, and so the exact timing numbers from the Facilitator Calibration Checklist stay reproducible.
- **A `golden/` reports directory checked into the repo**, generated once by the facilitator ahead of time, so that if any single laptop is too slow to finish a stage live, the room can look at the golden output and keep moving rather than stall.

```yaml
# docker-compose.yml (illustrative)
services:
  pd-workshop:
    image: ghcr.io/your-org/asic-pd-workshop:2026.1
    ports:
      - "6080:6080"   # noVNC for OpenROAD/KLayout GUIs
    volumes:
      - ./design:/workshop/design
      - ./config:/workshop/config
      - ./reports:/workshop/reports
    working_dir: /workshop
```

---

## 12. Suggested Scripts

```bash
#!/usr/bin/env bash
# run_stage.sh — single entrypoint, thin wrapper over OpenLane 2's per-step Python API
set -euo pipefail

STAGE="$1"; shift || true
DESIGN="${DESIGN:-fir_naive}"

case "$STAGE" in
  synth)    python3 scripts/stages/run_step.py --design "$DESIGN" --to Yosys.Synthesis ;;
  floorplan) python3 scripts/stages/run_step.py --design "$DESIGN" --to OpenROAD.Floorplan ;;
  place)    python3 scripts/stages/run_step.py --design "$DESIGN" --to OpenROAD.GlobalPlacement "$@" ;;
  cts)      python3 scripts/stages/run_step.py --design "$DESIGN" --to OpenROAD.CTS ;;
  route)    python3 scripts/stages/run_step.py --design "$DESIGN" --to OpenROAD.DetailedRouting ;;
  sta)      python3 scripts/stages/run_sta.py  --design "$DESIGN" "$@" ;;
  signoff)  python3 scripts/stages/run_step.py --design "$DESIGN" --to Magic.StreamOut --with-drc-lvs ;;
  all)      python3 scripts/stages/run_step.py --design "$DESIGN" --to Magic.StreamOut --with-drc-lvs ;;
  *) echo "unknown stage: $STAGE" ; exit 1 ;;
esac
```

```dockerfile
# Dockerfile (illustrative skeleton — real one pins exact commits/tags)
FROM ubuntu:24.04 AS pdk-builder
RUN apt-get update && apt-get install -y git python3 python3-pip make
RUN git clone --depth 1 https://github.com/RTimothyEdwards/open_pdks /open_pdks \
    && cd /open_pdks && ./configure --enable-sky130-pdk && make && make install

FROM ubuntu:24.04
COPY --from=pdk-builder /usr/local/share/pdk /usr/local/share/pdk
RUN apt-get update && apt-get install -y yosys magic klayout python3-pip
RUN pip install openlane==<pinned-version>
COPY . /workshop
WORKDIR /workshop
```

---

## 13. Suggested RTL Parameters

**Implementation A — `fir_naive.v` (the one that fails):**

```verilog
module fir_naive #(
    parameter N_TAPS  = 8,
    parameter DATA_W  = 8,
    parameter COEF_W  = 8
)(
    input  wire                                   clk,
    input  wire                                   rst_n,
    input  wire                                   sample_valid,
    input  wire signed [DATA_W-1:0]               x_in,
    output reg  signed [DATA_W+COEF_W+3:0]        y_out,
    output reg                                    y_valid
);
    localparam signed [COEF_W-1:0] COEF [0:N_TAPS-1] =
        '{8'd2, 8'd4, 8'd8, 8'd16, 8'd16, 8'd8, 8'd4, 8'd2};

    reg signed [DATA_W-1:0] shift_reg [0:N_TAPS-1];
    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < N_TAPS; i = i + 1) shift_reg[i] <= 0;
        end else if (sample_valid) begin
            shift_reg[0] <= x_in;
            for (i = 1; i < N_TAPS; i = i + 1) shift_reg[i] <= shift_reg[i-1];
        end
    end

    // Naive ripple-chain sum — the entire point of Implementation A.
    // Critical path grows linearly with N_TAPS: 7 sequential adds after 8 multiplies.
    wire signed [DATA_W+COEF_W+3:0] products [0:N_TAPS-1];
    genvar g;
    generate
        for (g = 0; g < N_TAPS; g = g + 1) begin : MUL
            assign products[g] = shift_reg[g] * COEF[g];
        end
    endgenerate

    wire signed [DATA_W+COEF_W+3:0] chain_sum =
        products[0] + products[1] + products[2] + products[3] +
        products[4] + products[5] + products[6] + products[7];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y_out   <= 0;
            y_valid <= 1'b0;
        end else begin
            y_out   <= chain_sum;
            y_valid <= sample_valid;
        end
    end
endmodule
```

**Implementation B — `fir_pipelined.v` (the fix — one added register):**

```verilog
// Identical to fir_naive.v except the final always block below,
// which registers two 4-term partial sums before adding them.
// This is the single change students need to see and understand.

reg signed [DATA_W+COEF_W+2:0] sum_lo_reg, sum_hi_reg;
reg pipe_valid;

wire signed [DATA_W+COEF_W+2:0] sum_lo =
    products[0] + products[1] + products[2] + products[3];
wire signed [DATA_W+COEF_W+2:0] sum_hi =
    products[4] + products[5] + products[6] + products[7];

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        sum_lo_reg <= 0; sum_hi_reg <= 0; pipe_valid <= 1'b0;
    end else begin
        sum_lo_reg <= sum_lo;
        sum_hi_reg <= sum_hi;
        pipe_valid <= sample_valid;
    end
end

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        y_out <= 0; y_valid <= 1'b0;
    end else begin
        y_out   <= sum_lo_reg + sum_hi_reg;
        y_valid <= pipe_valid;
    end
end
```

---

## 14. Suggested Constraints

```sdc
# constraints_a.sdc — Implementation A
# The exact period below MUST be calibrated per tool/PDK version — see §21 (Facilitator Checklist).
# Target behavior: small positive slack at synth-stage STA, negative slack post-route.
create_clock -name clk -period <CALIBRATE_ME_ns> [get_ports clk]
set_input_delay  -clock clk 1.0 [get_ports x_in]
set_input_delay  -clock clk 0.5 [get_ports sample_valid]
set_output_delay -clock clk 1.0 [get_ports y_out]
set_output_delay -clock clk 0.5 [get_ports y_valid]
```

```sdc
# constraints_b.sdc — Implementation B
# Same clock period as constraints_a.sdc — the point is that the SAME constraint
# now passes, because the RTL changed, not the clock.
create_clock -name clk -period <SAME_VALUE_AS_A_ns> [get_ports clk]
set_input_delay  -clock clk 1.0 [get_ports x_in]
set_input_delay  -clock clk 0.5 [get_ports sample_valid]
set_output_delay -clock clk 1.0 [get_ports y_out]
set_output_delay -clock clk 0.5 [get_ports y_valid]
```

**Utilization variants** (config JSON, not SDC): `PL_TARGET_DENSITY = 0.45` (healthy) vs `0.85` (congested), everything else identical between the two runs used in the side experiment.

---

## 15. Suggested Exercises (Take-Home / Extension)

1. **The balanced-tree alternative:** rewrite the 8-term chain as a balanced binary adder tree (still fully combinational, no new registers) and re-run signoff at the *original* Implementation A clock constraint. Does it close timing? Compare its area/latency trade-off against Implementation B.
2. **Push the tap count:** re-run Implementation A at 16 taps. Does the same clock period fail *earlier* (at synthesis, not just post-route)? What does that tell you about how much margin synthesis-stage STA actually gives you?
3. **Corner sweep:** re-run post-route STA at the sky130 slow/slow (SS) corner instead of typical. How much worse does the naive implementation's slack get?
4. **Reset fanout:** deliberately widen `DATA_W` to 16 and observe how the CTS/reset network report changes. Is the growth in buffer count proportional to bit width, tap count, or both?
5. **Two-stage pipeline:** split the 8-term chain into four 2-term partial sums with two pipeline stages instead of one. What's the new latency, and was one stage actually necessary, or was it enough?

---

## 16. Prediction Questions

- **Q1 (minute 8, before synthesis):** "We're about to constrain this at a clock period that looks generous for 8-bit logic. Does anyone want to bet whether it stays fine all the way to the end of the flow?"
- **Q2 (minute 22, after seeing the clean 45% placement):** "If I push utilization from 45% to 85% on this exact netlist, what do you expect to happen to (a) how long placement takes and (b) how routing goes afterward?"
- **Q3 (minute 40, after CTS finishes):** "Before I explain anything — why do you think the tool added ~40 cells we never wrote in the RTL?"
- **Q4 (minute 57, right after the post-route STA reveal):** "This is the exact same command and the exact same design as minute 18. What's different between then and now that could possibly explain a different answer?"
- **Q5 (minute 71, before showing the pipelined RTL diff):** "Given what you now know is broken, what's the smallest RTL change you'd try first?"

---

## 17. Discussion Prompts

- "We picked a *marginal* clock constraint on purpose. Why would picking an obviously-impossible constraint have taught you less?"
- "Implementation B costs one extra cycle of latency. In what kind of application would that be a dealbreaker, and in what kind would nobody notice?"
- "DRC and LVS both passed at the end, but so did STA earlier — for Implementation A, at synthesis. What does that tell you about needing *multiple, independent* signoff checks rather than trusting any single one?"
- "If you were told to fix Implementation A's timing but were *not allowed* to touch the RTL, what are your options, and what would you expect each to cost you in area or power?"

---

## 18. Common Student Misconceptions

- **"If synthesis timing passes, the chip will work."** Directly refuted by the workshop's central failure — this is the misconception the entire 90 minutes is built to correct.
- **"More utilization is strictly better because it saves area."** Refuted by the congestion side experiment — utilization is a trade-off, not a free win.
- **"The clock tree buffers are a sign something went wrong."** They're normal and expected on any design past a handful of flops; the workshop deliberately creates the "why are they here" moment specifically to preempt this misreading.
- **"Pipelining always makes a design faster."** It doesn't change throughput by itself in this example — it changes *whether the same clock period is achievable*, at the cost of latency. Worth stating explicitly, since "pipelining = faster" is a common oversimplification carried over from software contexts.
- **"DRC/LVS are basically the same check twice."** Directly addressed in Stage 8 — they check unrelated things (manufacturing geometry rules vs. netlist/layout equivalence).

---

## 19. Common Interview Questions That Naturally Arise

| Interview question | Answered by workshop moment |
|---|---|
| "Explain setup and hold timing." | Stage 5 reveal + Stage 6 root-cause |
| "Why would post-route timing differ from post-synthesis timing?" | The entire spine of the workshop |
| "What is clock skew, and how do you reduce it?" | Stage 3 |
| "What's the difference between WNS and TNS?" | Stage 5, reading `report_checks` |
| "Name three ways to fix a setup violation." | Stage 7 discussion (pipeline demonstrated; resize/buffer and restructure discussed) |
| "What's utilization, and why not maximize it?" | Side experiment, §5 Failure 1 |
| "What's the difference between DRC and LVS?" | Stage 8 |
| "Walk me through the RTL-to-GDSII flow." | The whole 90 minutes, which is exactly why living through it beats memorizing the list |

---

## 20. Extending Into a Longer Workshop Series

- **Session 2 — Power and IR drop:** same FIR design, add a power grid, introduce IR drop analysis and why it can create *timing* violations that look identical to setup violations but have a completely different root cause and fix.
- **Session 3 — Multi-corner, multi-mode (MCMM) signoff:** re-run Implementation B across slow/typical/fast corners and multiple operating modes; introduce the idea that "closing timing" means closing it everywhere, not just at the corner shown in this workshop.
- **Session 4 — DFT basics:** add scan chains to the pipelined FIR, show how DFT insertion perturbs placement/routing and reopens timing questions that were already "closed."
- **Session 5 — Hierarchical / macro-based design:** scale up to a design large enough to require hierarchical floorplanning, introducing macro placement, pin assignment across hierarchy boundaries, and abstract (black-box) timing models for hard macros.
- **Session 6 — ECO flow:** take the *routed* Implementation B design, introduce a late spec change (a coefficient set update), and walk through an incremental Engineering Change Order flow rather than a from-scratch re-run — a very real and very interview-relevant skill this 90-minute session intentionally has no room for.

---

## 21. Facilitator Calibration Checklist (do this before every cohort, not just once)

Tool versions, PDK revisions, and even host CPU architecture can shift exact timing numbers by tens of picoseconds — enough to flip a deliberately marginal constraint from "barely passes" to "barely fails" at the *wrong* stage. Before running this workshop with a new group:

1. Run the full flow for Implementation A on the exact image/PDK version you'll use, and record the actual synth-stage and post-route WNS.
2. Binary-search the clock period in `constraints_a.sdc` until synth-stage WNS is small and positive (a few hundred picoseconds, not a wide margin) and post-route WNS is clearly negative (at least a few hundred picoseconds negative, so it's unambiguous even on a screen share).
3. Confirm the *same* period, applied to Implementation B, produces positive slack post-route.
4. Re-generate the `reports/golden/` snapshots checked into the repo so a slow laptop can fall back to them without breaking the narrative.
5. Time a full dry run of Stage 7's "pre-cached full re-run" on your actual workshop hardware — if it doesn't finish inside the 10-minute window, cache the result rather than running it live, and tell the room you're showing them a captured run for time.

---

*This document is intentionally opinionated about ordering and pacing rather than following the standard RTL→GDSII stage list mechanically — the narrative spine (confidence → shock → investigation → fix → relief) is the actual pedagogical engine, and the flow order was chosen to serve that arc, not the other way around.*
