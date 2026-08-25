"""Thông báo API tiếng Việt cho ``api/v1/endpoints/`` (fork VN).

``api_error()`` / các schema response của upstream gán cứng chuỗi tiếng Trung —
không có tham số ngôn ngữ. Fork trước đây **ghi đè thẳng** các literal đó bằng
tiếng Anh/tiếng Việt, nên:

  * ``REPORT_LANGUAGE=zh`` nhận tiếng Anh/tiếng Việt (sai hành vi);
  * 4 test ``test_analysis_api_contract`` đỏ;
  * mỗi lần upstream sửa một thông báo là một conflict.

Nay literal tiếng Trung của upstream **giữ nguyên tại chỗ làm khoá tra cứu**,
chỉ bọc ``msg(...)``. Khoá chưa dịch -> trả về nguyên văn, không bao giờ
KeyError.

Khoá dùng ``{}`` cho phần nội suy (``msg`` gọi ``.format`` khi có kwargs) nên
tra cứu là so sánh chuỗi chính xác, không phải khớp tiền tố/hậu tố.
"""

from typing import Dict

__all__ = ["API_MESSAGES_VI", "msg"]

API_MESSAGES_VI: Dict[str, str] = {
    '请输入有效的股票代码或股票名称': 'Vui lòng nhập mã hoặc tên cổ phiếu hợp lệ',
    '单次分析请求最多支持 {max_batch} 只股票': 'Mỗi yêu cầu phân tích chỉ hỗ trợ tối đa {max_batch} mã cổ phiếu',
    '股票代码不能为空或仅包含空白字符': 'Mã cổ phiếu không được để trống hoặc chỉ chứa khoảng trắng',
    '同步模式仅支持单只股票分析，请使用 async_mode=true 进行批量分析': 'Chế độ đồng bộ chỉ hỗ trợ phân tích một mã; dùng async_mode=true để phân tích theo lô',
    '分析股票 {stock_code} 失败': 'Phân tích cổ phiếu {stock_code} thất bại',
    '大盘复盘': 'Phân tích thị trường',
    '大盘复盘任务已提交': 'Đã gửi yêu cầu phân tích thị trường',
    '大盘复盘任务已提交，完成后会保存报告并按配置推送通知': 'Đã gửi yêu cầu phân tích thị trường; báo cáo sẽ được lưu và gửi thông báo theo cấu hình.',
    '股票代码不能为空': 'Mã cổ phiếu không được để trống',
    "'{stripped}' 不是合法的股票代码格式": "'{stripped}' không phải định dạng mã cổ phiếu hợp lệ",
    '当前自选 {count} 只股票': 'Danh mục theo dõi hiện có {count} mã cổ phiếu',
    '未找到股票 {stock_code} 的行情数据': 'Không tìm thấy dữ liệu giá cho cổ phiếu {stock_code}',
    '服务器内部错误，请稍后重试': 'Lỗi nội bộ máy chủ, vui lòng thử lại sau',
    '请求参数验证失败': 'Xác thực tham số yêu cầu thất bại',
    '服务器内部错误': 'Lỗi nội bộ máy chủ',
}


def msg(template: str, **kwargs) -> str:
    """Đổi thông báo API sang tiếng Việt rồi nội suy.

    Đọc ngôn ngữ từ ``Config`` nên các endpoint không cần truyền thêm tham số.
    Bắt mọi lỗi: một dòng thông báo không bao giờ được phép làm vỡ response —
    thất bại thì trả về template gốc của upstream.
    """
    text = template
    try:
        from src.config import get_config
        from src.report_language import normalize_report_language

        lang = normalize_report_language(getattr(get_config(), "report_language", "zh"))
        if lang == "vi":
            text = API_MESSAGES_VI.get(template, template)
    except Exception:
        text = template
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except Exception:
        return text
