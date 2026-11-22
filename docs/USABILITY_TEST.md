# Teacher usability test: protocol and feedback form

Status: **prepared, not run.** No teacher has done this test yet. Do not report findings until real
sessions have happened; record exactly what teachers did and said.

## Purpose

Find out whether a primary teacher who has never seen PoraBondhu can do the core tasks with only the
[teacher guide](TEACHER_GUIDE.md), and where they get stuck. This is about the software, not the teacher.

## Setup (per session, about 30 minutes)

* A laptop running PoraBondhu **locally** (`start.ps1`) with demo data (`PB_SEED_DEMO=true`), or the
  public demo over HTTPS. **No children are recorded**: the teacher reads the passages in their own
  voice. A headset microphone.
* One facilitator (gives tasks, does not help unless the teacher is stuck for 2 minutes) and one note
  taker. Ask permission before starting; record notes, not video, unless the teacher agrees.
* Reset the demo before each session (Settings → Reset demo recordings).

Say first (Bangla or English): "We are testing the software, not you. Please think aloud. You can stop
at any time. We will not use your name unless you agree."

## Tasks

| # | Task given to the teacher | Success means | Note |
|---|---|---|---|
| 1 | Log in as the teacher and switch the menus to Bangla | Logged in, বাং toggle used | Time, hesitations |
| 2 | Create a class "Test 3" (Grade 3) and add 5 students | 5 roll numbers visible | Did they find **Add students**? |
| 3 | Assess Roll 01 of Class 2 with passage T06, reading it yourself with two mistakes | Reading uploaded, progress bar seen | Was the wait acceptable? |
| 4 | Review that reading: find a wrong word, listen to it, correct one mark, finalise | Finalised with ≥1 teacher change | Did they understand **unsure**? |
| 5 | On the Class 2 page, find which unit most children misread and assign practice to that group | Assignment created for the group | Did the pattern map make sense? |
| 6 | Log in as one of those children (`c2rNN` / `student123`, NN = roll number) and find what the teacher assigned; also open the reading from task 3 as `c2r01` | "From your teacher" found; the reading shows its mark only because it was finalised | |
| 7 | Back as teacher: export Class 2 and open it in Excel | CSV opens with Bangla readable | |
| 8 | Explain in your own words what one student's progress page tells you | Correct reading of marks and weak patterns | Misunderstandings |

## Measures

* Task success: done alone / done with a hint / not done.
* Time per task (stopwatch), and marking wait time for task 3.
* Number of times the teacher asked for help.
* System Usability Scale (SUS) after the session (10 standard statements, 1-5), in Bangla.

## Feedback form (after the tasks)

1. Which task was hardest, and why?
2. Did you trust the marks? When would you change a mark?
3. Was the meaning of "unsure" (অনিশ্চিত) clear?
4. How long could you spend per child per week on this? Is the review step worth it?
5. Which result would you actually use in class: per-child weak patterns, class pattern map, assigned
   practice, export, or the printed report?
6. What would stop you using it at your school (device, internet, noise, time, permission)?
7. Is anything on the child's screen unsuitable for a Grade 1-3 child?
8. One thing we should change first.

Record: date, role, grade taught, upazila, years of teaching, permission to quote (yes/no), permission
to use name (yes/no). No children's data.

## Reporting

Report the number of teachers, task success counts, median times, SUS scores and verbatim quotes
(with permission), plus the changes made because of them. Five teachers usually reveal most usability
problems; two are enough to start, but say how many took part.

## Minimum evidence before claiming stronger adoption

* At least 5 teachers completed tasks 1-5 alone, with the SUS score reported.
* At least 2 teacher interviews ([questions](CLASSROOM_AND_PILOT.md#6-teacher-interviews-not-done-yet))
  with permission to quote, and at least one design change traced to them.
* For any claim about children: a consent-based pilot meeting every safeguard in
  [section 7](CLASSROOM_AND_PILOT.md#7-safeguards-required-before-any-real-child-pilot), with
  child results reported separately (sample size, recall, precision, false alarms, teacher change rate).
