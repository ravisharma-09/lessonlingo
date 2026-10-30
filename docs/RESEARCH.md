# Why LessonLingo: sources

Figures below come from press coverage and project pages found on 31 Oct 2026. Re-check a number
against its original before quoting it on stage. We did not run a comparison with any cloud tool.

- **Policy pull.** AICTE has run a programme to translate engineering books into Indian languages
  (12 languages in its announcement). Its chairman said earlier efforts stalled because study
  material was not available in Indian languages.
  [Careers360](https://news.careers360.com/aicte-bets-big-on-engineering-in-indian-languages-undertakes-translation-of-technical-books-in-12-languages/amp)
- **Demand.** NPTEL is adding transcripts, subtitles and dubbed audio in 11 languages to popular
  courses, so far for selected courses.
  [NPTEL blog, Feb 2024](https://stories.nptel.ac.in/index.php/2024/02/12/nptel-courses-now-available-in-local-languages/)
- **Language is a barrier.** A 2017 KPMG-Google report ("Indian languages: defining India's
  internet") is widely reported as finding 234 million Indian-language internet users against
  175 million English users at the end of 2016, and 60% of Indian-language users naming limited
  language support and content as the largest barrier. Older data, read from press coverage.
  [KPMG report](https://assets.kpmg.com/content/dam/kpmg/in/pdf/2017/04/Indian-languages-Defining-Indias-Internet.pdf)
- **Technical terms need care.** A 2026 study of translating NPTEL technical lectures argues that
  terms must stay consistent within a course. This is why LessonLingo has a keep-in-English
  glossary and a teacher review step.
  [arXiv 2602.08698](https://arxiv.org/abs/2602.08698)
- **Open models.** IndicTrans2 is described as the first open model to support all 22 scheduled
  Indian languages, released with permissive licences.
  [IndicTrans2 paper](https://arxiv.org/abs/2305.16307)
- **Prior art.** IIT Madras and Bhashini have dubbed NPTEL Python lectures into Hindi, Tamil and
  Punjabi with a full pipeline (speech recognition, translation, speech synthesis, lip sync).
  Those are central, curated courses. LessonLingo is the tool one teacher can run on their own
  laptop, offline, for their own lecture.
  [Dubbing pipeline paper](https://arxiv.org/abs/2211.01338)

## What the research means for the product

Found on 31 Oct 2026, from search summaries. Check originals before quoting numbers.

- **Connectivity is improving but not solved.** Parliament data for 2023-24 lists 53.9% of all
  schools with internet; 2024-25 UDISE+ is reported at 63.5%. Government-school figures differ
  by source (about 46% in one report). Offline-first helps the schools still without a
  connection, but do not claim a single number on stage.
  [Business Standard](https://business-standard.com/india-news/57-schools-have-functional-computers-53-have-internet-access-govt-125010101044_1.html),
  [IndiaSpend](https://www.indiaspend.com/data-viz/are-indian-schools-ready-for-the-digital-age-942576)
- **Speech recognition is the weak link.** A study of about 8,740 hours of NPTEL lectures found
  Whisper's word error rate differs across speakers and subjects. Errors in the English
  transcript flow straight into the translation, so the teacher should be able to fix the
  transcript before translating. [arXiv 2307.10587](https://arxiv.org/abs/2307.10587)
- **Code-mixed speech is a known weak spot.** Machine translation is weaker on informal,
  code-mixed (for example Hinglish) text. We target English lectures; say so.
  [WMT 2022](https://aclanthology.org/2022.wmt-1.113)
- **Existing tools expect human editing.** UGC guidelines for Anuvadini say accuracy varies by
  subject and language and recommend a machine first pass followed by manual editing. We could
  not confirm whether Anuvadini or Bhashini translation works offline.
  [UGC guidelines](https://dakmnagpur.in/www.ugc.gov.in/pdfnews/5634541_Translation-to-indian-languages-Guidelines.pdf)
- **Subtitles in the learner's own language: evidence is mixed.** A 2022 study of 70 native Chinese
  speakers found native-language subtitles improved lecture comprehension; a 2020 study found no
  effect for same-language subtitles. Do not claim LessonLingo "improves learning" without a pilot.
  [JoSTrans 2022](https://www.jostrans.org/article/view/7984),
  [Research in Learning Technology 2020](https://journal.alt.ac.uk/index.php/rlt/article/view/2340/2629)

## Improvements ranked by value

1. **Check the English transcript before translating.** Addresses the speech-recognition risk.
2. **Flag doubtful lines.** faster-whisper reports a confidence score per segment (verify the field
   name on the laptop); highlight low-confidence lines in the review table.
3. **Per-course glossary with preferred translations** (term to the exact word to use), not only
   keep-in-English. Terms then stay consistent across a whole course.
4. **Feed glossary terms to Whisper** as a prompt so technical words are heard correctly
   (verify the option on the installed faster-whisper).
5. **Class pack.** One folder or zip with subtitles and translated notes that a teacher can copy
   to a pen drive or share, since the target classrooms may have weak internet.
6. **Pilot with a fluent speaker.** Have a Kannada or Hindi speaker rate 20 lines and record the
   result in the README. This is the strongest proof we can produce tonight.
7. **Dogfood.** Translate our own README and CONTRIBUTING into Hindi and Kannada to onboard
   first-time contributors, which matches the "guides that onboard first-time contributors" idea
   on the Hack Day theme slide.

## Real use cases

- A college teaching assistant subtitles recorded lectures for first-year students who study in
  a regional language.
- A teacher in a school with an unreliable connection prepares lessons once, offline.
- A community learning centre or NGO shares translated lesson packs on a pen drive.
- An open-source maintainer makes a README and contributor guide available in several languages.
- Subtitles also help students who are deaf or hard of hearing, which is a side benefit to mention.
