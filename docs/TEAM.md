# Danh sách thành viên & phân công — DeltaX

- **Tên nhóm:** DeltaX
- **Mã nhóm / lớp:** K4-L3B-DAY10
- **Repository nộp bài:** `K4-L3B-DAY10-DeltaX-DataPipelineDataObservability`

## Thành viên

| STT | Họ và tên | MSSV | Vai trò & phần việc chính | Báo cáo cá nhân |
| ---: | --- | --- | --- | --- |
| 1 | Phạm Xuân Quý | 2A202602745 | Thu thập dữ liệu, bảo toàn bản gốc, làm sạch dữ liệu và chuẩn bị văn bản tạo vector | `report/PhamXuanQuy-2A202602745.md` |
| 2 | Vũ Minh Điềm | 2A202602858 | Thiết lập Quality Gate bằng Great Expectations 1.x; xây dựng benchmark test set | `report/VuMinhDiem-2A202602858.md` |
| 3 | Nguyễn Minh Thịnh | 2A202602556 | Điều phối baseline pipeline; thiết kế và thực thi Data Corruption Suite | `report/2A202602556_NguyenMinhThinh.md` |
| 4 | Nguyễn Hoàng Tuyên | 2A202602439 | Đo lường suy giảm, xác minh repair và đối chiếu ba trạng thái Baseline–Corrupted–Repaired | `report/2A202602439_NguyenHoangTuyen.md` |

## Phân công theo luồng dữ liệu

| Khối công việc | Owner | Input | Output/bằng chứng cần bàn giao |
| --- | --- | --- | --- |
| Ingestion & raw preservation | Phạm Xuân Quý | Snapshot/Crossref response | `data/raw/` và raw records hợp lệ |
| Cleaning & embedding preparation | Phạm Xuân Quý | Raw records | Cleaned dataset, `text_for_embedding`, `age_days` |
| Quality & freshness | Vũ Minh Điềm | Cleaned dataset | Quality/freshness artifacts trong `data/quality/` |
| Benchmark evaluation set | Vũ Minh Điềm | Cleaned dataset và document IDs | `data/eval/test_set.json` |
| Baseline orchestration | Nguyễn Minh Thịnh | Các artifact pha 1 | Baseline metrics và `phase1_report.md` |
| Data corruption | Nguyễn Minh Thịnh | Baseline/cleaned artifacts | `corruption_log.json` và dữ liệu corrupted |
| Repair & comparison | Nguyễn Hoàng Tuyên | Corrupted artifacts, raw source, evaluation set cố định | Repaired metrics và `corruption_report.md` |

## Cam kết báo cáo

- Mỗi thành viên chỉ nhận ownership cho phần việc mình trực tiếp thực hiện và có bằng chứng từ code, artifact hoặc commit.
- Các chỉ số và kết luận trong báo cáo chỉ được điền sau khi chạy pipeline, không nhập thủ công.
- Không đưa `.env`, API key, token hoặc secret vào repository hay báo cáo.
