import argparse

from .colors import Colors
from .comparer import CodeComparer

TECHY_ASCII_ART = r"""
   ╔══════════╗     ╔══════════╗
   ║          ║     ║          ║
   ║   ░░░░   ║ <-> ║   ████   ║
   ║   ░░░░   ║ <-> ║   ████   ║
   ║          ║     ║          ║
   ╚══════════╝     ╚══════════╝
"""

SUMMARY_TABLE = """
Recommended repetitions for microbenchmarking:

+---------------+------------------------+--------------------+
| Code Duration | Recommended Repetitions| Executions per Rep |
+---------------+------------------------+--------------------+
|   < 10 μs     |   50,000 – 100,000     |      5 – 10        |
|  10–100 μs    |   10,000 – 50,000      |      3 – 10        |
|  0.1–1 ms     |   5,000 – 10,000       |      3 – 5         |
|   > 1 ms      |   1,000 – 5,000        |      1 – 3         |
+---------------+------------------------+--------------------+
"""

class CodeCompareCLI:
    def run(self):
        parser = argparse.ArgumentParser(
            description=(
                f"{Colors.bold('Compare the execution speed of two Python code snippets.')}\n"
                f"Uses default variable-time snippets if no files are provided.\n"
                f"Results are saved in the 'outputs' folder if exported.\n\n"
                f"{SUMMARY_TABLE}"
            ),
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument(
            "-f1", "--file1", type=str, default=None,
            help="Path to the first Python code file.\n(Uses Default Snippet 1 if omitted)"
        )
        parser.add_argument(
            "-f2", "--file2", type=str, default=None,
            help="Path to the second Python code file.\n(Uses Default Snippet 2 if omitted)"
        )
        parser.add_argument(
            "-r", "--reps", type=int, default=20000, metavar='N',
            help="Number of repetitions for timing each snippet (default: 20000)."
        )
        parser.add_argument(
            "-n", "--num", type=int, default=3, metavar='N',
            help="Number of times to execute snippet within each repetition (default: 3)."
        )
        parser.add_argument(
            "--setup", type=str, default=None, metavar='FILE',
            help="Path to a file containing custom setup code (e.g., imports).\n(Overrides default setup)"
        )
        parser.add_argument(
            "--no-color", action="store_true",
            help="Disable colored terminal output."
        )
        parser.add_argument(
            "--warmup", type=int, default=5, metavar='N',
            help="Number of warm-up runs before timing (default: 5)."
        )
        parser.add_argument(
            "--export-json", type=str, default=None, metavar='FILE',
            help="Export detailed results and statistics to a JSON file."
        )

        args = parser.parse_args()

        print(Colors.cyan(TECHY_ASCII_ART))

        if args.no_color:
            Colors.disable()
            print("Color output disabled.")

        custom_setup_code = None
        if args.setup:
            print(f"Attempting to load custom setup code from: {Colors.underline(args.setup)}")
            try:
                temp_comparer = CodeComparer()
                custom_setup_code = temp_comparer._read_file_content(args.setup)
                if custom_setup_code is not None:
                    print(Colors.green("Successfully loaded custom setup code."))
                else:
                    print(Colors.yellow("Falling back to default setup code."))
            except Exception as e:
                print(Colors.red(f"Unexpected error loading setup file '{args.setup}': {e}"))
                print(Colors.yellow("Falling back to default setup code."))

        try:
            comparer = CodeComparer(
                file_path_1=args.file1,
                file_path_2=args.file2,
                setup_code=custom_setup_code
            )

            def progress_callback(rep, elapsed):
                Colors.progress_bar(rep + 1, args.reps, prefix="Progress:", suffix=f"{rep + 1}/{args.reps}")

            results = comparer.compare_execution(
                num_repetitions=args.reps,
                num_executions_per_rep=args.num,
                warmup_runs=args.warmup,
                on_repeat_end=progress_callback,
                export_json=args.export_json
            )

            if results:
                rel_perf = results['relative_performance']
                print(Colors.bold(f"\nRelative Performance: {rel_perf['times']}x ({rel_perf['percentage']}%)"))

        except Exception as e:
            print(Colors.red(Colors.bold("\n--- UNEXPECTED ERROR ---")))
            print(Colors.red(f"An unexpected error occurred during execution: {e}"))
            print(Colors.red("Please check arguments and file contents."))
