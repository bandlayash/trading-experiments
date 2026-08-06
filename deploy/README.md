# Execution options

> **Nothing in this directory trades. Nothing in this directory runs.**
>
> This repo is a research home. The strategies in `strategies/` are backtested and
> compared; none of them is wired to a broker, and the owner has not decided to run any
> of them with real money. Everything here is **pseudocode and commented templates** —
> `runner_pseudocode.py` exits immediately if you execute it, and the workflow file
> carries a `.example` extension specifically so GitHub will not schedule it.
>
> No file in this repo contains, reads, or asks for API credentials. If you adapt this
> for live use, that is your decision and your risk; start by reading
> [What any live deployment needs](#what-any-live-deployment-needs) below, because the
> hosting choice is the easy part.

---

## Contents

- [The shape of the problem](#the-shape-of-the-problem)
- [Comparison](#comparison)
- [Local (cron / Task Scheduler)](#local-cron--task-scheduler)
- [GitHub Actions](#github-actions)
- [AWS Lambda + EventBridge](#aws-lambda--eventbridge)
- [A small always-on VM](#a-small-always-on-vm)
- [Broker-native and managed platforms](#broker-native-and-managed-platforms)
- [What any live deployment needs](#what-any-live-deployment-needs)
- [Files here](#files-here)

---

## The shape of the problem

All three strategies in this repo decide on **daily bars**. That single fact removes most
of the difficulty people associate with running a trading bot:

- **Latency is irrelevant.** A signal computed from daily closes does not care whether
  your code starts in 40 ms or 40 seconds. Cold starts, interpreter startup, and network
  round-trips are all noise against a decision that is only meaningful once a day.
- **Throughput is irrelevant.** One instrument, one decision, a few hundred bars of data.
  Every option below is enormously oversized for the compute involved.
- **Reliability is what actually matters**, and it is mostly about *missing* runs. If the
  scheduler silently skips a day, you hold a position the strategy wanted to exit.

So the choice is not about performance. It is about how much operational burden you are
willing to own, and how confident you need to be that the thing actually fired.

One consequence worth internalising early: for a daily-bar strategy, a run that is late is
usually fine, and a run that never happens is not. Evaluate the options below on whether
you would *find out* about a missed run, not on how fast they execute.

---

## Comparison

| Option | Cost | Reliability | Ops burden | Credentials live in | Best when |
|---|---|---|---|---|---|
| Local cron / Task Scheduler | None | Poor — dies with sleep, reboots, travel, ISP | Low to set up, high to trust | A local file or OS keychain | You are iterating, testing, or paper-trading and will notice failures yourself |
| GitHub Actions | Free tier covers this comfortably for a public repo | Good *only* with an external pinger; the native scheduler drops ticks | Low | Repo Secrets | You want zero infrastructure and can tolerate best-effort timing |
| AWS Lambda + EventBridge | Free tier covers this comfortably at daily-bar volume | Very good — EventBridge fires reliably | Medium — IAM, packaging, a pandas/numpy layer | Secrets Manager / SSM Parameter Store | You want managed reliability and are comfortable with AWS |
| Small always-on VM | Low, a few dollars a month | Good — you own it, including its failures | Highest — OS patching, disk, monitoring | A file on the box, ideally root-owned | You want one obvious mental model and full control |
| Broker-native / managed platform | Varies; often free to run | Very good — it is their core product | Lowest | The platform | You want to stop thinking about infrastructure entirely and accept lock-in |

Read the "Reliability" column as *how likely the run is to happen at all*, not how fast it
is when it does.

---

## Local (cron / Task Scheduler)

The cheapest possible answer: a Python script on a machine you already own, fired on a
schedule by the OS.

**macOS / Linux** — `crontab -e`, then something like:

```cron
# 15:45 America/New_York, weekdays. Note cron uses the machine's local timezone,
# so either set the machine to ET or do the offset arithmetic yourself — and redo it
# twice a year when DST shifts. This is a genuine, recurring source of missed runs.
45 15 * * 1-5 cd /path/to/trading-experiments && /path/to/.venv/bin/python deploy/runner_pseudocode.py >> run.log 2>&1
```

**Windows** — Task Scheduler, "Create Task" (not "Basic Task", which hides the options you
need). Point the action at your venv's `python.exe` with the script as an argument, set
"Start in" to the repo root, and enable **Run whether user is logged on or not** plus
**Run task as soon as possible after a scheduled start is missed**. Without that second
option a sleeping laptop simply skips the day with no trace.

**Trade-offs.**

- *For*: no accounts, no deploys, no cloud bill, and the fastest possible edit-run loop.
  For research iteration and paper trading this is genuinely the right answer.
- *Against*: it fails in ways you do not see. Laptop asleep, machine rebooted for updates,
  hotel Wi-Fi, dead battery — each is a silently skipped decision. Cron writes to a log
  nobody reads; a task that never fires produces no log at all.
- *Verdict*: fine for iterating and for paper trading. Do not put money behind a laptop
  unless you have external alerting that shouts when a run is missed (see below).

---

## GitHub Actions

Runs your code on GitHub's runners, triggered by a workflow file in `.github/workflows/`.
For a **public** repo the free tier covers a daily job comfortably. See
[`github_actions.example.yml`](github_actions.example.yml) in this directory for a
commented template.

**The caveat that matters.** GitHub's native `schedule:` (cron) trigger is explicitly
**best-effort**. Two documented behaviours bite trading use:

1. The finest granularity is **5 minutes**. You cannot ask for tighter.
2. Scheduled workflows are **delayed or dropped entirely** when the platform is under
   load. Delays of tens of minutes are common, and runs can be skipped outright with no
   notification. Scheduled jobs also queue against a shared pool, and there is no
   guarantee of execution at the requested minute.

For a daily-bar strategy a *delay* is survivable. A *dropped* run is not — it means the
day's exit never happened.

The standard workaround is to stop relying on GitHub's scheduler and drive the workflow
externally: expose a `workflow_dispatch` trigger and have a dedicated cron service (for
example **cron-job.org**, which is free, supports per-job timezones, and handles DST
automatically) hit the
[workflow-dispatch REST endpoint](https://docs.github.com/en/rest/actions/workflows)
on schedule. The external service becomes the source of truth for timing; GitHub becomes
the execution environment. Most such services will also email you when a ping fails,
which gives you the missed-run alerting the native scheduler does not.

**Credentials.** API keys go in **Settings → Secrets and variables → Actions → Secrets**,
referenced as `${{ secrets.NAME }}`. They are never in the repo. Two things to understand
before trusting this:

- Secrets are masked in logs, but masking is a string filter, not a security boundary.
  Anything your code prints in a *transformed* form (base64, JSON-escaped, sliced) will
  not be masked.
- On a **public** repo, workflow logs are world-readable. Assume anything you log is
  published.

Use repo **Variables** (not Secrets) for non-sensitive config, including a kill switch —
a variable like `LIVE_ENABLED` that every job checks first lets you halt trading from the
GitHub UI in seconds, with no commit and no deploy.

**Trade-offs.**

- *For*: no infrastructure at all, free for public repos, deploys are just `git push`,
  and the run history and logs are already a usable audit trail.
- *Against*: timing is not yours to control without an external pinger; public logs demand
  discipline about what you print; and you are subject to platform-wide incidents you
  cannot see coming or route around.
- *Verdict*: a good default for a small daily-bar strategy, **provided** you drive it
  externally rather than trusting `schedule:`.

---

## AWS Lambda + EventBridge

The classic serverless route: your handler in Lambda, an EventBridge (formerly CloudWatch
Events) rule firing it on a cron expression.

**Why it fits.** At one invocation a day, of a few seconds each, the free tier covers this
comfortably — Lambda's perpetual free tier is denominated in *millions* of requests. Cold
starts are the usual objection to Lambda and are **completely irrelevant here**: an extra
second or two of initialisation means nothing to a decision made on daily closes.
EventBridge, unlike GitHub's scheduler, is a real scheduling service with delivery
guarantees and retry behaviour.

**The one real friction: dependencies.** `pandas` and `numpy` are large binary wheels and
do not fit the inline editor workflow. Options, roughly in order of preference:

1. **AWS's managed SciPy layer** — AWS publishes a layer containing numpy and scipy.
   Check current availability for your region and Python runtime; the set of managed
   layers changes over time.
2. **Your own layer** — build the wheels on a manylinux base image (or in a container
   matching the Lambda runtime) and publish them as a layer. This is the reliable path.
   Build on the *same* architecture you deploy to; wheels built on Apple Silicon will not
   load on an x86_64 Lambda.
3. **Container image deployment** — Lambda supports container images up to a much larger
   size limit than zip packages. If you are already comfortable with Docker this is the
   least fiddly option and sidesteps layer size limits entirely.

**Credentials.** Use **Secrets Manager** or **SSM Parameter Store** (SecureString) and
grant the function's execution role read access to exactly those parameters. Do not put
keys in Lambda environment variables — they are visible to anyone with console read
access to the function, and they show up in `GetFunctionConfiguration` output.

**Trade-offs.**

- *For*: genuinely reliable scheduling, effectively free at this volume, no servers to
  patch, and CloudWatch Logs plus alarms give you monitoring without extra tooling.
- *Against*: the most moving parts of any option here — IAM roles, layers, packaging,
  region choice, log retention. The first deploy takes real time. Iteration is slower
  than local or Actions.
- *Verdict*: the right answer if you want managed reliability and already know AWS. If
  you do not, the learning curve is steeper than the strategy warrants.

---

## A small always-on VM

A cheap Linux box — EC2, Lightsail, Fly.io, Hetzner, DigitalOcean — running the same cron
job you would run locally, but on a machine that never sleeps. A few dollars a month at
the smallest instance sizes; some providers have free tiers that cover this.

**Trade-offs.**

- *For*: the simplest mental model of any option. It is just a computer that is always on.
  Everything you know about running scripts applies unchanged. Debugging is `ssh` and
  reading a log file. No packaging, no layers, no platform quirks. Persistent local state
  (a SQLite file of positions and fills, say) is trivial, where it is awkward everywhere
  else.
- *Against*: you own the entire stack. OS patching, disk filling up with logs, the process
  dying and not restarting, the provider's maintenance reboots, and the certificate that
  expires while you are on holiday. "Always-on" is a claim you are now responsible for
  making true. Use `systemd` timers rather than `cron` so a failed run is at least visible
  in `journalctl`, and set up something external that notices the box has gone quiet.
- *Verdict*: excellent if you want one obvious model and are willing to do sysadmin work.
  The ongoing burden is real but small, and it is the option that punishes neglect most
  gradually — which is exactly why it catches people out.

---

## Broker-native and managed platforms

Instead of hosting code that calls a broker, run inside a platform that owns both.

- **QuantConnect** — write the strategy against their engine (LEAN); they handle data,
  backtesting, and live deployment on their infrastructure. Backtest and live use the same
  code path, which eliminates an entire category of bug. LEAN is open source, so
  self-hosting is a real escape hatch, but the data and deployment convenience is theirs.
- **Alpaca** — a broker with a first-class REST API and paper-trading environment. You
  still host your own code, but the API surface is simple enough that the hosting question
  shrinks. Paper and live use the same interface with a different base URL, which makes
  validation straightforward.
- **Interactive Brokers** — the deepest instrument coverage and the most demanding API.
  Historically requires a running TWS or IB Gateway session that your code connects to,
  which means you are effectively back to running a VM, plus a session that needs periodic
  re-authentication. Powerful, and more operational work than it first appears.

**Trade-offs.**

- *For*: the least infrastructure of anything here. Some platforms remove the
  backtest-vs-live divergence problem entirely by construction, which is worth more than
  it sounds.
- *Against*: lock-in. Your strategy becomes expressed in their framework, their data, and
  their execution model. Migrating later means a rewrite. You inherit their outages and
  their roadmap.
- *Verdict*: strongest choice if you want to stop thinking about infrastructure and are
  happy to commit to one ecosystem. Weakest if the research itself — the thing this repo
  is for — is the point, since portability is what you give up.

---

## What any live deployment needs

The hosting decision is the easy part. These properties are what separate a bot that runs
from a bot you can trust, and **none of them are implemented in this repo**. They apply
regardless of which option above you pick.

### Idempotency

A re-run must not double-trade. Schedulers retry. You will re-run a job manually to check
something. A network timeout will make you unsure whether an order landed. If the same
invocation twice produces two positions, you have built a way to lose money by pressing a
button twice.

The robust pattern is to make the code **converge on a target state** rather than issue
deltas: compute the position the strategy wants, ask the broker what you actually hold,
and trade only the difference. Run it ten times and nine are no-ops. Client-side order IDs
(most brokers support an idempotency key) close the remaining window where you cannot tell
whether a submission succeeded.

### Reconciliation

Never assume the broker's state matches your intent. Orders get rejected for insufficient
buying power, partially fill, get cancelled at the close, or fail on a halted symbol. An
order that was *accepted* is not an order that *filled* — this distinction has surprised
everyone who has built one of these.

Every run should read actual positions from the broker and treat that as truth. If the
actual position disagrees with what the strategy believes it should hold, that is either
something to correct or something to alert on — but it must never be silently ignored.

### Structured logging

Log one machine-readable record per run — JSON lines, one object per event — capturing at
minimum: timestamp, the signal inputs (the actual channel bounds, moving averages, or
whatever the strategy computed), the decision, the position before and after, and any
order IDs. When a trade looks wrong three weeks later, this log is the only way to answer
"what did it see?" Reconstructing it after the fact from price history is guesswork,
because you will not know exactly which bars the code had at the time.

Log the *inputs to the decision*, not just the decision. A log line saying `action: buy`
is nearly useless; one saying `close=241.30 upper=239.80 aroon_up=100 → breakout=true` lets
you verify the logic without rerunning anything.

### A kill switch

One flag, checked at the very top of every run, that stops all trading — no code change,
no deploy, no commit. A repo Variable, an SSM parameter, an env var, a file on disk;
the mechanism does not matter, the *reflex* does. You want stopping to be something you
can do from your phone in under a minute, because the moment you need it is the moment
you least want to be editing code.

Consider a second, automatic form: a circuit breaker that halts on conditions that should
never occur — equity down more than X% in a day, more than N orders in a session, a
position size that does not match any target the strategy could produce. Automatic halts
catch the failure modes that happen faster than you can react to them.

### Alerting

Silence must not read as success. The specific failure a daily-bar strategy needs to catch
is the run that **did not happen** — and by construction, a run that did not happen sends
no error.

Two complementary mechanisms:

- **Push on action** — notify when a trade is placed, an order is rejected, or an
  exception is raised. Email, a webhook, an issue in a repo, whatever you actually read.
- **Dead-man's switch** — a heartbeat the run pings on every successful completion,
  monitored by something that alerts when the ping *stops* arriving. This is the only
  mechanism that catches total failure of the host, the scheduler, or the network.

---

## Files here

| File | What it is |
|---|---|
| `README.md` | This document. |
| `runner_pseudocode.py` | Non-runnable sketch of a live runner. Exits immediately if executed. Shows the intended shape, including reconciliation against actual broker state. |
| `github_actions.example.yml` | Commented example workflow. The `.example` extension is deliberate — GitHub only runs `.yml`/`.yaml` files inside `.github/workflows/`, so this file is inert where it sits. |

To adapt the workflow you would copy it to `.github/workflows/`, rename it to `.yml`, and
replace the placeholder runner with real code. **Do not do this with live credentials
until the runner actually implements everything in
[What any live deployment needs](#what-any-live-deployment-needs).**
