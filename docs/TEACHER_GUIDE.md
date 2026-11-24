# Teacher guide (শিক্ষক নির্দেশিকা)

PoraBondhu listens to a child read a short Bangla passage and suggests which words, and which written
units (কার, ফলা, রেফ, যুক্তাক্ষর), went wrong. **You have the final word on every mark.** It is a
teacher's aid, not an official test. Use the **বাং / EN** button at the top to switch the menus and
main buttons to Bangla.

## What you need

| Need | Value | Evidence |
|---|---|---|
| CPU | 4 cores comfortable; 2 cores work but slower | **Measured** on an Intel i5-10310U laptop (4 cores) and a 2-core VPS; no other machines tested |
| Marking time | 4-core laptop: about 4.5-5 s per 14-16 s of audio (roughly 18-20 s for a 60 s reading). 2-core server: 8.2-8.4 s per 16.2 s of audio (roughly 31 s for a 60 s reading); loading the model once takes about 10 s | **Measured**, a handful of recordings, 22 Nov 2026 |
| Memory | About 0.7 GB for the running app with the Bangla model loaded; 8 GB RAM laptop recommended | **Measured** on the VPS container (idle, model loaded); the 8 GB recommendation is an **estimate** |
| Disk | About 3.5 GB on our laptop: Python environment 1.4 GB, model folder 1.6 GB (the int8 model used is 339 MB; `setup.ps1` also keeps the 1.2 GB fp32 export), Whisper small 464 MB (English passages and the comparison only). The Docker image is 3.4 GB | **Measured** on our laptop and VPS |
| Microphone | USB or wired headset in a noisy classroom | **Recommendation**, not tested in a classroom |
| Internet | Only for setup (`setup.ps1` downloads the model). Afterwards it works offline, except the optional "Listen first" voice, which can be prepared in advance (`python -m scripts.pregen_tts`) | **Measured**: marking ran with networking switched off (Docker `--network none`, 22 Nov 2026); a full offline classroom session is not yet tried |
| Browser | Chrome or Edge. Recording needs `http://localhost` (same laptop) or an `https://` address | Browser rule |

The first reading after starting the program takes longer while the model loads. You can keep
working: the next child can read while the previous reading is being marked.

## First day

1. **Log in.** On a school installation, ask the person who set it up for your teacher login
   (created with `python -m scripts.create_teacher <name>`). Then **Settings → Change my password**.
2. **Create a class:** Dashboard → **New class** (name, grade). **Add students** by roll number. No
   names are needed; a nickname is optional.
3. **Optional child logins:** on a student's page, give the child a login so they can practise on their
   own. A grade 1-2 child usually reads with you instead.

## Hearing a child read

1. **New assessment** → choose the child and a passage. Passages `T01`-`T12` follow the NCTB lessons
   (see [CURRICULUM_ALIGNMENT.md](CURRICULUM_ALIGNMENT.md)); pick the one for the lesson you are on.
2. Press the big microphone button, let the child read, press stop. The progress bar shows each step.
3. The child sees the AI result straight away (mark, coloured words, words to practise), labelled
   "AI result · teacher will check". The reading also lands in your review list; after you finalise it,
   the child sees your checked mark instead.

## Reviewing (the important part)

1. **Review queue** lists readings waiting for you, "needs most help first".
2. Red = misread, grey line = skipped, dotted amber = **unsure** (the computer was not sure; it never
   counts as an error). Click a word to see which unit differs.
3. **Listen before you decide.** Each word has three buttons:
   * **Word** (space): just that word from the child's recording.
   * **In context** (C): the word with the words before and after, for cut-off or blended words.
   * **Compare** (V): the child's word, then the correct pronunciation, back to back.
   Use **0.75×** or **0.5×** to hear small slips (a missing ফলা or কার). While the recording plays,
   the word being read lights up in the passage.
4. **Quick check** jumps through only the flagged words and plays each one by itself: listen, press 1-4,
   and the next flagged word plays. A typical reading takes under a minute.
5. If the computer is wrong, change the mark with one tap (keys 1-4 also work). The bar above the passage
   shows how often you agreed with the AI. Then **Finalise review**. The recording is deleted unless you
   tick "Keep the audio".
6. After you finalise, the child sees your checked mark instead of the AI result.

### When to trust the AI less (trust guards)

| Mark | Meaning | What to do |
|---|---|---|
| ♪ **accent** | The heard word differs only by a regional sound swap (ভাত as বাত, র for ড়, স for চ). Left as unsure, never counted as an error. | Listen: if it is the child's accent, press **Accept as accent**; if it was a reading slip, mark it misread. |
| 〰 **noisy** | Background noise over this word. Left as unsure. | Listen and decide. |
| ⚑ **odd word** | A word the AI is unreliable on (long conjuncts, rare or foreign words, or one teachers often corrected). Left as unsure. | Listen and decide. |

* **Accept as accent** on a word: marks it correct and accepts that pronunciation for future readings in
  this installation (Settings → Accepted variants; you can remove it there). Use it after listening and
  confirming that the pronunciation is acceptable, not a reading slip.
* **AI unreliable here: always ask me** on a word (for names and rare words): the AI never counts a misread on
  that word again (Settings → Words the AI leaves to you).

## Using the results

| Where | What it tells you | What to do |
|---|---|---|
| **Student page** | Marks and reading speed over time, the units this child keeps misreading ("candidate weak patterns"), practice words | **Assign practice** on a weak pattern: words and a passage with that unit go to the child's home page |
| **Class page → pattern map** | Which units most children in the class misread, and who | **Assign to this group** sends the same practice to exactly those children; teach that unit to the whole class if many share it |
| **Practice given** (student and class pages) | What you assigned and whether it is done | An assignment is done when the child reads the passage or ticks the words |
| **Export** (class page) | Every reading as a spreadsheet (opens in Excel) | Keep with your school records |
| **Report** (student and class pages) | A printable A4 page | Parent meetings; print or save as PDF |

A unit becomes a "weak pattern" only after at least 3 errors across at least 2 readings, never from a
single slip.

## Privacy

Full details: [DATA_PROTECTION.md](DATA_PROTECTION.md).


* Use roll codes, not names. Do not take photos.
* Recordings are deleted when you finalise a review (unless you tick "Keep the audio"), and automatically after
  14 days (`PB_AUDIO_RETENTION_DAYS`); recordings you chose to keep are deleted after 90 days.
* Five wrong passwords lock a login for 10 minutes. Changing your password logs you out on other devices.
* Never use the public demo website for real children. Before any real use, see the safeguards in
  [CLASSROOM_AND_PILOT.md](CLASSROOM_AND_PILOT.md#7-safeguards-required-before-any-real-child-pilot).

## Limitations you should know

* Accuracy on **children's** voices has not been measured yet. Our measurements so far use adult
  speech. Treat every mark as a suggestion and check the red and amber words.
* Regional pronunciations may be marked as errors. Add them under **Settings → Accepted variants**.
* A noisy room makes more words "unsure"; a headset helps. Very quiet or very short recordings are
  rejected with a message to read again.
* English passages are marked with a different model (Whisper) and get no letter-unit diagnosis.
