# Báo cáo đối chiếu 3 trạng thái — Baseline vs Corrupted vs Repaired

## 1. Tóm tắt điều hành (Executive Summary)

Báo cáo này đối chiếu định lượng hiệu năng của hệ thống RAG Agent và các tín hiệu Data Observability qua ba trạng thái:
1. **Baseline**: Dữ liệu sạch thu thập từ Crossref và chuẩn hóa đầy đủ.
2. **Corrupted**: Dữ liệu bị tiêm 6 kịch bản lỗi giả lập sự cố sản xuất (drop records, blank summary, noise, title truncation, stale date, duplicates).
3. **Repaired**: Dữ liệu được tự phục hồi theo cơ chế **Idempotent Repair** từ nguồn lưu trữ thô ban đầu (`data/raw/crossref_records.json`).

Tất cả ba trạng thái đều được đánh giá độc lập trên cùng bộ câu hỏi chuẩn hóa (`data/eval/test_set.json`, 10 câu hỏi) để đảm bảo tính khách quan và nhất quán.

## 2. Bảng đối chiếu định lượng (Comparison Matrix)

| Chỉ số / Tín hiệu | Baseline | Corrupted | Repaired | Đánh giá xu hướng / Tác động |
| :--- | :---: | :---: | :---: | :--- |
| `samples` (số câu test) | 10 | 10 | 10 | Đánh giá trên cùng 10 câu hỏi cố định |
| `retrieval_hit_rate` | 1.000 | 0.900 | 1.000 | Suy giảm khi bị xóa/nhiễu, phục hồi 100% |
| `mean_token_f1` | 1.000 | 0.800 | 1.000 | Rơi tự do do context hỏng/rỗng, khôi phục hoàn toàn |
| `judge_accuracy` | 1.000 | 0.800 | 1.000 | LLM/Heuristic judge bắt trọn sự cố câu trả lời |
| `mean_judge_score` | 5.00 | 4.20 | 5.00 | Điểm đánh giá sụt giảm sâu và lấy lại mức tối đa |
| **Quality Gate** (GX 1.x) | **True** | **False** | **True** | GX phát hiện tức thì vi phạm unique & độ dài summary |
| Failed checks | `none` | `expect_column_values_to_be_unique, expect_column_value_lengths_to_be_between` | `none` | Bắt đúng các kỳ vọng kiểm tra chất lượng |
| **Freshness SLA** | **True** | **False** | **True** | Báo động vi phạm ngưỡng stale ratio > 25% |
| Stale ratio (`age_days > 180`) | 0.0417 | 0.4545 | 0.0417 | Tỷ lệ dữ liệu quá hạn tăng vọt trong tập corrupted |

## 3. Phân tích tác động của Data Corruption (Silent Failure)

Trong trạng thái **Corrupted**, 6 kịch bản lỗi giả lập đã bộc lộ rõ rệt hai khía cạnh:
- **Phát hiện bởi Observability Gate**: Great Expectations 1.x lập tức đánh cờ `success=False` do phát hiện bản ghi trùng lặp (`ExpectColumnValuesToBeUnique`) và tóm tắt rỗng (`ExpectColumnValueLengthsToBeBetween`). Đồng thời Freshness SLA phát hiện tỷ lệ bài báo quá hạn vượt ngưỡng 25%.
- **Sự sụp đổ của RAG Agent (Silent Failure)**: Khi dữ liệu bị mất 20% bản ghi mới nhất hoặc summary bị xóa trắng/bơm nhiễu, vector store không thể truy xuất đúng tài liệu mục tiêu, dẫn đến `retrieval_hit_rate` và `mean_token_f1` sụt giảm nghiêm trọng.

## 4. Cơ chế tự phục hồi (Idempotent Repair)

Cơ chế phục hồi được thiết kế theo nguyên lý **Idempotent Repair**:
1. **Bảo toàn nguồn gốc (Data Lineage)**: Pipeline không sửa đè trực tiếp trên tập dữ liệu bẩn mà quay lại đọc bản snapshot thô bất biến `data/raw/crossref_records.json`.
2. **Làm sạch & tái lập cấu trúc (Deterministic Cleaning)**: Tái thực thi toàn bộ quy trình tiền xử lý, khử trùng lặp và tạo trường `text_for_embedding`.
3. **Tính Idempotent**: Việc thực thi lại hàm repair nhiều lần liên tiếp luôn tạo ra đúng cùng một tập bản ghi, không tích lũy bản ghi rác hay sai lệch schema.
4. **Tái chỉ mục (Vector Index Rebuilding)**: ChromaDB collection `papers-repaired` được khởi tạo mới hoàn toàn, loại bỏ triệt để 'ghost vectors' của trạng thái corrupted.

## 5. Kết luận

- Hệ thống đã minh chứng được tính toàn vẹn của chuỗi dữ liệu (Data Lineage).
- Data Observability (GX 1.x + Freshness SLA) là chốt chặn quan trọng ngăn chặn dữ liệu bẩn lọt vào production.
- Cơ chế Idempotent Repair khôi phục hoàn toàn chất lượng RAG Agent về trạng thái Baseline ban đầu.
