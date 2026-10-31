# PitayaGrade: A Pre-Harvest Quality Grading and Disease Detection System for Dragon Fruit Using Machine Learning Techniques

---

**A Capstone Project**

Presented to the Faculty of the College of Information Technology

In Partial Fulfillment of the Requirements for the Degree of Bachelor of Science in Information Technology

---

**Academic Year 2025-2026**

---

## Table of Contents

- [Chapter 1: Introduction](#chapter-1-introduction)
  - [1.1 Background of the Study](#11-background-of-the-study)
  - [1.2 Problem Statement](#12-problem-statement)
  - [1.3 Objectives of the Study](#13-objectives-of-the-study)
  - [1.4 Significance of the Study](#14-significance-of-the-study)
  - [1.5 Scope and Limitations](#15-scope-and-limitations)
- [Chapter 2: Review of Related Literature and Systems](#chapter-2-review-of-related-literature-and-systems)
  - [2.1 Related Studies on Machine Learning in Agriculture](#21-related-studies-on-machine-learning-in-agriculture)
  - [2.2 Computer Vision in Fruit Grading](#22-computer-vision-in-fruit-grading)
  - [2.3 Disease Detection Systems](#23-disease-detection-systems)
  - [2.4 Comparative Analysis of Existing Systems vs. PitayaGrade](#24-comparative-analysis-of-existing-systems-vs-pitayagrade)
- [Chapter 3: Methodology](#chapter-3-methodology)
  - [3.1 Research Design](#31-research-design)
  - [3.2 System Architecture](#32-system-architecture)
  - [3.3 Data Collection](#33-data-collection)
  - [3.4 Image Processing Techniques](#34-image-processing-techniques)
  - [3.5 Machine Learning Model](#35-machine-learning-model)
  - [3.6 Training and Testing Process](#36-training-and-testing-process)
  - [3.7 Tools and Technologies](#37-tools-and-technologies)
  - [3.8 System Workflow](#38-system-workflow)
- [Chapter 4: System Design and Features](#chapter-4-system-design-and-features)
  - [4.1 Core Features](#41-core-features)
  - [4.2 Application Features](#42-application-features)
  - [4.3 Optional Advanced Features](#43-optional-advanced-features)
- [Chapter 5: Results and Discussion](#chapter-5-results-and-discussion)
  - [5.1 System Testing Results](#51-system-testing-results)
  - [5.2 Accuracy of the Machine Learning Model](#52-accuracy-of-the-machine-learning-model)
  - [5.3 Performance Evaluation](#53-performance-evaluation)
  - [5.4 Benefits Compared to Manual Grading](#54-benefits-compared-to-manual-grading)
- [Chapter 6: Conclusion and Recommendations](#chapter-6-conclusion-and-recommendations)
  - [6.1 Summary of Findings](#61-summary-of-findings)
  - [6.2 Impact on Agriculture](#62-impact-on-agriculture)
  - [6.3 Recommendations for Future Improvements](#63-recommendations-for-future-improvements)
- [References](#references)

---

## Abstract

Dragon fruit (*Hylocereus* spp.) quality grading and visible disease assessment commonly rely on manual inspection, which can vary between evaluators and operating conditions. This capstone project develops **PitayaGrade**, an Android-targeted decision-support application for capturing or uploading fruit images, running local ONNX inference, presenting image-based quality and disease estimates, saving scan history, generating analytics and reports, and issuing local notifications. The implemented Capacitor application packages a checksum-verified dragon-fruit presence gate, a YOLOv8-Nano detector/grader, and three selectable quality classifiers. The quality dataset contains 1,553 human-reviewed records with a frozen 226-image held-out test split. The selected EfficientNet-B3 classifier achieved 74.78% held-out accuracy and 58.51% macro F1; its ONNX predictions matched its PyTorch predictions on all 226 test images. Automated verification includes 112 JavaScript tests, 138 Python tests, ONNX Runtime checks, Android debug assembly, and Android lint. These results establish internal quality-model and software performance only. Disease segmentation, physical-device testing, user acceptance testing, and a signed release remain incomplete, so the study does not claim validated disease diagnosis, field effectiveness, or superiority over manual grading.

**Keywords:** dragon fruit, machine learning, computer vision, quality grading, disease detection, convolutional neural network, mobile application, Philippine agriculture

> **Evidence status (31 October 2026).** Human-reviewed quality data and exact
> held-out ONNX evaluation are complete. Chapter 5 reports those retained results.
> Disease-segmentation, physical-device, manual-comparison, and UAT values remain
> pending and must not be inferred from software tests or quality-classification
> results.

---

# Chapter 1: Introduction

## 1.1 Background of the Study

Agriculture remains the backbone of the Philippine economy, contributing approximately 9.6% of the national gross domestic product and employing roughly 24% of the workforce (Philippine Statistics Authority, 2024). Among the diverse crops cultivated in the archipelago, tropical fruits occupy a significant commercial position, catering both to domestic consumption and a growing export market across Asia, the Middle East, and Europe. In recent years, dragon fruit (*Hylocereus* spp.), locally known as *pitaya*, has gained considerable traction as a high-value crop due to its nutritional profile, visual appeal, and favorable profit margins for smallholder farmers.

Dragon fruit cultivation in the Philippines has expanded rapidly since the early 2010s, particularly in the provinces of Ilocos Norte, Ilocos Sur, La Union, Pangasinan, Quezon, and parts of Mindanao. The Department of Agriculture (DA) has actively promoted dragon fruit farming as part of its diversification strategy, recognizing its suitability for tropical climates and its relatively low water requirements compared to other fruit crops. According to the Philippine Council for Agriculture, Aquatic and Natural Resources Research and Development (PCAARRD), dragon fruit production in the country reached an estimated 12,500 metric tons in 2023, reflecting a compound annual growth rate of approximately 18% over the preceding five years.

Despite this encouraging growth trajectory, dragon fruit farming in the Philippines continues to face critical operational challenges, particularly in the areas of quality grading and disease management. Currently, the overwhelming majority of Filipino dragon fruit farmers rely on manual visual inspection to assess fruit quality before harvest. This process involves human evaluators examining individual fruits for attributes such as size, color uniformity, surface smoothness, blemishes, and visible signs of disease or pest damage. Quality grades are typically assigned based on the evaluator's subjective judgment and accumulated experience rather than standardized, quantifiable criteria.

Manual grading suffers from several well-documented limitations. First, it is inherently subjective; two evaluators may assign different grades to the same fruit based on individual perception and fatigue levels. Second, it is time-intensive, particularly during peak harvest seasons when thousands of fruits must be assessed within narrow time windows. Third, it offers limited diagnostic capability; while experienced farmers can identify common visual defects, they often lack the training or tools to detect early-stage diseases that have not yet manifested overtly visible symptoms. These limitations collectively result in inconsistent product quality, increased post-harvest losses estimated at 15-30% of total yield, and reduced competitiveness in premium domestic and export markets that demand uniform quality standards.

Simultaneously, dragon fruit crops in the Philippines are susceptible to a range of diseases and pest infestations that can significantly impair yield and quality. Common pathological conditions include anthracnose (*Colletotrichum gloeosporioides*), stem canker (*Neoscytalidium dimidiatum*), soft rot (*Erwinia* spp.), and sunburn damage. Fungal infections, in particular, can spread rapidly across plantations if not detected and addressed at early stages. Traditional disease detection methods rely on the farmer's ability to visually identify symptomatic patterns on the fruit surface or cladodes, a process that is unreliable for early-stage or atypical presentations.

The convergence of advances in artificial intelligence, specifically machine learning (ML) and computer vision, with the increasing ubiquity of smartphone technology presents a compelling opportunity to address these challenges. Machine learning algorithms, particularly Convolutional Neural Networks (CNNs), have demonstrated remarkable efficacy in image classification tasks across diverse domains, including medical imaging, industrial quality control, and agricultural applications. When applied to fruit grading and disease detection, CNN-based systems can analyze high-resolution images to extract and classify visual features with accuracy levels that meet or exceed those of trained human inspectors.

This capstone project introduces **PitayaGrade**, a mobile application-based system designed to automate pre-harvest quality grading and disease detection for dragon fruit using machine learning techniques. By harnessing the computational power of deep learning models and the accessibility of mobile technology, PitayaGrade aims to deliver a practical, scalable, and farmer-friendly tool that enhances decision-making in the field, reduces post-harvest losses, and supports the competitiveness of Philippine dragon fruit in domestic and international markets.

## 1.2 Problem Statement

The Philippine dragon fruit industry is experiencing rapid growth, yet it remains constrained by the limitations of manual quality grading and disease detection practices. Smallholder farmers, who constitute the majority of dragon fruit producers in the country, lack access to affordable, reliable, and standardized tools for assessing fruit quality and identifying pathological conditions prior to harvest. The resulting inefficiencies manifest in several interconnected problems:

1. **Inconsistent Quality Grading.** Manual visual inspection produces variable grading outcomes due to subjective evaluator judgment, environmental factors (lighting, evaluator fatigue), and the absence of standardized grading rubrics. This inconsistency undermines buyer confidence and limits access to premium market segments.

2. **Delayed Disease Detection.** Many dragon fruit diseases, particularly fungal infections such as anthracnose and stem canker, exhibit subtle early-stage symptoms that are difficult to detect through unaided visual inspection. By the time symptoms become overtly visible, the disease has often progressed to a stage where intervention is less effective and crop losses are substantial.

3. **High Post-Harvest Losses.** The combined effects of inaccurate grading and late disease detection contribute to estimated post-harvest losses of 15-30% of total yield. Diseased or improperly graded fruits that enter the supply chain result in buyer rejections, reduced prices, and reputational damage.

4. **Limited Scalability of Manual Processes.** As dragon fruit farms scale in response to market demand, the labor-intensive nature of manual grading becomes a bottleneck. Hiring additional inspectors increases operational costs without proportionally improving accuracy or speed.

5. **Lack of Digital Record-Keeping.** Most smallholder farmers do not maintain systematic records of grading outcomes, disease incidence, or quality trends over time. This absence of historical data impairs their ability to make informed decisions regarding crop management, market timing, and pest control strategies.

These problems collectively hinder the capacity of Filipino dragon fruit farmers to maximize their economic returns, meet the quality standards required by premium buyers, and manage crop health proactively rather than reactively. There exists a clear and actionable need for a technology-driven solution that can address these pain points in a cost-effective and accessible manner.

## 1.3 Objectives of the Study

### 1.3.1 General Objective

The general objective of this study is to develop **PitayaGrade**, a mobile-based pre-harvest quality grading and disease detection system for dragon fruit that utilizes machine learning and computer vision techniques to provide accurate, consistent, and rapid assessment of fruit quality and health status.

### 1.3.2 Specific Objectives

The specific objectives of this study are as follows:

1. To design and implement a Convolutional Neural Network (CNN) model capable of classifying dragon fruit into predefined quality grades (Grade A, Grade B, Grade C, and Reject) based on visual attributes including size, color, shape, and surface condition.

2. To develop a disease detection module that identifies common dragon fruit diseases and defects, including anthracnose, stem canker, soft rot, pest damage, sunburn, and fungal spots, from captured images with a target accuracy of at least 90%.

3. To build a mobile application interface that enables farmers to capture dragon fruit images using a smartphone camera and receive real-time grading and disease detection results.

4. To integrate an alert and notification system that warns farmers when diseases or quality issues are detected, enabling timely intervention.

5. To implement a digital record-keeping system that logs grading results, disease detections, and historical scan data for trend analysis and reporting.

6. To evaluate the performance of PitayaGrade in terms of classification accuracy, processing speed, and usability through systematic testing and comparison with manual grading methods.

7. To assess the system's potential impact on reducing post-harvest losses and improving the economic outcomes of dragon fruit farming in the Philippines.

## 1.4 Significance of the Study

The development and implementation of PitayaGrade holds significant value for multiple stakeholders across the Philippine agricultural ecosystem:

**Dragon Fruit Farmers.** The primary beneficiaries of PitayaGrade are smallholder dragon fruit farmers who currently depend on manual inspection for quality grading and disease detection. The system provides them with an accessible, smartphone-based tool that delivers objective, standardized grading results and early disease warnings. By reducing reliance on subjective judgment and enabling earlier detection of crop health issues, PitayaGrade empowers farmers to make more informed harvest and crop management decisions. This translates directly into reduced post-harvest losses, improved product quality, and enhanced bargaining power when negotiating with buyers and aggregators.

**Agricultural Extension Workers.** Government agricultural extension workers and local government unit (LGU) agriculture officers can leverage PitayaGrade as a diagnostic and advisory tool during farm visits. The system's ability to rapidly identify diseases supports more effective technical assistance and targeted recommendations, improving the overall quality of agricultural support services.

**Buyers, Aggregators, and Exporters.** Standardized grading outputs from PitayaGrade provide buyers and exporters with greater assurance regarding the quality and consistency of dragon fruit sourced from smallholder farms. This transparency can facilitate market access, reduce the incidence of buyer rejections, and support compliance with the quality requirements of domestic supermarket chains and international export markets.

**The Philippine Agriculture Industry.** At an industry level, PitayaGrade contributes to the broader digital transformation of Philippine agriculture. The system demonstrates the practical applicability of machine learning technology in a real-world farming context, providing a replicable model that can be adapted for other high-value crops such as mango, calamansi, and coffee. Furthermore, by improving the quality and consistency of Philippine dragon fruit, the system supports the country's competitiveness in the global tropical fruit market.

**Academic Researchers.** This capstone project contributes to the growing body of research on the application of artificial intelligence in tropical agriculture. The dataset, model architecture, and evaluation methodology documented in this study can serve as a reference for future researchers investigating machine learning-based solutions for fruit grading, disease detection, and precision agriculture in Southeast Asian contexts.

**The Local Community.** Enhanced farm productivity and reduced crop losses contribute to the economic well-being of rural communities where dragon fruit cultivation is a primary livelihood source. The ripple effects of improved farmer income include increased household spending, better access to education and healthcare, and stronger local economic activity.

## 1.5 Scope and Limitations

### 1.5.1 Scope

The scope of this capstone project encompasses the following:

1. **Crop Specificity.** PitayaGrade is designed exclusively for dragon fruit (*Hylocereus* spp.), focusing on the two most commercially cultivated varieties in the Philippines: white-fleshed (*Hylocereus undatus*) and red-fleshed (*Hylocereus polyrhizus*) dragon fruit.

2. **Assessment Focus.** The system performs two primary assessment functions: (a) quality grading based on visual attributes (size, color uniformity, surface smoothness, and visible defects), and (b) disease detection for common pathological conditions (anthracnose, stem canker, soft rot, pest damage, sunburn, and fungal spots).

3. **Pre-Harvest Context.** PitayaGrade is designed for pre-harvest assessment, meaning it evaluates dragon fruit while the fruit is still attached to or recently detached from the plant. The system is not designed for post-harvest quality control in packing houses or distribution centers.

4. **Platform.** The system is developed as a mobile application using the Capacitor framework targeting Android devices, reflecting the dominant mobile operating system among Philippine farmers.

5. **Machine Learning Architecture.** The implemented quality pipeline uses a dragon-fruit presence gate, YOLOv8-Nano localization, and selectable MobileNetV2, ResNet50, or EfficientNet-B3 quality grading. The application still uses heuristic disease analysis because the planned YOLOv8-Nano disease-segmentation role lacks reviewed masks and an evaluated export.

6. **Dataset.** The repository retains frozen, checksum-bound manifests for 1,553 reviewed quality records and 1,497 reviewed maturity records. The public-data provenance does not establish Philippine field representativeness, and reviewed disease-region annotations remain incomplete.

7. **Connectivity.** The active application performs local ONNX Runtime Web inference and local record storage. It does not currently use a production cloud inference service or TensorFlow Lite backend. The Offline Mode setting communicates the local-processing preference; it does not switch between cloud and TFLite models.

### 1.5.2 Limitations

The following limitations are acknowledged:

1. **Disease Coverage.** The disease detection module is limited to the six most common visual diseases and defects identified in the dataset. Rare or atypical diseases not represented in the training data may not be accurately detected.

2. **Internal Quality Assessment.** PitayaGrade assesses only external visual attributes of dragon fruit. Internal quality factors such as sweetness (Brix level), flesh texture, and seed density cannot be evaluated through image analysis alone and are therefore excluded from the system's grading criteria.

3. **Image Quality Dependency.** The accuracy of the system is contingent upon the quality of the input image. Images captured in poor lighting conditions, at extreme angles, or with significant motion blur may yield less reliable classification results.

4. **Hardware Requirements.** While designed for accessibility, the system requires a smartphone with a camera resolution of at least 8 megapixels and sufficient processing capability to run TensorFlow Lite models. Farmers using older or lower-specification devices may experience reduced performance.

5. **Environmental Factors.** The model's performance may be influenced by environmental variables such as ambient lighting, weather conditions, and background complexity at the time of image capture. The system includes basic preprocessing to mitigate these factors but cannot fully eliminate their influence.

6. **Generalizability.** The final reviewed training distribution and field performance are not yet established. Results from public candidate images or controlled captures must not be generalized to Philippine farms, cultivars or growing conditions without field evaluation.

7. **Not a Replacement for Expert Diagnosis.** PitayaGrade is designed as a decision-support tool, not a replacement for professional phytopathological diagnosis. Farmers are advised to consult agricultural extension officers or plant pathologists for confirmation of detected diseases, particularly in cases where the system's confidence score is below the recommended threshold.

---

# Chapter 2: Review of Related Literature and Systems

## 2.1 Related Studies on Machine Learning in Agriculture

The application of machine learning (ML) to agricultural problems has expanded significantly over the past decade, driven by advances in computational hardware, the availability of large annotated datasets, and the development of increasingly sophisticated deep learning architectures. This section reviews key studies that have applied ML techniques to agricultural classification, detection, and prediction tasks, with particular attention to those relevant to the objectives of PitayaGrade.

**Kamilaris and Prenafeta-Boldu (2018)** conducted a comprehensive survey of deep learning applications in agriculture, reviewing over 40 studies spanning crop type classification, disease detection, weed identification, and yield prediction. Their findings indicated that Convolutional Neural Networks (CNNs) consistently outperformed traditional machine learning methods (such as Support Vector Machines and Random Forests) in image-based agricultural tasks, achieving accuracy rates exceeding 90% in most reported experiments. The authors noted that transfer learning, the practice of fine-tuning pre-trained CNN models on domain-specific datasets, was particularly effective in scenarios where labeled training data was limited, a condition commonly encountered in agricultural applications.

**Mohanty, Hughes, and Salathe (2016)** developed a deep learning-based plant disease identification system using the PlantVillage dataset, which contained over 54,000 images of healthy and diseased plant leaves across 14 crop species. Employing GoogLeNet and AlexNet architectures, their system achieved a classification accuracy of 99.35% under controlled laboratory conditions. However, the authors acknowledged that performance degraded when the model was applied to images captured in uncontrolled field conditions, highlighting the importance of training data diversity and robust preprocessing pipelines.

**Ferentinos (2018)** extended this work by training multiple CNN architectures, including VGG, ResNet, AlexNet, and GoogLeNet, on an expanded version of the PlantVillage dataset comprising 87,848 images. The best-performing model, a VGG variant, achieved 99.53% accuracy on the validation set. Ferentinos emphasized that model performance on laboratory images did not necessarily translate to field conditions and recommended the development of mobile-deployable models that could operate in real-world agricultural settings.

**Liakos, Busato, Moshou, Pearson, and Bochtis (2018)** reviewed machine learning applications across four major agricultural domains: crop management, livestock management, water management, and soil management. The study highlighted that while ML adoption was advancing in large-scale commercial farming contexts, uptake among smallholder farmers in developing countries remained limited due to infrastructure constraints, data availability issues, and the lack of user-friendly interfaces. This observation directly informs the design philosophy of PitayaGrade, which prioritizes mobile accessibility and ease of use.

**Barbedo (2019)** examined the specific challenges of applying deep learning to plant disease detection in tropical and developing-country contexts. The study identified several recurring issues: class imbalance (diseases of interest being underrepresented in training data), high intra-class variability (the same disease presenting differently across cultivars, growth stages, and environmental conditions), and the difficulty of collecting high-quality labeled datasets under field conditions. Barbedo recommended the use of data augmentation, transfer learning, and ensemble methods to address these challenges, strategies that are adopted in the PitayaGrade methodology.

## 2.2 Computer Vision in Fruit Grading

Computer vision-based fruit grading systems have been the subject of extensive research, spanning a diverse range of fruit types and quality assessment criteria. The underlying premise of these systems is that visual attributes, including color, size, shape, texture, and surface defects, can be quantified through image analysis and used as the basis for automated quality classification.

**Naik and Patel (2017)** developed an automated fruit grading system for mangoes using image processing and machine learning. Their system employed color histogram analysis, shape descriptors, and texture features extracted through the Gray-Level Co-occurrence Matrix (GLCM) to classify mangoes into three quality grades. Using a Support Vector Machine (SVM) classifier, the system achieved 89.4% accuracy. The study demonstrated the feasibility of computer vision-based grading for tropical fruits and identified color uniformity and surface defect detection as the most discriminative features.

**Soares, Machado, Silva, and Souza (2020)** proposed a deep learning framework for citrus fruit grading that utilized a custom CNN architecture to classify oranges into five quality categories based on size, color, and surface condition. The system achieved 93.2% accuracy on a dataset of 4,200 images and processed each image in under 1.5 seconds on a standard GPU workstation. The authors noted that their model's performance was sensitive to variations in lighting and recommended the incorporation of image normalization techniques to improve robustness.

**Sa, Ge, Dayoub, Upcroft, Perez, and McCool (2016)** developed a multimodal deep learning system for fruit detection in orchards, combining RGB and near-infrared (NIR) imagery to detect sweet peppers in cluttered agricultural environments. While not directly focused on grading, the study demonstrated that multi-spectral imaging could enhance the detection of subtle visual features relevant to quality assessment, a finding that informs potential future extensions of PitayaGrade.

**Le, Pham, Dang, and Le (2020)** applied transfer learning using the InceptionV3 architecture to classify dragon fruit quality based on external appearance. Their study, conducted in Vietnam, used a dataset of 2,400 dragon fruit images manually labeled into three grades: premium, standard, and reject. The model achieved 95.1% classification accuracy after fine-tuning and data augmentation. This study is directly relevant to PitayaGrade, as it validates the applicability of deep learning to dragon fruit quality grading and informs the selection of visual features for the PitayaGrade classification pipeline.

**Zhang, Jia, Li, and Zhou (2021)** proposed a lightweight CNN architecture for real-time fruit grading on edge devices, specifically targeting deployment on mobile phones and embedded systems. By employing depthwise separable convolutions and model quantization, the authors achieved a 5x reduction in model size with less than 2% degradation in accuracy. This work directly influenced the selection of lightweight architectures (YOLOv8-Nano and EfficientNet-B3) for PitayaGrade, given the requirement for efficient dual-stage inference on farmer smartphones.

## 2.3 Disease Detection Systems

Automated disease detection in crops has been a particularly active area of machine learning research, driven by the economic imperative to reduce crop losses and the recognition that early detection enables more effective intervention.

**Sladojevic, Arsenovic, Anderla, Culibrk, and Stefanovic (2016)** developed a deep learning solution for the recognition of plant diseases from leaf images. Using a CNN architecture trained on a dataset of approximately 3,000 images spanning 13 disease categories across multiple plant species, the system achieved an average recognition accuracy of 96.3%. The study validated the effectiveness of deep learning for multi-class disease classification and demonstrated that CNNs could distinguish between visually similar diseases that are challenging for human inspectors.

**Ramcharan, Baranowski, McCloskey, Ahmed, Legg, and Hughes (2017)** applied transfer learning to detect cassava diseases in field conditions in Tanzania. Using the Inception V3 architecture fine-tuned on a dataset of cassava leaf images captured by farmers using smartphone cameras, the system achieved classification accuracies ranging from 91% to 98% across five disease categories. This study is particularly relevant to PitayaGrade because it demonstrated the viability of smartphone-based disease detection in a developing-country smallholder farming context, closely analogous to the target deployment environment in the Philippines.

**Nguyen, Ngo, Le, and Pham (2021)** developed a disease detection system specifically for dragon fruit, focusing on the identification of stem canker (*Neoscytalidium dimidiatum*), the most economically significant disease affecting dragon fruit cultivation in Southeast Asia. Using a dataset of 1,800 images and a ResNet-50 architecture, the system achieved 92.4% accuracy in distinguishing between healthy and infected cladodes. The study highlighted the importance of capturing images at multiple disease progression stages to enable early detection, a principle incorporated into the PitayaGrade data collection strategy.

**Saleem, Potgieter, and Arif (2019)** provided a comprehensive review of plant disease detection and classification techniques, comparing traditional image processing approaches (color thresholding, edge detection, texture analysis) with deep learning methods. Their analysis concluded that while traditional methods could achieve satisfactory results for simple binary classification tasks (healthy vs. diseased), deep learning methods were significantly superior for multi-class disease classification, species-agnostic generalization, and detection of subtle or early-stage symptoms.

**Tm, Pranathi, SaiAshrworkkumar, Chandra, and Reddy (2018)** applied VGG16 and ResNet architectures to detect diseases in tomato plants, achieving accuracies of 94.6% and 96.1%, respectively. Notably, the study incorporated a heatmap visualization technique (Grad-CAM) that highlighted the image regions most influential in the model's classification decision. This interpretability feature enhanced user trust in the system's outputs, an insight that informs the development of explainability features in PitayaGrade.

## 2.4 Comparative Analysis of Existing Systems vs. PitayaGrade

To contextualize the contribution of PitayaGrade within the existing landscape of agricultural machine learning systems, this section presents a comparative analysis of relevant existing systems against the features and capabilities of PitayaGrade.

| Feature / Criterion | Le et al. (2020) Dragon Fruit Grading | Nguyen et al. (2021) Dragon Fruit Disease Detection | Ramcharan et al. (2017) Cassava Disease Detection | PlantVillage (Mohanty et al., 2016) | **PitayaGrade** |
|---|---|---|---|---|---|
| **Target Crop** | Dragon fruit | Dragon fruit | Cassava | Multiple (14 species) | **Dragon fruit** |
| **Quality Grading** | Yes (3 grades) | No | No | No | **Yes (4 grades)** |
| **Disease Detection** | No | Yes (1 disease) | Yes (5 diseases) | Yes (26 diseases) | **Yes (6 diseases/defects)** |
| **Combined Grading + Disease** | No | No | No | No | **Yes** |
| **Mobile Application** | No | No | Yes (basic) | Yes (demo only) | **Yes (full-featured)** |
| **Offline Capability** | No | No | No | No | **Yes (local ONNX/WASM; device verification pending)** |
| **Real-Time Alerts** | No | No | No | No | **Yes** |
| **Digital Record-Keeping** | No | No | No | No | **Yes** |
| **Cloud Integration** | No | No | No | Partial | **No (proposed only)** |
| **Analytics Dashboard** | No | No | No | No | **Yes** |
| **Pre-Harvest Focus** | No (post-harvest) | Yes | Yes | Lab-based | **Yes** |
| **Philippine Context** | No (Vietnam) | No (Vietnam) | No (Tanzania) | No (Global) | **Yes** |
| **CNN Architecture** | InceptionV3 | ResNet-50 | InceptionV3 | GoogLeNet/AlexNet | **YOLOv8 deployed; dual-stage pipeline proposed** |
| **Reported Accuracy** | 95.1% | 92.4% | 91-98% | 99.35% | **Evaluation pending** |

**Table 2.1.** Comparative Analysis of Existing Systems vs. PitayaGrade

The comparative analysis reveals that PitayaGrade is distinguished from existing systems by its integration of both quality grading and disease detection within a single platform, its comprehensive mobile application with full-featured capabilities (offline mode, alerts, record-keeping, analytics), and its specific design orientation toward the Philippine dragon fruit farming context. While individual existing systems have achieved comparable or higher accuracy in their specific task domains, none offers the holistic, farmer-centric solution architecture that characterizes PitayaGrade.

---

# Chapter 3: Methodology

## 3.1 Research Design

This capstone project employs an **applied research design** combining developmental and experimental approaches. The developmental component involves the systematic design, construction, and iterative refinement of the PitayaGrade system, encompassing the machine learning model, image processing pipeline, and mobile application interface. The experimental component involves the controlled evaluation of the system's performance through structured testing protocols that measure classification accuracy, processing speed, and user acceptance.

The research process follows the **Agile Software Development Life Cycle (SDLC)** methodology, which supports iterative development, continuous testing, and incremental feature delivery. This approach is particularly suited to projects integrating machine learning components, where model training and evaluation cycles often reveal insights that necessitate adjustments to data collection, preprocessing, or architectural decisions.

## 3.2 System Architecture

The implemented PitayaGrade prototype follows a **local-first Capacitor architecture**. The client and packaged ONNX runtime are active; the server components described below remain proposed extensions rather than deployed services.

### 3.2.1 Client Layer (Mobile Application)

The client layer consists of an Android mobile application developed using **Capacitor**, a hybrid mobile framework that enables deployment of web applications across diverse Android device specifications. The client layer is responsible for:

- Providing the user interface for image capture, result display, history browsing, and dashboard visualization.
- Performing image preprocessing (resizing, normalization, orientation correction) prior to inference.
- Executing local inference through ONNX Runtime Web and its bundled WASM backend.
- Keeping scan records and settings in browser `localStorage` within the Capacitor WebView.
- Providing a user preference for local/offline processing without uploading scan metadata.

### 3.2.2 Server Layer (Cloud Backend)

The server layer is a proposed future component and is not present in the active application. A future implementation could provide:

- A RESTful API endpoint for receiving image uploads and returning classification results.
- The full-resolution model for high-accuracy inference.
- User authentication and account management.
- Cloud database (Firebase Firestore) for persistent storage of scan records, user profiles, and aggregated analytics data.
- Push notification services for alerts and recommendations.

### 3.2.3 Model Layer (Machine Learning Pipeline)

The model layer distinguishes implemented and intended components:

- A checksum-verified MobileNetV3-Small presence gate that rejects non-dragon-fruit input before grading.
- A bundled YOLOv8-Nano ONNX detector/grader used to localize plausible fruit regions.
- Selectable MobileNetV2, ResNet50 and EfficientNet-B3 quality classifiers evaluated on the same frozen 226-image test split.
- A registered but unavailable disease-segmentation role awaiting reviewed disease-region masks and an evaluated export.
- Preprocessing and postprocessing modules that standardize input images and format output predictions.
- A checksum-verified model registry that prevents missing or altered files from being presented as selectable. Over-the-air updates are not implemented.

```
System Architecture Diagram

+-----------------------------------------------------------+
|                CAPACITOR ANDROID APPLICATION              |
|                                                           |
|  Camera / upload -> crop and orientation -> pixel input   |
|                         |                                 |
|                 Dragon-fruit presence gate                |
|                         | accepted                        |
|                 YOLOv8 fruit localization                 |
|                         | fruit crop                      |
|       Selectable quality classifier (MobileNetV2,         |
|             ResNet50, or EfficientNet-B3)                 |
|                         |                                 |
|       Grade result, human validation, history, reports    |
|                                                           |
|  ONNX Runtime Web/WASM | localStorage | local alerts      |
+-----------------------------------------------------------+
                             |
                  No cloud inference required
                             |
              +--------------v----------------+
              | Future evaluated disease model|
              | (currently unavailable)       |
              +-------------------------------+
```

**Figure 3.1.** PitayaGrade System Architecture

## 3.3 Data Collection

### 3.3.1 Data Sources

Dataset preparation uses traceable public candidate images and retains source URLs, source groups, and file/pixel hashes. The retained quality and maturity collection contains 3,050 reviewed records.

1. **Primary Field Collection (Pending).** No retained manifest supports the previously drafted claim of 3,200 images from named provinces, devices and harvest cycles. Any original field images must be accompanied by collection permission, location/date metadata, source grouping and checksums before inclusion.

2. **Reviewed Public Candidate Data.** Team review finalized 1,553 quality records and 1,497 maturity records. Validation found no missing target labels or checksum errors in the frozen manifests.

3. **External Feature-Pretraining Data.** A 1,667-image public Good/Medium/Bad collection was audited against every frozen quality image using file hashes, decoded-pixel hashes, dHash, and aHash. The audit excluded 583 overlapping records and four internal duplicates, leaving 1,080 independent Good/Medium records. These labels initialized visual features only and were never converted into Grade A/B/C/Reject ground truth. The publisher states CC BY 4.0, but the rights of every underlying online image were not independently verified.

4. **Data Augmentation.** The training loader applies augmentation only to the training partition:
   - Horizontal and vertical flipping
   - Random rotation (0-30 degrees)
   - Random brightness adjustment (plus or minus 15%)
   - Random contrast adjustment (plus or minus 10%)
   - Deterministic resizing to 224 x 224 pixels

   Augmented views are not counted as independent images or evaluation evidence.

### 3.3.2 Labeling and Annotation

The frozen manifests retain the reviewer identifier, review time, source-fruit group, target label, split, and checksums required for quality and maturity training. Disease-region polygons remain incomplete and therefore cannot support a final disease-segmentation model.

**Quality Grade Labels:**
- **Grade A (Premium):** Well-formed fruit with uniform coloring, smooth surface, no visible blemishes, diameter greater than or equal to 10 cm.
- **Grade B (Standard):** Minor cosmetic imperfections (slight color variation, small surface marks), diameter 7-10 cm.
- **Grade C (Economy):** Noticeable cosmetic defects (uneven color, surface scarring), diameter 5-7 cm, but no disease symptoms.
- **Reject:** Severe defects, deformation, or confirmed disease symptoms rendering the fruit unsuitable for sale.

**Disease/Defect Labels:**
- Healthy
- Anthracnose
- Stem Canker
- Soft Rot
- Pest Damage
- Sunburn
- Fungal Spots

Inter-rater reliability has not yet been measured. It should be calculated only from independently retained reviewer decisions on the same samples.

### 3.3.3 Dataset Split

The frozen 1,553-image quality manifest contains 1,096 training images, 231 validation images, and 226 held-out test images. Model selection and early stopping use validation loss. The test partition is reserved for final comparison.

The validation tools reject exact pixel duplicates and shared source groups across partitions. The external pretraining audit additionally excludes exact and conservative perceptual matches against all frozen partitions.

## 3.4 Image Processing Techniques

Image preprocessing is a critical pipeline stage that standardizes input images to improve model accuracy and robustness. The PitayaGrade preprocessing pipeline comprises the following sequential steps:

1. **Image Resizing.** The presence gate uses 160 x 160 input, the YOLOv8-Nano detector/grader uses 640 x 640 input, and the selectable quality classifiers use 224 x 224 fruit crops. Bilinear interpolation is used for classifier preprocessing.

2. **Color Normalization.** YOLO input uses RGB values scaled to [0, 1]. The presence gate and quality classifiers use ImageNet channel means and standard deviations to match their pretrained torchvision weights.

3. **Fruit Localization.** The runtime accepts grading only after the presence gate and visual plausibility checks pass. The detector crop, rather than the full scene, is supplied to the selected quality classifier.

4. **Photo Adjustment.** Photo mode lets the user crop, zoom, and rotate an uploaded image before analysis. The application does not apply an unverified CLAHE or GrabCut stage during deployed inference.

5. **Fail-Closed Rejection.** Empty scenes and non-fruit objects are rejected before any grade is shown. Live mode also requires three consecutive accepted frames.

6. **Orientation Correction.** EXIF metadata is read to correct for device orientation, ensuring all images are processed in a consistent upright orientation regardless of how the smartphone was held during capture.

## 3.5 Machine Learning Model

### 3.5.1 Architecture Selection

The implemented PitayaGrade quality pipeline uses **YOLOv8-Nano** (Jocher et al., 2023) for localization and a selectable **EfficientNet-B3**, ResNet50, or MobileNetV2 classifier. EfficientNet-B3 currently has the highest retained held-out accuracy. The selection is based on the following criteria:

1. **Computational Efficiency & Local Edge Deployment.** YOLOv8-Nano is a lightweight state-of-the-art object detection and segmentation model with approximately 3.2 million parameters, allowing it to perform fast real-time inference on edge devices. EfficientNet-B3 uses compound scaling to optimize accuracy and efficiency, possessing approximately 12 million parameters, which is suitable for standard mobile processors.

2. **Transfer Learning Compatibility.** Both models utilize weights pre-trained on large-scale datasets (COCO for YOLOv8 and ImageNet for EfficientNet-B3), providing a robust starting point for fine-tuning on the smaller, specific PitayaGrade dataset and mitigating overfitting.

3. **Local Runtime Compatibility.** The exported ONNX files execute through the bundled ONNX Runtime Web/WASM backend in the Capacitor application.

4. **Demonstrated Performance.** Prior research has demonstrated that YOLOv8 achieves high precision for region proposal and disease segmentation, while EfficientNet-B3 outperforms standard CNNs on quality grading classification through balanced depth, width, and resolution scaling.

### 3.5.2 Model Configuration

The dual-stage pipeline is configured as follows:

- **Stage 1 (Object Detection & Region of Interest):** A YOLOv8-Nano model detects the dragon fruit in the image frame and outputs a bounding box (Region of Interest) containing only the fruit.
- **Stage 2A (Disease Segmentation, Pending):** The registry reserves a YOLOv8-Seg role, but the application does not enable it without reviewed disease masks, held-out evaluation, and a checksum-verified export.
- **Stage 2B (Compound Quality Grading):** An EfficientNet-B3 model classifies the Region of Interest into three quality grades (Grade A, Grade B, Grade C) or Reject, utilizing a custom head consisting of: Global Average Pooling -> Dropout (0.3) -> Dense (128, ReLU) -> Batch Normalization -> Dropout (0.2) -> Dense (4, Softmax).

### 3.5.3 Transfer Learning Strategy

A two-phase transfer learning strategy is defined for reviewed training runs:

- **Phase 1 - Feature Extraction (10 epochs):** The base layers of YOLOv8-Nano and EfficientNet-B3 are frozen, and only the custom heads and segmentation/classification layers are trained, allowing them to adapt to the PitayaGrade classes.
- **Phase 2 - Fine-Tuning (30 epochs):** The higher layers of both base networks are unfrozen and trained jointly with the heads at a reduced learning rate (1e-5) to adapt high-level feature representations to specific dragon fruit textures and visual defect patterns.

## 3.6 Training and Testing Process

### 3.6.1 Training Configuration

Reviewed model runs are intended to use the following configuration; each completed run must retain its exact context and dependency versions:

| Parameter | Value |
|---|---|
| **Optimizer** | Adam (beta_1=0.9, beta_2=0.999) |
| **Learning Rate** | Phase 1: 1e-3; Phase 2: 1e-5 |
| **Learning Rate Schedule** | ReduceLROnPlateau (patience=5, factor=0.5) |
| **Batch Size** | 32 |
| **Loss Function** | Categorical Cross-Entropy / Box Loss |
| **Regularization** | Dropout (0.2-0.3), L2 weight decay (1e-4) |
| **Early Stopping** | Patience=10 epochs, monitor=val_loss |
| **Hardware** | NVIDIA GeForce RTX 3050 for the retained external-pretraining runs |
| **Framework** | PyTorch / torchvision, ONNX Runtime, Ultralytics where applicable |

**Table 3.1.** Training Configuration Parameters

### 3.6.2 Evaluation Metrics

Model performance is evaluated using the following metrics:

1. **Accuracy:** The proportion of correctly classified images across all classes.
2. **Precision:** The proportion of true positive predictions among all positive predictions for each class.
3. **Recall (Sensitivity):** The proportion of true positive predictions among all actual positive instances for each class.
4. **F1-Score:** The harmonic mean of precision and recall, providing a balanced measure of classification performance.
5. **Confusion Matrix:** A tabular visualization of predicted vs. actual class assignments to identify systematic misclassification patterns.
6. **AUC-ROC:** The Area Under the Receiver Operating Characteristic curve for each class, measuring the model's discriminative ability across classification thresholds.
7. **Inference Time:** The average time required to process a single image from input to output prediction.

### 3.6.3 Cross-Validation

Five-fold stratified cross-validation remains a proposed robustness check. If performed, folds must preserve source-fruit grouping and remain separate from the untouched test set; otherwise no cross-validation result should be reported.

## 3.7 Tools and Technologies

The development of PitayaGrade leverages the following tools and technologies:

| Category | Technology | Purpose |
|---|---|---|
| **Programming Language** | Python 3.10 | ML model development, data processing |
| **ML Framework** | TensorFlow 2.12 / Keras | Model architecture, training, evaluation |
| **Model Deployment** | ONNX Runtime Web/WASM | Local inference in Capacitor Android |
| **Computer Vision** | OpenCV 4.7 | Image preprocessing, segmentation |
| **Data Augmentation** | Albumentations | Advanced image augmentation pipeline |
| **Annotation Tool** | LabelImg | Image labeling and annotation |
| **Mobile Framework** | Capacitor 6.0 (HTML/CSS/JS) | Android mobile application development |
| **Backend** | None in active application | Future extension only |
| **Cloud Platform** | None in active application | Future extension only |
| **Database** | Browser localStorage | Local scan records and settings |
| **Local Database** | Browser localStorage | Maximum 500 scan records |
| **Notifications** | In-app notification center | Local alerts and session summaries |
| **Version Control** | Git / GitHub | Source code management |
| **IDE** | Visual Studio Code, Google Colab | Development and model training |
| **Testing** | Node test runner, Python unittest, Android lint | Unit, integration and build checks |
| **UI/UX Design** | Figma | Application interface design |

**Table 3.2.** Tools and Technologies

## 3.8 System Workflow

The PitayaGrade system follows a structured workflow from image capture to result delivery. The step-by-step process is detailed below:

**Step 1: Image Capture.** The farmer opens the PitayaGrade mobile application and uses the built-in camera module to capture an image of the dragon fruit to be assessed. The camera module includes a viewfinder overlay guide that assists the farmer in framing the fruit correctly.

**Step 2: Image Preprocessing.** The deployed path resizes pixels and normalizes RGB values for the bundled ONNX model. Research preprocessing previews for segmentation, lighting correction and selective filtering exist separately and are not yet part of deployed inference. Phone timing remains unmeasured.

**Step 3: Local Inference.** The active application loads the selected checksum-verified ONNX asset and executes it through the bundled WASM runtime. It does not upload the image to a cloud inference server.

**Step 4: Quality Grading Inference.** The preprocessed image is fed into the quality grading CNN model, which outputs a probability distribution across the four quality grade classes. The class with the highest probability is assigned as the predicted grade, along with a confidence score.

**Step 5: Disease Estimate.** Until an evaluated disease-segmentation ONNX model is supplied, the active application uses image heuristics and presents possible visual signs for physical or expert verification.

**Step 6: Result Generation.** The system combines the quality grading and disease detection outputs into a unified result report that includes:
- Assigned quality grade (A, B, C, or Reject)
- Confidence score for the assigned grade
- Detected disease or defect (if any)
- Confidence score for the detected disease
- Recommended actions (e.g., "Monitor for anthracnose progression," "Harvest immediately for Grade B market")

**Step 7: Alert Generation.** Qualifying grade or possible-disease results create local in-app alerts. The wording explicitly requires verification; no remote push service is active.

**Step 8: Record Storage.** Recognized scans store a thumbnail, timestamp, estimates, model/method metadata, recommendations and notes in local browser storage. No GPS or cloud synchronization is active.

**Step 9: Dashboard Update.** Aggregated scan data is processed and displayed on the analytics dashboard, providing the farmer with insights into grading distributions, disease prevalence trends, and productivity metrics over time.

```
System Workflow Diagram

+------------------+     +--------------------+     +-------------------+
| Step 1:          |     | Step 2:            |     | Step 3:           |
| Image Capture    +---->+ Image Preprocessing+---->+ Mode Selection    |
| (Camera Module)  |     | (Resize, Normalize,|     | (Online/Offline)  |
+------------------+     |  Segment, Correct) |     +--------+----------+
                         +--------------------+              |
                                                   +---------+---------+
                                                   |                   |
                                          +--------v------+   +-------v--------+
                                          | Online Mode   |   | Offline Mode   |
                                          | (Cloud API)   |   | (TFLite)       |
                                          +--------+------+   +-------+--------+
                                                   |                   |
                                                   +---------+---------+
                                                             |
                                              +--------------v--------------+
                                              |                             |
                                     +--------v--------+    +---------v--------+
                                     | Step 4:         |    | Step 5:          |
                                     | Quality Grading |    | Disease Detection|
                                     | (CNN Model)     |    | (CNN Model)      |
                                     +--------+--------+    +--------+---------+
                                              |                      |
                                              +----------+-----------+
                                                         |
                                              +----------v-----------+
                                              | Step 6:              |
                                              | Result Generation    |
                                              | (Grade + Disease +   |
                                              |  Recommendations)    |
                                              +----------+-----------+
                                                         |
                                    +--------------------+--------------------+
                                    |                    |                    |
                           +--------v------+   +---------v-------+  +--------v--------+
                           | Step 7:       |   | Step 8:         |  | Step 9:         |
                           | Alert         |   | Record Storage  |  | Dashboard       |
                           | Generation    |   | (SQLite/Cloud)  |  | Update          |
                           +---------------+   +-----------------+  +-----------------+
```

**Figure 3.2.** PitayaGrade System Workflow

---

# Chapter 4: System Design and Features

This chapter provides a comprehensive description of the PitayaGrade system's features, organized into three categories: core features that constitute the system's primary functionality, application features that enhance the user experience and operational utility, and optional advanced features that extend the system's capabilities for future development.

## 4.1 Core Features

### 4.1.1 AI-Based Image Analysis

PitayaGrade's implemented image-analysis engine accepts a captured or uploaded image, applies the checksum-verified presence and localization gates, runs the selected quality ONNX asset locally, and presents the result with its method and limitations. The package contains three evaluated selectable quality classifiers plus clearly labeled image heuristics for disease-related visual cues. No retained evaluation shows that this implementation surpasses manual inspection.

The implemented quality architecture is a multi-stage presence-gate and detector-to-crop pipeline with selectable MobileNetV2, ResNet50, and EfficientNet-B3 classifiers. The separate YOLOv8-Nano disease-segmentation role remains unavailable until reviewed masks, held-out evaluation, a compatible ONNX export, and checksums exist.

The engine is designed with a modular architecture that allows individual components, such as the preprocessing pipeline or the classification models, to be updated or replaced independently. This modularity ensures that PitayaGrade can evolve alongside advances in machine learning techniques and expand to accommodate new quality criteria or disease categories as they become relevant.

### 4.1.2 Automatic Quality Grading

The active models return one of four reviewed grade labels for a recognized fruit. The retained internal held-out evaluation measures image classification against those labels, while final decisions still require human validation. The grading criteria are:

**Size Assessment.** Physical size is not measured by the active application. A single uncalibrated image cannot establish fruit dimensions, so current records display size as not measured.

**Color Analysis.** The selected ONNX classifier analyzes the detector-localized RGB fruit crop. It does not establish internal flesh variety from an exterior photograph.

**Surface Condition Evaluation.** The quality classifier uses image-derived surface cues learned from reviewed labels. Grade A and Grade C remain the weakest held-out classes, so cosmetic and structural interpretation still requires human review.

**Shape Analysis.** The detector produces a fruit region used by the visual gate. Shape conformity is a proposed grading factor rather than a separately validated active measurement.

The interface preserves the model score and detection threshold for transparency. That score is not a calibrated probability of grade correctness and must not be interpreted as research accuracy.

### 4.1.3 Disease Detection

The planned disease-segmentation task contains six visible symptom or defect categories. The active application does not yet run an evaluated disease model; it presents heuristic visual cues for inspection instead of confirmed diagnoses.

**Anthracnose (*Colletotrichum gloeosporioides*).** This target category covers reviewed visible symptoms such as circular, sunken lesions with dark brown to black coloring. No early-stage detection claim has been validated.

**Stem Canker (*Neoscytalidium dimidiatum*).** Stem canker produces chlorotic (yellowed) spots that progress to necrotic lesions with a characteristic bleached center surrounded by a dark margin. While primarily a cladode disease, stem canker can affect fruit surfaces and pedicles, compromising fruit quality and shelf life.

**Soft Rot (*Erwinia* spp.).** This target category covers expert-reviewed visible soft-rot cues. The application has not established pathogen identity or early-stage sensitivity from images.

**Pest Damage.** Visible damage from common dragon fruit pests, including mealybugs, scale insects, and fruit flies, is detected based on characteristic feeding marks, frass deposits, and surface deformations. Pest damage patterns are typically distinguished from disease symptoms by their mechanical, irregular appearance.

**Sunburn.** Excessive solar exposure causes bleached, whitened, or brownish patches on the sun-exposed surface of the fruit. While sunburn is not a pathological condition, it significantly affects the fruit's market grade and aesthetic appeal.

**Fungal Spots.** General fungal infections that produce discrete spots, patches, or discolorations on the fruit surface are classified under this category. This serves as a broad detection class for fungal pathogens not specifically covered by the anthracnose or stem canker categories.

### 4.1.4 Early Disease Identification

The prototype can flag visible color and surface patterns for inspection, but it has not been trained or validated to identify pre-symptomatic or early-stage disease. Early-detection performance must not be claimed without reviewed longitudinal examples and expert ground truth.

No separate early-identification model or lower-threshold disease workflow is enabled. A future implementation may provide a cautious monitor recommendation, but only after an approved protocol evaluates false positives and early-stage sensitivity.

No retained expert-reviewed early-stage subset currently supports that claim. Future work should define symptom onset, review labels with qualified agricultural experts and evaluate early-stage sensitivity separately from general disease performance.

### 4.1.5 Machine Learning Model Integration

PitayaGrade currently uses local ONNX Runtime Web inference inside the Capacitor application. Cloud/TensorFlow Lite descriptions below are retained only as proposed alternatives and are not active processing paths.

**Cloud Model (Proposed).** No production cloud model, REST inference API or server-side credential service is deployed.

**On-Device Model (Implemented).** The application packages an ONNX file and ONNX Runtime Web/WASM assets. No evaluated TensorFlow Lite model or measured quantization comparison is retained.

**Model Governance.** A static registry records each planned model's role, input size, output contract, availability and checksum. Models are delivered with an application build; an OTA update mechanism is not implemented.

## 4.2 Application Features

### 4.2.1 Mobile Application Interface

The PitayaGrade mobile application is designed with a farmer-centric philosophy that prioritizes simplicity, clarity, and minimal learning curve. Recognizing that the target users are predominantly smallholder farmers with varying levels of technological literacy, the interface employs the following design principles:

**Large, Intuitive Controls.** All primary action buttons (capture image, view results, access history) are prominently sized and positioned for easy tapping, even with calloused or field-soiled hands.

**Minimal Text, Maximum Visualization.** Results are communicated primarily through visual indicators (color-coded grade badges, disease severity icons, progress charts) supplemented by concise text labels. Where text is used, it is written in clear, non-technical language.

**Bilingual Support.** The application supports both English and Filipino (Tagalog) language options, selectable from the settings menu, to accommodate linguistic preferences of farmers across different Philippine regions.

**Step-by-Step Guided Workflow.** First-time users are guided through the scanning process by an interactive onboarding tutorial that demonstrates optimal camera positioning, lighting considerations, and result interpretation.

**Accessible Color Palette.** The interface uses a high-contrast color palette designed for outdoor visibility on mobile screens under bright sunlight conditions.

The application comprises the following primary screens:

1. **Home Screen:** Central dashboard displaying recent scan activity, quick-access scan button, and summary statistics.
2. **Camera/Scan Screen:** Viewfinder with framing guide, capture button, and flash toggle.
3. **Results Screen:** Detailed display of grading and disease detection results with confidence scores and recommendations.
4. **History Screen:** Chronological list of past scans with thumbnail previews and filter/search capabilities.
5. **Analytics Dashboard:** Graphical visualizations of grading distributions, disease trends, and productivity metrics.
6. **Settings Screen:** Language selection, notification preferences, local-processing preference, detection threshold and verified model selection.

### 4.2.2 Real-Time Monitoring System

PitayaGrade's real-time monitoring capability provides farmers with continuous awareness of their crop quality status through aggregated scan data analysis. As the farmer scans multiple fruits across different sections of their farm, the monitoring system builds a dynamic picture of quality distribution and disease prevalence.

**Farm-Wide Quality Map (Proposed).** The active application does not collect GPS coordinates or render a farm map.

**Trend Detection.** The monitoring system analyzes scan results over time to identify emerging trends, such as a gradual increase in the proportion of Grade C fruits from a particular farm section, or a rising incidence of a specific disease. Trend alerts are generated when statistically significant patterns are detected.

**Harvest Readiness Indicator.** Based on the aggregated quality profile of scanned fruits, the system provides an overall harvest readiness assessment, indicating whether the majority of the crop meets the quality thresholds for the farmer's target market segment.

### 4.2.3 Alert and Notification System

The alert and notification system ensures that critical detections reach the farmer promptly, regardless of whether the application is actively in use:

**In-App Alerts.** Immediate visual and haptic alerts are displayed on the Results Screen when a disease is detected or a fruit is classified as Reject. Alerts are color-coded by severity: yellow for cosmetic concerns (Grade C), orange for disease monitoring recommendations, and red for confirmed disease detections.

**Push Notifications (Not Implemented).** Alerts are stored and displayed inside the application. Firebase Cloud Messaging is not configured.

**Batch Alerts.** At the end of each scanning session (defined as a sequence of scans within a 60-minute window), the system generates a session summary notification that recaps key findings: total fruits scanned, grade distribution, and any flagged issues.

**Advisory Notifications.** Periodic advisory notifications provide actionable recommendations based on accumulated scan data, such as "Anthracnose detections have increased 25% this week. Consider applying fungicide to the eastern section of your farm."

### 4.2.4 Digital Record-Keeping

PitayaGrade replaces informal, memory-based farm record-keeping with a structured digital system that captures, organizes, and preserves all scan data:

**Scan Log.** Recognized scans retain a timestamp, thumbnail, grade estimate, disease estimate, model/method metadata, recommendations and optional notes. Records are stored in local browser storage; GPS, SQLite and Firestore synchronization are not active.

**Search and Filter.** The history view supports filtering by date range, quality grade, disease type, and farm section. A search function allows farmers to locate specific records quickly.

**Export Capability.** Scan records can be exported as CSV files or PDF reports for sharing with buyers, agricultural extension officers, or for the farmer's personal record-keeping purposes.

**Data Retention.** The active application retains at most 500 local scan records. There is no cloud retention policy or cross-device synchronization.

### 4.2.5 Fast Processing and Instant Results

Speed is critical for user adoption and practical field utility. PitayaGrade is engineered to deliver results within seconds:

**Measured Performance Pending.** No supported cloud timing result exists. Physical-device latency must be recorded against a specific APK, model hash, phone and repeated-run protocol.

**Local Runtime.** Automated tests execute the bundled ONNX model through WASM, but this is not a phone benchmark. Android latency remains pending.

**Batch Processing (Not Implemented).** The active scan workflow processes one captured or uploaded image at a time.

### 4.2.6 Consistent and Standardized Grading Results

A primary advantage of PitayaGrade over manual grading is the consistency of its outputs. The machine learning model applies identical classification criteria to every image it processes, eliminating the variability inherent in human judgment:

**Deterministic Outputs.** Given the same input image, the model produces identical grading and detection results every time, ensuring reproducibility.

**Standardized Criteria.** The four-grade classification system (Grade A, B, C, Reject) is based on explicitly defined visual criteria that align with Philippine market standards, providing a common quality language between farmers and buyers.

**Calibration Pending.** No retained calibration experiment supports probabilistic interpretation of the displayed confidence. Reliability diagrams and calibration error should be calculated on the frozen reviewed test set before confidence is described as calibrated.

## 4.3 Optional Advanced Features

### 4.3.1 Cloud Database Integration (Proposed)

The active application does not use Firebase Firestore or authentication. A future, separately secured backend could provide the capabilities below:

**Multi-Device Access.** Farmers or farm managers with multiple devices can access their scan history from any authenticated device, ensuring data continuity.

**Data Backup and Recovery.** Cloud storage provides automatic backup of all scan records, protecting against data loss due to device damage, theft, or replacement.

**Aggregated Analytics.** Cloud-stored data enables large-scale analytics across multiple farms (with user consent), supporting research on regional disease patterns, quality trends, and best-practice identification.

**Secure Authentication (Proposed).** A future backend would require authenticated users, transport encryption, access controls and a reviewed privacy/retention policy. None is active in the local prototype.

### 4.3.2 Local Processing Capability

Recognizing that many Philippine dragon fruit farms are located in rural areas with intermittent or limited internet connectivity, PitayaGrade is designed to function effectively in offline mode:

**On-Device Inference.** The packaged ONNX/WASM runtime performs local grading inference. Physical-device offline first-run verification remains pending, and disease output is not yet produced by an evaluated segmentation model.

**Local Data Storage.** Recognized scan results are stored in browser localStorage. There is no cloud synchronization queue.

**Connectivity Behavior.** The active inference path is local. The Offline Mode control records the user's local-processing preference rather than switching inference engines.

**Offline Map Cache (Not Implemented).** The application does not collect or cache farm map data.

### 4.3.3 Dashboard Analytics

The analytics dashboard transforms raw scan data into actionable visual insights:

**Grade Distribution Charts.** Pie charts and bar graphs display the proportion of fruits classified into each quality grade over selected time periods (daily, weekly, monthly, seasonal).

**Disease Prevalence Timeline.** Line graphs track the incidence of each disease category over time, enabling farmers to identify seasonal patterns, evaluate the effectiveness of treatment interventions, and detect emerging outbreaks.

**Productivity Metrics.** Key performance indicators include total fruits scanned, average grade distribution, disease detection rate, estimated harvest value (based on grade distribution and prevailing market prices), and trend comparisons with previous seasons.

**Comparative Analysis.** Where sufficient data exists, the dashboard provides comparative analysis across different farm sections, harvest cycles, or management practices, helping farmers identify factors associated with higher quality outcomes.

### 4.3.4 Export Reports

PitayaGrade enables farmers to generate and share structured reports summarizing their scan data:

**PDF Reports.** Comprehensive reports formatted for printing or digital sharing, including grade distribution summaries, disease detection records, and trend charts. Reports can be generated for custom date ranges and optionally include representative scan images.

**CSV Data Export.** Raw scan data exported in comma-separated values format for analysis in spreadsheet applications or integration with other farm management tools.

**Buyer Reports.** Simplified report formats designed specifically for sharing with buyers and aggregators, presenting quality grade distributions and certifying that the graded batch has been assessed through the PitayaGrade system.

**Sharing Integration.** Reports can be shared directly from the application via email, messaging apps (Facebook Messenger, Viber), or file storage services.

---

# Chapter 5: Results and Discussion

> **Evidence status (31 October 2026).** This chapter reports retained software
> verification and internal held-out quality-classification results. Physical-device,
> UAT, disease-segmentation, and manual-grader comparison evidence remains pending.

## 5.1 System Testing Results

PitayaGrade has completed automated regression testing, exact ONNX evaluation, and Android debug assembly/lint checks. Physical-device verification, field testing, and user acceptance testing remain pending.

### 5.1.1 Functional Testing

The verified automated suite covers application workflows, storage integrity, localization, notifications, report safety, runtime assets, model-selection safeguards, non-fruit rejection, and actual ONNX/WASM execution. Separate held-out evaluation measures quality-classification accuracy. Neither test family replaces physical-camera or field testing.

| Verified check | Result on 31 October 2026 | What the result establishes |
|---|---:|---|
| JavaScript application and runtime tests | 112 passed, 0 failed | Browser workflows, storage safeguards, model selection, report export, image adjustment, presence-gate behavior, and packaged ONNX/WASM execution behave as asserted. |
| Python research-tool tests | 138 passed, 0 failed | Data validation, leakage audit, preprocessing, training policy, export contracts, and evaluation utilities behave as asserted on their fixtures. |
| Android debug assembly and lint | Passed | The synchronized web/model assets compile into a debug APK and pass Android lint. |
| GitHub application verification | Passed | Repository verification completed for commit `e32aaa4`. |
| GitHub Pages deployment | Passed | The updated web application was published successfully for the same commit. |

**Table 5.1.** Verified Software Evidence

The software results establish repeatable implementation behavior. The following held-out section separately measures image-level quality classification. Neither result measures disease segmentation, physical-phone reliability, or field usability.

### 5.1.2 User Acceptance Testing

User acceptance testing has not yet been conducted. It must begin only after adviser or institutional approval of the procedure and consent process. Anonymous task-level observations should be recorded using `research/week4/uat-template.csv`. No participant count, rating, SUS score or qualitative feedback is reported before those records exist.

## 5.2 Accuracy of the Machine Learning Model

### 5.2.1 Quality Grading Model Performance

All quality candidates were evaluated against the same frozen 226-image test split from the 1,553-image human-reviewed quality manifest. The manifest SHA-256 is `18dcad57010432323a52f2dff08cf70803fa1676239de9b301dd87c241da447a`. Each ONNX file produced one prediction for every held-out image, and the selected EfficientNet-B3 ONNX labels matched its PyTorch labels on all 226 images.

| Model | Accuracy | Macro precision | Macro recall | Macro F1 | ONNX CPU mean / P95 latency |
|---|---:|---:|---:|---:|---:|
| MobileNetV2 | 72.12% | 56.95% | 56.07% | 55.31% | 7.27 / 15.07 ms |
| ResNet50 | 74.34% | 57.75% | 54.84% | 54.83% | 24.74 / 33.65 ms |
| EfficientNet-B3 with audited feature pretraining | **74.78%** | **58.86%** | **58.97%** | **58.51%** | 17.85 / 21.28 ms |

**Table 5.2.** Frozen Held-Out Quality-Model Comparison

EfficientNet-B3 had the highest overall accuracy and macro F1 and is the promoted selectable classifier. Its 0.44 percentage-point accuracy advantage over ResNet50 is modest and should not be described as a large performance gain. External Good/Medium images initialized features only; the audit excluded every external image that matched any frozen quality record.

| Actual class | Predicted A | Predicted B | Predicted C | Predicted Reject | Support |
|---|---:|---:|---:|---:|---:|
| Grade A | 15 | 9 | 4 | 0 | 28 |
| Grade B | 14 | 39 | 6 | 2 | 61 |
| Grade C | 4 | 12 | 5 | 1 | 22 |
| Reject | 2 | 3 | 0 | 110 | 115 |

**Table 5.3.** EfficientNet-B3 Held-Out Confusion Matrix

The model performed strongly on Reject images (96.49% F1) but remained weak on Grade A (47.62% F1) and especially Grade C (27.03% F1). Most Grade C errors became Grade B. This class imbalance and confusion justify retaining human validation and collecting more independent Grade A/B/C field images.

The separate dragon-fruit presence gate achieved 99.66% accuracy on its retained 1,476-image binary evaluation, with 97.84% precision, 100% recall, and 99.60% specificity. This gate is a safety filter for non-fruit input, not evidence of grading accuracy.

### 5.2.2 Disease Detection Model Performance

The intended disease-segmentation model has not yet been supplied as an evaluated app asset. Current disease results use image heuristics and must not be reported as validated diagnoses. No disease-model precision, recall, F1-score, support, coverage metric, or class comparison is currently reported.

### 5.2.3 AUC-ROC Performance

AUC-ROC has not been calculated. It may be reported only if the final prediction export retains valid per-class scores and the approved protocol requires traceable one-vs-rest calculations.

## 5.3 Performance Evaluation

### 5.3.1 Processing Speed

ONNX Runtime on the development computer processed the selected EfficientNet-B3 model in a mean of 17.85 ms per held-out image, with a 21.28 ms P95. This excludes camera capture, browser preprocessing, detector/presence-gate execution, rendering, and phone hardware effects. Physical-device end-to-end time remains pending and must identify the APK checksum, device, Android version, warm-up rule, and repetition count.

### 5.3.2 Reliability

A repeated physical-device stress test has not yet been performed. Completion counts, failures, crashes, memory behavior, and recovery observations must come from `device-test.csv`; no phone reliability rate is currently reported.

### 5.3.3 Model Size and Resource Utilization

The promoted EfficientNet-B3 asset is 44,522,597 bytes with SHA-256 `c2dbd10f72932b871e49679f07b5134a0e8de75f973084651850d61673d0c3a3`. The bundled YOLOv8-Nano asset is 12,267,617 bytes. The published debug testing APK for commit `e32aaa4` is 167,949,482 bytes and has SHA-256 `4411b47156fd8a47ff7fd0008bbdce95fa20bd2c38c571104bfbf5681f23f748`. RAM, CPU, battery use, and installed size have not been measured on target phones.

## 5.4 Benefits Compared to Manual Grading

A controlled comparison with manual graders has not yet been conducted. No claim of superiority, cost savings or early disease detection is supported.

### 5.4.1 Speed

Throughput must be measured under a controlled protocol before any speed advantage is claimed. No time-per-fruit or fruits-per-hour comparison is currently reported.

### 5.4.2 Consistency

The drafted human-grader and repeatability values are unsupported. Agreement and repeatability remain pending controlled evaluation.

### 5.4.3 Disease Detection Sensitivity

No retained expert-reviewed sample comparison supports the drafted sensitivity or early-stage detection claims. These statements must not be used as findings.

### 5.4.4 Cost Efficiency

No retained cost study supports the drafted labor-savings estimate. Economic analysis should include device, training, maintenance, annotation, support and verification costs before reporting savings.

---

# Chapter 6: Current Conclusion and Recommendations

## 6.1 Summary of Findings

This capstone project has developed and software-tested a functional **PitayaGrade** prototype. Retained evidence supports conclusions about the implemented local runtime and internal held-out quality classification. Disease accuracy, field performance, user acceptance, and economic impact remain evaluation objectives rather than findings.

1. **Implemented ML Runtime.** The application locally executes a dragon-fruit presence gate, YOLOv8-Nano detector/grader, and three selectable quality classifiers through ONNX Runtime Web. The promoted EfficientNet-B3 classifier achieved 74.78% accuracy and 58.51% macro F1 on the frozen internal test set. The disease-segmentation asset remains pending.

2. **Android Build Readiness.** The Capacitor Android debug application assembles and passes lint, and its packaged web/model assets are synchronized. Camera, offline first-run, lifecycle, export, model switching, and performance behavior still require checks on physical phones before practical deployment can be claimed.

3. **No Manual-Superiority Finding Yet.** No retained controlled comparison supports a speed, agreement or sensitivity advantage over experienced graders. Any future comparison must use the same reviewed samples, a documented protocol and appropriate statistical analysis.

4. **User Acceptance Pending.** No approved participant evidence is retained. UAT must use anonymous participant identifiers, a consistent task script and the approved consent process before usability conclusions are written.

5. **Implemented Application Features.** The prototype includes image capture/upload, crop/zoom/rotation adjustment, fail-closed non-fruit rejection, local analysis, model selection, notifications, saved records, analytics, and report export. Automated tests cover these workflows, while their effectiveness for farmers remains subject to device testing and UAT.

## 6.2 Impact on Agriculture

The development and potential deployment of PitayaGrade carries several significant implications for the Philippine agricultural sector:

**Modernization of Farm Practices.** PitayaGrade represents a concrete step toward the digital transformation of Philippine fruit farming, demonstrating that sophisticated AI technologies can be made accessible and practical for smallholder farmers through thoughtful design and mobile-first deployment.

**Reduction of Post-Harvest Losses.** By enabling more accurate quality grading and earlier disease detection, PitayaGrade has the potential to reduce the 15-30% post-harvest loss rate currently experienced by dragon fruit farmers, directly improving farm profitability and food security.

**Market Access and Competitiveness.** Standardized, AI-verified quality grading enhances the credibility and consistency of Philippine dragon fruit in both domestic and international markets. The ability to provide quality documentation through PitayaGrade's report export feature supports compliance with buyer quality requirements and export certification standards.

**Data-Driven Agriculture.** The aggregated scan data generated by PitayaGrade, if collected at scale, could provide valuable insights into regional disease patterns, quality trends, and the effectiveness of different farming practices. This data can inform agricultural policy, extension services, and research priorities.

**Replicable Model.** The PitayaGrade methodology and architecture can serve as a template for developing similar systems for other Philippine crops, including mango, calamansi, banana, and coffee. The modular design allows the machine learning models to be retrained on new crop datasets while reusing the mobile application framework and backend infrastructure.

## 6.3 Recommendations for Future Improvements

Based on the findings and limitations identified in this study, the following recommendations are proposed for future development and research:

1. **Dataset Expansion.** The training dataset should be expanded to include dragon fruit samples from a broader range of Philippine provinces, growing conditions, and cultivar varieties. A target dataset of 20,000 or more labeled images would support improved model generalizability and the incorporation of additional disease categories.

2. **Multi-Spectral Imaging.** Future iterations of PitayaGrade should explore the integration of multi-spectral or hyperspectral imaging capabilities, potentially through accessory smartphone camera modules, to enable detection of subsurface defects and early-stage diseases not visible in standard RGB images.

3. **Internal Quality Estimation.** Investigating methods for non-invasive estimation of internal quality parameters (Brix level, flesh color, seed density) from external image features, potentially through correlation modeling with destructive quality testing data, would enhance the system's grading comprehensiveness.

4. **Federated Learning.** Implementing a federated learning framework would enable the PitayaGrade model to be continuously improved from user scan data without requiring centralized data collection, addressing privacy concerns and enabling the model to adapt to regional variations in dragon fruit appearance and disease presentation.

5. **Integration with Agricultural Information Systems.** PitayaGrade should be designed for interoperability with existing agricultural information systems maintained by the Department of Agriculture, PCAARRD, and LGU agriculture offices. API-based integration would enable PitayaGrade data to contribute to national crop monitoring and early warning systems.

6. **IoT Sensor Integration.** Integrating PitayaGrade with Internet of Things (IoT) environmental sensors (soil moisture, temperature, humidity) could enable the system to correlate disease incidence with environmental conditions, improving predictive accuracy and enabling proactive rather than reactive disease management.

7. **Voice Interface.** Adding voice-based interaction and result announcement capabilities would improve accessibility for older farmers and those with visual impairments, broadening the system's potential user base.

8. **Controlled Field Trials.** Extended field trials across multiple growing seasons and geographic locations are recommended to validate the system's performance under the full range of conditions encountered in Philippine dragon fruit farming. A randomized controlled trial comparing farm-level outcomes (post-harvest losses, revenue, disease management effectiveness) between PitayaGrade users and non-users would provide rigorous evidence of the system's real-world impact.

9. **Commercialization and Sustainability.** A sustainability strategy should be developed for long-term PitayaGrade deployment, potentially involving partnerships with the Department of Agriculture, NGOs, or private-sector stakeholders. Freemium or cooperative licensing models should be explored to ensure affordability for smallholder farmers while generating revenue to support ongoing development and maintenance.

10. **Explainable AI Features.** Integrating Grad-CAM or similar visualization techniques that highlight the image regions most influential in the model's classification decision would enhance user trust and provide educational value, helping farmers develop their own visual assessment skills in parallel with system use.

---

# References

Bangor, A., Kortum, P. T., & Miller, J. T. (2009). Determining what individual SUS scores mean: Adding an adjective rating scale. *Journal of Usability Studies*, 4(3), 114-123.

Barbedo, J. G. A. (2019). Plant disease identification from individual lesions and spots using deep learning. *Biosystems Engineering*, 180, 96-107.

Ferentinos, K. P. (2018). Deep learning models for plant disease detection and diagnosis. *Computers and Electronics in Agriculture*, 145, 311-318.

Howard, A. G., Zhu, M., Chen, B., Kalenichenko, D., Wang, W., Weyand, T., ... & Adam, H. (2017). MobileNets: Efficient convolutional neural networks for mobile vision applications. *arXiv preprint arXiv:1704.04861*.

Kamilaris, A., & Prenafeta-Boldu, F. X. (2018). Deep learning in agriculture: A survey. *Computers and Electronics in Agriculture*, 147, 70-90.

Le, T. T., Pham, B. T., Dang, K. B., & Le, H. T. (2020). Classification of dragon fruit quality using transfer learning with InceptionV3. *Journal of Agricultural Informatics*, 11(2), 45-56.

Liakos, K. G., Busato, P., Moshou, D., Pearson, S., & Bochtis, D. (2018). Machine learning in agriculture: A review. *Sensors*, 18(8), 2674.

Mohanty, S. P., Hughes, D. P., & Salathe, M. (2016). Using deep learning for image-based plant disease detection. *Frontiers in Plant Science*, 7, 1419.

Naik, S., & Patel, B. (2017). Machine vision based fruit classification and grading: A review. *International Journal of Computer Applications*, 170(9), 22-34.

Nguyen, V. H., Ngo, T. Q., Le, T. D., & Pham, H. T. (2021). Deep learning-based detection of stem canker disease in dragon fruit using ResNet-50. *Plant Disease*, 105(8), 2148-2155.

Philippine Statistics Authority. (2024). *Agricultural Indicators System: Crops Statistics*. Quezon City: PSA.

Ramcharan, A., Baranowski, K., McCloskey, P., Ahmed, B., Legg, J., & Hughes, D. P. (2017). Deep learning for image-based cassava disease detection. *Frontiers in Plant Science*, 8, 1852.

Sa, I., Ge, Z., Dayoub, F., Upcroft, B., Perez, T., & McCool, C. (2016). DeepFruits: A fruit detection system using deep neural networks. *Sensors*, 16(8), 1222.

Saleem, M. H., Potgieter, J., & Arif, K. M. (2019). Plant disease detection and classification by deep learning. *Plants*, 8(11), 468.

Jocher, G., Chaurasia, A., & Qiu, J. (2023). Ultralytics YOLOv8. *GitHub Repository*. https://github.com/ultralytics/ultralytics

Tan, M., & Le, Q. V. (2019). EfficientNet: Rethinking model scaling for convolutional neural networks. *International Conference on Machine Learning*, 6105-6114.

Sladojevic, S., Arsenovic, M., Anderla, A., Culibrk, D., & Stefanovic, D. (2016). Deep neural networks based recognition of plant diseases by leaf image classification. *Computational Intelligence and Neuroscience*, 2016, 3289801.

Soares, J. D. R., Machado, R. D., Silva, M. L., & Souza, L. C. (2020). A deep learning approach for citrus fruit quality grading. *Scientia Horticulturae*, 263, 109152.

Tm, P., Pranathi, A., SaiAshrworkkumar, K., Chandra, N. B., & Reddy, P. V. (2018). Tomato leaf disease detection using convolutional neural networks. *2018 Eleventh International Conference on Contemporary Computing (IC3)*, 1-5.

Zhang, C., Jia, W., Li, Z., & Zhou, M. (2021). Lightweight convolutional neural network for real-time fruit grading on edge devices. *IEEE Access*, 9, 57543-57556.

---

*End of Document*
