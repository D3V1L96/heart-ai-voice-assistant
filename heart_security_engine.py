from __future__ import annotations
import psutil
import subprocess
import time
from datetime import datetime
import platform
import os

try:
    from pynvml import (
        nvmlInit, nvmlDeviceGetCount, nvmlDeviceGetHandleByIndex,
        nvmlDeviceGetName, nvmlDeviceGetUtilizationRates,
        nvmlDeviceGetMemoryInfo, nvmlDeviceGetTemperature,
        NVMLError, NVML_TEMPERATURE_GPU
    )
    PYNVML_AVAILABLE = True
    nvmlInit()
except (ImportError, NVMLError):
    PYNVML_AVAILABLE = False

try:
    import torch
    TORCH_CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    TORCH_CUDA_AVAILABLE = False

async def heart_security_utility(
    live_mode: bool = False,
    duration_seconds: int = 60
) -> str:
    """
    Real-time system monitoring and privacy check (optimized for Windows).
    Returns a formatted multi-line string report.
    """
    if platform.system() != "Windows":
        return "This monitoring tool is currently optimized for Windows systems only."

    report_lines = []
    report_lines.append("Heart Security & Performance Monitoring Report")
    report_lines.append("=" * 80)
    report_lines.append(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    def get_gpu_status() -> str:
        """Collect GPU usage, memory, and temperature (NVIDIA priority)."""
        gpu_lines = []

        # NVIDIA GPU monitoring (using nvidia-ml-py)
        if PYNVML_AVAILABLE:
            try:
                device_count = nvmlDeviceGetCount()
                for i in range(min(device_count, 2)):
                    handle = nvmlDeviceGetHandleByIndex(i)
                    name = nvmlDeviceGetName(handle).decode('utf-8')
                    util = nvmlDeviceGetUtilizationRates(handle)
                    mem_info = nvmlDeviceGetMemoryInfo(handle)
                    temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)

                    gpu_lines.append(
                        f"GPU {i}: {name}\n"
                        f"   Utilization: {util.gpu}% | "
                        f"Memory Used: {mem_info.used / 1024**3:.1f} / {mem_info.total / 1024**3:.1f} GB\n"
                        f"   Temperature: {temp}°C"
                    )
                if gpu_lines:
                    return "\n".join(gpu_lines)
            except Exception:
                pass

        # Fallback for CUDA (via PyTorch)
        if TORCH_CUDA_AVAILABLE:
            try:
                for i in range(min(torch.cuda.device_count(), 2)):
                    name = torch.cuda.get_device_name(i)
                    allocated = torch.cuda.memory_allocated(i) / 1024**3
                    reserved = torch.cuda.memory_reserved(i) / 1024**3
                    gpu_lines.append(
                        f"GPU {i} (CUDA/Torch): {name}\n"
                        f"   Memory Allocated: {allocated:.1f} GB\n"
                        f"   Memory Reserved:  {reserved:.1f} GB"
                    )
                if gpu_lines:
                    return "\n".join(gpu_lines)
            except Exception:
                pass

        return "No GPU detected or GPU monitoring libraries not available."

    def generate_report():
        nonlocal report_lines

        cpu_percent = psutil.cpu_percent(interval=1)
        ram_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('C:\\').percent
        net_io = psutil.net_io_counters()

        ts = datetime.now().strftime('%H:%M:%S')
        report_lines.append(f"[{ts}] SYSTEM PERFORMANCE SNAPSHOT")
        report_lines.append(f"  CPU Usage:          {cpu_percent:6.1f}%")
        report_lines.append(f"  RAM Usage:          {ram_percent:6.1f}%")
        report_lines.append(f"  Disk Usage (C:):    {disk_percent:6.1f}%")
        report_lines.append(f"  Network Sent:       {net_io.bytes_sent / (1024 * 1024):.1f} MB")
        report_lines.append(f"  Network Received:   {net_io.bytes_recv / (1024 * 1024):.1f} MB")

        report_lines.append("\nGPU STATUS (if available)")
        report_lines.append(get_gpu_status())

        # Top CPU consumers
        top_processes = sorted(
            psutil.process_iter(['name', 'cpu_percent', 'memory_percent']),
            key=lambda p: p.info['cpu_percent'], reverse=True
        )[:6]

        report_lines.append("\nTop 6 CPU-consuming processes:")
        for proc in top_processes:
            report_lines.append(
                f"  • {proc.info['name']:<25} | CPU: {proc.info['cpu_percent']:5.1f}% | "
                f"RAM: {proc.info['memory_percent']:5.1f}%"
            )

        # Security & performance alerts
        alerts = []
        if cpu_percent > 85:
            alerts.append("HIGH CPU USAGE DETECTED - possible background mining or malware activity")
        if ram_percent > 90:
            alerts.append("CRITICAL RAM USAGE - system performance may degrade")
        if disk_percent > 95:
            alerts.append("DISK SPACE NEARLY EXHAUSTED - immediate cleanup recommended")

        if alerts:
            report_lines.append("\nSECURITY & PERFORMANCE ALERTS:")
            for alert in alerts:
                report_lines.append(f"  ⚠️ {alert}")

        # Basic privacy/process check
        report_lines.append("\nACTIVE PROCESSES (potential microphone/camera/location users)")
        try:
            cmd = (
                "Get-Process | Where-Object {$_.MainWindowTitle} | "
                "Select-Object Name, Id, CPU | Sort-Object CPU -Descending | Select-Object -First 10"
            )
            result = subprocess.run(
                ['powershell', '-Command', cmd],
                capture_output=True,
                text=True,
                timeout=8
            )
            output = result.stdout.strip() or "No active windowed processes detected"
            report_lines.append(output)
        except Exception:
            report_lines.append("Privacy/process details unavailable (run as Administrator for full access)")

        report_lines.append("\nPermission Management:")
        report_lines.append("  → Press 'P' → Open Windows Privacy & Security settings")
        report_lines.append("  → Press 'T' → Open Task Manager for detailed process inspection")

    # Run monitoring
    if live_mode:
        report_lines.append(f"\nLIVE MONITORING MODE ENABLED ({duration_seconds} seconds)")
        report_lines.append("Press Ctrl+C in the terminal to stop monitoring early\n")
        try:
            start_time = time.time()
            while time.time() - start_time < duration_seconds:
                generate_report()
                time.sleep(5)
        except KeyboardInterrupt:
            report_lines.append("\nLive monitoring stopped by user.")
    else:
        generate_report()

    report_lines.append("\n" + "=" * 80)
    report_lines.append("Heart Security Utility - Report Complete")
    report_lines.append("Protect your personal data and stay vigilant.")

    return "\n".join(report_lines)


# ────────────────────────────────────────────────
# Standalone test / demo (run directly: python this_file.py)
# ────────────────────────────────────────────────
if __name__ == "__main__":
    # One-time report
    print("Generating one-time system security report...\n")
    print(heart_security_utility(live_mode=False))

    # Uncomment to test live monitoring:
    # print("\nStarting live monitoring for 30 seconds...\n")
    # print(heart_security_utility(live_mode=True, duration_seconds=30))