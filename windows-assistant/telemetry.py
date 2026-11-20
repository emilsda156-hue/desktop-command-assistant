"""Real measurements only. Missing hardware providers are explicitly unavailable."""
import json
import os
import platform
import shutil
import socket
import subprocess
import time
from datetime import datetime


def sensors():
    if os.name != 'nt':
        return []
    try:
        import wmi
        import pythoncom
        pythoncom.CoInitialize()
        try:
            rows = wmi.WMI(namespace=r'root\LibreHardwareMonitor').Sensor()
            return [{'name': row.Name, 'type': row.SensorType, 'value': float(row.Value), 'parent': row.Parent} for row in rows if row.Value is not None]
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return []


def snapshot():
    import psutil
    start_io = psutil.disk_io_counters()
    start_net = psutil.net_io_counters()
    cpu = psutil.cpu_percent(interval=1)
    end_io = psutil.disk_io_counters()
    end_net = psutil.net_io_counters()
    ram = psutil.virtual_memory()
    frequency = psutil.cpu_freq()
    battery = psutil.sensors_battery()
    disks = []
    for partition in psutil.disk_partitions():
        try:
            disk = psutil.disk_usage(partition.mountpoint)
            disks.append({'mount': partition.mountpoint, 'used_gb': round(disk.used / 1024**3, 2), 'free_gb': round(disk.free / 1024**3, 2), 'percent': disk.percent})
        except (OSError, PermissionError):
            pass
    hardware = sensors()
    data = {'time': datetime.now().isoformat(timespec='seconds'), 'os': platform.platform(), 'uptime_hours': round((time.time() - psutil.boot_time()) / 3600, 1), 'cpu_percent': cpu, 'cpu_mhz': frequency.current if frequency else None, 'ram': {'used_gb': round(ram.used / 1024**3, 2), 'available_gb': round(ram.available / 1024**3, 2), 'percent': ram.percent}, 'disks': disks, 'sensors': hardware, 'local_ips': [address.address for items in psutil.net_if_addrs().values() for address in items if address.family == socket.AF_INET], 'battery': {'percent': battery.percent, 'plugged': battery.power_plugged, 'remaining_minutes': battery.secsleft // 60 if battery.secsleft >= 0 else None} if battery else None, 'gpu': None}
    if start_io and end_io:
        data['disk_io_mb_s'] = {'read': round((end_io.read_bytes - start_io.read_bytes) / 1024**2, 2), 'write': round((end_io.write_bytes - start_io.write_bytes) / 1024**2, 2)}
    if start_net and end_net:
        data['network_mbps'] = {'download': round((end_net.bytes_recv - start_net.bytes_recv) * 8 / 1_000_000, 2), 'upload': round((end_net.bytes_sent - start_net.bytes_sent) * 8 / 1_000_000, 2)}
    executable = shutil.which('nvidia-smi')
    if executable:
        try:
            result = subprocess.run([executable, '--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5, check=True, shell=False)
            data['gpu'] = result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return data


def report():
    data = snapshot()
    rows = [f"CPU: {data['cpu_percent']}% · {data['cpu_mhz']} MHz", f"RAM: {data['ram']['percent']}% · zajęte {data['ram']['used_gb']} GB · dostępne {data['ram']['available_gb']} GB", f"GPU (NVIDIA): {data['gpu'] or 'brak obsługi nvidia-smi; użyj czujników LibreHardwareMonitor'}", f"Czas pracy: {data['uptime_hours']} h", f"System: {data['os']}", f"Data: {data['time']}", f"Lokalne IP: {', '.join(data['local_ips'])}", f"Bateria: {data['battery'] or 'brak baterii / danych'}"]
    rows += [f"Dysk {disk['mount']}: wolne {disk['free_gb']} GB · zajęte {disk['used_gb']} GB ({disk['percent']}%)" for disk in data['disks']]
    rows += [f"Transfer sieci (próbka 1 s, wszystkie interfejsy, nie speedtest): {data.get('network_mbps')}", f"Dyski odczyt/zapis (łącznie, próbka 1 s): {data.get('disk_io_mb_s')}"]
    rows += [f"{sensor['name']} ({sensor['type']}): {sensor['value']}" for sensor in data['sensors'] if sensor['type'] in {'Temperature', 'Fan', 'Load', 'SmallData'}]
    if not data['sensors']:
        rows.append('Temperatury CPU/GPU i wentylatory: niedostępne. Wymagają działającego LibreHardwareMonitor z WMI i odpowiednich czujników.')
    rows.append('Kondycja baterii i ruch sieciowy per proces: nieobsługiwane. SMART: osobne polecenie „smart”. Nie wnioskuję o zdrowiu dysku z wolnego miejsca.')
    return '\n'.join(rows)


def smart():
    if os.name != 'nt':
        return 'SMART wymaga Windows i sterownika udostępniającego dane.'
    import pythoncom
    import wmi
    pythoncom.CoInitialize()
    try:
        rows = wmi.WMI(namespace=r'root\wmi').MSStorageDriver_FailurePredictStatus()
        return '\n'.join(f"{row.InstanceName}: {'przewidywana awaria' if row.PredictFailure else 'sterownik nie zgłasza przewidywanej awarii'}" for row in rows) or 'Brak danych SMART. Nie każdy SSD/NVMe udostępnia je przez WMI.'
    finally:
        pythoncom.CoUninitialize()


def devices():
    if os.name != 'nt':
        return 'Lista urządzeń wymaga Windows.'
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', '[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Get-PnpDevice -PresentOnly | Where-Object {$_.Class -in @("Bluetooth","USB")} | Select-Object FriendlyName,Class,Status | ConvertTo-Json -Compress'], capture_output=True, text=True, encoding='utf-8', timeout=20, check=True, shell=False)
    return result.stdout.strip() or 'Brak urządzeń USB/Bluetooth.'


def network():
    from urllib.request import urlopen
    rows = []
    try:
        with urlopen('https://api.ipify.org?format=json', timeout=8) as response:
            rows.append('Publiczne IP: ' + json.loads(response.read(4096))['ip'])
    except Exception:
        rows.append('Nie udało się odczytać publicznego IP. Nie dowodzi to braku całego internetu.')
    if os.name == 'nt':
        for args in (['netsh.exe', 'wlan', 'show', 'interfaces'], ['ping.exe', '-n', '2', '-w', '1500', '1.1.1.1']):
            result = subprocess.run(args, capture_output=True, text=True, errors='replace', timeout=8, shell=False)
            rows.append(result.stdout.strip())
    return '\n'.join(rows)
