#!/usr/bin/env python3
"""Software-only monitor process: real cadence and signals, synthetic reads."""
import sys
import time
import types
import v27r3_monitor as monitor


def main():
    interval, overhead = map(float, sys.argv[1:3])
    sys.argv = [sys.argv[0], '--interval', str(interval), *sys.argv[3:]]
    monitor.get_cpu_times = lambda: {'cpu': [1, 1, 1, 100, 0, 0, 0, 0]}
    monitor.process_snapshot = lambda: {}
    monitor.get_temperatures = lambda: {}
    monitor.get_frequencies = lambda: {}
    monitor.power_settings = lambda: {}
    def process_read(*args, **kwargs):
        time.sleep(overhead)
        return types.SimpleNamespace(stdout='software fixture: no host process read\n')
    monitor.subprocess.run = process_read
    monitor.main()


if __name__ == '__main__':
    main()
