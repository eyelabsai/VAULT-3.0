"""
Post-processing gestalt rules for lens sizing recommendations.

These rules do NOT change the model output. They provide an optional
advisory recommendation based on clinician-style heuristics.
"""

from typing import Dict, List


def apply_gestalt_advice(
    input_data: Dict[str, float],
    model_size: float,
    model_prob: float | None = None,
    enabled: bool = False,
    toric: bool = False,
) -> List[Dict[str, str]]:
    """
    Return a list of advisory recommendations.

    Each item: {"recommendation": "...", "reason": "..."}
    """
    if not enabled:
        return []

    wtw = input_data.get("WTW")
    acd = input_data.get("ACD_internal")

    advice: List[Dict[str, str]] = []

    # Example rule: if ACD > 3.2 and WTW > 12.1, consider sizing up from 12.6 -> 13.2
    if (
        wtw is not None
        and acd is not None
        and wtw > 12.1
        and acd > 3.2
        and not toric
        and abs(model_size - 12.6) < 0.01
    ):
        reason = "ACD > 3.2 and WTW > 12.1 suggests a larger size in borderline cases."
        if model_prob is not None:
            reason = f"{reason} (model prob {model_prob:.1%})"
        advice.append(
            {
                "recommendation": "Consider 13.2 mm",
                "reason": reason,
            }
        )

    return advice

