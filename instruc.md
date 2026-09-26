# Hướng dẫn thực hiện Day 10 — Data Pipeline & Data Observability

Tài liệu này tóm tắt các việc cần làm theo thứ tự phụ thuộc, dựa trên codelab và **cấu trúc thực tế của repo DeltaX**. Đánh dấu `[x]` chỉ khi đã chạy lệnh kiểm tra và nhìn thấy artifact tương ứng. Một số module đã được triển khai; `src/pipelines/corruption_flow.py` và hàm báo cáo so sánh ba trạng thái vẫn còn `NotImplementedError`.

### Trạng thái đối chiếu tại workspace hiện tại

| Phần việc | Trạng thái | Bằng chứng / việc còn lại |
| --- | --- | --- |
| Bước 2–3, Quý | Đã có mã và 24 raw/clean records | Kiểm tra lại khi tích hợp hoặc refresh nguồn. |
| Bước 4–5, Điềm | Đã có mã; baseline quality đạt, test set có 10 câu | Kiểm tra lại khi dữ liệu nguồn thay đổi. |
| **Bước 6, Thịnh** | **Đã chạy thành công tại local** | Báo cáo ghi 24 docs; `data/results/baseline_metrics.json` ghi 10 câu, Hit Rate 1.0, Token F1 1.0. Có `data/reports/phase1_report.md`. |
| **Bước 7, Thịnh** | **Đã chạy thành công tại local** | `data/results/corruption_log.json` có 6 loại lỗi; corrupted quality/freshness đều fail như dự kiến. |
| **Bước 8, Tuyên** | **Đã chạy thành công tại local** | Đã hoàn thiện corruption flow, idempotent repair, sinh đủ `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` với bảng so sánh 3 trạng thái. |
| Bước 9, cả nhóm | Chưa xong | Chưa có đủ báo cáo cá nhân, tỷ lệ đóng góp, xác minh push và nộp LMS. Thịnh đã tạo hai commit cho bước 6–7 bằng Git author Nguyễn Minh Thịnh. |

Các artifact cho bước 6–7 đã được commit tại local. Kiểm tra `git status` để chọn chính xác các file còn lại; rà soát secret và artifact tạm trước khi stage.

## 0. Chuẩn bị repo và cách làm việc nhóm

- [ ] Trưởng nhóm xác nhận fork có tên `K4-L3B-DAY10-DeltaX-DataPipelineDataObservability`, repo ở chế độ Public. Repo local hiện có `origin` là `https://github.com/quycute2003/K4-L3B-DAY10-DeltaX-DataPipelineDataObservability.git`, `upstream` là repo mẫu, và nhánh hiện tại là `main`.
- [ ] Trưởng nhóm mời toàn bộ thành viên làm Collaborator; từng người chấp nhận lời mời và clone **repo nhóm**.
- [ ] Mỗi người đặt Git author bằng tên và email gắn với tài khoản GitHub của **chính mình**, rồi kiểm tra trước khi commit:

  ```powershell
  git config user.name "Ho Ten"
  git config user.email "email-tren-github@example.com"
  git config --get user.name
  git config --get user.email
  git remote -v
  git branch --show-current
  ```

  Dùng cấu hình local như trên để không vô tình đổi author của repo khác. Email GitHub `noreply` cũng dùng được nếu đã liên kết với tài khoản. Mỗi thành viên cần có commit riêng, thể hiện phần việc thực sự; kiểm tra tại **Insights → Contributors** sau khi push/merge vào `main`.

- [ ] Phân công owner cho ingestion, cleaning/test set, quality/reporting, corruption/repair, tích hợp pipeline. Thống nhất schema `PaperRecord`, các cột DataFrame, `paper_id`, đường dẫn trong `src/core/config.py`, và cùng một test set cho ba trạng thái.

## 1. Môi trường Python và cấu hình

- [ ] Dùng Python **3.11–3.13** (`pyproject.toml` quy định `>=3.11,<3.14`). Python 3.14 sẽ bị từ chối. Trên Windows PowerShell:

  ```powershell
  py -3.13 -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python --version
  python -m pip --version
  python -m pip install -e .
  ```

  Repo này đã có `.venv` dùng Python 3.13.15. Nếu chỉ cần sử dụng, **kích hoạt lại**, không cần tạo lại. Nếu `pip` chưa có, có thể dùng `uv sync` khi có mạng, hoặc cài `pip` vào môi trường trước khi chạy `python -m pip install -e .`. Chạy `uv sync` từ thư mục gốc repo. Việc tải thư viện và mô hình embedding cần kết nối mạng/cache sẵn có.

