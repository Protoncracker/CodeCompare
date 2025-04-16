import os
import sys
import math
import json
import time
import random
import statistics
import platform
import datetime
from typing import List, Tuple, Callable, Optional

try:
    import psutil
except ImportError:
    psutil = None

from .colors import Colors
from .utils import suppress_output, gc_disabled

class CodeComparer:
    """
    CodeComparer provides functionality to compare the execution speed of two Python code snippets.
    It supports deterministic benchmarking, statistical analysis, and exporting results.
    """

    DEFAULT_SETUP_CODE = """
import time
import random
"""
    DEFAULT_CODE_1 = """
sleep_duration = random.random() * 0.005
time.sleep(sleep_duration)
"""
    DEFAULT_CODE_2 = """
iterations = random.randint(50, 150)
result = 0
for i in range(iterations):
    result += i * random.random()
"""

    def __init__(self, file_path_1=None, file_path_2=None, setup_code=None):
        """
        Initialize the comparer, load code snippets, and prepare setup code.

        Args:
            file_path_1 (str|None): Path to first code file or None for default.
            file_path_2 (str|None): Path to second code file or None for default.
            setup_code (str|None): Optional setup code to prepend to each snippet.
        """
        print(Colors.blue(Colors.bold("Initializing CodeComparer...")))
        self.fixed_seed = 42
        self.setup_code = (
            f"import random\nrandom.seed({self.fixed_seed})\n"
            + (setup_code if setup_code is not None else self.DEFAULT_SETUP_CODE)
        )
        setup_display = self.setup_code.strip().split('\n')[0] + ('...' if '\n' in self.setup_code.strip() else '')
        print(f"Using Setup Code (starts with): {Colors.cyan(setup_display)}")

        self.code_1, self.source_1 = self._load_code_from_source(
            file_path_1, "Default Snippet 1", self.DEFAULT_CODE_1
        )
        print(f"Source for Code 1: {Colors.magenta(self.source_1)}")

        self.code_2, self.source_2 = self._load_code_from_source(
            file_path_2, "Default Snippet 2", self.DEFAULT_CODE_2
        )
        print(f"Source for Code 2: {Colors.magenta(self.source_2)}")

        self.measurements_1: List[float] = []
        self.measurements_2: List[float] = []
        self.stats_1 = {}
        self.stats_2 = {}

    def _read_file_content(self, file_path: str) -> Optional[str]:
        """
        Read and return the content of a file.

        Args:
            file_path (str): Path to the file.

        Returns:
            str|None: File content or None if error.
        """
        try:
            if not os.path.isfile(file_path):
                print(Colors.red(f"Error: File not found at '{file_path}'."))
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except (OSError, UnicodeDecodeError) as e:
            print(Colors.red(f"Error reading file '{file_path}': {e}"))
            return None

    def _load_code_from_source(self, file_path: Optional[str], default_source_name: str, default_code: str) -> Tuple[str, str]:
        """
        Load code from a file or use a default snippet.

        Args:
            file_path (str|None): Path to code file or None.
            default_source_name (str): Name for default code.
            default_code (str): Default code string.

        Returns:
            (str, str): Tuple of code and its source description.
        """
        if file_path:
            print(f"Attempting to load code from file: {Colors.underline(file_path)}")
            file_content = self._read_file_content(file_path)
            if file_content is not None:
                return file_content, f"File ('{os.path.basename(file_path)}')"
            print(Colors.yellow(f"Failed to load from '{file_path}'. Using default: {default_source_name}."))
            return default_code, f"{default_source_name} (Fallback)"
        return default_code, default_source_name

    def _ensure_outputs_dir(self) -> str:
        """
        Ensure the outputs directory exists.

        Returns:
            str: Absolute path to the outputs directory.
        """
        outputs_dir = os.path.join(os.getcwd(), "outputs")
        if not os.path.exists(outputs_dir):
            os.makedirs(outputs_dir)
        return outputs_dir

    def _warmup(self, code: str, setup_code: str, runs: int = 5):
        """
        Run warmup executions to stabilize timing.

        Args:
            code (str): Code to execute.
            setup_code (str): Setup code to run before.
            runs (int): Number of warmup runs.
        """
        for _ in range(runs):
            with suppress_output():
                exec(setup_code, {}, {})
                exec(code, {}, {})

    def _detailed_stats(self, data: List[float]) -> dict:
        """
        Compute detailed statistics for a list of timings.

        Args:
            data (List[float]): List of timing measurements.

        Returns:
            dict: Statistics including mean, stdev, percentiles, min, max, count.
        """
        percentiles = statistics.quantiles(data, n=100) if len(data) >= 20 else [None]*99
        return {
            "mean": statistics.mean(data),
            "stdev": statistics.stdev(data) if len(data) > 1 else 0,
            "median": statistics.median(data),
            "percentile_5": percentiles[4] if percentiles[4] else None,
            "percentile_95": percentiles[94] if percentiles[94] else None,
            "min": min(data),
            "max": max(data),
            "count": len(data)
        }

    def _system_load_info(self) -> dict:
        """
        Get current system load information.

        Returns:
            dict: CPU and memory usage info.
        """
        if psutil:
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "virtual_memory": dict(psutil.virtual_memory()._asdict())
            }
        return {"cpu_percent": None, "virtual_memory": None}

    def _env_info(self) -> dict:
        """
        Get Python and platform environment info.

        Returns:
            dict: Python version, platform, executable.
        """
        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "executable": sys.executable
        }

    def _confidence_interval(self, data: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calculate a confidence interval for the mean of the data.

        Args:
            data (List[float]): List of timing measurements.
            confidence (float): Confidence level (default 0.95).

        Returns:
            (float, float): Lower and upper bounds of the confidence interval.
        """
        if not data or len(data) < 2:
            return (0.0, 0.0)
        mean = statistics.mean(data)
        stdev = statistics.stdev(data)
        n = len(data)
        t = 1.96 if n > 30 else {
            2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 6: 2.57, 7: 2.45, 8: 2.36, 9: 2.31, 10: 2.26
        }.get(n, 2.0)
        margin = t * stdev / math.sqrt(n)
        return (mean - margin, mean + margin)

    def _reset_state(self):
        """
        Reset any internal state or cache between repetitions.
        (Currently a placeholder for future use.)
        """
        pass

    def _format_duration(self, seconds: float) -> str:
        """
        Format a duration in seconds into a human-readable string.

        Args:
            seconds (float): Duration in seconds.

        Returns:
            str: Formatted duration string.
        """
        if seconds >= 60:
            m = int(seconds // 60)
            s = seconds % 60
            return f"{m}m {s:.2f}s"
        elif seconds >= 1:
            return f"{seconds:.2f}s"
        elif seconds >= 1e-3:
            return f"{seconds*1e3:.2f}ms"
        elif seconds >= 1e-6:
            return f"{seconds*1e6:.2f}μs"
        else:
            return f"{seconds*1e9:.2f}ns"

    def _get_log_filename(self) -> str:
        """
        Generate a unique filename for the verbose log.

        Returns:
            str: Filename string.
        """
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"compare_log_{now}.json"

    def _time_single_snippet(
        self,
        snippet_name: str,
        code_to_time: str,
        setup_code: str,
        repeat: int,
        number: int,
        warmup_runs: int = 5,
        on_repeat_end: Optional[Callable[[int, float], None]] = None
    ) -> Tuple[float, float]:
        """
        Time the execution of a single code snippet.

        Args:
            snippet_name (str): Name for reporting.
            code_to_time (str): The code to time.
            setup_code (str): Setup code to run before timing.
            repeat (int): Number of repetitions.
            number (int): Number of executions per repetition.
            warmup_runs (int): Warmup runs before timing.
            on_repeat_end (callable): Optional callback after each repetition.

        Returns:
            (float, float): Mean and standard deviation of timings.
        """
        print(f"Timing {Colors.cyan(snippet_name)} ({Colors.yellow(str(repeat))} repetitions)...")
        times = []
        self._warmup(code_to_time, setup_code, runs=warmup_runs)
        try:
            with gc_disabled():
                for rep in range(repeat):
                    local_setup = setup_code + f"\nrandom.seed({self.fixed_seed + rep})"
                    self._reset_state()
                    start = time.perf_counter()
                    with suppress_output():
                        for _ in range(number):
                            exec(code_to_time, {}, {})
                    end = time.perf_counter()
                    elapsed = (end - start) / number if number > 0 else 0
                    times.append(elapsed)
                    if on_repeat_end:
                        on_repeat_end(rep, elapsed)
            if "1" in snippet_name:
                self.measurements_1 = times.copy()
            else:
                self.measurements_2 = times.copy()
            mean_time = statistics.mean(times)
            stdev_time = statistics.stdev(times) if len(times) > 1 else 0
            return mean_time, stdev_time
        except Exception as e:
            print(Colors.red(Colors.bold("\n--- ERROR during timing ---")))
            print(Colors.red(f"An error occurred while executing {snippet_name}:"))
            print(Colors.red(f"Error details: {e}"))
            print(Colors.yellow("Check setup code and snippet syntax/logic."))
            print(Colors.red(Colors.bold("---------------------------\n")))
            return None, None

    def compare_execution(
        self,
        num_repetitions: int = 20000,
        num_executions_per_rep: int = 3,
        warmup_runs: int = 5,
        on_repeat_end: Optional[Callable[[int, float], None]] = None,
        export_json: Optional[str] = None
    ):
        """
        Compare the execution of two code snippets and print/report results.

        Args:
            num_repetitions (int): Number of repetitions.
            num_executions_per_rep (int): Executions per repetition.
            warmup_runs (int): Warmup runs before timing.
            on_repeat_end (callable): Optional progress callback.
            export_json (str|None): Optional path to export JSON results.

        Returns:
            dict: Summary of relative performance, total test time, and log path.
        """
        print(Colors.bold("\n--- Starting Code Comparison ---"))
        print(f"Repetitions: {Colors.yellow(str(num_repetitions))}, Executions per repetition: {Colors.yellow(str(num_executions_per_rep))}")
        print(f"Warm-up runs: {Colors.yellow(str(warmup_runs))}")
        print(f"Random seed fixed for determinism: {Colors.yellow(str(self.fixed_seed))}")

        total_start = time.perf_counter()

        mean1, stdev1 = self._time_single_snippet(
            "Snippet 1", self.code_1, self.setup_code, num_repetitions, num_executions_per_rep, warmup_runs, on_repeat_end
        )
        mean2, stdev2 = self._time_single_snippet(
            "Snippet 2", self.code_2, self.setup_code, num_repetitions, num_executions_per_rep, warmup_runs, on_repeat_end
        )

        total_end = time.perf_counter()
        total_duration = total_end - total_start
        formatted_total_time = self._format_duration(total_duration)

        stats1 = self._detailed_stats(self.measurements_1)
        stats2 = self._detailed_stats(self.measurements_2)
        ci1 = self._confidence_interval(self.measurements_1)
        ci2 = self._confidence_interval(self.measurements_2)

        if stats1["mean"] < stats2["mean"]:
            faster = "Snippet 1"
            slower = "Snippet 2"
            ratio = stats2["mean"] / stats1["mean"] if stats1["mean"] > 0 else float('inf')
            percent = (1 - stats1["mean"] / stats2["mean"]) * 100 if stats2["mean"] > 0 else 0
        else:
            faster = "Snippet 2"
            slower = "Snippet 1"
            ratio = stats1["mean"] / stats2["mean"] if stats2["mean"] > 0 else float('inf')
            percent = (1 - stats2["mean"] / stats1["mean"]) * 100 if stats1["mean"] > 0 else 0

        if ratio == float('inf'):
            rel_msg = Colors.red("Relative speed: Not computable (division by zero).")
            rel_perf = {"times": "inf", "percentage": "N/A", "faster": faster, "slower": slower}
        else:
            rel_msg = (
                f"{Colors.bold(faster)} is {Colors.green(f'{ratio:.2f}x')} faster than {Colors.bold(slower)} "
                f"({Colors.green(f'{percent:.2f}%')} faster)."
            )
            rel_perf = {"times": f"{ratio:.2f}", "percentage": f"{percent:.2f}", "faster": faster, "slower": slower}

        print(Colors.bold("\n--- Results ---"))
        print(f"{Colors.cyan('Snippet 1')}: mean = {Colors.green(f'{stats1['mean']*1e6:.2f} μs')}, stdev = {Colors.yellow(f'{stats1['stdev']*1e6:.2f} μs')}, median = {Colors.green(f'{stats1['median']*1e6:.2f} μs')}")
        print(f"    95% CI: {Colors.yellow(f'{ci1[0]*1e6:.2f} μs')} - {Colors.yellow(f'{ci1[1]*1e6:.2f} μs')}")
        print(f"{Colors.cyan('Snippet 2')}: mean = {Colors.green(f'{stats2['mean']*1e6:.2f} μs')}, stdev = {Colors.yellow(f'{stats2['stdev']*1e6:.2f} μs')}, median = {Colors.green(f'{stats2['median']*1e6:.2f} μs')}")
        print(f"    95% CI: {Colors.yellow(f'{ci2[0]*1e6:.2f} μs')} - {Colors.yellow(f'{ci2[1]*1e6:.2f} μs')}")
        print(f"\n{Colors.bold('All individual measurements are logged for further analysis.')}")
        print(f"\n{Colors.bold('Recommendation:')} Run with higher repetitions for more stable results.")
        print(f"\n{rel_msg}")
        print(Colors.bold(f"\nTotal test time: {Colors.blue(formatted_total_time)}"))

        outputs_dir = self._ensure_outputs_dir()
        log_filename = self._get_log_filename()
        log_path = os.path.join(outputs_dir, log_filename)

        export_data = {
            "snippet_1": {
                "source": self.source_1,
                "code": self.code_1,
                "stats": stats1,
                "confidence_interval": ci1,
                "measurements": self.measurements_1
            },
            "snippet_2": {
                "source": self.source_2,
                "code": self.code_2,
                "stats": stats2,
                "confidence_interval": ci2,
                "measurements": self.measurements_2
            },
            "relative_performance": {
                "faster": faster,
                "slower": slower,
                "ratio": ratio,
                "percent_faster": percent
            },
            "env_info": self._env_info(),
            "system_load": self._system_load_info(),
            "parameters": {
                "num_repetitions": num_repetitions,
                "num_executions_per_rep": num_executions_per_rep,
                "warmup_runs": warmup_runs,
                "fixed_seed": self.fixed_seed
            },
            "total_test_time_seconds": total_duration,
            "total_test_time_human": formatted_total_time
        }

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)
        print(Colors.green(f"\nVerbose log written to outputs/{log_filename}"))

        if export_json:
            filename = export_json if os.path.isabs(export_json) else os.path.join(outputs_dir, export_json)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            print(Colors.green(f"\nExported detailed results to {filename}"))

        print(Colors.bold("\n--- Comparison Complete ---"))
        print(
            Colors.bold(
                Colors.reverse(
                    f" Winner: {faster} "
                )
            )
        )
        return {
            "relative_performance": rel_perf,
            "total_test_time": formatted_total_time,
            "log_path": f"outputs/{log_filename}"
        }
