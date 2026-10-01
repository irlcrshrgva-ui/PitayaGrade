# Public image candidates for owner review

Reviewed 2026-09-19. Status: candidates only; not approved for training or integrated.
The owner requested finding images and seeing them before use.

## 1. Fruit maturity and quality — recommended first inspection

- Source: https://data.mendeley.com/datasets/2jpzbx8tm6/1
- Authors: Tania Khatun, Md. Asraful Sharker Nirob, Prayma Bishshash,
  Mohammad Shorif Uddin. DOI: 10.17632/2jpzbx8tm6.1.
- Publisher lists CC BY 4.0. Retain attribution and note modifications.
- Source reports 3,779 original images across maturity and quality tasks, from
  Bangladesh; augmented images are separate. File counts require verification.
- Quality mirror: https://huggingface.co/datasets/Project-AgML/dragonfruit_quality_classification
  lists 1,652 raw images: 898 Fresh and 754 Defect.
- Opened real Fresh and Defect sample photographs in the browser for owner review.
- Fit: candidate fruit imagery and visual-defect research. Does not supply the
  manuscript's Grade A/B/C/Reject annotations or measured fruit diameters.
- Sample concern: the inspected fresh image has an orchard background; the inspected
  defect image has a white background. Audit whether background predicts labels.
  Two samples do not establish dataset-wide bias.

## 2. Fruit and plant disease — partial coverage

- Source: https://data.mendeley.com/datasets/cfchfdpfw5/1
- Authors: Pronob Sarkar, Gourab Kumar Pranta, Mayen Uddin Mojumdar.
- DOI: 10.17632/cfchfdpfw5.1. Publisher lists CC BY 4.0.
- Source reports 4,518 Bangladesh images across fruit and leaf categories, including
  healthy fruit, insect-infected fruit, mealybugs/scale insects and sunburn damage.
- Fit: inspect fruit-only categories for existing manuscript requirements.
- Limitation: fungal infections combine Anthracnose or Stem Canker; these cannot
  be turned into separate verified diagnoses by renaming folders. Image files,
  actual class counts and annotations have not yet been inspected.

## 3. Stem disease — hold pending scope suitability

- Source: https://data.mendeley.com/datasets/v3brsrm2f7/1
- Contributor: Sushmoy Md Abu Rayhan Sushmoy. DOI: 10.17632/v3brsrm2f7.1.
- Publisher lists CC BY 4.0 and 724 images: Anthracnose, Brown Stem Spot, Gray Blight,
  Soft Rot, Stem Canker, Healthy; describes segmentation annotations.
- Images are of stems in Bangladesh. They do not validate diagnosis from a fruit
  crop. Do not add a stem-scanning feature or extra disease classes without approval.
- Downloaded contents and annotation quality have not been verified.

## Conditions before research use

Owner approval of a source is not expert validation of labels. Keep original
labels and source provenance; audit original images, duplicate/related groups,
background confounds and annotations before splitting or training. Use augmentation
only after splitting training data. Public data cannot substantiate the manuscript's
claim that the project team collected farm images in Philippine provinces. Any
replacement of that methodology or change of output classes needs an approved
manuscript revision. No model or manuscript changes were made during this search.
