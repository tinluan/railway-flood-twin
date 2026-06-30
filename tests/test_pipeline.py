import pytest
from unittest.mock import patch, MagicMock
from src.engine.pipeline_orchestrator import PipelineOrchestrator

class TestPipelineOrchestrator:
    @patch("src.engine.pipeline_orchestrator.RainfallIngestor")
    @patch("src.engine.pipeline_orchestrator.SWICalculator")
    def test_run_cycle_demo_mode(self, mock_swi_class, mock_ingestor_class, tmp_path):
        # Setup mocks
        mock_ingestor = mock_ingestor_class.return_value
        mock_ingestor.output_file = tmp_path / "dummy.csv"
        mock_ingestor.get_active_rainfall.return_value = (mock_ingestor.output_file, "demo")

        mock_swi = mock_swi_class.return_value
        mock_swi_df = MagicMock()
        mock_swi_df["swi_mm"].max.return_value = 50.0  # Below HEC-RAS threshold
        mock_swi.process_corridor_risk.return_value = mock_swi_df

        # Run cycle
        orc = PipelineOrchestrator()
        orc.log_file = tmp_path / "cycle_log.json"
        
        result = orc.run_cycle(source_mode="demo")

        assert result["status"] == "success"
        assert result["source_mode"] == "demo"
        assert result["swi_peak_mm"] == 50.0
        assert not result["hecras_triggered"]
        
    @patch("src.engine.pipeline_orchestrator.RainfallIngestor")
    @patch("src.engine.pipeline_orchestrator.SWICalculator")
    def test_run_cycle_hecras_trigger(self, mock_swi_class, mock_ingestor_class, tmp_path):
        # Setup mocks
        mock_ingestor = mock_ingestor_class.return_value
        mock_ingestor.output_file = tmp_path / "dummy.csv"

        mock_swi = mock_swi_class.return_value
        mock_swi_df = MagicMock()
        mock_swi_df["swi_mm"].max.return_value = 150.0  # Above HEC-RAS threshold (100)
        mock_swi.process_corridor_risk.return_value = mock_swi_df

        # Run cycle
        orc = PipelineOrchestrator()
        orc.log_file = tmp_path / "cycle_log.json"
        
        # We test with force_hecras to explicitly check that path
        result = orc.run_cycle(source_mode="demo", force_hecras=True)

        assert result["status"] == "success"
        assert result["hecras_triggered"] is True
        assert "HEC-RAS recomputed successfully" in result["message"]
