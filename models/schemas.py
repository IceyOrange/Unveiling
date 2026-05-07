from pydantic import BaseModel, Field
from typing import List, Optional


# ── Abstracter 输出 ──

class AbstractionLens(BaseModel):
    """一个抽象透镜——理解 topic 的一种高阶视角"""
    lens_name: str = Field(..., description="透镜名称，如'特定时代的前卫工具'")
    rationale: str = Field(..., description="为什么这个透镜能揭示 topic 的本质")
    horizontal_queries: List[str] = Field(
        ..., description="用于横向搜索的 query（跨领域）", min_length=2, max_length=5
    )
    vertical_queries: List[str] = Field(
        ..., description="用于纵向搜索的 query（跨时期）", min_length=2, max_length=5
    )


class AbstractionResult(BaseModel):
    """Abstracter 的完整输出"""
    topic: str = Field(..., description="原始 topic")
    lenses: List[AbstractionLens] = Field(
        ..., description="2-3 个抽象透镜", min_length=2, max_length=3
    )


# ── Discovery 输出 ──

class DiscoveredInstance(BaseModel):
    """一个被发现的同类实例"""
    name: str = Field(..., description="实例名称，如'蒸汽机'")
    era_or_domain: str = Field(..., description="所属时期或领域，如'工业时代'或'医学'")
    brief: str = Field(..., description="简要描述")
    source_lens: str = Field(..., description="来源于哪个透镜的搜索")
    relevance: str = Field(..., description="为什么与原始 topic 具有类比价值")


class VerticalDiscoveryResult(BaseModel):
    """纵向发现结果——穿越时间"""
    instances: List[DiscoveredInstance] = Field(
        ..., description="按时期排列的历史实例", min_length=3, max_length=8
    )
    chronological_pattern: str = Field(
        ..., description="这些实例在时间上呈现什么规律"
    )
    blackboard_anchors: List[str] = Field(
        default_factory=list, description="写入黑板的关键锚点"
    )


class HorizontalDiscoveryResult(BaseModel):
    """横向发现结果——穿越领域"""
    instances: List[DiscoveredInstance] = Field(
        ..., description="按领域排列的跨领域实例", min_length=3, max_length=8
    )
    cross_domain_pattern: str = Field(
        ..., description="这些实例跨领域呈现什么共性"
    )
    blackboard_anchors: List[str] = Field(
        default_factory=list, description="写入黑板的关键锚点"
    )


# ── Comparator 输出 ──

class PairwiseComparison(BaseModel):
    """原始 topic 与某个实例的对比"""
    instance_name: str = Field(..., description="对比对象名称")
    instance_era_or_domain: str = Field(..., description="对比对象的时期或领域")
    commonalities: List[str] = Field(
        ..., description="共性——两者共享的特征和模式", min_length=1
    )
    distinctions: List[str] = Field(
        ..., description="特性——各自独特的、不可互换的特征", min_length=1
    )
    insight: str = Field(..., description="这次对比揭示了什么")


class ComparisonResult(BaseModel):
    """所有对比结果"""
    topic: str = Field(..., description="原始 topic")
    vertical_comparisons: List[PairwiseComparison] = Field(
        ..., description="纵向对比组（原始 topic vs 历史实例）"
    )
    horizontal_comparisons: List[PairwiseComparison] = Field(
        ..., description="横向对比组（原始 topic vs 跨领域实例）"
    )
    vertical_pattern: str = Field(..., description="纵向对比揭示的历史规律")
    horizontal_pattern: str = Field(..., description="横向对比揭示的时代特征")


# ── Causal Reviewer 输出 ──

class ValidatedCommonality(BaseModel):
    """通过因果审查的共性"""
    commonality: str = Field(..., description="共性内容")
    causal_chain: str = Field(..., description="支撑该共性的因果链条")
    confidence: float = Field(
        ..., description="可信度评分 0-1", ge=0, le=1
    )
    supporting_comparisons: List[str] = Field(
        ..., description="哪些对比实例支持这个共性"
    )


class RejectedCommonality(BaseModel):
    """被因果审查剔除的共性"""
    commonality: str = Field(..., description="被剔除的共性")
    rejection_reason: str = Field(..., description="剔除原因")
    confounding_variable: Optional[str] = Field(
        None, description="导致伪相关的混淆变量"
    )


class CausalReviewResult(BaseModel):
    """因果审查结果"""
    validated: List[ValidatedCommonality] = Field(
        ..., description="通过审查的共性"
    )
    rejected: List[RejectedCommonality] = Field(
        ..., description="被剔除的共性"
    )
    overall_confidence: float = Field(
        ..., description="整体分析可信度 0-1", ge=0, le=1
    )


# ── Synthesizer 输出 ──

class SynthesisInsight(BaseModel):
    """一个综合洞察"""
    title: str = Field(..., description="洞察标题")
    description: str = Field(..., description="完整说明")
    vertical_evidence: str = Field(..., description="纵向证据")
    horizontal_evidence: str = Field(..., description="横向证据")
    implication: str = Field(..., description="这对原始 topic 意味着什么")


class AnalysisSynthesis(BaseModel):
    """最终综合分析"""
    topic: str = Field(..., description="原始 topic")
    core_thesis: str = Field(..., description="核心论点（横纵交叉后的结论）")
    vertical_summary: str = Field(..., description="纵向分析摘要")
    horizontal_summary: str = Field(..., description="横向分析摘要")
    insights: List[SynthesisInsight] = Field(
        ..., description="综合洞察", min_length=3, max_length=6
    )
    prediction: str = Field(..., description="基于分析的前瞻性预测")
    recommendations: List[str] = Field(
        ..., description="建议", min_length=1, max_length=4
    )


# ── Slide Generator 输入 ──

class SlideData(BaseModel):
    """传给 slide generator 的汇总数据"""
    topic: str
    lenses: List[str] = Field(..., description="透镜名称列表")
    vertical_instances: List[DiscoveredInstance]
    horizontal_instances: List[DiscoveredInstance]
    vertical_comparisons: List[PairwiseComparison]
    horizontal_comparisons: List[PairwiseComparison]
    validated_commonalities: List[ValidatedCommonality]
    rejected_commonalities: List[RejectedCommonality]
    insights: List[SynthesisInsight]
    core_thesis: str
    prediction: str
    recommendations: List[str]
    style_preset: str = Field(default="swiss-modern")
