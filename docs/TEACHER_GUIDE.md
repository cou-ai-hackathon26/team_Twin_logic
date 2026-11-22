# Teacher guide (শিক্ষক নির্দেশিকা)

PoraBondhu listens to a child read a short Bangla passage and suggests which words, and which written
units (কার, ফলা, রেফ, যুক্তাক্ষর), went wrong. **You have the final word on every mark.** It is a
teacher's aid, not an official test. Use the **বাং / EN** button at the top to switch the menus and
main buttons to Bangla.

## What you need

| | |
|---|---|
| Computer | A laptop with 4 CPU cores and 8 GB RAM is comfortable; 2 cores work but marking is slower |
| Disk | About 3 GB free for the program and speech model |
| Microphone | A USB or wired headset microphone works best in a noisy classroom |
| Internet | Only for the one-time setup (`setup.ps1` downloads the model). After that it works offline, except the optional "Listen first" voice, which can be prepared in advance (`python -m scripts.pregen_tts`) |
| Browser | Chrome or Edge. Recording needs `http://localhost` (on the same laptop) or an `https://` address |

Marking time measured on our development laptop (Intel i5-10310U, 4 cores): about 18-20 seconds for a
60-second reading. The first reading after starting the program takes longer while the model loads.
You can keep working: the next child can read while the previous reading is being marked.

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
3. The child sees "your teacher will check your reading", not a mark.

## Reviewing (the important part)

1. **Review queue** lists readings waiting for you, "needs most help first".
2. Red = misread, grey line = skipped, dotted amber = **unsure** (the computer was not sure; it never
   counts as an error). Click a word to hear just that word and see which unit differs.
3. If the computer is wrong, change the mark with one tap (keys 1-4 also work). Then **Finalise**.
   The recording is deleted unless you tick "keep audio".
4. Only now does the child see their mark out of 10 and the words to practise.

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

* Use roll codes, not names. Do not take photos.
* Recordings are deleted when you finalise a review (unless you keep them), and automatically after
  the number of days set by `PB_AUDIO_RETENTION_DAYS` (we recommend 14).
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
