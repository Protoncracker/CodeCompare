class Colors:
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    ORANGE = '\033[38;5;208m'
    GRAY = '\033[90m'
    BRIGHT_BLUE = '\033[38;5;39m'
    BRIGHT_CYAN = '\033[38;5;51m'
    BRIGHT_MAGENTA = '\033[38;5;207m'
    BRIGHT_GREEN = '\033[38;5;82m'
    BRIGHT_YELLOW = '\033[38;5;226m'

    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'
    BG_BLUE = '\033[104m'
    BG_MAGENTA = '\033[105m'
    BG_CYAN = '\033[106m'
    BG_WHITE = '\033[107m'

    # Styles
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    REVERSE = '\033[7m'
    ENDC = '\033[0m'
    enabled = True

    @staticmethod
    def disable():
        Colors.enabled = False
        for attr in dir(Colors):
            val = getattr(Colors, attr)
            if isinstance(val, str) and val.startswith('\033'):
                setattr(Colors, attr, '')

    @staticmethod
    def _colorize(code, text):
        return f"{code}{text}{Colors.ENDC}" if Colors.enabled else text

    red = staticmethod(lambda t: Colors._colorize(Colors.RED, t))
    green = staticmethod(lambda t: Colors._colorize(Colors.BRIGHT_GREEN, t))
    yellow = staticmethod(lambda t: Colors._colorize(Colors.BRIGHT_YELLOW, t))
    blue = staticmethod(lambda t: Colors._colorize(Colors.BRIGHT_BLUE, t))
    magenta = staticmethod(lambda t: Colors._colorize(Colors.BRIGHT_MAGENTA, t))
    cyan = staticmethod(lambda t: Colors._colorize(Colors.BRIGHT_CYAN, t))
    white = staticmethod(lambda t: Colors._colorize(Colors.WHITE, t))
    orange = staticmethod(lambda t: Colors._colorize(Colors.ORANGE, t))
    gray = staticmethod(lambda t: Colors._colorize(Colors.GRAY, t))
    bold = staticmethod(lambda t: Colors._colorize(Colors.BOLD, t))
    underline = staticmethod(lambda t: Colors._colorize(Colors.UNDERLINE, t))
    reverse = staticmethod(lambda t: Colors._colorize(Colors.REVERSE, t))

    @staticmethod
    def progress_bar(current, total, bar_length=32, prefix='', suffix=''):
        percent = float(current) / total if total else 0
        filled_length = int(bar_length * percent)
        bar = Colors.green('█' * filled_length) + Colors.gray('░' * (bar_length - filled_length))
        percent_str = Colors.cyan(f"{percent*100:6.2f}%")
        print(f"\r{prefix}[{bar}] {percent_str} {suffix}", end='', flush=True)
        if current == total:
            print()
