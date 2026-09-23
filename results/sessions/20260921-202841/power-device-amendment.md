# Power-device enumeration amendment

Authorized by the user after a reboot prevented resumption at 93 completed matrix trials.

The original environment record is preserved byte-for-byte in `environment.before-usbc-amendment.json`. The only change to `environment.json` is the addition of `ucsi-source-psy-USBC000:001: "0"` to `power_settings.external_power`. This USB-C power-supply entry was absent from the original record and is currently offline. The original `ACAD: "1"` requirement remains in force.

Read-only checks before this amendment found that all recorded CPU policies, frequency bounds, platform profile, and AC state matched the proposed expectation. The user confirmed `powerprofilesctl get` returned `balanced` in their normal terminal. Codex's restricted environment could not read that desktop profile; the saved `desktop_profile: "balanced"` requirement is retained for the runner to verify.

This is an explicit amendment to the expected device inventory, not evidence that every aspect of the environment is identical across the reboot. Preserve the interruption boundary for analysis. Historical trial records continue to describe the inventory observed at their measurement time.

No experiment code, source hashes, temperature baseline or thresholds, workload, matrix order, or completed trial records were changed. The runner still compares power settings exactly and will reject a changed AC state, an active USB-C entry, or another inventory/settings mismatch. The experiment was not restarted as part of this amendment.
