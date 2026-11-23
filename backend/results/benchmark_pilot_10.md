# PoraBondhu pilot benchmark: 10 FLEURS recordings

- **Scope:** first 10 recordings from the held-out FLEURS bn_in test split.
- **Audio:** real adult read speech.
- **Error labels:** simulated by modifying the expected passage text; these are not authentic speaker misreadings.
- **System:** PoraBondhu only; no Whisper or plain-CTC comparison in this pilot.
- **Interpretation:** exploratory pipeline result with wide confidence intervals. It is not child-speech validation and is not a representative benchmark.
- **Full evaluation:** the 100-recording comparison and robustness runs are still pending.

See `benchmark_pilot_10.json` for counts, intervals, model configuration, and per-recording outputs.