- [ ] Sao chép cấu hình rồi điền key cá nhân cho provider đang dùng:

  ```powershell
  Copy-Item .env.example .env
  ```

  Mặc định `.env.example` dùng `LLM_PROVIDER=gemini`, nên cần `GOOGLE_API_KEY`. Nếu đổi provider, xem `src/core/config.py` để biết biến bắt buộc. Không commit `.env` hay in key vào log/báo cáo.

- [ ] Kiểm tra Python đang trỏ tới `.venv` và ba thư viện chính đã import được:

  ```powershell
  python -c "import sys; print(sys.executable)"
  python -c "import chromadb, great_expectations, sentence_transformers; print('Environment Ready!')"
  ```

  **Đạt:** đường dẫn Python chứa `.venv`; console in `Environment Ready!`.

## 2. Thu thập và giữ dữ liệu gốc — `src/ingestion/crossref.py`

- [ ] Hoàn thiện `parse_crossref_payload(payload)`: đọc `payload["message"]["items"]`; lấy DOI làm `paper_id`, tiêu đề, abstract/summary, tác giả, subject/category, ngày xuất bản/cập nhật và URL; bỏ thẻ XML/HTML trong abstract; xử lý trường thiếu và bỏ bản ghi không hợp lệ. Đầu ra là `list[PaperRecord]` theo dataclass đang có trong file.
- [ ] Hoàn thiện `fetch_source_records(settings)`: dùng `settings.source_query`, `source_filter`, `max_results`; gọi Crossref với timeout/retry phù hợp (đặc biệt 429/503); nếu API lỗi thì đọc snapshot `data/raw/crossref_response.json`; giữ nguyên payload gốc tại `settings.paths.raw_api_response`; ghi records đã parse vào `settings.paths.raw_records_json`.
- [ ] Hoàn thiện **cả** `load_raw_records(path)` vì bước cleaning/repair cần đọc lại raw records mà không gọi API.
- [ ] Không sửa tay snapshot raw để làm đẹp kết quả; nó là điểm khôi phục khi dữ liệu downstream hỏng.

  ```powershell
  python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Da tai {len(r)} bai bao')"
  ```

  **Đạt:** snapshot đi kèm repo có 24 `items`, hai file raw JSON tồn tại và lệnh in 24 bản ghi hợp lệ.

## 3. Làm sạch dữ liệu — `src/ingestion/cleaning.py`

- [ ] Hoàn thiện `build_clean_dataframe(records, run_date)`: chuẩn hóa khoảng trắng/title/summary/authors/categories; chuẩn hóa ngày; tính `age_days = (run_date - published).days`; tạo `authors_joined`, `categories_joined`, `summary_chars` và `text_for_embedding` gồm Title, Authors, Published, Categories, Summary theo thứ tự codelab.
- [ ] Khử trùng lặp theo `paper_id`, loại dòng thiếu dữ liệu cốt lõi, sắp xếp ổn định. Giữ schema tương thích với `retrieval/index.py`, `evaluation/testset.py` và quality gate. Đảm bảo `run_date` có timezone phù hợp với ngày đọc từ Crossref.

  ```powershell
  python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print('Clean rows:', len(df)); print(df.columns.tolist())"
  ```

  **Đạt:** snapshot mẫu tạo 24 dòng sạch, `paper_id` duy nhất và có `text_for_embedding`. Sau khi pipeline lưu file, kiểm tra `data/clean/papers_clean.csv` và `.json`.

## 4. Quality gate và freshness — `src/observability/quality.py`

