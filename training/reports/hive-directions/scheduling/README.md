# Five public schedules as a development baseline

These five single-mode PSPLIB instances each contain 30 real activities, two dummy endpoints, precedence constraints and four renewable resources. The objective is to minimize completion time. Every proposed schedule was checked independently by recounting resource use over its intervals and checking all precedence edges. The full receipt includes all three selected schedules as start times in ascending job-ID order. [Official PSPLIB instances and solution records](https://www.om-db.wi.tum.de/psplib/getdata.php?mode=sm)

| Instance | Proven optimum | Shortest duration first | Longest remaining precedence path first | Best of 64 random priority lists |
| --- | ---: | ---: | ---: | ---: |
| j301_1 | 43 | 57 | 46 | 45 |
| j301_2 | 47 | 57 | 48 | 51 |
| j301_3 | 47 | 50 | 51 | 47 |
| j301_4 | 62 | 71 | 63 | 62 |
| j301_5 | 39 | 42 | 47 | 42 |

Random priority search attained two published optima. It cost 64 schedules per instance. Each deterministic policy used one schedule per instance. These are five development cases from a single parameter family. They calibrate a classical baseline for future work. No HiveMIND model was measured. The portable run checked all 330 schedules in 0.225 seconds on the test host after downloading the data. Timing varies with the machine and the checker's implementation.

## Repeat the measurement

Python 3.9 or newer is sufficient. Run from the folder containing `pilot.py`. The default command fetches both official files into memory. For an offline rerun, fetch them once and use the local flags.

```sh
python pilot.py > rerun.json
curl -fL 'https://www.om-db.wi.tum.de/psplib/download_dataset.php?set=j30&mode=sm&format=zip' -o j30.zip
curl -fL 'https://www.om-db.wi.tum.de/psplib/download_merged.php?set=j30&mode=sm' -o j30-solutions.json
python pilot.py --archive j30.zip --solutions j30-solutions.json > offline-rerun.json
```

The receipt records the SHA256 of both downloads and each individual instance, the seeds (2808 through 2812), the chosen random draw and all makespans. The parser reads the instances directly from the ZIP in memory. The solver never receives the published optima. The published optimality flag is used only to identify the five certified reference values in the report. Reference pages can update over time. [Recorded measurements and hashes](results.json)
