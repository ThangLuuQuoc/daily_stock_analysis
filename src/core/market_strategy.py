# -*- coding: utf-8 -*-
"""Market strategy blueprints for CN/HK/US daily market recap."""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class StrategyDimension:
    """Single strategy dimension used by market recap prompts."""

    name: str
    objective: str
    checkpoints: List[str]


@dataclass(frozen=True)
class MarketStrategyBlueprint:
    """Region specific market strategy blueprint."""

    region: str
    title: str
    positioning: str
    principles: List[str]
    dimensions: List[StrategyDimension]
    action_framework: List[str]

    def to_prompt_block(self) -> str:
        """Render blueprint as prompt instructions."""
        principles_text = "\n".join([f"- {item}" for item in self.principles])
        action_text = "\n".join([f"- {item}" for item in self.action_framework])

        dims = []
        for dim in self.dimensions:
            checkpoints = "\n".join([f"  - {cp}" for cp in dim.checkpoints])
            dims.append(f"- {dim.name}: {dim.objective}\n{checkpoints}")
        dimensions_text = "\n".join(dims)

        return (
            f"## Strategy Blueprint: {self.title}\n"
            f"{self.positioning}\n\n"
            f"### Strategy Principles\n{principles_text}\n\n"
            f"### Analysis Dimensions\n{dimensions_text}\n\n"
            f"### Action Framework\n{action_text}"
        )

    def to_markdown_block(self) -> str:
        """Render blueprint as markdown section for template fallback report."""
        dims = "\n".join([f"- **{dim.name}**: {dim.objective}" for dim in self.dimensions])
        section_title = "### VI. Strategy Framework" if self.region == "us" else "### VI. Khung chiến lược"
        return f"{section_title}\n{dims}\n"


CN_BLUEPRINT = MarketStrategyBlueprint(
    region="cn",
    title="Chiến lược phục thị ba bước thị trường A-share",
    positioning="Tập trung vào xu hướng chỉ số, dòng tiền và luân chuyển nhóm ngành để xây dựng kế hoạch giao dịch cho phiên tới.",
    principles=[
        "Trước tiên xem hướng đi của chỉ số, rồi đến cấu trúc khối lượng, cuối cùng là tính bền vững của nhóm ngành.",
        "Kết luận bắt buộc phải chuyển thành hành động về tỷ trọng, nhịp giao dịch và kiểm soát rủi ro.",
        "Chỉ phán đoán dựa trên dữ liệu trong ngày và tin tức 3 ngày gần nhất, không suy diễn thông tin chưa được kiểm chứng.",
    ],
    dimensions=[
        StrategyDimension(
            name="Cấu trúc xu hướng",
            objective="Xác định thị trường đang ở giai đoạn tăng, đi ngang hay phòng thủ.",
            checkpoints=["Các chỉ số chính có đồng pha không", "Tăng kèm khối lượng lớn hay giảm kèm khối lượng thấp có thành lập không", "Các vùng hỗ trợ/kháng cự then chốt có bị phá vỡ không"],
        ),
        StrategyDimension(
            name="Dòng tiền và tâm lý",
            objective="Nhận diện khẩu vị rủi ro ngắn hạn và nhiệt độ tâm lý.",
            checkpoints=["Số mã tăng/giảm và cấu trúc trần/sàn", "Giá trị giao dịch có mở rộng không", "Cổ phiếu vùng giá cao có xuất hiện phân kỳ không"],
        ),
        StrategyDimension(
            name="Nhóm ngành chủ đạo",
            objective="Chắt lọc chủ đề có thể giao dịch và hướng cần tránh.",
            checkpoints=["Nhóm ngành dẫn dắt có xúc tác sự kiện không", "Trong nhóm ngành có cổ phiếu đầu tàu dẫn dắt không", "Nhóm ngành giảm mạnh có lan rộng không"],
        ),
    ],
    action_framework=[
        "Tấn công: chỉ số cùng đi lên + giá trị giao dịch mở rộng + chủ đề chủ đạo được củng cố.",
        "Cân bằng: chỉ số phân hóa hoặc đi ngang thanh khoản thấp, kiểm soát tỷ trọng và chờ xác nhận.",
        "Phòng thủ: chỉ số chuyển yếu + nhóm ngành giảm mạnh lan rộng, ưu tiên kiểm soát rủi ro và giảm tỷ trọng.",
    ],
)

