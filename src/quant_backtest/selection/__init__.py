"""Daily stock selection and selector backtesting utilities."""

from quant_backtest.selection.backtest import SelectionBacktestConfig, run_selection_backtest
from quant_backtest.selection.backtrader_validation import (
    SelectorBacktraderValidationConfig,
    run_selector_backtrader_validation,
)
from quant_backtest.selection.diagnostics import (
    SelectorValidationGapConfig,
    run_selector_validation_gap,
)
from quant_backtest.selection.execution import (
    SelectionExecutionConfig,
    run_selection_execution_simulation,
    sweep_selection_execution,
)
from quant_backtest.selection.factors import FactorSelectorConfig, build_factor_table, select_candidates
from quant_backtest.selection.hit_rate import (
    SelectionHitRateConfig,
    evaluate_candidate_hit_rate,
    run_selection_hit_rate,
    summarize_factor_attribution,
    summarize_daily_hit_rate,
    summarize_overall_hit_rate,
    sweep_selection_hit_rate,
)

__all__ = [
    "FactorSelectorConfig",
    "SelectionBacktestConfig",
    "SelectionExecutionConfig",
    "SelectionHitRateConfig",
    "SelectorBacktraderValidationConfig",
    "SelectorValidationGapConfig",
    "build_factor_table",
    "evaluate_candidate_hit_rate",
    "run_selection_backtest",
    "run_selection_execution_simulation",
    "sweep_selection_execution",
    "run_selection_hit_rate",
    "run_selector_backtrader_validation",
    "run_selector_validation_gap",
    "summarize_factor_attribution",
    "select_candidates",
    "summarize_daily_hit_rate",
    "summarize_overall_hit_rate",
    "sweep_selection_hit_rate",
]
