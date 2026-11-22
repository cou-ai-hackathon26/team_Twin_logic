# Classroom workflow, pilot and cost plan

Status: **proposal**. No school, NGO or government partnership exists yet, and no teacher has used
PoraBondhu in a classroom. Everything below is a plan to test, not a result.

## 1. A week in a Grade 3 class (60 children, one teacher)

| Step | Who | Time | What happens |
|---|---|---|---|
| Set up once | Teacher | 10 min | Create the class, add roll numbers (no names), print the login slips if children will read on their own |
| Hear each child | Child reads, teacher or a helper starts the recording | 1-2 min per child | One graded passage (for example T05-T08 for Grade 2, matched to the textbook lesson the class is on). 10-12 children a day covers the class in a week |
| Wait for marks | Laptop | ~20-30 s per reading on a 4-core laptop CPU, runs in the background | The next child can start reading while the previous one is marked |
| Review | Teacher | 1-2 min per reading | Open the review queue (sorted "needs most help first"), listen to any red or amber word, correct with one tap. "Unsure" words are never counted as errors |
| Plan the lesson | Teacher | 5 min per week | Class pattern map: which units (e.g. র-ফলা, ি/ী, যুক্তাক্ষর) most children misread. Group children by weak pattern; the practice words come from the passage bank |
| Talk to parents | Teacher | optional | Print the one-page student report (Report button), marks only after the teacher has reviewed them |

Total extra teacher time: about 2-3 minutes per child per assessment round, against listening to
every child read individually and noting errors by hand.

## 2. Without reliable internet

* Everything (speech model, marking, database) runs on the school's laptop CPU. No internet is
  needed after setup; the models are downloaded once (`setup.ps1`, about 3 GB).
* The only online feature is the "Listen first" model reading (Microsoft Edge TTS). Its audio can be
  generated in advance while online (`python -m scripts.pregen_tts`) and is then cached.
* Children's audio never leaves the laptop and is deleted when the teacher finalises the review.

## 3. Cost per school (estimates, to be checked with local prices)

| Item | One-time | Notes |
|---|---|---|
| Laptop, 4 cores, 8 GB RAM (often already in the school's ICT lab) | 0 if reused | Tested on an Intel i5-10310U (2020) |
| USB headset microphone | small | Cuts classroom noise; the audio quality check rejects unusable recordings |
| Software and models | 0 | Open source (Apache-2.0 model), no API fees, no subscription |
| Teacher orientation | 2 hours | Recording, the review screen, what "unsure" means, reading the class map |

Running cost: electricity only. There is no per-child or per-reading charge, because no cloud AI is used.

## 4. Pilot plan (8 weeks, proposed)

1. **Weeks 1-2: consent and baseline.** One or two government primary schools, Grades 2-3. Written
   parent/guardian consent, roll codes only, no faces or names. Teachers mark one reading per child by
   hand as the baseline.
2. **Weeks 3-6: use.** Teachers assess each child twice with PoraBondhu. Two trained annotators
   independently label a sample of recordings (target 300+ words per grade) to measure accuracy on
   **children** (kappa between annotators, recall/precision/false alarms of the system).
3. **Weeks 7-8: review.** Teacher interviews (time saved, trust in the marks, which features they used),
   changes to the passage bank and thresholds, a short report.

Success would mean: teachers keep using it without help, children's misreads are caught with at most a
10% false-alarm rate on child speech (our own pre-set target), and teachers say the pattern map changed
what they taught. If those are not met, we report it.

## 5. Possible routes to scale (no agreement exists)

* **School ICT labs / Upazila resource centres**: install on existing laptops.
* **NGO-run schools and reading programmes**: organisations that already run early-grade reading
  assessments could use it to cut assessment time.
* **DPE / NCTB**: the passages follow the national textbook sequence (see
  [CURRICULUM_ALIGNMENT.md](CURRICULUM_ALIGNMENT.md)), so a validated version could support existing
  reading-assessment work. This would need a proper child-speech validation first.

## 6. Teacher interviews

Use `teacher_interview_guide.txt`. Record only what teachers actually said, ask permission before
quoting, and list here the design changes made because of their answers.

| Teacher (role, district, no name unless they agree) | Key points | Change we made |
|---|---|---|
| _not yet interviewed_ | | |