- [ ] Hoàn thiện `run_data_quality_checks(df, settings, report_name)` bằng Great Expectations 1.x Ephemeral Context: `gx.get_context(mode="ephemeral")` → pandas datasource → dataframe asset → whole-dataframe batch → validate.
- [ ] Kiểm tra 4 nhóm expectation: số dòng 5–5000; `paper_id`, `title`, `text_for_embedding` không null; `paper_id` duy nhất; `summary` dài tối thiểu 30 ký tự. Ghi kết quả vào `data/quality/`, trả về dict có `success` và chi tiết từng kiểm tra.
- [ ] Tính freshness từ `age_days`: dòng cũ khi `age_days > 180`; `is_fresh=False` khi tỷ lệ dòng cũ **vượt** 25%. Repo hiện có `build_freshness_report(df, settings, report_path)` nhưng **không có sẵn** hàm `evaluate_freshness_sla()` được nhắc trong codelab; có thể triển khai helper này hoặc tính trực tiếp, rồi để `build_freshness_report` ghi `data/quality/freshness_report.json`.
- [ ] Thử thêm dữ liệu lỗi (null/trùng lặp/summary ngắn) để xác nhận gate trả lỗi đúng, không chỉ thử dữ liệu sạch.

  ```powershell
  python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); r=run_data_quality_checks(df,s,'test'); print('Quality:',r['success'])"
  ```

  **Đạt:** dữ liệu sạch trả `success=True`; dữ liệu lỗi bị phát hiện. Lệnh trên cần `data/clean/papers_clean.json` đã được tạo ở bước 6 hoặc lưu thủ công sau bước 3.

## 5. Bộ câu hỏi chuẩn và vector index

- [ ] Hoàn thiện `build_test_set(df, output_path)` trong `src/evaluation/testset.py`: sinh 10 câu hỏi phủ bốn loại `summary`, `authors`, `date`, `categories`; mỗi mục có `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` chứa đúng DOI; kết quả ổn định khi chạy lại và ghi `data/eval/test_set.json`.
- [ ] Kiểm tra `src/retrieval/embeddings.py` và `src/retrieval/index.py` khi tích hợp: dùng model `sentence-transformers/all-MiniLM-L6-v2`, index đủ 24 tài liệu sạch vào collection `papers-baseline` tại `data/chroma/`; giữ `paper_id` làm document ID để tính retrieval hit.

  ```powershell
  python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df,s.paths.eval_testset); print('Test questions:',len(ts))"
  ```

  **Đạt:** `data/eval/test_set.json` có 10 câu, phủ cả bốn loại và tham chiếu DOI có thật trong dữ liệu.

## 6. Baseline pipeline và báo cáo