US_BLUEPRINT = MarketStrategyBlueprint(
    region="us",
    title="US Market Regime Strategy",
    positioning="Focus on index trend, macro narrative, and sector rotation to define next-session risk posture.",
    principles=[
        "Read market regime from S&P 500, Nasdaq, and Dow alignment first.",
        "Separate beta move from theme-driven alpha rotation.",
        "Translate recap into actionable risk-on/risk-off stance with clear invalidation points.",
    ],
    dimensions=[
        StrategyDimension(
            name="Trend Regime",
            objective="Classify the market as momentum, range, or risk-off.",
            checkpoints=[
                "Are SPX/NDX/DJI directionally aligned",
                "Did volume confirm the move",
                "Are key index levels reclaimed or lost",
            ],
        ),
        StrategyDimension(
            name="Macro & Flows",
            objective="Map policy/rates narrative into equity risk appetite.",
            checkpoints=[
                "Treasury yield and USD implications",
                "Breadth and leadership concentration",
                "Defensive vs growth factor rotation",
            ],
        ),
        StrategyDimension(
            name="Sector Themes",
            objective="Identify persistent leaders and vulnerable laggards.",
            checkpoints=[
                "AI/semiconductor/software trend persistence",
                "Energy/financials sensitivity to macro data",
                "Volatility signals from VIX and large-cap earnings",
            ],
        ),
    ],
    action_framework=[
        "Risk-on: broad index breakout with expanding participation.",
        "Neutral: mixed index signals; focus on selective relative strength.",
        "Risk-off: failed breakouts and rising volatility; prioritize capital preservation.",
    ],
)

HK_BLUEPRINT = MarketStrategyBlueprint(
    region="hk",
    title="Chiến lược phục thị ba bước thị trường Hồng Kông",
    positioning="Tập trung vào xu hướng chỉ số Hang Seng, dòng vốn Nam hướng và luân chuyển nhóm ngành để xây dựng kế hoạch giao dịch cho phiên tới.",
    principles=[
        "Trước tiên xem hướng đi của các chỉ số Hang Seng/Hang Seng Tech/HSCEI, rồi đến tâm lý dòng vốn Nam hướng, cuối cùng là tính bền vững của nhóm ngành.",
        "Kết luận bắt buộc phải chuyển thành hành động về tỷ trọng, nhịp giao dịch và kiểm soát rủi ro.",
        "Chỉ phán đoán dựa trên dữ liệu trong ngày và tin tức 3 ngày gần nhất, không suy diễn thông tin chưa được kiểm chứng.",
    ],
    dimensions=[
        StrategyDimension(
            name="Cấu trúc xu hướng",
            objective="Xác định thị trường đang ở giai đoạn tăng, đi ngang hay phòng thủ.",
            checkpoints=["Các chỉ số Hang Seng/Hang Seng Tech/HSCEI có đồng pha không", "Tăng kèm khối lượng lớn hay giảm kèm khối lượng thấp có thành lập không", "Các vùng hỗ trợ/kháng cự then chốt có bị phá vỡ không"],
        ),
        StrategyDimension(
            name="Dòng tiền và tâm lý",
            objective="Nhận diện khẩu vị rủi ro của dòng vốn Nam hướng và nhiệt độ tâm lý.",
            checkpoints=["Hướng và quy mô dòng vốn Nam hướng ròng", "Tỷ giá HKD và hàm ý chính sách Trung Quốc đại lục", "Độ rộng thị trường và mức độ tập trung vào cổ phiếu đầu tàu"],
        ),
        StrategyDimension(
            name="Nhóm ngành chủ đạo",
            objective="Chắt lọc chủ đề có thể giao dịch và hướng cần tránh.",
            checkpoints=["Tính bền vững xu hướng của nhóm công nghệ/nền tảng internet", "Độ nhạy của nhóm tài chính/bất động sản với thay đổi chính sách", "Luân chuyển giữa nhóm phòng thủ và nhóm tăng trưởng"],
        ),
    ],
    action_framework=[
        "Tấn công: chỉ số Hang Seng cùng đi lên + dòng vốn Nam hướng tiếp tục chảy vào + chủ đề chủ đạo được củng cố.",
        "Cân bằng: chỉ số phân hóa hoặc đi ngang thanh khoản thấp, kiểm soát tỷ trọng và chờ xác nhận.",
        "Phòng thủ: chỉ số chuyển yếu + độ biến động tăng, ưu tiên kiểm soát rủi ro và giảm tỷ trọng.",
    ],
)


VN_BLUEPRINT = MarketStrategyBlueprint(
    region="vn",
    title="Chiến lược phục thị ba bước thị trường Việt Nam",
    positioning="Tập trung vào xu hướng VN-Index, dòng tiền (gồm khối ngoại) và luân chuyển nhóm ngành để xây dựng kế hoạch giao dịch cho phiên tới.",
    principles=[
        "Trước tiên xem hướng đi của VN-Index, rồi đến cấu trúc khối lượng, cuối cùng là tính bền vững của nhóm ngành.",
        "Kết luận bắt buộc phải chuyển thành hành động về tỷ trọng, nhịp giao dịch và kiểm soát rủi ro.",
        "Chỉ phán đoán dựa trên dữ liệu trong ngày và tin tức 3 ngày gần nhất, không suy diễn thông tin chưa được kiểm chứng.",
    ],
    dimensions=[
        StrategyDimension(
            name="Cấu trúc xu hướng",
            objective="Xác định thị trường đang ở giai đoạn tăng, đi ngang hay phòng thủ.",
            checkpoints=["VN-Index ở trên hay dưới MA20/MA50", "Tăng kèm khối lượng lớn hay giảm kèm khối lượng thấp có thành lập không", "Các vùng hỗ trợ/kháng cự then chốt có bị phá vỡ không"],
        ),
        StrategyDimension(
            name="Dòng tiền và tâm lý",
            objective="Nhận diện khẩu vị rủi ro ngắn hạn và nhiệt độ tâm lý.",
            checkpoints=["Số mã tăng/giảm và độ rộng thị trường", "Giá trị giao dịch có mở rộng không", "Khối ngoại mua/bán ròng nghiêng về phía nào"],
        ),
        StrategyDimension(
            name="Nhóm ngành chủ đạo",
            objective="Chắt lọc chủ đề có thể giao dịch và hướng cần tránh.",
            checkpoints=["Nhóm ngành dẫn dắt có xúc tác sự kiện không", "Trong nhóm ngành có cổ phiếu đầu tàu dẫn dắt không", "Nhóm ngành giảm mạnh có lan rộng không"],
        ),
    ],
    action_framework=[
        "Tấn công: VN-Index đi lên + giá trị giao dịch mở rộng + chủ đề chủ đạo được củng cố.",
        "Cân bằng: chỉ số phân hóa hoặc đi ngang thanh khoản thấp, kiểm soát tỷ trọng và chờ xác nhận.",
        "Phòng thủ: chỉ số chuyển yếu + nhóm ngành giảm mạnh lan rộng, ưu tiên kiểm soát rủi ro và giảm tỷ trọng.",
    ],
)


