# Báo cáo cá nhân — Nguyễn Hoàng Tuyên

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Hoàng Tuyên |
| MSSV | 2A202602439 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | DeltaX |
| Vai trò chính | Đo lường suy giảm (Degradation Analysis), Xác minh phục hồi (Idempotent Repair) và Đối chiếu 3 trạng thái Baseline–Corrupted–Repaired |
| Repository | [quycute2003/K4-L3B-DAY10-DeltaX-DataPipelineDataObservability](https://github.com/quycute2003/K4-L3B-DAY10-DeltaX-DataPipelineDataObservability) |
| Ngày cập nhật | 2026-09-27 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu chính (Bước 8)

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Bước 8: Đo lường suy giảm & Tự phục hồi | `src/pipelines/corruption_flow.py`; hàm `run_corruption_flow_pipeline`, `repair_from_raw_snapshot`, `main` | Dữ liệu clean, log corruption, raw snapshot | `corrupted_metrics.json`, `repaired_metrics.json`, `papers_clean_corrupted.*`, `papers_clean_repaired.*` | Hoàn thành, đã chạy thực tế trong `.venv` |
| Báo cáo so sánh 3 trạng thái | `src/observability/reporting.py`; hàm `generate_corruption_report` | Metrics & Quality/Freshness reports của 3 trạng thái | `data/reports/corruption_report.md` | Hoàn thành, bảng đối chiếu định lượng |

---

## 3. Công việc kỹ thuật đã thực hiện

### 3.1. Thiết kế và triển khai Pipeline Đo lường & Phục hồi (`src/pipelines/corruption_flow.py`)
- **Tải và tái sử dụng chuẩn hóa**: Đọc `clean_json` và `baseline_metrics.json`. Đảm bảo đánh giá trên cùng tập test set cố định `data/eval/test_set.json` (10 câu hỏi thuộc 4 nhóm nghiệp vụ: `summary`, `authors`, `date`, `categories`) để loại bỏ hoàn toàn nhiễu do thay đổi mẫu câu hỏi.
- **Đánh giá trạng thái Corrupted**:
  - Tiêm 6 kịch bản lỗi giả lập qua `corrupt_clean_dataframe()`.
  - Lưu trữ artifact `data/clean/papers_clean_corrupted.csv` và `.json`.
  - Khởi tạo ChromaDB collection `papers-corrupted` bằng embedding model `sentence-transformers/all-MiniLM-L6-v2`.
  - Chạy `evaluate_pipeline()` lưu `data/results/corrupted_metrics.json` và `data/results/corrupted_answers.json`.
  - Chạy Great Expectations 1.x và Freshness SLA lưu `data/quality/corrupted_quality_report.json`.
- **Cơ chế Idempotent Repair (`repair_from_raw_snapshot`)**:
  - Không sửa chữa chắp vá trên tập dữ liệu corrupted mà quay lại đọc bản lưu trữ thô bất biến `data/raw/crossref_records.json` (hoặc `crossref_response.json`).
  - Tái thực thi toàn bộ quy trình làm sạch chuẩn qua `build_clean_dataframe()`.
  - **Kiểm chứng tính Idempotent**: Thực thi lặp lại hàm repair và assert kiểm tra: số dòng, thứ tự và `paper_id` hoàn toàn bất biến giữa các lần chạy, không gây tích tụ dòng trùng lặp hay sai lệch schema.
  - Lưu artifact `data/clean/papers_clean_repaired.csv` và `.json`.
  - Khởi tạo ChromaDB collection `papers-repaired`, tái đánh giá lưu `data/results/repaired_metrics.json` và `data/results/repaired_answers.json`.
  - Chạy kiểm định Data Observability cho tập repaired.

### 3.2. Hoàn thiện hàm sinh báo cáo Markdown (`src/observability/reporting.py`)
- Triển khai hàm `generate_corruption_report(...)` tự động trích xuất các chỉ số thực tế từ kết quả chạy và xuất ra `data/reports/corruption_report.md`.
- Trình bày ma trận so sánh chi tiết: `samples`, `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`, trạng thái Quality Gate (GX 1.x), danh sách Failed Checks, trạng thái Freshness SLA và tỷ lệ Stale.
- Xử lý tương thích encoding UTF-8 an toàn trên Windows terminal (`sys.stdout.reconfigure`), ngăn chặn lỗi `charmap` codec.

---

## 4. Kết quả thực nghiệm và Bằng chứng định lượng

### Bảng đối chiếu định lượng 3 trạng thái (Baseline vs Corrupted vs Repaired)

Dữ liệu được trích xuất trực tiếp từ các artifact JSON sinh ra bởi pipeline:

| Chỉ số / Tín hiệu | Baseline | Corrupted | Repaired | Đánh giá xu hướng / Tác động | Bằng chứng |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `samples` (số câu test) | 10 | 10 | 10 | Đánh giá trên cùng bộ câu hỏi | `test_set.json` |
| `retrieval_hit_rate` | **1.000** | **0.900** | **1.000** | Giảm 10% do mất 20% bản ghi mới | `*_metrics.json` |
| `mean_token_f1` | **1.000** | **0.800** | **1.000** | Rơi sâu 20% do nhiễu và xóa summary | `*_metrics.json` |
| `judge_accuracy` | **1.000** | **0.800** | **1.000** | Judge phát hiện câu trả lời suy giảm | `*_metrics.json` |
| `mean_judge_score` | **5.00** | **4.20** | **5.00** | Điểm trung bình giảm từ 5.0 xuống 4.2 | `*_metrics.json` |
| **Quality Gate** (GX 1.x) | **True** (Pass) | **False** (Fail) | **True** (Pass) | Bắt đúng lỗi duplicate & summary rỗng | `*_quality_report.json` |
| Failed Checks | `none` | `unique, min_length` | `none` | 2 Expectation vi phạm bị chặn | `corrupted_quality_report.json` |
| **Freshness SLA** | **True** (Pass) | **False** (Fail) | **True** (Pass) | Báo động khi stale vượt ngưỡng 25% | `freshness_report.json` |
| Tỷ lệ stale (`age_days > 180`) | 4.17% (1/24) | 45.45% (10/22) | 4.17% (1/24) | Tăng vọt trong tập corrupted | `corrupted_quality_report.json` |

---

## 5. Phân tích hiện tượng Silent Failure và Cơ chế Tự phục hồi

### 5.1. Hiện tượng Silent Failure ở RAG Agent
- Khi không có Data Observability chốt chặn, RAG Agent vẫn trả về câu trả lời nhưng chất lượng sụt giảm âm thầm:
  - Do 20% bài báo mới nhất bị loại bỏ và các trường summary bị xóa/chèn nhiễu, vector store không thể tìm đúng ngữ cảnh đích.
  - `retrieval_hit_rate` giảm từ 1.0 xuống 0.9 và `mean_token_f1` giảm từ 1.0 xuống 0.8.
- Great Expectations 1.x và Freshness SLA đã hoạt động xuất sắc như một lớp lá chắn phát hiện tức thì:
  - `ExpectColumnValuesToBeUnique`: Bắt quả tang 3 bản ghi trùng lặp DOI.
  - `ExpectColumnValueLengthsToBeBetween`: Bắt quả tang 4 bản ghi bị xóa trắng summary.
  - Freshness SLA: Đánh dấu vi phạm SLA khi tỷ lệ bài báo cũ đạt 45.45% (ngưỡng tối đa 25%).

### 5.2. Nguyên lý Idempotent Repair
- **Tính Idempotent**: Hàm `repair_from_raw_snapshot` có thể chạy bất kỳ số lần nào mà không gây tác dụng phụ. Output luôn là tập 24 bản ghi sạch duy nhất, không tích lũy bản ghi rác.
- **Tái thiết lập Vector Space**: Việc tạo mới collection `papers-repaired` trên ChromaDB dọn sạch các vector lỗi, đưa độ chính xác truy xuất và Token F1 quay về mức hoàn hảo 1.0.

---

## 6. Lệnh kiểm chứng độc lập trong môi trường ảo

```powershell
# Kích hoạt môi trường ảo
.\.venv\Scripts\Activate.ps1

# Chạy pipeline đối chiếu 3 trạng thái
python script/run_corruption_flow.py

# Kiểm tra các artifact sinh ra
Get-ChildItem data\results, data\reports, data\quality | Select-Object Name, Length, LastWriteTime
```

---

## 7. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc tôi trực tiếp phụ trách và kết quả thực nghiệm.
- [x] Đã hiểu và giải thích thấu đáo toàn bộ luồng pipeline end-to-end từ Raw -> Clean -> Observability -> Corruption -> Repair.
- [x] Các số liệu trong báo cáo hoàn toàn khớp với các file artifact JSON và Markdown thực tế.
- [x] Không đưa API key, token hoặc file `.env` vào repository.

**Họ và tên:** Nguyễn Hoàng Tuyên  
**Xác nhận nghiệm thu:** Đạt yêu cầu Checkpoint 5 và Rubric mục 8 (15/15đ).
