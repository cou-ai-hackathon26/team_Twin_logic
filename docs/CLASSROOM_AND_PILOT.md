# Classroom workflow, pilot and cost plan

Status: **proposal**. No school, NGO or government partnership exists yet, and no teacher has used
PoraBondhu in a classroom. Everything below is a plan to test, not a result.

## 1. A week in a Grade 3 class (60 children, one teacher)

Times are our estimates; only the marking time was measured (on our development laptop).

| Step | Who | Time | What happens |
|---|---|---|---|
| Set up once | Teacher | 10 min | Create the class, add roll numbers (no names), print the login slips if children will read on their own |
| Hear each child | Child reads, teacher or a helper starts the recording | 1-2 min per child | One graded passage (for example T05-T08 for Grade 2, matched to the textbook lesson the class is on). 10-12 children a day covers the class in a week |
| Wait for marks | Laptop | ~20-30 s per reading on a 4-core laptop CPU, runs in the background | The next child can start reading while the previous one is marked |
| Review | Teacher | 1-2 min per reading | Open the review queue (sorted "needs most help first"), listen to any red or amber word, correct with one tap. "Unsure" words are never counted as errors |
| Plan the lesson | Teacher | 5 min per week | Class pattern map: which units (e.g. র-ফলা, ি/ী, যুক্তাক্ষর) most children misread. **Assign to this group** sends words and a passage with that unit to exactly those children |
| Practice | Child, on a shared device | 5 min | "From your teacher": hear each word, say it, get an instant check; reading the assigned passage marks it done |
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

## 6. Teacher interviews (not done yet)

No teacher has been interviewed yet. Use these questions (from the team's interview guide), about 10
minutes per teacher, in person or by phone. Ask permission before quoting, never reword an answer,
and if the answers contradict this plan, change the plan.

1. Which grade do you teach, and how many students are in the class?
2. How do you currently find out whether a student can read Bangla properly?
3. How often do you get to hear each child read individually?
4. About how long does it take to listen to one child?
5. What is the hardest part of identifying weak readers?
6. Where do children usually get stuck: conjuncts, vowel signs, ফলা, or something else?
7. If a device listened to a child for two minutes and showed which words and units go wrong, would
   that help? How would you use it?
8. What could stop you using it in class (device, internet, time, noise, trust in the marks)?
9. Would you rather see results per child or a class summary? Would you assign practice from it?
10. Would you trust a mark you can change with one tap? What would make you distrust it?

| Teacher (role, upazila; no name unless they agree) | Date | Key points (their words) | Change we made |
|---|---|---|---|
| _not yet interviewed_ | | | |

## 7. Safeguards required before any real child pilot

None of these is in place yet; all are required before recording a single child.

* **Consent:** written, informed consent from a parent or guardian for each child, in Bangla, saying
  what is recorded, who hears it, how long it is kept and how to withdraw. The child can also say no.
* **Approval:** permission from the head teacher (and the upazila education office if required), and
  an ethics review through the university if results will be published.
* **Separate, private installation:** `PB_SEED_DEMO=false` (no public logins or demo data), a teacher
  login created with `scripts/create_teacher.py`, each child's login changed from any default, and
  the app run on the school's own laptop or a server only the team controls, over HTTPS.
* **Minimal data:** roll codes only (no names, photos or dates of birth); `PB_AUDIO_RETENTION_DAYS`
  set (we suggest 14); audio kept longer only for annotation, with explicit consent for that use.
* **Storage:** the laptop disk encrypted (e.g. BitLocker) or the audio folder on an encrypted volume;
  backups encrypted; a named team member responsible for the data and for deleting it after the pilot.
* **Child wellbeing:** children see their mark only after the teacher checks it (built in); no
  rankings; a child who is upset by reading aloud stops without penalty.
* **Reporting:** results reported for children separately from adults, with sample size and limits;
  no claim beyond what the pilot measured.

## 8. Biggest operational risks and next steps

| Risk | Why it matters | Realistic next step |
|---|---|---|
| Accuracy on children's voices is unmeasured | All numbers so far are adult speech; teachers will stop using it after a few false accusations | Consent-based pilot with two independent annotators (section 4), report child results separately |
| Marking speed on old school laptops | ~18-20 s per 60 s of reading on our 4-core laptop; slower on 2-core machines | Measure on the actual school laptop first; chunked processing while the child reads is the planned fix |
| Classroom noise and microphones | Noise makes words "unsure" or rejected | Use a USB headset; the quality check already rejects unusable audio |
| Regional pronunciation | Standard-Bangla model may mark accepted local forms as errors | Teachers add accepted variants in Settings; collect them during the pilot |
| Teacher time and trust | Reviewing still costs 1-2 min per reading (estimate) | Ask teachers in the interviews; track how often they change AI marks during the pilot |
| Devices and setup | Needs a laptop with ~3 GB free and a one-time model download | A prepared USB installer or a pre-loaded laptop per school |
| Hosting real data | A public server is not acceptable for children's voices | Offline school laptop by default; any hosted version only after the safeguards in section 7 |
