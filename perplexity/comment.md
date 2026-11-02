ได้ครับ สำหรับ Fast-MCP ที่ส่งมา ผมพบงานวิจัยที่นำมาอ้างอิงได้ตรงกับกรอบงาน ทั้งด้าน Text-to-SQL, การใช้เครื่องมือของ LLM, ระบบหลายเอเจนต์ และการวัดความถูกต้องควบคู่ประสิทธิภาพ โดยควรเน้น **หลักฐาน** ที่รองรับข้ออ้างแต่ละประเภท ไม่ใช่เพิ่มจำนวนรายการอ้างอิงอย่างเดียว

ข้อสำคัญคือ งานวิจัยภายนอกช่วยรองรับแนวคิดและวิธีประเมิน แต่ไม่ได้ยืนยันตัวเลขของ Fast-MCP เช่น EX 98.6%, VES 0.962 หรือ latency 243.8 ms ตัวเลขเหล่านี้ต้องมีข้อมูลการทดลองและวิธีคำนวณของงานคุณเองประกอบด้วย

ผมตรวจจากเอกสารที่คุณวางมาเป็นหลัก ส่วนหน้า GitHub ที่ระบุยังดึงเนื้อหาไม่ได้ในการตรวจครั้งนี้ จึงยังไม่ได้ยืนยันว่าโค้ดและไฟล์ผลลัพธ์ตรงกับ README หรือไม่

## 1. Paper ที่ควรเพิ่ม และใช้รองรับส่วนใดของงาน

### กลุ่ม A: ปัญหา Text-to-SQL และการประเมินบนฐานข้อมูลจริง

