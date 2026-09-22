#!/usr/bin/env bash
set -euo pipefail

METADATA_DIR="/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/metadata"
mkdir -p "$METADATA_DIR"
OUTFILE="$METADATA_DIR/system-info.txt"

echo "=== SYSTEM & HARDWARE INVENTORY ===" > "$OUTFILE"
echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$OUTFILE"
echo "" >> "$OUTFILE"

echo "=== UNAME ===" >> "$OUTFILE"
uname -a >> "$OUTFILE"
echo "" >> "$OUTFILE"

echo "=== OS RELEASE ===" >> "$OUTFILE"
cat /etc/os-release >> "$OUTFILE"
echo "" >> "$OUTFILE"

echo "=== LSCPU FULL ===" >> "$OUTFILE"
lscpu >> "$OUTFILE"
echo "" >> "$OUTFILE"

echo "=== LSCPU TOPOLOGY (CPU, CORE, SOCKET, NODE, ONLINE) ===" >> "$OUTFILE"
lscpu -e=CPU,CORE,SOCKET,NODE,ONLINE >> "$OUTFILE"
echo "" >> "$OUTFILE"

echo "=== MEMORY (free -h) ===" >> "$OUTFILE"
free -h >> "$OUTFILE"
echo "" >> "$OUTFILE"

echo "=== CGROUP V2 STATUS ===" >> "$OUTFILE"
echo -n "/sys/fs/cgroup filesystem type: " >> "$OUTFILE"
stat -fc %T /sys/fs/cgroup >> "$OUTFILE"
echo "Root cgroup controllers:" >> "$OUTFILE"
cat /sys/fs/cgroup/cgroup.controllers >> "$OUTFILE"
echo "Root cgroup subtree_control:" >> "$OUTFILE"
cat /sys/fs/cgroup/cgroup.subtree_control >> "$OUTFILE"
echo "system.slice cpu.max:" >> "$OUTFILE"
cat /sys/fs/cgroup/system.slice/cpu.max >> "$OUTFILE"
echo "system.slice cpu.max.burst:" >> "$OUTFILE"
cat /sys/fs/cgroup/system.slice/cpu.max.burst >> "$OUTFILE"
echo "" >> "$OUTFILE"

echo "=== DOCKER VERSION ===" >> "$OUTFILE"
docker version >> "$OUTFILE"
echo "" >> "$OUTFILE"

echo "=== DOCKER INFO ===" >> "$OUTFILE"
docker info >> "$OUTFILE"
echo "" >> "$OUTFILE"

echo "=== CPU FREQUENCY & GOVERNOR ===" >> "$OUTFILE"
for p in /sys/devices/system/cpu/cpufreq/policy*; do
    policy_name=$(basename "$p")
    gov=$(cat "$p/scaling_governor" 2>/dev/null || echo "N/A")
    driver=$(cat "$p/scaling_driver" 2>/dev/null || echo "N/A")
    epp=$(cat "$p/energy_performance_preference" 2>/dev/null || echo "N/A")
    cur_freq=$(cat "$p/scaling_cur_freq" 2>/dev/null || echo "N/A")
    echo "$policy_name: driver=$driver governor=$gov epp=$epp cur_freq_khz=$cur_freq" >> "$OUTFILE"
done
echo "" >> "$OUTFILE"

echo "=== THERMAL ZONES ===" >> "$OUTFILE"
for z in /sys/class/thermal/thermal_zone*; do
    z_name=$(basename "$z")
    temp=$(cat "$z/temp" 2>/dev/null || echo "N/A")
    type=$(cat "$z/type" 2>/dev/null || echo "N/A")
    echo "$z_name ($type): temp_mC=$temp" >> "$OUTFILE"
done
echo "" >> "$OUTFILE"

echo "Environment recorded successfully to $OUTFILE"