JP_BLUEPRINT = MarketStrategyBlueprint(
    region="jp",
    title="日本市场三段式复盘策略",
    positioning="聚焦日经225、东证指数、汇率与全球风险偏好，形成次日交易计划。",
    principles=[
        "先看日经225与TOPIX是否同向，再看日元、半导体/出口链与金融股表现。",
        "把指数结论映射到仓位、节奏与风险控制动作。",
        "只基于可得指数、新闻和价格行为判断，不臆造市场广度或板块统计。",
    ],
    dimensions=[
        StrategyDimension(
            name="趋势结构",
            objective="判断日本市场处于上攻、震荡还是防守阶段。",
            checkpoints=["日经225/TOPIX是否同向", "指数是否突破或跌破关键区间", "大盘权重与成长链是否共振"],
        ),
        StrategyDimension(
            name="宏观与汇率",
            objective="识别日元、利率和全球风险偏好对权益市场的影响。",
            checkpoints=["日元方向对出口链的影响", "日本央行和美债利率叙事", "海外科技股与半导体链映射"],
        ),
        StrategyDimension(
            name="主题线索",
            objective="提炼可延续主线与需要规避的拥挤方向。",
            checkpoints=["半导体/自动化/汽车链持续性", "金融与内需股是否轮动", "新闻催化是否支撑价格行为"],
        ),
    ],
    action_framework=[
        "进攻：主要指数共振上行 + 外部风险偏好改善 + 主线强化。",
        "均衡：指数分化或汇率扰动，降低追涨并等待确认。",
        "防守：主要指数转弱或外部风险升温，优先控制仓位。",
    ],
)

KR_BLUEPRINT = MarketStrategyBlueprint(
    region="kr",
    title="韩国市场三段式复盘策略",
    positioning="聚焦 KOSPI、KOSDAQ、半导体权重与全球科技风险偏好，形成次日交易计划。",
    principles=[
        "先看 KOSPI/KOSDAQ 是否同向，再看三星电子、SK 海力士等权重线索。",
        "区分指数 beta、半导体周期和成长股风险偏好的贡献。",
        "只基于可得指数、新闻和价格行为判断，不臆造市场广度或板块统计。",
    ],
    dimensions=[
        StrategyDimension(
            name="趋势结构",
            objective="判断韩国市场处于上攻、震荡还是防守阶段。",
            checkpoints=["KOSPI/KOSDAQ 是否同向", "权重股是否支撑指数", "关键支撑阻力是否被突破"],
        ),
        StrategyDimension(
            name="科技周期",
            objective="识别半导体、AI 硬件和全球科技股对韩国市场的映射。",
            checkpoints=["存储/半导体链新闻催化", "美股科技方向联动", "外资风险偏好变化"],
        ),
        StrategyDimension(
            name="主题线索",
            objective="提炼可延续主线与需要规避的拥挤方向。",
            checkpoints=["电池/汽车/互联网是否轮动", "KOSDAQ 成长股风险偏好", "新闻催化是否支撑价格行为"],
        ),
    ],
    action_framework=[
        "进攻：KOSPI/KOSDAQ 共振上行 + 科技权重确认 + 外部风险偏好改善。",
        "均衡：指数或权重股分化，控制仓位并等待确认。",
        "防守：科技权重转弱或外部风险升温，优先控制回撤。",
    ],
)

def get_market_strategy_blueprint(region: str) -> MarketStrategyBlueprint:
    """Return strategy blueprint by market region."""
    if region == "us":
        return US_BLUEPRINT
    if region == "hk":
        return HK_BLUEPRINT
    if region == "vn":
        return VN_BLUEPRINT
    if region == "jp":
        return JP_BLUEPRINT
    if region == "kr":
        return KR_BLUEPRINT
    return CN_BLUEPRINT
