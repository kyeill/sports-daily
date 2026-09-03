# Working on Sports Daily

Read `README.md` first. It carries the whole design and, more usefully, a
**Traps** section recording each thing that already cost a debugging pass.
Do not rediscover them.

## Orientation

A daily page of the games worth watching across ten sports, built by GitHub
Actions each morning and published to <https://kyeill.github.io/sports-daily/>.
Nothing runs locally; there is no scheduled task and no server.

```
python site.py            build the 15-day app into output/site/
python sports_daily.py    one day, to output/today.html (--text, --date, --check)
python showcase.py        one real game from all 36 competitions, for review
python styles.py          colour and font comparisons
```

Python is not on PATH:
`C:\Users\kyleh\AppData\Local\Programs\Python\Python312-arm64\python.exe`

**No pandas or numpy.** Windows Smart App Control blocks numpy's ARM64 binaries
on this machine. Standard library plus `requests`, and `openpyxl` only for the
optional sheet template.

## If you are Claude and this folder is your working directory

Kyle's project notes live in the memory for the **parent** directory,
`C:\Users\kyleh\My Drive\Documents\Claude`. Opening a session here instead
means none of that loads, and you are working from the README alone. There is a
copy of those notes in `..\memory-backup\` -- read it before making decisions
about filter rules, because it records *why* things are the way they are.

Two of his standing preferences, since they are easy to miss:

* End every reply with a clearly marked section of outstanding **questions**,
  plus any **key notes** and **action items**. Buried asks get lost.
* **Anything he must paste, SHIP THE CODE WITH THE ASK.** Never write
  "redeploy the script" on its own -- a redeploy publishes whatever is already
  in the editor, so without the code nothing changes. Attach the whole file when
  it has moved a lot; give the exact before/after block when it is small, which
  also avoids a paste wiping his credentials.
* Verify claims by running things. Much of what is in the Traps list came from
  code that looked obviously correct.

## The shape of the thing

`config.json` is the source of truth for teams and rules -- no database, and no
Google Sheet for them (that was built, then deliberately abandoned; the
`control_sheet` block is switched off and should stay that way).

**One narrow exception, added 2026-08-30 at his request:** team COLOURS are read
from the `Colors` tab of his sheet, because the same overrides are needed by
standings and k-money and had already drifted apart between them -- Tottenham
was ffffff here and 132257 there. That is `colors_sheet`, deliberately separate
from `control_sheet` so enabling one cannot enable the other, and
`team_colors` in config.json remains the committed fallback. Do not read this
as the sheet coming back for teams and rules. `filters.py` decides
what is kept and which of the three buckets it lands in; `render.py` draws it;
`espn.py` is the only thing that talks to the network.

Run `python sports_daily.py --check` after editing any team name: matching is
substring, so "Michigan" also means Michigan State.
