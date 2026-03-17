"""
ModernTensor CLI — Cyberpunk UI Components
═══════════════════════════════════════════

Rich-based terminal UI with a unified "Tensor Cyberpunk" theme.
Every print helper, banner, table, and log line flows through this module
so the entire CLI + subnet runtime looks visually cohesive.
"""

from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple, Union

from rich.box import HEAVY_HEAD, MINIMAL, ROUNDED
from rich.columns import Columns
from rich.console import Console
from rich.align import Align
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# ═══════════════════════════════════════════════════════════
# Theme
# ═══════════════════════════════════════════════════════════

theme = Theme(
    {
        # Brand palette
        "brand": "#F23F5D",           # Neon Crimson
        "brand.bold": "bold #F23F5D",
        "accent": "#B24BF3",          # Electric Purple
        "accent.bold": "bold #B24BF3",

        # Semantic colours
        "success": "#00FF9D",         # Matrix Green
        "warning": "#FFD600",         # Cyber Yellow
        "error": "#FF003C",           # Reactor Red
        "info": "#00E5FF",            # Holo Blue

        # Data presentation
        "key": "bold #00E5FF",
        "value": "#E0E0E0",
        "dim": "#6C7086",             # Timestamps, borders
        "muted": "#4C4F69",           # Deep Space

        # Table / header helpers
        "header": "bold #F23F5D",
        "col.cyan": "bold #00E5FF",
        "col.green": "bold #00FF9D",
        "col.yellow": "bold #FFD600",
        "col.magenta": "bold #B24BF3",
        "col.blue": "bold #5B7FFF",
        "col.white": "bold #E0E0E0",
    }
)

console = Console(theme=theme, highlight=False)


# ═══════════════════════════════════════════════════════════
# Basic message helpers
# ═══════════════════════════════════════════════════════════

def print_success(message: str):
    """Prints a success message."""
    console.print(f"[success]✅ {message}[/success]")


def print_error(message: str, exit_code: int = 0):
    """Prints an error message. Does not exit by default."""
    console.print(f"[error]❌ {message}[/error]")


def print_info(message: str):
    """Prints an info message."""
    console.print(f"[info]ℹ  {message}[/info]")


def print_warning(message: str):
    """Prints a warning message."""
    console.print(f"[warning]⚠  {message}[/warning]")


def print_kv(key: str, value: str):
    """Prints a Key-Value pair aligned."""
    console.print(f" [key]{key:<15}[/key] [value]{value}[/value]")


# ═══════════════════════════════════════════════════════════
# Tables
# ═══════════════════════════════════════════════════════════

ColumnSpec = Union[str, Tuple[str, str]]
"""Either a plain column name or (name, style_key)."""


def create_table(
    title: Optional[str] = None,
    columns: Optional[Sequence[ColumnSpec]] = None,
) -> Table:
    """Creates a standardised themed table.

    *columns* may be plain strings (``"Name"``) or
    ``(name, style)`` tuples (``("Stake", "green")``).
    """
    table = Table(
        box=HEAVY_HEAD,
        header_style="brand.bold",
        border_style="dim",
        show_lines=False,
        padding=(0, 1),
    )
    if title:
        table.title = f"[brand]{title}[/brand]"

    if columns:
        for col in columns:
            if isinstance(col, (list, tuple)):
                name, style = col[0], col[1]
                table.add_column(name, style=style)
            else:
                table.add_column(col)

    return table


def print_table(
    columns: Sequence[ColumnSpec],
    rows: Sequence[Sequence[str]],
    title: Optional[str] = None,
):
    """Prints a standardised table with data."""
    table = create_table(title, columns)
    for row in rows:
        table.add_row(*row)
    console.print(table)


# ═══════════════════════════════════════════════════════════
# Panels
# ═══════════════════════════════════════════════════════════

