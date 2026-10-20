# Search for existing A/B/C/Reject dragon-fruit labels

As of 2026-10-21, this search has **not verified a downloadable, licensed
dragon-fruit image dataset with all four Grade A, Grade B, Grade C and Reject
targets matching PitayaGrade's criteria**. This is not proof that none exists.

* [Fitri et al. (2022), Comparison of Classification for Grading Red Dragon Fruit](https://doi.org/10.25077/jnte.v11n1.899.2022)
  reports 216 training and 75 testing images across A/B/C. Its red-fruit grades
  are weight-based (>350 g, 250–350 g, <250 g). There is no Reject class, and
  no public downloadable image dataset was verified from the paper. The paper's
  license alone does not establish permission to obtain/reuse an unavailable
  image collection. These postharvest weight grades are not automatically the
  project's preharvest quality grades.
* [Mendeley 2jpzbx8tm6, version 1](https://data.mendeley.com/datasets/2jpzbx8tm6/1)
  explicitly distinguishes Fresh/Defective for quality and Mature/Immature for
  maturity, under CC BY 4.0. Its “quality grading” title does not imply A/B/C/Reject.
* [Multi-fruit classification repository](https://github.com/codernayeem/fruit-classification-dataset)
  describes 1,667 dragon-fruit images in Good/Medium/Bad, not the four targets.
  Image reuse licensing was not verified; it is not integrated.
* Roboflow search results surface a project called “Dragon Fruit Quality”
  with mixed maturity/GradeA/GradeB/GradeC names, but a direct usable export,
  precise grading criteria and complete Reject mapping were not verified.
  The separately verified [Buah Naga Mutu project](https://universe.roboflow.com/m-rizki-fatihah/buah-naga-mutu)
  has five maturity/rot labels and CC BY 4.0, not the required four grades.

No grade labels were invented or inferred from Fresh/Defective, Good/Bad, a
disease class, maturity, or filenames as part of this integration. Existing
folder labels do not need manual transcription. A future grade dataset must
have documented compatible criteria before it can replace the grade-label gap.
