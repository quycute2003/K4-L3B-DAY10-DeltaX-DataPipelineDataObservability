# Báo cáo cá nhân — Vũ Minh Điềm

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Vũ Minh Điềm |
| MSSV | 2A202602858 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | DeltaX |
| Vai trò chính | Data Observability & Benchmark Evaluation |
| Repository | [quycute2003/K4-L3B-DAY10-DeltaX-DataPipelineDataObservability](https://github.com/quycute2003/K4-L3B-DAY10-DeltaX-DataPipelineDataObservability) |
| Ngày cập nhật | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File/hàm phụ trách | Input | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Bước 4: Quality Gate & Freshness | `src/observability/quality.py`; `run_data_quality_checks`, `build_freshness_report` | Clean DataFrame | Quality/freshness JSON trong `data/quality/` | Hoàn thành, đã có artifact baseline và corrupted |
| Bước 5: Benchmark Test Set | `src/evaluation/testset.py`; `build_test_set` | Clean DataFrame và document IDs | `data/eval/test_set.json` | Hoàn thành, 10 câu hỏi |

## 3. Kết quả và bằng chứng

### Quality Gate & Freshness

Quality Gate sử dụng Great Expectations 1.x với ephemeral context và các expectation: row count, `paper_id`/`title`/`text_for_embedding` không null, `paper_id` unique và độ dài `summary` tối thiểu 30 ký tự. Freshness SLA đánh dấu dữ liệu không fresh khi tỷ lệ `age_days > 180` vượt 25%.

| Trạng thái | Rows | Quality Gate | Freshness | Bằng chứng |
| --- | ---: | --- | --- | --- |
| Baseline | 24 | Pass | Pass — 1/24 stale (4.17%) | `data/quality/baseline_quality_report.json` |
| Corrupted | 22 | Fail | Fail — 10/22 stale (45.45%) | `data/quality/corrupted_quality_report.json` |

Baseline pass toàn bộ expectation. Dữ liệu corrupted bị phát hiện đúng kỳ vọng: `paper_id` không unique và có 4 summary rỗng; đồng thời stale ratio vượt SLA.

### Benchmark Test Set

`data/eval/test_set.json` có 10 câu hỏi, mỗi câu gồm `id`, `question_type`, `question`, `ground_truth` và `ground_truth_doc_ids`. Tập test cố định để so sánh công bằng giữa baseline, corrupted và repaired.

| Question type | Số câu |
| --- | ---: |
| `summary` | 3 |
| `authors` | 3 |
| `date` | 2 |
| `categories` | 2 |

## 4. Giải thích kỹ thuật

Quality checks xác nhận dữ liệu đủ điều kiện trước khi đi vào index/evaluation; freshness trả lời một câu hỏi khác: dữ liệu có còn mới theo SLA không. Việc tách hai tín hiệu giúp phát hiện cả lỗi cấu trúc lẫn hiện tượng dữ liệu cũ gây silent failure.

Test set được tạo từ cleaned dataset, gắn mỗi câu hỏi với ground-truth document ID. Khi đánh giá ba trạng thái trên cùng test set, thay đổi metric có thể quy về corruption/repair thay vì do thay đổi mẫu câu hỏi.

## 5. Cách xác minh

```powershell
$env:PYTHONUTF8='1'
py -c 'from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, "test"); print(res["success"])'
py -c 'from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); print(len(build_test_set(df, s.paths.eval_testset)))'
```

Kết quả đã xác minh: Quality Gate baseline `True`; test set có 10 câu và phủ đủ bốn nhóm câu hỏi.

## 6. Điều học được

- Một dataset có thể không lỗi schema nhưng vẫn stale; vì vậy Quality Gate và Freshness SLA cần được theo dõi song song.
- `paper_id` unique và ground-truth document ID là contract cốt lõi để evaluation đáng tin cậy.
- Artifact JSON giúp đối chiếu kết luận với bằng chứng, thay vì chỉ dựa trên thông báo console.

## 7. Cam kết

- [ ] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Mọi kết luận đều có code, artifact hoặc metric đối chiếu.
- [ ] Báo cáo không chứa API key, token hoặc secret.

**Họ và tên:** Vũ Minh Điềm
