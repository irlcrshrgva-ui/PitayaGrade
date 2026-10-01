/* Presentation-only translations. Stored labels, notes, and exports stay intact. */
const LanguageManager = {
  language: 'en',
  originals: new WeakMap(),
  attributes: new WeakMap(),
  filipino: {
    'No grading confidence is available for an unrecognized image.': 'Walang maibibigay na kumpiyansa sa paggrado para sa larawang hindi nakilala.',
    '📁 Local Engine': '📁 Lokal na Pagsusuri', 'Flagged Scans': 'Mga Scan na Dapat Suriin',
    'Most saved scans show no visible disease symptoms. These image-based estimates do not confirm overall farm health.': 'Walang nakikitang sintomas ng sakit sa karamihan ng naka-save na scan. Hindi kinukumpirma ng mga tantiyang ito ang pangkalahatang kalusugan ng sakahan.',
    'Over 20% of saved scans were flagged by the image-based disease analysis. Review these records and inspect the fruit.': 'Mahigit 20% ng naka-save na scan ang may palatandaan sa pagsusuri ng sakit batay sa larawan. Balikan ang mga rekord at inspeksyunin ang prutas.',
    'Inspect flagged fruit and seek confirmation.': 'Inspeksyunin ang mga prutas na may palatandaan at humingi ng kumpirmasyon.',
    'Image heuristics cannot confirm a pathogen or its spread. Confirm the condition before selecting treatment.': 'Hindi makukumpirma ng pagtataya mula sa larawan ang sanhi ng sakit o pagkalat nito. Kumpirmahin ang kondisyon bago pumili ng paggamot.',
    'Saved scans include quality or symptom flags. Review the individual assessments before harvest.': 'May mga palatandaan tungkol sa kalidad o sintomas sa naka-save na scan. Suriin ang bawat pagtataya bago anihin.',
    'Review lower-grade and flagged records.': 'Balikan ang mga rekord na mababa ang grado o may palatandaan.',
    'The aggregate counts do not identify a cause or establish a trend over time.': 'Hindi tinutukoy ng kabuuang bilang ang sanhi o ang pagbabago sa paglipas ng panahon.',
    'Continue standard hydration and monitoring cycles.': 'Ipagpatuloy ang karaniwang pagdidilig at pagsubaybay.',
    'Continue inspecting fruit on the plant alongside the saved image assessments.': 'Patuloy na inspeksyunin ang prutas sa halaman kasabay ng pagtingin sa naka-save na pagsusuri ng larawan.',
    'Maturity Grading': 'Pagtataya ng Pagkahinog',
    'Harvestable': 'Maaari nang anihin', 'Developing': 'Umuunlad pa',
    'Harvestable Stage': 'Yugto na maaari nang anihin', 'Developing Stage': 'Yugto ng pag-unlad',
    'Not Applicable Stage': 'Hindi naaangkop',
    'Detected Symptoms': 'Mga Natukoy na Sintomas',
    'Pipeline Feature Extraction': 'Mga Katangiang Sinuri',
    'Details': 'Mga Detalye', 'Color': 'Kulay', 'Color Uniformity': 'Pagkakapantay ng Kulay',
    'Brightness': 'Liwanag', 'Model': 'Modelo', 'Processing': 'Pagproseso',
    'Assessment Limitations': 'Mga Limitasyon ng Pagsusuri',
    'Disease and maturity results are image-based estimates. Size is estimated from framing, not measured weight. Validated performance metrics for this deployed pipeline are not available.': 'Ang mga resulta tungkol sa sakit at pagkahinog ay mga tantiya batay sa larawan. Tinataya ang laki mula sa pagkakakuha ng larawan, hindi sa sinukat na timbang. Wala pang napatunayang sukatan ng pagganap para sa kasalukuyang sistema.',
    'Scan Another': 'Mag-scan ng Iba', 'Delete This Record': 'Burahin ang Rekord na Ito',
    'Healthy': 'Malusog', 'Unrecognized': 'Hindi nakilala',
    'Object: Detecting...': 'Bagay: Tinutukoy...', 'Object: Unknown Object': 'Bagay: Hindi kilala',
    'Smooth': 'Makinis', 'Slightly Rough': 'Bahagyang magaspang', 'Minor Blemishes': 'Kaunting mantsa',
    'Cracked': 'May bitak', 'Scarred': 'May peklat', 'Spotted': 'May mga batik',
    'Vibrant Pink': 'Matingkad na rosas', 'Deep Magenta': 'Malalim na magenta',
    'Light Pink': 'Mapusyaw na rosas', 'Green-Pink': 'Berde at rosas',
    'Pale': 'Maputla', 'Dark Reddish': 'Madilim na mapula',
    'Small (150-250g)': 'Maliit (150-250g)', 'Medium (250-400g)': 'Katamtaman (250-400g)',
    'Large (400-550g)': 'Malaki (400-550g)', 'Extra Large (550g+)': 'Napakalaki (550g+)',
    'No visible symptoms detected': 'Walang nakitang sintomas',
    'Analysis Model': 'Modelo ng Pagsusuri',
    'The image heuristic assigned Grade A. Verify physical grading criteria before making market or export decisions.': 'Grade A ang ibinigay ng pagsusuri ng larawan. Suriin ang pisikal na pamantayan ng paggrado bago magpasya tungkol sa pagbebenta o pag-export.',
    'Disease Analysis': 'Pagsusuri ng Sintomas',
    'Image color heuristics; inspect flagged fruit': 'Pagsusuri ng kulay; suriin ang prutas na may babala',
    'Signs to Inspect': 'Mga Palatandaang Susuriin',
    'Not measured': 'Hindi sinukat',
    'No visible symptoms flagged by color analysis': 'Walang sintomas na na-flag ng pagsusuri ng kulay',
    'Inspect the fruit to confirm its condition': 'Suriin ang prutas upang kumpirmahin ang kondisyon nito',
    'Disease and maturity results are image-based estimates. Physical size and weight are not measured. Symptom guidance describes signs to inspect, not confirmed findings. Validated performance metrics for this deployed pipeline are not available.':
      'Tantiya mula sa larawan ang sakit at pagkahinog. Hindi sinusukat ang pisikal na laki at timbang. Ang gabay sa sintomas ay mga palatandaang susuriin, hindi kumpirmadong natuklasan. Wala pang napatunayang sukatan ng pagganap para sa kasalukuyang sistema.',
    'Uniform skin texture confirmed': 'Nakumpirma ang pantay na tekstura ng balat',
    'Normal coloration verified': 'Natiyak ang normal na kulay',
    'Dark sunken lesions on skin': 'Madidilim at lubog na sugat sa balat',
    'Brown/black circular spots': 'Kayumanggi o itim na bilog na batik',
    'Soft tissue around lesions': 'Malambot na tisyu sa paligid ng sugat',
    'Fungal spore masses visible': 'Nakikitang kumpol ng mga spore ng fungus',
    'Swollen/discolored stem base': 'Namamaga o nag-iba ang kulay ng puno ng tangkay',
    'Cracking near stem junction': 'Mga bitak malapit sa dugtungan ng tangkay',
    'Yellowish tissue exudate': 'Madilaw na likidong lumalabas sa tisyu',
    'Darkened vascular tissue': 'Nangingitim na tisyu ng daluyan',
    'Water-soaked soft areas': 'Malalambot na bahaging tila babad sa tubig',
    'Foul odor present': 'May mabahong amoy',
    'Tissue collapse on pressure': 'Lumulubog ang tisyu kapag pinisil',
    'Bacterial ooze visible': 'Nakikitang likidong dulot ng bakterya',
    'Surface scarring/scratches': 'Mga peklat o gasgas sa balat',
    'Small puncture marks': 'Maliliit na marka ng tusok',
    'Irregular holes on skin': 'Hindi pantay na mga butas sa balat',
    'Frass deposits detected': 'May natukoy na dumi ng insekto',
    'Bleached/whitened patches': 'Mga bahaging kumupas o namuti',
    'Dry cracked skin areas': 'Mga bahaging tuyo at bitak ang balat',
    'Uneven pigmentation': 'Hindi pantay na kulay',
    'Dehydrated tissue zones': 'Mga bahaging natuyuan ng tisyu',
    'Small dark spots clustered': 'Magkakumpol na maliliit at madidilim na batik',
    'White/gray fuzzy growth': 'Puti o abong mabalahibong tumubo',
    'Concentric ring patterns': 'Mga bilog na magkakapatong ang hugis',
    'Raised lesion borders': 'Nakaangat na gilid ng sugat',
    'Unidentified symptoms present': 'May mga sintomas na hindi pa natutukoy',
    'No data yet. Start scanning!': 'Wala pang datos. Magsimulang mag-scan!',
    'Total': 'Kabuuan', 'No quality data yet': 'Wala pang datos ng kalidad',
    'No disease data yet': 'Wala pang datos ng sakit',
    'Start scanning dragon fruit to unlock dynamic AI farm insights.': 'Magsimulang mag-scan ng dragon fruit upang makita ang mga pagsusuri ng sakahan.',
    'English / Filipino — interface translation; detailed guidance remains in English': 'English / Filipino — salin ng interface; may ilang gabay pang nasa Ingles',
    'Fruit Rejected': 'Prutas na may gradong Reject',
    'Premium Quality Detected': 'Natukoy ang Premium na Kalidad',
    'Object Unrecognized': 'Hindi Nakilala ang Bagay',
    'No Dragon Fruit Detected': 'Walang Natukoy na Dragon Fruit',
    'Detection Diagnostics': 'Mga Detalye ng Pagtukoy',
    'Try Again': 'Subukang Muli',
    'The assessment could not verify a dragon fruit in this image. Check the image and detection threshold, then try again.': 'Hindi makumpirma ng pagsusuri ang dragon fruit sa larawang ito. Suriin ang larawan at minimum na kumpiyansa sa pagtukoy, pagkatapos ay subukang muli.',
    'Please capture a clear, centered, and well-lit photo of a white-fleshed or red-fleshed dragon fruit on the vine, keeping background clutter to a minimum.': 'Kumuha ng malinaw, nakasentro, at maliwanag na larawan ng dragon fruit na may puti o pulang laman habang nasa halaman. Bawasan ang mga bagay sa likuran.',
    'Image features suggest harvest maturity. Confirm ripeness on the plant before harvesting.': 'Ipinapahiwatig ng larawan na maaaring hinog na ang prutas. Kumpirmahin ang pagkahinog sa halaman bago anihin.',
    'Image analysis suggests the fruit is developing. Check maturity on the plant before scheduling harvest.': 'Ipinapahiwatig ng larawan na lumalaki pa ang prutas. Suriin ang pagkahinog sa halaman bago magtakda ng pag-ani.',
    'The model assigned Grade A. Verify physical grading criteria before making market or export decisions.': 'Grade A ang ibinigay ng modelo. Suriin ang pisikal na pamantayan ng paggrado bago magpasya tungkol sa pagbebenta o pag-export.',
    'Try adjusting your filters or search.': 'Subukang baguhin ang mga filter o hinahanap.',
    'No data for this period': 'Walang datos sa panahong ito',
    'No scan records found within the selected date range.': 'Walang rekord ng scan sa napiling saklaw ng petsa.',
    'PitayaGrade Farm Report': 'Ulat ng Sakahan mula sa PitayaGrade',
    'Summary Overview': 'Pangkalahatang Buod', 'Metric': 'Sukatan', 'Value': 'Halaga',
    'Average Confidence': 'Karaniwang Kumpiyansa', 'Healthy Fruits': 'Mga Prutas na Tinayang Malusog',
    'Fruits with estimated disease symptoms': 'Mga prutas na may tinatayang sintomas ng sakit',
    'Quality Grade Distribution': 'Distribusyon ng Grado ng Kalidad',
    'Grade': 'Grado', 'Count': 'Bilang', 'Percentage': 'Bahagdan', 'Date': 'Petsa',
    'Disease': 'Sakit', 'Disease Detection Summary': 'Buod ng Tinatayang Sakit',
    'No image-based disease flags in this period.': 'Walang palatandaan ng sakit batay sa larawan sa panahong ito.',
    'Recent Scan Log': 'Mga Kamakailang Rekord ng Scan', '🖨️ Print Report': '🖨️ I-print ang Ulat',
    'Disease, maturity, and size are image-based estimates. Confirm findings through inspection.': 'Ang sakit, pagkahinog, at laki ay mga tantiya batay sa larawan. Kumpirmahin ang mga ito sa aktuwal na inspeksyon.',
    'Clear all saved notifications?': 'Burahin ang lahat ng naka-save na abiso?',
    'Delete this scan record?': 'Burahin ang rekord ng scan na ito?',
    'Are you sure you want to delete all scan records? This cannot be undone.': 'Sigurado ka bang buburahin ang lahat ng rekord ng scan? Hindi na ito maibabalik.',
    'Saved notifications could not be read. Original data has been preserved.': 'Hindi mabasa ang mga naka-save na abiso. Napanatili ang orihinal na datos.',
    'Notifications could not be saved. Existing alerts are unchanged.': 'Hindi na-save ang mga abiso. Walang nabago sa mga dating abiso.',
    'Session summary state could not be saved.': 'Hindi na-save ang katayuan ng buod ng sesyon.',
    'Report generated successfully': 'Matagumpay na nagawa ang ulat',
    'No data to export': 'Walang datos na mai-export',
    'CSV exported successfully': 'Matagumpay na na-export ang CSV',
    'CSV download requested': 'Hiniling ang pag-download ng CSV',
    'Report could not be exported. Please try again.': 'Hindi ma-export ang ulat. Subukang muli.',
    'Printing is unavailable or blocked. Export CSV instead.': 'Hindi magagamit o hinaharangan ang pag-print. I-export bilang CSV.',
    'Record deleted': 'Nabura ang rekord',
    'Some saved data could not be loaded. Original data has been preserved.': 'Hindi ma-load ang ilang naka-save na datos. Napanatili ang orihinal na datos.',
    'Offline mode enabled': 'Naka-on ang offline mode',
    'Offline mode disabled': 'Naka-off ang offline mode',
    'Settings could not be saved.': 'Hindi na-save ang mga setting.',
    'Live scanner activated': 'Naka-on ang live scanner',
    'Camera access denied or unavailable': 'Hindi pinayagan o hindi magagamit ang camera',
    'Switched to rear camera': 'Ginagamit na ang camera sa likod',
    'Switched to front camera': 'Ginagamit na ang camera sa harap',
    'Camera not ready': 'Hindi pa handa ang camera',
    'Frame captured. Analyzing...': 'Nakunan ang larawan. Sinusuri...',
    'Choose an image smaller than 20 MB.': 'Pumili ng larawang mas maliit sa 20 MB.',
    'Unable to read this image. Please choose another file.': 'Hindi mabasa ang larawang ito. Pumili ng ibang file.',
    'Unable to read image file.': 'Hindi mabasa ang file ng larawan.',
    'No Data': 'Walang Datos', 'No matching records': 'Walang tumutugmang rekord',
    'No records yet': 'Wala pang mga rekord',
    'Offline mode': 'Offline mode',
    'Detection confidence threshold': 'Minimum na kumpiyansa sa pagtukoy',
    'Connected — scanning runs on this device': 'Nakakonekta — sa device na ito ginagawa ang pagsusuri',
    'Offline — scanning runs on this device': 'Offline — sa device na ito ginagawa ang pagsusuri',
    'Home': 'Simula', 'Dashboard': 'Pangkalahatang-ideya', 'History': 'Kasaysayan',
    'Scan': 'I-scan', 'Analytics': 'Pagsusuri', 'Settings': 'Mga Setting',
    'Reports': 'Mga Ulat', 'Notifications': 'Mga Abiso',
    'Your farm overview at a glance': 'Buod ng iyong sakahan',
    'Total Scans': 'Kabuuang Scan', 'Avg. Grade': 'Karaniwang Grado',
    'Disease Rate': 'Bahagdan ng Tinatayang Sakit', 'Healthy Rate': 'Bahagdan ng Malusog',
    'Quick Actions': 'Mga Mabilis na Aksyon', 'New Scan': 'Bagong Scan',
    'Export Report': 'I-export ang Ulat', 'View History': 'Tingnan ang Kasaysayan',
    'Harvest Readiness': 'Kahandaan sa Pag-ani',
    'Average image-based maturity of saved scans': 'Karaniwang tinatayang pagkahinog batay sa mga larawan',
    'Grade Distribution': 'Distribusyon ng Grado', 'Recent Scans': 'Mga Kamakailang Scan',
    'View All': 'Tingnan Lahat', 'No scans yet': 'Wala pang mga scan',
    'Start scanning dragon fruit to see results here.': 'Mag-scan ng dragon fruit upang makita rito ang mga resulta.',
    'Scan Fruit': 'I-scan ang Prutas',
    'Capture, upload, or scan live with your camera': 'Kumuha o mag-upload ng larawan, o gamitin ang live camera',
    'Photo Mode': 'Larawan', 'Live Scanner': 'Live Scanner',
    'Tap to capture or upload': 'Pindutin upang kumuha o mag-upload ng larawan',
    'JPG, PNG - best results with good lighting': 'JPG, PNG — gumamit ng sapat na liwanag',
    'Capture Photo': 'Kumuha ng Larawan', 'Analyze Fruit': 'Suriin ang Prutas',
    'Analyze': 'Suriin', 'Scan Again': 'Mag-scan Muli', 'Reset': 'I-reset',
    'Start Camera': 'Buksan ang Camera', 'Stop Scanner': 'Ihinto ang Scanner',
    'Switch Camera': 'Palitan ang Camera', 'Capture & Analyze': 'Kunan at Suriin',
    'Start Scanner': 'Simulan ang Scanner', 'Camera Off': 'Nakasara ang Camera',
    'Ready to scan': 'Handa nang mag-scan', 'Analyzing...': 'Sinusuri...',
    'Scan History': 'Kasaysayan ng mga Scan', 'Search by notes...': 'Maghanap sa mga tala...',
    'All': 'Lahat', 'All Grades': 'Lahat ng Grado', 'No Records Found': 'Walang Nahanap na Rekord',
    'No records found': 'Walang nahanap na rekord',
    'Scanned dragon fruit assessments will appear here.': 'Dito makikita ang mga naitalang pagsusuri ng dragon fruit.',
    'Deep insights into your farm data': 'Mas detalyadong pagsusuri ng datos ng iyong sakahan',
    'Premium Rate': 'Bahagdan ng Premium', 'AI Farm Insights': 'Mga Pagsusuri ng Sakahan',
    'Initializing...': 'Inihahanda...', 'Disease Trend (Last 7 Days)': 'Takbo ng Tinatayang Sakit (Huling 7 Araw)',
    'Quality Over Time': 'Kalidad sa Paglipas ng Panahon', 'Disease Breakdown': 'Buod ng Tinatayang Sakit',
    'Generate and export farm reports': 'Gumawa at mag-export ng mga ulat ng sakahan',
    'Date Range': 'Saklaw ng Petsa', 'From': 'Mula', 'To': 'Hanggang',
    '📄 Generate Report': '📄 Gumawa ng Ulat', 'Generate Report': 'Gumawa ng Ulat',
    'Configure your preferences': 'Ayusin ang iyong mga kagustuhan',
    'General': 'Pangkalahatan', 'Language': 'Wika', 'Offline Mode': 'Offline Mode',
    'Keep analysis on this device': 'Panatilihin ang pagsusuri sa device na ito',
    'Detection Pipeline': 'Proseso ng Pagsusuri', 'Primary Model': 'Pangunahing Modelo',
    'Available': 'Magagamit', 'Alternate Model': 'Alternatibong Modelo',
    'Not bundled': 'Hindi kasama sa app', 'Transfer Learning': 'Transfer Learning',
    'Detection Threshold': 'Minimum na Kumpiyansa sa Detection', 'Model Metrics': 'Mga Sukatan ng Modelo',
    'Overall Accuracy': 'Pangkalahatang Katumpakan',
    'Not validated for the deployed pipeline': 'Hindi pa napatunayan para sa kasalukuyang sistema',
    'Pending linked evaluation results': 'Hinihintay ang mga resulta ng kaugnay na pagsusuri',
    'Training Configuration': 'Mga Setting ng Pagsasanay',
    'See retained training experiment outputs': 'Tingnan ang naitalang mga resulta ng pagsasanay',
    'Scan alerts': 'Mga abiso sa scan',
    'Show in-app alerts after saving scans': 'Magpakita ng abiso sa app pagkatapos mag-save ng scan',
    'Data': 'Datos', 'Clear All Data': 'Burahin ang Lahat ng Datos',
    'Remove all scan records': 'Burahin ang lahat ng rekord ng scan',
    'Open notifications': 'Buksan ang mga abiso', 'Close notifications': 'Isara ang mga abiso',
    'Mark all read': 'Markahang nabasa lahat', 'Clear alerts': 'Burahin ang mga abiso',
    'No Notifications': 'Walang mga Abiso',
    "You're all caught up. Notifications will appear here when issues are detected.": 'Dito makikita ang mga abiso kapag may natukoy na posibleng problema.',
    'Scan Details': 'Mga Detalye ng Scan', 'Notes': 'Mga Tala', 'Save Notes': 'I-save ang mga Tala',
    'Delete Scan': 'Burahin ang Scan', 'Delete': 'Burahin', 'Cancel': 'Kanselahin',
    'Close': 'Isara', 'Confidence': 'Kumpiyansa', 'Quality Grade': 'Grado ng Kalidad',
    'Disease Detection': 'Pagtukoy ng Sakit', 'Maturity': 'Pagkahinog',
    'Recommendations': 'Mga Rekomendasyon', 'Size': 'Laki', 'Surface Condition': 'Kondisyon ng Balat',
    'Skip': 'Laktawan', 'Next': 'Susunod', 'Get Started': 'Magsimula', 'Done ✓': 'Tapos ✓',
    'Welcome': 'Maligayang pagdating', 'Welcome to PitayaGrade!': 'Maligayang pagdating sa PitayaGrade!',
    'Your AI-powered dragon fruit grading assistant. Let us show you around in just a few steps.': 'Ang iyong katuwang sa pagsusuri ng dragon fruit gamit ang AI. Ipapakita namin ang paggamit nito sa ilang hakbang.',
    'This is your Home screen. See your total scans, average grade, disease rate, and harvest readiness at a glance.': 'Ito ang pangunahing pahina. Makikita rito ang kabuuang scan, karaniwang grado, tinatayang sakit, at kahandaan sa pag-ani.',
    'Scan a Fruit': 'I-scan ang Prutas',
    'Tap Scan to capture or upload a dragon fruit photo. The app grades the image and estimates visible symptoms. Processing time depends on your device.': 'Pindutin ang I-scan upang kumuha o mag-upload ng larawan ng dragon fruit. Tinataya ng app ang grado at nakikitang sintomas. Nakadepende sa device ang tagal ng pagsusuri.',
    'Every scan is saved here automatically. Filter by grade, search by notes, and view full details for any past assessment.': 'Awtomatikong itinatala rito ang mga scan. Salain ayon sa grado, maghanap sa mga tala, at tingnan ang detalye ng nakaraang pagsusuri.',
    'Track disease trends, quality over time, and grade distribution across all your scans. Great for farm-level decision making.': 'Tingnan ang takbo ng tinatayang sakit, kalidad sa paglipas ng panahon, at distribusyon ng grado upang makatulong sa pagpapasya sa sakahan.',
    'Configure your language, detection threshold, and offline mode here. You can also clear all scan data from this page.': 'Piliin dito ang wika, minimum na kumpiyansa, at offline mode. Maaari ring burahin ang mga rekord ng scan.',
    'Just now': 'Ngayon lang', 'Session Summary': 'Buod ng Sesyon',
    'Image-based estimate, not a confirmed diagnosis. Inspect the fruit and consult an agricultural officer for confirmation.':
      'Tantiya batay sa larawan, hindi kumpirmadong diagnosis. Suriin ang prutas at kumonsulta sa agricultural officer para sa kumpirmasyon.',
    'Choose a valid date range with From on or before To.': 'Pumili ng wastong petsa. Ang simula ay dapat bago o kapareho ng huling petsa.',
    'All scan records cleared': 'Nabura ang lahat ng rekord ng scan',
    'Unable to clear scan records.': 'Hindi mabura ang mga rekord ng scan.',
    'Notes saved': 'Na-save ang mga tala', 'Scan deleted': 'Nabura ang scan',
    'Analysis failed. Please try again or choose another image.': 'Nabigo ang pagsusuri. Subukang muli o pumili ng ibang larawan.',
    'Model unavailable. Using image heuristics.': 'Hindi magagamit ang modelo. Tantiya batay sa larawan ang ginagamit.',
    'Assessment displayed but could not be saved. Check available storage.': 'Naipakita ang pagsusuri ngunit hindi na-save. Tingnan ang bakanteng storage.',
  },

  translate(text) {
    if (this.language !== 'fil') return text;
    const key = text.trim();
    const assessment = key.match(/^(Grade A|Grade B|Grade C|Reject) Assessment$/);
    if (assessment) return text.replace(key, `Pagsusuri: ${assessment[1]}`);
    const translated = Object.hasOwn(this.filipino, key) ? this.filipino[key] : undefined;
    const step = key.match(/^Step (\d+) of (\d+)$/i);
    if (step) return text.replace(key, `Hakbang ${step[1]} sa ${step[2]}`);
    const period = key.match(/^Period: (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})$/);
    if (period) return text.replace(key, `Panahon: ${period[1]} hanggang ${period[2]}`);
    const more = key.match(/^\.\.\. and (\d+) more records$/);
    if (more) return text.replace(key, `... at ${more[1]} pang rekord`);
    const ago = key.match(/^(\d+)(m|h|d) ago$/);
    if (ago) return text.replace(key, `${ago[1]} ${ {m: 'minuto', h: 'oras', d: 'araw'}[ago[2]] } ang nakalipas`);
    const confidence = key.match(/^(\d+(?:\.\d+)?)% confidence$/);
    if (confidence) return text.replace(key, `${confidence[1]}% kumpiyansa`);
    const maturity = key.match(/^(\d+(?:\.\d+)?)% (Readiness|Maturity)$/);
    if (maturity) return text.replace(key, `${maturity[1]}% ${maturity[2] === 'Readiness' ? 'Kahandaan' : 'Pagkahinog'}`);
    const liveMaturity = key.match(/^(Harvestable|Developing) \((\d+)%\)$/);
    if (liveMaturity) return text.replace(key, `${this.filipino[liveMaturity[1]]} (${liveMaturity[2]}%)`);
    const possible = key.match(/^Possible (Anthracnose|Stem Canker|Soft Rot|Pest Damage|Sunburn|Fungal Spots)$/);
    if (possible) return text.replace(key, `Posibleng ${possible[1]}`);
    const rejected = key.match(/^Fruit classified as Reject with (\d+(?:\.\d+)?)% confidence\. Remove from harvest batch\.$/);
    if (rejected) return text.replace(key, `Nauri ang prutas bilang Reject na may ${rejected[1]}% kumpiyansa. Alisin sa pangkat ng aanihin.`);
    const premium = key.match(/^Excellent! Grade A fruit with (\d+(?:\.\d+)?)% confidence\. Ready for premium market\.$/);
    if (premium) return text.replace(key, `Napakahusay! Prutas na Grade A na may ${premium[1]}% kumpiyansa. Handa para sa premium na merkado.`);
    const reviewedReject = key.match(/^Fruit classified as Reject with (\d+(?:\.\d+)?)% confidence\. Verify the fruit against grading criteria before deciding its use\.$/);
    if (reviewedReject) return text.replace(key, `Nauri ang prutas bilang Reject na may ${reviewedReject[1]}% kumpiyansa. Suriin ang prutas ayon sa pamantayan ng paggrado bago magpasya sa paggamit nito.`);
    const reviewedPremium = key.match(/^Grade A fruit with (\d+(?:\.\d+)?)% confidence\. Verify physical grading criteria before making market decisions\.$/);
    if (reviewedPremium) return text.replace(key, `Prutas na Grade A na may ${reviewedPremium[1]}% kumpiyansa. Suriin ang pisikal na pamantayan ng paggrado bago magpasya tungkol sa pagbebenta.`);
    const session = key.match(/^(\d+) scans saved\. (Grade A: \d+, Grade B: \d+, Grade C: \d+, Reject: \d+)\. (\d+) with image-based disease flags; these are estimates\.$/);
    if (session) return text.replace(key, `${session[1]} scan ang na-save. ${session[2]}. ${session[3]} ang may palatandaan ng sakit batay sa larawan; mga tantiya lamang ang mga ito.`);
    const disease = key.match(/^Possible (Anthracnose|Stem Canker|Soft Rot|Pest Damage|Sunburn|Fungal Spots) based on image features\. Inspect the fruit and consult an agricultural officer before treatment\.$/);
    if (disease) return text.replace(key, `Posibleng ${disease[1]} batay sa larawan. Suriin ang prutas at kumonsulta sa agricultural officer bago gamutin.`);
    return translated === undefined ? text : text.replace(key, translated);
  },

  confirm(message) {
    return window.confirm(this.translate(message));
  },

  init(language) {
    this.observer = new MutationObserver(() => this.apply());
    this.setLanguage(language);
  },

  setLanguage(language) {
    this.language = language === 'fil' ? 'fil' : 'en';
    document.documentElement.lang = this.language;
    this.apply();
  },

  apply() {
    this.observer?.disconnect();
    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walk.nextNode())) {
      if (!node.parentElement || node.parentElement.closest('script,style,textarea,pre,code,[data-no-translate]')) continue;
      const previous = this.originals.get(node);
      const source = previous && node.nodeValue === previous.rendered ? previous.source : node.nodeValue;
      const rendered = this.translate(source);
      if (node.nodeValue !== rendered) node.nodeValue = rendered;
      this.originals.set(node, { source, rendered });
    }
    for (const element of document.querySelectorAll('[aria-label],[placeholder],[title]')) {
      if (element.closest('[data-no-translate]')) continue;
      const stored = this.attributes.get(element) || {};
      for (const key of ['aria-label', 'placeholder', 'title']) {
        if (!element.hasAttribute(key)) continue;
        const value = element.getAttribute(key), previous = stored[key];
        const source = previous && value === previous.rendered ? previous.source : value;
        const rendered = this.translate(source);
        if (value !== rendered) element.setAttribute(key, rendered);
        stored[key] = { source, rendered };
      }
      this.attributes.set(element, stored);
    }
    this.observer?.observe(document.body, { childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ['aria-label', 'placeholder', 'title'] });
  }
};
