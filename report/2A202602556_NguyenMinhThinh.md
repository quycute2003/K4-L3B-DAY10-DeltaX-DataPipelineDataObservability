# Báo cáo cá nhân — Nguyễn Minh Thịnh

- **MSSV:** 2A202602556
- **Nhóm:** DeltaX, K4-L3B Day 10
- **Phần được giao:** Bước 6 (baseline pipeline) và bước 7 (data corruption suite).

## 1. Công việc đã thực hiện

### Bước 6 — Baseline pipeline

- Hoàn thiện `run_phase1_pipeline(settings)` và `main()` trong `src/pipelines/phase1.py`; entrypoint `script/run_phase1.py` gọi `main()`.
- Nối các module của nhóm theo luồng raw Crossref → cleaned DataFrame → quality/freshness → test set → ChromaDB index → đánh giá → báo cáo. Dùng đường dẫn từ `src/core/config.py` và lưu cả cleaned CSV/JSON.
- Hoàn thiện `generate_phase1_report()` trong `src/observability/reporting.py` để ghi số liệu lấy từ kết quả chạy thật.
- Giữ test set cũ khi còn hợp lệ với tập dữ liệu mới; tạo lại khi thiếu, không hợp lệ hoặc cấu hình yêu cầu refresh.
- Cho baseline dừng trước khi tạo ChromaDB index nếu quality/freshness gate trả `success=False`; đã kiểm tra nhánh lỗi này bằng mock và xác nhận hàm build index không được gọi.

**Lệnh kiểm tra:**

```powershell
.\.venv\Scripts\python.exe script/run_phase1.py
```

**Kết quả đã quan sát:** lệnh kết thúc với exit code 0; 24 bài báo sạch được index; 10 câu hỏi test; `retrieval_hit_rate=1.0`, `mean_token_f1=1.0`, quality gate `success=True`. `judge_accuracy=1.0` và `mean_judge_score=5` trong metrics. Ragas được bỏ qua vì `RUN_RAGAS` chưa bật. Các số này thuộc lần chạy trên snapshot và cấu hình hiện tại, không đại diện cho mọi lần tải Crossref về sau.

**Artifact:** `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`, `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`, `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json`, `data/reports/phase1_report.md`.

## 2. Bước 7 — Data corruption suite

- Hoàn thiện `corrupt_clean_dataframe(df, output_log_path)` trong `src/ingestion/corruption.py` với sáu kịch bản: bỏ khoảng 20% bản ghi mới nhất, xóa summary, chèn noise, cắt ngắn title, lùi ngày xuất bản 365 ngày và tạo bản ghi trùng.
- Làm bẩn trên bản sao của DataFrame sạch; cập nhật `summary_chars`, `age_days` và `text_for_embedding` theo nội dung đã sửa. Ghi từng sự kiện vào `data/results/corruption_log.json` với `paper_id`, loại lỗi và giá trị trước/sau.
- Chọn dòng theo vị trí cố định để cùng input cho cùng kết quả, phục vụ so sánh với baseline và repair.

**Kết quả đã quan sát:** từ 24 dòng sạch, DataFrame bẩn có 22 dòng (bỏ 5 dòng mới nhất, thêm 3 dòng trùng). Log ghi đủ sáu loại lỗi. Quality gate trên dữ liệu bẩn trả `success=False` do trùng `paper_id` và summary ngắn; freshness `is_fresh=False`, tỷ lệ stale ghi nhận 0.4545. Đây là kết quả kiểm tra dữ liệu; metric RAG sau corruption thuộc bước 8 của thành viên phụ trách và chưa được ghi là hoàn thành ở đây.

## 3. Phụ thuộc và giới hạn

- Bước 6 sử dụng kết quả ingestion/cleaning của Quý và quality/test set của Điềm; bước 8 của Tuyên sử dụng output corruption của tôi. Cần dùng cùng `data/eval/test_set.json` khi so baseline, corrupted và repaired.
- Lần đầu chạy baseline thiếu model `sentence-transformers/all-MiniLM-L6-v2` trong cache; sau khi tải model, baseline đã chạy thành công. Muốn tái hiện trên máy khác cần cài dependencies và tải model.
- Chưa tự nhận phần repair và báo cáo so sánh ba trạng thái, vì đây là bước 8 do Tuyên phụ trách.

## 4. Cách kiểm chứng lại

```powershell
.\.venv\Scripts\python.exe script/run_phase1.py
.\.venv\Scripts\python.exe -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); dirty=corrupt_clean_dataframe(pd.read_json(s.paths.clean_json),s.paths.corruption_log); print(len(dirty),run_data_quality_checks(dirty,s,'corrupted')['success'])"
```

Đối chiếu `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`, `data/results/corruption_log.json` và `data/quality/corrupted_quality_report.json`; không đưa API key hoặc `.env` vào báo cáo.
