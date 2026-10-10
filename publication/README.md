# GitHub research snapshot — 10 October 2026

Repository: [Katori-bo/Minor_Research_Project_cgroup-bandwidth-eval](https://github.com/Katori-bo/Minor_Research_Project_cgroup-bandwidth-eval).
Branch: `main`. Snapshot tag: `research-snapshot-2026-10-10`.
Full evidence: [snapshot release](https://github.com/Katori-bo/Minor_Research_Project_cgroup-bandwidth-eval/releases/tag/research-snapshot-2026-10-10).

The Git repository contains the current source code, manuscript sources,
figures, protocols, reports, and smaller saved observations. Large records and
downloaded software trees are preserved in release archives at their original
relative paths. A clone alone is therefore insufficient for the full offline
evidence checks. The snapshot manifest lists every original tracked or
previously untracked, non-ignored file, its identity, and its archive group.
Local virtual environments, Python bytecode, locks, and build folders that were
already ignored are not part of the snapshot. No experiment was rerun.

The `evidence` archive contains large saved research records and compiled
research artifacts. The `software` archive contains downloaded toolchains,
dependencies, and audited upstream source snapshots, with their existing
licenses. Identical files are represented by tar hardlinks to reduce download
size. Each zstd-compressed archive is split into ordered parts of at most
512 MiB. The parts are pieces of one compressed stream, not independent tar
files. `SHA256SUMS` and `snapshot-manifest.json` identify the exact parts.

## Read the completed research

- [Capacity-calibration empirical manuscript](../paper/capacity_calibration_empirical.md).
- [Deadline-resolution extension](../paper/deadline_resolution_extension.md).
- [Capacity-calibration reproduction guide](../paper/capacity_calibration_reproducibility.md).
- [Deadline-resolution reproduction guide](../paper/deadline_resolution_reproducibility.md).

The scientific limitations and historical unsuccessful candidates remain
preserved. This is an artifact snapshot, not a journal submission. Author and
venue fields remain as they were. No new license is assigned to the original
research by this upload.

## Clone and restore all saved evidence

Requirements: Git, Python 3.8 or newer, GNU tar, and zstd. Allow at least 40 GiB
of free disk space for the clone, compressed downloads, and expanded evidence.
GitHub authentication is unnecessary for public downloads.

```bash
git clone https://github.com/Katori-bo/Minor_Research_Project_cgroup-bandwidth-eval.git
cd Minor_Research_Project_cgroup-bandwidth-eval
git checkout research-snapshot-2026-10-10
python3 -B publication/restore_snapshot.py
python3 -B analysis/verify_empirical_paper.py
python3 -B analysis/verify_deadline_extension_revision.py
```

The restore tool downloads the release parts, checks their SHA256 identities,
extracts both groups into a fresh clone, and checks every original file. It
refuses to overwrite a partially populated archive group. Downloads are saved
under the ignored directory `publication/downloads/`; `--assets-dir PATH`
selects another location. `--download-only` verifies downloads without
extraction. To check an already restored snapshot without network access:

```bash
python3 -B publication/restore_snapshot.py --verify
```

The saved software contains historical executable artifacts for identity and
reproducibility. The manuscript verification commands perform offline checks.
Follow each reproduction guide for additional dependencies or stronger replay
commands; do not invoke workload launchers to reproduce saved findings.

## Future source updates from the original working folder

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
git status
git add -A
git diff --cached --stat
git commit -m "Describe the research update"
git push origin main
```

Review the staged changes before committing. Large snapshot paths are ignored
because their original bytes are attached to this release. New large datasets
should receive a new snapshot release and checksum manifest. Keep this dated
release intact so its tag, inventory and evidence remain reproducible.