- [x] Hoàn thiện **`main()`** trong `src/pipelines/phase1.py`. Codelab gọi tên `run_phase1_pipeline(settings)`, nhưng entrypoint `script/run_phase1.py` của repo hiện import `main`; `main()` đã gọi helper này.
- [x] Nối theo thứ tự: load/fetch raw → clean → lưu CSV/JSON → quality/freshness gate → tạo hoặc nạp test set → tạo embeddings/index Chroma → đánh giá qua `src/evaluation/metrics.py` → báo cáo Markdown. Pipeline dừng trước khi index nếu gate fail.
- [x] Hoàn thiện `generate_phase1_report(...)` trong `src/observability/reporting.py`; báo cáo lấy số liệu từ kết quả chạy thật. Đã kiểm tra `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` trong `data/results/baseline_metrics.json`.

  ```powershell
  python script/run_phase1.py
  ```

  **Đạt:** có `data/clean/papers_clean.csv`, `.json`, `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `data/quality/` và `data/reports/phase1_report.md`; pipeline chạy không có exception.

## 7. Tiêm sáu loại lỗi — `src/ingestion/corruption.py`

- [x] Hoàn thiện `corrupt_clean_dataframe(df, output_log_path)` trên **bản sao** dữ liệu sạch: bỏ khoảng 20% bản ghi mới nhất; xóa summary; chèn noise; cắt title dưới 8 ký tự; lùi published/age; thêm bản ghi trùng DOI. Đã cập nhật các cột dẫn xuất `summary_chars`, `age_days`, `text_for_embedding`.
- [x] Ghi `data/results/corruption_log.json` với loại lỗi, `paper_id`, giá trị trước/sau hoặc thông tin đủ để truy vết. Đã kiểm tra raw và baseline không bị hàm corruption sửa.

  ```powershell
  python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df,s.paths.corruption_log); print('Corrupted rows:',len(c))"
  ```

  **Đạt:** log có đủ sáu loại lỗi, số dòng và dữ liệu sau biến đổi hợp lý. Quality gate trên corrupted data phải phát hiện ít nhất các vi phạm đã chủ ý tạo ra.

## 8. Đo suy giảm, phục hồi và đối chiếu

- [x] Hoàn thiện **`main()`** trong `src/pipelines/corruption_flow.py`; entrypoint `script/run_corruption_flow.py` hiện import tên này. Đã triển khai `run_corruption_flow_pipeline(settings)` và cho `main()` gọi nó.
- [x] Nạp baseline metrics và cùng `data/eval/test_set.json`; ghi corrupted CSV/JSON, tạo collection `papers-corrupted`, đánh giá và lưu `data/results/corrupted_metrics.json`, chạy quality/freshness.
- [x] Phục hồi **từ raw snapshot** bằng cách parse/clean lại, ghi repaired CSV/JSON, tạo collection `papers-repaired`, đánh giá trên đúng test set cũ và lưu `data/results/repaired_metrics.json`. Chạy lại repair để kiểm tra tính idempotent: không tích lũy bản ghi trùng và kết quả dữ liệu ổn định. Đã bổ sung hàm `repair_from_raw_snapshot()`.
- [x] Hoàn thiện `generate_corruption_report(...)` trong `src/observability/reporting.py`; xuất bảng Baseline / Corrupted / Repaired tại `data/reports/corruption_report.md`, gồm metrics, quality và freshness. Đối chiếu số trong Markdown với JSON, ghi nhận kết quả thực tế kể cả khi suy giảm/phục hồi không như kỳ vọng.

  ```powershell
  python script/run_corruption_flow.py
  ```

  **Đạt:** có `data/results/corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json`, báo cáo ba trạng thái và console hiển thị so sánh rõ ràng.

## 9. Rà soát và nộp bài

- [ ] Chạy lại `python script/run_phase1.py` và `python script/run_corruption_flow.py`; kiểm tra artifact mới tạo và số liệu báo cáo khớp JSON. Chuẩn bị demo giải thích raw → clean → index → quality → corruption → repair.
- [ ] Điền `docs/TEAM.md`: tên nhóm DeltaX, từng thành viên/MSSV/email/vai trò và tỷ lệ đóng góp đã thống nhất. Kiểm tra rubric tại `docs/RUBRIC.md`.
- [ ] Repo thực tế dùng thư mục **`report/`** và có `report/individual_report.md`, `report/group_report.md`, `report/README.md`. Codelab lại ghi `reports/` cùng mẫu `TEMPLATE_individual.md`, nhưng các đường dẫn đó **không có trong repo**. Nhóm nên dùng quy ước trong `report/README.md` (bản cá nhân `<MSSV>_HoTen.md`) và xác nhận trên LMS nếu yêu cầu nộp cụ thể khác. Viết báo cáo nhóm và mỗi cá nhân từ công việc, artifact, metric thực tế.
- [ ] Kiểm tra secret/file rác trước khi commit: `git status --short`, `git diff --check`, `git check-ignore .env .venv/ data/chroma/`. `.gitignore` hiện đã bỏ qua `.env`, `.venv/`, `venv/`, `.tmp/`, `.uv-cache/`, `data/chroma/` và `__pycache__/`. Chọn rõ các artifact cần nộp; không commit cache/model hoặc key.
- [ ] Đảm bảo mọi phần việc đã merge vào `main`; sau khi rà soát, commit/push đúng thay đổi của mình và xem lại `git status`. Mỗi thành viên kiểm tra commit của mình hiển thị trên GitHub.
- [ ] Mỗi cá nhân nộp link repo nhóm trên VLearn LMS. **Hạn nộp đang mâu thuẫn:** đoạn codelab bạn gửi nói 13:00/18:00; `README.md` và `docs/SUBMISSION.md` trong repo ghi 23:59:59 cùng ngày. Kiểm tra thông báo **hiện hành trên LMS/giảng viên** và theo hạn được xác nhận; đừng tự suy đoán từ tài liệu này.

## Tóm tắt thứ tự thực hiện

`Git team + Python/.env` → `Crossref raw (24)` → `clean (24)` → `GX + freshness` → `test set (10) + Chroma` → `baseline metrics/report` → `6 lỗi + log` → `corrupted metrics` → `repair từ raw` → `repaired metrics + bảng so sánh` → `báo cáo nhóm/cá nhân + nộp LMS`.
