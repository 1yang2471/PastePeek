"""已移除来源类型推断的回归测试。"""

from dataclasses import fields

from src.analyzer.deep_analyzer import DeepAnalysis, DeepAnalyzer


def test_deep_analysis_exposes_no_source_inference_fields():
    """结构分析结果不得恢复来源应用或来源类型推断。"""
    result = DeepAnalyzer().analyze(
        html='<p style="mso-style-name:Normal">正文</p>',
        text="正文",
    )
    public_fields = {field.name for field in fields(DeepAnalysis)}

    assert "is_mso_source" not in public_fields
    assert "source_estimate" not in public_fields
    assert not hasattr(result, "is_mso_source")
    assert not hasattr(result, "source_estimate")
