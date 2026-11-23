# Children's data: what PoraBondhu stores, who can see it, and how it is deleted

This describes what the software does today. It is not legal advice, and no ethics or legal approval
has been obtained. Before any real child is recorded, follow the safeguards in
[CLASSROOM_AND_PILOT.md, section 7](CLASSROOM_AND_PILOT.md#7-safeguards-required-before-any-real-child-pilot).

## What is stored

| Data | Where | Kept until |
|---|---|---|
| Roll code, optional nickname, class, grade | Database (`backend/data/porabondhu.db`, or PostgreSQL) | The teacher deletes the student or class |
| Child's recording (16 kHz WAV) | `backend/data/audio/` on the computer running PoraBondhu | The teacher finalises the review (unless "Keep the audio" is ticked), or `PB_AUDIO_RETENTION_DAYS` after recording (default 14, failed readings included), whichever comes first. Kept recordings expire after `PB_KEPT_AUDIO_DAYS` (default 90) |
| Word marks, transcript of what the model heard, scores | Database | The teacher deletes the reading, student or class |
| Single-word practice checks | Not stored: processed in memory and discarded | — |
| Optional child login (username, password hash) | Database | The teacher removes the login or the student |

No names, photos, dates of birth or contact details are asked for. No audio or text is sent to any
outside AI or analytics service; the only outside call is Microsoft Edge TTS, which receives the
**passage text** for the "Listen first" voice, never a child's voice or data.

## Who can see it

* **A teacher** sees the classes they created, plus shared classes (classes with no owner, such as
  the demo classes or classes created before per-teacher access existed). Another teacher's class
  returns "not found".
* A **district officer** sees only the district view: per school, how many children were assessed,
  the median reading speed and error rates per kind of written unit, from **teacher-checked readings
  only**. No child, roll number, nickname, class list, recording or single reading is ever sent to this
  role; any school, unit or week with **fewer than 5 children is hidden**, so one child cannot be
  singled out. The server refuses every other page for this role (tested).
* A **child login** sees only that child's own readings and assignments, and sees marks and errors only
  after the teacher has reviewed the reading (enforced by the server).
* Whoever has **administrator access to the computer or server** can read the files directly. Use an
  encrypted disk (e.g. BitLocker on Windows) and keep the laptop locked.
* On the **public demo** the logins are shared, so anyone can see what is recorded there. It must never
  be used for real children.

## Consent and withdrawal (process the school must run)

* Written consent from a parent or guardian before a child is recorded, explaining the points above;
  the child may also refuse on the day.
* **Withdrawal:** the teacher opens the student page and deletes the student. This deletes the child's
  readings, marks, recordings and login at once. To keep the child but remove recordings, delete
  the readings individually or let retention remove the audio.
* Keep the signed consent forms on paper at school, separate from the roll codes.

## Security in the software

* Passwords are stored only as salted hashes; sessions are server-side (only a hash of the cookie is
  stored), cookies are HttpOnly, SameSite=Lax and Secure over HTTPS.
* Writes from other websites are blocked (Origin check). Five wrong passwords lock the login for 10
  minutes (per account on a real installation, per account and address on the public demo).
* Changing a password logs that account out everywhere else. Teacher passwords need 8+ characters.
* Uploads are limited to 25 MB; recordings longer than 5 minutes or too quiet are rejected and deleted.
* Per-login limits: 30 reading uploads and 60 word checks per 10 minutes. The word check accepts only
  assigned or teacher-checked practice words, keeps no audio, and is shown as a practice hint.
* On the server, the app port is bound to 127.0.0.1 so only the HTTPS proxy can reach it.

## Real installation checklist

1. `PB_SEED_DEMO=false` before the first start (no demo logins, simulated data or demo reset).
2. `PB_AUDIO_RETENTION_DAYS=14` (or shorter).
3. Teacher logins with `python -m scripts.create_teacher <name>`, one per teacher, unique passwords.
   Settings shows a red warning if any teacher still uses the demo password.
4. Run on the school's own laptop (offline) or a server only the team controls, over HTTPS.
5. Encrypted disk; no copies of `backend/data/` on USB sticks or personal phones.
6. A named person who deletes all data at the end of the pilot and confirms it in writing.