| งานวิจัย | สาระสำคัญที่ใช้ได้ | ตำแหน่งที่เหมาะในงาน Fast-MCP |
|---|---|---|
| Yu et al. (2018), *Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task* | เสนอการประเมิน Text-to-SQL ที่ต้องทำงานกับ SQL และ schema ที่ไม่เคยเห็น ชุดข้อมูลมี 200 ฐานข้อมูล ครอบคลุม 138 โดเมน | บทที่ 2: พัฒนาการของ Text-to-SQL และข้อจำกัดด้านการ generalize ข้าม schema  [aclanthology](https://aclanthology.org/D18-1425/) |
| Li et al. (2023), *Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs* — BIRD | ให้ความสำคัญกับข้อมูลในฐานข้อมูลจริง ข้อมูลสกปรก ความรู้ภายนอก และประสิทธิภาพ SQL มี 12,751 คู่คำถาม–SQL บน 95 ฐานข้อมูล รวม 33.4 GB | บทที่ 1: ช่องว่างระหว่าง benchmark กับการใช้งานจริง; บทที่ 3: ที่มาของ EX และ VES  [arxiv](https://arxiv.org/abs/2305.03111) |
| Gao et al. (2024), *Text-to-SQL Empowered by Large Language Models: A Benchmark Evaluation* — DAIL-SQL | ศึกษา question representation, example selection และ example organization อย่างเป็นระบบ โดยพิจารณาความถูกต้อง ประสิทธิภาพ และความประหยัด | บทที่ 2: prompt engineering; บทที่ 3: baseline ที่ควบคุม token budget และตัวอย่างใน prompt  [dl.acm](https://dl.acm.org/doi/10.14778/3641204.3641221) |

สามเรื่องนี้ควรเป็นแกนหลัก เพราะช่วยแยกให้ชัดว่า “แปลภาษาธรรมชาติเป็น SQL ได้” กับ “ตอบถูกและทำงานได้มีประสิทธิภาพบนฐานข้อมูลขนาดใหญ่” เป็นคนละประเด็นกัน โดย BIRD เชื่อมกับโจทย์ของ Fast-MCP โดยตรงที่สุด [arxiv](https://arxiv.org/abs/2305.03111)

### กลุ่ม B: Baseline แบบแยกขั้นตอนและหลายเอเจนต์

| งานวิจัย | สาระสำคัญที่ใช้ได้ | ตำแหน่งที่เหมาะในงาน Fast-MCP |
|---|---|---|
| Pourreza & Rafiei (2023), *DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction* | ใช้แนวทางแยกปัญหาเป็นองค์ประกอบร่วมกับ self-correction เพื่อปรับปรุง Text-to-SQL | บทที่ 2: decomposed pipeline; บทที่ 3: การเปรียบเทียบจำนวน model calls กับคุณภาพคำตอบ  [arxiv](https://arxiv.org/abs/2304.11015) |
| Wang et al., *MAC-SQL: A Multi-Agent Collaborative Framework for Text-to-SQL* | ใช้ decomposer เป็นแกนกลาง ร่วมกับเอเจนต์ช่วยเลือกส่วนของฐานข้อมูลและแก้ SQL ที่ผิด | บทที่ 2: multi-agent Text-to-SQL; บทที่ 3: baseline แบบ Selector–Decomposer–Refiner  [arxiv](https://arxiv.org/abs/2312.11242) |
| Yao et al. (2023), *ReAct: Synergizing Reasoning and Acting in Language Models* | เสนอการสลับ reasoning กับ action เพื่อให้โมเดลวางแผน เรียกเครื่องมือ และปรับตามข้อมูลตอบกลับ | บทที่ 2: ฐานแนวคิดของ exploratory agent และเหตุผลที่ต้องวัดจำนวน tool calls  [iclr](https://iclr.cc/virtual/2023/poster/11003) |

ข้อควรระวัง: ReAct เป็นฐานแนวคิดของการให้เหตุผลสลับกับการกระทำ ไม่ใช่งานที่พิสูจน์โดยตรงว่า “LangChain SQL Agent ใช้ 6.8 turns” หรือ “เสียเวลา 24.8 วินาที” ตัวเลขเช่นนี้ต้องอ้างผลทดลองของคุณเอง ไม่ใช่อ้าง ReAct แทน [iclr](https://iclr.cc/virtual/2023/poster/11003)

### กลุ่ม C: การใช้เครื่องมือของ LLM และการประเมิน tool calling

| งานวิจัย | สาระสำคัญที่ใช้ได้ | ตำแหน่งที่เหมาะในงาน Fast-MCP |
|---|---|---|
| Schick et al., *Toolformer: Language Models Can Teach Themselves to Use Tools* | ศึกษาการให้โมเดลเรียนรู้ว่าจะเรียก API ใด เมื่อใด ส่ง argument อย่างไร และใช้ผลลัพธ์อย่างไร | บทที่ 2: เหตุผลของการเปลี่ยนจากสร้าง SQL อิสระไปสู่การเรียกเครื่องมือที่มี interface ชัดเจน  [ai.meta](https://ai.meta.com/research/publications/toolformer-language-models-can-teach-themselves-to-use-tools/) |
| Li et al. (2023), *API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs* | แยกความสามารถการใช้เครื่องมือเป็น planning, retrieving และ calling APIs พร้อมระบบประเมินที่รันได้จริง มี 73 tools และ 753 API calls ในชุดประเมิน | บทที่ 3: การประเมินเลือก tool ถูก ส่ง argument ถูก และได้ผลลัพธ์ถูก  [aclanthology](https://aclanthology.org/2023.emnlp-main.187/) |

API-Bank มีประโยชน์มากกับ Fast-MCP เพราะทำให้ไม่ต้องวัดเพียงว่า SQL รันได้หรือไม่ แต่สามารถแยกได้ว่า ความผิดพลาดมาจากการเลือกเครื่องมือ การกำหนดพารามิเตอร์ หรือการสรุปผลหลังได้รับข้อมูล [aclanthology](https://aclanthology.org/2023.emnlp-main.187/)

## 2. รายการบรรณานุกรมที่ตรวจสอบแล้วสำหรับนำไปจัดรูปแบบ

ด้านล่างเป็นข้อมูลบรรณานุกรมตั้งต้น โดยแยกรุ่นที่ตรวจพบให้ชัด ไม่เติมชื่อวารสารหรือ DOI ที่ยังไม่ได้ยืนยัน

1. Yu, T., Zhang, R., Yang, K., Yasunaga, M., Wang, D., Li, Z., Ma, J., Li, I., Yao, Q., Roman, S., Zhang, Z., & Radev, D. (2018). Spider: A large-scale human-labeled dataset for complex and cross-domain semantic parsing and text-to-SQL task. In *Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing* (pp. 3911–3921). Association for Computational Linguistics. DOI: `10.18653/v1/D18-1425`. [aclanthology](https://aclanthology.org/D18-1425/)

2. Li, J., Hui, B., Qu, G., Yang, J., Li, B., Li, B., Wang, B., Qin, B., Cao, R., Geng, R., Huo, N., Zhou, X., Ma, C., Li, G., Chang, K. C.-C., Huang, F., Cheng, R., & Li, Y. (2023). *Can LLM already serve as a database interface? A BIg bench for large-scale database grounded text-to-SQLs*. arXiv:2305.03111. DOI: `10.48550/arXiv.2305.03111`. หน้าเอกสารระบุว่าเป็นงาน NeurIPS 2023; รายการนี้อ้างรุ่น arXiv ที่ตรวจสอบได้ [arxiv](https://arxiv.org/abs/2305.03111)

3. Gao, D., Wang, H., Li, Y., Sun, X., Qian, Y., Ding, B., & Zhou, J. (2024). Text-to-SQL empowered by large language models: A benchmark evaluation. *Proceedings of the VLDB Endowment, 17*(5), 1132–1145. DOI: `10.14778/3641204.3641221`. [dl.acm](https://dl.acm.org/doi/10.14778/3641204.3641221)

4. Pourreza, M., & Rafiei, D. (2023). *DIN-SQL: Decomposed in-context learning of text-to-SQL with self-correction*. arXiv:2304.11015. สำหรับรายการตั้งต้นนี้ใช้รุ่น arXiv ที่ตรวจพบ [arxiv](https://arxiv.org/abs/2304.11015)

5. Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language models. *International Conference on Learning Representations*. รหัส preprint: `arXiv:2210.03629`. [iclr](https://iclr.cc/virtual/2023/poster/11003)

6. Li, M., Zhao, Y., Yu, B., Song, F., Li, H., Yu, H., Li, Z., Huang, F., & Li, Y. (2023). API-Bank: A comprehensive benchmark for tool-augmented LLMs. In *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing* (pp. 3102–3116). Association for Computational Linguistics. DOI: `10.18653/v1/2023.emnlp-main.187`. [aclanthology](https://aclanthology.org/2023.emnlp-main.187/)

สำหรับ MAC-SQL และ Toolformer มีแหล่งต้นฉบับรองรับชื่อและแนวคิดแล้ว แต่ควรนำ metadata จากรายการเผยแพร่ฉบับสุดท้ายเข้าระบบจัดการบรรณานุกรมก่อนลงเล่ม โดยเฉพาะ MAC-SQL ไม่ควรใช้คำกำกับ “TKDE ’24” ตาม README โดยยังไม่ได้ตรวจรายการตีพิมพ์นั้นแยกต่างหาก [arxiv](https://arxiv.org/abs/2312.11242)

## 3. จุดใน README ที่ควรแก้ก่อนใช้ในเล่มวิจัย

ประเด็นต่อไปนี้มาจากความสอดคล้องภายในข้อความที่คุณส่งมา ไม่ใช่ข้อสรุปจากการตรวจโค้ด

| จุดที่พบ | ความเสี่ยงทางวิชาการ | วิธีปรับให้ชัด |
|---|---|---|
| ใช้ “Sub-Second” แต่ total latency เท่ากับ 2.18 วินาที | ผู้อ่านอาจเข้าใจว่าคำตอบครบทั้งระบบใช้เวลาต่ำกว่า 1 วินาที | แยกคำว่า database/tool execution latency ออกจาก end-to-end response latency |
| DAIL-SQL ใช้เวลา 2.07 วินาที แต่ Fast-MCP 2.18 วินาที | ไม่รองรับการกล่าวว่า Fast-MCP เร็วที่สุดในตารางนี้ | รายงานว่า Fast-MCP ใช้ token น้อยกว่า แต่ DAIL-SQL มี end-to-end latency ต่ำกว่าในผลที่แสดง |
| ตารางหนึ่งระบุ Fast-MCP “100% Valid & Correct” แต่อีกตาราง EX 98.6% | ความถูกต้องและการรันได้ถูกนำมารวมกัน | แยก VSR ออกจาก EX และระบุว่าทั้งสองตารางใช้ชุดทดสอบเดียวกันหรือไม่ |
| รายงาน 605 tokens และ 510 tokens | ไม่ทราบว่าตัวเลขมาจากคนละ workload หรือคนละวิธีเฉลี่ย | ระบุจำนวนคำถาม ชุดทดสอบ และนิยาม input/output/total tokens |
| กล่าว \(O(\log N)\) กับงาน aggregate หลายตาราง | ข้ออ้างความซับซ้อนกว้างกว่าหลักฐานที่แสดง | ระบุขอบเขตว่าเป็น indexed lookup, จำนวนแถวที่จับคู่ หรือใช้ pre-aggregation พร้อม query plan และ scaling results |
| ระบุ benchmark ทั้ง live และ deterministic mock | หากไม่แยก อาจไม่ทราบว่าตารางใดเป็นการวัดจริง | แยกผล live กับ mock อย่างเด็ดขาด และให้ mock ใช้ตรวจการทำงานของ harness |
| Case 1 แสดง 3 โครงการมีตัวเลขเท่ากัน และตรงกับยอดระดับแผนกใน Case 3 | เป็นสัญญาณที่ควรตรวจ aggregation และการทำซ้ำจาก join | ตรวจ gold query และ cardinality ก่อนนำตัวอย่างไปอ้าง |
| เรียก DB-GPT-Hub ว่า CodeLlama-13B แต่ส่วน setup กล่าวว่าทุก paradigm เชื่อมกับ foundation model endpoint | ไม่ชัดว่าทดลองโมเดล fine-tuned จริง หรือเพียงจำลอง pipeline | เปิดเผย model checkpoint, training/fine-tuning และ endpoint ของแต่ละ baseline |

อีกจุดหนึ่งคือคำว่า “matching BIRD / Spider standards” ควรลดระดับเป็น “ใช้ตัวชี้วัดที่อ้างอิงจาก...” หากทดลองบนชุดข้อมูลสังเคราะห์ของคุณเอง เพราะ BIRD และ Spider เป็นทั้งชุดข้อมูลและกรอบโจทย์เฉพาะ ไม่ใช่เพียงชื่อของ metric ที่นำมาใช้แล้วจะทำให้คะแนนเปรียบเทียบกันได้ทันที [aclanthology](https://aclanthology.org/D18-1425/)

## 4. จะเพิ่มความน่าเชื่อถือของการทดลองอย่างไร

จากงานที่ค้นได้ ผมเสนอให้จัดวิธีวิจัยเป็นสามชั้น

### 4.1 วัดความถูกต้องแยกตามขั้นตอน

สำหรับ Fast-MCP ให้รายงานอย่างน้อย:

- Tool selection accuracy: เลือกเครื่องมือถูกหรือไม่
- Argument accuracy: รหัสแผนก ปีงบประมาณ เดือน และเงื่อนไขจำนวนเงินถูกหรือไม่
- Result correctness: ผลข้อมูลตรงกับ gold result หรือไม่
- Answer fidelity: คำตอบภาษาธรรมชาติสอดคล้องกับผลข้อมูลหรือไม่

การแยกเช่นนี้สอดคล้องกับแนวทางประเมินความสามารถด้าน planning, retrieval และ API calling ของ API-Bank และช่วยเปิดเผยความผิดพลาดที่ VSR เพียงตัวเดียวมองไม่เห็น [aclanthology](https://aclanthology.org/2023.emnlp-main.187/)

### 4.2 เปรียบเทียบให้แยก “ผลของ tool abstraction” ออกจาก “ผลของการปรับฐานข้อมูล”

เสนอให้มีเงื่อนไขทดลองเพิ่มเติมดังนี้:

| เงื่อนไข | สิ่งที่ช่วยตรวจสอบ |
|---|---|
| Text-to-SQL บนฐานข้อมูลและ index ชุดเดียวกับ Fast-MCP | Fast-MCP ได้เปรียบจาก semantic tools หรือจากการได้ index ที่ดีกว่า |
| Fast-MCP ที่ปิด index บางรายการ | ผลของ index ต่อ latency |
| เรียก parameterized SQL เดียวกันโดยตรง โดยไม่ผ่าน MCP | overhead ของ protocol |
| Fast-MCP กับคำถามที่อยู่นอกขอบเขตเครื่องมือ | ข้อจำกัดด้าน coverage และการ generalize |
| baseline ต้นฉบับหรือ reproduction ที่ระบุการดัดแปลงครบ | ความเที่ยงตรงของการเปรียบเทียบกับชื่อระบบที่อ้าง |

นี่เป็นข้อเสนอการออกแบบทดลองสำหรับงานของคุณ ไม่ใช่ข้ออ้างว่าบทความที่ค้นได้ใช้การทดลองเหมือนกันทั้งหมด โดยการเลือก baseline ควรอธิบายให้สอดคล้องกับองค์ประกอบจริงของ DAIL-SQL, DIN-SQL และ MAC-SQL [dl.acm](https://dl.acm.org/doi/10.14778/3641204.3641221)

### 4.3 เปิดเผยสูตรและฐานอ้างอิงของ VES

ควรระบุให้ครบว่า:

- ใช้สูตรจาก BIRD รุ่นใด
- ใช้ reference SQL ใดเป็นฐาน
- ตรวจผลลัพธ์ถูกต้องก่อนคำนวณประสิทธิภาพอย่างไร
- จัดการ timeout และ execution failure อย่างไร
- รายงานคะแนนบนสเกล 0–1 หรือสเกลเปอร์เซ็นต์

เหตุผลคือ BIRD เสนอ VES เพื่อพิจารณาประสิทธิภาพของ SQL ควบคู่กับความถูกต้อง ไม่ใช่คะแนนที่ยืนยันได้จากการมี index หรือมี latency ต่ำเพียงอย่างเดียว [arxiv](https://arxiv.org/pdf/2305.03111.pdf)

## 5. ตัวอย่างข้อความสำหรับนำไปปรับใช้ในบทที่ 2

> การประเมินระบบแปลงภาษาธรรมชาติเป็นคำสั่ง SQL จำเป็นต้องพิจารณาทั้งความสามารถในการทำงานข้ามโครงสร้างฐานข้อมูลและความถูกต้องของผลลัพธ์ โดย Spider เสนอการประเมินบนฐานข้อมูลและคำสั่ง SQL ที่แตกต่างกันระหว่างชุดฝึกกับชุดทดสอบ เพื่อศึกษาความสามารถในการถ่ายโอนของระบบไปยัง schema ใหม่ (Yu et al., 2018) ขณะที่ BIRD ขยายความสนใจไปยังฐานข้อมูลขนาดใหญ่ โดยเน้นความท้าทายจากค่าข้อมูล ความรู้ภายนอก และประสิทธิภาพการประมวลผล SQL (Li et al., 2023) [aclanthology](https://aclanthology.org/D18-1425/)
>
> แนวทางปรับปรุง Text-to-SQL มีทั้งการออกแบบ prompt และการคัดเลือกตัวอย่างอย่างเป็นระบบ เช่น DAIL-SQL ตลอดจนการแยกกระบวนการแก้ปัญหาและตรวจแก้คำสั่ง เช่น DIN-SQL อย่างไรก็ตาม แนวทางเหล่านี้ยังแตกต่างจากการกำหนดเครื่องมือเชิงความหมายที่มีขอบเขตและพารามิเตอร์ชัดเจน ซึ่งควรประเมินเพิ่มเติมทั้งด้านความถูกต้องของการเลือกเครื่องมือและการส่งอาร์กิวเมนต์ ตามแนวทางการประเมินระบบ LLM ที่ใช้ API ภายนอก (Gao et al., 2024; Pourreza & Rafiei, 2023; Li et al., 2023) [dl.acm](https://dl.acm.org/doi/10.14778/3641204.3641221)

เวลาใช้งานจริงควรแยก Li et al. ที่เป็น BIRD ออกจาก Li et al. ที่เป็น API-Bank ให้ชัด เช่นใช้ชื่อชุดประเมินกำกับในเนื้อหา และให้โปรแกรมจัดการบรรณานุกรมจัดรูปแบบตามคู่มือของสถาบัน

สำหรับงานนี้ แกนที่น่าเชื่อถือที่สุดจึงไม่ใช่การกล่าวว่า “MCP ทำให้ SQL เร็วขึ้น” โดยตรง แต่เป็นการตั้งข้อเสนอว่า การใช้ semantic tools ที่มีขอบเขตชัดเจนร่วมกับการออกแบบ query และ index อาจลดภาระการสร้างคำสั่งและการสำรวจ schema ใน workload ที่กำหนดไว้ แล้วใช้การทดลองแยกองค์ประกอบพิสูจน์ว่าแต่ละส่วนสร้างประโยชน์มากน้อยเพียงใด

โครงสร้าง README ของ Fast-MCP ที่ส่งมา ครอบคลุมทั้งแนวคิด ผลทดลอง วิธีติดตั้ง และการอ้างอิง แต่ยังมีลักษณะเป็น “บทความนำเสนอผลวิจัยผสมคู่มือใช้งาน” มากกว่า README ของชุด benchmark ที่ผู้อื่นนำไปรันซ้ำได้สะดวก

สิ่งที่ควรแก้เป็นอันดับแรกคือ **ลำดับ**: ให้ผู้อ่านทราบก่อนว่าโครงการนี้คืออะไร ทดลองอะไรได้ และรันอย่างไร แล้วจึงแสดงผลกับรายละเอียดการประเมิน ไม่ควรวางผลเปรียบเทียบหลายชุดและตัวอย่างคำตอบยาว ๆ ก่อนขั้นตอนติดตั้ง

การตรวจด้านล่างอ้างอิงเฉพาะ README ที่คุณวางไว้ในบทสนทนา ไม่ใช่การยืนยันโค้ดหรือผลทดลองใน repository

## 1. ภาพรวมโครงสร้างปัจจุบัน

| ส่วนปัจจุบัน | ข้อสังเกต | ข้อเสนอ |
|---|---|---|
| ชื่อโครงการและ badges | ระบุตัวตนชัด แต่ badges ด้านคะแนนอยู่ก่อนคำอธิบายขอบเขตการทดลอง | คง License/Python ไว้ ส่วน EX/VES ย้ายลง Results หรือให้ลิงก์ไปผลทดลองที่ระบุรุ่น |
| Academic Note | เหมาะสมกับงานที่อยู่ระหว่างพิจารณา | เพิ่มสถานะของ artifact และแยกให้ชัดว่า manuscript กับ software เป็นคนละสิ่ง |
| Overview & Motivation | อธิบายปัญหาได้ แต่รวมปัญหา สถาปัตยกรรม และผลลัพธ์ไว้ในส่วนเดียว | แยกเป็น Overview, Scope และ Architecture |
| Latency profile แบบแถบข้อความ | อ่านภาพรวมได้ แต่ซ้ำกับตารางผลถัดมา | ตัดออก หรือย้ายเป็น visualization ในเอกสารผลทดลอง |
| Live LLM benchmark | มีรายละเอียดมาก แต่ยังไม่อธิบาย experimental setup ก่อน | ย้ายไว้หลัง Evaluation Protocol |
| Standard metrics | เป็นสาระสำคัญ แต่ชื่อส่วนสื่อว่าผ่านมาตรฐานมากกว่าที่ README อธิบาย | เปลี่ยนเป็น Accuracy and Efficiency Evaluation และระบุชุดข้อมูล/สูตร |
| Why Naive SQL Fails | ผสมคำอธิบายเชิงเทคนิคกับข้อสรุปเชิงเปรียบเทียบ | ย้ายไป Design Rationale หรือเอกสารวิเคราะห์ข้อผิดพลาด |
| Speed benchmark | ซ้ำบางส่วนกับ Overview และ live benchmark | แยกชัดว่าเป็น database-only benchmark |
| Qualitative responses | ยาวและเบียดส่วนใช้งานออกไปด้านล่าง | คงตัวอย่างสั้นหนึ่งกรณี แล้วแยกกรณีเต็มไปเอกสารอื่น |
| Configuration | อยู่ช้าเกินไปสำหรับผู้ที่จะทดลอง | ย้ายขึ้นก่อน Quickstart หรือรวมเป็น Installation and Configuration |
| Quickstart | มีคำสั่งหลักครบ แต่ขาด prerequisites ที่ชัดเจน | เพิ่มการเตรียม environment และติดตั้ง dependencies ตามที่โค้ดต้องใช้จริง |
| Custom Scale Testing | มีประโยชน์ต่อการรันซ้ำ | อยู่ต่อจาก Reproduction |
| Repository Structure | เหมาะสม แต่คำอธิบายบางไฟล์เป็นข้ออ้างด้านประสิทธิภาพ | เปลี่ยนเป็นคำอธิบายหน้าที่ของไฟล์อย่างเป็นกลาง |
| Citation | มีแล้ว แต่รายการ `@article` กับ `journal={Under Review}` ยังไม่ชัดว่าใช้อ้าง software หรือ manuscript | แยก Citation for Software และ Associated Manuscript |

## 2. โครงสร้างที่แนะนำ

สำหรับเป้าหมาย “repository ประกอบงานวิจัยที่ให้ผู้อื่นทดลองซ้ำได้” ผมแนะนำโครงสร้างนี้:

```text
# Fast-MCP Enterprise Benchmark Suite

Badges
Short project description
Research/artifact status

## Overview
## Scope and Non-Goals
## Architecture

## Installation
### Requirements
### Environment Setup
### Provider Configuration

## Quickstart
### Offline Smoke Test
### Live LLM Evaluation
### Database-Only Benchmark

## Dataset
### Schema and Scale
### Data Generation
### Synthetic Data Limitations

## Evaluation Protocol
### Workloads and Ground Truth
### Baselines and Implementation Fidelity
### Metrics
### Timing Boundaries
### Experimental Environment

## Results
### End-to-End Live Evaluation
### Accuracy and Efficiency
### Database Execution Performance

## Reproducing the Reported Results
### Exact Commands and Configurations
### Output Files
### Custom-Scale Experiments

## Example
## Limitations
## Repository Structure
## Documentation
## Citation
## License
```

จุดสำคัญคือ Results ต้องตามหลังคำอธิบายว่าผลเหล่านั้นวัดอะไร และ Quickstart ต้องมาก่อนรายละเอียดผลทดลองทั้งหมด

## 3. ส่วนต้นควรเขียนใหม่ให้บอกตัวตนชัดกว่าเดิม

ปัจจุบัน README ใช้ชื่อ “benchmark suite” แต่เนื้อหาช่วงต้นเน้นการเสนอ Fast-MCP เป็นระบบที่เหนือกว่า baseline ทำให้ผู้อ่านอาจไม่แน่ใจว่า repository นี้เป็น:

- implementation ของ Fast-MCP
- benchmark harness สำหรับเปรียบเทียบหลายระบบ
- artifact ประกอบบทความ
- หรือทั้งสามอย่าง

ควรระบุให้ชัดตั้งแต่ย่อหน้าแรก ตัวอย่างที่ปรับจากเนื้อหาเดิมโดยไม่เพิ่มข้ออ้างผลทดลอง:

```markdown
# Fast-MCP Enterprise Benchmark Suite

A research implementation and evaluation harness for comparing
semantic-tool-based database access with Text-to-SQL and agentic
database workflows on a synthetic enterprise SQLite database.

The repository includes:
- A synthetic enterprise database generator.
- The Fast-MCP semantic tool implementation.
- Baseline implementations and evaluation runners.
- Scripts for measuring correctness, latency, token usage, and tool calls.

## Research Status

The associated manuscript is under peer review.

This repository is intended to support inspection and reproduction
of the experimental workflow. Live API results and deterministic
mock outputs are documented separately.
```

ประโยคท้ายควรใช้เมื่อคุณแยกเอกสารและผลลัพธ์ live/mock แล้วจริง ไม่ใช่ใส่ข้อความก่อนปรับระบบให้ตรงกัน

## 4. เพิ่ม Scope and Non-Goals ก่อนนำเสนอความเร็ว

ส่วนนี้ขาดอยู่ และสำคัญต่อการตีความผลของ semantic tools เพราะผู้อ่านควรทราบว่าเครื่องมือรองรับโจทย์กว้างแค่ไหน

ควรตอบให้ได้อย่างน้อย:

| ประเด็น | สิ่งที่ควรระบุ |
|---|---|
| ขอบเขตฐานข้อมูล | SQLite, schema ที่กำหนด และข้อมูลสังเคราะห์ |
| ขอบเขตคำถาม | รองรับ intent หรือ business workload ใดบ้าง |
| การเตรียมล่วงหน้า | มี SQL templates, indexes หรือ pre-aggregation อะไร |
| ผู้กำหนดเครื่องมือ | นักพัฒนากำหนดไว้ก่อน หรือสร้างระหว่างรัน |
| คำถามนอกขอบเขต | ปฏิเสธ ส่งต่อ baseline หรือพยายามตอบอย่างไร |
| เป้าหมายที่ไม่ได้ทดสอบ | เช่น การใช้งานกับ schema ใหม่โดยไม่ปรับเครื่องมือ หากยังไม่ได้ทดลอง |

ส่วนนี้ช่วยให้ผู้อ่านแยก “ประสิทธิภาพบน workload ที่เตรียมรองรับ” ออกจาก “ความสามารถตอบคำถามฐานข้อมูลทั่วไป” โดยไม่ต้องตีความเอง

## 5. แยกผลทดลองสามชนิดให้ชัด

README ปัจจุบันมีตารางหลายชุด แต่ยังเชื่อมกันไม่พอว่ามาจากการทดลองเดียวกันหรือคนละชุด

แนะนำให้แต่ละตารางมีคำอธิบายสั้น ๆ ก่อนตารางในรูปแบบเดียวกัน:

```text
Run type:
Dataset:
Workload / number of questions:
Model and endpoint:
Repetitions:
Timing boundary:
Aggregation method:
Raw output:
```

### 5.1 End-to-End Live Evaluation

ใช้แสดง:

- เวลาที่รวมการเรียกโมเดลกับฐานข้อมูล
- token usage
- model calls
- tool calls
- สถานะความถูกต้องของผลลัพธ์

ควรระบุด้วยว่ารวมขั้นตอนสรุปคำตอบภาษาธรรมชาติหลังเรียกเครื่องมือแล้วหรือไม่

### 5.2 Accuracy and Efficiency

ใช้แสดง:

- EX
- VSR
- VES
- จำนวนคำถามทั้งหมด
- จำนวนสำเร็จ/ล้มเหลว
- วิธีจัดการ timeout

ควรแยกนิยาม VSR สำหรับระบบสร้าง SQL กับระบบเรียก semantic tools ให้ชัด เพราะรายการที่ถูกประเมินอาจไม่ใช่สิ่งเดียวกัน

### 5.3 Database Execution Performance

ใช้แสดงเฉพาะ:

- เวลา query/tool execution
- SQL หรือ tool ที่ทดสอบ
- index configuration
- cache condition
- จำนวนรอบและสถิติที่รายงาน

ใน README ของคุณ 243.8 ms กับ 2,182.1 ms จึงควรอยู่คนละขอบเขตการวัดอย่างชัดเจน ไม่ใช้คำว่า “latency” ลอย ๆ ครอบทั้งสองค่า

## 6. ย้ายตัวอย่างยาวและคำอธิบายเชิงลึกออกจากหน้าแรก

แนะนำให้ README เหลือตัวอย่างสั้นเพียงหนึ่งกรณี:

```text
Natural-language question
        ↓
Selected semantic tool and arguments
        ↓
Short result preview
```

ตัวอย่างคำตอบทั้งสามกรณี ตารางการเงินเต็ม และ failure analysis สามารถแยกไปเอกสารเฉพาะ

โครงสร้างเอกสารที่เสนอเพิ่มเติม:

```text
docs/
├── architecture.md
├── dataset.md
├── evaluation_protocol.md
├── baseline_implementations.md
├── reproducibility.md
├── examples.md
└── limitations.md
```

นี่เป็นโครงสร้างที่เสนอให้เพิ่ม ไม่ใช่รายการไฟล์ที่ยืนยันว่ามีอยู่แล้ว

ส่วน README ควรเก็บเฉพาะข้อมูลที่ช่วยให้ผู้อ่านตอบได้ว่า “เกี่ยวกับอะไร ใช้อย่างไร และต้องอ่านอะไรต่อเพื่อประเมินผล”

## 7. ปรับ Quickstart ให้แยกการตรวจระบบกับการทำซ้ำผลวิจัย

Quickstart ปัจจุบันใช้คำสั่งเดียวกันได้ทั้ง Live และ Mock ซึ่งสะดวก แต่ทำให้ผู้อ่านเสี่ยงเข้าใจว่ารันสำเร็จแล้วเท่ากับทำซ้ำผลวิจัยสำเร็จ

ควรแยกเป็นสองเส้นทาง:

| เส้นทาง | วัตถุประสงค์ | สิ่งที่ควรแจ้ง |
|---|---|---|
| Offline smoke test | ตรวจว่า generator และ evaluation pipeline ทำงาน | ไม่ใช้ผลนี้ยืนยัน live model performance |
| Live evaluation | ทดลองผ่าน API จริง | ต้องมี API key, ค่าใช้จ่าย และ model configuration |
| Reported-results reproduction | ทำซ้ำตารางในบทความ | ต้องใช้ configuration, seed, workload และ environment ที่ระบุ |

ส่วน “Reproducing the Reported Results” ต้องบอกด้วยว่าคำสั่งใดสร้างตารางใด เช่น:

```text
README table                      Evaluation script                 Output
End-to-end comparison             run_all_comparisons.py           ...
Accuracy and efficiency           benchmark_suite.py               ...
Database execution performance    test_real_800k.py                ...
```

ให้เติม output จากพฤติกรรมจริงของสคริปต์ ไม่ควรเดาชื่อไฟล์ขึ้นมา

## 8. ปรับชื่อหัวข้อและภาษาที่ทำให้ดูเป็นงานวิจัยมากขึ้น

| ข้อความเดิม | ข้อเสนอ |
|---|---|
| `Why Naive SQL Fails in Real Enterprise Accuracy` | `Observed Error Categories` |
| `Standard Accuracy & Efficiency Metrics (BIRD / Spider Standard)` | `Accuracy and Efficiency Evaluation` |
| `800,000 Rows / Real-Scale Schema` | `800,000-Row Synthetic Enterprise Schema` |
| `100% Valid & Correct` | แยกเป็น validity และ correctness พร้อมจำนวนกรณีทดสอบ |
| `Eliminates 100% of exploratory tool thrashing` | ระบุค่าที่วัดได้และขอบเขต workload แทนคำสรุปเหมารวม |
| `Parameterized O(log N) compound indexed primitives` ใน tree | `Parameterized semantic database tools` |
| `Single-turn sub-second agent synthesizer` ใน tree | `Agent orchestration and response synthesis` |

คำอธิบายใน repository tree ควรบอก “ไฟล์ทำอะไร” ไม่ใช่ “ไฟล์ให้ผลดีแค่ไหน” ส่วนข้ออ้างด้านประสิทธิภาพให้ไปอยู่ Results พร้อมเงื่อนไขการวัด

## 9. ลำดับการแก้ที่คุ้มที่สุด

1. ย้าย Installation และ Quickstart ขึ้นก่อน Results
2. เพิ่ม Scope และ Architecture แบบสั้น
3. แยก live, mock และ database-only ให้ชัด
4. เพิ่ม Evaluation Protocol ก่อนตารางผล
5. ย้าย qualitative responses และรายละเอียด baseline ไป `docs/`
6. เพิ่ม Limitations และเชื่อมตารางกับ raw outputs
7. แยกการอ้างอิง software ออกจาก manuscript

เมื่อจัดตามนี้ README จะเปลี่ยนจากหน้าที่เน้นประกาศผลลัพธ์ ไปเป็นเอกสารที่ช่วยให้กรรมการหรือผู้ประเมินตรวจสอบได้อย่างเป็นขั้นตอนว่า ระบบทำอะไร ขอบเขตอยู่ตรงไหน และผลแต่ละชุดเกิดจากวิธีทดลองใด

ควรเพิ่มหรือปรับอีก 6 หัวข้อครับ โดยเน้นให้กรรมการตอบได้เร็วว่า “งานนี้เสนออะไร ทดลองอย่างเป็นธรรมหรือไม่ และตรวจสอบผลจากตรงไหน” มากกว่าการเพิ่มรายละเอียดทางเทคนิคให้ยาวขึ้น

สำหรับ README ของคุณ ผมให้ความสำคัญสูงสุดกับ **เส้นทางตรวจสอบ** จากคำถามวิจัย → วิธีทดลอง → ผลลัพธ์ → ไฟล์หลักฐาน แนวทางนี้สอดคล้องกับเกณฑ์ artifact ของ ACM ที่เน้นเอกสารครบ ความสอดคล้องกับบทความ ความครบถ้วนขององค์ประกอบ และการรันได้จริง [acm](https://www.acm.org/publications/policies/artifact-review-and-badging-current)

## 1. เพิ่ม “Reviewer Guide” ให้กรรมการรู้ว่าควรอ่านตรงไหน

วางถัดจากคำอธิบายโครงการ ไม่ต้องยาวเกินหนึ่งตาราง

| สิ่งที่ต้องการตรวจ | ส่วนที่ควรอ่าน |
|---|---|
| งานนี้เสนออะไรใหม่ | Research Questions and Contributions |
| ระบบทำงานอย่างไร | Architecture and Execution Flow |
| เปรียบเทียบอย่างเป็นธรรมหรือไม่ | Evaluation Design and Baseline Controls |
| ตัวเลขแต่ละค่าหมายถึงอะไร | Metric Definitions and Timing Boundaries |
| ตรวจสอบหรือรันซ้ำผลได้อย่างไร | Results-to-Evidence Map |
| ผลใช้ได้ภายใต้เงื่อนไขใด | Limitations and Threats to Validity |

นี่เป็นข้อเสนอการจัดเอกสารสำหรับ README นี้โดยเฉพาะ ไม่ใช่หัวข้อบังคับตาม ACM แต่ช่วยทำให้ README ทำหน้าที่เป็นคู่มือเดินตามการทดลอง ซึ่งสอดคล้องกับคำแนะนำ artifact evaluation ที่ให้ระบุขั้นตอน คำสั่ง และตำแหน่งข้อมูลอย่างชัดเจน [icpe2026.spec](https://icpe2026.spec.org/tracks-and-submissions/artifact-evaluation-track/)

## 2. แยก “Research Questions” ออกจาก “Contributions”

ในต้นฉบับ ส่วน Overview รวมปัญหา วิธีแก้ และข้ออ้างผลลัพธ์ไว้ด้วยกัน ควรแยกให้เห็นว่า “ต้องการทดสอบอะไร” กับ “พัฒนาอะไรขึ้นมา”

### Research Questions — คำถามที่ต้องพิสูจน์

ตัวอย่างที่เสนอให้ปรับใช้ โดยต้องตรงกับการทดลองจริง:

- RQ1: Fast-MCP ให้ความถูกต้องของผลลัพธ์ต่างจาก baseline อย่างไรบน workload ที่กำหนด?
- RQ2: Fast-MCP ลด end-to-end latency, token usage และจำนวน tool calls ได้มากน้อยเพียงใด?
- RQ3: ความได้เปรียบที่พบเกิดจาก semantic tool abstraction, การปรับ SQL/index หรือองค์ประกอบใด?
- RQ4: เมื่อเพิ่มจำนวนแถว ประสิทธิภาพของแต่ละวิธีเปลี่ยนแปลงอย่างไร?

### Contributions — สิ่งที่งานส่งมอบ

จากคำอธิบายโครงการของคุณ สามารถจัดเป็น:

1. ชุด semantic tools สำหรับ workload ทางการเงินที่ระบุขอบเขตไว้
2. ตัวสร้างฐานข้อมูล enterprise สังเคราะห์
3. evaluation harness สำหรับเปรียบเทียบหลายแนวทาง
4. ชุดข้อมูลผลทดลองและคำสั่งสำหรับตรวจสอบซ้ำ

ไม่ควรเขียน “เร็วกว่าอย่างมีนัยสำคัญ” หรือ “กำจัดข้อผิดพลาดทั้งหมด” ใน Contributions หากยังไม่มีหลักฐานที่รองรับถ้อยคำนั้น

## 3. เปลี่ยน “Architecture” เป็น “Architecture and Execution Flow”

กรรมการควรเห็นภาพเส้นทางทำงานก่อนอ่านชื่อไฟล์หรือศัพท์ MCP แนะนำให้มีแผนภาพเพียงหนึ่งภาพ พร้อมระบุขอบเขตที่จับเวลา

```text
User question
      ↓
LLM selects a semantic tool
      ↓
Tool name and arguments are validated
      ↓
Parameterized SQL is executed
      ↓
Structured results are returned
      ↓
Natural-language answer is generated
```

แผนภาพนี้เป็นแม่แบบ ต้องแก้ให้ตรงกับโค้ดจริง โดยเฉพาะสองประเด็นที่ยังไม่ชัดจาก README:

- หลังได้ผลฐานข้อมูล มีการเรียก LLM เพื่อสรุปคำตอบอีกครั้งหรือไม่?
- “1 turn” หมายถึงหนึ่งข้อความจากผู้ใช้ หนึ่ง model call หรือหนึ่ง tool call?

ควรใส่นิยามใต้ภาพแทนการให้กรรมการอนุมานจากตาราง หากมีการเรียกโมเดลรอบหลัง ก็ต้องระบุว่ารวมอยู่ใน end-to-end latency หรือไม่

## 4. เพิ่ม “Evaluation Design and Baseline Controls”

หัวข้อนี้ควรอยู่ก่อน Results เพราะช่วยให้กรรมการรู้ว่าความแตกต่างของผลมาจากอะไร

ใช้ตารางสรุปแทนคำอธิบายยาว:

| ปัจจัย | สิ่งที่ต้องเปิดเผย |
|---|---|
| โมเดล | ชื่อรุ่นและ configuration ของแต่ละระบบ |
| ฐานข้อมูล | ใช้ข้อมูลและ snapshot เดียวกันหรือไม่ |
| Index | ทุกระบบเข้าถึง index ชุดเดียวกันหรือไม่ |
| Prompt และ tools | แต่ละระบบได้รับ schema, ตัวอย่าง และความรู้ล่วงหน้าอะไร |
| Baseline implementation | ใช้ต้นฉบับ ดัดแปลง หรือสร้างใหม่ตามแนวคิด |
| ข้อจำกัดการรัน | timeout, retry และจำนวนรอบสูงสุด |
| การวัดเวลา | รวมขั้นตอนใดบ้าง |
| ผลล้มเหลว | นับเป็นผิด ตัดออก หรือรายงานแยกอย่างไร |

สำหรับ Fast-MCP ประเด็นที่ควรอธิบายเป็นพิเศษคือ “ระบบที่มี SQL templates เตรียมไว้” เปรียบเทียบกับ “ระบบที่ต้องสร้าง SQL เอง” ภายใต้ข้อมูลและการเตรียมล่วงหน้าแบบใด ไม่จำเป็นต้องทำให้ทุกระบบเหมือนกันทั้งหมด แต่ต้องบอกความต่างให้ตรวจสอบได้

การเปิดเผยสภาพแวดล้อม ซอฟต์แวร์ และขั้นตอนรันอย่างเจาะจงยังสอดคล้องกับคำแนะนำ README สำหรับการประเมิน artifact ด้านประสิทธิภาพ [icpe2026.spec](https://icpe2026.spec.org/tracks-and-submissions/artifact-evaluation-track/)

## 5. เพิ่ม “Results-to-Evidence Map” แทนการให้กรรมการหาไฟล์เอง

นี่เป็นหัวข้อที่น่าจะช่วย README ของคุณได้มากที่สุด เพราะมีผลหลายตาราง แต่ยังไม่เห็นความสัมพันธ์กับคำสั่งและไฟล์ต้นทางครบถ้วน

ตัวอย่างโครงตาราง:

| ผลที่รายงาน | สคริปต์ที่ระบุใน README | หลักฐานที่ต้องเชื่อมให้ครบ |
|---|---|---|
| End-to-end latency และ token usage | `run_all_comparisons.py` | configuration และ raw logs ของ run ที่ใช้สร้างตาราง |
| EX, VSR และ VES | `benchmark_suite.py` | ผลระดับคำถาม, gold results และคะแนนรวม |
| Database-only latency | `test_real_800k.py` | timing records และ query/index configuration |
| Scalability | ต้องระบุสคริปต์ให้ชัด | ผลแต่ละขนาดฐานข้อมูลและวิธีสรุป |

ชื่อสคริปต์ข้างต้นมาจาก README ของคุณ ส่วนความเชื่อมโยงกับไฟล์จริงยังต้องตรวจโค้ดก่อนเติม

ควรระบุ version หรือ commit ของชุดผลด้วย เพื่อไม่ให้ตารางใน README เปลี่ยนตามโค้ดล่าสุดโดยไม่มีจุดอ้างอิง แนวคิดการเชื่อม artifact กับผลหลักของบทความตรงกับเกณฑ์ “consistent” ของ ACM [acm](https://www.acm.org/publications/policies/artifact-review-and-badging-current)

## 6. แยก “Result Interpretation” ออกจาก “Limitations”

อย่าให้ Results มีแต่ตาราง และอย่ารวมข้อจำกัดไว้เป็นหมายเหตุเล็กท้ายหน้า

### Result Interpretation — ผลบอกอะไร

จากตารางที่คุณส่งมา สามารถเขียนอย่างตรงไปตรงมาได้ว่า:

> ในผล live evaluation ที่รายงาน DAIL-SQL มี end-to-end latency ต่ำกว่า Fast-MCP เล็กน้อย ขณะที่ Fast-MCP ใช้ token น้อยกว่า จึงควรอภิปรายผลในฐานะความแตกต่างระหว่างความเร็วกับ token usage ไม่ใช่สรุปว่า Fast-MCP เร็วที่สุดทุกมิติ

อีกตัวอย่าง:

> ค่า database latency ต่ำกว่าหนึ่งวินาที ไม่ได้หมายความว่าเวลาตอบกลับครบทั้งระบบต่ำกว่าหนึ่งวินาที

ข้อความลักษณะนี้ช่วยตีความตัวเลข โดยไม่เพิ่มข้ออ้างเกินข้อมูลที่มี

### Limitations and Threats to Validity — ผลยังไม่บอกอะไร

แนะนำให้จัดเป็นสามคำถามที่อ่านง่าย:

| คำถาม | สิ่งที่ควรชี้แจง |
|---|---|
| อะไรอาจทำให้ผลคลาดเคลื่อน? | ความผันผวนของ API, cache, จำนวนรอบทดลอง และวิธีสร้าง gold results |
| อะไรอาจทำให้การเปรียบเทียบไม่เท่ากัน? | Index, SQL templates, prompt knowledge และความครบถ้วนของ baseline |
| ผลยังใช้สรุปไปถึงอะไรไม่ได้? | ฐานข้อมูลจริง schema อื่น และคำถามนอกขอบเขต tools หากยังไม่ได้ทดสอบ |

## โครงสร้างฉบับอ่านสำหรับกรรมการ

เมื่อรวมกับข้อเสนอเดิม ผมแนะนำให้ใช้หัวข้อหลักประมาณนี้ โดยย้ายรายละเอียดปลีกย่อยไปเอกสารประกอบ:

```markdown
# Fast-MCP Enterprise Benchmark Suite

## Overview and Research Status
## Reviewer Guide
## Research Questions and Contributions
## Scope and Supported Workloads
## Architecture and Execution Flow
## Quickstart
## Evaluation Design and Baseline Controls
## Metric Definitions and Timing Boundaries
## Results and Interpretation
## Results-to-Evidence Map
## Limitations and Threats to Validity
## Detailed Documentation
## Citation and License
```

ถ้าต้องเลือกแก้ก่อนเพียงสามอย่าง ให้ทำ Research Questions and Contributions, Evaluation Design and Baseline Controls และ Results-to-Evidence Map เพราะสามส่วนนี้จะเชื่อม “สิ่งที่เสนอ–วิธีพิสูจน์–หลักฐาน” ให้กรรมการอ่านได้ต่อเนื่อง โดยไม่ต้องเพิ่มตารางผลทดลองอีกชุด

