# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | DeltaX |
| Repository | [quycute2003/K4-L3B-DAY10-DeltaX-DataPipelineDataObservability](https://github.com/quycute2003/K4-L3B-DAY10-DeltaX-DataPipelineDataObservability) |
| Ngày cập nhật | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| ---: | --- | --- | --- | --- |
| 1 | Phạm Xuân Quý | 2A202602745 | Data ingestion & cleaning owner | Bước 2: `src/ingestion/crossref.py`; Bước 3: `src/ingestion/cleaning.py` |
| 2 | Vũ Minh Điềm | 2A202602858 | Observability & benchmark owner | Bước 4: `src/observability/quality.py`; Bước 5: `src/evaluation/testset.py` |
| 3 | Nguyễn Minh Thịnh | 2A202602556 | Baseline & corruption owner | Bước 6: `script/run_phase1.py`; Bước 7: `src/ingestion/corruption.py` |
| 4 | Nguyễn Hoàng Tuyên | 2A202602439 | Recovery & comparative evaluation owner | Bước 8: `src/pipelines/corruption_flow.py` và `data/reports/corruption_report.md` |

## 2. Phạm vi và trạng thái báo cáo

Nhóm DeltaX triển khai pipeline RAG theo chuỗi: Crossref/raw records → cleaning và chuẩn bị embedding → vector index → benchmark và Quality Gate/freshness → baseline → corruption → repair → bảng so sánh ba trạng thái. Phân công ở trên là nguồn tham chiếu chính thức cho các báo cáo cá nhân.

Các kết quả định lượng, trạng thái pass/fail và kết luận nhân quả sẽ chỉ được bổ sung từ các artifact được tạo bởi pipeline. Không ghi nhận một luồng là thành công trước khi có lệnh chạy, log và artifact tương ứng.

## 3. Luồng end-to-end

```text
Crossref/raw snapshot
    -> raw records
    -> cleaning + text_for_embedding + age_days
    -> embedding + ChromaDB index
    -> benchmark evaluation + quality/freshness signals
    -> baseline metrics
    -> data corruption
    -> corrupted metrics
    -> repair from trusted raw source
    -> repaired metrics + comparison report
```

### Phạm vi kỹ thuật của từng thành viên

| Thành viên | Công việc được giao | Bàn giao dự kiến |
| --- | --- | --- |
| Phạm Xuân Quý | Thu thập dữ liệu Crossref và cất giữ raw snapshot trong `src/ingestion/crossref.py`; làm sạch, chuẩn hóa và tạo văn bản embedding trong `src/ingestion/cleaning.py`. | Raw records; cleaned dataset; `text_for_embedding`; `age_days`. |
| Vũ Minh Điềm | Thiết lập Quality Gate bằng Great Expectations 1.x, gồm freshness theo `age_days`, trong `src/observability/quality.py`; tạo benchmark test set trong `src/evaluation/testset.py`. | Quality/freshness artifacts; test set và ground-truth document IDs. |
| Nguyễn Minh Thịnh | Chạy baseline qua `script/run_phase1.py`; hoàn thiện `corrupt_clean_dataframe(clean_df, log_path)` trong `src/ingestion/corruption.py`. | Baseline artifacts/metrics; corrupted dataset; `data/results/corruption_log.json`. |
| Nguyễn Hoàng Tuyên | Hoàn thiện `run_corruption_flow_pipeline(settings)` trong `src/pipelines/corruption_flow.py`: đo trạng thái corrupted, repair từ raw snapshot, tái đánh giá và xuất bảng ba trạng thái. | Corrupted/repaired metrics; `data/reports/corruption_report.md`. |

### Các corruption scenarios

1. **Drop latest records:** bỏ 20% bài báo mới nhất.
2. **Blank summary:** xóa trắng summary ở một số dòng.
3. **Inject noise:** chèn chuỗi ký tự rác vào summary.
4. **Truncate title:** cắt tiêu đề còn dưới 8 ký tự.
5. **Stale date:** lùi ngày xuất bản 365 ngày.
6. **Duplicate rows:** nhân đôi dòng để tạo trùng lặp.

## 4. Cách tái hiện

```powershell
.\.venv\Scripts\Activate.ps1
py -m pip install -e .
py script/run_phase1.py
py script/run_corruption_flow.py
```

Các lệnh trên phải được chạy lại trước khi hoàn thiện các phần metrics trong báo cáo. Không đưa API key hoặc nội dung `.env` vào tài liệu này.

## 5. Bảng kết quả — chờ artifact thực tế

| Metric/signal | Baseline | Corrupted | Repaired | Nguồn bằng chứng |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | Chưa xác minh | Chưa xác minh | Chưa xác minh | `data/results/*_metrics.json` |
| `mean_token_f1` | Chưa xác minh | Chưa xác minh | Chưa xác minh | `data/results/*_metrics.json` |
| `judge_accuracy` | Chưa xác minh | Chưa xác minh | Chưa xác minh | `data/results/*_metrics.json` |
| `mean_judge_score` | Chưa xác minh | Chưa xác minh | Chưa xác minh | `data/results/*_metrics.json` |
| Quality checks | Chưa xác minh | Chưa xác minh | Chưa xác minh | `data/quality/` |
| Freshness status | Chưa xác minh | Chưa xác minh | Chưa xác minh | `data/quality/` |

## 6. Checklist trước khi nộp

- [ ] Hai pipeline chạy exit code 0.
- [ ] Metrics, quality reports và comparison report được sinh từ pipeline.
- [ ] Bảng trên khớp artifact thực tế.
- [ ] Mỗi thành viên hoàn thiện báo cáo riêng và có commit được GitHub nhận diện.
- [ ] Repository không chứa `.env` hoặc secret.
