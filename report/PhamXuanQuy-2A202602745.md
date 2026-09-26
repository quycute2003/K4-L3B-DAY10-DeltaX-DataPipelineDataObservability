# Báo cáo cá nhân — Phạm Xuân Quý

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phạm Xuân Quý |
| MSSV | 2A202602745 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | DeltaX |
| Vai trò chính | Thu thập dữ liệu, cất giữ bản gốc, làm sạch dữ liệu và chuẩn bị văn bản tạo vector |
| Repository | [quycute2003/K4-L3B-DAY10-DeltaX-DataPipelineDataObservability](https://github.com/quycute2003/K4-L3B-DAY10-DeltaX-DataPipelineDataObservability) |
| Ngày cập nhật | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Bước 2: Thu thập dữ liệu & cất giữ bản gốc | `src/ingestion/crossref.py` | Snapshot/response từ Crossref | Raw response và 24 raw records trong `data/raw/` | Hoàn thành, đã xác minh |
| Bước 3: Làm sạch dữ liệu & chuẩn bị văn bản tạo vector | `src/ingestion/cleaning.py` | 24 raw records | Clean DataFrame 24 dòng, `text_for_embedding`, `age_days` | Hoàn thành, đã xác minh |

### Quan hệ phụ thuộc

Phần việc này cung cấp dữ liệu đầu vào cho Quality Gate, benchmark test set, embedding/index và toàn bộ các lần đo baseline, corrupted, repaired. Raw snapshot phải được bảo toàn để pipeline repair có thể phục hồi dữ liệu từ nguồn đáng tin cậy.

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/artifact liên quan | Kết quả cần bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Thu thập và lưu dữ liệu nguồn | `src/ingestion/crossref.py`, `data/raw/` | Raw snapshot và 24 raw records có schema hợp lệ | Đã chạy `fetch_source_records`; đọc lại raw records thành công |
| Làm sạch và chuẩn bị dữ liệu embedding | `src/ingestion/cleaning.py` | Clean DataFrame 24 dòng có document ID duy nhất, `text_for_embedding`, `age_days` | Đã chạy `build_clean_dataframe` và kiểm tra các cột helper |

Kết quả định lượng và trạng thái hoàn thành sẽ chỉ được bổ sung từ artifact thực tế sau khi pipeline chạy thành công.

## 4. Giải thích phần kỹ thuật

### Vấn đề cần giải quyết

Pipeline RAG cần một nguồn dữ liệu truy vết được, có schema nhất quán và đủ thông tin để vừa xây dựng vector index, vừa kiểm soát chất lượng/freshness. Nếu raw source không được bảo toàn, bước repair sau corruption không có cơ sở đáng tin cậy để phục hồi.

### Cách triển khai

`crossref.py` chịu trách nhiệm đọc/thu thập và ghi lại raw response, raw records. `cleaning.py` chuẩn hóa các trường cần thiết, xử lý bản ghi không hợp lệ hoặc trùng lặp, đồng thời tạo `text_for_embedding` cho vectorization và `age_days` cho kiểm tra freshness.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref response/raw records |
| Output | Raw snapshot, cleaned dataset, document ID, `text_for_embedding`, `age_days` |
| Module phụ thuộc | `src/ingestion/crossref.py` |
| Module sử dụng output | `quality.py`, `testset.py`, embedding/index, baseline và corruption flow |
| Điều kiện lỗi cần xử lý | Trường thiếu, dữ liệu không hợp lệ, bản ghi trùng lặp và dữ liệu quá cũ |

### Cách xác minh

```powershell
py script/run_phase1.py
```

- **Kết quả mong đợi:** sinh raw và cleaned artifacts theo cấu trúc dự án.
- **Kết quả thực tế:** `fetch_source_records` đã parse/lưu 24 raw records; `build_clean_dataframe` làm sạch thành công 24 dòng, với `paper_id` duy nhất và đầy đủ helper columns.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`; cleaned artifacts sẽ được ghi bởi baseline pipeline.

## 5. Quyết định kỹ thuật cần đối chiếu khi triển khai

- **Bối cảnh:** cần bảo toàn khả năng repair trong khi vẫn có dataset sạch để index và evaluation.
- **Các phương án:** chỉ giữ cleaned dataset; hoặc giữ cả raw snapshot và cleaned dataset.
- **Phương án chọn:** giữ raw snapshot bất biến, tạo cleaned dataset như một artifact dẫn xuất.
- **Lý do:** repair có thể tái tạo dữ liệu từ nguồn gốc thay vì che lỗi trên dữ liệu corrupted.
- **Bằng chứng cần có:** baseline/corruption/repair artifacts và log tương ứng.

## 6. Blocker hoặc lỗi đã xử lý

Chưa ghi nhận blocker đã được xác minh. Nếu phát sinh, nội dung sẽ ghi lỗi nguyên văn đã che secret, nguyên nhân gốc, thay đổi xử lý và lệnh xác minh.

## 7. Hiểu biết về luồng end-to-end

1. Crossref response được lưu thành raw snapshot/raw records; cleaning tạo dataset chuẩn hóa với document ID, `text_for_embedding` và `age_days`, sau đó dữ liệu được embedding và nạp vào ChromaDB.
2. Test set lưu question, ground truth và document IDs để đo retrieval/answer quality trên cùng mục tiêu tham chiếu.
3. Quality checks kiểm tra tính hợp lệ/đầy đủ/nhất quán của dữ liệu; freshness giám sát độ mới, chẳng hạn từ `age_days`.
4. Dùng cùng test set giúp thay đổi metric phản ánh ảnh hưởng của corruption hoặc repair, thay vì do thay đổi câu hỏi đánh giá.
5. Repair chỉ thành công khi artifact repaired được phục hồi từ raw snapshot và quality/freshness cùng metrics được đối chiếu lại với baseline/corrupted.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | Chưa xác minh | Chưa xác minh | Chưa xác minh | Chờ `*_metrics.json` |
| `mean_token_f1` | Chưa xác minh | Chưa xác minh | Chưa xác minh | Chờ `*_metrics.json` |
| `judge_accuracy` | Chưa xác minh | Chưa xác minh | Chưa xác minh | Chờ `*_metrics.json` |
| `mean_judge_score` | Chưa xác minh | Chưa xác minh | Chưa xác minh | Chờ `*_metrics.json` |
| Quality checks | Chưa xác minh | Chưa xác minh | Chưa xác minh | Chờ `data/quality/` |
| Freshness status | Chưa xác minh | Chưa xác minh | Chưa xác minh | Chờ `data/quality/` |

## 9. Điều học được và hướng cải thiện

- Bảo toàn raw snapshot là điều kiện quan trọng để repair có thể kiểm chứng và tái lập.
- Data contract của cleaned dataset liên kết trực tiếp ingestion, observability, index và evaluation.
- Khi có artifact thực tế, có thể bổ sung quy tắc cleaning hoặc kiểm tra schema dựa trên những lỗi phát hiện được.

## 10. Cam kết của thành viên

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** Phạm Xuân Quý
**Ngày xác nhận:** Chờ cập nhật sau khi nghiệm thu artifact