def print_panel(
    message: str,
    title: str = "Alert",
    style: str = "brand",
    border_style: Optional[str] = None,
):
    """Prints a prominent panel."""
    bs = border_style or style
    console.print(
        Panel(message, title=f"[{style}]{title}[/{style}]", border_style=bs)
    )


# ═══════════════════════════════════════════════════════════
# Spinner
# ═══════════════════════════════════════════════════════════

def spinner(message: str):
    """Returns a spinner context manager."""
    return console.status(f"[bold cyan]{message}...", spinner="dots")


# ═══════════════════════════════════════════════════════════
# Confirmation
# ═══════════════════════════════════════════════════════════

def confirm_action(message: str) -> bool:
    """Prompts for user confirmation."""
    from rich.prompt import Confirm
    return Confirm.ask(f"[bold brand]{message}[/]")


# ═══════════════════════════════════════════════════════════
# CLI Header (mtcli entrypoint)
# ═══════════════════════════════════════════════════════════

def print_header(version: str, network: str = "mainnet"):
    """Prints the Tensor-Style ASCII Header."""
    ascii_art = r"""
 █▀▄▀█ █▀█ █▀▄ █▀▀ █▀█ █▄ █ ▀█▀ █▀▀ █▄ █ █▀▀ █▀█ █▀█
 █ ▀ █ █ █ █ █ ██▄ █▀▄ █ ▀█  █  ██▄ █ ▀█ ▄█▄ █ █ █▀▄
 ▀   ▀ ▀▀▀ ▀▀  ▀▀▀ ▀ ▀ ▀  ▀  ▀  ▀▀▀ ▀  ▀ ▀▀▀ ▀▀▀ ▀ ▀
"""
    console.print(Text(ascii_art, style="brand"))

    # Status Bar
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row(
        Text(f" CLI v{version}", style="muted"),
        Text(f"Network: {network} ● ", style="success"),
    )
    console.print(grid)
    console.print(Rule(style="dim"))
    console.print()


# ═══════════════════════════════════════════════════════════
# Runtime banner (miner / validator startup)
# ═══════════════════════════════════════════════════════════

def print_banner(
    title: str,
    subtitle: str,
    details: Dict[str, str],
    *,
    border_style: str = "brand",
    icon: str = "⬡",
):
    """Render a premium Rich Panel used as the startup banner.

    Parameters
    ----------
    title:
        e.g. ``"ModernTensor MINER 1"``
    subtitle:
        One-line tagline, e.g. ``"Polkadot Hub Testnet — Continuous Mining Loop"``
    details:
        Key-value pairs rendered inside the panel.
    """
    lines: List[str] = [f"[dim]{subtitle}[/dim]\n"]
    for k, v in details.items():
        lines.append(f"  [key]{k + ':':<18}[/key] [value]{v}[/value]")

    body = "\n".join(lines)
    panel = Panel(
        body,
        title=f"[bold]{icon}  {title}[/bold]",
        title_align="left",
        border_style=border_style,
        padding=(1, 2),
        expand=True,
    )
    console.print()
    console.print(panel)


# ═══════════════════════════════════════════════════════════
# Runtime status box  (miner / validator periodic status)
# ═══════════════════════════════════════════════════════════

def print_status_box(
    title: str,
    rows: Sequence[Tuple[str, str]],
    *,
    border_style: str = "info",
):
    """Compact status box rendered as a slim Rich Panel.

    Parameters
    ----------
    title:
        e.g. ``"Miner 1 Status (UID=0)"``
    rows:
        Sequence of ``(label, value)`` tuples.
    """
    table = Table(
        box=None,
        show_header=False,
        padding=(0, 2),
        expand=True,
    )
    table.add_column("Label", style="key", min_width=20)
    table.add_column("Value", style="value")

    for label, value in rows:
        table.add_row(label, value)

    panel = Panel(
        table,
        title=f"[bold]{title}[/bold]",
        title_align="left",
        border_style=border_style,
        padding=(0, 1),
    )
    console.print()
    console.print(panel)


