จากการทดลองที่ระบุใน README ควรใช้ Research Questions จำนวน 3 ข้อหลัก โดยแยกการประเมินเป็นความถูกต้อง ประสิทธิภาพตั้งแต่รับคำถามจนได้คำตอบ และประสิทธิภาพการประมวลผลฐานข้อมูล เพื่อให้แต่ละข้อมีผลทดลองรองรับโดยตรง

ส่วนคำถามว่า “ประโยชน์เกิดจาก semantic tools หรือ index” และ “ประสิทธิภาพเปลี่ยนอย่างไรเมื่อเพิ่มจำนวนแถว” ยังไม่ควรเป็นคำถามหลัก เพราะข้อมูลที่ส่งมายังไม่แสดงผลการทดลองแยกองค์ประกอบหรือผลหลายขนาดฐานข้อมูลอย่างครบถ้วน

## Research Questions ฉบับภาษาอังกฤษสำหรับใส่ README

```markdown
## Research Questions

This benchmark evaluates Fast-MCP on predefined financial workloads
using a synthetic enterprise SQLite database containing 800,000
transaction ledger rows. The evaluation addresses three research
questions:

### RQ1: Execution Correctness
How does Fast-MCP compare with the evaluated Text-to-SQL and agentic
baselines in execution accuracy on the synthetic enterprise
financial workload suite?

### RQ2: End-to-End Efficiency
How does Fast-MCP compare with the evaluated baselines in end-to-end
latency, token usage, and the number of model and tool calls during
live LLM evaluation?

### RQ3: Database Execution Performance
How does the database execution latency of Fast-MCP's parameterized
semantic tools compare with that of the corresponding baseline SQL
queries across the four evaluated financial workloads?
```

ถ้อยคำนี้เน้น **เปรียบเทียบ** ไม่ตั้งสมมติฐานล่วงหน้าว่า Fast-MCP ต้องดีกว่าทุกมิติ และจำกัดข้อสรุปไว้กับ workload และฐานข้อมูลที่ทดลองจริง

## ฉบับภาษาไทยสำหรับใส่เล่มวิจัย

### คำถามวิจัยที่ 1: ความถูกต้องของผลการประมวลผล

> Fast-MCP มีความถูกต้องของผลการประมวลผลเมื่อเปรียบเทียบกับวิธีฐานด้าน Text-to-SQL และระบบเอเจนต์ที่นำมาประเมินอย่างไร บนชุดภาระงานทางการเงินของฐานข้อมูลองค์กรสังเคราะห์?

### คำถามวิจัยที่ 2: ประสิทธิภาพการทำงานตั้งแต่ต้นจนจบ

> Fast-MCP มีระยะเวลาตอบสนองตั้งแต่ต้นจนจบ ปริมาณการใช้โทเคน และจำนวนครั้งในการเรียกโมเดลและเครื่องมือแตกต่างจากวิธีฐานที่นำมาประเมินอย่างไร เมื่อทดลองผ่านบริการ LLM จริง?

### คำถามวิจัยที่ 3: ประสิทธิภาพการประมวลผลฐานข้อมูล

> เครื่องมือเชิงความหมายแบบกำหนดพารามิเตอร์ของ Fast-MCP มีระยะเวลาประมวลผลฐานข้อมูลแตกต่างจากคำสั่ง SQL ของวิธีฐานที่ใช้เปรียบเทียบอย่างไร ในภาระงานทางการเงินทั้งสี่ประเภทที่ศึกษา?

ในย่อหน้าเกริ่นก่อนคำถามวิจัย ให้ระบุร่วมกันว่าการทดลองใช้ฐานข้อมูล SQLite สังเคราะห์ที่มีรายการธุรกรรม 800,000 แถว จะได้ไม่ต้องกล่าวซ้ำทุกข้อ

## ความสัมพันธ์ระหว่างคำถามวิจัยกับการทดลองที่มี

| คำถามวิจัย | การทดลองที่รองรับใน README | ตัวชี้วัดหลัก | ขอบเขตการสรุปผล |
|---|---|---|---|
| RQ1: Execution Correctness | ตาราง Accuracy & Efficiency ของชุด financial workloads | EX เป็นหลัก; VSR เป็นข้อมูลประกอบ | ความถูกต้องบนชุดคำถามที่นำมาทดสอบ ไม่ใช่ความสามารถตอบคำถามฐานข้อมูลทั่วไปทั้งหมด |
| RQ2: End-to-End Efficiency | ตาราง Live LLM Service vs. Baselines | Total wall-clock latency, token usage, model calls และ tool calls | ประสิทธิภาพภายใต้โมเดล การตั้งค่า และเงื่อนไข API ที่ใช้จริง |
| RQ3: Database Execution Performance | ตาราง Speed & Latency ของ 4 workloads | Database execution latency และ speedup ratio | ความแตกต่างของเวลาระหว่าง implementation ที่ทดลอง ไม่ใช่ผลของ MCP เพียงองค์ประกอบเดียว |

