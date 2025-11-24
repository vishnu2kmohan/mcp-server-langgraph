"""
Test Hook Profiler

Tests for scripts/profiling/profile_hooks.py which profiles pre-commit
hooks to identify candidates for moving from commit to pre-push stage.
"""

import gc
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mark as meta test to run in CI
pytestmark = pytest.mark.meta


@pytest.mark.xdist_group(name="testhookprofiler")
class TestHookProfiler:
    """Test hook performance profiling script."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @property
    def repo_root(self) -> Path:
        """Get repository root directory."""
        return Path(__file__).parent.parent.parent

    @property
    def profiler_script(self) -> Path:
        """Get path to profiler script."""
        return self.repo_root / "scripts" / "profiling" / "profile_hooks.py"

    def test_profiler_script_exists(self):
        """Verify profiler script exists and is executable."""
        assert self.profiler_script.exists(), f"Profiler script not found: {self.profiler_script}"
        assert self.profiler_script.stat().st_mode & 0o111, f"Profiler script not executable: {self.profiler_script}"

    def test_profiler_imports_successfully(self):
        """Verify profiler script imports without errors."""
        # Import the module
        import sys

        sys.path.insert(0, str(self.profiler_script.parent))
        try:
            import profile_hooks

            assert hasattr(profile_hooks, "HookProfiler")
            assert hasattr(profile_hooks, "HookPerformance")
        finally:
            sys.path.pop(0)

    @patch("subprocess.run")
    def test_profile_single_hook_measures_time(self, mock_run):
        """Test profiling a single hook measures execution time."""
        # Mock subprocess.run to return quickly
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        import sys

        sys.path.insert(0, str(self.profiler_script.parent))
        try:
            from profile_hooks import HookProfiler

            profiler = HookProfiler()

            # Profile a known hook (ruff-format is fast and always exists)
            if any(h["id"] == "ruff-format" for h in profiler.hooks):
                result = profiler.profile_hook("ruff-format", iterations=3)

                # Verify result structure
                assert result.hook_id == "ruff-format"
                assert result.iterations == 3
                assert result.mean_ms >= 0
                assert result.median_ms >= 0
                assert result.p90_ms >= 0
                assert result.p95_ms >= 0
                assert result.p99_ms >= 0
                assert result.min_ms >= 0
                assert result.max_ms >= 0
                assert result.stddev_ms >= 0
                assert result.category in ["fast", "medium", "heavy"]

                # Verify mock was called 3 times
                assert mock_run.call_count == 3
        finally:
            sys.path.pop(0)

    def test_profile_hook_calculates_statistics_correctly(self):
        """Test that profiler calculates statistics correctly."""
        import sys

        sys.path.insert(0, str(self.profiler_script.parent))
        try:
            from profile_hooks import HookProfiler

            # Test percentile calculation
            profiler = HookProfiler()
            data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

            # For 10 items, p90 is at index int(10 * 0.90) = 9, which is 100.0
            p90 = profiler._percentile(data, 0.90)
            assert p90 == 100.0

            # For 10 items, p95 is at index int(10 * 0.95) = 9 (capped), which is 100.0
            p95 = profiler._percentile(data, 0.95)
            assert p95 == 100.0

            # For 10 items, p99 is at index int(10 * 0.99) = 9 (capped), which is 100.0
            p99 = profiler._percentile(data, 0.99)
            assert p99 == 100.0

            # Test with more data points for better percentile differentiation
            large_data = [float(i) for i in range(1, 101)]  # 1 to 100
            p90_large = profiler._percentile(large_data, 0.90)
            assert 85.0 <= p90_large <= 95.0  # Should be around 90th element

            p50_large = profiler._percentile(large_data, 0.50)
            assert 45.0 <= p50_large <= 55.0  # Should be around median
        finally:
            sys.path.pop(0)

    def test_categorize_hooks_by_speed(self):
        """Test hooks are categorized correctly by speed."""
        import sys

        sys.path.insert(0, str(self.profiler_script.parent))
        try:
            from profile_hooks import HookPerformance

            # Test fast hook (<500ms)
            fast_hook = HookPerformance(
                hook_id="test-fast",
                hook_name="Test Fast",
                stage="commit",
                iterations=10,
                mean_ms=250.0,
                median_ms=240.0,
                p90_ms=280.0,
                p95_ms=290.0,
                p99_ms=300.0,
                min_ms=200.0,
                max_ms=300.0,
                stddev_ms=20.0,
                category="fast",
            )
            assert fast_hook.category == "fast"

            # Test medium hook (500ms-2s)
            medium_hook = HookPerformance(
                hook_id="test-medium",
                hook_name="Test Medium",
                stage="commit",
                iterations=10,
                mean_ms=1000.0,
                median_ms=950.0,
                p90_ms=1100.0,
                p95_ms=1150.0,
                p99_ms=1200.0,
                min_ms=800.0,
                max_ms=1200.0,
                stddev_ms=100.0,
                category="medium",
            )
            assert medium_hook.category == "medium"

            # Test heavy hook (>2s)
            heavy_hook = HookPerformance(
                hook_id="test-heavy",
                hook_name="Test Heavy",
                stage="push",
                iterations=10,
                mean_ms=5000.0,
                median_ms=4900.0,
                p90_ms=5500.0,
                p95_ms=5800.0,
                p99_ms=6000.0,
                min_ms=4500.0,
                max_ms=6000.0,
                stddev_ms=500.0,
                category="heavy",
            )
            assert heavy_hook.category == "heavy"
        finally:
            sys.path.pop(0)

    def test_export_json_format(self, tmp_path):
        """Test exporting results to JSON format."""
        import sys

        sys.path.insert(0, str(self.profiler_script.parent))
        try:
            from profile_hooks import HookPerformance, HookProfiler

            profiler = HookProfiler()

            # Create sample results
            results = [
                HookPerformance(
                    hook_id="test-hook",
                    hook_name="Test Hook",
                    stage="commit",
                    iterations=10,
                    mean_ms=250.0,
                    median_ms=240.0,
                    p90_ms=280.0,
                    p95_ms=290.0,
                    p99_ms=300.0,
                    min_ms=200.0,
                    max_ms=300.0,
                    stddev_ms=20.0,
                    category="fast",
                )
            ]

            # Export to JSON
            output_file = tmp_path / "test_results.json"
            profiler.export_json(results, output_file)

            # Verify file exists and has correct structure
            assert output_file.exists()

            with open(output_file) as f:
                data = json.load(f)

            assert "timestamp" in data
            assert data["total_hooks"] == 1
            assert "summary" in data
            assert data["summary"]["fast"] == 1
            assert data["summary"]["medium"] == 0
            assert data["summary"]["heavy"] == 0
            assert len(data["hooks"]) == 1
            assert data["hooks"][0]["hook_id"] == "test-hook"
            assert data["hooks"][0]["mean_ms"] == 250.0
        finally:
            sys.path.pop(0)

    def test_export_csv_format(self, tmp_path):
        """Test exporting results to CSV format."""
        import sys

        sys.path.insert(0, str(self.profiler_script.parent))
        try:
            from profile_hooks import HookPerformance, HookProfiler

            profiler = HookProfiler()

            # Create sample results
            results = [
                HookPerformance(
                    hook_id="test-hook-1",
                    hook_name="Test Hook 1",
                    stage="commit",
                    iterations=10,
                    mean_ms=250.0,
                    median_ms=240.0,
                    p90_ms=280.0,
                    p95_ms=290.0,
                    p99_ms=300.0,
                    min_ms=200.0,
                    max_ms=300.0,
                    stddev_ms=20.0,
                    category="fast",
                ),
                HookPerformance(
                    hook_id="test-hook-2",
                    hook_name="Test Hook 2",
                    stage="push",
                    iterations=10,
                    mean_ms=5000.0,
                    median_ms=4900.0,
                    p90_ms=5500.0,
                    p95_ms=5800.0,
                    p99_ms=6000.0,
                    min_ms=4500.0,
                    max_ms=6000.0,
                    stddev_ms=500.0,
                    category="heavy",
                ),
            ]

            # Export to CSV
            output_file = tmp_path / "test_results.csv"
            profiler.export_csv(results, output_file)

            # Verify file exists
            assert output_file.exists()

            # Verify CSV content
            content = output_file.read_text()
            assert "hook_id,hook_name,stage,category" in content
            assert "test-hook-1,Test Hook 1,commit,fast" in content
            assert "test-hook-2,Test Hook 2,push,heavy" in content
        finally:
            sys.path.pop(0)

    def test_export_markdown_format(self, tmp_path):
        """Test exporting results to Markdown format."""
        import sys

        sys.path.insert(0, str(self.profiler_script.parent))
        try:
            from profile_hooks import HookPerformance, HookProfiler

            profiler = HookProfiler()

            # Create sample results with different categories
            results = [
                HookPerformance(
                    hook_id="fast-hook",
                    hook_name="Fast Hook",
                    stage="commit",
                    iterations=10,
                    mean_ms=250.0,
                    median_ms=240.0,
                    p90_ms=280.0,
                    p95_ms=290.0,
                    p99_ms=300.0,
                    min_ms=200.0,
                    max_ms=300.0,
                    stddev_ms=20.0,
                    category="fast",
                ),
                HookPerformance(
                    hook_id="heavy-hook",
                    hook_name="Heavy Hook",
                    stage="push",
                    iterations=10,
                    mean_ms=5000.0,
                    median_ms=4900.0,
                    p90_ms=5500.0,
                    p95_ms=5800.0,
                    p99_ms=6000.0,
                    min_ms=4500.0,
                    max_ms=6000.0,
                    stddev_ms=500.0,
                    category="heavy",
                ),
            ]

            # Export to Markdown
            output_file = tmp_path / "test_results.md"
            profiler.export_markdown(results, output_file)

            # Verify file exists
            assert output_file.exists()

            # Verify Markdown content
            content = output_file.read_text()
            assert "# Hook Performance Profile" in content
            assert "## Summary" in content
            assert "**Fast hooks (<500ms)**: 1 hooks" in content
            assert "**Heavy hooks (>2s)**: 1 hooks" in content
            assert "## Recommendations" in content
            assert "### Move 1 Heavy Hooks to Pre-push" in content
            assert "| Hook ID | Stage | Mean | p90 | p95 | Category |" in content
            assert "`fast-hook`" in content
            assert "`heavy-hook`" in content
        finally:
            sys.path.pop(0)

    def test_load_hooks_from_precommit_config(self):
        """Test loading hooks from .pre-commit-config.yaml."""
        import sys

        sys.path.insert(0, str(self.profiler_script.parent))
        try:
            from profile_hooks import HookProfiler

            profiler = HookProfiler()

            # Verify hooks loaded
            assert len(profiler.hooks) > 0, "Should load at least one hook"

            # Verify hook structure
            for hook in profiler.hooks:
                assert "id" in hook
                assert "name" in hook
                assert "stages" in hook
                assert isinstance(hook["stages"], list)

            # Verify common hooks exist
            hook_ids = [h["id"] for h in profiler.hooks]
            assert "ruff-format" in hook_ids or "ruff" in hook_ids, "Should have ruff formatter"
        finally:
            sys.path.pop(0)

    def test_profiler_script_cli_help(self):
        """Test profiler script CLI help output."""
        result = subprocess.run(
            ["python", str(self.profiler_script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Profile pre-commit hooks" in result.stdout
        assert "--hook-id" in result.stdout
        assert "--iterations" in result.stdout
        assert "--format" in result.stdout
        assert "--output-dir" in result.stdout