# ═══════════════════════════════════════════════════════════
# Runtime log line  (replaces plain print in base.py)
# ═══════════════════════════════════════════════════════════

def print_log(emoji: str, msg: str, **kw: object):
    """Themed timestamped log line.

    Example output::

        [14:02:33] 📥 TASK RECEIVED  (task_id=abc123 | total=5)
    """
    ts = datetime.now().strftime("%H:%M:%S")
    extra = " [dim]|[/dim] ".join(
        f"[key]{k}[/key]=[value]{v}[/value]" for k, v in kw.items()
    )
    ts_str = f"[dim]\\[{ts}][/dim]"
    msg_str = f"[value]{msg}[/value]"
    tail = f"  [dim]([/dim]{extra}[dim])[/dim]" if extra else ""
    console.print(f"  {ts_str} {emoji} {msg_str}{tail}")


# ═══════════════════════════════════════════════════════════
# Metagraph table  (replaces manual box-drawing in base.py)
# ═══════════════════════════════════════════════════════════

def print_metagraph_table(
    nodes,
    total_stake: str,
    n_miners: int,
    n_validators: int,
    title: str = "Metagraph",
    block: Optional[int] = None,
):
    """Render the full subnet metagraph as a Rich Table.

    Parameters
    ----------
    nodes:
        Iterable of objects with ``.uid``, ``.is_validator``, ``.active``,
        ``.total_stake_ether``, ``.trust_float``, ``.rank_float``,
        ``.emission_ether``.
    """
    full_title = title
    if block is not None:
        full_title += f" @ block {block}"

    table = create_table(
        full_title,
        [
            ("UID", "col.cyan"),
            ("Type", "col.blue"),
            ("Stake", "col.green"),
            ("Trust", "col.yellow"),
            ("Rank", "col.magenta"),
            ("Emission", "col.white"),
        ],
    )

    for node in nodes:
        if not node.active:
            continue
        ntype = "VALIDATOR" if node.is_validator else "MINER"
        emoji_n = "🔷" if node.is_validator else "⛏️"
        table.add_row(
            f"{emoji_n} {node.uid}",
            ntype,
            f"{node.total_stake_ether:.2f}",
            f"{node.trust_float:.4f}",
            f"{node.rank_float:.6f}",
            f"{node.emission_ether:.6f}",
        )

    console.print()
    console.print(table)
    console.print(
        f"  [dim]Total Stake:[/dim] [success]{total_stake} MDT[/success]  "
        f"[dim]│[/dim]  [dim]Miners:[/dim] [info]{n_miners}[/info]  "
        f"[dim]│[/dim]  [dim]Validators:[/dim] [accent]{n_validators}[/accent]"
    )
    console.print()


# ═══════════════════════════════════════════════════════════
# Epoch / section divider
# ═══════════════════════════════════════════════════════════

def print_divider(label: str = "", style: str = "brand"):
    """Print a horizontal rule with an optional centre label."""
    console.print()
    if label:
        console.print(Rule(f"[bold]{label}[/bold]", style=style))
    else:
        console.print(Rule(style=style))


# ═══════════════════════════════════════════════════════════
# AI model list  (used in miner banner)
# ═══════════════════════════════════════════════════════════

def print_model_list(models: Dict[str, dict]):
    """Render loaded AI models as a mini table."""
    table = Table(
        box=None,
        show_header=False,
        padding=(0, 1),
    )
    table.add_column("Domain", style="accent", min_width=10, justify="right")
    table.add_column("Model", style="value")
    table.add_column("Params", style="dim")

    for domain, model in models.items():
        table.add_row(domain, model["name"], f"({model['params']})")

    console.print(
        Panel(
            table,
            title="[bold]🧠  AI Models Loaded[/bold]",
            title_align="left",
            border_style="accent",
            padding=(0, 1),
        )
    )
