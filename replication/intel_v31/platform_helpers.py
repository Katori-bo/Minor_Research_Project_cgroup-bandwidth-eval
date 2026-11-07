"""Read-only Intel topology and temperature helpers."""
from pathlib import Path


def topology():
    return {str(i): dict(core=(Path(f'/sys/devices/system/cpu/cpu{i}/topology/core_id').read_text().strip()),
                        package=(Path(f'/sys/devices/system/cpu/cpu{i}/topology/physical_package_id').read_text().strip()),
                        siblings=(Path(f'/sys/devices/system/cpu/cpu{i}/topology/thread_siblings_list').read_text().strip()))
            for i in range(8)}


def check_topology():
    result = topology()
    key = lambda i: (result[str(i)]['package'], result[str(i)]['core'])
    if key(2) == key(3) or {key(0), key(1)} & {key(2), key(3)} or key(0) == key(1):
        raise RuntimeError('host02 server/control physical cores overlap')
    expected = {'0': '0,4', '1': '1,5', '2': '2,6', '3': '3,7',
                '4': '0,4', '5': '1,5', '6': '2,6', '7': '3,7'}
    if {i: row['siblings'] for i, row in result.items()} != expected:
        raise RuntimeError('host02 topology differs from the supplied Intel host inventory')
    return result


def temperatures():
    values = {}
    for hw in sorted(Path('/sys/class/hwmon').glob('hwmon*')):
        try:
            if (hw / 'name').read_text().strip() != 'coretemp':
                continue
            for sensor in sorted(hw.glob('temp*_input')):
                label = sensor.with_name(sensor.name.replace('_input', '_label'))
                name = label.read_text().strip() if label.exists() else sensor.stem
                # hwmon enumeration index is retained to distinguish duplicate sensors.
                values[f'coretemp:{hw.name}:{name}'] = int(sensor.read_text()) / 1000
        except OSError:
            continue
    if not values:
        raise RuntimeError('No readable Intel coretemp sensors; preserve output for apparatus review')
    return values
