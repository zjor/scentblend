# Spikes

A spike is a time-boxed piece of research. Each spike keeps all its files in one folder, so nothing is scattered across the repo.

## Layout

```
spikes/<name>/
  README.md   # goal, questions, method, findings
  scripts/    # code for this spike
  data/       # raw inputs        (ignored by Git)
  reports/    # generated outputs (ignored by Git)
  .env        # credentials       (ignored by Git; see .env.example)
```

## Rules

- `README.md` is in Git. Write only aggregate findings there: no names, email addresses or message contents.
- Personal and raw data lives only in `data/` and `reports/`.
- When a spike becomes regular work, move its scripts to `scripts/` and its doc to the right business area.

## Spikes

| Spike | Status | Started |
| --- | --- | --- |
| [Cooperation mailbox analysis](cooperation-mail-analysis/README.md) | open | 2026-11-17 |
