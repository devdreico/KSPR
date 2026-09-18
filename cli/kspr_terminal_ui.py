class TerminalTheme:
    """Strict grayscale and monochrome ANSI theme for professional CLI UI."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    INVERSE = "\033[7m"
    
    WHITE = "\033[97m"         # Primary focus, active titles, prompt
    SILVER = "\033[37m"        # Normal readable text
    GRAPHITE = "\033[90m"      # Borders, dividers, metadata
    CHARCOAL = "\033[2m"       # Dim background accents


class TerminalUI:
    @staticmethod
    def print_colored(text: str, color: str = TerminalTheme.SILVER, bold: bool = False) -> None:
        prefix = TerminalTheme.BOLD if bold else ""
        print(f"{color}{prefix}{text}{TerminalTheme.RESET}")

    @staticmethod
    def get_width() -> int:
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80

    @staticmethod
    def print_box(title: str, lines: list[str]) -> None:
        width = min(max(len(title) + 6, max((len(l) for l in lines), default=40) + 4), TerminalUI.get_width() - 2)
        horizontal = "─" * (width - 2)
        
        print()
        TerminalUI.print_colored(f"┌─ {title} " + "─" * max(0, width - len(title) - 4) + "┐", TerminalTheme.WHITE, bold=True)
        for line in lines:
            padding = max(0, width - len(line) - 4)
            TerminalUI.print_colored(f"│  {line}" + " " * padding + "│", TerminalTheme.SILVER)
        TerminalUI.print_colored(f"└{horizontal}┘", TerminalTheme.GRAPHITE)
        print()

    @staticmethod
    def print_session_banner(session_id: str, provider: str, model: str, workspace: Path, attached_count: int, tokens_used: int, max_tokens: int) -> None:
        width = min(TerminalUI.get_width() - 2, 90)
        horizontal = "─" * (width - 2)
        
        pct = int((tokens_used / max_tokens) * 100) if max_tokens > 0 else 0
        filled = int((pct / 100) * 14)
        bar = "█" * filled + "░" * (14 - filled)
        
        ws_str = str(workspace)
        if len(ws_str) > 30:
            ws_str = "..." + ws_str[-27:]

        print()
        TerminalUI.print_colored(f"┌─ KSPR I  │  sess: {session_id}  │  {provider}:{model}  " + "─" * max(0, width - len(session_id) - len(provider) - len(model) - 34) + "┐", TerminalTheme.GRAPHITE)
        TerminalUI.print_colored(f"│  ctx: [{bar}] {tokens_used // 1000}k/{max_tokens // 1000}k ({pct}%)  │  dir: {ws_str:<24}  │  files: {attached_count:<2}  │", TerminalTheme.SILVER)
        TerminalUI.print_colored(f"└─ tips: [@] attach   [/] commands   [/decompilate] context tree   [^C] exit " + "─" * max(0, width - 73) + "┘", TerminalTheme.GRAPHITE)
        print()

    @staticmethod
    async def animate_spinner(task_coro, message: str) -> tuple[Any, float]:
        spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0
        start_time = time.time()
        
        task = asyncio.create_task(task_coro)
        
        sys.stdout.write("\033[?25l")
        try:
            while not task.done():
                elapsed = time.time() - start_time
                sys.stdout.write(f"\r{TerminalTheme.WHITE}{spinners[idx]} {message} {TerminalTheme.GRAPHITE}[ {elapsed:.1f}s ]{TerminalTheme.RESET}")
                sys.stdout.flush()
                idx = (idx + 1) % len(spinners)
                await asyncio.sleep(0.08)
            sys.stdout.write("\r\033[K")
            elapsed = time.time() - start_time
            return await task, elapsed
        finally:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    @staticmethod
    def print_tool_step(fn_name: str, args: dict, result: str, duration_ms: float) -> None:
        args_str = json.dumps(args, ensure_ascii=False)
        if len(args_str) > 60:
            args_str = args_str[:57] + "..."
        trunc_res = str(result).replace("\n", " ").strip()
        if len(trunc_res) > 80:
            trunc_res = trunc_res[:77] + "..."

        TerminalUI.print_colored(f"  ● Tool Call: {fn_name}", TerminalTheme.WHITE)
        TerminalUI.print_colored(f"    ├─ args: {args_str}", TerminalTheme.GRAPHITE)
        TerminalUI.print_colored(f"    └─ result: [OK] · {duration_ms:.0f}ms · {trunc_res}", TerminalTheme.SILVER)

    @staticmethod
    def print_response(title: str, text: str | list[str], latency: float = 0.0) -> None:
        if isinstance(text, list):
            lines = text
        else:
            lines = text.splitlines()
            if not lines:
                lines = [text]
        width = min(max(len(title) + 16, max((len(l) for l in lines), default=40) + 4), TerminalUI.get_width() - 2)
        horizontal = "─" * (width - 2)
        
        lat_str = f" │ {latency:.2f}s " if latency > 0 else ""
        
        print()
        TerminalUI.print_colored(f"┌── {title}{lat_str}" + "─" * max(0, width - len(title) - len(lat_str) - 3) + "┐", TerminalTheme.WHITE, bold=True)
        for line in lines:
            while len(line) > width - 4:
                chunk = line[:width - 4]
                line = line[width - 4:]
                TerminalUI.print_colored(f"│  {chunk}  │", TerminalTheme.SILVER)
            padding = max(0, width - len(line) - 4)
            TerminalUI.print_colored(f"│  {line}" + " " * padding + "│", TerminalTheme.SILVER)
        TerminalUI.print_colored(f"└{horizontal}┘", TerminalTheme.WHITE)
        print()
