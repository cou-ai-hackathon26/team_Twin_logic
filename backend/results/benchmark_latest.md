# PoraBondhu benchmark (test split)

Generated 2026-11-22 17:35 UTC. 100 recordings, speakers: fleurs-test-male.

## all

| System | Recall | Precision | False alarms | Unsure | WCPM MAE |
|---|---|---|---|---|---|
| whisper_word | 100.0% (262/262; 95% CI 98.6-100.0) | 14.6% (262/1791; 95% CI 13.1-16.3) | 95.1% (1529/1608; 95% CI 93.9-96.0) | 0.0% (0/1870; 95% CI 0.0-0.2) | n/a |
| ctc_word | 100.0% (262/262; 95% CI 98.6-100.0) | 27.4% (262/955; 95% CI 24.7-30.4) | 43.1% (693/1608; 95% CI 40.7-45.5) | 0.0% (0/1870; 95% CI 0.0-0.2) | n/a |
| porabondhu | 82.4% (216/262; 95% CI 77.4-86.6) | 76.1% (216/284; 95% CI 70.8-80.7) | 4.2% (68/1608; 95% CI 3.3-5.3) | 17.7% (331/1870; 95% CI 16.0-19.5) | n/a |

## adult

| System | Recall | Precision | False alarms | Unsure | WCPM MAE |
|---|---|---|---|---|---|
| whisper_word | 100.0% (262/262; 95% CI 98.6-100.0) | 14.6% (262/1791; 95% CI 13.1-16.3) | 95.1% (1529/1608; 95% CI 93.9-96.0) | 0.0% (0/1870; 95% CI 0.0-0.2) | n/a |
| ctc_word | 100.0% (262/262; 95% CI 98.6-100.0) | 27.4% (262/955; 95% CI 24.7-30.4) | 43.1% (693/1608; 95% CI 40.7-45.5) | 0.0% (0/1870; 95% CI 0.0-0.2) | n/a |
| porabondhu | 82.4% (216/262; 95% CI 77.4-86.6) | 76.1% (216/284; 95% CI 70.8-80.7) | 4.2% (68/1608; 95% CI 3.3-5.3) | 17.7% (331/1870; 95% CI 16.0-19.5) | n/a |

## Hypothesis

Recall gain over Whisper: -17.6 pp; precision not worse: True; supported: **False**

## Targets (adult)

| Measure | Target | Value | Met |
|---|---|---|---|
| recall | >= 0.8 | 0.824 | yes |
| precision | >= 0.8 | 0.761 | no |
| false_alarm | <= 0.05 | 0.042 | yes |
| grapheme_accuracy | >= 0.7 | 1.0 | yes |
| wcpm_mae | <= 5.0 | n/a | n/a |
| wcpm_spearman | >= 0.9 | n/a | n/a |
| uncertainty_coverage_noisy | >= 0.5 | n/a | n/a |
| kappa | >= 0.8 | n/a | n/a |
| sec_per_60s | <= 15.0 | 16.21 | no |
