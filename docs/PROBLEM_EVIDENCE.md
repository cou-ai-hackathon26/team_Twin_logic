# The problem, with evidence

Every number below comes from a published source that we opened and checked on 23 Nov 2026. Anything
we have **not** measured is labelled as an assumption or as not yet done. No teacher interview,
classroom observation or child recording has been made by the team.

## 1. The problem in one sentence

**Bangladeshi primary teachers know that about half of their pupils cannot read Bangla at grade
level, but they have no quick way to hear each child read and find out *which* letters and
conjuncts that child is stuck on, so the help they give is not targeted.**

| Question | Answer |
|---|---|
| **Who has the problem?** | Teachers of Grades 1-5 in government primary schools (Bangla lessons) |
| **Who is hurt by it?** | Children who fall behind in reading and are not noticed until a written test |
| **What do they do today?** | Read-aloud in class, written tests, and the national assessment every few years |
| **Why is that not enough?** | Written tests do not show *how* a child reads; listening to each child one by one takes too long (section 3) |
| **What does PoraBondhu change?** | The child reads one short passage aloud; every word is marked and each error is traced to the written unit (কার, ফলা, যুক্তাক্ষর, রেফ). The teacher checks the marks and assigns practice |

## 2. Evidence chain

| # | Fact | Source | What it means for us |
|---|---|---|---|
| E1 | In 2022, **51%** of 10-year-olds in Bangladesh could not read and understand a simple text (learning poverty) | World Bank, *Human Capital Complementary Indicators: Bangladesh*, 2025 ([PDF](https://thedocs.worldbank.org/en/doc/24459fe03f47e132c41e1e9823b1c765-0140012025/original/Bangladesh.pdf)) | The reading problem is large and national |
| E2 | National Student Assessment 2022: on 6 Dec 2022, **54,232 students** in Grades 3 and 5 were tested; **about 50%** showed grade-level proficiency in Bangla | DPE / UNICEF, presented by technical partner ACER ([slides, UNESCO NEQMAP 2024](https://neqmap.bangkok.unesco.org/wp-content/uploads/2024/01/Session-3-Priyanka-Sharma.pdf)); full report: [DPE](https://dpe.portal.gov.bd/sites/default/files/files/dpe.portal.gov.bd/publications/27a08801_1d5d_4e08_8fdb_25a4a693a2f3/NSA-2022%20Final%20Report.pdf) | Half the children in Grades 3 and 5 are below grade level in Bangla |
| E3 | NSA 2022 is a **pen-and-paper, system-level** test, run once every few years (2017, then 2022) | Same ACER/UNICEF slides; ACER news, *Report shows reading and maths successes and challenges in Bangladesh* | It tells the government *how many* children struggle. It does not tell a teacher *which* child misreads *which* letter, and it does not listen to oral reading at all |
| E4 | Oral reading fluency benchmark: at least **45 words per minute by the end of Grade 2**; Bangla is harder because it has "different vowel signs and conjunct letters" | Room to Read, *Benchmarking reading fluency in Bangladesh*, 16 Oct 2017 ([page](https://www.roomtoread.org/the-latest/benchmarking-reading-fluency-in-bangladesh/)) | Fluency must be measured by **listening**, per child; vowel signs (কার) and conjuncts (যুক্তাক্ষর) are named as the hard part. That is exactly the unit PoraBondhu diagnoses |
| E5 | Government primary schools had **1 teacher per 28 students** in 2023 (average) | *The Daily Star*, opinion by Dr Nawshad Ahmed, 4 Sep 2025 (cites Annual Primary School Statistics) ([article](https://www.thedailystar.net/opinion/views/news/bangladesh-needs-better-education-infrastructure-prevent-primary-dropouts-3977821)) | Even at the average, one round of individual listening is long (section 3); crowded schools are worse than the average |
| E6 | Large gaps remain between divisions, districts, school types and areas (e.g. haor, hill tracts lower) | NSA 2022 slides (E2) | Teachers in the weakest areas need help that works offline and costs nothing per use |

## 3. Why the teacher cannot do this alone (our calculation, an assumption)

A one-to-one oral reading check (hear the child read for one minute, note the errors, write down which
letters were wrong) takes **about 3 minutes per child**. This is our estimate, not a measurement.

| Class size | One round of listening, by hand |
|---|---|
| 28 (national average, E5) | 28 × 3 = **84 minutes** |
| 50 (a crowded class) | 50 × 3 = **150 minutes** |

A Bangla period is about 40 minutes, so one round takes 2-4 periods, and it still gives no letter-level
diagnosis unless the teacher writes it down for each word. PoraBondhu marks a one-minute reading in
about 16-20 s on a laptop CPU (measured, see the README Evaluation), so the teacher only has to check the
words it flags. **How much time this actually saves in a real class is not measured yet.**

## 4. How each part of PoraBondhu answers the evidence

| Evidence | Feature |
|---|---|
| E2, E3: half are behind, but a written test does not say why | Every word marked; each error traced to its written unit; weak patterns per child |
| E4: fluency needs listening; কার and যুক্তাক্ষর are the hard part | WCPM per reading; Bangla grapheme segmenter; class pattern map by unit |
| E5: too many children per teacher | The child reads alone on a laptop or phone; the teacher reviews only flagged words |
| E6: weakest areas, poor connectivity | Runs offline on a CPU, no API cost, data stays on the device |
| Teachers must stay in charge | Unsure marks are never counted; the teacher has the final word; the child sees no mark before review |

## 5. What is still missing: confirmation from teachers

We have **not** spoken to any teacher about this project. The evidence above shows that the problem
exists at national level; it does not show that teachers want *this* tool. That is the most important
gap, and we say so openly.

How to close it (takes about 10 minutes per teacher; can be done by phone):

1. Ask a working primary teacher the five questions below, **without showing the app first**.
2. Then show the 2-minute [demo video](https://youtu.be/z_jiGV3ZkbU) and ask question 6.
3. Write down the answers as said. Quote a teacher only with their permission and without their name or
   school unless they agree. Never record children for this.

| # | Question |
|---|---|
| 1 | How many children are in your Bangla class? |
| 2 | How do you find out which children read poorly? How long does it take? |
| 3 | When a child reads poorly, do you know which letters or conjuncts they get wrong? How? |
| 4 | Which kinds of letters cause the most mistakes (কার, ফলা, যুক্তাক্ষর, রেফ, others)? |
| 5 | Do you have a laptop or smartphone at school? Is there internet? |
| 6 | (after the video) Would a tool like this help you? What would stop you from using it? |

Result so far: **0 interviews done.** Answers will be added here (with dates) only after they happen.
