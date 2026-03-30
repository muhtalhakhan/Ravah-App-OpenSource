"""
Ravah CLI — turn what you ship into a week of social content.

Usage (after pip install):
    ravah             # generate posts (default)
    ravah health      # check config
    ravah reset       # clear saved profile and last session
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ── App ───────────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="ravah",
    help="Turn what you ship into a week of social content.",
    no_args_is_help=False,
    invoke_without_command=True,
)
console = Console()

PROFILE_PATH      = Path.home() / ".ravah" / "profile.json"
LAST_SESSION_PATH = Path.home() / ".ravah" / "last_session.json"

_PLATFORM_LABELS = {"x": "X (Twitter)", "instagram": "Instagram", "linkedin": "LinkedIn"}

_CONTENT_TYPES = {
    "1": ("personal",           "Myself — personal brand"),
    "2": ("brand",              "A brand or product"),
    "3": ("building_in_public", "Building in public — sharing my founder journey"),
}

_STYLE_CHOICES = {
    "1": ("educational",        "Educational"),
    "2": ("storytelling",       "Storytelling"),
    "3": ("motivational",       "Motivational"),
    "4": ("behind_the_scenes",  "Behind the scenes"),
    "5": ("mixed",              "Mixed"),
}

_TONE_PRESETS = {
    "1": "Casual & friendly",
    "2": "Professional & authoritative",
    "3": "Conversational",
    "4": "Bold & direct",
    "5": "Witty & playful",
}


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _save_last_session(summary: str, platforms: list, style: str,
                       tone: str, audience: str, keywords: str, avoid: str) -> None:
    _save(LAST_SESSION_PATH, {
        "summary":      summary,
        "platforms":    platforms,
        "style":        style,
        "tone":         tone,
        "audience":     audience,
        "keywords":     keywords,
        "avoid":        avoid,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    })


# ── Menu helper ───────────────────────────────────────────────────────────────

def _pick(question: str, choices: dict[str, tuple | str]) -> str:
    console.print(f"\n[bold cyan]{question}[/bold cyan]")
    for key, val in choices.items():
        label = val[1] if isinstance(val, tuple) else val
        console.print(f"  [{key}] {label}")
    while True:
        raw = typer.prompt("").strip()
        if raw in choices:
            return raw
        console.print(f"[red]Enter one of: {', '.join(choices.keys())}[/red]")


# ── Post panel renderer ───────────────────────────────────────────────────────

def _show_post(post) -> None:
    pname = _PLATFORM_LABELS.get(post.platform, post.platform)
    cv = post.clearv

    body = Text()
    body.append("C  ", style="bold yellow")
    body.append(cv.capture + "\n\n")
    body.append("L  ", style="bold green")
    body.append(cv.lead + "\n\n")
    body.append("E  ", style="bold blue")
    body.append(cv.educate + "\n\n")
    body.append("A  ", style="bold magenta")
    body.append(cv.activate + "\n\n")
    body.append("R  ", style="bold red")
    body.append(cv.resonate + "\n\n")
    body.append("V  ", style="bold white")
    body.append(cv.visual + "\n\n")
    body.append("── post ──\n", style="dim")
    body.append(post.full_post + "\n\n")
    body.append(f"{' '.join(post.hashtags)}  •  {post.char_count} chars", style="dim")

    console.print(Panel(body, title=f"[bold]Day {post.day} — {pname}[/bold]", border_style="cyan"))


# ── `generate` ────────────────────────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        generate()


@app.command()
def generate():
    """Interactive post generator — answer a few questions, get a full content calendar."""
    from ravah.config import settings

    console.rule("[bold cyan]Ravah[/bold cyan]")
    console.print("[dim]Turn what you ship into a week of social content.[/dim]\n")

    profile      = _load(PROFILE_PATH)
    last_session = _load(LAST_SESSION_PATH)
    first_run    = not profile.get("name")

    # ── API key (once, saved to profile) ─────────────────────────────────────
    api_key = profile.get("google_api_key") or settings.GOOGLE_API_KEY
    if not api_key or api_key == "your-google-ai-api-key-here":
        console.print("[bold cyan]Paste your Google AI API key[/bold cyan]")
        console.print("[dim]Get one free at https://aistudio.google.com/app/apikey[/dim]")
        api_key = typer.prompt("API key", hide_input=True).strip()
        profile["google_api_key"] = api_key

    # ── Name (once) ───────────────────────────────────────────────────────────
    if not profile.get("name"):
        console.print()
        profile["name"] = typer.prompt("What's your name?").strip()

    name = profile["name"]

    # ── Content type (once) ───────────────────────────────────────────────────
    if not profile.get("content_type"):
        type_key = _pick("Are you creating content for:", _CONTENT_TYPES)
        profile["content_type"] = _CONTENT_TYPES[type_key][0]

    content_type = profile["content_type"]
    content_type_label = next(v[1] for v in _CONTENT_TYPES.values() if v[0] == content_type)

    _save(PROFILE_PATH, profile)

    if first_run:
        console.print(f"\n[green]Profile saved.[/green] Won't ask again.\n")
    else:
        console.print(f"Welcome back, [bold]{name}[/bold] · {content_type_label}\n")

    # ── New vs continue ───────────────────────────────────────────────────────
    use_last = False
    if last_session.get("summary"):
        short        = last_session["summary"]
        short        = short[:60] + "…" if len(short) > 60 else short
        generated_at = last_session.get("generated_at", "")[:10]

        console.print(f"[dim]Last session ({generated_at}):[/dim] {short}\n")

        choice = _pick(
            "Pick up where you left off or start fresh?",
            {
                "1": "Start fresh — I'm working on something new",
                "2": "Carry on — keep going with the old content",
            },
        )
        use_last = choice == "2"

    # ── Content questions ─────────────────────────────────────────────────────
    if use_last:
        summary     = last_session["summary"]
        platforms   = last_session["platforms"]
        style       = last_session["style"]
        tone        = last_session["tone"]
        audience    = last_session["audience"]
        keywords    = last_session.get("keywords", "")
        avoid       = last_session.get("avoid", "")
        style_label = next(
            (v[1] for v in _STYLE_CHOICES.values() if v[0] == style), style
        )
        console.print(
            f"\n[dim]Using:[/dim] {summary[:80]}"
            f"\n[dim]Style:[/dim] {style_label}  [dim]Tone:[/dim] {tone}"
            f"\n[dim]Audience:[/dim] {audience}\n"
        )
        days_key = _pick("How many days of content?", {"1": "7 days", "2": "18 days", "3": "30 days"})
        num_days = {"1": 7, "2": 18, "3": 30}[days_key]

    else:
        console.print("\n[bold cyan]What are you building, shipping, or working on?[/bold cyan]")
        console.print("[dim]Be specific — the more detail, the better the posts.[/dim]")
        summary = typer.prompt("").strip()
        while len(summary) < 15:
            console.print("[red]Add a bit more detail.[/red]")
            summary = typer.prompt("").strip()

        days_key = _pick("How many days of content?", {"1": "7 days", "2": "18 days", "3": "30 days"})
        num_days = {"1": 7, "2": 18, "3": 30}[days_key]

        console.print("\n[bold cyan]Which platforms?[/bold cyan]  [dim](Enter to use all three)[/dim]")
        console.print("  Options: [bold]x[/bold], [bold]instagram[/bold], [bold]linkedin[/bold]")
        raw_p = typer.prompt("", default="x,instagram,linkedin").strip().lower()
        platforms = [p.strip() for p in raw_p.split(",") if p.strip() in _PLATFORM_LABELS]
        if not platforms:
            platforms = ["x", "instagram", "linkedin"]

        style_key   = _pick("Content style:", _STYLE_CHOICES)
        style       = _STYLE_CHOICES[style_key][0]
        style_label = _STYLE_CHOICES[style_key][1]

        tone_key = _pick("Tone:", {**_TONE_PRESETS, "6": "Custom — I'll type it"})
        tone = typer.prompt("Describe your tone").strip() if tone_key == "6" else _TONE_PRESETS[tone_key]

        console.print("\n[bold cyan]Who is your audience?[/bold cyan]  [dim](e.g. early-stage founders)[/dim]")
        audience = typer.prompt("").strip() or "early adopters and founders"

        console.print("\n[bold cyan]Keywords or hashtags to always include?[/bold cyan]  [dim](optional)[/dim]")
        keywords = typer.prompt("", default="").strip()

        console.print("\n[bold cyan]Anything to avoid?[/bold cyan]  [dim](optional)[/dim]")
        avoid = typer.prompt("", default="").strip()

    # ── Confirm ───────────────────────────────────────────────────────────────
    console.print()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="dim cyan")
    t.add_column()
    t.add_row("Name",      name)
    t.add_row("Type",      content_type_label)
    t.add_row("Days",      str(num_days))
    t.add_row("Platforms", ", ".join(_PLATFORM_LABELS[p] for p in platforms))
    t.add_row("Style",     style_label)
    t.add_row("Tone",      tone)
    t.add_row("Audience",  audience)
    if keywords:
        t.add_row("Keywords", keywords)
    if avoid:
        t.add_row("Avoid", avoid)
    console.print(t)
    console.print()

    total = num_days * len(platforms)
    if not typer.confirm(f"Generate {total} posts?", default=True):
        raise typer.Exit(0)

    # ── Call Gemini ───────────────────────────────────────────────────────────
    from ravah.gemini_service import GenerationContext, generate_posts, render_markdown

    ctx = GenerationContext(
        name=name,
        content_type=content_type,
        summary=summary,
        num_days=num_days,
        platforms=platforms,
        style=style,
        tone=tone,
        audience=audience,
        keywords=keywords,
        avoid=avoid,
    )

    console.print()
    with console.status(f"[bold green]Writing {total} posts with Gemini…[/bold green]", spinner="dots"):
        try:
            posts = generate_posts(ctx, api_key=api_key, model=settings.GOOGLE_AI_MODEL)
        except Exception as exc:
            console.print(f"\n[red]Error:[/red] {exc}")
            raise typer.Exit(1)

    # ── Save last session ─────────────────────────────────────────────────────
    _save_last_session(summary, platforms, style, tone, audience, keywords, avoid)

    # ── Save MD — written to ./output/ in the current working directory ───────
    output_dir = Path.cwd() / "output"
    output_dir.mkdir(exist_ok=True)
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = output_dir / f"posts_{ts}_{num_days}d.md"
    md_path.write_text(render_markdown(posts, ctx), encoding="utf-8")

    # ── Display ───────────────────────────────────────────────────────────────
    console.print(f"\n[green]Got {len(posts)} posts.[/green]\n")
    console.rule("[bold cyan]Your Content[/bold cyan]")

    days: dict[int, list] = {}
    for post in posts:
        days.setdefault(post.day, []).append(post)

    for day_num in sorted(days.keys()):
        console.print(f"\n[bold white on blue]  Day {day_num}  [/bold white on blue]\n")
        for post in days[day_num]:
            _show_post(post)

    console.rule()
    console.print(f"\n[green]Done![/green] Saved to [bold]{md_path}[/bold]\n")


# ── Utility commands ──────────────────────────────────────────────────────────

@app.command()
def health():
    """Show config, saved profile, and last session info."""
    from ravah.config import settings

    profile      = _load(PROFILE_PATH)
    last_session = _load(LAST_SESSION_PATH)

    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="dim cyan")
    t.add_column()
    t.add_row("Model",   settings.GOOGLE_AI_MODEL)
    t.add_row("API key", "set" if (profile.get("google_api_key") or settings.GOOGLE_API_KEY) else "[red]not set[/red]")
    t.add_row("Name",    profile.get("name", "[dim]none[/dim]"))
    t.add_row("Type",    profile.get("content_type", "[dim]none[/dim]"))

    if last_session.get("summary"):
        short = last_session["summary"]
        short = short[:60] + ("…" if len(short) > 60 else "")
        t.add_row("Last session", f"{last_session.get('generated_at', '')[:10]}  {short}")

    console.print(t)


@app.command()
def reset():
    """Clear saved profile and last session — start completely fresh."""
    removed = []
    for path, label in [(PROFILE_PATH, "profile"), (LAST_SESSION_PATH, "last session")]:
        if path.exists():
            path.unlink()
            removed.append(label)
    if removed:
        console.print(f"[green]Cleared:[/green] {', '.join(removed)}. Next run starts fresh.")
    else:
        console.print("[dim]Nothing to clear.[/dim]")


def main():
    app()


if __name__ == "__main__":
    main()