สำหรับ VES สามารถรายงานเป็นตัวชี้วัดเสริมที่เชื่อมความถูกต้องกับประสิทธิภาพภายใต้ RQ1–RQ3 ได้ แต่ต้องระบุสูตรและเวลาที่นำมาคำนวณ ไม่จำเป็นต้องสร้างคำถามวิจัยแยกเพื่อรองรับทุก metric

## จุดที่ต้องทำให้ตรงกันก่อนใช้ฉบับสุดท้าย

### 1. RQ1 ต้องมีเกณฑ์ตรวจคำตอบถูกที่ชัดเจน

คำว่า execution accuracy ในคำถามวิจัยควรหมายถึงการตรวจผลลัพธ์กับคำตอบอ้างอิง ไม่ใช่เพียง SQL รันผ่าน

ใน Methods จึงควรระบุ:

- จำนวนคำถามที่ทดสอบ
- วิธีสร้างและตรวจสอบ gold results
- วิธีเปรียบเทียบผลลัพธ์
- วิธีนับคำตอบผิด timeout และ execution failure

หากยังตรวจเพียงว่า SQL รันสำเร็จ จะยังตอบ RQ1 ตามถ้อยคำข้างต้นไม่ได้ครบ

### 2. RQ2 ต้องแยก model calls กับ tool calls

README ปัจจุบันใช้ทั้ง “turns”, “calls” และ “steps” ในตารางเดียวกัน จึงควรแยกคอลัมน์ก่อนตอบคำถามนี้:

| รายการ | สิ่งที่ต้องนับ |
|---|---|
| Model calls | จำนวนครั้งที่ส่งคำขอไปยัง LLM |
| Tool calls | จำนวนครั้งที่เรียกเครื่องมือ |
| End-to-end latency | เวลาตั้งแต่เริ่มรับคำถามจนถึงจุดสิ้นสุดที่กำหนด |
| Token usage | ระบุว่าเป็น input, output หรือผลรวม |

ถ้ายังไม่มี telemetry แยก model calls และ tool calls ให้ใช้ RQ2 ฉบับที่แคบลงชั่วคราว:

> How does Fast-MCP compare with the evaluated baselines in end-to-end latency and token usage during live LLM evaluation?

ฉบับนี้ตรงกับคอลัมน์เวลารวมและโทเคนที่แสดงอยู่แล้วมากกว่า

### 3. RQ3 ต้องระบุว่ากำลังเทียบ SQL ชุดใด

ตารางปัจจุบันใช้คำว่า “Standard SQL” แต่ยังไม่ชัดว่าเป็น:

- SQL ที่โมเดลสร้าง
- SQL ที่เขียนด้วยมือ
- SQL ที่ยังไม่ได้ปรับประสิทธิภาพ
- หรือ reference SQL ที่ตรวจความถูกต้องแล้ว

ควรกำหนดให้แน่นอนใน Methods และตรวจว่าทั้งสองวิธีตอบโจทย์เดียวกัน หาก SQL ฝั่งหนึ่งคืนผลผิด การเปรียบเทียบเวลาต้องแสดงสถานะความถูกต้องควบคู่กัน ไม่ตีความ speedup แยกจากคุณภาพผลลัพธ์

## คำถามที่ยังไม่ควรใส่เป็นข้อหลัก

| คำถามที่เคยเสนอ | เหตุผลที่ยังไม่ตรงกับผลที่แสดง |
|---|---|
| ความได้เปรียบเกิดจาก semantic abstraction, index หรือ MCP? | ต้องมีการทดลองแยกองค์ประกอบ ซึ่งยังไม่ปรากฏในผลที่ส่งมา |
| Fast-MCP รองรับการเพิ่มขนาดฐานข้อมูลได้ดีเพียงใด? | มีคำสั่งสร้างข้อมูลหลายขนาด แต่ยังไม่แสดงผลการทดลองเปรียบเทียบหลายขนาด |
| Fast-MCP ทำงานกับ schema ใหม่ได้หรือไม่? | ยังไม่มีการทดลองข้าม schema |
| Fast-MCP ลดความผิดพลาดของคำตอบภาษาธรรมชาติได้หรือไม่? | มีตัวอย่างคำตอบ แต่ยังไม่แสดงเกณฑ์ประเมินและคะแนน answer fidelity |

ดังนั้น สำหรับชุดผลที่มีตอนนี้ ให้ใช้ 3 RQs ข้างต้นเป็นแกน โดยอย่าเพิ่มคำว่า “อย่างมีนัยสำคัญทางสถิติ” หรืออ้างเหตุเชิงองค์ประกอบ จนกว่าจะมีการทดลองที่รองรับโดยตรง