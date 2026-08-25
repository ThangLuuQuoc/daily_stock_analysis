"""Thông báo tiến trình tiếng Việt cho ``src/core/pipeline.py``.

Trước đây fork dịch thẳng 11 chuỗi ``_emit_progress()`` tại chỗ, xoá hẳn bản
tiếng Trung của upstream. Hậu quả: ``REPORT_LANGUAGE=zh|en|ko`` vẫn thấy tiến
trình tiếng Việt, và mỗi lần upstream đổi thông báo là một conflict.

Nay ``pipeline.py`` giữ nguyên **template tiếng Trung của upstream ngay tại
chỗ** làm khoá tra cứu, chỉ bọc ``self._tr(...)``. Chưa dịch thì hiện tiếng
Trung — không bao giờ vỡ.

Khoá là template CHƯA nội suy (còn ``{code}`` / ``{stock_name}``), không phải
chuỗi đã format, nên tra cứu là so sánh chuỗi chính xác chứ không phải khớp
tiền tố/hậu tố mong manh.
"""

from typing import Dict

__all__ = ["PROGRESS_VI", "translate"]

# khoá = template tiếng Trung của upstream, y nguyên trong pipeline.py
PROGRESS_VI: Dict[str, str] = {
    '{code}：正在获取行情与筹码数据': '{code}: Đang lấy dữ liệu giá & giao dịch',
    '{stock_name}：正在聚合基本面与趋势数据': '{stock_name}: Đang tổng hợp dữ liệu cơ bản & xu hướng',
    '{stock_name}：正在切换 Agent 分析链路': '{stock_name}: Đang chuyển luồng phân tích Agent',
    '{stock_name}：正在检索新闻与舆情': '{stock_name}: Đang tìm tin tức & dư luận',
    '{stock_name}：正在整理分析上下文': '{stock_name}: Đang chuẩn bị ngữ cảnh phân tích',
    '{stock_name}：正在请求 LLM 生成报告': '{stock_name}: Đang yêu cầu LLM tạo báo cáo',
    '{stock_name}：正在校验并整理分析结果': '{stock_name}: Đang kiểm tra & sắp xếp kết quả phân tích',
    '{stock_name}：正在保存分析报告': '{stock_name}: Đang lưu báo cáo phân tích',
    '{code}：正在准备分析任务': '{code}: Đang chuẩn bị tác vụ phân tích',
    '{code}：行情数据准备完成': '{code}: Đã chuẩn bị xong dữ liệu giá',
    '{stock_name}：LLM 正在生成分析结果（已接收 {chars_received} 字符）': '{stock_name}: LLM đang tạo kết quả phân tích (đã nhận {chars_received} ký tự)',
}


def translate(template: str, report_language: str) -> str:
    """Đổi template sang tiếng Việt; ngôn ngữ khác trả về nguyên văn.

    Chưa dịch -> trả về chính ``template`` (tiếng Trung của upstream), không bao
    giờ ném KeyError. Thấy sai ngôn ngữ trong thanh tiến trình dễ phát hiện hơn
    nhiều so với việc phân tích bị vỡ.
    """
    if report_language != "vi":
        return template
    return PROGRESS_VI.get(template, template)
