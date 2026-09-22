#!/usr/bin/env python3
import os
import sys
import glob
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

def load_results(directory):
    records = []
    files = glob.glob(os.path.join(directory, "*.json"))
    for f in sorted(files):
        try:
            with open(f, 'r') as fp:
                d = json.load(fp)
            cfg = d.get('config', {})
            cg = d.get('cgroup_metrics', {})
            lg = d.get('loadgen_metrics', {})
            env = d.get('environment_metrics', {})

            s_lat = lg.get('service_latency_summary', {})
            e_lat = lg.get('end_to_end_latency_summary', {})
            d_lag = lg.get('dispatch_lag_summary', {})

            row = {
                "run_id": d.get("run_id"),
                "trial": d.get("trial", 1),
                "period_us": cfg.get("period_us"),
                "period_ms": cfg.get("period_us", 0) / 1000.0,
                "quota_us": cfg.get("quota_us"),
                "is_unlimited": cfg.get("is_unlimited", False),
                "workers": cfg.get("workers"),
                "pattern": cfg.get("pattern"),
                "target_rate": cfg.get("rate"),
                "achieved_rps": lg.get("achieved_throughput_rps"),
                "total_scheduled": lg.get("total_scheduled"),
                "total_completed": lg.get("total_completed"),
                "total_success": lg.get("total_success"),
                "total_503": lg.get("total_503"),
                "total_errors": lg.get("total_errors"),
                "client_dropped": lg.get("client_dropped"),
                "missed_arrivals": lg.get("missed_arrivals"),
                # Latencies
                "e2e_p50": e_lat.get("p50_ms"),
                "e2e_p95": e_lat.get("p95_ms"),
                "e2e_p99": e_lat.get("p99_ms"),
                "e2e_max": e_lat.get("max_ms"),
                "service_p50": s_lat.get("p50_ms"),
                "service_p95": s_lat.get("p95_ms"),
                "service_p99": s_lat.get("p99_ms"),
                "service_max": s_lat.get("max_ms"),
                "dispatch_lag_mean": d_lag.get("mean_ms"),
                "dispatch_lag_p99": d_lag.get("p99_ms"),
                # Cgroup
                "delta_usage_usec": cg.get("delta_usage_usec"),
                "delta_nr_periods": cg.get("delta_nr_periods"),
                "delta_nr_throttled": cg.get("delta_nr_throttled"),
                "delta_throttled_usec": cg.get("delta_throttled_usec"),
                "throttling_pct": cg.get("throttling_fraction", 0.0) * 100.0,
                "cpu_usage_cores": cg.get("cpu_usage_cores"),
                # Environment
                "mean_temp_c": env.get("mean_temp_c"),
                "max_temp_c": env.get("max_temp_c"),
                "core01_util": env.get("mean_util_core01_pct"),
                "core24_util": env.get("mean_util_core24_pct")
            }
            records.append(row)
        except Exception as e:
            print(f"Warning: could not parse {f}: {e}")

    return pd.DataFrame(records)

def plot_figures(df, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    if df.empty:
        print("No data to plot.")
        return

    # Categorical period label
    df['period_label'] = df.apply(
        lambda r: "Unlimited" if r['is_unlimited'] else f"{int(r['period_ms'])}ms", axis=1
    )

    # 1. Tail Latency (p95, p99) vs Configuration
    plt.figure(figsize=(9, 5))
    plot_df = df.sort_values(by=["period_ms", "workers", "pattern"])
    
    palette = sns.color_palette("muted")
    ax = sns.barplot(
        data=plot_df,
        x="period_label",
        y="e2e_p99",
        hue="pattern",
        palette=["#4C72B0", "#DD8452"]
    )
    plt.title("p99 End-to-End Latency vs Quota Period and Traffic Pattern", fontsize=14, pad=12)
    plt.xlabel("cgroup v2 cpu.max Period (0.5 CPU Quota)", fontsize=12)
    plt.ylabel("p99 Latency (ms)", fontsize=12)
    plt.tight_layout()
    f1 = os.path.join(output_dir, "fig1_tail_latency_vs_period.png")
    plt.savefig(f1, dpi=300)
    plt.close()
    print(f"Generated {f1}")

    # 2. Throttling Percent vs Quota Period
    plt.figure(figsize=(9, 5))
    ax = sns.barplot(
        data=plot_df,
        x="period_label",
        y="throttling_pct",
        hue="workers",
        palette="viridis"
    )
    plt.title("CFS Bandwidth Throttling Rate (%) vs Period Length and Workers", fontsize=14, pad=12)
    plt.xlabel("cgroup v2 cpu.max Period", fontsize=12)
    plt.ylabel("Throttled Periods (%)", fontsize=12)
    plt.tight_layout()
    f2 = os.path.join(output_dir, "fig2_throttling_vs_period.png")
    plt.savefig(f2, dpi=300)
    plt.close()
    print(f"Generated {f2}")

    # 3. Worker Concurrency Impact on p50 vs p99
    plt.figure(figsize=(9, 5))
    melted = plot_df.melt(
        id_vars=["run_id", "period_label", "workers", "pattern"],
        value_vars=["e2e_p50", "e2e_p95", "e2e_p99"],
        var_name="percentile",
        value_name="latency_ms"
    )
    melted["percentile"] = melted["percentile"].str.replace("e2e_", "").str.upper()
    sns.catplot(
        data=melted,
        x="workers",
        y="latency_ms",
        hue="percentile",
        col="pattern",
        kind="bar",
        height=4.5,
        aspect=1.2,
        palette="Blues"
    )
    plt.subplots_adjust(top=0.85)
    plt.suptitle("Latency Percentiles (p50, p95, p99) by Worker Pool Concurrency", fontsize=13)
    f3 = os.path.join(output_dir, "fig3_worker_concurrency.png")
    plt.savefig(f3, dpi=300)
    plt.close()
    print(f"Generated {f3}")

def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/results/pilot"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/analysis/figures"
    summary_csv = sys.argv[3] if len(sys.argv) > 3 else "/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/results/processed/summary.csv"

    os.makedirs(os.path.dirname(summary_csv), exist_ok=True)
    df = load_results(data_dir)
    print(f"Loaded {len(df)} records from {data_dir}")

    if not df.empty:
        df.to_csv(summary_csv, index=False)
        print(f"Saved aggregated summary to {summary_csv}")

        # Display summary table
        cols_to_show = ["run_id", "period_label" if "period_label" in df else "period_ms", "workers", "pattern", "achieved_rps", "e2e_p50", "e2e_p99", "throttling_pct", "cpu_usage_cores", "mean_temp_c"]
        avail_cols = [c for c in cols_to_show if c in df.columns]
        print("\n=== SUMMARY TABLE ===")
        print(df[avail_cols].to_string(index=False))

        plot_figures(df, output_dir)

if __name__ == "__main__":
    main()

