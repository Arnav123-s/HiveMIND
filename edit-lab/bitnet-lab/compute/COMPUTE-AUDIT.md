# COMPUTE-AUDIT — where a standard lab run's time goes (Muse's work, Muse's side)

Method: two instruments in this folder, both run against the lab as it is.
`probe_phases.py` times a short instrumented training run phase by phase
(imports, data setup, per-step backward / clip / vote phases) using CPU time;
`probe_startup.py` itemizes process startup (bare python → import torch →
import train → memmap+held windows → model+trainer build) with wall, CPU, and
RSS, 2 reps each. Every number below comes from those runs; contention during
measurement is stated, not hidden.

## Machine state during measurement

_(pending — processes sharing the VM, load, free RAM at measurement time)_

## Startup — what a run pays before step 1 (probe_startup.py)

_(pending)_

## Setup + phases — where the steps' time goes (probe_phases.py)

_(pending)_

## Threading behavior

_(pending)_

## Memory

_(pending)_

## Headline — the top time sinks, ranked

_(pending)_

## What this picks as targets

_(pending)_
