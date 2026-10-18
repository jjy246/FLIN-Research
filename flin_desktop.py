#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brain_Project — mathematics-first evidence-backed memory network desktop application.

Python 3.10+. Sources: Wikipedia, arXiv, Crossref, optional offline catalog; OpenAlex API is optional and OFF by default.
Google Scholar remains a manual verification link; API quotas and paywalls are respected.
Stores source-grounded mathematical concepts and candidate relations from pure and applied mathematics across disciplines. No embeddings. SQLite retains provenance.
"""
from __future__ import annotations

import html
import sys
import argparse
import gzip
import datetime
import contextlib
import ipaddress
import json
import math
import os
import queue
import random
import re
import sqlite3
import subprocess
import threading
import time
import traceback
import urllib.parse
import xml.etree.ElementTree as ET
import unicodedata
import hashlib
import shutil
import uuid
import webbrowser
from collections import defaultdict, deque
from functools import lru_cache
from difflib import SequenceMatcher
from pathlib import Path

import matplotlib
# Maintenance commands must also work over SSH without a DISPLAY.
_CLI_HEADLESS = any(flag in sys.argv for flag in (
    '--catalog-info','--catalog-search','--catalog-import-network','--catalog-backfill-keys','--source-info','--diagnose','--flin-discovery-info','--flin-source-report','--flin-association-audit','--flin-repair-associations','--flin-efficiency-report','--flin-retrofit','--flin-retrofit-limit','--purity-report','--purity-clean','--audit-math-quality','--export-curated-network','--build-fast-index','--import-openalex','--export-network','--list-networks','--new-network','--switch-network','--import-network','--domain','--cpu-info','--math-coverage','--display-check','--abc-info','--flin-info','--abc-enable','--flin-enable','--abc-learn-existing','--flin-learn-existing','--abc-simulate','--flin-simulate','--abc-create-network','--flin-create-network','--abc-reconcile','--flin-reconcile','--abc-clusters','--flin-clusters','--abc-pulse-rate','--flin-pulse-rate','--abc-duration','--flin-duration','--abc-threshold','--flin-threshold','--abc-window','--flin-window','--abc-revisits','--flin-revisits','--verify-export','--flin-bridges','--flin-related','--help','-h'))
matplotlib.use('Agg' if _CLI_HEADLESS else 'TkAgg')
import matplotlib.pyplot as plt
# Ensure CJK captions render when a Noto CJK font is installed.
# Matplotlib's available CJK family can differ from `fc-match` on Ubuntu.
from matplotlib import font_manager as _fonts
_present = {f.name for f in _fonts.fontManager.ttflist}
for _candidate in ("Noto Sans CJK TC", "Noto Sans CJK JP", "Noto Serif CJK TC",
                   "Noto Serif CJK JP", "Microsoft JhengHei"):
    if _candidate in _present:
        plt.rcParams["font.sans-serif"] = [_candidate, "DejaVu Sans"]
        break
plt.rcParams["axes.unicode_minus"] = False
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib import font_manager
from mpl_toolkits.mplot3d import proj3d
from mpl_toolkits.mplot3d.art3d import Line3DCollection
import networkx as nx
import numpy as np
import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

try:
    import fitz  # PyMuPDF: optional only if PDF mode is used
except ImportError:
    fitz = None
else:
    # Some academic PDFs declare optional content groups but omit their /D
    # default layer configuration. MuPDF emits a recoverable format error even
    # when page text is readable. Avoid flooding the terminal during collection;
    # Python exceptions still propagate to the existing PDF fallback, and the
    # low-level diagnostics remain available via fitz.TOOLS.mupdf_warnings().
    try:
        fitz.TOOLS.mupdf_display_errors(False)
    except AttributeError:
        pass  # Older PyMuPDF builds may lack this control.

APP_TITLE = "FLIN — Feature-Link Intellegence Network | Efficiency-Aware v19.0"


def _flin_linux_cgroup_resources():
    """Find effective cgroup v1/v2 quotas without changing scheduler settings.

    Nested container limits may be tighter than the leaf cgroup. /proc/self/cgroup
    resolves the effective hierarchy; malformed or unreadable files are ignored.
    """
    if not sys.platform.startswith('linux'):
        return None, None
    cpu_limits, memory_limits = [], []
    paths = {'unified': '/', 'cpu': '/', 'memory': '/'}
    try:
        for line in Path('/proc/self/cgroup').read_text().splitlines():
            parts = line.split(':', 2)
            if len(parts) != 3:
                continue
            hierarchy, controllers, path = parts
            if hierarchy == '0' and not controllers:
                paths['unified'] = path
            for controller in controllers.split(','):
                if controller in ('cpu', 'memory'):
                    paths[controller] = path
    except OSError:
        pass

    def walk(base, group):
        # Avoid path traversal: cgroup paths are kernel-provided, not user input.
        pieces = [p for p in group.split('/') if p not in ('', '.', '..')]
        root = Path(base)
        current = root
        yield current
        for piece in pieces:
            current = current / piece
            yield current

    def positive_int(path):
        try:
            value = path.read_text().strip()
            return int(value) if value.isdecimal() else None
        except (OSError, ValueError):
            return None

    unified = Path('/sys/fs/cgroup')
    if (unified / 'cgroup.controllers').exists():
        for folder in walk(unified, paths['unified']):
            try:
                raw = (folder / 'cpu.max').read_text().split()
                if len(raw) == 2 and raw[0] != 'max':
                    quota, period = int(raw[0]), int(raw[1])
                    if quota > 0 and period > 0:
                        cpu_limits.append(quota / period)
            except (OSError, ValueError, IndexError):
                pass
            limit = positive_int(folder / 'memory.max')
            if limit is not None and limit > 0:
                usage = positive_int(folder / 'memory.current')
                if usage is not None:
                    memory_limits.append(max(0, limit - usage))
    else:
        for folder in walk('/sys/fs/cgroup/cpu', paths['cpu']):
            quota = positive_int(folder / 'cpu.cfs_quota_us')
            period = positive_int(folder / 'cpu.cfs_period_us')
            if quota is not None and period and quota > 0:
                cpu_limits.append(quota / period)
        for folder in walk('/sys/fs/cgroup/memory', paths['memory']):
            limit = positive_int(folder / 'memory.limit_in_bytes')
            usage = positive_int(folder / 'memory.usage_in_bytes')
            if limit is not None and usage is not None and limit < (1 << 60):
                memory_limits.append(max(0, limit - usage))
    return (min(cpu_limits) if cpu_limits else None,
            min(memory_limits) if memory_limits else None)


def _flin_windows_memory_available():
    """Standard-library fallback when optional psutil is not installed."""
    if sys.platform != 'win32':
        return None, None
    try:
        import ctypes
        from ctypes import wintypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [('dwLength', wintypes.DWORD), ('dwMemoryLoad', wintypes.DWORD),
                        ('ullTotalPhys', ctypes.c_ulonglong),
                        ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong),
                        ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong),
                        ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        state = MEMORYSTATUSEX()
        state.dwLength = ctypes.sizeof(state)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            return int(state.ullAvailPhys), int(state.ullTotalPhys)
    except (AttributeError, OSError, ValueError):
        pass
    return None, None


def _flin_windows_process_affinity():
    """Query the Windows process affinity mask when psutil is unavailable.

    Windows with >64 CPUs may have several processor groups; the group-aware
    psutil result is preferred. This legacy API reports the current mask only.
    """
    if sys.platform != 'win32':
        return None
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.GetProcessAffinityMask.argtypes = (
            wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t),
            ctypes.POINTER(ctypes.c_size_t))
        k32.GetProcessAffinityMask.restype = wintypes.BOOL
        proc_mask, system_mask = ctypes.c_size_t(), ctypes.c_size_t()
        ok = k32.GetProcessAffinityMask(k32.GetCurrentProcess(),
                                        ctypes.byref(proc_mask), ctypes.byref(system_mask))
        if ok and proc_mask.value:
            return [i for i in range(ctypes.sizeof(proc_mask)*8)
                    if proc_mask.value & (1 << i)]
    except (AttributeError, OSError, ValueError):
        pass
    return None


def _flin_windows_cpu_percent_fallback():
    """Measure CPU usage with Win32 GetSystemTimes, no extra Python package.

    The native call returns aggregate system usage (not a processor-group aware
    per-process measurement). Prefer psutil for the full view when available.
    """
    if sys.platform != 'win32':
        return None
    try:
        import ctypes
        from ctypes import wintypes
        class FILETIME(ctypes.Structure):
            _fields_ = [('low', wintypes.DWORD), ('high', wintypes.DWORD)]
        k32 = ctypes.windll.kernel32
        k32.GetSystemTimes.argtypes = (ctypes.POINTER(FILETIME),
                                      ctypes.POINTER(FILETIME),
                                      ctypes.POINTER(FILETIME))
        k32.GetSystemTimes.restype = wintypes.BOOL
        def sample():
            idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
            if not k32.GetSystemTimes(ctypes.byref(idle),
                                      ctypes.byref(kernel), ctypes.byref(user)):
                return None
            to_int = lambda ft: (int(ft.high) << 32) | int(ft.low)
            return (to_int(idle), to_int(kernel) + to_int(user))
        earlier = sample()
        if earlier is None:
            return None
        time.sleep(0.15)
        later = sample()
        if later is None:
            return None
        total = later[1] - earlier[1]
        idle = later[0] - earlier[0]
        if total > 0:
            return round(100.0*max(0.0, min(1.0, 1.0-idle/total)), 1)
    except (AttributeError, OSError, ValueError):
        pass
    return None


def _flin_cpu_percent_fallback(affinity):
    """Measure Linux per-CPU utilization using two /proc/stat samples."""
    if not sys.platform.startswith('linux'):
        return None
    def snapshot():
        counters = {}
        try:
            with open('/proc/stat', encoding='ascii') as stream:
                for line in stream:
                    parts = line.split()
                    if len(parts) < 5 or not parts[0].startswith('cpu'):
                        continue
                    suffix = parts[0][3:]
                    if not suffix.isdecimal():
                        continue
                    values = [int(value) for value in parts[1:]]
                    idle = values[3] + (values[4] if len(values) > 4 else 0)
                    counters[int(suffix)] = (sum(values), idle)
        except (OSError, ValueError):
            return {}
        return counters
    before = snapshot()
    if not before:
        return None
    time.sleep(0.10)
    after = snapshot()
    changes = []
    for index in affinity:
        if index in before and index in after:
            total = after[index][0] - before[index][0]
            idle = after[index][1] - before[index][1]
            if total > 0:
                changes.append(100.0 * (total-idle) / total)
    return round(max(0.0, min(100.0, sum(changes)/len(changes))), 1) if changes else None


def detect_cpu_resources():
    """Observe actual machine limits and current free resources (Linux/Windows/macOS).

    psutil is optional. With it, read process CPU affinity, physical cores,
    per-CPU load and available RAM. Otherwise use stdlib platform fallbacks.
    This function NEVER changes process affinity or resource reservations.
    """
    logical = max(1, os.cpu_count() or 1)
    affinity = None
    physical = None
    available_bytes = total_bytes = None
    cpu_load = None
    backend = 'system'
    try:
        import psutil
    except ImportError:
        psutil = None
    if psutil is not None:
        backend = 'psutil'
        try:
            logical = max(1, int(psutil.cpu_count(logical=True) or logical))
            physical = psutil.cpu_count(logical=False)
        except (OSError, ValueError):
            pass
        try:
            affinity = sorted(set(int(x) for x in psutil.Process().cpu_affinity()))
        except (AttributeError, OSError, ValueError):
            pass
        try:
            memory = psutil.virtual_memory()
            available_bytes, total_bytes = int(memory.available), int(memory.total)
        except (OSError, ValueError):
            pass
    if affinity is None:
        try:
            affinity = sorted(os.sched_getaffinity(0))
        except (AttributeError, OSError):
            affinity = None
        if affinity is None:
            affinity = _flin_windows_process_affinity()
        if affinity is None:
            affinity = list(range(logical))
    if not affinity:
        affinity = list(range(logical))
    if physical is None and sys.platform.startswith('linux'):
        cores = set()
        for cpu in affinity:
            base = Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
            try:
                pkg = (base / 'physical_package_id').read_text().strip()
                core = (base / 'core_id').read_text().strip()
                cores.add((pkg, core))
            except OSError:
                pass
        physical = len(cores) if cores else None
    if available_bytes is None:
        if sys.platform.startswith('linux'):
            values = {}
            try:
                for line in Path('/proc/meminfo').read_text().splitlines():
                    if line.startswith(('MemAvailable:', 'MemTotal:')):
                        key, number, *_ = line.split()
                        values[key[:-1]] = int(number) * 1024
                available_bytes = values.get('MemAvailable', values.get('MemTotal'))
                total_bytes = values.get('MemTotal')
            except (OSError, ValueError):
                pass
        elif sys.platform == 'win32':
            available_bytes, total_bytes = _flin_windows_memory_available()
        else:
            try:
                available_bytes = int(os.sysconf('SC_AVPHYS_PAGES')) * int(os.sysconf('SC_PAGE_SIZE'))
                total_bytes = int(os.sysconf('SC_PHYS_PAGES')) * int(os.sysconf('SC_PAGE_SIZE'))
            except (AttributeError, OSError, ValueError):
                pass
    quota_cores, cgroup_memory_left = _flin_linux_cgroup_resources()
    quota_slots = max(1, math.floor(quota_cores)) if quota_cores is not None else None
    capacity = max(1, min(len(affinity), quota_slots) if quota_slots else len(affinity))
    if available_bytes is not None and cgroup_memory_left is not None:
        available_bytes = min(available_bytes, cgroup_memory_left)
    elif available_bytes is None:
        available_bytes = cgroup_memory_left
    if psutil is not None:
        try:
            loads = psutil.cpu_percent(interval=0.12, percpu=True)
            chosen = [loads[idx] for idx in affinity if 0 <= idx < len(loads)]
            if chosen:
                cpu_load = round(sum(chosen) / len(chosen), 1)
        except (OSError, ValueError):
            pass
    if cpu_load is None:
        cpu_load = _flin_cpu_percent_fallback(affinity)
    if cpu_load is None:
        cpu_load = _flin_windows_cpu_percent_fallback()
    to_gib = lambda n: round(max(0, n) / (1024 ** 3), 2) if n is not None else None
    return {
        'system_logical': logical,
        'affinity_logical': len(affinity),
        'physical_visible': physical,
        'quota_logical': quota_slots,
        'quota_cores': round(quota_cores, 3) if quota_cores is not None else None,
        'available': capacity,
        'cpu_ids': tuple(affinity),
        'cpu_load_pct': cpu_load,
        'memory_available_gib': to_gib(available_bytes),
        'memory_total_gib': to_gib(total_bytes),
        'resource_backend': backend,
    }


def recommend_build_resources(info, read_pdf=False):
    """Adapt to actual CPU headroom, free RAM and the selected collection mode.

    This is an initial operating suggestion, not a throughput benchmark. APIs,
    PDF downloads and SQLite's serialized writes can still set lower limits.
    No fixed 70%% CPU / 45%% worker fraction or eight-worker ceiling is used.
    """
    cap = max(1, int(info['available']))
    busy = info.get('cpu_load_pct')
    if busy is not None:
        busy = max(0.0, min(100.0, float(busy)))
        headroom = cap * (1.0 - busy / 100.0)
        cpu = round(headroom * 0.95)
    else:
        cpu = cap
    # Reserve one available logical CPU for an interactive desktop when possible.
    if cap >= 4:
        cpu = min(cpu, cap - 1)
    cpu = max(1, min(cap, cpu))
    # I/O workers need not equal active CPU cores; PDF parsing is more memory heavy.
    factor = 0.85 if read_pdf else 0.72
    workers = max(1, min(cap, math.ceil(cpu * factor) + 1))
    ram_gib = info.get('memory_available_gib')
    if ram_gib is not None:
        # Reserve free RAM for SQLite, Python, GUI, and other foreground work.
        per_worker = 1.2 if read_pdf else 0.48
        ram_cap = max(1, math.floor((max(0.0, float(ram_gib)) - 0.8) / per_worker))
        workers = min(workers, ram_cap)
        if ram_gib < 1.5:
            cpu = min(cpu, 2)
            workers = 1
    return {'cpu_budget': cpu, 'workers': workers,
            'worker_max': cap, 'cpu_max': cap, 'pdf_mode': bool(read_pdf),
            'cpu_load_pct': busy, 'memory_available_gib': ram_gib}


def constrain_collector_cpu_affinity(cpu_budget, log=None):
    """Apply Linux per-thread affinity only to the background collector thread.

    Worker threads created by the collector inherit its affinity; Tk and any
    external Ollama process keep their own settings. Windows/macOS do not have
    this Linux per-thread API, so CPU budget remains an advisory GUI setting.
    """
    if not hasattr(os, 'sched_setaffinity'):
        if log:
            log('Collector CPU affinity is not supported on this platform; worker-count limit remains active.')
        return False
    info = detect_cpu_resources()
    selected = info['cpu_ids'][:max(1, min(int(cpu_budget), info['available']))]
    try:
        os.sched_setaffinity(0, set(selected))
        if log:
            log(f'Collector affinity: {len(selected)}/{info["available"]} permitted logical CPUs (Linux worker threads only).')
        return True
    except OSError as exc:
        if log:
            log(f'Collector affinity could not be applied ({exc}); worker-count limit remains active.')
        return False


NODE_STYLES = {
    'theory': {'name':' Topic / theory ', 'color':'#ffb34d', 'marker':'o', 'size':140, 'legend':'●'},
    'paper': {'name':' Research Paper ', 'color':'#54acff', 'marker':'s', 'size':46, 'legend':'■'},
    'concept': {'name':'Active concept memory', 'color':'#32e4b1', 'marker':'^', 'size':53, 'legend':'▲'},
    'relation': {'name':' Relation Memory Unit ', 'color':'#c792ff', 'marker':'D', 'size':42, 'legend':'◆'},
    'candidate': {'name':'Legacy candidate', 'color':'#a9b1be', 'marker':'.', 'size':28, 'legend':'·'},
}
DATA_DIR = Path.home() / ".local" / "share" / "brain_project"
# Existing installations keep the original association.sqlite3 as the legacy network.
# Other networks are individual SQLite files; no database is overwritten on switch.
LEGACY_DB_PATH = DATA_DIR / "association.sqlite3"
NETWORKS_DIR = DATA_DIR / "networks"
NETWORK_REGISTRY = DATA_DIR / "network_registry.json"
_NETWORK_REGISTRY_LOCK = threading.RLock()

# Domain IDs are stable and form part of the per-network registry, not graph IDs.
# Existing legacy installations remain in their old mathematics mode. New graphs
# default to a cross-disciplinary profile and do not inherit mathematics filters.
DOMAIN_PROFILES = {
    'general': {
        'name': ' cross-disciplinary / general-purpose research ',
        'entries': ('Science', 'Engineering', 'Medicine', 'Business', 'Economics',
                    'Social science', 'Computer science', 'History', 'Biology',
                    'Psychology', 'Technology', 'Environmental science',
                    'Artificial intelligence', 'Research methods'),
        'categories': ('Category:Scientific disciplines', 'Category:Academic disciplines',
                       'Category:Branches of science', 'Category:Engineering disciplines',
                       'Category:Social sciences', 'Category:Humanities',
                       'Category:Applied sciences', 'Category:Research methods',
                       'Category:Technology'),
        'keywords': ('research', 'model', 'method', 'theory', 'analysis', 'system',
                     'design', 'process', 'framework', 'effect', 'mechanism'),
    },
    'custom': {'name':' custom Domain (Wikipedia  Topic / category )', 'entries': (), 'categories': (), 'keywords': ()},
    'mathematics': {'name': 'Mathematics (pure and applied across disciplines)', 'entries': (), 'categories': (), 'keywords': ()},
    'engineering': {
        'name': ' Engineering and Manufacturing ',
        'entries': ('Mechanical engineering', 'Electrical engineering', 'Control engineering',
                    'Materials science', 'Robotics', 'Manufacturing'),
        'categories': ('Category:Engineering disciplines', 'Category:Mechanical engineering',
                       'Category:Electrical engineering', 'Category:Control engineering',
                       'Category:Manufacturing', 'Category:Robotics', 'Category:Materials science'),
        'keywords': ('engineering','control','robot','manufacturing','mechanism','material','design'),
    },
    'computer_science': {
        'name':' computer science and  AI',
        'entries': ('Computer science', 'Artificial intelligence', 'Machine learning',
                    'Computer vision', 'Information security', 'Databases'),
        'categories': ('Category:Computer science', 'Category:Artificial intelligence',
                       'Category:Machine learning', 'Category:Computer vision',
                       'Category:Information security', 'Category:Databases'),
        'keywords': ('algorithm','computing','learning','model','database','network'),
    },
    'medicine': {
        'name':' Medicine and Health ',
        'entries': ('Medicine', 'Clinical research', 'Public health', 'Neuroscience',
                    'Pharmacology', 'Epidemiology'),
        'categories': ('Category:Medical specialties', 'Category:Medicine',
                       'Category:Public health', 'Category:Neuroscience',
                       'Category:Pharmacology', 'Category:Epidemiology'),
        'keywords': ('clinical','medical','patient','disease','treatment','health','therapy'),
    },
    'life_science': {
        'name':' Life Sciences and Biology ',
        'entries': ('Biology', 'Molecular biology', 'Genetics', 'Biochemistry', 'Ecology'),
        'categories': ('Category:Branches of biology', 'Category:Molecular biology',
                       'Category:Genetics', 'Category:Biochemistry', 'Category:Ecology'),
        'keywords': ('cell','gene','protein','species','organism','genetic','molecular'),
    },
    'business': {
        'name':' business / Finance / economics ',
        'entries': ('Business', 'Finance', 'Management', 'Marketing', 'Economics',
                    'Corporate finance', 'Accounting'),
        'categories': ('Category:Business', 'Category:Finance', 'Category:Management',
                       'Category:Marketing', 'Category:Economics', 'Category:Accounting'),
        'keywords': ('finance','market','business','consumer','revenue','economic','management'),
    },
    'social_science': {
        'name':' Social Sciences ',
        'entries': ('Sociology', 'Psychology', 'Political science', 'Education',
                    'Anthropology', 'Human geography'),
        'categories': ('Category:Social sciences', 'Category:Sociology',
                       'Category:Psychology', 'Category:Education',
                       'Category:Anthropology', 'Category:Political science'),
        'keywords': ('society','behavior','policy','population','education','culture'),
    },
    'humanities': {
        'name':' humanities / history / philosophy learning ',
        'entries': ('History', 'Philosophy', 'Literature', 'Linguistics', 'Ethics'),
        'categories': ('Category:Humanities', 'Category:History', 'Category:Philosophy',
                       'Category:Linguistics', 'Category:Literature'),
        'keywords': ('history','language','philosophy','literature','culture','ethics'),
    },
}

def active_domain():
    """Math-only collection policy, regardless of a legacy registry label.

    Historical non-math databases are not deleted or silently reclassified;
    switching to them only changes which SQLite file is open. Fresh indexing,
    retrieval-quality gates and problem generation always use mathematics.
    """
    return 'mathematics'


def domain_profile():
    key=active_domain()
    if key!='custom':return DOMAIN_PROFILES[key]
    try:
        record=active_network_record()
        base=DOMAIN_PROFILES['general']
        return {'name':record.get('custom_name') or ' custom Domain ',
                'entries':tuple(record.get('custom_entries') or base['entries']),
                'categories':tuple(record.get('custom_categories') or base['categories']),
                'keywords':tuple(record.get('custom_keywords') or base['keywords'])}
    except Exception:
        return DOMAIN_PROFILES['general']


def domain_name():
    return domain_profile()['name']

DOMAIN_REVIEW_GUIDES = {
    'general': ' Research objects , operational definitions , Data can obtain properties , method can feasibility , comparison baselines , ethics and Evidence Limit .',
    'mathematics': ' clear confirm Mathematical objects and mathematical notation , domain , quantifiers , required assumptions , define principle / reverse example / reproducible count value Validate , cross-disciplinaryModelMathematics mapping , already knowledge research comparison , Evidence Source and applicable boundary .',
    'engineering': ' system needs request , design Limit , physical measurement , experiments reproducible properties , install all , can reliability and performance metrics .',
    'computer_science': ' dataset / algorithm definitions , complexity , baseline , ablation test , generalization , security and reproducible properties .',
    'medicine': ' research population , intervention and for as , end points , efficiency should size , bias and confounding , ethics and clinical can feasibility .',
    'life_science': ' biological mechanisms , sample this and for as , measurement validity , experimental confounders , reproducible properties and reason result Limit .',
    'business': ' research market and period , primary metrics , knowledge other Assumptions , confounders , applicable context and benefit .',
    'social_science': ' research population , operational measurement , sampling , research design , confounding and ethical risks .',
    'humanities': ' historical sources / text this Source , concept context , interpretation Path , falsifiable for argument and Limit .',
    'custom': ' according to user Settings research Domain , Check concept define meaning , method suitability , Evidence and verifiable items label .',
}

def domain_review_guide():
    return DOMAIN_REVIEW_GUIDES.get(active_domain(), DOMAIN_REVIEW_GUIDES['general'])


def _as_custom_list(value, limit=30):
    if isinstance(value,(tuple,list)): bits=[str(x).strip() for x in value]
    else:bits=[str(x).strip() for x in str(value or '').replace(';',',').replace('；','，').replace('，',',').split(',')]
    return list(dict.fromkeys([x for x in bits if 1<=len(x)<=120]))[:limit]


def _custom_profile_options(custom_entries=(),custom_categories=(),custom_keywords=()):
    entries=_as_custom_list(custom_entries,40)
    categories=[x if x.startswith('Category:') else 'Category:'+x
                for x in _as_custom_list(custom_categories,40)]
    keywords=_as_custom_list(custom_keywords,60)
    return dict(custom_entries=entries,custom_categories=categories,
                custom_keywords=keywords)


def _network_default_registry():
    return {'version': 1, 'active': 'legacy', 'networks': [
        {'id': 'legacy', 'name': ' Original Memory Network ', 'created': '', 'filename': 'legacy'}]}


def _registry_path_for(record):
    network_id = str(record.get('id', ''))
    if network_id == 'legacy' and record.get('filename') == 'legacy':
        return LEGACY_DB_PATH
    # Filenames are generated by this application, never imported paths.
    filename = record.get('filename', '')
    if not re.fullmatch(r'net_[0-9a-f]{32}\.sqlite3', filename):
        raise ValueError(' Network The registry contains an invalid  SQLite  filename .')
    return NETWORKS_DIR / filename


def read_network_registry():
    with _NETWORK_REGISTRY_LOCK:
        if not NETWORK_REGISTRY.exists():
            return _network_default_registry()
        data = json.loads(NETWORK_REGISTRY.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or not isinstance(data.get('networks'), list):
            raise ValueError(' Network list format with error ; original database Not yet changes .')
        ids = set()
        for item in data['networks']:
            if not isinstance(item, dict) or item.get('id') in ids:
                raise ValueError(' Network list duplicate or invalid format .')
            ids.add(item.get('id'))
            _registry_path_for(item)
        if data.get('active') not in ids:
            raise ValueError(' Current enable Network NOT in in the list , please Repair registry file .')
        return data


def set_network_domain(network_id, domain, *, custom_options=None):
    """Only mathematics is a supported future collection policy."""
    if domain != 'mathematics':
        raise ValueError(' this application already focus on all Domain Mathematics ; please use  mathematics  Mode . legacy network still can read .')
    if domain not in DOMAIN_PROFILES:
        raise ValueError(' unknown Domain code :'+str(domain))
    with _NETWORK_REGISTRY_LOCK:
        registry=read_network_registry()
        target=next((item for item in registry['networks'] if item['id']==network_id),None)
        if target is None: raise ValueError(' Network NOT in in registry .')
        target['domain']=domain
        if custom_options:target.update(custom_options)
        try:
            with sqlite3.connect(str(_registry_path_for(target)),timeout=30) as cn:
                cn.execute('INSERT OR REPLACE INTO network_meta(key,value) VALUES(?,?)',
                           ('research_domain',domain))
                if custom_options:
                    cn.execute('INSERT OR REPLACE INTO network_meta(key,value) VALUES(?,?)',
                        ('research_custom_options',json.dumps(custom_options,ensure_ascii=False)))
                cn.commit()
        except sqlite3.DatabaseError:
            pass

        _write_network_registry(registry)
        if registry.get('active')==network_id:
            globals()['ACTIVE_DOMAIN_ID']=domain
    return domain


def _write_network_registry(registry):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = NETWORK_REGISTRY.with_name('.network_registry_' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, NETWORK_REGISTRY)
    finally:
        tmp.unlink(missing_ok=True)


def active_network_record():
    registry = read_network_registry()
    return next(item for item in registry['networks'] if item['id'] == registry['active'])


def network_entries():
    return [(item, _registry_path_for(item)) for item in read_network_registry()['networks']]


def network_path_from_id(network_id):
    for record, path in network_entries():
        if record['id'] == network_id:
            return path
    raise ValueError(' cannot find point define Memory unit Network :' + str(network_id))


def _validate_network_name(name):
    name = str(name or '').strip()
    if not 1 <= len(name) <= 80 or any(x in name for x in ('\n', '\r', '\0')):
        raise ValueError('Enter Input 1-80  charactersNetwork Name.')
    return name


def _register_network(name, path, network_id, *, activate=False, domain='mathematics',
                      custom_options=None):
    global DB_PATH
    with _NETWORK_REGISTRY_LOCK:
        reg = read_network_registry()
        if any(x['id'] == network_id for x in reg['networks']):
            raise ValueError(' Network  ID  duplicate .')
        # The SQLite database independently records its research-domain setting,
        # so a .sqlite3 backup remains self-describing without registry.json.
        try:
            with sqlite3.connect(str(path), timeout=30) as cn:
                cn.execute('INSERT OR REPLACE INTO network_meta(key,value) VALUES(?,?)',
                           ('research_domain',domain))
                if custom_options:
                    cn.execute('INSERT OR REPLACE INTO network_meta(key,value) VALUES(?,?)',
                        ('research_custom_options',json.dumps(custom_options,ensure_ascii=False)))
                cn.commit()
        except sqlite3.DatabaseError:
            pass  # Portable nodes/edges are still valid; registry is authoritative.
        reg['networks'].append({
            'id': network_id, 'name': _validate_network_name(name),
            'created': datetime.datetime.now().isoformat(timespec='seconds'),
            'filename': path.name, 'domain': domain, **(custom_options or {})})
        if activate:
            reg['active'] = network_id
        _write_network_registry(reg)
        if activate:
            DB_PATH = path
            globals()['ACTIVE_DOMAIN_ID']=domain
    return network_id


def switch_active_network(network_id):
    global DB_PATH
    with _NETWORK_REGISTRY_LOCK:
        registry = read_network_registry()
        entry = next((x for x in registry['networks'] if x['id'] == network_id), None)
        if entry is None:
            raise ValueError(' cannot find This Network .')
        path = _registry_path_for(entry)
        if not path.is_file():
            if network_id == 'legacy' and not LEGACY_DB_PATH.exists():
                # First run can initialize the legacy database on demand.
                with contextlib.closing(database(path=LEGACY_DB_PATH)):
                    pass
            else:
                raise FileNotFoundError(' Network Database NOT store in :' + str(path))
        registry['active'] = network_id
        _write_network_registry(registry)
        DB_PATH = path
        globals()['ACTIVE_DOMAIN_ID']=entry.get('domain','mathematics')
        return entry


def create_empty_network(name, *, activate=False, domain='mathematics',custom_options=None):
    name = _validate_network_name(name)
    if domain != 'mathematics': raise ValueError(' new build Network only support all Domain Mathematics Mode .')
    NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    network_id = uuid.uuid4().hex
    path = NETWORKS_DIR / ('net_' + network_id + '.sqlite3')
    try:
        with contextlib.closing(database(path=path)) as con:
            with con:
                con.execute('INSERT OR REPLACE INTO network_meta(key,value) VALUES(?,?)',
                            ('network_display_name', name))
        _register_network(name, path, network_id, activate=activate, domain=domain,custom_options=custom_options)
        return network_id
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _validate_sqlite_network(connection):
    tables = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'units', 'edges'}.issubset(tables):
        raise ValueError(' this NOT is  Brain_Project  Memory unit Network  SQLite: missing  units/edges  Data table .')
    required = {'units': {'id', 'label', 'kind'},
                'edges': {'src', 'dst', 'kind', 'weight'}}
    for table, cols in required.items():
        existing = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
        if not cols.issubset(existing):
            raise ValueError(' Incompatible network database columns :' + table)
    # Check SQLite pages before admitting an external copy into the registry.
    result = connection.execute('PRAGMA quick_check(1)').fetchone()[0]
    if result != 'ok':
        raise ValueError('SQLite  completeness check failed validation :' + str(result))


class NetworkImportCancelled(Exception):
    pass


def import_network(source, name, *, activate=False, stop_event=None, progress=None,
                   domain='mathematics', custom_options=None):
    """Import our SQLite snapshots or portable manifest/JSONL.gz folders.

    Stream into an isolated staging DB. Never replace an existing network.
    A cancelled/failed import is not registered as switchable.
    """
    name = _validate_network_name(name)
    source = Path(source).expanduser().resolve()
    NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    network_id = uuid.uuid4().hex
    target = NETWORKS_DIR / ('net_' + network_id + '.sqlite3')
    stage = NETWORKS_DIR / ('.stage_' + network_id + '.sqlite3')
    def checkpoint():
        if stop_event is not None and stop_event.is_set():
            raise NetworkImportCancelled(' Import already cancel ; No modify original with Network .')
    def report(label, done=0, total=0):
        if progress:
            progress(label, done, total)
    if source.is_dir() and (source / 'association.sqlite3').is_file():
        source = source / 'association.sqlite3'
    try:
        checkpoint()
        if source.is_file() and source.suffix.lower() in ('.db', '.sqlite', '.sqlite3'):
            if source == DB_PATH.resolve() or source == target.resolve():
                raise ValueError(' Cannot Processing use Network directly Import to yourself ; Select Export backup .')
            with contextlib.closing(sqlite3.connect(source.as_uri() + '?mode=ro',
                                                    uri=True, timeout=30)) as original:
                _validate_sqlite_network(original)
                try:
                    rec=original.execute("SELECT value FROM network_meta WHERE key='research_domain'").fetchone()
                    if domain=='general' and rec and rec[0] in DOMAIN_PROFILES:
                        domain=rec[0]
                    opts=original.execute("SELECT value FROM network_meta WHERE key='research_custom_options'").fetchone()
                    if custom_options is None and opts:custom_options=json.loads(opts[0])
                except (sqlite3.DatabaseError,ValueError,TypeError):pass
                with contextlib.closing(sqlite3.connect(str(stage), timeout=30)) as new:
                    def backup_progress(status, remaining, total):
                        checkpoint()
                        report(' backup  SQLite  page ', total - remaining, total)
                    original.backup(new, pages=512, progress=backup_progress, sleep=0.05)
            report(' Processing Check Import after  SQLite  complete properties ', 0, 0)
            with contextlib.closing(sqlite3.connect(str(stage))) as con:
                _validate_sqlite_network(con)
            # Schema migrations remain the responsibility of database() when activated.
        elif source.is_dir() and (source / 'manifest.json').is_file():
            manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
            # Portable exports record provenance; caller may override its domain.
            if domain=='general' and manifest.get('domain') in DOMAIN_PROFILES:
                domain=manifest['domain']
            if custom_options is None and manifest.get('domain_custom_options'):
                custom_options=manifest['domain_custom_options']
            if (manifest.get('format') != 'brain-project-directed-memory-network'
                    or int(manifest.get('schema_version', 0)) != 1):
                raise ValueError(' can portable Network formatVersionincompatible .')
            tables = manifest.get('tables') or {}
            if not {'units', 'edges'}.issubset(tables):
                raise ValueError(' Import must include includes  units  and  edges; please use complete Network Export folder .')
            # New DB contains all current tables, even if the portable export has
            # only the core graph. Auxiliary tables not present remain empty.
            with contextlib.closing(database(path=stage)) as con:
                with con:
                    con.execute("INSERT OR REPLACE INTO network_meta(key,value) VALUES('skip_legacy_event_migration','1')")
                for table, info in tables.items():
                    checkpoint()
                    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', table):
                        raise ValueError(' Data table name NOT valid .')
                    allowed = set(EXPORT_CORE_TABLES + EXPORT_PROVENANCE_TABLES)
                    if table not in allowed:
                        continue
                    path = source / (table + '.jsonl.gz')
                    if not path.is_file():
                        raise FileNotFoundError(' cannot find Export file :' + str(path))
                    columns = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
                    wanted = [x for x in info.get('columns', []) if x in columns]
                    if not wanted or len(wanted) != len(info.get('columns', [])):
                        raise ValueError(' field format and Current program incompatible :' + table)
                    sql = (f'INSERT OR REPLACE INTO "{table}" (' +
                           ','.join('"'+col+'"' for col in wanted) + ') VALUES (' +
                           ','.join('?' for _ in wanted) + ')')
                    count = 0
                    batch = []
                    expected = int(info.get('rows', 0))
                    report(' Import  ' + table, count, expected)
                    with gzip.open(path, 'rt', encoding='utf-8') as stream:
                        for line in stream:
                            if not line.strip():
                                continue
                            if count % 500 == 0:
                                checkpoint()
                            data = json.loads(line)
                            if not isinstance(data, dict):
                                raise ValueError(table + '  store in not object  JSON.')
                            batch.append(tuple(data.get(col) for col in wanted))
                            if len(batch) >= 1000:
                                with con:
                                    con.executemany(sql, batch)
                                count += len(batch)
                                batch.clear()
                                if count % 10000 == 0:
                                    report(' Import  ' + table, count, expected)
                    if batch:
                        with con:
                            con.executemany(sql, batch)
                        count += len(batch)
                    if count != expected:
                        raise ValueError(f'{table}  record count NOT consistent : expected  {expected}, collect to  {count}.')
                    report(' Completed  ' + table, count, expected)
                _validate_sqlite_network(con)
                con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        else:
            raise ValueError(' Select this application Export  SQLite  file or includes  manifest.json   JSONL.gz  folder .')
        checkpoint()
        stage.rename(target)
        _register_network(name, target, network_id, activate=activate,domain=domain,custom_options=custom_options)
        return network_id
    except BaseException:
        stage.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        for part in (str(stage)+'-wal', str(stage)+'-shm'):
            Path(part).unlink(missing_ok=True)
        raise


def _initial_active_database_path():
    return _registry_path_for(active_network_record())


DB_PATH = _initial_active_database_path()
try:
    _ACTIVE_RECORD=active_network_record()
    ACTIVE_DOMAIN_ID=_ACTIVE_RECORD.get('domain','mathematics')
    if ACTIVE_DOMAIN_ID not in DOMAIN_PROFILES:ACTIVE_DOMAIN_ID='general'
except Exception:
    ACTIVE_DOMAIN_ID='general'
WIKI_PAGE = "https://en.wikipedia.org/wiki/List_of_mathematical_theories"
# 4 GB VRAM: 2.5 GB quantized instruct model + room for KV cache.
# Do not run DeepSeek 14B (about 9 GB weights) on a 4 GB GPU.
DEFAULT_OLLAMA_MODEL = "qwen3:4b-instruct"
FALLBACK_OLLAMA_MODEL = "qwen2.5:3b"
# 4GB VRAM role assignment: mathematical author/reviser and rigorous reviewer
# use the stronger 4B model; a smaller instruction model prepares critiques.
# All inference is SERIALIZED by _OLLAMA_INFERENCE_GATE.
ROLE_MODELS = {
    'generator': 'qwen3:4b-instruct',
    'judge': 'qwen3:4b-instruct',
    'critic': 'qwen2.5:3b',
    'reviser': 'qwen3:4b-instruct',
}
MODEL_ALIASES = {'deepseek-r1:14b': DEFAULT_OLLAMA_MODEL,
                 'deepseek:14b': DEFAULT_OLLAMA_MODEL}

OPENALEX = "https://api.openalex.org/works"
CROSSREF = "https://api.crossref.org/works"
ARXIV_API = "https://export.arxiv.org/api/query"
LOCAL_CATALOG = DATA_DIR / "literature_catalog.sqlite3"
WIKI_API = "https://en.wikipedia.org/w/api.php"
# Read every Wikipedia footnote as a citation record, but cap how many
# *candidate papers* are resolved per theory to respect the configured cap.
MAX_WIKI_REFERENCE_WORKS = 1_000_000
OPENALEX_FIELDS = 'id,doi,display_name,publication_year,cited_by_count,abstract_inverted_index,best_oa_location,type'
MAX_THEORIES = 1_000_000
MAX_PAPERS_PER_THEORY = 1_000_000
MAX_WIKI_OFFSET = 999_999
# Skipping an offset must not consume the user-requested theory budget.
MAX_DISCOVERY_CANDIDATES = MAX_THEORIES + MAX_WIKI_OFFSET
# SQLite remains the source of truth; 3D overview is a bounded, interactive
# level of detail. A 1.5M-node, 7M-edge Matplotlib scene freezes Tk.
FAST_OVERVIEW_NODES = max(1000, min(25000, int(os.environ.get('BRAIN_OVERVIEW_NODES', '2200'))))
FAST_LOCAL_NODES = 900
FAST_DRAW_EDGES = 3500



def env_openalex_api_key():
    """Read the OpenAlex API key without writing it to logs or the database.

    The GUI preloads this value on startup. Users may override it by editing
    the masked API-key field; those edits are used by checks and collection.
    """
    return os.environ.get("OPENALEX_API_KEY", "").strip()

# Wikipedia discovery is about *mathematical knowledge*, not just article titles
# ending in "theory".  These are starting points, not a fixed list of 165 items:
# recursive Categorymembers exploration discovers additional methods and models.
# Interleave foundational and applied subjects so even a small run is diverse.
MATH_ENTRY_TOPICS = (
    'Graph theory', 'Engineering mathematics', 'Applied mathematics',
    'Mathematical statistics', 'Econometrics', 'Operations research',
    'Numerical analysis', 'Mathematical finance', 'Optimization (mathematics)',
    'Control theory', 'Probability theory', 'Statistical inference',
    'Regression analysis', 'Time series', 'Finite element method',
    'Signal processing', 'Linear programming', 'Bayesian inference',
    'Stochastic process', 'Actuarial science', 'Scientific computing',
    'Forecasting', 'Game theory', 'Decision theory', 'Partial differential equation',
    'Linear algebra', 'Monte Carlo method', 'Queueing theory',
    'Design of experiments', 'Optimal control', 'Markov chain',
    'Stochastic optimization', 'Wavelet transform', 'Spectral theory',
    'Numerical linear algebra', 'Information theory', 'Mathematical model',
    'Finite difference method', 'Finite volume method', 'Financial econometrics',
    'Inventory theory', 'Stochastic calculus', 'Kalman filter',
    'Simulation', 'Computational mathematics', 'Mathematical economics',
)
# Seed categories are queried individually via the public MediaWiki API.
# Unknown or empty categories are harmless; well-populated branches remain.
MATH_CATEGORIES = (
    'Category:Mathematical theories',
    'Category:Applied mathematics',
    'Category:Mathematics',
    'Category:Statistics',
    'Category:Numerical analysis',
    'Category:Econometrics',
    'Category:Operations research',
    'Category:Mathematical finance',
    'Category:Mathematical statistics',
    'Category:Optimization',
    'Category:Probability theory',
    'Category:Scientific computing',
    'Category:Computational mathematics',
    'Category:Control theory',
    'Category:Signal processing',
    'Category:Time series analysis',
    'Category:Statistical methods',
    'Category:Regression analysis',
    'Category:Machine learning',
    'Category:Stochastic processes',
    'Category:Actuarial science',
    'Category:Decision theory',
    'Category:Game theory',
    'Category:Mathematical economics',
    'Category:Numerical linear algebra',
    'Category:Linear algebra',
    'Category:Differential equations',
    'Category:Partial differential equations',
    'Category:Finite element method',
    'Category:Mathematical modeling',
    'Category:Applied statistics',
    'Category:Multivariate statistics',
    'Category:Bayesian statistics',
    'Category:Financial mathematics',
    'Category:Computational finance',
    'Category:Forecasting',
    'Category:Business analytics',
    'Category:Statistical inference',
    'Category:Experimental design',
    'Category:Queueing theory',
    'Category:Operations management',
    'Category:Risk analysis',
    'Category:Mathematical physics', 'Category:Mathematical biology',
    'Category:Mathematical epidemiology', 'Category:Biostatistics',
    'Category:Computational neuroscience', 'Category:Mathematical chemistry',
    'Category:Mathematical ecology', 'Category:Mathematical modelling in biology',
    'Category:Inverse problems', 'Category:Computational geometry',
    'Category:Cryptography', 'Category:Mathematical logic',
    'Category:Algebraic topology', 'Category:Algebraic geometry',
    'Category:Number theory', 'Category:Combinatorics',
    'Category:Mathematical optimization', 'Category:Geometric analysis',
    'Category:Statistical mechanics', 'Category:Mathematical sociology',
    'Category:Spatial statistics',
)
# Balanced pure/applied/math-in-other-fields discovery. These entries are verified
# against Wikipedia before entering the queue; labels are not invented nodes.
# The interleaving ensures that small automatic builds do not explore only
# the first (formerly economics/engineering-heavy) section of a seed list.
MATH_RESEARCH_AREAS = {
    'logic_foundations': ('Set theory','Mathematical logic','Model theory','Proof theory','Category theory'),
    'algebra': ('Linear algebra','Abstract algebra','Commutative algebra','Representation theory','Algebraic geometry'),
    'analysis': ('Real analysis','Complex analysis','Functional analysis','Measure theory','Harmonic analysis'),
    'geometry_topology': ('Differential geometry','Topology','Algebraic topology','Riemannian geometry','Geometric analysis'),
    'numbers_discrete': ('Number theory','Combinatorics','Graph theory','Discrete mathematics','Cryptography'),
    'probability_statistics': ('Probability theory','Mathematical statistics','Stochastic process','Bayesian inference','Statistical learning theory'),
    'pde_dynamics': ('Partial differential equation','Dynamical system','Calculus of variations','Ergodic theory','Optimal control'),
    'computation_optimization': ('Numerical analysis','Optimization (mathematics)','Numerical linear algebra','Inverse problem','Scientific computing'),
    'mathematical_physics': ('Mathematical physics','Statistical mechanics','Quantum mechanics','Fluid dynamics','General relativity'),
    'engineering_control': ('Control theory','Signal processing','System identification','Finite element method','Operations research'),
    'computer_ai': ('Information theory','Computational complexity theory','Machine learning','Computational geometry','Formal verification'),
    'financial_economics': ('Mathematical finance','Econometrics','Game theory','Actuarial science','Financial econometrics'),
    'biological_medical_math': ('Mathematical biology','Biostatistics','Computational neuroscience','Mathematical epidemiology','Population dynamics'),
    'environment_ecology': ('Climate model','Mathematical ecology','Geophysical fluid dynamics','Spatial statistics','Population ecology'),
    'social_network_math': ('Social choice theory','Network science','Mathematical sociology','Agent-based model','Queueing theory'),
    'chemical_material_math': ('Chemical kinetics','Mathematical chemistry','Reaction–diffusion system','Computational chemistry','Continuum mechanics'),
}

def mathematics_discovery_seeds():
    """Round-robin mathematical branches without claiming unverified pages."""
    groups=list(MATH_RESEARCH_AREAS.values())
    rows=[group[i] for i in range(max(map(len,groups))) for group in groups if i<len(group)]
    return tuple(dict.fromkeys(rows+list(MATH_ENTRY_TOPICS)))

# Subject tags do NOT assert mathematical truth or create cross-field edges.
# They record which application fields are explicitly mentioned by accepted papers.
MATH_APPLICATION_TAGS = {
    'physics': ('quantum','physics','mechanics','thermodynamics','relativity','photon','wave'),
    'engineering': ('control','robot','mechanical','electrical','signal','manufacturing','aerodynamics'),
    'computing_ai': ('machine learning','neural network','computer vision','algorithm','computational complexity','artificial intelligence'),
    'finance_economics': ('financial','finance','econometric','portfolio','option pricing','market','asset pricing','game theory'),
    'medicine_epidemiology': ('epidemiology','epidemic','infectious disease','biostatistic','clinical','patient','public health'),
    'biology_neuroscience': ('biological','ecolog','gene','protein','neuron','neuroscience','population dynamics','synaptic'),
    'environment_climate': ('climate','weather','geophysic','environment','hydrolog','ecolog'),
    'social_networks': ('social','sociolog','voting','network science','human behavior','urban'),
    'chemistry_materials': ('chemical','reaction diffusion','material','molecular dynamics','chemistry'),
}

def mathematical_application_tags(title, abstract=''):
    sample=(str(title or '')+' '+str(abstract or '')[:7000]).casefold()
    # Topic tags are metadata only, based on explicit textual evidence.
    return {area:next((word for word in words if re.search(
        r'(?<![a-z])'+re.escape(word)+r'(?![a-z])',sample)),None)
        for area,words in MATH_APPLICATION_TAGS.items() if any(re.search(
        r'(?<![a-z])'+re.escape(word)+r'(?![a-z])',sample) for word in words)}

# Guard against category graphs branching into biographies, geography,
# educational institutions and other non-methodological pages.
MATH_CATEGORY_EXCLUSIONS = (
    ' by country', ' by nationality', ' by continent', ' by region',
    ' by university', ' by year', ' by decade', ' by century',
    'mathematicians', 'statisticians', 'econometricians', 'scientists',
    'alumni', 'people', 'biographies', 'births', 'deaths', 'prizes',
    'awards', 'textbooks', 'books', 'journals', 'magazines', 'publications',
    'academic', 'societies', 'associations', 'organizations', 'companies',
    'universities', 'schools', 'institutes', 'education', 'history of',
    'competitions', 'olympiads', 'conferences', 'lists of', 'glossaries',
    'templates', 'wikipedia', 'stubs', 'works by', 'fictional', 'puzzles',
    'popular culture',
)
MATH_PAGE_EXCLUSIONS = re.compile(
    r'^(?:list of|lists of|index of|outline of|glossary of|timeline of|'
    r'history of|bibliography of|comparison of|mathematicians|'
    r'statisticians|category:|template:|portal:|wikipedia:)|'
    r'(?:\s*\((?:disambiguation|journal|magazine|company)\))$',
    re.IGNORECASE,
)


def math_page_title_ok(title):
    """Allow named methods/models/algorithms, not only *theory* articles."""
    title = str(title or '').strip()
    if not 3 <= len(title) <= 140 or MATH_PAGE_EXCLUSIONS.search(title):
        return False
    if ':' in title and title.split(':', 1)[0].casefold() in (
            'category', 'portal', 'file', 'help', 'template', 'user', 'wikipedia'):
        return False
    return True


def math_category_ok(category):
    name = category.casefold().removeprefix('category:')
    exclusions=(MATH_CATEGORY_EXCLUSIONS if active_domain()=='mathematics' else
        (' by country',' by nationality',' by year',' births',' deaths',
         ' celebrities',' fictional',' stubs',' wikipedia',' by decade'))
    return not any(term in name for term in exclusions)


def wikipedia_article_url(title):
    return 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(
        title.replace(' ', '_'), safe='()_-')
USER_AGENT = "BrainProjectResearch/2.0 (educational local desktop application; Python requests)"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json, application/atom+xml, application/xml, text/html, application/pdf"}
STOP = set(ENGLISH_STOP_WORDS) | {
    "study", "studies", "paper", "article", "results", "result", "using", "used",
    "approach", "method", "methods", "new", "based", "provide", "present", "propose",
    "show", "shown", "consider", "case", "cases", "recent", "work", "works",
    "research", "given", "general", "particular", "different",
    "obtained", "discuss", "introduction", "section",
    "abstract", "conclusion", "investigates", "investigate", "investigated",
    "consisting", "consists", "includes", "include", "including",
    "involves", "involve", "establishes", "establish", "derive", "derives",
    "demonstrates", "demonstrate", "utilize", "utilizes", "use", "uses",
}
# Purely lexical math vocabulary. These are normalization/aliases, not
# semantic vectors and not assertions that different mathematical ideas equal.
_IRREGULAR = {'matrices':'matrix','indices':'index','analyses':'analysis',
    'hypotheses':'hypothesis','series':'series','data':'data','vertices':'vertex',
    'axes':'axis','bases':'basis','statistics':'statistics','calculus':'calculus'}
_ALIASES = {
    'partial differentiation':'partial derivative',
    'partial derivatives':'partial derivative',
    'partial derivative':'partial derivative',
    'pde':'partial differential equation',
    'pdes':'partial differential equation',
    'partial differential equations':'partial differential equation',
    'ode':'ordinary differential equation',
    'odes':'ordinary differential equation',
    'ordinary differential equations':'ordinary differential equation',
    'fourier transforms':'fourier transform',
    'fourier analysis':'fourier transform',
    'laplacian operator':'laplacian',
    'gradient vector':'gradient',
    'eigenvectors':'eigenvector',
    'eigenvalues':'eigenvalue',
    'stochastic processes':'stochastic process',
    'regression models':'regression model',
}
_LEX_STOP = set(STOP) | {'the','with','into','from','than','where','whose',
                          'when','while','among','between','these','those'}

def _lemma(word):
    word = word.casefold()
    if word in _IRREGULAR: return _IRREGULAR[word]
    if len(word)>5 and word.endswith('ies'): return word[:-3]+'y'
    if len(word)>5 and word.endswith('sses'): return word[:-2]
    if len(word)>4 and word.endswith('s') and not word.endswith(('ss','us','is')):
        return word[:-1]
    return word

def canonical_phrase(text):
    text=unicodedata.normalize('NFKC',str(text or '')).casefold()
    text=text.replace('∂',' partial derivative ').replace('∇',' nabla ')
    text=re.sub(r'[^a-z0-9\u3400-\u9fff]+',' ',text).strip()
    if text in _ALIASES:
        text=_ALIASES[text]
    parts=[_lemma(x) for x in text.split()]
    normalized=' '.join(parts)
    return _ALIASES.get(normalized, normalized)

def lexical_tokens(text):
    return tuple(dict.fromkeys(x for x in canonical_phrase(text).split()
                               if len(x)>1 and x not in _LEX_STOP))

def index_unit(con, uid, label):
    terms=lexical_tokens(label)
    if terms:
        con.executemany('INSERT OR IGNORE INTO unit_terms(unit_id,token) VALUES(?,?)',
                        [(uid,t) for t in terms])

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]*")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


_DB_SCHEMA_LOCK = threading.RLock()
_DB_SCHEMA_READY = set()

def database(path=None) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dbfile = Path(path) if path is not None else DB_PATH
    dbfile.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(dbfile), timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    # A bounded cache prevents repeated disk seeks for indexed local traversals.
    # 16 MiB per connection also keeps eight collector workers memory-conscious.
    con.execute("PRAGMA cache_size=-16384")
    # CREATE TABLE / index migration must never race across worker threads.
    # Once initialized, opening a connection performs no DDL at all.
    with _DB_SCHEMA_LOCK:
        key = str(dbfile.resolve())
        if key not in _DB_SCHEMA_READY:
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript("""
            CREATE TABLE IF NOT EXISTS theories(
                name TEXT PRIMARY KEY, url TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS wikipedia_references(
                theory TEXT NOT NULL,
                reference_key TEXT NOT NULL,
                citation_text TEXT NOT NULL,
                doi TEXT NOT NULL DEFAULT '',
                arxiv_id TEXT NOT NULL DEFAULT '',
                paper_title TEXT NOT NULL DEFAULT '',
                reference_url TEXT NOT NULL DEFAULT '',
                work_id TEXT NOT NULL DEFAULT '',
                read_level TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'found',
                error TEXT NOT NULL DEFAULT '',
                updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(theory,reference_key)
            );
            CREATE INDEX IF NOT EXISTS idx_wiki_references_status ON wikipedia_references(status,theory);
            CREATE INDEX IF NOT EXISTS idx_wiki_references_work ON wikipedia_references(work_id);
            CREATE TABLE IF NOT EXISTS wikipedia_reference_scans(
                theory TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                processed INTEGER NOT NULL DEFAULT 0,
                added INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                updated TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS papers(
                id TEXT PRIMARY KEY, title TEXT NOT NULL, year INTEGER, citations INTEGER,
                doi TEXT, url TEXT, abstract TEXT, summary TEXT, fulltext_used INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS paper_theories(
                paper_id TEXT, theory TEXT, score REAL,
                PRIMARY KEY(paper_id,theory)
            );
            CREATE TABLE IF NOT EXISTS paper_math_applications(
                paper_id TEXT NOT NULL, area TEXT NOT NULL, evidence TEXT NOT NULL,
                PRIMARY KEY(paper_id,area)
            );
            CREATE INDEX IF NOT EXISTS idx_paper_math_application_area
                ON paper_math_applications(area,paper_id);
            CREATE TABLE IF NOT EXISTS paper_quality_decisions(
                theory TEXT NOT NULL, paper_id TEXT NOT NULL,
                state TEXT NOT NULL, confidence REAL NOT NULL,
                reason TEXT NOT NULL, updated TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(theory,paper_id)
            );
            CREATE INDEX IF NOT EXISTS idx_quality_decision_state
                ON paper_quality_decisions(state);
            CREATE TABLE IF NOT EXISTS unit_quality_audit(
                unit_id TEXT PRIMARY KEY, state TEXT NOT NULL,
                reason TEXT NOT NULL, updated TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS unit_purity_scores(
                unit_id TEXT PRIMARY KEY, score INTEGER NOT NULL,
                reason TEXT NOT NULL, updated TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS purity_rejection_summary(
                label TEXT NOT NULL, reason TEXT NOT NULL,
                rejected_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(label,reason)
            );
            CREATE TABLE IF NOT EXISTS purity_metrics(
                key TEXT PRIMARY KEY, value INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS purity_prune_queue(
                unit_id TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS purity_deleted_log(
                unit_id TEXT PRIMARY KEY, label TEXT NOT NULL,
                kind TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
                source_url TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT 'obvious_lexical_noise',
                deleted_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_paper_theories_by_theory ON paper_theories(theory);
            CREATE TABLE IF NOT EXISTS theory_progress(
                name TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'running',
                found INTEGER NOT NULL DEFAULT 0,
                processed INTEGER NOT NULL DEFAULT 0,
                newly_linked INTEGER NOT NULL DEFAULT 0,
                failures INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS openalex_failures(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theory TEXT NOT NULL,
                page INTEGER NOT NULL,
                category TEXT NOT NULL,
                status INTEGER,
                reason TEXT NOT NULL,
                created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_openalex_failures_theory ON openalex_failures(theory,id);
            CREATE TABLE IF NOT EXISTS units(
                id TEXT PRIMARY KEY, label TEXT, kind TEXT, description TEXT, url TEXT,
                citations INTEGER DEFAULT 0, support INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS mentions(
                unit_id TEXT, paper_id TEXT, quote TEXT,
                PRIMARY KEY(unit_id,paper_id)
            );
            CREATE TABLE IF NOT EXISTS edges(
                src TEXT, dst TEXT, kind TEXT, weight REAL, support INTEGER DEFAULT 1,
                PRIMARY KEY(src,dst,kind)
            );
            CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
            CREATE INDEX IF NOT EXISTS idx_units_kind_support ON units(kind,support);
            CREATE INDEX IF NOT EXISTS idx_mentions_unit ON mentions(unit_id);
            CREATE TABLE IF NOT EXISTS build_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                unit_id TEXT,
                src TEXT,
                dst TEXT,
                edge_kind TEXT,
                delta REAL DEFAULT 0,
                label TEXT,
                created TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_build_events_action ON build_events(action,id);
            CREATE INDEX IF NOT EXISTS idx_build_events_node ON build_events(unit_id,id);
            CREATE TABLE IF NOT EXISTS association_runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                paths_json TEXT NOT NULL,
                problem TEXT NOT NULL DEFAULT '',
               model TEXT NOT NULL DEFAULT '',
                created TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS positions(
                unit_id TEXT PRIMARY KEY,
                x REAL NOT NULL, y REAL NOT NULL, z REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS relation_evidence(
                relation_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                sentence TEXT NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(relation_id,source_id,sentence)
            );
            CREATE INDEX IF NOT EXISTS idx_relation_evidence_id ON relation_evidence(relation_id);
            CREATE TABLE IF NOT EXISTS association_context(
                run_id INTEGER PRIMARY KEY,
                context_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS unit_terms(
                unit_id TEXT NOT NULL, token TEXT NOT NULL,
                PRIMARY KEY(unit_id,token)
            );
            CREATE INDEX IF NOT EXISTS idx_unit_terms_token ON unit_terms(token,unit_id);
            CREATE TABLE IF NOT EXISTS network_meta(
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS question_sets(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                topic TEXT NOT NULL DEFAULT '',
                created TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_question_sets_run ON question_sets(run_id);
            CREATE TABLE IF NOT EXISTS question_candidates(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                version INTEGER NOT NULL,
                content_json TEXT NOT NULL,
               model TEXT NOT NULL,
                current INTEGER NOT NULL DEFAULT 1,
                created TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(set_id,slot,version)
            );
            CREATE INDEX IF NOT EXISTS idx_question_current ON question_candidates(set_id,current,slot);
            CREATE TABLE IF NOT EXISTS question_feedback(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                role TEXT NOT NULL,
               model TEXT NOT NULL DEFAULT '',
                score INTEGER,
                comment TEXT NOT NULL DEFAULT '',
                rubric_json TEXT NOT NULL DEFAULT '{}',
                created TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_question_feedback ON question_feedback(candidate_id,role,id);
            """)
            # Upgrade a malformed legacy model-column translation in-place.
            # Never rebuild a user database or delete any candidate/version.
            for _table in ('association_runs', 'question_candidates', 'question_feedback'):
                _cols = {row[1] for row in con.execute(f'PRAGMA table_info("{_table}")')}
                if 'model' not in _cols:
                    con.execute(f"ALTER TABLE \"{_table}\" ADD COLUMN model TEXT NOT NULL DEFAULT ''")
            con.commit()
            # Do not expose draft questions until every requested question is reviewed.
            # Existing sets remain hidden until their review is explicitly resumed.
            set_columns={row[1] for row in con.execute('PRAGMA table_info(question_sets)')}
            if 'pipeline_status' not in set_columns:
                con.execute("ALTER TABLE question_sets ADD COLUMN pipeline_status TEXT NOT NULL DEFAULT 'draft'")
                con.commit()
            # Review rounds are chosen AFTER all requested drafts exist. Persist
            # that choice to make reopening and resuming unambiguous.
            if 'review_round_limit' not in set_columns:
                con.execute('ALTER TABLE question_sets ADD COLUMN review_round_limit INTEGER')
                con.commit()
            # Legacy question sets contained ten questions. New sets persist an
            # independent 1..20 target so interrupted jobs resume correctly.
            if 'question_count' not in set_columns:
                con.execute('ALTER TABLE question_sets '
                            'ADD COLUMN question_count INTEGER NOT NULL DEFAULT 10')
                con.commit()
            # v5.1: preserve matched seeds so diagnostics survive restarting the app.
            cols = {row[1] for row in con.execute('PRAGMA table_info(association_runs)')}
            if 'matches_json' not in cols:
                con.execute("ALTER TABLE association_runs ADD COLUMN matches_json TEXT NOT NULL DEFAULT '[]'")
                con.commit()
            # Never materialize millions of legacy nodes/edges in Python RAM.
            # Portable imports intentionally lack build_events: do not fabricate
            # an 8M-event history just to load their stored graph.
            event_skip = con.execute("SELECT value FROM network_meta WHERE key='skip_legacy_event_migration'").fetchone()
            if (not event_skip and
                    con.execute("SELECT 1 FROM build_events LIMIT 1").fetchone() is None and
                    con.execute("SELECT 1 FROM units LIMIT 1").fetchone()):
                sample=con.execute('SELECT id FROM units LIMIT 10001').fetchall()
                if len(sample) > 10000:
                    with con:
                        con.execute("INSERT OR REPLACE INTO network_meta(key,value) "
                                    "VALUES('skip_legacy_event_migration','1')")
                else:
                    with con:
                        for uid, label in con.execute("SELECT id,label FROM units ORDER BY rowid"):
                            con.execute("INSERT INTO build_events(action,unit_id,label) VALUES('node',?,?)",
                                        (uid, label))
                        for a,b,k,w in con.execute("SELECT src,dst,kind,weight FROM edges ORDER BY rowid"):
                            con.execute("INSERT INTO build_events(action,src,dst,edge_kind,delta,label) "
                                        "VALUES('edge',?,?,?,?,?)",(a,b,k,w,' legacy data Link ( transfer )'))
            _DB_SCHEMA_READY.add(key)
    abc_schema(con)  # persistent, independently versioned associative memory tables
    return con



# ---------------------------------------------------------------------------
# Portable network export (does not materialize millions of nodes in RAM).
# The independent, schema-versioned JSONL files can be read by any language.
# A full SQLite snapshot is offered separately to preserve *all* app state.
# ---------------------------------------------------------------------------
EXPORT_CORE_TABLES = ('units', 'edges', 'positions', 'network_meta',
                      'abc_units','abc_edges','abc_ssrs','abc_meta',
                       'abc_sources','abc_source_topics','abc_topics','abc_positions')
EXPORT_PROVENANCE_TABLES = (
    'theories', 'papers', 'paper_theories', 'paper_math_applications', 'mentions', 'relation_evidence',
    'unit_terms', 'wikipedia_references', 'wikipedia_reference_scans',
    'theory_progress', 'paper_quality_decisions', 'unit_quality_audit',
    'unit_purity_scores', 'purity_rejection_summary', 'purity_metrics',
    'purity_prune_queue', 'purity_deleted_log',
    'abc_evidence','abc_learning_events','abc_runs','abc_pulse_events','abc_feedback',
    'abc_sources','abc_source_topics','abc_topics','abc_positions','flin_source_depth',
    'abc_input_clusters','abc_cluster_features','abc_cluster_links','abc_replay_queue',
    'flin_patterns','flin_pattern_evidence','flin_shortcut_members','flin_cost_decisions',
    'flin_ingest_diagnostics',
)


class NetworkExportCancelled(Exception):
    """Raised for a user-cancelled export; partial output is removed."""


def _export_checkpoint(stop_event):
    if stop_event is not None and stop_event.is_set():
        raise NetworkExportCancelled(' Export already cancel ; not yet Completed temporary store Data already clear .')


def _read_only_database(path=None):
    source_path = Path(path) if path is not None else DB_PATH
    if not source_path.is_file():
        raise FileNotFoundError(' cannot find existing Memory unit Database :' + str(source_path))
    uri = source_path.resolve().as_uri() + '?mode=ro'
    con = sqlite3.connect(uri, uri=True, timeout=30)
    con.execute('PRAGMA busy_timeout=30000')
    con.execute('PRAGMA query_only=ON')
    return con


def flin_export_counts(con):
    """Exact graph counts; the active FLIN graph is abc_*, NOT legacy units/edges.

    Reads a single SQLite connection/snapshot. No rendering or sample LIMIT.
    """
    names = {name for (name,) in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    needed = {'abc_units', 'abc_edges'}
    if not needed.issubset(names):
        raise RuntimeError('FLIN associative graph tables are missing: ' +
                           ', '.join(sorted(needed - names)))
    values = {
        'flin_units_all': int(con.execute('SELECT COUNT(*) FROM abc_units').fetchone()[0]),
        'flin_units_active': int(con.execute(
            "SELECT COUNT(*) FROM abc_units WHERE status='active'").fetchone()[0]),
        'flin_edges_all': int(con.execute('SELECT COUNT(*) FROM abc_edges').fetchone()[0]),
    }
    values['flin_units_other'] = values['flin_units_all'] - values['flin_units_active']
    for table in ('units', 'edges'):
        values['legacy_' + table] = (int(con.execute(
            f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) if table in names else None)
    return values


def _verify_sqlite_graph_file(path, expected, *, mirror=False):
    """Fail closed if a completed SQLite export has lost even one unit/link."""
    path = Path(path)
    with contextlib.closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as con:
        check = con.execute('PRAGMA quick_check').fetchone()
        if not check or check[0] != 'ok':
            raise RuntimeError('SQLite integrity check failed: ' + str(check))
        if mirror:
            actual = {
                'flin_units_all': int(con.execute('SELECT COUNT(*) FROM units').fetchone()[0]),
                'flin_units_active': int(con.execute(
                    "SELECT COUNT(*) FROM units WHERE status='active'").fetchone()[0]),
                'flin_edges_all': int(con.execute('SELECT COUNT(*) FROM edges').fetchone()[0]),
            }
        else:
            actual = flin_export_counts(con)
        for key in ('flin_units_all', 'flin_units_active', 'flin_edges_all'):
            if actual[key] != expected[key]:
                raise RuntimeError(f'Incomplete FLIN export: {key}: '
                                   f'expected {expected[key]:,}, found {actual[key]:,}')
        return actual


def _make_flin_graph_sqlite(full_snapshot, output_path, expected, *, stop_event=None,
                            progress=None):
    """Create a standalone FULL FLIN graph for ordinary SQLite graph readers.

    This is an *analysis copy*, not the restorable full application backup.
    The original full backup, including legacy tables and all provenance, is
    separately preserved unchanged as association.sqlite3.
    """
    output_path = Path(output_path)
    with contextlib.closing(sqlite3.connect(Path(full_snapshot).as_uri() + '?mode=ro',
                                           uri=True)) as src:
        with contextlib.closing(sqlite3.connect(str(output_path))) as dst:
            dst.execute('PRAGMA journal_mode=DELETE')
            dst.executescript("""
                CREATE TABLE units (
                    id TEXT PRIMARY KEY, label TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT 'concept',
                    description TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '',
                    citations INTEGER NOT NULL DEFAULT 0, support INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL, quality INTEGER NOT NULL,
                    evidence_count INTEGER NOT NULL, created TEXT
                );
                CREATE TABLE edges (
                    src TEXT NOT NULL, dst TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT 'association',
                    weight REAL NOT NULL, support INTEGER NOT NULL,
                    observations INTEGER NOT NULL,
                    PRIMARY KEY(src,dst,kind)
                );
                CREATE TABLE export_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            def transfer(query, insert, label):
                cursor = src.execute(query)
                size = 0
                while True:
                    _export_checkpoint(stop_event)
                    batch = cursor.fetchmany(4000)
                    if not batch:
                        break
                    with dst:
                        dst.executemany(insert, batch)
                    size += len(batch)
                    if progress:
                        progress('FLIN graph ' + label, size, expected['flin_' + label + '_all'])
                return size
            nodes = transfer("""SELECT id,label,'concept',definition,'',0,
                            evidence_count,status,quality,evidence_count,created
                            FROM abc_units""",
                            """INSERT INTO units(id,label,kind,description,url,citations,
                                support,status,quality,evidence_count,created)
                                VALUES(?,?,?,?,?,?,?,?,?,?,?)""", 'units')
            edges = transfer("""SELECT src,dst,'association',weight,observations,observations
                            FROM abc_edges""",
                            """INSERT INTO edges(src,dst,kind,weight,support,observations)
                                VALUES(?,?,?,?,?,?)""", 'edges')
            if nodes != expected['flin_units_all'] or edges != expected['flin_edges_all']:
                raise RuntimeError('FLIN graph transfer did not copy all associative records.')
            with dst:
                dst.executemany('INSERT INTO export_metadata(key,value) VALUES(?,?)',
                    [('graph_source_units','abc_units'),('graph_source_edges','abc_edges'),
                     ('source_format','FLIN association network'),
                     ('purpose','standalone graph analysis; use association.sqlite3 to restore FLIN'),
                     ('source_snapshot', 'association.sqlite3'),
                     ('counts_json',json.dumps(expected,sort_keys=True))])
                dst.execute('CREATE INDEX idx_flin_edges_src ON edges(src)')
                dst.execute('CREATE INDEX idx_flin_edges_dst ON edges(dst)')
                dst.execute('CREATE INDEX idx_flin_units_status ON units(status)')
    return _verify_sqlite_graph_file(output_path, expected, mirror=True)


def _write_flin_export_report(directory, counts, mode, *, files=None, source_db=None):
    payload = {
        'format': 'FLIN complete export verification v1',
        'mode': mode,
        'source_database': str(source_db) if source_db is not None else None,
        'source_of_truth': {'units':'abc_units','edges':'abc_edges'},
        'counts': counts,
        'files': files or [],
        'verified': True,
        'notes': ('FLIN active units are abc_units rows with status=active; '
                  'all FLIN units include candidates. FLIN links are abc_edges. '
                  'Legacy units/edges are separate research/provenance structures. '
                  'Counts describe a point-in-time SQLite snapshot.'),
    }
    (Path(directory) / 'FLIN_EXPORT_VERIFICATION.json').write_text(
        json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    return payload


def _safe_export_destination(parent_dir, prefix='brain_network'):
    root = Path(parent_dir).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(' Export items NOT is folder :' + str(root))
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    name = f'{prefix}_{stamp}'
    candidate = root / name
    i = 1
    while candidate.exists():
        candidate = root / f'{name}_{i:02d}'
        i += 1
    # Staging is in the same filesystem, so final rename is atomic.
    staging = root / ('.' + candidate.name + '.partial_' + uuid.uuid4().hex[:8])
    return staging, candidate


def _export_readme():
    return """Brain_Project Portable Memory Network /  can portable associative network 
=========================================================
FORMAT: Brain_Project portable directed graph, schema_version=1
IMPORTANT: FLIN ASSOCIATIVE NETWORK = abc_units.jsonl.gz / abc_edges.jsonl.gz.
The separate units.jsonl.gz / edges.jsonl.gz describe the LEGACY graph.
See FLIN_EXPORT_VERIFICATION.json for exact FLIN node/edge counts.
ENCODING: UTF-8, JSON Lines, gzip compression (*.jsonl.gz)

Core files:
  units.jsonl.gz: one JSON object per memory node; `id` is its unique key.
  edges.jsonl.gz: one JSON object per independent DIRECTED edge.
    `src` -> `dst`; `kind` distinguishes edges between the same pair.
    `weight` is link strength; `support` is the observation count.
  positions.jsonl.gz: optional 3D x/y/z layout coordinates.
  network_meta.jsonl.gz: network metadata, if present.

Additional optional files: papers, theories, mentions, paper_theories,
paper_math_applications (explicit application-field source tags),
relation_evidence, unit_terms and Wikipedia citation references/progress.
The fields in each object are the original SQLite column names and data
values (null stays null). See manifest.json for exact columns and row totals.
A paper's abstract or extracted relation's source sentence is EVIDENCE,
not verified proof. Edges do not imply validated causal or logical relations.

Python example:
    import gzip, json
    from pathlib import Path
    root = Path('PATH_TO_THIS_DIRECTORY')
    with gzip.open(root / 'units.jsonl.gz', 'rt', encoding='utf-8') as stream:
        for line in stream:
            node = json.loads(line)
            print(node['id'], node['label'])
            break
    with gzip.open(root / 'edges.jsonl.gz', 'rt', encoding='utf-8') as stream:
        for line in stream:
            edge = json.loads(line)
            print(edge['src'], edge['dst'], edge['weight'])
            break

For tens of millions of rows, iterate over gzip streams, do not call list().
For a FULL archival backup (including question/feedback/build histories),
use the separate SQLite snapshot export option instead.
"""


def export_memory_network(parent_dir, mode='portable', with_sources=True,
                          stop_event=None, progress=None, source_db_path=None):
    """Consistently export the complete stored graph without loading it into RAM.

    Output is a new directory inside parent_dir. Supports:
      portable: streaming gzip JSON Lines with manifest.json + README.txt
      sqlite: SQLite online backup (preserves questions, logs and every table)
    Returns the final output directory. Callback receives (stage, rows, total).
    """
    source_db_path = Path(source_db_path or DB_PATH).expanduser().resolve()
    if mode not in ('portable', 'sqlite'):
        raise ValueError(' NOT support Export format :' + str(mode))
    _export_checkpoint(stop_event)
    stage_dir, final_dir = _safe_export_destination(parent_dir)
    stage_dir.mkdir(mode=0o700)
    def report(stage, done, total):
        if progress is not None:
            progress(stage, done, total)
    try:
        if mode == 'sqlite':
            report('Create complete SQLite snapshot (including all FLIN tables)', 0, 0)
            snapshot = stage_dir / 'association.sqlite3'
            with contextlib.closing(_read_only_database(source_db_path)) as src:
                with contextlib.closing(sqlite3.connect(str(snapshot))) as dst:
                    def on_backup(status, remaining, total):
                        _export_checkpoint(stop_event)
                        report('Backing up SQLite database pages', total-remaining, total)
                    src.backup(dst, pages=512, progress=on_backup, sleep=0.05)
            _export_checkpoint(stop_event)
            # The source database uses WAL. A copied WAL-mode database may spawn
            # -wal/-shm sidecars when opened for verification. Convert ONLY the
            # exported snapshot to DELETE journal mode so association.sqlite3 is
            # independently portable as a single file. Do not touch the live DB.
            report('Finalizing portable standalone SQLite snapshot', 0, 0)
            with contextlib.closing(sqlite3.connect(str(snapshot), timeout=30)) as exported:
                exported.execute('PRAGMA wal_checkpoint(TRUNCATE)')
                journal_mode = exported.execute('PRAGMA journal_mode=DELETE').fetchone()[0]
                if journal_mode.lower() != 'delete':
                    raise RuntimeError('Failed to finalize standalone SQLite snapshot: ' + str(journal_mode))
            for extension in ('-wal', '-shm'):
                sidecar = Path(str(snapshot) + extension)
                if sidecar.exists():
                    if extension == '-wal' and sidecar.stat().st_size != 0:
                        raise RuntimeError('Exported SQLite WAL is not empty after finalization; aborting export.')
                    sidecar.unlink()
            _export_checkpoint(stop_event)
            # Verify the *exported snapshot*, not a concurrently changing live DB.
            with contextlib.closing(sqlite3.connect(snapshot.as_uri() + '?mode=ro',
                                                    uri=True)) as snapshot_con:
                counts = flin_export_counts(snapshot_con)
            _verify_sqlite_graph_file(snapshot, counts)
            report('Export FLIN associative graph (not legacy tables)', 0,
                   counts['flin_units_all'] + counts['flin_edges_all'])
            _make_flin_graph_sqlite(snapshot, stage_dir / 'flin_graph.sqlite3', counts,
                                    stop_event=stop_event, progress=report)
            _export_checkpoint(stop_event)
            _write_flin_export_report(stage_dir, counts, 'sqlite',
                 files=['association.sqlite3', 'flin_graph.sqlite3'],source_db=source_db_path)
            (stage_dir / 'README.txt').write_text(
                'FLIN complete verified SQLite export\n'
                '====================================\n'
                'flin_graph.sqlite3: FLIN ASSOCIATIVE MEMORY NETWORK.\n'
                '  Its units table represents ALL abc_units (including inactive candidates),\n'
                '  and edges represents ALL directed abc_edges.\n'
                '  Filter units.status=active for triggerable memories.\n'
                '  This is the file to open in external SQLite/network analysis tools.\n\n'
                'association.sqlite3: COMPLETE APPLICATION BACKUP.\n'
                '  It preserves ALL original application tables, events, documents,\n'
                '  historical legacy units/edges, and FLIN abc_units/abc_edges.\n'
                '  This is the file to import into FLIN to restore the network.\n\n'
                'FLIN_EXPORT_VERIFICATION.json: exact counts independently verified\n'
                'against the exported snapshot and FLIN graph analysis copy.\n'
                '3D render sampling is NEVER applied to either SQLite file.\n',
                encoding='utf-8')
            report('Verified complete FLIN snapshot and graph',
                   counts['flin_units_all'] + counts['flin_edges_all'],
                   counts['flin_units_all'] + counts['flin_edges_all'])
        else:
            metadata = {
                'format': 'brain-project-directed-memory-network',
                'schema_version': 1,
                'exported_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'mode': 'portable-jsonl-gzip',
                'all_nodes_exported': True,
                'all_edges_exported': True,
                'direction': 'directed',
                'domain': active_domain(),
                'domain_label': domain_name(),
                'domain_custom_options':{k:active_network_record().get(k,[]) for k in
                   ('custom_entries','custom_categories','custom_keywords')} if active_domain()=='custom' else {},
                'with_sources': bool(with_sources),
                'notes': ('Complete SQLite units and edges are exported. '
                          'Visual overview sampling does not apply.'),
                'tables': {},
            }
            with contextlib.closing(_read_only_database(source_db_path)) as con:
                # Keep one logical point-in-time view while reading every table.
                con.execute('BEGIN')
                names = {r[0] for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                tables = EXPORT_CORE_TABLES + (EXPORT_PROVENANCE_TABLES if with_sources else ())
                tables = [name for name in tables if name in names]
                core_totals = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                               for t in ('abc_units','abc_edges') if t in names}
                counts = flin_export_counts(con)
                expected = sum(core_totals.values())
                core_progress = 0
                for tablename in tables:
                    _export_checkpoint(stop_event)
                    filename = tablename + '.jsonl.gz'
                    n = 0
                    cursor = con.execute(f'SELECT * FROM "{tablename}"')
                    columns = [col[0] for col in cursor.description]
                    report(' Export  ' + tablename, core_progress, expected)
                    with gzip.open(stage_dir / filename, 'wt', encoding='utf-8',
                                   compresslevel=4) as fout:
                        while True:
                            _export_checkpoint(stop_event)
                            rows = cursor.fetchmany(1500)
                            if not rows:
                                break
                            fout.write(''.join(json.dumps(dict(zip(columns, row)),
                                                ensure_ascii=False, separators=(',', ':'),
                                                default=str) + '\n' for row in rows))
                            n += len(rows)
                            if tablename in core_totals:
                                core_progress += len(rows)
                            if n % 15000 < len(rows):
                                report(' Export  '+ tablename + f'({n:,}  records )', core_progress, expected)
                    metadata['tables'][tablename] = {
                        'file': filename, 'rows': n, 'columns': columns,
                        'bytes': (stage_dir / filename).stat().st_size,
                    }
                    report(' Completed  ' + tablename + f'({n:,}  records )',core_progress, expected)
                con.rollback()
            for key, tablename in (('flin_units_all','abc_units'), ('flin_edges_all','abc_edges')):
                written = metadata['tables'].get(tablename, {}).get('rows')
                if written != counts[key]:
                    raise RuntimeError(f'Incomplete portable FLIN export: {tablename}: '
                                       f'expected {counts[key]:,}, wrote {written!r}')
            metadata['flin_graph_counts'] = counts
            metadata['primary_graph_tables'] = {'units':'abc_units','edges':'abc_edges'}
            _write_flin_export_report(stage_dir, counts, 'portable',
                                      files=['abc_units.jsonl.gz','abc_edges.jsonl.gz'],source_db=source_db_path)
            _export_checkpoint(stop_event)
            (stage_dir / 'manifest.json').write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
            (stage_dir / 'README.txt').write_text(_export_readme(), encoding='utf-8')
        _export_checkpoint(stop_event)
        stage_dir.rename(final_dir)
        report(' Completed ', 1, 1)
        return final_dir
    except BaseException:
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise


def get_json(session, url, params=None, tries=3):
    for i in range(tries):
        try:
            r = session.get(url, params=params, timeout=(8, 30), headers=HEADERS)
            if r.status_code in (429, 500, 502, 503, 504):
                retry = min(8, 2 ** i + 1)
                if i + 1 < tries:
                    time.sleep(retry)
                    continue
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if i + 1 >= tries:
                raise
            time.sleep(1 + i)
    raise RuntimeError("API request failed")


def discover_theories(session, cap=100, stop_event=None, log=None, on_found=None):
    """Stream mathematical subjects from diverse Wikipedia categories.

    Page titles need not contain the word "theory".  A discovered subject is
    handed off to `on_found` immediately, even while categories are still being
    explored.  Categorymembers paging uses MediaWiki's official `continue`.

    Requested count is an upper bound, never a claim that N articles exist.
    """
    cap = max(1, min(MAX_DISCOVERY_CANDIDATES, int(cap)))
    profile=domain_profile()
    seeds=mathematics_discovery_seeds()
    categories_seed=MATH_CATEGORIES
    found, seen = [], set()
    def stopped():
        return stop_event is not None and stop_event.is_set()

    def add(title, href):
        if stopped():
            return False
        title = str(title or '').strip()
        if not math_page_title_ok(title):
            return False
        key = title.casefold().replace('_', ' ')
        if key in seen or len(found) >= cap:
            return False
        parsed = urllib.parse.urlsplit(href)
        if parsed.netloc != 'en.wikipedia.org' or not parsed.path.startswith('/wiki/'):
            return False
        seen.add(key)
        index = len(found)
        found.append((title, href))
        if on_found is not None:
            on_found(title, href, index)
        return True

    # Verify independently in chunks (MediaWiki non-bot clients typically
    # allow 50 titles/request). Stream confirmed seeds to topic workers early.
    for chunk_start in range(0,len(seeds),40):
        if stopped() or len(found)>=cap:break
        batch=seeds[chunk_start:chunk_start+40]
        try:
            initial=get_json(session,WIKI_API,{
                'action':'query','format':'json','formatversion':2,
                'prop':'info','redirects':1,'titles':'|'.join(batch),
            },tries=2)
            if 'error' in initial:raise RuntimeError(str(initial['error'])[:160])
            q=initial.get('query',{})
            pages=q.get('pages')
            if not isinstance(pages,list):raise RuntimeError('Wikipedia  response missing  pages')
            aliases={x['from'].casefold():x['to'] for group in ('normalized','redirects')
                     for x in q.get(group,[]) if x.get('from') and x.get('to')}
            existing={p['title'].casefold():p['title'] for p in pages
                      if p.get('title') and 'missing' not in p and
                      not p.get('invalid') and p.get('ns',0)==0}
            for title in batch:
                target=title
                for _ in range(4):
                    nxt=aliases.get(target.casefold())
                    if not nxt or nxt==target:break
                    target=nxt
                canonical=existing.get(target.casefold())
                if canonical:add(canonical,wikipedia_article_url(canonical))
        except Exception as ex:
            if log:log(f'⚠ Wikipedia  Mathematics initial Topic batch imes  {chunk_start//40+1}  Validate Failed :{ex}')
    if log:log(f'Wikipedia  already Validate  {len(found)}  items cross Mathematical branches initial Topic , resume Discover Mathematics category .')

    # Preserve compatibility with the Wikipedia theory list, including titles
    # without the word "theory".  HTML may fail; the category API still works.
    try:
        if active_domain()=='mathematics' and not stopped() and len(found) < cap:
            r = session.get(WIKI_PAGE, headers=HEADERS, timeout=(8, 30))
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            main = (soup.select_one('#mw-content-text .mw-parser-output')
                    or soup.select_one('#mw-content-text') or soup)
            for a in main.select('ul li a[href]'):
                if stopped() or len(found) >= cap:
                    return found
                add(a.get_text(' ', strip=True),
                    urllib.parse.urljoin(WIKI_PAGE, a['href']))
    except Exception as ex:
        if log:
            log(f'Wikipedia  research Topic list read Failed ; resume category  API:{ex}')

    # Breadth-first across diverse subject trees; avoid the previous hard-coded
    # 180-category cap. Depth protects against the unrelated parts of Wikipedia.
    categories = deque((name, 0) for name in categories_seed)
    visited_categories = set()
    errors = []
    # Scale the discovery budget with the user's requested topic cap.  The old
    # 6,000-category ceiling prevented larger runs even with a raised GUI cap.
    # The depth/math-category guards remain, so the real Wikipedia corpus can
    # exhaust naturally well before the configured maximum.
    category_budget = max(600, cap * 2)
    max_depth = 5
    while categories and len(found) < cap and len(visited_categories) < category_budget:
        if stopped():
            return found
        cat, depth = categories.popleft()
        if cat in visited_categories or not math_category_ok(cat):
            continue
        visited_categories.add(cat)
        continuation = {}
        # 80 pages * 500 members protects against a pathological category;
        # normally only a few pages are required.
        for _ in range(80):
            if stopped():
                return found
            params = {
                'action':'query', 'list':'categorymembers',
                'format':'json', 'formatversion':2, 'cmtitle':cat,
                'cmtype':'page|subcat', 'cmprop':'title|type',
                'cmlimit':500, **continuation,
            }
            try:
                payload = get_json(session, WIKI_API, params, tries=2)
                if 'error' in payload:
                    raise RuntimeError(str(payload['error'])[:240])
            except Exception as ex:
                errors.append(f'{cat}: {type(ex).__name__}: {ex}')
                if log and len(errors) <= 4:
                    log(f'⚠ Wikipedia  category read Failed  {cat}:{str(ex)[:160]}')
                break
            for entry in payload.get('query', {}).get('categorymembers', []):
                if stopped() or len(found) >= cap:
                    return found
                title = entry.get('title', '')
                kind = entry.get('type')
                if kind == 'subcat' or entry.get('ns') == 14:
                    if (depth < max_depth and title not in visited_categories
                            and math_category_ok(title)):
                        categories.append((title, depth + 1))
                elif kind == 'page' or entry.get('ns') == 0:
                    add(title, wikipedia_article_url(title))
            continuation = payload.get('continue') or {}
            if not continuation or len(found) >= cap:
                break
        if log and (len(visited_categories) % 20 == 0 or len(found) >= cap):
            log(f'Wikipedia  already Discover  {len(visited_categories)}  items category , found  {len(found)}  items research Topic ;'
                f' pending Discover category  {len(categories)}  items .')
    if log:
        log(f'Wikipedia  Discover Finish :{len(found)}  items Topic , already query  {len(visited_categories)}  items category .'
            + (f'( with  {len(errors)}  items category read Failed )' if errors else ''))
    if not found:
        raise RuntimeError('Wikipedia  cannot obtain research Topic .'
                           + ('；' + errors[-1] if errors else ''))
    return found


# Explicit user-selected research subjects are different from automatic
# Wikipedia category discovery. They retain their order and are never
# silently replaced by whatever subjects happen to be in a Wikipedia list.
MAX_USER_TOPICS = 1000
# Optional transparent aliases for common colloquial Chinese labels. Other
# Chinese entries use Wikipedia's language links and are not translated by an LLM.
USER_TOPIC_ALIASES = {
    '\u7dda\u6027\u4ee3\u6578': 'Linear algebra', '\u7ebf\u6027\u4ee3\u6570': 'Linear algebra',
    '\u5fae\u7a4d\u5206': 'Calculus', '\u5fae\u79ef\u5206': 'Calculus',
    '\u8ca1\u91d1': 'Finance', '\u8d22\u91d1': 'Finance', '\u91d1\u878d': 'Finance',
    '\u7d71\u8a08': 'Statistics', '\u7edf\u8ba1': 'Statistics',
    '\u6a5f\u5668\u5b78\u7fd2': 'Machine learning', '\u673a\u5668\u5b66\u4e60': 'Machine learning',
    '\u4eba\u5de5\u667a\u6167': 'Artificial intelligence', '\u4eba\u5de5\u667a\u80fd': 'Artificial intelligence',
    '\u63a7\u5236\u7406\u8ad6': 'Control theory', '\u63a7\u5236\u7406\u8bba': 'Control theory',
    '\u795e\u7d93\u79d1\u5b78': 'Neuroscience', '\u795e\u7ecf\u79d1\u5b66': 'Neuroscience',
    '\u6a5f\u5668\u4eba': 'Robotics', '\u673a\u5668\u4eba': 'Robotics',
    '\u7d93\u6fdf\u5b78': 'Economics', '\u7ecf\u6d4e\u5b66': 'Economics',
    '\u91ab\u5b78': 'Medicine', '\u533b\u5b66': 'Medicine',
    '\u6750\u6599\u79d1\u5b78': 'Materials science', '\u6750\u6599\u79d1\u5b66': 'Materials science',
    '\u751f\u7269\u5b78': 'Biology', '\u751f\u7269\u5b66': 'Biology',
    '\u6c23\u5019': 'Climate model', '\u6c14\u5019': 'Climate model',
    '\u6d41\u9ad4\u529b\u5b78': 'Fluid dynamics', '\u6d41\u4f53\u529b\u5b66': 'Fluid dynamics',
    '\u751f\u7269\u6578\u5b78': 'Mathematical biology', '\u751f\u7269\u6570\u5b66': 'Mathematical biology',
    '\u6578\u5b78\u7269\u7406': 'Mathematical physics', '\u6570\u5b66\u7269\u7406': 'Mathematical physics',
    '\u7d71\u8a08\u7269\u7406': 'Statistical mechanics', '\u7edf\u8ba1\u7269\u7406': 'Statistical mechanics',
    '\u6578\u5b78\u7d93\u6fdf\u5b78': 'Mathematical economics', '\u6570\u5b66\u7ecf\u6d4e\u5b66': 'Mathematical economics',
}


# Broad field queries are converted to an explicit mathematical branch BEFORE
# Wikipedia resolution. Raw user text remains visible in worker logs.
# No semantic equivalence edges are created by this search normalization.
MATH_APPLICATION_FOCUS = {
    'finance':'Mathematical finance', 'economics':'Mathematical economics',
    'medicine':'Biostatistics', 'biology':'Mathematical biology',
    'neuroscience':'Computational neuroscience',
    'robotics':'Control theory', 'engineering':'Engineering mathematics',
    'chemistry':'Mathematical chemistry', 'physics':'Mathematical physics',
    'epidemiology':'Mathematical epidemiology',
    'ecology':'Mathematical ecology', 'social science':'Mathematical sociology',
    'climate':'Climate model', 'statistics':'Mathematical statistics',
}

def mathematics_topic_focus(raw):
    """Turn a *broad discipline* input into its named mathematical branch."""
    return MATH_APPLICATION_FOCUS.get(canonical_phrase(raw),str(raw).strip())

def parse_research_topics(text):
    """Comma-separated subject input; support full-width commas and newlines.

    Strict validation avoids silently dropping user-selected subjects.
    """
    raw=str(text or '').replace('，', ',').replace('、', ',').replace('\n', ',')
    names=[part.strip().strip('\"\' ') for part in raw.split(',')]
    names=[name for name in names if name]
    if len(names)>MAX_USER_TOPICS:
        raise ValueError(f' single imes at most manual input  {MAX_USER_TOPICS:,}  items Topic ; large amounts of Topic please use automatic Discover .')
    if any(len(name)>140 for name in names):
        raise ValueError(' single research Topic at most  140  items characters .')
    if any(len(name)<2 for name in names):
        raise ValueError(' research Topic at least needs two items characters .')
    result=[];seen=set()
    for name in names:
        key=unicodedata.normalize('NFKC',name).casefold()
        if key not in seen:
            seen.add(key);result.append(name)
    return result


def _wikipedia_canonical_title(session, title, api=WIKI_API):
    """Confirm a real mainspace article; never fabricate an article URL."""
    payload=get_json(session,api,{
        'action':'query','format':'json','formatversion':2,'prop':'info',
        'redirects':1,'titles':title,
    },tries=2)
    if 'error' in payload: raise RuntimeError(str(payload['error'])[:200])
    for item in (payload.get('query') or {}).get('pages',[]):
        if (isinstance(item,dict) and item.get('ns')==0 and
                'missing' not in item and not item.get('invalid')):
            return item.get('title') or title
    return ''


def resolve_manual_topic(session, original, log=None):
    """Resolve manual input to a verified enwiki title or retain raw topic.

    Chinese Wikipedia language links are used when a matching zh article exists.
    Unresolved items are still valid literature search queries, with NO invented
    Wikipedia URL or claim that Wikipedia article content was obtained.
    """
    requested=str(original).strip()
    candidate=USER_TOPIC_ALIASES.get(requested,requested)
    try:
        en_title=_wikipedia_canonical_title(session,candidate)
        if en_title:
            return en_title,wikipedia_article_url(en_title)
    except Exception as exc:
        if log:log(f'⚠ Wikipedia  English article confirm Failed  {requested}:{str(exc)[:130]}')
    if re.search(r'[\u3400-\u9fff]',requested):
        zh_api='https://zh.wikipedia.org/w/api.php'
        try:
            zh_payload=get_json(session,zh_api,{
                'action':'query','format':'json','formatversion':2,
                'prop':'langlinks','lllang':'en','lllimit':1,
                'redirects':1,'titles':requested,
            },tries=2)
            for item in (zh_payload.get('query') or {}).get('pages',[]):
                if not isinstance(item,dict) or 'missing' in item:
                    continue
                for link in item.get('langlinks',[]):
                    if link.get('lang')=='en' and link.get('title'):
                        target=_wikipedia_canonical_title(session,link['title'])
                        if target:
                            return target,wikipedia_article_url(target)
        except Exception as exc:
            if log:log(f'⚠ Wikipedia  Chinese cross-language query Failed  {requested}:{str(exc)[:130]}')
    if log:
        log(f'○ `{requested}` not yet Verify mapping English  Wikipedia  article ; directly use original name Search academic Literature .')
    return requested,''


def get_wikipedia_description(session, url):
    """Fetch Wikipedia article prose, with official MediaWiki extract fallback."""
    errors=[]
    try:
        r=session.get(url,headers=HEADERS,timeout=(8,25))
        r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        main=(soup.select_one('#mw-content-text .mw-parser-output') or
              soup.select_one('.mw-parser-output') or soup.select_one('main') or soup)
        paragraphs=[p.get_text(' ',strip=True) for p in main.select('p')]
        paragraphs=[p for p in paragraphs if len(p)>=60 and
                    not p.startswith(('Coordinates:','From Wikipedia'))]
        content=' '.join(paragraphs[:6])[:6500]
        if len(content)>=70:
            return content
        errors.append('HTML  article Content insufficient ')
    except Exception as exc:
        errors.append(str(exc))
    title=urllib.parse.unquote(urllib.parse.urlsplit(url).path.split('/wiki/')[-1]).replace('_',' ')
    try:
        payload=get_json(session,WIKI_API,{
            'action':'query','prop':'extracts','exintro':1,'explaintext':1,
            'titles':title,'format':'json','formatversion':2},tries=2)
        pages=payload.get('query',{}).get('pages',[])
        content=(pages[0].get('extract','') if pages else '').strip()
        if len(content)>=70:
            return content[:6500]
        errors.append('API  abstract Content insufficient ')
    except Exception as exc:
        errors.append(str(exc))
    raise RuntimeError('Wikipedia  Unable to read  '+title+':'+ ';'.join(errors)[-400:])



# --- Wikipedia bibliography extraction / independently verifiable provenance ---
_DOI_RX = re.compile(r'(?i)\b10\.\d{4,9}/[^\s<>"\'\[\]{}|]+')
_ARXIV_RX = re.compile(r'(?i)(?:arxiv\s*:\s*|arxiv\.org/(?:abs|pdf)/)([a-z.-]+/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?')
_PAPER_TYPES = {None, 'article', 'preprint', 'review', 'proceedings-article', 'book-chapter'}


def normalize_doi(raw):
    raw=urllib.parse.unquote(html.unescape(str(raw or ''))).strip()
    raw=re.sub(r'(?i)^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)','',raw)
    match=_DOI_RX.search(raw)
    return match.group(0).rstrip('.,;:)]') .lower() if match else ''


def reference_title(node):
    """Best-effort *literal citation title*; never hallucinate a paper title."""
    cite=node.select_one('cite.citation') or node
    # Wikipedia CS1 citation titles are frequently in linked text.
    for el in cite.select('a.external.text, a[href]'):
        title=el.get_text(' ',strip=True).strip(' ."“”')
        href=el.get('href','')
        if ('doi.org/' in href or 'arxiv.org/' in href or
                'google.com' in href or not 16 <= len(title) <= 260):
            continue
        if title.casefold().startswith(('doi:', 'arxiv:', 'bibcode:', 'isbn:', 'pdf')):
            continue
        return title
    # A quotation in a citation is often the work title.
    txt=cite.get_text(' ',strip=True)
    m=re.search(r'[“"]([^"”]{16,220})[”"]',txt)
    return m.group(1).strip() if m else ''


def wikipedia_reference_records(soup):
    """Read Wikipedia <ol class=references> and reflist footnote records.

    Include all footnotes as provenance; non-papers stay visible as 'non_paper'.
    Only bibliographic work candidates proceed to OpenAlex matching.
    """
    result=[];seen=set()
    elements=soup.select('ol.references > li, .reflist ol > li, li[id^="cite_note-"]')
    for ix,li in enumerate(elements,1):
        refid=li.get('id') or f'footnote-{ix}'
        if refid in seen:continue
        seen.add(refid)
        sub=li.select_one('span.reference-text, span.mw-reference-text') or li
        literal=' '.join(sub.get_text(' ',strip=True).split())[:1600]
        if not literal:continue
        links=[]
        for a in sub.find_all('a',href=True):
            raw=a['href'].strip()
            url=urllib.parse.urljoin('https://en.wikipedia.org/',raw)
            if url.startswith('https://') and safe_pdf_url(url):
                links.append(url)
        doi=''
        for link in links:
            doi=normalize_doi(link)
            if doi:break
        doi=doi or normalize_doi(literal)
        arxiv=''
        for value in links+[literal]:
            match=_ARXIV_RX.search(value)
            if match:
                arxiv=match.group(1).lower()
                break
        title=reference_title(sub)
        academic_citation=bool(sub.select('cite.citation.journal, cite.citation.conference, cite.citation.arxiv'))
        if not academic_citation:
            academic_citation=bool(re.search(r'(?i)\b(?:journal|proceedings|transactions|preprint|arxiv)\b',literal))
        primary=next((x for x in links if 'doi.org/' in x or 'arxiv.org/' in x),
                     next((x for x in links if x.lower().split('?')[0].endswith('.pdf')), 
                          links[0] if links else ''))
        kind='candidate' if doi or arxiv or (academic_citation and title) else 'non_paper'
        result.append(dict(key=refid,text=literal,doi=doi,arxiv_id=arxiv,
                           paper_title=title,url=primary,status='found' if kind=='candidate' else kind))
    return result


def get_wikipedia_article(session, url):
    """Fetch prose AND footnotes in one request; only API extract is fallback.

    The plain MediaWiki `extracts` API lacks reference structure, so failure
    to obtain HTML footnotes is logged rather than silently called success.
    """
    errors=[];refs=[];content=''
    try:
        response=session.get(url,headers=HEADERS,timeout=(8,30))
        response.raise_for_status()
        soup=BeautifulSoup(response.text,'html.parser')
        main=(soup.select_one('#mw-content-text .mw-parser-output') or
              soup.select_one('.mw-parser-output') or soup.select_one('main') or soup)
        paragraphs=[p.get_text(' ',strip=True) for p in main.select('p')]
        paragraphs=[p for p in paragraphs if len(p)>=60 and
                    not p.startswith(('Coordinates:','From Wikipedia'))]
        content=' '.join(paragraphs[:6])[:6500]
        refs=wikipedia_reference_records(soup)
    except Exception as exc:
        errors.append(str(exc))
    if len(content)<70:
        # Keep the old API fallback for wiki prose; it does not contain citations.
        try:content=get_wikipedia_description(session,url)
        except Exception as exc:errors.append(str(exc))
    if len(content)<70 and not refs:
        raise RuntimeError('Wikipedia HTML/API  average Unable to read :'+';'.join(errors)[-330:])
    return content, refs


def save_wikipedia_references(con,theory,refs):
    """Durably preserve citation text before calling third-party APIs."""
    with con:
        for ref in refs:
            con.execute('''INSERT INTO wikipedia_references
                (theory,reference_key,citation_text,doi,arxiv_id,paper_title,reference_url,status)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(theory,reference_key) DO UPDATE SET
                    citation_text=excluded.citation_text,doi=excluded.doi,
                    arxiv_id=excluded.arxiv_id,paper_title=excluded.paper_title,
                    reference_url=excluded.reference_url,
                    status=CASE WHEN wikipedia_references.status='linked' THEN 'linked'
                                ELSE excluded.status END,
                    updated=CURRENT_TIMESTAMP''',
                    (theory,ref['key'],ref['text'],ref['doi'],ref['arxiv_id'],
                     ref['paper_title'],ref['url'],ref['status']))


def _reference_title_similarity(a,b):
    norm=lambda x:re.sub(r'[^a-z0-9]+',' ',str(x).casefold()).strip()
    return SequenceMatcher(None,norm(a),norm(b)).ratio()


def resolve_wikipedia_references(session,refs,api_key,stop_event,log=None,limit=MAX_PAPERS_PER_THEORY,
                                 openalex_enabled=False,unavailable_event=None,
                                 arxiv_unavailable=None,crossref_unavailable=None):
    """Yield (reference, verified paper record) with exact arXiv/DOI matching.

    DOI requests are batched to reduce quotas. For references without DOI,
    title search is *strictly verified*; guesses stay unresolved. Yield
    (reference,None) for every unresolved candidate for diagnostic records.
    """
    candidates=[r for r in refs if r['status']=='found'][:max(0,min(MAX_WIKI_REFERENCE_WORKS,int(limit)))]
    by_doi=defaultdict(list)
    for ref in candidates:
        doi=ref['doi']
        if doi:by_doi[doi].append(ref)
    resolved=set()
    # Reuse verified local DOI/arXiv metadata before issuing any public API
    # request. This cache is shared across all mathematics topic workers.
    for ref in candidates:
        cached=catalog_lookup_reference(ref.get('doi',''),ref.get('arxiv_id',''),
                                        ref.get('paper_title',''))
        if cached and cached.get('type') in _PAPER_TYPES:
            resolved.add(ref['key'])
            yield ref,cached
    by_arxiv=defaultdict(list)
    for ref in candidates:
        if ref.get('arxiv_id') and ref['key'] not in resolved:
            by_arxiv[ref['arxiv_id'].lower()].append(ref)
    if by_arxiv and not (arxiv_unavailable and arxiv_unavailable.is_set()):
        try:
            found=fetch_arxiv_reference_batch(session,list(by_arxiv),stop_event,on_retry=log)
            if found:
                try:catalog_store_batch(list(found.values()),provider='arxiv-reference')
                except sqlite3.Error:pass
            for arxiv_id,refs_for_id in by_arxiv.items():
                work=found.get(arxiv_id)
                if work and work.get('type') in _PAPER_TYPES:
                    for ref in refs_for_id:
                        resolved.add(ref['key'])
                        yield ref,work
        except OpenAlexSearchFailure as exc:
            if arxiv_unavailable is not None:arxiv_unavailable.set()
            if log:log('arXiv  citation Verify temporarily Failed , resume its they Source :'+exc.reason[:160])
    keys=[doi for doi,items in by_doi.items()
          if any(r['key'] not in resolved for r in items)]
    for start in range(0,len(keys),40):
        if stop_event.is_set():return
        batch=keys[start:start+40]
        params={'filter':'doi:'+'|'.join('https://doi.org/'+d for d in batch),
                'per_page':100,'select':OPENALEX_FIELDS}
        if api_key:params['api_key']=api_key
        works={}
        if openalex_enabled:
            try:
                response=openalex_request(session,params,stop_event,on_retry=log)
                works={normalize_doi(w.get('doi')):w for w in response['results']
                       if isinstance(w,dict) and w.get('id')}
            except OpenAlexSearchFailure as exc:
                if log:log('OpenAlex DOI  parse NOT available , switch to  Crossref DOI:'+exc.reason[:130])
                if unavailable_event is not None and exc.category in ('quota','auth'):
                    unavailable_event.set()
                openalex_enabled=False
        for doi in batch:
            if all(ref['key'] in resolved for ref in by_doi[doi]):continue
            if doi in works or (crossref_unavailable and crossref_unavailable.is_set()):continue
            try:
                item=crossref_request(session,stop_event=stop_event,doi=doi,on_retry=log)
                work=crossref_work_to_openalex(item) if item else None
                if work:works[doi]=work
            except OpenAlexSearchFailure as exc:
                if log:log('Crossref DOI  Verify Failed :'+exc.reason[:160])
                if exc.category in ('quota','auth','network','server'):
                    if crossref_unavailable is not None:crossref_unavailable.set()
                    break
        if works:
            try:catalog_store_batch(list(works.values()),provider='wikipedia-doi')
            except sqlite3.Error:pass
        for doi in batch:
            work=works.get(doi)
            if work and work.get('type') in _PAPER_TYPES:
                for ref in by_doi[doi]:
                    if ref['key'] in resolved:continue
                    resolved.add(ref['key'])
                    yield ref,work
    # Strict title verification is a fallback, not an unconstrained keyword
    # search: it is used for entries containing a recognizable paper title.
    title_attempts=0
    for ref in candidates:
        if stop_event.is_set():return
        if ref['key'] in resolved:continue
        title=ref.get('paper_title','')
        if (title and title_attempts<12 and (not ref['doi'] or ref['arxiv_id'])
                and (openalex_enabled or not (crossref_unavailable and crossref_unavailable.is_set()))):
            title_attempts+=1
            params={'search':title,'per_page':5,'select':OPENALEX_FIELDS}
            if api_key:params['api_key']=api_key
            try:
                if openalex_enabled:
                    data=openalex_request(session,params,stop_event,on_retry=log)
                    rows=data['results']
                else:
                    data=crossref_request(session,{'query.bibliographic':title,'rows':5},
                                          stop_event,on_retry=log)
                    rows=[x for w in (data.get('items',[]) if isinstance(data,dict) else [])
                          if (x:=crossref_work_to_openalex(w))]
                valid=[w for w in rows if w.get('id') and
                       w.get('type') in _PAPER_TYPES and
                       _reference_title_similarity(title,w.get('display_name','')) >= .88]
                if valid:
                    best=max(valid,key=lambda w:w.get('cited_by_count') or 0)
                    try:catalog_store_batch([best],provider='wikipedia-title')
                    except sqlite3.Error:pass
                    resolved.add(ref['key'])
                    yield ref,best
                    continue
            except OpenAlexSearchFailure as exc:
                if exc.category in ('auth','quota','network','server'):
                    if openalex_enabled and unavailable_event is not None:unavailable_event.set()
                    if not openalex_enabled and crossref_unavailable is not None:crossref_unavailable.set()
                    openalex_enabled=False
                if log:log(f'Wikipedia  references title parse Failed :{str(exc)[:130]}')
        yield ref,None


def paper_unit_id(identifier):
    """Stable graph ID for both new and old-style arXiv IDs.

    Legacy `math/0603001` must retain its archive name, otherwise it collides
    with other archive categories that have the same seven-digit suffix.
    """
    value=str(identifier)
    if 'arxiv.org/abs/' in value:
        tail=value.split('arxiv.org/abs/',1)[1].split('?',1)[0]
        return 'paper:arxiv:'+tail.replace('/','_').casefold()
    return 'paper:'+value.rsplit('/',1)[-1]


def mark_wikipedia_citation(con,theory,ref,work=None,error=''):
    """Citation relation is distinct from generic search membership.

    It is recorded once per exact Wikipedia footnote. The original note is
    preserved separately from abstract/full-text and can be audited later.
    """
    with con:
        if not work:
            con.execute('''UPDATE wikipedia_references SET status='unresolved',error=?,
                updated=CURRENT_TIMESTAMP WHERE theory=? AND reference_key=? AND status!='linked' ''',
                (error[:550] or ' The research paper could not be verified using available literature providers ',theory,ref['key']))
            return False
        paper_id=paper_unit_id(work['id'])
        theory_id='theory:'+theory.casefold()
        previous=con.execute('''SELECT work_id,status FROM wikipedia_references
            WHERE theory=? AND reference_key=?''',(theory,ref['key'])).fetchone()
        if not previous or previous[1]!='linked' or previous[0]!=work['id']:
            # Exactly one directed citation edge per theory/paper, separate
            # from the generic theory->paper similarity edge.
            existing=con.execute('''SELECT 1 FROM edges
                WHERE src=? AND dst=? AND kind='wikipedia-cites-paper' ''',
                (theory_id,paper_id)).fetchone()
            if not existing:
                upsert_edge(con,theory_id,paper_id,'wikipedia-cites-paper',1.2)
        source=con.execute('SELECT abstract,fulltext_used FROM papers WHERE id=?',
                           (work['id'],)).fetchone()
        read_level=('fulltext' if source and source[1] else
                    'abstract' if source and source[0] else 'title_only')
        con.execute('''UPDATE wikipedia_references SET status='linked',work_id=?,read_level=?,error='',
            updated=CURRENT_TIMESTAMP WHERE theory=? AND reference_key=?''',
            (work['id'],read_level,theory,ref['key']))
        return True


def abstract_from_index(idx):
    if not idx or not isinstance(idx, dict):
        return ""
    slots = {}
    for word, positions in idx.items():
        for p in positions:
            if isinstance(p, int) and 0 <= p <= 30000:
                slots[p] = word
    return " ".join(slots[k] for k in sorted(slots))[:45000]


def score_candidate(work, theory, rank_bonus):
    title = (work.get("display_name") or "").lower()
    abstract = (work.get("_abstract_text") or abstract_from_index(work.get("abstract_inverted_index"))).lower()
    needle = theory.casefold().replace("–", "-").replace("—", "-")
    title = title.replace("–", "-")
    abstract = abstract.replace("–", "-")
    words = [x.lower() for x in TOKEN_RE.findall(needle) if len(x) > 2 and x not in STOP]
    if not words:
        words = [x.lower() for x in TOKEN_RE.findall(needle) if len(x) > 2]
    # Count real normalized word matches, not accidental substrings such as
    # linear contained in nonlinear. This keeps Crossref/title-only records
    # conservative, while real abstracts strengthen evidence-based ranking.
    title_terms={_lemma(w) for w in TOKEN_RE.findall(title)}
    abstract_terms={_lemma(w) for w in TOKEN_RE.findall(abstract[:35000])}
    topic_terms=[_lemma(w) for w in words]
    lexical=(sum(w in title_terms for w in topic_terms)/max(1,len(topic_terms))) * 0.8
    lexical+=(sum(w in abstract_terms for w in topic_terms)/max(1,len(topic_terms))) * 0.2
    # Phrase match only on normalized word boundaries.
    is_phrase=lambda hay: bool(re.search(r'(?<![a-z0-9])'+re.escape(needle)+r'(?![a-z0-9])',hay))
    exact=0.75 if is_phrase(title) else 0.4 if is_phrase(abstract) else 0
    # Search-provider relevance gating: a famous unrelated paper must not
    # pass purely by citation count and spend PDF/SQLite resources.
    # Expansions improve recall for genuine cross-disciplinary mathematical
    # papers; they are SEARCH HINTS, not equivalence assertions or graph edges.
    if active_domain()=='mathematics':
        math_title=bool(MATH_TOPIC_RESEARCH.search(title))
        math_abstract=bool(MATH_TOPIC_RESEARCH.search(abstract[:12000]))
        if not (math_title or math_abstract):
            return 0.0
        extras={_lemma(w) for w in MATH_TOPIC_EXPANSIONS.get(canonical_phrase(theory),())}
        diagnostic=extras & (title_terms|abstract_terms)
        if not (lexical>0 or exact or len(diagnostic)>=2):
            return 0.0
        if lexical<=0 and len(diagnostic)>=2:
            lexical=0.30+0.07*min(len(diagnostic),3)
    citations=int(work.get("cited_by_count") or 0)
    prestige=min(1.0,math.log1p(citations)/10.0)
    return lexical + exact + (0.12 if active_domain()=='mathematics' else 0.40)*prestige + 0.25*rank_bonus



def fetch_papers(session, theory, wanted, api_key, stop_event, pause_event=None, progress=None):
    """Backward-compatible batch helper (streaming is preferred for large jobs).

    WARNING: this returns a list, so main collection uses stream_papers() to
    avoid holding potentially a million academic works in RAM.
    """
    wanted = max(1, min(MAX_PAPERS_PER_THEORY, int(wanted)))
    def adapt_progress(page, total, _emitted, batch_size):
        if progress:
            progress(page, total, batch_size)
    rows = list(stream_papers(session, theory, wanted, api_key, stop_event,
                              pause_event=pause_event, progress=adapt_progress))
    rows.sort(key=lambda pair: pair[0], reverse=True)
    return rows


def safe_pdf_url(url):
    try:
        parsed = urllib.parse.urlsplit(url or "")
        if parsed.scheme != "https" or not parsed.hostname:
            return False
        hostname = parsed.hostname.lower()
        if hostname in ("localhost",) or hostname.endswith((".local", ".internal")):
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_global
        except ValueError:
            return True
    except (ValueError, AttributeError):
        return False


def obtain_pdf_text(session, work, fallback_pdf_url=''):
    if fitz is None:
        return ""
    loc = work.get("best_oa_location") or {}
    url = loc.get("pdf_url")
    if not safe_pdf_url(url) and str(fallback_pdf_url).lower().split('?')[0].endswith('.pdf'):
        url = fallback_pdf_url
    if not safe_pdf_url(url):
        return ""
    try:
        with session.get(url, headers=HEADERS, timeout=(8, 16), stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            if not safe_pdf_url(r.url):
                return ""
            chunks, size = [], 0
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                size += len(chunk)
                if size > 10_000_000:
                    return ""
                chunks.append(chunk)
        body = b"".join(chunks)
        if not body.startswith(b"%PDF-"):
            return ""
        with fitz.open(stream=body, filetype="pdf") as doc:
            # An isolated unreadable page should not discard the rest of an
            # otherwise extractable paper. The abstract remains the fallback
            # when insufficient full text survives.
            extracted = []
            for page_index in range(min(30, len(doc))):
                try:
                    extracted.append(doc[page_index].get_text("text"))
                except (RuntimeError, ValueError):
                    continue
            text = "\n".join(extracted)
        # Exclude likely bibliography and garbage; permit 40k for memory extraction.
        text = re.split(r"\n\s*(?:references|bibliography)\s*\n", text, flags=re.I)[0]
        return " ".join(text.split())[:65000] if len(text) > 500 else ""
    except Exception:
        return ""


def split_sentences(text):
    cleaned = re.sub(r"\s+", " ", html.unescape(text or "")).strip()
    return [s.strip() for s in SENTENCE_RE.split(cleaned) if 45 <= len(s.strip()) <= 500][:260]


def keyphrases(text, title, limit=12):
    """High-precision extraction of explicitly mathematical terms only.

    Never create nodes from arbitrary TF-IDF ngrams. A new unrecognised term
    must contain a mathematical structural head and a substantive qualifier.
    The source text must contain the matched term. No LLM / embeddings.
    """
    if active_domain()!='mathematics':
        return general_keyphrases(text,title,limit)
    corpus=(title+' . '+(text or '')[:30000]).casefold()
    corpus=re.sub(r'[^a-z0-9\s-]',' ',corpus)
    corpus=re.sub(r'\s+',' ',corpus)
    if not corpus:return []
    count=defaultdict(float)
    anchored=set()
    for term,pat in _MATH_ANCHOR_PATTERNS:
        hits=list(pat.finditer(corpus))[:18]
        if not hits:continue
        c=canonical_phrase(term)
        if not math_concept_quality(c)[0]:continue
        score=1.0+min(5,len(hits))*.25+(1.1 if term.lower() in title.lower() else 0)
        count[c]+=score
        anchored.add(c)
    # Discover named formulas/methods from explicit mathematical heads,
    # not arbitrary repeated tokens ('students', 'chromatography', ...).
    words=corpus.split()[:8000]
    for j,token in enumerate(words):
        stem=_lemma(token)
        if stem not in MATH_CONCEPT_HEADS:continue
        for left in (1,2,3):
            lo=j-left
            if lo<0:continue
            phrase=' '.join(words[lo:j+1])
            valid,reason=math_concept_quality(phrase)
            if not valid:continue
            qualifiers=set(words[lo:j+1]) & (
                MATH_SPECIFIERS - {'approximation','rate','pricing','risk','model','element'})
            if reason=='mathematical_expression' and not qualifiers:
                continue
            c=canonical_phrase(phrase)
            count[c]+=(1.3 if phrase in title.lower() else .42)
    # Avoid a long phrase duplicating its own anchored concept: choose more
    # source-supported and more specific terms, but preserve distinct objects.
    ranked=sorted(count.items(),key=lambda x:(-x[1],-len(x[0].split()),x[0]))
    chosen=[]
    for phrase,score in ranked:
        if any(phrase==q for q,_ in chosen):continue
        if any(phrase in q.split(' | ') for q,_ in chosen):continue
        chosen.append((phrase,score))
        if len(chosen)>=limit:break
    if not chosen:return []
    best=max(x[1] for x in chosen)
    return [(phrase,round(float(score/max(best,.001)),4)) for phrase,score in chosen]


def summarize(text, phrases, max_sentences=3):
    sentences = split_sentences(text)
    if not sentences:
        return (text or "")[:750]
    weighted = []
    for i, sentence in enumerate(sentences):
        lower = sentence.lower()
        hits = sum((1 + 0.25 * (len(t.split()) - 1)) * strength
                   for t, strength in phrases if t in lower)
        weighted.append((hits + 0.20 / math.sqrt(i + 1), i))
    selected = sorted(i for _, i in sorted(weighted, reverse=True)[:max_sentences])
    return " ".join(sentences[i] for i in selected)[:1800]


# ---------------------------------------------------------------------------
# Mathematical purity gate: strict for standalone noise, conservative for
# ambiguous mathematics, with a transparent per-database heuristic score.
# This is source/lexical quality control, NOT theorem validation.
# ---------------------------------------------------------------------------
_PURITY_SHORT_MATH = frozenset({'pi','ln','e','i'})
# Generic standalone navigation / academic prose is not a mathematical concept.
# Never include foundational terms such as analysis, logic or group here.
_PURITY_DISPOSABLE_SINGLETONS = frozenset({
    'student','students','author','authors','article','articles',
    'introduction','conclusion','conclusions','abstract','paper','papers',
    'study','studies','review','reviews','chromatography','novel',
    'today','various','results','discussion','bibliography',
})
# An explicit, narrow DELETE allowlist. A broad NLP stopword list contains
# mathematics-relevant labels such as 'one'; never hard-delete those blindly.
_PURITY_TRIVIAL_WORDS = frozenset({
    'is','or','an','and','are','were','was','be','been','being','am','the','a',
    'of','to','for','from','on','in','by','as','at','with','without','it','its',
    'this','that','these','those','we','they','you','our','their','your',
    'et','al','fig','figure','page','pages','www','http','https',
})

@lru_cache(maxsize=180000)
def score_math_unit_purity(label, kind='concept'):
    '''0..100 heuristic; <75 gets rejected for new concept memories.

    One-word stopwords are unconditionally junk as stand-alone *concept*
    memories, even though words like 'or' can be meaningful inside longer
    logical expressions. Such expressions must be source-grounded separately.
    '''
    phrase=canonical_phrase(label)
    if not phrase or phrase in _PURITY_TRIVIAL_WORDS:
        return 0,'isolated_function_word_or_empty'
    if phrase in _PURITY_DISPOSABLE_SINGLETONS:
        return 5,'nonmathematical_singleton'
    if len(phrase)<=2 and phrase not in _PURITY_SHORT_MATH and not phrase.isdigit():
        return 0,'isolated_short_token'
    if kind=='concept':
        if phrase in _PURITY_SHORT_MATH:
            return 83,'short_mathematical_notation_candidate'
        valid,reason=_pure_math_concept_quality(label)
        if not valid:return 15,reason
        if phrase in MATH_ANCHOR_CANONICAL:return 98,'curated_mathematics_anchor'
        if phrase in MATH_SINGLE_ACCEPT:return 95,'curated_mathematics_term'
        return 86,reason
    if kind=='relation':
        parts=re.split(r'\s*[—→]\s*',label or '')
        valid=(len(parts)>=3 and _pure_math_concept_quality(parts[0])[0]
               and _pure_math_concept_quality(parts[-1])[0])
        return (85,'sourced_relation_candidate') if valid else (20,'invalid_relation_endpoints')
    # The paper and theory nodes represent provenance / topic navigation.
    # Avoid scoring an entire article by grammar words in its title.
    return 80,'source_or_topic_metadata'


def _purity_add_counter(con, key, delta=1):
    if delta:
        con.execute('''INSERT INTO purity_metrics(key,value) VALUES(?,?)
            ON CONFLICT(key) DO UPDATE SET value=value+excluded.value''',
            (key,int(delta)))


def _purity_reject(con, label, reason):
    # The original candidate is not stored as a memory unit. Keep a short
    # aggregate audit trail of rejected labels so purity statistics are honest.
    safe_label=str(label or '')[:120].casefold()
    con.execute('''INSERT INTO purity_rejection_summary(label,reason,rejected_count)
        VALUES(?,?,1) ON CONFLICT(label,reason)
        DO UPDATE SET rejected_count=rejected_count+1''',(safe_label,reason))
    _purity_add_counter(con,'rejected_candidates')


def purity_report(con):
    data={k:int(v) for k,v in con.execute('SELECT key,value FROM purity_metrics')}
    accepted=data.get('accepted_candidates',0)
    rejected=data.get('rejected_candidates',0)
    scored=data.get('score_sum',0)
    # The observed admission rate is distinct from a semantic truthfulness score.
    total=accepted+rejected
    old_total=data.get('old_concepts_evaluated',0)
    removed_concepts=data.get('deleted_noise_concepts',0)
    remaining=max(0,old_total-removed_concepts)
    remaining_weak=max(0,data.get('old_concepts_below_threshold',0)-removed_concepts)
    remaining_score=max(0,data.get('old_concepts_score_sum',0)-
                        data.get('deleted_noise_score_sum',0))
    return {
        'approved_candidates':accepted,
        'rejected_candidates':rejected,
        'old_units_scanned':data.get('old_units_scanned',0),
        'old_concepts_evaluated':data.get('old_concepts_evaluated',0),
        'old_concepts_below_threshold':data.get('old_concepts_below_threshold',0),
        'old_concept_purity_score':round(remaining_score/remaining,1) if remaining else None,
        'old_concept_pass_rate_pct':round(100*(remaining-remaining_weak)/remaining,1) if remaining else None,
        'old_concepts_current_scanned':remaining,
        'old_concepts_remaining_low_score':remaining_weak,
        'deleted_noise_units':data.get('deleted_noise_units',0),
        'admission_rate_pct':round(100*accepted/total,1) if total else None,
        'mean_heuristic_score':round(scored/max(1,accepted),1) if accepted else None,
        'samples':con.execute('''SELECT label,reason,rejected_count FROM purity_rejection_summary
             ORDER BY rejected_count DESC LIMIT 8''').fetchall(),
    }


def purge_trivial_legacy_units_batch(con, limit=900, flush=False):
    '''Incremental, restartable old-network cleanup, scanning ROWID once.

    Only standalone function words or one/two-letter fragments are deleted.
    Anything ambiguous is *not* hard-deleted. Batch node/edge cleanup so a
    million-edge network is not scanned once for every removed word.
    The caller must serialize graph writes with the Collector writer lock.
    '''
    limit=max(0,min(5000,int(limit)))
    cursor=con.execute("SELECT value FROM network_meta WHERE key='purity_scan_rowid'").fetchone()
    after=int(cursor[0]) if cursor else 0
    rows=(con.execute('''SELECT rowid,id,label,kind FROM units
        WHERE rowid>? ORDER BY rowid LIMIT ?''',(after,limit)).fetchall() if limit else [])
    queued=0
    evaluated=0;below_threshold=0;score_sum=0
    with con:
        for _,uid,label,kind in rows:
            # A malformed old relation that explicitly uses a disposable
            # function word as its endpoint cannot be a math claim.  Prune it
            # together with its source edges/evidence rather than leaving a
            # dangling relation unit after its concept was deleted.
            if kind=='relation':
                endpoints=re.split(r'\s*[—→]\s*',label or '')
                if len(endpoints)>=3 and any(
                     canonical_phrase(term) in (_PURITY_TRIVIAL_WORDS |
                         _PURITY_DISPOSABLE_SINGLETONS) for term in
                     (endpoints[0],endpoints[-1])):
                    con.execute('INSERT OR IGNORE INTO purity_prune_queue(unit_id) VALUES(?)',(uid,))
                    queued+=1
                continue
            # Compute a sampled, accumulating purity estimate as we sweep.
            # Score is heuristic and cannot replace source/logic validation.
            if kind!='concept':continue
            purity_score,_=score_math_unit_purity(label,'concept')
            evaluated+=1
            below_threshold+=int(purity_score<75)
            score_sum+=purity_score
            # Removal is deliberately MUCH stricter than quality acceptance.
            # Keep legitimate math and all scholarly paper/source metadata.
            phrase=canonical_phrase(label)
            if (phrase in _PURITY_TRIVIAL_WORDS or phrase in _PURITY_DISPOSABLE_SINGLETONS
                or (len(phrase)<=2 and phrase not in _PURITY_SHORT_MATH and not phrase.isdigit())):
                con.execute('INSERT OR IGNORE INTO purity_prune_queue(unit_id) VALUES(?)',(uid,))
                queued+=1
        if rows:
            con.execute("INSERT INTO network_meta(key,value) VALUES('purity_scan_rowid',?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (str(rows[-1][0]),))
        _purity_add_counter(con,'old_units_scanned',len(rows))
        _purity_add_counter(con,'old_concepts_evaluated',evaluated)
        _purity_add_counter(con,'old_concepts_below_threshold',below_threshold)
        _purity_add_counter(con,'old_concepts_score_sum',score_sum)
        queue_size=con.execute('SELECT COUNT(*) FROM purity_prune_queue').fetchone()[0]
        # Keep global edge deletion infrequent: dst may be unindexed in old DB.
        if queue_size>=60 or flush or not rows:
            if queue_size:
                to_delete=con.execute('''SELECT u.label FROM units u
                    JOIN purity_prune_queue q ON q.unit_id=u.id
                    WHERE u.kind='concept' ''').fetchall()
                _purity_add_counter(con,'deleted_noise_concepts',len(to_delete))
                _purity_add_counter(con,'deleted_noise_score_sum',sum(
                    score_math_unit_purity(row[0],'concept')[0] for row in to_delete))
                # Preserve a minimal recovery/audit record before removing
                # the node and all current graph references. The original DB
                # itself is never rebuilt or overwritten as part of this sweep.
                con.execute('''INSERT OR IGNORE INTO purity_deleted_log
                    (unit_id,label,kind,description,source_url)
                    SELECT id,label,kind,COALESCE(description,''),COALESCE(url,'')
                    FROM units WHERE id IN (SELECT unit_id FROM purity_prune_queue)''')
                con.execute('''DELETE FROM edges WHERE
                    src IN (SELECT unit_id FROM purity_prune_queue) OR
                    dst IN (SELECT unit_id FROM purity_prune_queue)''')
                for table,column in (('mentions','unit_id'),('positions','unit_id'),
                                     ('unit_terms','unit_id'),('unit_quality_audit','unit_id'),
                                     ('unit_purity_scores','unit_id'),('relation_evidence','relation_id')):
                    con.execute(f'DELETE FROM {table} WHERE {column} IN '
                                '(SELECT unit_id FROM purity_prune_queue)')
                con.execute('DELETE FROM units WHERE id IN (SELECT unit_id FROM purity_prune_queue)')
                _purity_add_counter(con,'deleted_noise_units',queue_size)
                con.execute('DELETE FROM purity_prune_queue')
        return {'scanned':len(rows),'queued':queued,
                'deleted':queue_size if queue_size>=60 or flush or not rows else 0,
                'completed':not bool(rows)}


def event_node(con, uid, label):
    con.execute("INSERT INTO build_events(action,unit_id,label) VALUES('node',?,?)",
                (uid, label[:240]))


def add_unit(con, uid, label, kind, description, url, citations=0, support=0):
    if kind in ('concept','relation'):
        purity_score,purity_reason=score_math_unit_purity(label,kind)
        if purity_score<75:
            _purity_reject(con,label,purity_reason)
            return False
    exists = con.execute("SELECT 1 FROM units WHERE id=?", (uid,)).fetchone()
    if exists:
        if support:
            con.execute("UPDATE units SET support=support+? WHERE id=?", (support, uid))
        # Also handles older databases as they are gradually accessed.
        index_unit(con, uid, label)
        return False
    con.execute("""INSERT INTO units(id,label,kind,description,url,citations,support)
        VALUES(?,?,?,?,?,?,?)""", (uid, label, kind, description, url, citations, support))
    event_node(con, uid, label)
    index_unit(con, uid, label)
    if kind in ('concept','relation'):
        con.execute('''INSERT OR IGNORE INTO unit_purity_scores(unit_id,score,reason)
            VALUES(?,?,?)''',(uid,purity_score,purity_reason))
        _purity_add_counter(con,'accepted_candidates')
        _purity_add_counter(con,'score_sum',purity_score)
    return True


def upsert_edge(con, src, dst, kind, w):
    if src == dst:
        return
    # Prevent dangling edges to rejected lexical fragments on all paths.
    for endpoint in (src,dst):
        if endpoint.startswith('concept:') and score_math_unit_purity(
                endpoint.split(':',1)[1],'concept')[0]<75:
            return
    delta = round(float(w), 4)
    con.execute("""INSERT INTO edges(src,dst,kind,weight,support) VALUES(?,?,?,?,1)
        ON CONFLICT(src,dst,kind) DO UPDATE SET
            weight=weight+excluded.weight, support=support+1""", (src, dst, kind, delta))
    # Preserve critical theory/relation events, but do not write millions of
    # redundant replay rows for source-only lookup edge updates.
    if kind in ('theory-paper','concept-relation','relation-object','source-relation',
                'wikipedia-cites-paper','wiki-concept'):
        con.execute("""INSERT INTO build_events(action,src,dst,edge_kind,delta,label)
            VALUES('edge',?,?,?,?,?)""", (src, dst, kind, delta, kind))


def add_theory_memory(con, title, url, description):
    """A visible, persisted Wikipedia node appears BEFORE OpenAlex searching."""
    uid = "theory:" + title.casefold()
    with con:
        con.execute("INSERT OR IGNORE INTO theories(name,url) VALUES(?,?)", (title, url))
        existing = con.execute('SELECT description FROM units WHERE id=?',(uid,)).fetchone()
        needs_description = bool(description) and (not existing or not existing[0])
        new = add_unit(con, uid, title, "theory", description, url)
        if needs_description:
            con.execute('UPDATE units SET description=? WHERE id=?',(description,uid))
            for term, strength in keyphrases(description, title, limit=7):
                cid = "concept:" + norm_concept(term)
                quote = next((x for x in split_sentences(description)
                              if term in x.casefold()), description[:500])
                if score_math_unit_purity(term,'concept')[0]<75:
                    continue
                add_unit(con, cid, term, "concept", quote[:550], url, support=1)
                upsert_edge(con, uid, cid, "wiki-concept", 0.35 + strength)
                upsert_edge(con, cid, uid, "concept-theory-source", 0.19 + .12*strength)
            add_math_relation_memories(con,uid,url,description,limit=10)
    return new


# These words are *recognition anchors*, not a hand-coded mathematical ontology.
# A relation is admitted only with an actual source sentence and an explicit predicate.
MATH_ANCHORS = (
    'calculus', 'differential calculus', 'integral calculus', 'multivariable calculus',
    'partial derivative', 'partial derivatives', 'partial differentiation',
    'partial differential equation', 'partial differential equations',
    'ordinary differential equation', 'ordinary differential equations',
    'heat equation', 'wave equation', 'laplace equation', 'poisson equation',
    'navier stokes equation', 'gradient', 'divergence', 'curl', 'laplacian',
    'hessian', 'jacobian', 'fourier transform', 'laplace transform',
    'eigenvalue', 'eigenvector', 'eigenvalues', 'eigenvectors',
    'matrix', 'linear algebra', 'linear operator', 'differential operator',
    'boundary condition', 'initial condition', 'boundary value problem',
    'initial value problem', 'finite element method', 'finite difference method',
    'spectral method', 'weak solution', 'strong solution', 'weak formulation',
    'variational principle', 'functional analysis', 'sobolev space',
    'hilbert space', 'banach space', 'normed space', 'inner product',
    'convex function', 'convex optimization', 'optimization',
    'lagrange multiplier', 'lagrange multipliers', 'gradient descent',
    'stochastic process', 'markov chain', 'markov process',
    'probability distribution', 'bayesian inference', 'statistical inference',
    'maximum likelihood estimation', 'fisher information',
    'information geometry', 'regression analysis', 'time series',
    'linear regression', 'dynamical system', 'control system',
    'stability', 'convergence', 'continuity', 'differentiability',
    'integrability', 'existence', 'uniqueness', 'boundedness',
    'fixed point', 'fixed point theorem', 'taylor series', 'fourier series',
    'green function', 'green functions', 'fundamental solution',
    'riemannian manifold', 'manifold', 'tensor', 'differential geometry',
    'geometric calculus', 'geometric algebra', 'clifford algebra',
    'numerical analysis', 'numerical integration', 'numerical differentiation',
    'graph theory', 'spectral graph theory', 'spectral theory',
    'monte carlo method', 'mathematical finance', 'econometrics',
    'set theory', 'proof theory', 'model theory', 'category theory',
    'commutative algebra', 'abstract algebra', 'representation theory',
    'group theory', 'ring theory', 'algebraic topology', 'homology', 'cohomology',
    'homotopy', 'algebraic geometry', 'number theory', 'combinatorics',
    'measure theory', 'real analysis', 'complex analysis', 'harmonic analysis',
    'ergodic theory', 'dynamical systems', 'calculus of variations',
    'stochastic differential equation', 'ito calculus', 'martingale',
    'point process', 'gaussian process', 'inverse problem', 'ill posed problem',
    'regularization', 'integral equation', 'integral operator',
    'nonlinear dynamics', 'reaction diffusion equation', 'transport equation',
    'optimal transport', 'bifurcation theory', 'fixed point iteration',
    'finite volume method', 'finite element analysis', 'finite difference scheme',
    'stochastic control', 'system identification', 'state space model',
    'kalman filter', 'particle filter', 'graph neural network',
    'information theory', 'coding theory', 'computational complexity',
    'mathematical epidemiology', 'compartmental model', 'sir model',
    'biostatistics', 'population dynamics', 'computational neuroscience',
    'mathematical biology', 'mathematical ecology', 'spatial statistics',
    'agent based model', 'social choice theory', 'network science',
    'econometric model', 'portfolio optimization', 'option pricing',
    'stochastic volatility', 'black scholes model', 'risk neutral pricing',
    'computational fluid dynamics', 'continuum mechanics',
    'chemical kinetics', 'reaction kinetics', 'mathematical physics',
    'statistical mechanics', 'quantum information theory',
)
_MATH_KEYWORD_CUES={'equation','equations','operator','operators','transform','transforms','derivative','derivatives',
                   'integral','integrals','gradient','tensor','tensors','space','spaces','theorem',
                   'distribution','distributions','function','functions','algorithm','algorithms',
                   'series','formulation','inequality','norm','norms','matrix','matrices',
                   'geometry','geometric','stochastic','statistics','optimization','approximation',
                   'differentiation','dynamics','eigenvalue','eigenvalues','eigenvector','eigenvectors',
                   'convergence','stability','spectral','regression','variation','variational'}
MATH_COMMON_BLOCKLIST = {'students', 'student', 'engineering', 'mathematics',
                         'financial', 'mathematical', 'results', 'method',
                         'paper', 'research', 'applications', 'equations'}
_MATH_ANCHOR_PATTERNS = [(phrase, re.compile(r'(?<![A-Za-z])'+re.escape(phrase)+r'(?![A-Za-z])',re.I))
                         for phrase in sorted(MATH_ANCHORS,key=len,reverse=True)]

# v10.1: Conservative mathematical vocabulary gate. New concepts must be
# identifiable mathematical objects, operations, methods, or predicates.
# These are *lexical source-evidence filters*, NOT logical proofs or embeddings.
MATH_CONCEPT_HEADS = frozenset(['theorem', 'lemma', 'corollary', 'proposition', 'conjecture', 'proof', 'equation', 'equations', 'operator', 'operators', 'derivative', 'derivatives', 'differential', 'differentiation', 'integral', 'integrals', 'integration', 'transform', 'transforms', 'matrix', 'matrices', 'vector', 'vectors', 'tensor', 'tensors', 'eigenvalue', 'eigenvalues', 'eigenvector', 'eigenvectors', 'eigenfunction', 'spectrum', 'spectral', 'decomposition', 'factorization', 'factorisation', 'distribution', 'distributions', 'regression', 'estimator', 'estimation', 'inference', 'optimization', 'minimization', 'minimisation', 'maximization', 'maximisation', 'convexity', 'convex', 'algorithm', 'algorithms', 'method', 'methods', 'scheme', 'schemes', 'discretization', 'discretisation', 'approximation', 'approximations', 'convergence', 'stability', 'asymptotics', 'functional', 'function', 'functions', 'spaces', 'space', 'manifold', 'manifolds', 'metric', 'metrics', 'norm', 'norms', 'inequality', 'inequalities', 'identity', 'identities', 'gradient', 'gradients', 'jacobian', 'hessian', 'kernel', 'kernels', 'boundary', 'boundaries', 'condition', 'conditions', 'stochastic', 'probability', 'probabilistic', 'variational', 'dynamics', 'system', 'systems', 'process', 'processes', 'model', 'models', 'calculus', 'algebra', 'geometry', 'topology', 'statistic', 'statistics', 'covariance', 'variance', 'correlation', 'entropy', 'entropy', 'rate', 'pricing', 'hedging', 'portfolio', 'arbitrage', 'volatility', 'risk', 'recurrence', 'sequence', 'series', 'simulation', 'monte', 'carlo', 'graph', 'graphs', 'network', 'networks', 'filtering', 'filter', 'quadrature', 'interpolation', 'differentiation', 'control', 'controllability', 'observability', 'homology','cohomology','homotopy','category','categories','group','groups','ring','rings','module','modules','functor','functors','sheaf','sheaves','filtration','martingale','process','dynamics','transport','bifurcation','identifiability','parameterization','parameterisation','equilibrium','entropy','regularization','regularisation','simulation'])
# Terms with a generic head (model/method/system/etc.) need a second
# mathematical qualifier. 'analysis', 'students', 'chromatography' never qualify.
MATH_GENERIC_HEADS = frozenset({'method','methods','model','models','system',
    'systems','process','processes','network','networks','algorithm','algorithms',
    'application','applications','simulation','analysis','function','functions',
    'condition','conditions','study','studies','estimate','estimation'})
MATH_SPECIFIERS = frozenset(['linear', 'nonlinear', 'stochastic', 'partial', 'differential', 'ordinary', 'spectral', 'numerical', 'matrix', 'tensor', 'eigenvalue', 'eigenvector', 'eigenfunction', 'convex', 'bayesian', 'likelihood', 'probability', 'probabilistic', 'dynamical', 'finite', 'element', 'difference', 'volume', 'wavelet', 'fourier', 'laplace', 'hessian', 'jacobian', 'integral', 'derivative', 'variational', 'hilbert', 'sobolev', 'banach', 'riemannian', 'topological', 'algebraic', 'statistical', 'regression', 'graph', 'optimal', 'optimization', 'operator', 'functional', 'equilibrium', 'covariance', 'portfolio', 'asset', 'pricing', 'option', 'volatility', 'econometric', 'time', 'stability', 'convergence', 'interpolation', 'quadrature', 'monte', 'carlo', 'symplectic', 'control', 'geometric', 'random', 'markov', 'gaussian', 'stochasticity', 'gradient', 'boundary', 'initial', 'recursive','algebraic','topology','category','measure','ergodic','geometric','bio','biological','epidemiological','population','compartmental','spatial','network','neural','information','chemical','fluid','transport','inverse','regularization','quantum','agent','reaction','diffusion'])
MATH_ANCHOR_CANONICAL=frozenset(canonical_phrase(x) for x in MATH_ANCHORS)
# Search-topic expansion is only for deciding whether a paper is relevant;
# these are NOT stored as equivalences or new edges.
MATH_TOPIC_EXPANSIONS={
    'linear algebra':{'matrix','eigenvalue','eigenvector','linear','spectral','rank',
                     'decomposition','tensor','determinant'},
    'calculus':{'derivative','differential','integral','gradient','jacobian',
                'hessian','differentiation','integration','limit'},
    'statistics':{'regression','inference','estimate','estimator','probability',
                  'distribution','variance','covariance','bayesian'},
    'mathematical statistics':{'regression','inference','estimate','probability',
                              'distribution','variance','covariance'},
    'partial differential equation':{'differential','partial','equation','boundary',
                                    'operator','laplacian','solution'},
    'graph theory':{'graph','vertex','edge','network','adjacency','laplacian'},
    'mathematical finance':{'financial','portfolio','option','pricing','volatility',
                           'asset','stochastic','hedging','arbitrage'},
    'biostatistics':{'clinical','patient','cohort','survival','regression','risk','hazard','biological'},
    'mathematical biology':{'biological','population','ecological','reaction','species','dynamics','differential'},
    'computational neuroscience':{'neural','neuron','neuronal','synaptic','cortical','brain','dynamical'},
    'mathematical epidemiology':{'epidemic','infection','infectious','compartmental','susceptible','reproduction'},
    'mathematical economics':{'economic','market','equilibrium','utility','game','optimization'},
    'control theory':{'feedback','controller','controllability','stability','state','lyapunov'},
    'mathematical physics':{'quantum','physical','wave','field','symmetry','operator','particle'},
    'numerical analysis':{'numerical','error','convergence','discretization',
                          'finite','algorithm','approximation'},
}
_MATH_ADJECTIVE_ENDINGS={'spectral','functional','stochastic','differential',
                            'convex','probabilistic','variational','linear','nonlinear'}
MATH_SINGLE_ACCEPT = frozenset({canonical_phrase(x) for x in MATH_ANCHORS
    if len(x.split()) == 1 and canonical_phrase(x) not in
    {'analysis','existence','uniqueness','stability','continuity','convergence',
     'integrability','differentiability','boundedness','statistics','optimization'}})
MATH_PAPER_NEGATIVE = re.compile(
    r'\b(?:chromatograph\w*|spectrometr\w*|assay\w*|student\w*|school\w*|'
    r'pedagog\w*|curriculum|teach\w*|classroom\w*|educational)\b',re.I)
MATH_TOPIC_RESEARCH = re.compile(
    r'\b(?:mathematical|mathematics|algebra|calculus|differential|partial|'
    r'eigen(?:value|vector|function)|matrix|matrices|tensor|operator|'
    r'variational|stochastic|probability|statistical|statistics|bayesian|'
    r'numerical|finite.element|finite.difference|finite.volume|spectral|'
    r'fourier|laplace|optimization|optimal|convex|regression|'
    r'econometric|portfolio.optimization|asset.pricing|option.pricing|'
    r'financial.mathematics|time.series|risk.model|queueing|markov|'
    r'control.theory|linear.programming|nonlinear|functional.analysis|'
    r'monte.carlo|approximation|convergence|asymptotic|stability|'
    r'boundary.value|initial.value|theorem|lemma|proof|inequality|'
    r'dynamical.system|graph.theory|network.flow|algorithmic|'
    r'computational.complexity|simulation.model|algebraic|topolog|homolog|homotop|'
    r'cohomolog|combinator|group.theory|ring.theory|measure.theory|'
    r'optimal.transport|inverse.problem|regularization|martingale|'
    r'point.process|gaussian.process|kalman|bifurcation|ergodic|'
    r'population.dynamics|compartmental.model|sir.model|reaction.diffusion|'
    r'control.system|state.space.model|information.theory|entropy)\b',re.I)


_DOMAIN_GENERIC_BAD_WORDS = frozenset({
    'student','students','introduction','intros','overview','review','reviews',
    'application','applications','results','conclusion','abstract','paper',
    'study','studies','article','chapter','author','authors','figure','table',
    'important','various','several','different','novel','recent','present','approach',
    'people','research','general','significant','based','using','used','today',
})
_DOMAIN_GENERIC_HEADS = frozenset({
    'theory','model','method','system','algorithm','framework','process','effect',
    'mechanism','principle','technique','technology','protocol','policy',
    'procedure','strategy','structure','condition','factor','function',
    'experiment','intervention','treatment','regulation','analysis','assessment',
    'architecture','methodology','approach','design','material','device',
    'network','disease','syndrome','protein','gene','cell','species','market',
    'organization','behaviour','behavior','equation','operator','matrix',
    'transformation','inference','estimation','distribution','optimization',
    'measurement','simulation','language','concept','tradition',
})

@lru_cache(maxsize=160000)
def general_concept_quality(term):
    """Conservative domain-neutral label gate; no broad stopword n-gram spam."""
    phrase=canonical_phrase(term)
    words=phrase.split()
    if not 3<=len(phrase)<=95 or not 1<=len(words)<=5:
        return False,'invalid_length'
    if any((w in (STOP - _DOMAIN_GENERIC_HEADS) or
            w in _DOMAIN_GENERIC_BAD_WORDS) for w in words):
        return False,'generic_phrase'
    if not all(re.fullmatch(r'[a-z0-9][a-z0-9-]*',w) for w in words):
        return False,'unsupported_phrase'
    if len(words)==1 and len(phrase)<6 and phrase not in ('gene','cell','risk','law'):
        return False,'weak_single_term'
    if len(words)>=2 and not (set(words)&_DOMAIN_GENERIC_HEADS or
            any(len(w)>=7 for w in words)):
        return False,'weak_multiword_term'
    return True,'source_term_candidate'

def general_keyphrases(text, title, limit=12):
    """Conservative extractive labels, with source text occurrence required.

    Prefer title noun phrases and repeated multiword spans, without inventing
    cross-domain semantic relations. Nothing is accepted solely by citation count.
    """
    title_words=re.findall(r'[a-z][a-z0-9-]*',str(title).casefold())[:32]
    corpus=' '.join(re.findall(r'[a-z][a-z0-9-]*',str(text or '').casefold()))[:45000]
    words=corpus.split()[:8500]
    scores=defaultdict(float)
    word_counts=defaultdict(int)
    for word in words:word_counts[word]+=1
    for tokens,base in ((title_words,2.3),(words,0.0)):
        for j in range(len(tokens)):
            for size in (3,2,1):
                if j+size>len(tokens): continue
                phrase=' '.join(tokens[j:j+size])
                valid,_=general_concept_quality(phrase)
                if not valid:continue
                if size==1 and base==0 and word_counts[tokens[j]]<3:continue
                if size>=2 and base==0 and j>0 and j%4!=0:continue
                scores[phrase]+=1.15+base+(size-1)*.14
    # Anchor to the TITLE: unrelated repeated incidental phrases should not win.
    ranked=sorted(scores.items(),key=lambda z:(-z[1],-len(z[0]),z[0]))
    chosen=[]
    for phrase,score in ranked:
        if any(phrase in other and phrase!=other for other,_ in chosen):continue
        chosen.append((phrase,score))
        if len(chosen)>=limit:break
    best=max([x[1] for x in chosen],default=1.0)
    return [(p,round(v/best,4)) for p,v in chosen]

def general_paper_quality(paper, subject):
    title=str(paper.get('display_name') or '').strip()
    abstract=(paper.get('_abstract_text') or
        abstract_from_index(paper.get('abstract_inverted_index')) or '')
    if len(title)<8:return False,0.0,'missing_title'
    subject_words=set(lexical_tokens(subject))-_DOMAIN_GENERIC_BAD_WORDS
    title_words=set(lexical_tokens(title))
    abstract_words=set(lexical_tokens(abstract[:12000]))
    if not subject_words:return False,0.0,'unusable_subject'
    overlap_title=len(subject_words & title_words)
    overlap_abstract=len(subject_words & abstract_words)
    exact=canonical_phrase(subject) in canonical_phrase(title)
    # Broad headings such as Medicine or Business are discipline labels;
    # allow two independently grounded field cues, without treating them as
    # synonyms and without fabricating any relation edge.
    profile=domain_profile()
    cues={_lemma(w) for w in profile.get('keywords',())}
    observed=title_words|abstract_words
    title_cues=title_words&cues
    all_cues=observed&cues
    broad=canonical_phrase(subject) in {canonical_phrase(v) for v in profile['entries']}
    if broad and (len(title_cues)>=2 or (len(title_cues)>=1 and len(all_cues)>=2)):
        overlap_title=max(overlap_title,1)
        overlap_abstract=max(overlap_abstract,2)
    if not (exact or overlap_title or overlap_abstract):
        return False,0.0,'no_topic_overlap'
    if len(subject_words)>=3 and overlap_title<2 and overlap_abstract<2 and not exact:
        return False,0.0,'insufficient_specific_overlap'
    if not abstract and not (exact or overlap_title>=2):
        return False,0.0,'insufficient_title_only_evidence'
    score=min(1.0,.24+(.40 if exact else 0)+.17*min(2,overlap_title)+
              .1*min(2,overlap_abstract)+(.08 if abstract else 0))
    return True,round(score,3),'lexical_topic_evidence'

def general_topic_quality(title, article=''):
    if not math_page_title_ok(title):return False,'invalid_page_title'
    if len(title.strip())<4:return False,'short_title'
    # The article must be a real Wikipedia page; non-methodological titles are
    # not a reliable basis for rejecting entire disciplines (e.g. education).
    return True,'wikipedia_subject_candidate'

def math_concept_quality(term):
    return (general_concept_quality(term) if active_domain()!='mathematics'
            else _pure_math_concept_quality(term))


@lru_cache(maxsize=120000)
def _pure_math_concept_quality(term):
    """Return (accepted, reason) without inventing a semantic relationship.

    Deny generic substrings; permit curated mathematical singleton names,
    mathematical adjective-noun phrases, and longer named constructs.
    """
    phrase = canonical_phrase(term)
    if not phrase or len(phrase) < 3 or len(phrase) > 100:
        return False, 'invalid_length'
    words = phrase.split()
    if len(words)>6 or all(w.isdigit() for w in words):
        return False, 'invalid_shape'
    if MATH_PAPER_NEGATIVE.search(phrase):
        return False, 'off_domain_phrase'
    if len(words)==1:
        return (phrase in MATH_SINGLE_ACCEPT,
                'curated_math_term' if phrase in MATH_SINGLE_ACCEPT else 'generic_word')
    if phrase in MATH_ANCHOR_CANONICAL:
        return True,'curated_math_phrase'
    if words[0] in {'prove','proofs','shows','shown','studies','studied','using',
                    'introduce','novel','different','application','analysis','solve','solving','derive','deriving','present'}:
        return False,'sentence_fragment'
    if any(w in STOP and w not in MATH_CONCEPT_HEADS and w not in MATH_SPECIFIERS for w in words):
        return False,'generic_stopword'
    if words[-1] not in MATH_CONCEPT_HEADS or words[-1] in _MATH_ADJECTIVE_ENDINGS:
        return False,'non_noun_fragment'
    heads={_lemma(w) for w in words} & MATH_CONCEPT_HEADS
    if not heads:
        return False,'no_mathematical_head'
    if heads.issubset(MATH_GENERIC_HEADS) and not (set(words) & MATH_SPECIFIERS):
        return False,'generic_head_without_math_qualifier'
    if len(words)>=2 and not (set(words)&MATH_SPECIFIERS or
        any(w not in MATH_GENERIC_HEADS and w in MATH_CONCEPT_HEADS for w in words)):
        return False,'weak_mathematical_context'
    return True,'mathematical_expression'


def paper_math_quality(paper, theory):
    """High-precision paper relevance gate: zero citation-count shortcuts.

    Unknown abstracts can pass ONLY when title itself is unmistakably
    mathematical and topically aligned. Conservative false negatives are
    reported; accepted papers are not thereby mathematically validated.
    """
    if active_domain()!='mathematics': return general_paper_quality(paper,theory)
    title=str(paper.get('display_name') or '').strip()
    abstract=(paper.get('_abstract_text') or
        abstract_from_index(paper.get('abstract_inverted_index')) or '')
    title_terms=set(lexical_tokens(title))
    theory_terms=set(lexical_tokens(theory))
    aterms=set(lexical_tokens(abstract[:20000])) if abstract else set()
    # Topic vocabulary is used for SEARCH RELEVANCE only, never to assert
    # semantic equivalence between memories or insert invented graph edges.
    if 'finance' in theory_terms:
        if {'financial','portfolio','asset','pricing','volatility','hedging'} & (title_terms|aterms):
            title_terms.add('finance')
            if MATH_TOPIC_RESEARCH.search(title) and 'mathematical' in theory_terms:
                title_terms.add('mathematical')
    if 'statistic' in theory_terms and 'statistical' in (title_terms|aterms):
        title_terms.add('statistic')
    if 'optimization' in theory_terms and 'optimisation' in (title_terms|aterms):
        title_terms.add('optimization')
    shared_title=len(title_terms&theory_terms)
    shared_abs=len(aterms&theory_terms)
    exact=canonical_phrase(theory) in canonical_phrase(title)
    math_title=bool(MATH_TOPIC_RESEARCH.search(title))
    math_abs=bool(MATH_TOPIC_RESEARCH.search(abstract[:10000]))
    topic_key=canonical_phrase(theory)
    expanded={_lemma(x) for x in MATH_TOPIC_EXPANSIONS.get(topic_key,set())}
    # An explicit pair of independent topic-specific math terms may substitute
    # for an exact broad discipline label (linear algebra -> matrix/eigenvalue).
    diagnostic_terms=expanded & (title_terms | aterms)
    diagnostic_title=expanded & title_terms
    if not exact and len(diagnostic_terms)>=2 and shared_title<2 and shared_abs<2:
        shared_title=max(shared_title,min(2,len(diagnostic_title)))
        shared_abs=max(shared_abs,min(2,len(diagnostic_terms)))
    unrelated=bool(MATH_PAPER_NEGATIVE.search(title))
    if not title or len(title)<6:
        return False,0.0,'missing_title'
    if not (shared_title or shared_abs or exact):
        return False,0.0,'no_topic_overlap'
    if unrelated and not (math_title and shared_title>=2):
        return False,0.0,'strong_nonmath_title'
    if not math_title and not (math_abs and (shared_title or shared_abs>=2)):
        return False,0.0,'no_math_evidence'
    # Loose one-word overlap with a long topic is not good evidence.
    if len(theory_terms)>=2 and shared_title<2 and shared_abs<2 and not exact:
        if not ('finance' in theory_terms and math_title and
                {'portfolio','financial','volatility','asset','pricing'} & (title_terms|aterms)):
            return False,0.0,'partial_topic_only'
    if not abstract and not math_title:
        return False,0.0,'title_only_ambiguous'
    score=round(min(1.0,(0.40 if math_title else .1)+
        (0.22 if math_abs else 0)+(.22 if exact else .12*min(2,shared_title))+
        .07*min(2,shared_abs)),3)
    return True,score,('math_title_abstract' if abstract else 'math_title_only')


def math_topic_quality(title, wiki_text=''):
    """A Wikipedia math category is not by itself proof of mathematical content."""
    if active_domain()!='mathematics': return general_topic_quality(title,wiki_text)
    if MATH_PAPER_NEGATIVE.search(title or ''):
        return False,'off_domain_wikipedia_title'
    if MATH_TOPIC_RESEARCH.search(title or '') or canonical_phrase(title) in MATH_ANCHOR_CANONICAL or any(
            re.search(r'(?<![a-z])'+re.escape(t)+r'(?![a-z])', (title or '').lower())
            for t in ('algebra','calculus','econometrics','queueing theory','game theory',
                      'probability','stochastic','forecasting','optimization','numerical')):
        return True,'explicit_math_topic'
    # Unknown eponym articles may be genuine (e.g. a theorem named for its
    # author); require mathematical evidence from more than one anchor.
    passage=(wiki_text or '')[:7000]
    found=0
    for _term,pat in _MATH_ANCHOR_PATTERNS:
        if pat.search(passage):
            found+=1
            if found>=3:return True,'source_mathematical_context'
    return False,'insufficient_math_topic_evidence'


def mathematical_coverage_report(con):
    """Count evidence-tagged accepted papers by application area, with gaps.

    Cross-field papers may count in multiple areas; the sum is NOT unique
    accepted papers. Pure mathematics appears as a separate untagged bucket.
    """
    counts=dict(con.execute('SELECT area,COUNT(*) FROM paper_math_applications GROUP BY area'))
    accepted=int(con.execute('SELECT COUNT(*) FROM papers').fetchone()[0])
    tagged=int(con.execute('SELECT COUNT(DISTINCT paper_id) FROM paper_math_applications').fetchone()[0])
    # Stream grouped counts exactly once; avoid iterating the entire topic
    # dictionary 16 times on million-row networks.
    name_to_branch={canonical_phrase(name):branch
                    for branch,names in MATH_RESEARCH_AREAS.items() for name in names}
    branch_stats={branch:{'paper_topic_links':0,'covered_seed_topics':0,
                          'known_seed_topics':len(set(names))}
                  for branch,names in MATH_RESEARCH_AREAS.items()}
    for theory,total in con.execute('SELECT theory,COUNT(*) FROM paper_theories GROUP BY theory'):
        branch=name_to_branch.get(canonical_phrase(theory))
        if branch:
            branch_stats[branch]['paper_topic_links']+=total
            branch_stats[branch]['covered_seed_topics']+=1
    return {'papers':accepted,'tagged_papers':tagged,
            'untagged_including_pure_math':max(0,accepted-tagged),
            'application_areas':{area:counts.get(area,0) for area in MATH_APPLICATION_TAGS},
            'mathematical_seed_branches':branch_stats,
            'note':' application Domain and branch can may overlap in counts ; pure Mathematics or not yet category Paper all can can No application label ;0  represents Current lack of Log , NOT equal to that Domain NOT store in .'}


def quality_counts(con):
    return {state:count for state,count in con.execute(
        'SELECT state, COUNT(*) FROM paper_quality_decisions GROUP BY state')}


def store_paper_quality(con, paper, theory, accepted, confidence, reason):
    uid=str(paper.get('id') or paper.get('doi') or paper.get('display_name') or '')
    con.execute("""INSERT INTO paper_quality_decisions(theory,paper_id,state,confidence,reason)
                   VALUES(?,?,?,?,?) ON CONFLICT(theory,paper_id) DO UPDATE SET
                   state=excluded.state, confidence=excluded.confidence,
                   reason=excluded.reason, updated=CURRENT_TIMESTAMP""",
                (theory,uid,'accepted' if accepted else 'rejected',float(confidence),reason))


def quick_math_node_ok(label, kind):
    """On-demand legacy filter: avoids scanning 1.5M nodes at startup."""
    if active_domain()!='mathematics':
        return general_concept_quality(label)[0] if kind=='concept' else True
    if kind=='concept':return math_concept_quality(label)[0]
    if kind=='paper':
        return bool(MATH_TOPIC_RESEARCH.search(label or '')) and not (
            MATH_PAPER_NEGATIVE.search(label or '') and not
            re.search(r'\b(?:mathematical|numerical|optimization|algorithm|regression)\b',label or '',re.I))
    return True


# Fast deterministic lexicon-based extraction: NOT TF-IDF of arbitrary words.
_MATH_NGRAM_RE = re.compile(r"\b[a-z][a-z0-9-]*(?:\s+[a-z][a-z0-9-]*){0,5}\b", re.I)

# Only a predicate located BETWEEN two expressions licenses a typed claim.
_PREDICATES = (
    ('defined_as', re.compile(r'\b(?:is|are)\s+defined\s+(?:as|by)\b|\bdenotes?\b|\brepresents?\b',re.I)),
    ('is_a', re.compile(r'\b(?:is|are)\s+(?:a|an|the|one\s+of\s+the)\b|\b(?:is|are)\s+special\s+cases?\s+of\b',re.I)),
    ('generalizes', re.compile(r'\bgenerali[sz]es?\b|\bextends?\b',re.I)),
    ('equivalent_to', re.compile(r'\bequivalent\s+to\b|\bis\s+equivalent\s+to\b',re.I)),
    ('implies', re.compile(r'\bimplies?\b|\bentails?\b',re.I)),
    ('derived_from', re.compile(r'\bderived\s+from\b|\bobtained\s+from\b',re.I)),
    ('used_for', re.compile(r'\bused\s+(?:to|for|in)\b|\bapplied\s+to\b',re.I)),
    ('solves', re.compile(r'\bsolves?\b|\bsolutions?\s+of\b',re.I)),
    ('depends_on', re.compile(r'\bdepends?\s+on\b|\brequires?\b',re.I)),
    ('approximates', re.compile(r'\bapproximates?\b|\bapproximations?\s+(?:to|of)\b',re.I)),
    ('satisfies', re.compile(r'\bsatisf(?:y|ies)\b|\bsubject\s+to\b',re.I)),
    ('relates_to', re.compile(r'\brelated\s+to\b|\bconnected\s+to\b',re.I)),
)

def general_terms_in_sentence(sentence, extra=()):
    phrases=[]
    for candidate in list(extra)[:28]:
        label=canonical_phrase(str(candidate or ''))
        if general_concept_quality(label)[0] and label not in phrases:
            phrases.append(label)
    # Detect explicit domain-general named concepts, grounded in the source.
    for m in re.finditer(r'\b(?:[a-z][a-z0-9-]*\s+){1,3}(?:'+
            '|'.join(sorted(_DOMAIN_GENERIC_HEADS,key=len,reverse=True))+r')\b',
            sentence,re.I):
        label=canonical_phrase(m.group())
        if general_concept_quality(label)[0] and label not in phrases:
            phrases.append(label)
    # Explicit relation sentences may have a one-word predicate object
    # (e.g. 'a clinical trial is an experiment'). Include known research
    # object heads only when they literally occur in that sentence.
    for word in _DOMAIN_GENERIC_HEADS:
        if len(word)>=5 and general_concept_quality(word)[0]:
            if re.search(r'(?<![A-Za-z])'+re.escape(word)+r'(?![A-Za-z])',sentence,re.I):
                if word not in phrases:phrases.append(word)
    found=[]
    for label in sorted(phrases,key=len,reverse=True):
        for m in re.finditer(r'(?<![A-Za-z])'+re.escape(label)+r'(?![A-Za-z])',sentence,re.I):
            if any(m.start()<b and a<m.end() for a,b,_ in found):continue
            found.append((m.start(),m.end(),label))
    return sorted(found)[:24]


def math_terms_in_sentence(sentence, extra=()):
    """Return nonoverlapping source-occurring math terms with offsets."""
    if active_domain()!='mathematics':
        return general_terms_in_sentence(sentence,extra)
    found=[]
    candidates=list(_MATH_ANCHOR_PATTERNS)
    for phrase in list(extra)[:18]:
        phrase=str(phrase or '').strip().lower()
        if (len(phrase)>6 and phrase not in MATH_COMMON_BLOCKLIST and
            len(phrase.split())<=4 and bool(set(phrase.split())&_MATH_KEYWORD_CUES)):
            candidates.append((phrase,re.compile(r'(?<![A-Za-z])'+re.escape(phrase)+r'(?![A-Za-z])',re.I)))
    for name,pattern in candidates:
        for match in pattern.finditer(sentence):
            if any(match.start()<b and a<match.end() for a,b,_ in found):
                continue
            found.append((match.start(),match.end(),canonical_phrase(name)))
    found.sort()
    # Remove exact duplicates that can arise from extra keyphrases.
    return list(dict.fromkeys(found))

def source_math_relations(text, extras=(), limit=16):
    """Extract *candidate* typed claims, not verified logical implications.

    The literal sentence remains attached to each relation for later checking.
    Co-mention alone is never enough to create a mathematical relation memory.
    """
    output=[];seen=set()
    sentences=re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])|[\r\n]+',html.unescape(text or ''))
    for sentence in sentences[:280]:
        sentence=' '.join(sentence.split()).strip()
        if not (18<=len(sentence)<=800):continue
        terms=math_terms_in_sentence(sentence,extras)
        for first,second in zip(terms,terms[1:]):
            a_end=first[1];b_start=second[0]
            if b_start<=a_end or b_start-a_end>105: continue
            between=sentence[a_end:b_start]
            if re.search(r'[.;!?]',between): continue
            predicate=next((kind for kind,pattern in _PREDICATES if pattern.search(between)),None)
            forbidden=('relates_to','used_for') if active_domain()=='mathematics' else ('relates_to',)
            if not predicate or predicate in forbidden or first[2]==second[2]:continue
            if not (math_concept_quality(first[2])[0] and
                    math_concept_quality(second[2])[0]):continue
            if len(between)>70:continue
            # Avoid treating conjunctions, long descriptions and negated claims
            # as affirmative equations or implications.
            if re.search(r'\b(?:not|never|without|cannot|doesn.t)\b',between,re.I):continue
            key=(first[2],predicate,second[2],sentence)
            if key in seen:continue
            seen.add(key)
            output.append((first[2],predicate,second[2],sentence[:550]))
            if len(output)>=limit:return output
    return output

def add_math_relation_memories(con, source_id, url, text, extras=(), limit=16):
    """Persist source-backed typed relation memories and their directed links."""
    n=0
    for lhs, predicate, rhs, sentence in source_math_relations(text,extras,limit):
        left_id='concept:'+norm_concept(lhs)
        right_id='concept:'+norm_concept(rhs)
        fingerprint='|'.join((lhs,predicate,rhs))
        rel_id='relation:'+hashlib.sha1(fingerprint.encode('utf-8')).hexdigest()[:24]
        exists=con.execute('SELECT 1 FROM relation_evidence WHERE relation_id=? AND source_id=? AND sentence=?',
                           (rel_id,source_id,sentence)).fetchone()
        if exists:continue
        add_unit(con,left_id,lhs,'concept',sentence,url,support=1)
        add_unit(con,right_id,rhs,'concept',sentence,url,support=1)
        label=f'{lhs}  — {predicate.replace("_"," ")} →  {rhs}'
        add_unit(con,rel_id,label,'relation',sentence,url,support=1)
        con.execute('INSERT OR IGNORE INTO relation_evidence(relation_id,source_id,sentence,source_url) VALUES(?,?,?,?)',
                    (rel_id,source_id,sentence,url or ''))
        # An asserted direction is kept as a chain with a distinct relation
        # unit.  Retrieval edges never masquerade as the inverse proposition.
        upsert_edge(con,left_id,rel_id,'concept-relation',.95)
        upsert_edge(con,rel_id,right_id,'relation-object',.95)
        if source_id.startswith('paper:') or source_id.startswith('theory:'):
            upsert_edge(con,source_id,rel_id,'source-relation',.45)
            upsert_edge(con,rel_id,source_id,'relation-source-reference',.20)
        n+=1
    return n

def norm_concept(term):
    # Canonical concept identity: singular/plural and curated math variants merge.
    # Old SQLite IDs are retained and searchable through unit_terms.
    return canonical_phrase(term)


def prepare_paper_payload(paper, text, lightweight=False, make_abc_clusters=False):
    """CPU-focused text extraction outside the DB writer lock for concurrency."""
    title = paper.get('display_name') or 'Untitled'
    abstract = ((paper.get('_abstract_text') or abstract_from_index(paper.get('abstract_inverted_index')))
                if not lightweight else '')
    source_text = ((abstract + '. ' + text) if text else abstract) or title
    phrases = keyphrases(source_text, title) if not lightweight else []
    summary = summarize(abstract or source_text[:8000], phrases) if not lightweight else ''
    uri=paper.get('doi') or paper['id']
    # Build source-grounded clusters *outside* the shared SQLite writer lock.
    # The other workers can continue fetching and extracting in parallel.
    abc_clusters=(abc_extract_input_clusters(paper['id'],title,abstract,text,uri)
                  if make_abc_clusters and not lightweight else None)
    return dict(title=title, abstract=abstract, source_text=source_text,
                phrases=phrases, summary=summary, abc_clusters=abc_clusters,
                abc_paper_id=paper['id'],
                citations=int(paper.get('cited_by_count') or 0),
                doi=paper.get('doi') or '', url=uri)


def paper_to_memory(con, theory, wiki_url, paper, score, text, fulltext, prepared=None):
    doi_key=normalize_doi(paper.get('doi'))
    if doi_key:
        existing_doi=con.execute('SELECT id FROM papers WHERE lower(doi)=? OR lower(doi)=?',
            ('https://doi.org/'+doi_key,doi_key)).fetchone()
        if existing_doi and existing_doi[0]!=paper['id']:
            paper['id']=existing_doi[0]
    accepted,confidence,reason=paper_math_quality(paper,theory)
    if not accepted:
        with con:
            store_paper_quality(con,paper,theory,False,confidence,reason)
        return False
    pid = paper["id"]
    paper_id = paper_unit_id(pid)
    theory_id = "theory:" + theory.casefold()
    if con.execute("SELECT 1 FROM paper_theories WHERE paper_id=? AND theory=?",
                   (pid, theory)).fetchone():
        return False
    data = prepared if prepared is not None else prepare_paper_payload(paper,text)
    title, abstract, source_text = data['title'], data['abstract'], data['source_text']
    phrases, summary = data['phrases'], data['summary']
    citations, doi, url = data['citations'], data['doi'], data['url']
    # Reuse papers already stored for other theories, but create a new theory->paper edge.
    first_time = not con.execute("SELECT 1 FROM papers WHERE id=?", (pid,)).fetchone()
    with con:
        store_paper_quality(con,paper,theory,True,confidence,reason)
        con.execute("INSERT OR IGNORE INTO theories(name,url) VALUES(?,?)", (theory, wiki_url))
        add_unit(con, theory_id, theory, "theory", "Wikipedia  research Topic article ", wiki_url)
        con.execute("""INSERT OR IGNORE INTO papers(id,title,year,citations,doi,url,abstract,summary,fulltext_used)
                        VALUES(?,?,?,?,?,?,?,?,?)""", (pid, title, paper.get("publication_year"),
                        citations, doi, url, abstract, summary, int(bool(fulltext))))
        add_unit(con, paper_id, title, "paper", summary, url, citations)
        con.execute("INSERT INTO paper_theories(paper_id,theory,score) VALUES(?,?,?)",
                    (pid, theory, float(score)))
        upsert_edge(con, theory_id, paper_id, "theory-paper", 0.8 + score / 3)
        for area,keyword in mathematical_application_tags(title,abstract).items():
            con.execute('INSERT OR IGNORE INTO paper_math_applications(paper_id,area,evidence) '
                        'VALUES(?,?,?)',(pid,area,keyword))
        if not first_time:
            if abc_enabled(con):abc_learn_paper(con,pid)
            return True
        title_and_source = title + ". " + source_text
        for term, strength in phrases:
            if score_math_unit_purity(term,'concept')[0]<75:
                _purity_reject(con,term,'candidate_prewrite_gate')
                continue
            unit_id = "concept:" + norm_concept(term)
            evidence = next((s for s in split_sentences(source_text)
                             if term in s.casefold()), "")[:550]
            add_unit(con, unit_id, term, "concept", evidence, url, support=1)
            con.execute("INSERT OR IGNORE INTO mentions(unit_id,paper_id,quote) VALUES(?,?,?)",
                        (unit_id, pid, evidence))
            upsert_edge(con, paper_id, unit_id, "paper-concept", 0.5 + 1.2 * strength)
            # Independent directed retrieval edge: concept -> the paper that mentions it.
            upsert_edge(con, unit_id, paper_id, "concept-paper-source", .22 + .12 * strength)
        # Claim nodes require an explicit predicate and keep literal source evidence.
        # No guessed mathematics is added from mere keyword co-occurrence.
        add_math_relation_memories(con,paper_id,url,title_and_source,
                                   extras=[term for term,_ in phrases],limit=18)
        # ABC is an independent learning engine; only enabled for opt-in networks.
        # A paper that passes existing math-quality gates is an effective
        # source event; source-link weights NEVER become ABC weights.
        abc_learn_paper(con,pid,fulltext=text if fulltext else '',
            prepared_clusters=data.get('abc_clusters') if data.get('abc_paper_id')==pid else None)
        # v10.1: DO NOT generate concept->concept from co-mention order.
        # Co-mention is not a mathematical relation; provenance paper-concept
        # edges and explicitly source-backed relation memories remain available.
    return True


def stats(con):
    return tuple(con.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
                 for t in ("theories", "papers", "units", "edges"))


def inspect_display_health(con, sample_size=1000):
    """Read-only network/view consistency inspection for large SQLite files.

    Uses bounded node/edge/position samples. Does NOT claim to inspect all
    millions of historical links; complete integrity scans require downtime.
    """
    result={'database':str(DB_PATH),'totals':dict(zip(
        ('theories','papers','nodes','edges'),stats(con))),'sample_size':sample_size}
    indexes={row[0] for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type='index'")}
    result['required_graph_indexes']={
        key:(key in indexes) for key in ('idx_edges_src','idx_units_kind_support')}
    node_rows=con.execute('SELECT id,label,kind,description FROM units '
                          'ORDER BY rowid DESC LIMIT ?',(sample_size,)).fetchall()
    supported={'theory','paper','concept','relation'}
    result['recent_node_sample']={
        'checked':len(node_rows),
        'unsupported_type':sum(kind not in supported for _,_,kind,_ in node_rows),
        'hidden_by_purity_gate':sum(
            (kind in ('concept','paper') and not quick_math_node_ok(label,kind)) or
            (kind=='theory' and not math_topic_quality(label,desc or '')[0]) or
            (kind=='relation' and (lambda p:len(p)<3 or not(
                math_concept_quality(p[0])[0] and math_concept_quality(p[-1])[0]))(
                   re.split(r'\s*[—→]\s*',label or '')))
            for _,label,kind,desc in node_rows)}
    edge_rows=con.execute('SELECT src,dst FROM edges ORDER BY rowid DESC LIMIT ?',
                          (sample_size,)).fetchall()
    endpoint_ids=set(uid for src,dst in edge_rows for uid in (src,dst))
    found=set()
    for start in range(0,len(endpoint_ids),400):
        part=list(endpoint_ids)[start:start+400]
        found.update(r[0] for r in con.execute('SELECT id FROM units WHERE id IN ('+
                     ','.join('?' for _ in part)+')',part))
    result['recent_edge_sample']={
        'checked':len(edge_rows),
        'missing_endpoints':sum(src not in found or dst not in found for src,dst in edge_rows)}
    coordinate_rows=con.execute('SELECT x,y,z FROM positions ORDER BY rowid DESC LIMIT ?',
                                (sample_size,)).fetchall()
    result['recent_position_sample']={
        'checked':len(coordinate_rows),
        'invalid_or_extreme':sum(not all(math.isfinite(v) and abs(v)<1e6 for v in pos)
                                  for pos in coordinate_rows)}
    result['note']=' Only a recent sample , Cannot replace full-database completeness check ; not yet modify Database .'
    return result


def repair_existing_associations(progress=None):
    """Idempotent, provenance-only enhancement for existing SQLite networks.

    Adds searchable normalized tokens for old nodes and independent *directed*
    evidence traversal edges. Does not invent semantic/causal connections.
    Old paper/concept and wiki/concept edges are never removed.
    """
    with database() as con:
        ready = con.execute("SELECT value FROM network_meta WHERE key='lexical_v5'").fetchone()
        if ready and ready[0] == '1':
            return {'indexed':0,'bridged':0,'cached':True}
        total = con.execute('SELECT COUNT(*) FROM units').fetchone()[0]
        indexed = 0
        cursor = con.execute('SELECT id,label FROM units ORDER BY rowid')
        while True:
            batch = cursor.fetchmany(600)
            if not batch: break
            with con:
                for uid,label in batch:
                    index_unit(con,uid,label or '')
            indexed += len(batch)
            if progress and indexed % 3000 < 600:
                progress(f' already Build  {indexed:,}/{total:,}  items Memory unit term form Index ')
        bridged = 0
        for src_kind, dest_kind, mult in (
            ('paper-concept','concept-paper-source',.24),
            ('wiki-concept','concept-theory-source',.30)):
            # Add event records for newly derived edges so history remains honest.
            with con:
                con.execute("""INSERT INTO build_events(action,src,dst,edge_kind,delta,label)
                    SELECT 'edge', e.dst,e.src,?,MIN(0.5,e.weight*?),
                           ' Source Traceable Reverse lookup Link ( not causal )'
                    FROM edges e WHERE e.kind=?
                      AND NOT EXISTS (SELECT 1 FROM edges r
                        WHERE r.src=e.dst AND r.dst=e.src AND r.kind=?)""",
                    (dest_kind,mult,src_kind,dest_kind))
                old=con.total_changes
                con.execute("""INSERT OR IGNORE INTO edges(src,dst,kind,weight,support)
                    SELECT e.dst,e.src,?,MIN(0.5,e.weight*?),e.support
                    FROM edges e WHERE e.kind=?""",
                    (dest_kind,mult,src_kind))
                bridged += con.total_changes-old
            if progress: progress(f'{src_kind}  already Complete missing , New  {bridged:,}  edges Traceable reference edges ')
        with con:
            con.execute("INSERT OR REPLACE INTO network_meta(key,value) VALUES('lexical_v5','1')")
        return {'indexed':indexed,'bridged':bridged,'cached':False}


def repair_math_relation_memories(progress=None, batch_size=20, stop_event=None):
    """Rescan already stored abstracts/summaries, resumable per source.

    Previously crawled PDFs are not stored, so old PDF-only evidence cannot be
    reconstructed. This limitation is reported rather than invented.
    """
    added=0;done=0
    with database() as con:
        last=(con.execute("SELECT value FROM network_meta WHERE key='math_v6_last_paper'").fetchone() or ('',))[0]
        while True:
            rows=con.execute("SELECT id,title,abstract,summary,url FROM papers WHERE id>? ORDER BY id LIMIT ?",
                             (last,batch_size)).fetchall()
            if not rows:break
            with con:
                for pid,title,abstract,summary,url in rows:
                    sid=paper_unit_id(pid)
                    material=(title or '')+'. '+(abstract or summary or '')
                    added+=add_math_relation_memories(con,sid,url or pid,material,limit=18)
                    last=pid;done+=1
                con.execute("INSERT OR REPLACE INTO network_meta(key,value) VALUES('math_v6_last_paper',?)",(last,))
            if progress:progress(f' research relationship building : already scan  {done:,}  papers existing Paper , New Source support  {added:,}  edges ')
            if stop_event is not None and stop_event.is_set():break
        # Existing theory descriptions are normally available in unit descriptions.
        if not (stop_event and stop_event.is_set()):
            with con:
                rows=con.execute("SELECT id,description,url FROM units WHERE kind='theory'").fetchall()
                for uid,description,url in rows:
                    if description:
                        added+=add_math_relation_memories(con,uid,url or '',description,limit=10)
            if progress:progress(f' legacy network relationship Index Completed : shared scan Paper  {done:,}  papers , New Source support  {added:,}  edges ')
    return {'scanned':done,'relations_added':added}


class OpenAlexSearchFailure(RuntimeError):
    """Search could not finish; *not* evidence that no relevant papers exist."""

    def __init__(self, theory, page, reason, category='temporary', status=None):
        self.theory = theory
        self.page = page
        self.reason = reason
        self.category = category
        self.status = status
        super().__init__(f'{theory} /  #  {page}  pages :{reason}')


class OpenAlexServiceUnavailable(RuntimeError):
    """A shared service/configuration issue. Never silently skip 1000 theories."""

    def __init__(self, reason, category='service'):
        self.category = category
        super().__init__(reason)


# v8.7: Public metadata catalogs are not bypasses for restricted full text.
# A freely downloaded OpenAlex work snapshot can be indexed once and queried
# offline, without OpenAlex API requests. The snapshot is very large; only
# files explicitly selected by the user are imported.
# arXiv is the primary live source for mathematics. The publicly documented
# API asks clients to wait at least three seconds between consecutive calls.
# One global limiter applies to ALL topic and reference worker threads.
_ARXIV_LOCK = threading.Lock()
_ARXIV_NEXT = [0.0]
_ARXIV_ATOM = '{http://www.w3.org/2005/Atom}'
_ARXIV_NS = '{http://arxiv.org/schemas/atom}'

def arxiv_throttle(stop_event=None):
    with _ARXIV_LOCK:
        now=time.monotonic()
        delay=max(0.0,_ARXIV_NEXT[0]-now)
        _ARXIV_NEXT[0]=max(now,_ARXIV_NEXT[0])+3.1
    if delay:
        if stop_event is not None and stop_event.wait(delay):
            raise InterruptedError(' Cancelled ')
        if stop_event is None:time.sleep(delay)

def arxiv_request(session,params,stop_event=None,on_retry=None):
    """Fetch a public Atom page; never pretend HTTP errors mean zero papers."""
    for attempt in range(2):
        if stop_event is not None and stop_event.is_set():raise InterruptedError(' Cancelled ')
        arxiv_throttle(stop_event)
        try:
            r=session.get(ARXIV_API,params=params,headers=HEADERS,timeout=(9,38))
        except requests.RequestException as exc:
            if attempt==0:
                if on_retry:on_retry('arXiv  temporarily connection failed ; short temporary Retry ')
                continue
            raise OpenAlexSearchFailure('',0,'arXiv  connection failed :'+str(exc)[:160],category='network') from exc
        if r.status_code==200:
            try:
                root=ET.fromstring(r.content)
                if root.tag!=_ARXIV_ATOM+'feed':raise ValueError(' NOT is  Atom feed')
                return root
            except (ValueError,ET.ParseError) as exc:
                raise OpenAlexSearchFailure('',0,'arXiv Atom  Data invalid format :'+str(exc)[:130],category='schema') from exc
        if r.status_code in (408,500,502,503,504) and attempt==0:
            if on_retry:on_retry(f'arXiv HTTP {r.status_code}, change by its they literature provider take over ( Later can Retry )')
            continue
        raise OpenAlexSearchFailure('',0,f'arXiv HTTP {r.status_code}：'+r.text[:120],
            category='quota' if r.status_code==429 else 'auth' if r.status_code in (401,403) else 'http',
            status=r.status_code)
    raise OpenAlexSearchFailure('',0,'arXiv  Retry Failed ',category='network')

def arxiv_entry_to_work(entry):
    """Normalize Atom metadata to the same source-grounded paper schema."""
    get=lambda key: ' '.join((entry.findtext(_ARXIV_ATOM+key) or '').split())
    title=get('title')
    arxiv_url=get('id').replace('http://','https://')
    match=_ARXIV_RX.search(arxiv_url)
    if not match or not title:return None
    arxiv_id=match.group(1)
    abstract=get('summary')[:35000]
    published=get('published')
    doi_elem=entry.find(_ARXIV_NS+'doi')
    reported_doi=normalize_doi(doi_elem.text if doi_elem is not None else '')
    doi=reported_doi or '10.48550/arxiv.'+arxiv_id
    pdf_url='https://arxiv.org/pdf/'+arxiv_id
    for link in entry.findall(_ARXIV_ATOM+'link'):
        if link.get('title')=='pdf' or link.get('type')=='application/pdf':
            candidate=link.get('href','').replace('http://','https://')
            if safe_pdf_url(candidate):pdf_url=candidate
            break
    year=int(published[:4]) if published[:4].isdigit() else None
    return {'id':'https://arxiv.org/abs/'+arxiv_id,'doi':'https://doi.org/'+doi,
        'display_name':title,'publication_year':year,'cited_by_count':0,
        'abstract_inverted_index':None,'_abstract_text':abstract,'type':'preprint',
        'best_oa_location':{'pdf_url':pdf_url,'landing_page_url':arxiv_url},
        '_provider':'arxiv','_arxiv_id':arxiv_id}

def stream_arxiv(session,theory,wanted,stop_event,pause_event=None,progress=None,on_retry=None):
    """Stream ranked math/preprint candidates; a single topic may span pages.

    arXiv limits a search to 30k results, so other catalogs take over once
    this source is exhausted. Requests are shared and strictly throttled.
    """
    cleaned=re.sub(r'["\\]', ' ',str(theory)).strip()
    if not cleaned:return
    query='all:"'+cleaned[:160]+'"'
    yielded=0;empty=0;page=0;start=0
    while yielded<wanted and start<30000:
        if stop_event.is_set():return
        while pause_event is not None and pause_event.is_set() and not stop_event.is_set():time.sleep(.15)
        size=min(100,wanted-yielded,30000-start)
        root=arxiv_request(session,{'search_query':query,'start':start,'max_results':size,
                                    'sortBy':'relevance','sortOrder':'descending'},
                            stop_event,on_retry)
        entries=root.findall(_ARXIV_ATOM+'entry')
        page+=1;accepted=[]
        for i,entry in enumerate(entries):
            work=arxiv_entry_to_work(entry)
            if not work:continue
            score=score_candidate(work,theory,1/(1+page+i/80))
            if score>=.33:accepted.append((score,work))
        accepted.sort(key=lambda pair:pair[0],reverse=True)
        if progress:progress(page,0,yielded,len(accepted))
        empty=empty+1 if not accepted else 0
        for row in accepted:
            yield row
            yielded+=1
            if yielded>=wanted:return
        start+=len(entries)
        if len(entries)<size or empty>=2:return

def fetch_arxiv_reference_batch(session,arxiv_ids,stop_event,on_retry=None):
    """Resolve explicitly cited arXiv IDs without OpenAlex or Crossref DOI guesses."""
    works={}
    for offset in range(0,len(arxiv_ids),40):
        ids=arxiv_ids[offset:offset+40]
        root=arxiv_request(session,{'id_list':','.join(ids),'max_results':len(ids)},
                           stop_event,on_retry)
        for entry in root.findall(_ARXIV_ATOM+'entry'):
            work=arxiv_entry_to_work(entry)
            if work:works[work['_arxiv_id'].lower()]=work
    return works

_CROSSREF_LOCK = threading.Lock()
_CROSSREF_NEXT = [0.0]
_CROSSREF_PUBLIC_SEM=threading.BoundedSemaphore(1)
_CROSSREF_POLITE_SEM=threading.BoundedSemaphore(3)

def crossref_throttle(stop_event=None):
    # Conservative shared rate for ALL threads, including Wikipedia citations.
    email=os.environ.get('CROSSREF_MAILTO','').strip()
    interval=0.55 if '@' in email else 1.1
    with _CROSSREF_LOCK:
        now=time.monotonic()
        delay=max(0.0,_CROSSREF_NEXT[0]-now)
        _CROSSREF_NEXT[0]=max(now,_CROSSREF_NEXT[0])+interval
    if delay:
        if stop_event is not None:
            if stop_event.wait(delay):raise InterruptedError(' Cancelled ')
        else:time.sleep(delay)


def crossref_request(session, params=None, stop_event=None, doi=None, on_retry=None):
    params=dict(params or {})
    email=os.environ.get('CROSSREF_MAILTO','').strip()
    if email and '@' in email:params['mailto']=email
    url=CROSSREF if not doi else CROSSREF+'/'+urllib.parse.quote(doi,safe='/')
    for attempt in range(3):
        if stop_event is not None and stop_event.is_set():raise InterruptedError(' Cancelled ')
        sem=_CROSSREF_POLITE_SEM if '@' in email else _CROSSREF_PUBLIC_SEM
        try:
            # Enforce BOTH Crossref rate and max concurrent requests, even
            # across many mathematics topic/reference worker threads.
            with sem:
                crossref_throttle(stop_event)
                r=session.get(url,params=params,headers=HEADERS,timeout=(8,30))
        except requests.RequestException as exc:
            if attempt<2:
                if on_retry:on_retry('Crossref  Network temporarily Failed , Later Retry ')
                time.sleep(1+attempt)
                continue
            raise OpenAlexSearchFailure('',0,'Crossref  connection failed :'+str(exc)[:160],category='network') from exc
        if r.status_code==200:
            try:return r.json()['message']
            except (ValueError,KeyError,TypeError) as exc:
                raise OpenAlexSearchFailure('',0,'Crossref JSON  format abnormal ',category='schema') from exc
        if r.status_code==404 and doi:return None
        if r.status_code in (429,500,502,503,504) and attempt<2:
            wait=min(15.0,2.0*(attempt+1))
            if on_retry:on_retry(f'Crossref HTTP {r.status_code},{wait:g}  seconds after Retry ')
            if stop_event and stop_event.wait(wait):raise InterruptedError(' Cancelled ')
            if not stop_event:time.sleep(wait)
            continue
        raise OpenAlexSearchFailure('',0,
            f'Crossref HTTP {r.status_code}：{r.text[:180]}',
            category='quota' if r.status_code==429 else 'http',status=r.status_code)
    raise OpenAlexSearchFailure('',0,'Crossref  attempt Failed ',category='network')


def crossref_work_to_openalex(item):
    """Normalize verified Crossref metadata for the existing paper pipeline."""
    if not isinstance(item,dict):return None
    doi=normalize_doi(item.get('DOI',''))
    title=item.get('title') or []
    if isinstance(title,list):title=title[0] if title else ''
    if not doi or not title:return None
    kind=item.get('type','')
    types={'journal-article':'article','proceedings-article':'proceedings-article',
           'posted-content':'preprint','book-chapter':'book-chapter',
           'journal-issue':'other','book':'other'}
    year=None
    for field in ('published','issued','published-online','created'):
        dates=(item.get(field) or {}).get('date-parts',[]) if isinstance(item.get(field),dict) else []
        if dates and dates[0]:year=dates[0][0];break
    abstract=BeautifulSoup(str(item.get('abstract','')), 'html.parser').get_text(' ',strip=True)[:35000]
    uid='https://api.crossref.org/works/C'+hashlib.sha256(doi.encode()).hexdigest()[:28]
    return {'id':uid,'doi':'https://doi.org/'+doi, 'display_name':str(title),
            'publication_year':year,'cited_by_count':int(item.get('is-referenced-by-count') or 0),
            'abstract_inverted_index':None, '_abstract_text':abstract,
            'type':types.get(kind,'other'),'best_oa_location':None,'_provider':'crossref'}


def stream_crossref(session,theory,wanted,stop_event,pause_event=None,progress=None,
                    on_retry=None,seen_doi=None):
    """Respect public rate limits; do NOT claim a quota-free or unlimited API."""
    yielded=0;page=0;cursor='*';empty=0
    seen=seen_doi if seen_doi is not None else set()
    while yielded<wanted:
        if stop_event.is_set():return
        while pause_event is not None and pause_event.is_set() and not stop_event.is_set():time.sleep(.15)
        page+=1
        params={'query.bibliographic':theory,'rows':min(100,wanted-yielded),
                'cursor':cursor,'select':'DOI,title,abstract,type,published,issued,published-online,created,is-referenced-by-count'}
        data=crossref_request(session,params,stop_event,on_retry=on_retry)
        rows=data.get('items',[]) if isinstance(data,dict) else []
        if not isinstance(rows,list):raise OpenAlexSearchFailure(theory,page,'Crossref items  format NOT correct confirm ',category='schema')
        if not rows:return
        accepted=[]
        for rank,item in enumerate(rows):
            work=crossref_work_to_openalex(item)
            if not work or work.get('type') not in _PAPER_TYPES:continue
            doi=normalize_doi(work['doi'])
            if doi in seen:continue
            seen.add(doi)
            score=score_candidate(work,theory,rank_bonus=1/(1+page+rank/80))
            if score >= .33:accepted.append((score,work))
        accepted.sort(key=lambda x:x[0],reverse=True)
        if progress:progress(page,0,yielded,len(accepted))
        empty=empty+1 if not accepted else 0
        for item in accepted:
            yield item
            yielded+=1
            if yielded>=wanted:return
        if empty>=2 or len(rows)<params['rows']:return
        next_cursor=data.get('next-cursor')
        if not next_cursor or next_cursor==cursor:return
        cursor=next_cursor



# ---------------------------------------------------------------------------
# FLIN v17.1: provider adapters. All endpoints are public metadata APIs; the
# optional Semantic Scholar endpoint runs only with a user-supplied API key.
# DOI/title identity stays in the existing shared local catalog.
# ---------------------------------------------------------------------------
OPENAIRE_GRAPH_API = 'https://api.openaire.eu/graph/v3/research-products'
EUROPE_PMC_API = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
DBLP_PUBLICATIONS_API = 'https://dblp.org/search/publ/api'
SEMANTIC_SCHOLAR_API = 'https://api.semanticscholar.org/graph/v1/paper/search'
_FLIN_PROVIDER_NEXT = defaultdict(float)
_FLIN_PROVIDER_LOCK = threading.Lock()


def flin_provider_get(session, provider, endpoint, *, params=None, stop_event=None,
                      headers=None, interval=1.3, retries=2):
    """Bounded, global per-provider throttling and explicit HTTP failure state."""
    request_headers=dict(HEADERS)
    if headers:request_headers.update(headers)
    for retry in range(retries+1):
        if stop_event is not None and stop_event.is_set():
            raise InterruptedError(' Stopped by user ')
        with _FLIN_PROVIDER_LOCK:
            now=time.monotonic()
            delay=max(0.0, _FLIN_PROVIDER_NEXT[provider]-now)
            _FLIN_PROVIDER_NEXT[provider]=max(now,_FLIN_PROVIDER_NEXT[provider])+interval
        if delay:
            if stop_event is not None and stop_event.wait(delay):
                raise InterruptedError(' Stopped by user ')
            elif stop_event is None:time.sleep(delay)
        try:
            response=session.get(endpoint,params=params,headers=request_headers,timeout=(9,32))
        except requests.RequestException as exc:
            if retry<retries:
                if stop_event is not None and stop_event.wait(1.5*(retry+1)):
                    raise InterruptedError(' Stopped by user ')
                elif stop_event is None:time.sleep(1.5*(retry+1))
                continue
            raise OpenAlexSearchFailure(provider,retry,f' connection failed :{exc}',category='network') from exc
        if response.status_code == 200:
            try:return response.json()
            except (ValueError,TypeError) as exc:
                raise OpenAlexSearchFailure(provider,retry,' return not  JSON  format ',category='schema') from exc
        status=response.status_code
        if status in (429,500,502,503,504) and retry<retries:
            retry_after=response.headers.get('Retry-After','')
            wait=float(retry_after) if retry_after.isdigit() else 3*(retry+1)
            wait=min(35,max(1,wait))
            if stop_event is not None and stop_event.wait(wait):
                raise InterruptedError(' Stopped by user ')
            elif stop_event is None:time.sleep(wait)
            continue
        raise OpenAlexSearchFailure(provider,retry,f'{provider} HTTP {status}',
            category='quota' if status==429 else 'auth' if status in (401,403) else 'http',status=status)
    raise OpenAlexSearchFailure(provider,0,' unknown  API  Error ',category='network')


def flin_clean_abstract(raw):
    """Preserve literal source metadata; do not manufacture an abstract."""
    if isinstance(raw,dict):
        raw=raw.get('text') or raw.get('value') or ''
    if isinstance(raw,list):
        raw=' '.join(str(x.get('text') or x.get('value') or '') if isinstance(x,dict) else str(x) for x in raw)
    return ' '.join(BeautifulSoup(str(raw or ''),'html.parser').get_text(' ',strip=True).split())[:35000]


def flin_openaire_work(item):
    if not isinstance(item,dict):return None
    title=item.get('mainTitle') or item.get('title') or ''
    if isinstance(title,dict):title=title.get('text') or title.get('value') or ''
    if not isinstance(title,str) or len(title.strip())<8:return None
    raw_pids=item.get('pids') or item.get('pid') or []
    if isinstance(raw_pids,dict):raw_pids=[raw_pids]
    doi=''
    for pid in raw_pids:
        if isinstance(pid,dict):
            candidate=pid.get('value') or pid.get('id') or ''
        else:candidate=str(pid)
        doi=normalize_doi(candidate)
        if doi:break
    unique_id=item.get('id') or item.get('originalId') or ''
    if not unique_id and not doi:return None
    abstract=flin_clean_abstract(item.get('description') or item.get('abstract'))
    year=item.get('publicationYear') or item.get('year')
    try:year=int(year)
    except (TypeError,ValueError):year=None
    # OA repositories are NOT assumed to have a downloadable unrestricted PDF.
    return {'id':'https://api.openaire.eu/graph/v3/research-products/'+str(unique_id or doi),
            'doi':'https://doi.org/'+doi if doi else '',
            'display_name':title.strip(),'_abstract_text':abstract,
            'publication_year':year,'cited_by_count':int(item.get('citationCount') or 0),
            'type':'article','_provider':'OpenAIRE'}


def stream_openaire(session,theory,wanted,stop_event,pause_event=None,progress=None,on_retry=None):
    total=0
    for page in range(1,max(1,min(12,math.ceil(wanted/50)*2))+1):
        if stop_event.is_set() or total>=wanted:return
        while pause_event is not None and pause_event.is_set() and not stop_event.is_set():time.sleep(.15)
        size=min(50,max(10,wanted-total))
        data=flin_provider_get(session,'OpenAIRE',OPENAIRE_GRAPH_API,
            params={'search':theory,'type':'publication','page':page,'pageSize':size},stop_event=stop_event)
        rows=data.get('results') if isinstance(data,dict) else None
        if not isinstance(rows,list):
            raise OpenAlexSearchFailure('OpenAIRE',page,' No  results  field ',category='schema')
        accepted=[]
        for rank,item in enumerate(rows):
            work=flin_openaire_work(item)
            if work:
                score=score_candidate(work,theory,1/(1+page+rank/80))
                if score>=.33:accepted.append((score,work))
        if progress:progress(page,0,total,len(accepted))
        for row in sorted(accepted,key=lambda p:-p[0]):
            yield row
            total+=1
            if total>=wanted:return
        if len(rows)<size or not accepted:return


def flin_europepmc_work(item):
    if not isinstance(item,dict):return None
    title=str(item.get('title') or '').strip()
    if len(title)<8:return None
    doi=normalize_doi(item.get('doi'))
    key=str(item.get('id') or '')
    source=str(item.get('source') or 'MED')
    if not key and not doi:return None
    year=item.get('pubYear')
    try:year=int(year)
    except (ValueError,TypeError):year=None
    abstract=flin_clean_abstract(item.get('abstractText'))
    return {'id':'https://europepmc.org/article/'+urllib.parse.quote(source,safe='')+'/'+urllib.parse.quote(key,safe=''),
            'doi':'https://doi.org/'+doi if doi else '',
            'display_name':title,'_abstract_text':abstract,'publication_year':year,
            'cited_by_count':int(item.get('citedByCount') or 0),
            'type':'article','_provider':'Europe PMC'}


def stream_europepmc(session,theory,wanted,stop_event,pause_event=None,progress=None,on_retry=None):
    # Intended for mathematical biology / neuroscience, not every math category.
    if not re.search(r'biolog|epidemiolog|neuro|medic|bio-stat|biostat|clinical|'
                     r'population|ecolog|chemic|pharmac|genet|disease',theory,re.I):
        return
    cursor='*';total=0
    for page in range(1,5):
        if stop_event.is_set() or total>=wanted:return
        while pause_event is not None and pause_event.is_set() and not stop_event.is_set():time.sleep(.15)
        size=min(50,max(10,wanted-total))
        data=flin_provider_get(session,'Europe PMC',EUROPE_PMC_API,
            params={'query':theory,'format':'json','resultType':'core',
                    'pageSize':size,'cursorMark':cursor},stop_event=stop_event)
        rows=(data.get('resultList') or {}).get('result') if isinstance(data,dict) else None
        if not isinstance(rows,list):
            raise OpenAlexSearchFailure('Europe PMC',page,' No  resultList.result  field ',category='schema')
        accepted=[]
        for rank,item in enumerate(rows):
            work=flin_europepmc_work(item)
            if work:
                score=score_candidate(work,theory,1/(1+page+rank/80))
                if score>=.33:accepted.append((score,work))
        if progress:progress(page,0,total,len(accepted))
        for row in sorted(accepted,key=lambda p:-p[0]):
            yield row;total+=1
            if total>=wanted:return
        nxt=data.get('nextCursorMark') or ''
        if not nxt or nxt==cursor or len(rows)<size or not accepted:return
        cursor=nxt


def flin_dblp_work(item):
    info=item.get('info') if isinstance(item,dict) else None
    if not isinstance(info,dict):return None
    title=flin_clean_abstract(info.get('title'))
    if len(title)<8:return None
    doi=normalize_doi(info.get('doi'))
    key=str(info.get('key') or '')
    if not key and not doi:return None
    year=info.get('year')
    try:year=int(year)
    except (TypeError,ValueError):year=None
    return {'id':'https://dblp.org/rec/'+urllib.parse.quote(key,safe='/'),
            'doi':'https://doi.org/'+doi if doi else '',
            'display_name':title,'_abstract_text':'', 'publication_year':year,
            'cited_by_count':0,'type':'article','_provider':'DBLP'}


def stream_dblp(session,theory,wanted,stop_event,pause_event=None,progress=None,on_retry=None):
    # Computer science/algorithms/discrete mathematics; metadata often title-only.
    if not re.search(r'graph|algorithm|comput|logic|optimization|linear algebra|'
                     r'machine learning|information|complexity|combinator|numerical|'
                     r'cryptograph|finite element|control|coding|geometry',theory,re.I):
        return
    total=0;offset=0
    for page in range(min(5,max(1,math.ceil(wanted/60)))):
        if stop_event.is_set() or total>=wanted:return
        size=min(60,max(10,wanted-total))
        data=flin_provider_get(session,'DBLP',DBLP_PUBLICATIONS_API,
            params={'q':theory,'format':'json','h':size,'f':offset,'c':0},stop_event=stop_event)
        hits=(data.get('result') or {}).get('hits') or {}
        rows=hits.get('hit',[])
        if isinstance(rows,dict):rows=[rows]
        if not isinstance(rows,list):raise OpenAlexSearchFailure('DBLP',page,'hits  invalid format ',category='schema')
        accepted=[]
        for rank,item in enumerate(rows):
            work=flin_dblp_work(item)
            if work:
                score=score_candidate(work,theory,1/(1+page+rank/80))
                if score>=.33:accepted.append((score,work))
        if progress:progress(page+1,0,total,len(accepted))
        for row in sorted(accepted,key=lambda p:-p[0]):
            yield row;total+=1
            if total>=wanted:return
        offset+=len(rows)
        if len(rows)<size or not accepted:return


def flin_semantic_scholar_work(item):
    if not isinstance(item,dict):return None
    title=str(item.get('title') or '').strip()
    pid=item.get('paperId')
    if not pid or len(title)<8:return None
    doi=normalize_doi((item.get('externalIds') or {}).get('DOI',''))
    year=item.get('year')
    try:year=int(year)
    except (TypeError,ValueError):year=None
    oa=item.get('openAccessPdf') or {}
    loc={'pdf_url':oa.get('url')} if isinstance(oa,dict) and safe_pdf_url(oa.get('url')) else None
    return {'id':'https://api.semanticscholar.org/graph/v1/paper/'+str(pid),
            'doi':'https://doi.org/'+doi if doi else '', 'display_name':title,
            '_abstract_text':flin_clean_abstract(item.get('abstract')),
            'publication_year':year,'cited_by_count':int(item.get('citationCount') or 0),
            'best_oa_location':loc,'type':'article','_provider':'Semantic Scholar'}


def stream_semantic_scholar(session,theory,wanted,stop_event,pause_event=None,progress=None,on_retry=None):
    key=os.environ.get('SEMANTIC_SCHOLAR_API_KEY','').strip()
    if not key:return
    count=0;offset=0
    for page in range(1,4):
        if stop_event.is_set() or count>=wanted:return
        size=min(100,wanted-count,1000-offset)
        if size<=0:return
        data=flin_provider_get(session,'Semantic Scholar',SEMANTIC_SCHOLAR_API,
            params={'query':theory,'offset':offset,'limit':size,
                    'fields':'title,abstract,year,citationCount,externalIds,openAccessPdf'},
            headers={'x-api-key':key},stop_event=stop_event,interval=1.15)
        rows=data.get('data') if isinstance(data,dict) else None
        if not isinstance(rows,list):
            raise OpenAlexSearchFailure('Semantic Scholar',page,' No  data  field ',category='schema')
        accepted=[]
        for rank,item in enumerate(rows):
            work=flin_semantic_scholar_work(item)
            if work:
                score=score_candidate(work,theory,1/(1+page+rank/80))
                if score>=.33:accepted.append((score,work))
        if progress:progress(page,0,count,len(accepted))
        for item in sorted(accepted,key=lambda p:-p[0]):
            yield item;count+=1
            if count>=wanted:return
        offset+=len(rows)
        if len(rows)<size or not accepted:return


# Persistent, network-independent mathematical literature catalog.
# The shared SQLite DB stores only metadata and source provenance; it never
# replaces the evidence filters that govern the memory graph.
_CATALOG_SCHEMA_LOCK = threading.RLock()
_CATALOG_SCHEMA_READY = set()
_CATALOG_BATCH = 32


def _catalog_connect():
    LOCAL_CATALOG.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(LOCAL_CATALOG), timeout=60)
    con.execute('PRAGMA busy_timeout=60000')
    con.execute('PRAGMA cache_size=-8192')
    with _CATALOG_SCHEMA_LOCK:
        key = str(LOCAL_CATALOG.resolve())
        if key not in _CATALOG_SCHEMA_READY:
            con.execute('PRAGMA journal_mode=WAL')
            con.executescript("""
                CREATE TABLE IF NOT EXISTS local_works(
                    id TEXT PRIMARY KEY,doi TEXT,title TEXT,abstract TEXT,year INTEGER,
                    citations INTEGER,kind TEXT,oa_location TEXT);
                CREATE VIRTUAL TABLE IF NOT EXISTS local_works_fts
                    USING fts5(title,abstract,content='local_works',content_rowid='rowid',
                               tokenize='porter unicode61');
                CREATE TABLE IF NOT EXISTS catalog_identifiers(
                    identity TEXT PRIMARY KEY,work_id TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS catalog_sources(
                    work_id TEXT NOT NULL,provider TEXT NOT NULL,source_id TEXT NOT NULL,
                    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(work_id,provider,source_id));
                CREATE TABLE IF NOT EXISTS catalog_query_hits(
                    query_key TEXT NOT NULL,work_id TEXT NOT NULL,
                    PRIMARY KEY(query_key,work_id));
                CREATE INDEX IF NOT EXISTS idx_catalog_hits_work
                    ON catalog_query_hits(work_id);
                CREATE TABLE IF NOT EXISTS catalog_queries(
                    query_key TEXT PRIMARY KEY,query_text TEXT NOT NULL,
                    completed_at REAL NOT NULL,state TEXT NOT NULL,
                    source_count INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS catalog_maintenance(
                    key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_catalog_sources_provider
                    ON catalog_sources(provider);
            """)
            columns={row[1] for row in con.execute('PRAGMA table_info(catalog_queries)')}
            if 'suite' not in columns:
                con.execute("ALTER TABLE catalog_queries ADD COLUMN suite TEXT NOT NULL DEFAULT 'v16'")
            con.commit()
            _CATALOG_SCHEMA_READY.add(key)
    return con


def _catalog_title_key(title):
    value = re.sub(r'[^a-z0-9\u3400-\u9fff]+', '',
                   unicodedata.normalize('NFKC', str(title or '')).casefold())
    # Short, generic titles cannot safely act as globally unique paper IDs.
    return 'title:' + hashlib.sha256(value.encode('utf-8')).hexdigest() if len(value)>=22 else ''


def _catalog_identities(work):
    """Candidate record IDs, including cross-provider arXiv/DOI/title aliases."""
    found = []
    doi = normalize_doi(work.get('doi'))
    if doi: found.append('doi:' + doi)
    uid = str(work.get('_arxiv_id') or '')
    url = str(work.get('id') or '')
    if not uid:
        m = _ARXIV_RX.search(url)
        uid = m.group(1) if m else ''
    if uid:
        found.append('arxiv:' + re.sub(r'v\d+$', '', uid.casefold()))
    title_key = _catalog_title_key(work.get('display_name'))
    if title_key:found.append(title_key)
    if url:found.append('source:' + url.casefold())
    return list(dict.fromkeys(found))


def _catalog_work_to_row(work):
    title = str(work.get('display_name') or '').strip()[:1200]
    if not title or not str(work.get('id') or '').strip():return None
    abstract = str(work.get('_abstract_text') or
                   abstract_from_index(work.get('abstract_inverted_index')) or '')[:30000]
    kind = str(work.get('type') or 'article')
    if kind not in _PAPER_TYPES:return None
    location = work.get('best_oa_location')
    if not isinstance(location,dict):location = None
    try: year = int(work.get('publication_year') or 0) or None
    except (ValueError,TypeError):year=None
    try: cited = max(0,int(work.get('cited_by_count') or 0))
    except (ValueError,TypeError):cited=0
    doi=normalize_doi(work.get('doi'))
    return (str(work['id']), 'https://doi.org/'+doi if doi else '',title,
            abstract,year,cited,kind,json.dumps(location,ensure_ascii=False))


def _catalog_insert_batch(con,works,query=None,provider=None):
    """Store canonical metadata in one SQLite transaction; merge cross-provider IDs.

    Existing snapshot IDs remain untouched; multiple provider identifiers can
    resolve to one row. FTS is updated only when searchable text improves.
    """
    query_key = _catalog_query_key(query) if query else None
    inserted=0;merged=0
    for work in works:
        row = _catalog_work_to_row(work)
        if not row:continue
        keys = _catalog_identities(work)
        chosen=None
        for key in keys:
            hit=con.execute('SELECT work_id FROM catalog_identifiers WHERE identity=?',(key,)).fetchone()
            if hit:
                if key.startswith('title:'):
                    # A recurring generic title from different years is not
                    # sufficient proof that two papers are identical.
                    prior=con.execute('SELECT year FROM local_works WHERE id=?',(hit[0],)).fetchone()
                    if prior and prior[0] and row[4] and abs(int(prior[0])-int(row[4]))>3:
                        continue
                chosen=hit[0];break
        if chosen is None:
            exists=con.execute('SELECT id FROM local_works WHERE id=?',(row[0],)).fetchone()
            if exists:chosen=exists[0]
        if chosen is None:
            cur=con.execute("""INSERT OR IGNORE INTO local_works
                (id,doi,title,abstract,year,citations,kind,oa_location)
                VALUES(?,?,?,?,?,?,?,?)""",row)
            if cur.rowcount:
                rid=cur.lastrowid
                con.execute('INSERT INTO local_works_fts(rowid,title,abstract) VALUES(?,?,?)',
                            (rid,row[2],row[3]))
                inserted+=1
            chosen=row[0]
        else:
            previous=con.execute("""SELECT rowid,doi,title,abstract,year,citations,kind,oa_location
                                     FROM local_works WHERE id=?""",(chosen,)).fetchone()
            if not previous:continue
            rid,doi,title,abstract,year,citations,kind,oa=previous
            # A preprint's synthetic DOI is superseded by its publisher DOI.
            incoming_doi=row[1]
            use_doi = incoming_doi if (not doi or (
                '10.48550/arxiv.' in doi.lower() and incoming_doi and
                '10.48550/arxiv.' not in incoming_doi.lower())) else doi
            title_new=title if len(title or '')>=len(row[2]) else row[2]
            abstract_new=abstract if len(abstract or '')>=len(row[3]) else row[3]
            changes=(title_new!=title or abstract_new!=abstract)
            # Keep known preprint PDF location if the publisher has none.
            new_oa=oa if oa and oa!='null' else row[7]
            new_kind=kind if kind!='preprint' else row[6]
            con.execute("""UPDATE local_works SET doi=?,title=?,abstract=?,
                           year=?,citations=?,kind=?,oa_location=? WHERE id=?""",
                        (use_doi,title_new,abstract_new,year or row[4],
                         max(citations or 0,row[5]),new_kind,new_oa,chosen))
            if changes:
                con.execute("""INSERT INTO local_works_fts(local_works_fts,rowid,title,abstract)
                               VALUES('delete',?,?,?)""",(rid,title,abstract))
                con.execute('INSERT INTO local_works_fts(rowid,title,abstract) VALUES(?,?,?)',
                            (rid,title_new,abstract_new))
            merged+=1
        for key in keys:
            # An ambiguous title never reassigns an established identifier.
            con.execute('INSERT OR IGNORE INTO catalog_identifiers(identity,work_id) VALUES(?,?)',
                        (key,chosen))
        src=str(provider or work.get('_provider') or 'snapshot')[:48]
        con.execute("""INSERT INTO catalog_sources(work_id,provider,source_id)
                       VALUES(?,?,?) ON CONFLICT(work_id,provider,source_id)
                       DO UPDATE SET last_seen=CURRENT_TIMESTAMP""",
                    (chosen,src,str(work['id'])[:800]))
        if query_key:
            con.execute('INSERT OR IGNORE INTO catalog_query_hits(query_key,work_id) VALUES(?,?)',
                        (query_key,chosen))
    return inserted,merged


def catalog_store_batch(works,query=None,provider=None):
    if not works:return (0,0)
    con=_catalog_connect()
    try:
        with con:return _catalog_insert_batch(con,works,query,provider)
    finally:con.close()


def _catalog_query_key(theory):
    return hashlib.sha256(canonical_phrase(theory).encode('utf-8')).hexdigest()


def catalog_query_fresh(theory):
    """Cache successful search attempts, not provider failures or cancellations."""
    if os.environ.get('BRAIN_CATALOG_REFRESH','0')=='1' or not LOCAL_CATALOG.exists():
        return False
    try:
        ttl=max(0,min(720,float(os.environ.get('BRAIN_CATALOG_TTL_HOURS','72'))))*3600
        if ttl<=0:return False
        with sqlite3.connect(str(LOCAL_CATALOG),timeout=6) as con:
            row=con.execute('SELECT completed_at,state,suite FROM catalog_queries WHERE query_key=?',
                            (_catalog_query_key(theory),)).fetchone()
            return bool(row and row[2]=='v17_multisource' and
                        row[1]=='complete' and time.time()-row[0]<ttl)
    except (sqlite3.Error,ValueError):return False


def catalog_mark_query(theory,source_count):
    con=_catalog_connect()
    try:
        with con:
            con.execute("""INSERT INTO catalog_queries(query_key,query_text,completed_at,state,source_count,suite)
                           VALUES(?,?,?,'complete',?,'v17_multisource')
                           ON CONFLICT(query_key) DO UPDATE SET
                           completed_at=excluded.completed_at,state=excluded.state,
                           source_count=excluded.source_count,suite=excluded.suite""",
                        (_catalog_query_key(theory),str(theory)[:500],time.time(),source_count))
    finally:con.close()


def local_catalog_available():
    if not LOCAL_CATALOG.exists():return False
    try:
        with sqlite3.connect(str(LOCAL_CATALOG),timeout=3) as con:
            return con.execute('SELECT 1 FROM local_works LIMIT 1').fetchone() is not None
    except sqlite3.Error:return False


def local_catalog_count():
    if not LOCAL_CATALOG.exists():return 0
    try:
        with sqlite3.connect(str(LOCAL_CATALOG),timeout=3) as con:
            return int(con.execute('SELECT COUNT(*) FROM local_works').fetchone()[0])
    except sqlite3.Error:return 0


def catalog_statistics():
    con=_catalog_connect()
    try:
        works=int(con.execute('SELECT COUNT(*) FROM local_works').fetchone()[0])
        sources=con.execute('SELECT provider,COUNT(*) FROM catalog_sources GROUP BY provider ORDER BY provider').fetchall()
        queries=int(con.execute('SELECT COUNT(*) FROM catalog_queries WHERE state="complete"').fetchone()[0])
        hits=int(con.execute('SELECT COUNT(*) FROM catalog_query_hits').fetchone()[0])
        identities=int(con.execute('SELECT COUNT(*) FROM catalog_identifiers').fetchone()[0])
        size=sum(f.stat().st_size for f in (LOCAL_CATALOG,Path(str(LOCAL_CATALOG)+'-wal')) if f.exists())
        return {'catalog_path':str(LOCAL_CATALOG),'works':works,'identities':identities,
                'query_hits':hits,'cached_queries':queries,'sources':dict(sources),
                'main_db_mib':round(size/(1024**2),2)}
    finally:con.close()


def _iter_snapshot_works(filepath):
    opener=gzip.open if str(filepath).endswith('.gz') else open
    with opener(filepath,'rt',encoding='utf-8') as src:
        for raw in src:
            try:work=json.loads(raw)
            except (json.JSONDecodeError,UnicodeError):continue
            if isinstance(work,dict) and work.get('id') and work.get('display_name'):
                yield work


def import_openalex_snapshot(filepath,limit=0,progress=None,stop_event=None):
    """Incrementally import official works metadata (not subscription full text)."""
    fp=Path(filepath).expanduser().resolve()
    if not fp.is_file() or not (str(fp).endswith('.jsonl') or str(fp).endswith('.jsonl.gz')):
        raise ValueError(' Select  OpenAlex  official  works   .jsonl  or  .jsonl.gz  file ')
    imported=0;scanned=0;buffer=[]
    for w in _iter_snapshot_works(fp):
        if stop_event and stop_event.is_set():break
        scanned+=1
        if w.get('type') in _PAPER_TYPES:
            buffer.append(w)
        if len(buffer)>=200:
            new,_=catalog_store_batch(buffer,provider='openalex-snapshot')
            imported+=new;buffer.clear()
        if scanned%3000==0 and progress:progress(scanned,imported)
        if limit and scanned>=limit:break
    if buffer:
        new,_=catalog_store_batch(buffer,provider='openalex-snapshot')
        imported+=new
    if progress:progress(scanned,imported)
    return scanned,imported


def catalog_import_network(path=None,limit=0,progress=None):
    """Copy metadata from an existing Brain_Project network DB, read-only."""
    source=Path(path or DB_PATH).expanduser().resolve()
    if not source.exists():raise FileNotFoundError(' cannot find Source Database :'+str(source))
    con=sqlite3.connect(f'file:{urllib.parse.quote(str(source))}?mode=ro',uri=True,timeout=30)
    inserted=0;scanned=0;last=''
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='papers'").fetchone():
            raise ValueError(' Source  SQLite  NOT is includes  papers  Data table  Brain_Project  Network ')
        while True:
            rows=con.execute("""SELECT id,title,abstract,year,citations,doi,url FROM papers
                                WHERE id>? ORDER BY id LIMIT 300""",(last,)).fetchall()
            if not rows:break
            works=[]
            for pid,title,abstract,year,citations,doi,url in rows:
                last=pid;scanned+=1
                works.append({'id':pid,'display_name':title,'_abstract_text':abstract or '',
                    'publication_year':year,'cited_by_count':citations or 0,'doi':doi or '',
                    'type':'article','best_oa_location':None,'_provider':'brain-network'})
                if limit and scanned>=limit:break
            new,_=catalog_store_batch(works,provider='brain-network')
            inserted+=new
            if progress:progress(scanned,inserted)
            if limit and scanned>=limit:break
    finally:con.close()
    return scanned,inserted


def catalog_backfill_keys(limit=0,progress=None):
    """Build canonical IDs for legacy snapshot rows, checkpointing every batch."""
    con=_catalog_connect();scanned=0
    try:
        old=con.execute("SELECT value FROM catalog_maintenance WHERE key='key_backfill_rowid'").fetchone()
        last=int(old[0]) if old else 0
        while True:
            page_limit=min(800,max(1,limit-scanned)) if limit else 800
            rows=con.execute("""SELECT rowid,id,doi,title FROM local_works WHERE rowid>?
                                ORDER BY rowid LIMIT ?""",(last,page_limit)).fetchall()
            if not rows:break
            with con:
                for rid,wid,doi,title in rows:
                    keys=_catalog_identities({'id':wid,'doi':doi,'display_name':title})
                    for key in keys:
                        con.execute('INSERT OR IGNORE INTO catalog_identifiers(identity,work_id) VALUES(?,?)',
                                    (key,wid))
                    last=rid;scanned+=1
                con.execute("""INSERT INTO catalog_maintenance(key,value)
                                VALUES('key_backfill_rowid',?)
                                ON CONFLICT(key) DO UPDATE SET value=excluded.value""",(str(last),))
            if progress:progress(scanned)
            if limit and scanned>=limit:break
        return scanned
    finally:con.close()


def _catalog_row_to_work(row):
    wid,doi,title,abstract,year,citations,kind,oa=row
    try:location=json.loads(oa) if oa else None
    except (TypeError,ValueError):location=None
    return {'id':wid,'doi':doi or '', 'display_name':title,
            '_abstract_text':abstract or '', 'publication_year':year,
            'cited_by_count':citations or 0,'type':kind or 'article',
            'abstract_inverted_index':None,'best_oa_location':location,
            '_provider':'local-catalog'}


def catalog_lookup_reference(doi='',arxiv_id='',title=''):
    """Exact DOI/arXiv lookup, or strictly verified title, never a guess."""
    if not LOCAL_CATALOG.exists():return None
    probe={'id':'', 'doi':doi,'_arxiv_id':arxiv_id,'display_name':title}
    keys=[k for k in _catalog_identities(probe) if not k.startswith('source:')]
    if not keys:return None
    try:
        with sqlite3.connect(str(LOCAL_CATALOG),timeout=6) as con:
            for key in keys:
                hit=con.execute('SELECT work_id FROM catalog_identifiers WHERE identity=?',(key,)).fetchone()
                if not hit:continue
                row=con.execute("""SELECT id,doi,title,abstract,year,citations,kind,oa_location
                                   FROM local_works WHERE id=?""",(hit[0],)).fetchone()
                if not row:continue
                work=_catalog_row_to_work(row)
                if doi and normalize_doi(work['doi'])!=normalize_doi(doi):
                    # A record can have multiple DOI aliases (e.g. preprint and journal).
                    # Only an exact key hit proves a valid match.
                    if key!='doi:'+normalize_doi(doi):continue
                if title and not doi and not arxiv_id and _reference_title_similarity(
                        title,work['display_name'])<.92:continue
                return work
    except sqlite3.Error:pass
    return None


def stream_local_works(theory,wanted,stop_event,pause_event=None,progress=None,seen_doi=None):
    """Prioritize exact previous query hits; then use flexible FTS5 retrieval.

    Re-score all hits with the existing mathematics gate. Does not synthesize
    concepts and does not fetch external papers.
    """
    if not local_catalog_available():return
    words=[x.casefold() for x in TOKEN_RE.findall(theory) if len(x)>2 and x.casefold() not in STOP]
    if not words:words=[x.casefold() for x in TOKEN_RE.findall(theory) if len(x)>2]
    if not words:return
    seen_ids=set();yielded=0;page=0
    con=sqlite3.connect(str(LOCAL_CATALOG),timeout=30)
    columns='w.id,w.doi,w.title,w.abstract,w.year,w.citations,w.kind,w.oa_location'
    def emit(rows):
        nonlocal yielded,page
        page+=1;batch=[]
        for row in rows:
            if stop_event.is_set():break
            if row[0] in seen_ids:continue
            seen_ids.add(row[0])
            work=_catalog_row_to_work(row)
            score=score_candidate(work,theory,1/(1+page))
            if score>=.33:batch.append((score,work))
        batch.sort(key=lambda r:r[0],reverse=True)
        if progress:progress(page,0,yielded,len(batch))
        for item in batch:
            if stop_event.is_set():break
            yield item
            yielded+=1
            if yielded>=wanted:break
    try:
        # Exact per-query hits are important if a provider found a relevant
        # paper whose title/abstract wording cannot be recovered by strict AND.
        cursor=con.execute(f"""SELECT {columns} FROM catalog_query_hits h
                      JOIN local_works w ON w.id=h.work_id
                      WHERE h.query_key=? LIMIT ?""",
                      (_catalog_query_key(theory),min(max(100,wanted*2),20000)))
        while not stop_event.is_set():
            rows=cursor.fetchmany(64)
            if not rows:break
            for item in emit(rows):
                yield item
                if yielded>=wanted:return
        terms=['"'+w.replace('"','')+'"' for w in words[:6]]
        # AND prioritizes precision. OR broadens only if AND found too little.
        # fetchmany() avoids loading thousands of 30KB abstracts into RAM
        # simultaneously when 8-20 topic workers use the same local catalog.
        for fts_query in (' AND '.join(terms),' OR '.join(terms)):
            if yielded>=wanted or stop_event.is_set():return
            if not fts_query:continue
            cursor=con.execute(f"""SELECT {columns} FROM local_works_fts f
                    JOIN local_works w ON w.rowid=f.rowid
                    WHERE local_works_fts MATCH ? ORDER BY bm25(local_works_fts)
                    LIMIT ?""",(fts_query,min(max(100,wanted*4),6000)))
            while not stop_event.is_set():
                rows=cursor.fetchmany(64)
                if not rows:break
                for item in emit(rows):
                    yield item
                    if yielded>=wanted:return
    finally:con.close()


def stream_literature(session,theory,wanted,api_key,stop_event,pause_event=None,
                      progress=None,on_retry=None,openalex_enabled=False,
                      openalex_unavailable=None,arxiv_unavailable=None,
                      crossref_unavailable=None):
    """Fair multi-provider harvesting with provenance, DOI/title dedup and caching.

    Provider failures are not proof that a topic is absent. Each provider gets
    a fraction of the topic budget so one source cannot crowd out every other.
    """
    wanted=max(1,int(wanted))
    yielded=0;seen_ids=set();seen_titles=set()
    successes=0;remote_ok=0;remote_failed=False;last_error=None

    providers=[]
    if local_catalog_available():
        providers.append((' local Index ',stream_local_works,None,False))
    if not (arxiv_unavailable and arxiv_unavailable.is_set()):
        providers.append(('arXiv',stream_arxiv,arxiv_unavailable,True))
    if not (crossref_unavailable and crossref_unavailable.is_set()):
        providers.append(('Crossref',stream_crossref,crossref_unavailable,True))
    providers.append(('OpenAIRE',stream_openaire,None,True))
    providers.append(('Europe PMC',stream_europepmc,None,True))
    providers.append(('DBLP',stream_dblp,None,True))
    if os.environ.get('SEMANTIC_SCHOLAR_API_KEY','').strip():
        providers.append(('Semantic Scholar',stream_semantic_scholar,None,True))
    if openalex_enabled and not (openalex_unavailable and openalex_unavailable.is_set()):
        providers.append(('OpenAlex',stream_papers,openalex_unavailable,True))
    # Never hide unconsulted remote providers behind a one-provider cache hit.
    query_fresh=catalog_query_fresh(theory)
    if query_fresh:
        providers=[item for item in providers if not item[3]]
        if on_retry:on_retry(' local query still in valid  TTL  inside ; skip passed recent Successful Search passed online Source ')
    remote_count=sum(p[3] for p in providers)
    remote_share=max(4,math.ceil(wanted/max(1,len(providers))))
    for provider,func,unavailable,remote in providers:
        if stop_event.is_set() or yielded>=wanted:return
        remaining=wanted-yielded
        budget=min(remaining,max(4,remote_share)) if remote else min(remaining,max(8,wanted//5))
        if not budget:continue
        if provider=='OpenAlex':
            iterable=func(session,theory,budget,api_key,stop_event,pause_event,progress,on_retry)
        elif provider==' local Index ':
            iterable=func(theory,budget,stop_event,pause_event,progress)
        else:iterable=func(session,theory,budget,stop_event,pause_event,progress,on_retry)
        pending=[]
        try:
            for score,work in iterable:
                if stop_event.is_set():return
                if remote:
                    pending.append(work)
                    if len(pending)>=_CATALOG_BATCH:
                        try:catalog_store_batch(pending,query=theory,provider=provider)
                        except sqlite3.Error as exc:
                            if on_retry:on_retry(f'{provider}  cache temporarily must not write :{exc}')
                        pending.clear()
                doi=normalize_doi(work.get('doi'))
                title=re.sub(r'[^a-z0-9]+','',str(work.get('display_name','')).casefold())[:180]
                wid=doi or work.get('id','')
                if wid in seen_ids or (title and title in seen_titles):continue
                seen_ids.add(wid)
                if title:seen_titles.add(title)
                yielded+=1
                yield score,work
                if yielded>=wanted:return
            successes+=1
            if remote:remote_ok+=1
        except OpenAlexSearchFailure as exc:
            last_error=exc;remote_failed=True
            if unavailable is not None and exc.category in ('quota','auth','network','server','http'):
                unavailable.set()
            if on_retry:on_retry(f'⚠ {provider}  Unable to Completed :{exc.reason[:180]}; resume its they Source ')
        finally:
            if pending:
                try:catalog_store_batch(pending,query=theory,provider=provider)
                except sqlite3.Error as exc:
                    if on_retry:on_retry(f'{provider}  cache write Failed :{exc}')
    if remote_ok and not remote_failed and not stop_event.is_set():
        try:catalog_mark_query(theory,remote_ok)
        except sqlite3.Error:pass
    if yielded==0 and successes==0:
        if last_error:
            raise OpenAlexSearchFailure(theory,last_error.page,
                ' All available literature providers failed :'+last_error.reason,category=last_error.category,status=last_error.status)
        raise OpenAlexSearchFailure(theory,0,' No literature providers are available ',category='network')


_OPENALEX_RATE_LOCK = threading.Lock()
_OPENALEX_NEXT_REQUEST = [0.0]


def openalex_throttle(stop_event=None, interval=0.35):
    """A modest shared per-process request ceiling across all worker threads."""
    with _OPENALEX_RATE_LOCK:
        now = time.monotonic()
        delay = max(0.0, _OPENALEX_NEXT_REQUEST[0] - now)
        _OPENALEX_NEXT_REQUEST[0] = max(now, _OPENALEX_NEXT_REQUEST[0]) + interval
    if delay > 0:
        if stop_event is not None and stop_event.wait(delay):
            raise InterruptedError(' user abort or service circuit breaker ')
        elif stop_event is None:
            time.sleep(delay)


def openalex_request(session, params, stop_event=None, on_retry=None):
    """Read a page, preserve safe HTTP diagnostics, retry transient failures.

    Returns verified envelope. 400 may be an obsolete sort/select parameter;
    retry a basic query without them, but never silently discard the search.
    A persistent 429, missing authentication or invalid authorization is a
    shared SERVICE failure rather than a theory with zero matching papers.
    """
    supplied = dict(params)
    variants = [supplied]
    if 'sort' in supplied or 'select' in supplied:
        variants.append({k:v for k,v in supplied.items() if k not in ('sort','select')})
    for variant_i, variant in enumerate(variants):
        for attempt in range(3):
            if stop_event and stop_event.is_set():
                raise InterruptedError(' Cancelled ')
            openalex_throttle(stop_event)
            try:
                response = session.get(OPENALEX, params=variant, timeout=(8, 28),
                                       headers=HEADERS)
            except requests.RequestException as exc:
                reason = f'{type(exc).__name__}: {str(exc)[:400]}'
                secret=str(params.get('api_key','') or '')
                if secret:reason=reason.replace(secret,'[API KEY]')
                reason=reason[:240]
                if attempt < 2:
                    if on_retry: on_retry(f'OpenAlex  connection failed , Retry  {attempt+1}/2:{reason}')
                    if stop_event:
                        if stop_event.wait(min(6, 2**attempt)): raise InterruptedError(' Cancelled ')
                    else: time.sleep(min(6, 2**attempt))
                    continue
                raise OpenAlexSearchFailure('', int(params.get('page',1)), reason,
                                           category='network') from exc
            status = response.status_code
            if status == 200:
                try:
                    data = response.json()
                    if not isinstance(data,dict) or not isinstance(data.get('results'),list):
                        raise ValueError('JSON  invalid format or missing  results')
                    return data
                except (ValueError,TypeError) as exc:
                    if attempt < 2:
                        if on_retry:on_retry('OpenAlex  response format abnormal , Later Retry ')
                        time.sleep(0.7 + attempt)
                        continue
                    raise OpenAlexSearchFailure('',int(params.get('page',1)),str(exc),
                                               category='schema') from exc
            try:
                body = response.json()
                detail = str(body.get('message') or body.get('error') or '') if isinstance(body,dict) else ''
            except ValueError:
                detail = re.sub(r'<[^>]*>', ' ', response.text[:250]).strip()
            detail = detail[:400] or response.reason or ' not provided Error description '
            secret=str(params.get('api_key','') or '')
            if secret:detail=detail.replace(secret,'[API KEY]')
            detail=detail[:240]
            if status == 400 and variant_i == 0 and len(variants)>1:
                if on_retry:on_retry(f'OpenAlex HTTP 400({detail}), use no  sort/select  install all query Retry ')
                break
            if status in (401,403):
                raise OpenAlexSearchFailure('',int(params.get('page',1)),
                    f'HTTP {status}:{detail}; Check  OpenAlex API key /  permissions ',
                    category='auth',status=status)
            if status == 429:
                remaining=response.headers.get('X-RateLimit-Remaining','')
                reset=response.headers.get('X-RateLimit-Reset','')
                if on_retry:on_retry('OpenAlex HTTP 429; immediately disable this Source , this run change by  arXiv/Crossref')
                raise OpenAlexSearchFailure('',int(params.get('page',1)),
                    f'OpenAlex HTTP 429：{detail}；remaining={remaining or "?"}；reset={reset or "?"}',
                    category='quota',status=429)
            if status in (408,425,500,502,503,504) and attempt < 2:
                if on_retry:on_retry(f'OpenAlex HTTP {status}:{detail}; temporarily properties Error Retry  {attempt+1}/2')
                if stop_event:
                    if stop_event.wait(1.5 * (attempt+1)): raise InterruptedError(' Cancelled ')
                else: time.sleep(1.5*(attempt+1))
                continue
            kind = 'bad_request' if status==400 else 'server' if status>=500 else 'http'
            raise OpenAlexSearchFailure('',int(params.get('page',1)),
                                        f'HTTP {status}：{detail}',category=kind,status=status)
    raise OpenAlexSearchFailure('',int(params.get('page',1)),
                                'OpenAlex  rejected on grounds this query ',category='bad_request')


def openalex_preflight(session, api_key, stop_event=None, on_retry=None):
    """Test THE SAME fields/sort used by collection before accepting any jobs."""
    params = {'search':'graph theory','sort':'relevance_score:desc', 'page':1,
              'per_page':1,'select':'id,doi,display_name,publication_year,cited_by_count,abstract_inverted_index,best_oa_location,type'}
    if api_key: params['api_key'] = api_key
    return openalex_request(session, params, stop_event=stop_event, on_retry=on_retry)


def stream_papers(session, theory, wanted, api_key, stop_event, pause_event=None,
                  progress=None, on_retry=None):
    """Stream OpenAlex search results; supports up to 1M *accepted* papers.

    For more than 10,000 requested works, cursor pagination avoids OpenAlex's
    documented 10,000-result basic-page limit.  Results are yielded per page,
    not buffered until the target count. The crawl stops when the source runs
    out, two consecutive pages contain no relevant works, or user stops.
    """
    wanted = max(1, min(MAX_PAPERS_PER_THEORY, int(wanted)))
    cursor_mode = wanted > 10_000
    cursor = '*' if cursor_mode else None
    seen = set()
    yielded = 0
    empty_pages = 0
    page = 0
    # Basic paging is valid only for the first 10,000 OpenAlex results.
    basic_page_limit = min(100, max(2, math.ceil(wanted / 100) * 2 + 2))
    # Track cursor values to guard against an erroneous repeated API cursor.
    last_cursor = None
    while yielded < wanted and (cursor_mode or page < basic_page_limit):
        while pause_event is not None and pause_event.is_set() and not stop_event.is_set():
            time.sleep(.15)
        if stop_event.is_set():
            return
        page += 1
        params = {'search': theory, 'sort': 'relevance_score:desc',
                  'per_page': 100, 'select': OPENALEX_FIELDS}
        if cursor_mode:
            params['cursor'] = cursor
        else:
            params['page'] = page
        if api_key:
            params['api_key'] = api_key
        try:
            payload = openalex_request(session, params, stop_event, on_retry=on_retry)
        except OpenAlexSearchFailure as exc:
            raise OpenAlexSearchFailure(theory, page, exc.reason,
                                        category=exc.category, status=exc.status) from exc
        rows = payload['results']
        if not rows:
            if progress:
                progress(page, 0 if cursor_mode else basic_page_limit, yielded, 0)
            return
        batch = []
        for rank, work in enumerate(rows):
            wid = work.get('id') if isinstance(work, dict) else None
            if not wid or not work.get('display_name') or wid in seen:
                continue
            seen.add(wid)
            if work.get('type') not in (None, 'article', 'preprint', 'review',
                                        'proceedings-article', 'book-chapter'):
                continue
            rank_bonus = 1 / (1 + (page - 1) * .8 + rank / 80)
            score = score_candidate(work, theory, rank_bonus)
            if score >= .33:
                batch.append((score, work))
        batch.sort(key=lambda pair: pair[0], reverse=True)
        empty_pages = empty_pages + 1 if not batch else 0
        if progress:
            progress(page, 0 if cursor_mode else basic_page_limit, yielded, len(batch))
        for score, work in batch:
            if stop_event.is_set():
                return
            while pause_event is not None and pause_event.is_set() and not stop_event.is_set():
                time.sleep(.15)
            yield score, work
            yielded += 1
            if yielded >= wanted:
                return
        if empty_pages >= 2 or len(rows) < 100:
            return
        if cursor_mode:
            next_cursor = (payload.get('meta') or {}).get('next_cursor')
            if not next_cursor:
                return
            if next_cursor == cursor or next_cursor == last_cursor:
                raise OpenAlexSearchFailure(theory, page,
                    'OpenAlex  transmit return duplicate  cursor, already stop to avoid duplicate read ', category='schema')
            last_cursor, cursor = cursor, next_cursor


# ---------------------------------------------------------------------------
# FLIN v16: persistent, breadth-first mathematics discovery.
# There is no positional Wikipedia offset: identities and page cursors survive
# restarts, changing API ordering, and interrupted batches.
# ---------------------------------------------------------------------------

def flin_seed_discovery(con):
    """Seed a durable, per-network frontier without resetting completed work."""
    abc_schema(con)
    with con:
        con.executemany('''INSERT OR IGNORE INTO flin_discovery_categories(name,depth)
            VALUES(?,0)''', [(x,) for x in MATH_CATEGORIES if math_category_ok(x)])
        con.executemany('''INSERT OR IGNORE INTO flin_discovery_topics(name,url,origin)
            VALUES(?,?,'seed')''',
            [(x,wikipedia_article_url(x)) for x in mathematics_discovery_seeds()
             if math_page_title_ok(x)])
        # A previous process may have exited while a producer had queued work.
        # Processed work is separately protected by the abc_topics state gate.
        con.execute("UPDATE flin_discovery_topics SET state='pending' WHERE state='claimed'")
        con.execute('''UPDATE flin_discovery_topics SET state='archived'
            WHERE state='pending' AND EXISTS (
                SELECT 1 FROM abc_topics a WHERE a.name=flin_discovery_topics.name
                AND a.state IN ('complete','no_candidates','off_topic'))''')
        # Failed pages are retried once per collector launch, then after a cooldown.
        # Resetting them on EVERY frontier probe can cause an endless hot retry
        # loop when a provider is down, with the GUI appearing frozen.



def flin_discovery_counts(con):
    categories=dict(con.execute('''SELECT state,COUNT(*)
        FROM flin_discovery_categories GROUP BY state''').fetchall())
    topics=dict(con.execute('''SELECT state,COUNT(*)
        FROM flin_discovery_topics GROUP BY state''').fetchall())
    return {'category_pages':int(con.execute('''SELECT COALESCE(SUM(pages),0)
        FROM flin_discovery_categories''').fetchone()[0]),
        'categories':categories,'topics':topics,
        'processed_topics':int(con.execute('SELECT COUNT(*) FROM abc_topics').fetchone()[0])}


def flin_expand_memory_topics(con, limit=500):
    """Find further scholarly search topics from *source-grounded* FLIN units.

    This is a search-lead generator, NOT a new memory or a semantic edge.
    The rowid cursor is persisted; it can resume when more units are learned.
    """
    row=con.execute("SELECT value FROM flin_discovery_meta WHERE key='memory_scan_rowid'").fetchone()
    after=int(row[0]) if row else 0
    rows=con.execute('''SELECT rowid,label FROM abc_units
        WHERE rowid>? AND status='active' AND quality>=75
        ORDER BY rowid LIMIT ?''',(after,limit)).fetchall()
    if not rows:return 0,False
    added=0
    with con:
        for _,label in rows:
            # Only explicit, well-formed mathematical expressions are searched.
            if not (math_concept_quality(label)[0] and
                    math_topic_quality(label)[0] and math_page_title_ok(label)):
                continue
            before=con.total_changes
            con.execute('''INSERT OR IGNORE INTO flin_discovery_topics
                (name,url,origin) VALUES(?,'','flin_memory')''',(label,))
            added+=con.total_changes-before
        con.execute('''INSERT INTO flin_discovery_meta(key,value)
            VALUES('memory_scan_rowid',?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value''',(str(rows[-1][0]),))
    return added,True


def flin_stream_discovery(con, session, limit, stop_event, on_topic,
                          log=None, wait_if_paused=None, max_depth=10):
    """Continuously stream UNSEEN mathematics topics from a SQLite frontier.

    A page and all its discovered members are committed atomically. API errors
    remain retryable and are reported distinctly from real frontier exhaustion.
    Returns (status, statistics). It never claims to exhaust all mathematics.
    """
    flin_seed_discovery(con)
    queued=pages=page_errors=0
    errors=[]
    consecutive_empty_pages=0
    while queued < limit and not stop_event.is_set():
        if wait_if_paused:wait_if_paused()
        if stop_event.is_set():break
        row=con.execute('''SELECT f.name,f.url FROM flin_discovery_topics f
            WHERE f.state='pending' AND NOT EXISTS (
              SELECT 1 FROM abc_topics a WHERE a.name=f.name
              AND a.state IN ('complete','off_topic','no_candidates'))
            ORDER BY f.rowid LIMIT 1''').fetchone()
        if row:
            title,url=row
            # Callback reports True only when successfully placed on worker queue.
            if not on_topic(title,url,queued):break
            with con:
                con.execute("UPDATE flin_discovery_topics SET state='claimed' WHERE name=?",(title,))
            queued+=1
            continue
        # Mark already processed/persisted topics once, avoiding repeated probes.
        with con:
            con.execute('''UPDATE flin_discovery_topics SET state='archived'
                WHERE state='pending' AND EXISTS (
                  SELECT 1 FROM abc_topics a WHERE a.name=flin_discovery_topics.name
                  AND a.state IN ('complete','off_topic','no_candidates'))''')
        cat=con.execute('''SELECT name,depth,continuation FROM flin_discovery_categories
            WHERE state='pending' ORDER BY depth,pages,name LIMIT 1''').fetchone()
        if cat is None:
            # Wikipedia categories may be finite; grow the literature search
            # frontier from mathematical memories collected from real sources.
            added,scanned=flin_expand_memory_topics(con)
            if scanned:
                if added and log:log(f'FLIN  Memory unit derived  {added}  items Mathematics literature search Topic .')
                continue
            break
        name,depth,stored_cursor=cat
        try:
            cursor=json.loads(stored_cursor or '{}')
            params={'action':'query','list':'categorymembers','format':'json',
                'formatversion':2,'cmtitle':name,'cmtype':'page|subcat',
                'cmprop':'title|type','cmlimit':500,**cursor}
            payload=get_json(session,WIKI_API,params,tries=3)
            if 'error' in payload:raise RuntimeError(str(payload['error'])[:250])
            query=payload.get('query') or {}
            members=query.get('categorymembers')
            if not isinstance(members,list):raise RuntimeError('MediaWiki  response missing  categorymembers')
            next_cursor=payload.get('continue') or {}
            if next_cursor == cursor and next_cursor:
                raise RuntimeError('MediaWiki  duplicate return the same parts pages cursor label ')
            discovered=[];subcats=[]
            for entry in members:
                title=str(entry.get('title') or '').strip()
                if ((entry.get('ns')==14 or entry.get('type')=='subcat')
                        and depth < max_depth and math_category_ok(title)):
                    subcats.append((title,depth+1))
                elif ((entry.get('ns')==0 or entry.get('type')=='page')
                        and math_page_title_ok(title)):
                    discovered.append((title,wikipedia_article_url(title)))
            with con:
                if discovered:
                    con.executemany('''INSERT OR IGNORE INTO flin_discovery_topics
                        (name,url,origin) VALUES(?,?,'wikipedia')''',discovered)
                if subcats:
                    con.executemany('''INSERT OR IGNORE INTO flin_discovery_categories
                        (name,depth) VALUES(?,?)''',subcats)
                con.execute('''UPDATE flin_discovery_categories
                    SET continuation=?,state=?,pages=pages+1,last_error=''
                    WHERE name=?''',
                    (json.dumps(next_cursor,ensure_ascii=False),
                     'pending' if next_cursor else 'done',name))
            pages+=1
            if pages<=3 or pages%25==0:
                if log:log(f' Mathematics category Discover : already read  {pages}  pages |{name}|'
                           f' New Candidate article  {len(discovered)}| New subcategories  {len(subcats)}')
            consecutive_empty_pages=(consecutive_empty_pages+1 if not discovered else 0)
            # Respect a modest request rate and service limits; no scraping APIs.
            time.sleep(.20)
        except Exception as exc:
            page_errors+=1
            detail=f'{name}: {type(exc).__name__}: {str(exc)[:200]}'
            errors.append(detail)
            with con:
                con.execute('''UPDATE flin_discovery_categories
                    SET state='error',failures=failures+1,last_error=? WHERE name=?''',
                    (detail[:350],name))
            if log:log(f'⚠  category Discover temporarily Failed ( next run can continue exploring ):{detail}')
            # A failed category must not hide the rest of the queue.
            if page_errors>=15:break
    stats={'queued':queued,'pages':pages,'page_errors':page_errors,
           'frontier':flin_discovery_counts(con),'last_error':errors[-1] if errors else ''}
    if stop_event.is_set():return 'stopped',stats
    if queued >= limit:return 'batch_limit',stats
    if stats['frontier']['categories'].get('error',0):return 'source_limited',stats
    return 'frontier_idle',stats


# A finite SOURCE frontier can be drained; no amount of crawling proves that all
# mathematics is known. The completion flag therefore describes only the source
# snapshot, not universal scientific or theoretical completeness.
FLIN_FRONTIER_RECHECK_HOURS = max(1, min(168, int(os.environ.get('FLIN_FRONTIER_RECHECK_HOURS', '24'))))


def flin_frontier_health(con, *, workers_pending=0):
    """Evaluate the complete persistent frontier, not the GUI's visible graph.

    A single failure, queued topic, unprocessed memory-unit search lead, or
    outstanding worker blocks any assertion of finished collection.
    """
    cats = dict(con.execute('SELECT state,COUNT(*) FROM flin_discovery_categories GROUP BY state'))
    topics = dict(con.execute('SELECT state,COUNT(*) FROM flin_discovery_topics GROUP BY state'))
    incomplete = int(con.execute("""SELECT COUNT(*) FROM abc_topics WHERE state IN
        ('running','skipped_search','error','interrupted','partial')""").fetchone()[0])
    replay = int(con.execute('SELECT COUNT(*) FROM abc_replay_queue').fetchone()[0])
    # Has the incremental memory->literature cursor actually visited all units?
    scan_row = con.execute("SELECT value FROM flin_discovery_meta WHERE key='memory_scan_rowid'").fetchone()
    scan_through = int(scan_row[0]) if scan_row else 0
    later_units = int(con.execute("SELECT COUNT(*) FROM abc_units WHERE rowid>? AND status='active'",
                                  (scan_through,)).fetchone()[0])
    # Completion must not ignore older, locally saved abstracts that still
    # await extraction under the improved grounded concept recognizer.
    cached_row=con.execute("SELECT value FROM abc_meta WHERE key='flin_source_input_backfill_v2_rowid'").fetchone()
    cached_after=int(cached_row[0]) if cached_row else 0
    cached_pending=int(con.execute('SELECT COUNT(*) FROM abc_sources WHERE rowid>?',
                                    (cached_after,)).fetchone()[0])
    unresolved = (cached_pending
                  + sum(cats.get(k,0) for k in ('pending','error','running'))
                  + sum(topics.get(k,0) for k in ('pending','claimed','error'))
                  + incomplete + replay + later_units + max(0,int(workers_pending)))
    return {'complete': unresolved==0, 'unresolved':unresolved,
            'categories':cats, 'topics':topics, 'failed_topics':incomplete,
            'pending_replay':replay, 'unscanned_active_units':later_units,
            'cached_sources_pending_backfill':cached_pending,
            'workers_pending':int(workers_pending)}


def flin_clear_verified_frontier(con):
    with con:
        con.execute("DELETE FROM flin_discovery_meta WHERE key IN "
                    "('verified_frontier_utc','verified_frontier_counts')")


def flin_store_verified_frontier(con, state):
    if not state['complete']:
        raise ValueError('Cannot mark an incomplete literature frontier as completed.')
    with con:
        con.execute("""INSERT OR REPLACE INTO flin_discovery_meta(key,value)
            VALUES('verified_frontier_utc',?)""",
            (datetime.datetime.now(datetime.timezone.utc).isoformat(),))
        con.execute("""INSERT OR REPLACE INTO flin_discovery_meta(key,value)
            VALUES('verified_frontier_counts',?)""",
            (json.dumps(state,ensure_ascii=False,sort_keys=True),))


def flin_recent_verified_frontier(con, *, now=None):
    stamp=con.execute("SELECT value FROM flin_discovery_meta "
                      "WHERE key='verified_frontier_utc'").fetchone()
    if not stamp:
        return False
    try:
        verified=datetime.datetime.fromisoformat(stamp[0])
        if verified.tzinfo is None:
            verified=verified.replace(tzinfo=datetime.timezone.utc)
        clock=now or datetime.datetime.now(datetime.timezone.utc)
        if (clock-verified).total_seconds() >= FLIN_FRONTIER_RECHECK_HOURS*3600:
            return False
        return flin_frontier_health(con)['complete']
    except (ValueError,TypeError):
        return False


class Collector(threading.Thread):
    """Streaming topic producer + independent bounded topic workers.

    Manual topics are resolved inside the workers, not serially by the producer.
    Workers have their own HTTP sessions and SQLite connections. A shared lock
    makes graph writes atomic across workers (no duplicate paper edge races).
    SQLite/WAL permits the Tk viewer to read while the network is expanding.
    """
    def __init__(self, out, stop_event, theory_count, papers_per_theory,
                 start_offset, read_pdf, api_key, pause_event=None, workers=3,
                 cpu_budget=None, retry_failed_only=False, wikipedia_references=True,
                 references_only=False, manual_topics=None, continuous=False):
        super().__init__(daemon=True)
        self.manual_topics = list(manual_topics or [])
        self.continuous = bool(continuous)
        self.discovery_outcome = ''
        self.discovery_stats = {}
        # Thread-safe Event wakeup: GUI never calls Tk from this background thread.
        self.wake_discovery = threading.Event()
        self.phase = 'starting'
        self.idle_until = 0.0
        self.last_activity = time.monotonic()
        self.phase_started = self.last_activity
        self.out, self.stopped = out, stop_event
        self.pause_event = pause_event if pause_event is not None else threading.Event()
        self.count, self.per_theory = theory_count, papers_per_theory
        self.start_offset, self.read_pdf, self.api_key = start_offset, read_pdf, api_key
        self.use_wikipedia_references = bool(wikipedia_references) or references_only
        self.references_only=bool(references_only)
        capacity = detect_cpu_resources()['available']
        self.workers = max(1, min(capacity, int(workers)))
        self.cpu_budget = max(1, min(capacity, int(cpu_budget if cpu_budget is not None else capacity)))
        self.writer_lock = threading.RLock()
        with database() as _abc_con:
            abc_enable(_abc_con)
            self.abc_mode=True
        self.jobs = queue.Queue(maxsize=self.workers * 2)
        self.enqueued = 0
        self.completed = 0
        self.failed = 0
        self.skipped_search = 0
        self.counter_lock = threading.Lock()
        self.retry_failed_only = retry_failed_only
        self.succeeded = 0
        self.no_candidates = 0
        self.consecutive_api_failures = 0
        self.block_reason = ''
        self.openalex_enabled = os.environ.get('BRAIN_USE_OPENALEX','0') == '1'
        self.openalex_unavailable = threading.Event()
        self.arxiv_unavailable = threading.Event()
        self.crossref_unavailable = threading.Event()
        # Canonical Wikipedia titles may resolve from multiple input aliases.
        # Only one worker may write a given resolved topic at a time.
        self._manual_claimed = set()
        self._retry_attempts = defaultdict(int)
        self._retry_limit = max(0,min(4,int(os.environ.get('FLIN_AUTO_RETRY_LIMIT','2'))))
        self._retry_wait = max(1,min(300,int(os.environ.get('FLIN_RETRY_WAIT_SECONDS','15'))))
        self._auto_repair_status = ''
        self._verified_frontier = False
        self._worker_last_event = {}
        self._worker_active = {}
        # Migrate incomplete old-process work only at start of a NEW collector.
        # Never rewrite 'running' while another live collector owns those jobs.
        with contextlib.closing(database()) as fix_con:
            with fix_con:
                restored=fix_con.execute("""UPDATE abc_topics SET state='interrupted',
                    message='Recovered incomplete previous build; scheduled for retry',
                    updated=CURRENT_TIMESTAMP WHERE state='running' """).rowcount
                fix_con.execute("""UPDATE flin_discovery_topics SET state='pending'
                    WHERE state='claimed' OR (state='archived' AND name IN
                    (SELECT name FROM abc_topics WHERE state IN
                    ('interrupted','partial','error','skipped_search')))""")
                if restored:
                    flin_clear_verified_frontier(fix_con)
        if restored:
            self.out.put(('discovery',f'Recovered {restored} unfinished topics from the previous session.'))

    def _record_api_outcome(self, success=False, error=None):
        """Never stop the entire crawl for one provider's quota/auth failure."""
        if success or error is None:return
        with self.counter_lock:
            self.consecutive_api_failures += 1
        self.log('⚠  literature provider Failed (OpenAlex  quota insufficient will not interrupt its they Source ):'+str(error)[:250])
        if (self.arxiv_unavailable.is_set() and self.crossref_unavailable.is_set()
                and (not self.openalex_enabled or self.openalex_unavailable.is_set())
                and not local_catalog_available()):
            with self.counter_lock:
                if self.block_reason:return
                self.block_reason=' Current All literature provider all Failed , retain not yet Completed Topic pending retry ; Check  arXiv/Crossref  connection .'
            self.stopped.set()
            self.pause_event.clear()
            self.out.put(('service_alert',self.block_reason))

    def log(self, message):
        self.last_activity = time.monotonic()
        self.out.put(('log', message))

    def _set_phase(self, phase, info=''):
        self.phase = phase
        self.phase_started = time.monotonic()
        self.last_activity = self.phase_started
        self.out.put(('collector_phase', (phase, info)))

    def request_immediate_discovery(self):
        """Wake a genuinely idle collector; never start a second collector."""
        if self.is_alive() and self.phase == 'idle':
            self.wake_discovery.set()
            return True
        return False

    def wait_if_paused(self):
        while self.pause_event.is_set() and not self.stopped.is_set():
            time.sleep(.15)

    def _send_worker(self, worker, title, phase, done=0, target=0, page=0, linked=0):
        self.last_activity = time.monotonic()
        with self.counter_lock:
            self._worker_last_event[worker] = self.last_activity
            if title and not str(phase).lower().startswith(('finished','idle')):
                self._worker_active[worker] = title
            else:
                self._worker_active.pop(worker,None)
        self.out.put(('worker', (worker, title, phase, done, target, page, linked)))

    def _put_job(self, item):
        first_wait = time.monotonic()
        reported_backpressure = False
        while not self.stopped.is_set():
            self.wait_if_paused()
            try:
                self.jobs.put(item, timeout=.25)
                if reported_backpressure and self.phase == 'queue_backpressure':
                    self._set_phase('discovering')
                return True
            except queue.Full:
                # A full work queue means collector is working, not stopped.
                # In slow-PDF/API cases this previously looked like a hung GUI.
                if not reported_backpressure and time.monotonic()-first_wait > 7.0:
                    reported_backpressure = True
                    self._set_phase('queue_backpressure', self.jobs.unfinished_tasks)
        return False

    def _process_theory(self, worker, theory, url):
        return self._process_theory_abc(worker, theory, url)
        # Historical literature-graph implementation is intentionally unreachable.
        con = database()
        session = requests.Session()
        found, processed, linked, failures = 0, 0, 0, 0
        phase = 'Wikipedia'
        failure_detail = ''
        previous_progress = None
        self._send_worker(worker, theory, phase)
        self.log(f'⚙ W{worker}   Topic Start :{theory}')
        try:
            with self.writer_lock, con:
                if self.references_only:
                    previous_progress=con.execute("""SELECT state,found,processed,
                        newly_linked,failures,message FROM theory_progress
                        WHERE name=?""",(theory,)).fetchone()
                con.execute("""INSERT INTO theory_progress
                    (name,state,found,processed,newly_linked,failures,message,updated)
                    VALUES(?,'running',0,0,0,0,'Wikipedia',CURRENT_TIMESTAMP)
                    ON CONFLICT(name) DO UPDATE SET state='running',found=0,
                    processed=0,newly_linked=0,failures=0,message='Wikipedia',
                    updated=CURRENT_TIMESTAMP""", (theory,))
            # Do not introduce an unverified non-mathematical topic into the
            # knowledge graph while its Wikipedia description is being read.
            wiki_refs=[]
            if url:
                try:
                    wiki_text, wiki_refs = get_wikipedia_article(session, url)
                    self.log(f'✓ W{worker} Wikipedia:{theory}; article text  {len(wiki_text)}  characters ,'
                             f' references  {len(wiki_refs)}  records ')
                except Exception as exc:
                    wiki_text = ''
                    self.log(f'⚠ W{worker} Wikipedia  article text / references read Failed  {theory}: {exc}')
            else:
                wiki_text = ''
                self.log(f'○ W{worker} {theory}: no already confirm  Wikipedia  article , use Topic name Search Literature .')
            self.wait_if_paused()
            if self.stopped.is_set():
                raise InterruptedError(' Cancelled ')
            if not self.references_only:
                topic_ok,topic_reason=math_topic_quality(theory,wiki_text)
                if not topic_ok:
                    state='off_topic'
                    failure_detail=' research Topic quality threshold :'+topic_reason
                    self.log(f' Quality skip passed  W{worker} {theory}: {topic_reason}')
                    return
            with self.writer_lock:
                add_theory_memory(con, theory, url, wiki_text)
                if wiki_refs and self.use_wikipedia_references:
                    save_wikipedia_references(con,theory,wiki_refs)
            self.out.put(('refresh', None))
            if wiki_refs and self.use_wikipedia_references:
                phase='Wikipedia  references '
                self._send_worker(worker,theory,phase,processed,self.per_theory)
                possible=sum(r['status']=='found' for r in wiki_refs)
                self.log(f'W{worker} {theory}: read to  {len(wiki_refs)}  edges Source ,'
                         f'{possible}  edges suspected Paper ; Start  DOI/ title Verify .')
                ref_done=0
                try:
                    with self.writer_lock:
                        linked_refs={row[0] for row in con.execute("""SELECT reference_key FROM wikipedia_references
                            WHERE theory=? AND status='linked' """,(theory,))}
                    pending_refs=[r for r in wiki_refs if r['key'] not in linked_refs]
                    for ref,work in resolve_wikipedia_references(
                             session,pending_refs,self.api_key,self.stopped,
                             log=lambda detail:self.log(f'⚠ W{worker}  citation Verify :{detail}'),
                             limit=self.per_theory,openalex_enabled=(self.openalex_enabled and not self.openalex_unavailable.is_set()),
                             unavailable_event=self.openalex_unavailable,
                             arxiv_unavailable=self.arxiv_unavailable,
                             crossref_unavailable=self.crossref_unavailable):
                        self.wait_if_paused()
                        if self.stopped.is_set():break
                        if processed>=self.per_theory:break
                        ref_done+=1
                        if work:
                            valid,conf,reason=paper_math_quality(work,theory)
                            if not valid:
                                with self.writer_lock, con:
                                    store_paper_quality(con,work,theory,False,conf,reason)
                                    con.commit()
                                    mark_wikipedia_citation(con,theory,ref,error=' Domain quality filter :'+reason)
                                processed+=1
                                continue
                            # Bibliography references already present in the
                            # DB are relinked without re-parsing their content.
                            with self.writer_lock:
                                exists=con.execute('''SELECT 1 FROM paper_theories
                                    WHERE paper_id=? AND theory=?''',
                                    (work['id'],theory)).fetchone() is not None
                                already=con.execute('SELECT 1 FROM papers WHERE id=?',
                                    (work['id'],)).fetchone() is not None
                            paper_text=(obtain_pdf_text(session,work,ref.get('url',''))
                                if self.read_pdf and not already and not exists else '')
                            prepared=prepare_paper_payload(work,paper_text,lightweight=already,
                                make_abc_clusters=self.abc_mode)
                            with self.writer_lock:
                                if not exists and paper_to_memory(con,theory,url,work,
                                            1.25,paper_text,bool(paper_text),prepared=prepared):
                                    linked+=1
                                mark_wikipedia_citation(con,theory,ref,work)
                            found+=1;processed+=1
                            self._send_worker(worker,theory,' citation Paper Import ',processed,
                                              self.per_theory,0,linked)
                            self.out.put(('refresh',None))
                        else:
                            with self.writer_lock:
                                mark_wikipedia_citation(con,theory,ref)
                    self.log(f'✓ W{worker} {theory}: already Verify  {ref_done}  records Wikipedia citation Candidate ,'
                             f' imported successfully / Associations  {processed}  papers , resume its they Source Topic Search .')
                except OpenAlexSearchFailure as exc:
                    # Failure to resolve a citation is NOT proof it isn't a
                    # research paper. Never silently mark 200 entries skipped.
                    self.log(f'⚠ W{worker}  Wikipedia citation Verify in break , save existing Results :{exc}')
                    # Continue with arXiv/Crossref general search even if
                    # individual DOI/title reference verification fails.
                except Exception as exc:
                    self.log(f'⚠ W{worker}  Wikipedia citation extraction Failed , fall back to normal Search :'
                             f'{type(exc).__name__}: {str(exc)[:220]}')
                with self.writer_lock,con:
                    con.execute('''UPDATE theory_progress SET found=?,processed=?,
                        newly_linked=?,message=?,updated=CURRENT_TIMESTAMP WHERE name=?''',
                        (found,processed,linked,f' Wikipedia citation Processed  {ref_done}  records ',theory))
            if self.references_only:
                # Existing networks can enrich their citations without repeating
                # the expensive general-topic OpenAlex search.
                with self.writer_lock:
                    linked_total=con.execute("SELECT COUNT(*) FROM wikipedia_references "
                        "WHERE theory=? AND status='linked'",(theory,)).fetchone()[0]
                state='complete' if linked_total else 'no_candidates'
                self.log(f'✓ W{worker}  Wikipedia citation Backfill Completed :{theory}; New Association  {linked}  papers .')
                return
            if processed >= self.per_theory:
                state='complete'
                self.log(f'✓ W{worker} {theory}: already by Wikipedia citation reached to this run Paper maximum .')
                return
            phase = ' multiple Source Literature sequence stream '
            self._send_worker(worker, theory, phase)
            last_notify = time.monotonic()

            def page_progress(page, total_pages, emitted, batch_size):
                self._record_api_outcome(success=True)
                self._send_worker(worker, theory, ' Search page ', processed, self.per_theory,
                                  page, linked)
                self.log(f'W{worker} {theory} ·  literature provider pages  {page}' + (f'/{total_pages}' if total_pages else "(cursor)") + f', this pages meets threshold  {batch_size} papers')

            for score, work in stream_literature(session, theory, max(1,self.per_theory-processed),
                        self.api_key, self.stopped, self.pause_event, progress=page_progress,
                        on_retry=lambda detail: self.log(f'⚠ W{worker} {theory}: {detail}'),
                        openalex_enabled=self.openalex_enabled,
                        openalex_unavailable=self.openalex_unavailable,
                        arxiv_unavailable=self.arxiv_unavailable,
                        crossref_unavailable=self.crossref_unavailable):
                self.wait_if_paused()
                if self.stopped.is_set():
                    break
                if processed >= self.per_theory:
                    break
                found += 1
                try:
                    # A rejected off-domain paper must never trigger an expensive
                    # PDF download or untrusted graph insertion.
                    admissible,confidence,reason=paper_math_quality(work,theory)
                    if not admissible:
                        with self.writer_lock, con:
                            store_paper_quality(con,work,theory,False,confidence,reason)
                            con.commit()
                        processed+=1
                        if processed<=3 or processed%20==0:
                            self.log(f' Quality reject  W{worker} {theory}: {reason}( #  {processed}  records Candidate )')
                        continue
                    # Fetch PDF outside DB lock. Other workers continue independently.
                    with self.writer_lock:
                        exists = con.execute(
                          'SELECT 1 FROM paper_theories WHERE paper_id=? AND theory=?',
                          (work['id'], theory)).fetchone() is not None
                        already = con.execute('SELECT 1 FROM papers WHERE id=?',
                                              (work['id'],)).fetchone() is not None
                    pdf_text = (obtain_pdf_text(session, work)
                                if self.read_pdf and not exists and not already else '')
                    if not exists:
                        # TF-IDF and summary extraction happen concurrently outside
                        # the short SQLite transaction lock.
                        prepared = prepare_paper_payload(work, pdf_text, lightweight=already,
                                    make_abc_clusters=self.abc_mode)
                        with self.writer_lock:
                            if paper_to_memory(con, theory, url, work, score,
                                               pdf_text, bool(pdf_text), prepared=prepared):
                                linked += 1
                except Exception as exc:
                    failures += 1
                    self.log(f'⚠ W{worker} {theory}  #  {found}  papers Failed :{type(exc).__name__}: {exc}')
                processed += 1
                with self.writer_lock, con:
                    con.execute("""UPDATE theory_progress SET found=?,processed=?,
                        newly_linked=?,failures=?,message=?,updated=CURRENT_TIMESTAMP
                        WHERE name=?""", (found,processed,linked,failures,
                                          f' sequence stream Import #  {processed} papers',theory))
                now = time.monotonic()
                # UI refresh is coalesced; database commits remain per paper.
                if now-last_notify >= .30 or processed <= 2 or processed % 5 == 0:
                    self._send_worker(worker, theory, ' Import Paper ', processed,
                                      self.per_theory, 0, linked)
                    self.out.put(('refresh', None))
                    last_notify = now
            if self.stopped.is_set():
                state='interrupted'
            elif failures:
                state='partial'
            elif processed == 0:
                state='no_candidates'
            else:
                state='complete'
        except InterruptedError:
            state = 'interrupted'
        except OpenAlexSearchFailure as exc:
            state = 'skipped_search'
            failures += 1
            failure_detail = (f' multiple Source Literature  {exc.category} /  pages  {exc.page}:{exc.reason}')
            if self.api_key:
                failure_detail = failure_detail.replace(self.api_key, '[API KEY]')
            self.log(f'⏭ W{worker} {theory}: already Import  {processed}  papers ; search failed :{failure_detail}')
            with self.writer_lock, con:
                con.execute("""INSERT INTO openalex_failures(theory,page,category,status,reason)
                               VALUES(?,?,?,?,?)""",
                            (theory,exc.page,exc.category,exc.status,failure_detail[:1200]))
            self._record_api_outcome(error=exc)
        except Exception as exc:
            state = 'error'
            failures += 1
            failure_detail = f'{phase}：{type(exc).__name__}: {str(exc)[:320]}'
            self.log(f'✕ W{worker} {theory} {failure_detail}')
        finally:
            with self.writer_lock, con:
                if self.references_only:
                    con.execute("""INSERT INTO wikipedia_reference_scans
                        (theory,state,processed,added,message,updated)
                        VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)
                        ON CONFLICT(theory) DO UPDATE SET state=excluded.state,
                        processed=excluded.processed,added=excluded.added,
                        message=excluded.message,updated=CURRENT_TIMESTAMP""",
                        (theory,state,processed,linked,
                         (failure_detail or f' citation Backfill :{processed}  papers , New  {linked}  edges ')[:900]))
                if self.references_only and previous_progress:
                    # The enrichment scan must not erase the original
                    # thematic-OpenAlex crawl completion / failure status.
                    con.execute("""UPDATE theory_progress SET
                        state=?,found=?,processed=?,newly_linked=?,failures=?,message=?
                        WHERE name=?""",(*previous_progress,theory))
                else:
                    con.execute("""UPDATE theory_progress SET state=?,found=?,processed=?,
                          newly_linked=?,failures=?,message=?,updated=CURRENT_TIMESTAMP
                          WHERE name=?""", (state,found,processed,linked,failures,
                                          (failure_detail or f'{processed}  papers already Import ;{state}')[:1200], theory))
            with self.counter_lock:
                self.completed += 1
                if state == 'skipped_search':
                    self.skipped_search += 1
                elif state == 'complete':
                    self.succeeded += 1
                elif state in ('no_candidates','off_topic'):
                    self.no_candidates += 1
                elif state in ('error', 'partial'):
                    self.failed += 1
                finished = self.completed
            self._send_worker(worker, theory, ' Completed :'+state,
                              processed, self.per_theory, 0, linked)
            self.out.put(('theory_finished', (worker,theory,state,processed,linked,finished)))
            self.out.put(('refresh', None))
            self.log(f'■ W{worker} {theory}:{state};{processed}  papers , New Associations  {linked}; already store file ')
            session.close()
            con.close()

    def _process_theory_abc(self, worker, theory, url):
        '''Wikipedia / scholarly documents -> FLIN clusters directly.

        There is deliberately no call to add_theory_memory(),
        paper_to_memory(), add_unit() or upsert_edge(). The original graph's
        units/edges/papers/theories tables remain unchanged throughout.
        '''
        session=requests.Session()
        con=database()
        found=processed=linked=failures=0
        accepted_papers=new_memories=new_input_clusters=missing_math_inputs=0
        phase='Wikipedia';state='running';failure_detail=''
        self._send_worker(worker,theory,phase)
        self.log(f'Starting direct FLIN learning from mathematical sources: {theory}')
        try:
            with self.writer_lock,con:
                con.execute('''INSERT INTO abc_topics(name,url,state,found,processed,linked,failures,message)
                    VALUES(?,?,'running',0,0,0,0,'Wikipedia')
                    ON CONFLICT(name) DO UPDATE SET url=excluded.url,state='running',
                    message='Wikipedia',updated=CURRENT_TIMESTAMP''',(theory,url or ''))
            wiki_text='';references=[]
            if url:
                try:
                    wiki_text,references=get_wikipedia_article(session,url)
                    self.log(f'Wikipedia: {theory}; article excerpt {len(wiki_text)} characters; {len(references)} references')
                except Exception as exc:
                    self.log(f'Warning: Wikipedia content unavailable for {theory}: {str(exc)[:200]}')
            self.wait_if_paused()
            if self.stopped.is_set():raise InterruptedError()
            if not self.references_only:
                valid,reason=math_topic_quality(theory,wiki_text)
                if not valid:
                    state='off_topic';failure_detail=reason
                    return
            # Article is evidence, not a mathematics theory memory node.
            if wiki_text:
                wid='wiki:'+hashlib.sha256(theory.casefold().encode('utf-8')).hexdigest()[:24]
                prepared=abc_extract_input_clusters(wid,theory,wiki_text,'',url,max_clusters=64)
                with self.writer_lock:
                    abc_register_source(con,wid,'wikipedia',theory,url,wiki_text,topic=theory)
                    wiki_outcome=abc_ingest_online_clusters(con,wid,theory,wiki_text,url=url,
                                               prepared_clusters=prepared)
                    flin_record_ingest_diagnostic(con,wid,theory,wiki_outcome)
                    con.execute('''INSERT INTO flin_source_depth(source_id,provider,read_level,text_chars)
                        VALUES(?,'Wikipedia','article_excerpt',?)
                        ON CONFLICT(source_id) DO UPDATE SET
                        text_chars=MAX(flin_source_depth.text_chars,excluded.text_chars)''',
                        (wid,len(wiki_text)))
                    con.commit()
                self.out.put(('refresh',None))
            seen=set()
            def accept_work(work, fallback_pdf_url=''):
                nonlocal found,processed,linked,failures
                nonlocal accepted_papers,new_memories,new_input_clusters,missing_math_inputs
                if self.stopped.is_set():return
                self.wait_if_paused()
                if self.stopped.is_set():return
                doi_key=normalize_doi(work.get('doi'))
                paper_id=('doi:'+doi_key if doi_key else str(work.get('id') or ''))
                if not paper_id or paper_id in seen:return
                seen.add(paper_id)
                found+=1;processed+=1
                ok,confidence,why=paper_math_quality(work,theory)
                if not ok:
                    return
                accepted_papers+=1
                abstract=(work.get('_abstract_text') or
                    abstract_from_index(work.get('abstract_inverted_index')) or '')
                title=str(work.get('display_name') or '').strip()
                if not title:return
                source_id='paper:'+paper_id
                uri=str(work.get('doi') or work.get('id') or '')
                # The same paper may support multiple mathematical topics;
                # independent paper evidence still contributes at most one vote.
                with self.writer_lock:
                    previous=con.execute('SELECT LENGTH(abstract) FROM abc_sources WHERE id=?',
                                         (source_id,)).fetchone()
                with self.writer_lock:
                    depth=con.execute('SELECT read_level FROM flin_source_depth WHERE source_id=?',
                        (source_id,)).fetchone()
                # Previously reading only an abstract is NOT a reason to skip
                # later full-text extraction when the user enables PDF mode.
                already_pdf=bool(depth and depth[0]=='pdf_excerpt')
                fulltext=(obtain_pdf_text(session,work,fallback_pdf_url)
                          if self.read_pdf and not already_pdf else '')
                clusters=abc_extract_input_clusters(paper_id,title,abstract,fulltext,uri,
                                                     max_clusters=64)
                with self.writer_lock:
                    abc_register_source(con,source_id,'paper',title,uri,abstract,
                        work.get('publication_year'),work.get('cited_by_count') or 0,topic=theory)
                    outcome=abc_ingest_online_clusters(con,paper_id,title,abstract,fulltext,uri,
                                                       prepared_clusters=clusters)
                    flin_record_ingest_diagnostic(con,source_id,theory,outcome)
                    read_level='pdf_excerpt' if fulltext or already_pdf else 'abstract' if abstract else 'title_only'
                    con.execute('''INSERT INTO flin_source_depth(source_id,provider,read_level,text_chars)
                        VALUES(?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET
                        read_level=CASE WHEN flin_source_depth.read_level='pdf_excerpt'
                             THEN 'pdf_excerpt' ELSE excluded.read_level END,
                        text_chars=MAX(flin_source_depth.text_chars,excluded.text_chars),
                        provider=CASE WHEN flin_source_depth.provider='' THEN excluded.provider
                             ELSE flin_source_depth.provider END,
                        updated=CURRENT_TIMESTAMP''',
                        (source_id,work.get('_provider','academic-api'),read_level,
                         len(fulltext or abstract or '')))
                    con.commit()
                linked+=outcome['edges']
                new_memories+=outcome['promoted']
                new_input_clusters+=outcome['clusters']
                missing_math_inputs+=int(not outcome.get('extracted',0))
                if processed<=3 or processed%10==0:
                    self._send_worker(worker,theory,'Learning from research papers',processed,
                                      self.per_theory,0,linked)
                    self.out.put(('refresh',None))
            if references and self.use_wikipedia_references:
                self._send_worker(worker,theory,'Resolving cited papers',processed,self.per_theory)
                candidates=[r for r in references if r.get('status')=='found']
                # Keep a fair share for non-Wikipedia scholarly databases.
                reference_budget=(max(1,self.per_theory//3) if self.per_theory>1 else 0)
                try:
                    for ref,work in resolve_wikipedia_references(
                            session,candidates,self.api_key,self.stopped,
                            log=lambda msg:self.log(f'Worker {worker}, citation resolution: {msg}'),
                            limit=reference_budget,openalex_enabled=(
                                self.openalex_enabled and not self.openalex_unavailable.is_set()),
                            unavailable_event=self.openalex_unavailable,
                            arxiv_unavailable=self.arxiv_unavailable,
                            crossref_unavailable=self.crossref_unavailable):
                        if self.stopped.is_set() or processed>=reference_budget:break
                        if work:
                            try:accept_work(work,ref.get('url',''))
                            except Exception as exc:
                                failures+=1;self.log(f'Could not process cited work: {str(exc)[:180]}')
                except Exception as exc:
                    self.log(f'Warning: citation resolution incomplete; trying other research providers: {str(exc)[:210]}')
            if not self.references_only and not self.stopped.is_set() and processed<self.per_theory:
                self._send_worker(worker,theory,'Searching scholarly databases',processed,self.per_theory)
                def progress(page,total,emitted,batch):
                    self._send_worker(worker,theory,'Searching literature',processed,
                                      self.per_theory,page,linked)
                for score,work in stream_literature(session,theory,self.per_theory-processed,
                    self.api_key,self.stopped,self.pause_event,progress=progress,
                    on_retry=lambda msg:self.log(f'W{worker}: {msg}'),
                    openalex_enabled=self.openalex_enabled,
                    openalex_unavailable=self.openalex_unavailable,
                    arxiv_unavailable=self.arxiv_unavailable,
                    crossref_unavailable=self.crossref_unavailable):
                    if self.stopped.is_set() or processed>=self.per_theory:break
                    try:accept_work(work)
                    except Exception as exc:
                        failures+=1;self.log(f'Warning: paper extraction or FLIN learning failed: {str(exc)[:230]}')
                    if processed % 8 == 0:
                        with self.writer_lock,con:
                            con.execute('''UPDATE abc_topics SET found=?,processed=?,linked=?,
                                failures=?,updated=CURRENT_TIMESTAMP WHERE name=?''',
                                (found,processed,linked,failures,theory))
            if self.stopped.is_set():state='interrupted'
            elif failures:state='partial'
            elif processed==0 and not wiki_text:state='no_candidates'
            else:state='complete'
        except InterruptedError:
            state='interrupted'
        except OpenAlexSearchFailure as exc:
            state='skipped_search';failures+=1
            failure_detail=f'{exc.category}: {exc.reason[:280]}'
            self.log('Warning: FLIN literature search temporarily unavailable: '+failure_detail)
        except Exception as exc:
            state='error';failures+=1
            failure_detail=f'{phase}: {type(exc).__name__}: {str(exc)[:250]}'
            self.log('Error while building FLIN network: '+failure_detail)
        finally:
            with self.writer_lock,con:
                # Drain bounded replay queue, without rebuilding the old graph.
                if not self.stopped.is_set():
                    for _ in range(3):
                        if not abc_reconcile_pending(con,limit=350)['processed']:break
                con.execute('''UPDATE abc_topics SET state=?,found=?,processed=?,
                    linked=?,failures=?,message=?,updated=CURRENT_TIMESTAMP WHERE name=?''',
                    (state,found,processed,linked,failures,
                     (failure_detail or f'Processed {processed} source documents for FLIN')[:400],theory))
                con.commit()
            with self.counter_lock:
                self.completed+=1
                if state=='skipped_search':self.skipped_search+=1
                elif state=='complete':self.succeeded+=1
                elif state in ('no_candidates','off_topic'):self.no_candidates+=1
                elif state in ('error','partial'):self.failed+=1
                finished=self.completed
            self._send_worker(worker,theory,'Finished: '+state,processed,self.per_theory,0,linked)
            self.out.put(('theory_finished',
                         (worker,theory,state,processed,linked,finished)))
            self.out.put(('refresh',None))
            self.log(f'FLIN topic {theory}: {state}; {processed} papers considered; '
                     f'{accepted_papers} passed mathematics quality checks; '
                     f'{new_input_clusters} grounded input clusters; '
                     f'{new_memories} new active memories; {linked} directed-link updates; '
                     f'{missing_math_inputs} accepted papers without eligible mathematical input.')
            session.close();con.close()


    def _process_manual_topic(self, worker, original):
        """Resolve an explicit topic INSIDE its worker, then stream its papers.

        The producer never waits on Wikipedia for any manual topic. All manual
        topics resolve and build in parallel up to ``self.workers``. HTTP
        sessions are worker-local, and canonical aliases are claimed under a
        short lock before a worker opens the graph database.
        """
        self._send_worker(worker, original, 'Verifying Wikipedia topic')
        focused=mathematics_topic_focus(USER_TOPIC_ALIASES.get(original,original))
        self.log(f'Worker {worker}, mathematics topic: {original} -> {focused}')
        self.wait_if_paused()
        if self.stopped.is_set():
            return
        with requests.Session() as session:
            title, url = resolve_manual_topic(session, focused,
                              log=lambda msg: self.log(f'W{worker} {msg}'))
        self.wait_if_paused()
        if self.stopped.is_set():
            return
        canonical_key = unicodedata.normalize('NFKC', title).casefold().strip()
        with self.counter_lock:
            duplicate = canonical_key in self._manual_claimed
            if duplicate:
                self.completed += 1
                finished = self.completed
            else:
                self._manual_claimed.add(canonical_key)
        if duplicate:
            self.log(f'Worker {worker}: {original} resolves to an already queued topic ({title}); skipping duplicate.')
            self._send_worker(worker, original, 'Finished: duplicate')
            self.out.put(('theory_finished',
                          (worker, original, 'duplicate', 0, 0, finished)))
            return
        self.log(f'Worker {worker}, verified topic: {original} -> {title}' +
                 (' (Wikipedia)' if url else ' (direct literature search)'))
        self._process_theory(worker, title, url)

    def _worker_loop(self, worker):
        while True:
            try:
                job = self.jobs.get(timeout=.30)
            except queue.Empty:
                if self.stopped.is_set():
                    return
                continue
            try:
                if job is None:
                    return
                if self.stopped.is_set():
                    continue
                if isinstance(job, tuple) and len(job) == 2 and job[0] == 'manual_topic':
                    self._process_manual_topic(worker, job[1])
                else:
                    self._process_theory(worker, *job)
            except Exception as exc:
                self.log(f'Worker {worker}, unexpected error: {type(exc).__name__}: {exc}')
                # In normal flow _process_theory_abc persists exceptions itself.
                # This catches failures outside that handler (e.g. manual-topic
                # resolution) so no durable `running` job is orphaned.
                title = (str(job[1]) if isinstance(job,tuple) and
                         len(job)==2 and job[0]=='manual_topic'
                         else str(job[0]) if isinstance(job,tuple) and job else '')
                if title:
                    try:
                        with contextlib.closing(database()) as failure_con:
                            with failure_con:
                                failure_con.execute('''UPDATE abc_topics SET state='error',
                                    message=?,updated=CURRENT_TIMESTAMP WHERE name=?
                                    AND state='running' ''',
                                    (f'Worker failure: {type(exc).__name__}: {str(exc)[:270]}',title))
                                failure_con.execute("UPDATE flin_discovery_topics SET state='pending' WHERE name=?",
                                                    (title,))
                    except Exception as db_exc:
                        self.log(f'Cannot record worker failure: {str(db_exc)[:180]}')
            finally:
                self.jobs.task_done()
                self._send_worker(worker, '', 'Idle')

    def _purity_maintenance_loop(self):
        """Low-impact quality sweep concurrent with the build, not an API worker."""
        tick=0
        while not self._purity_maintenance_stop.is_set() and not self.stopped.is_set():
            try:
                if self.pause_event.is_set():
                    self._purity_maintenance_stop.wait(1.0)
                    continue
                tick+=1
                with self.writer_lock:
                    with database() as con:
                        result=purge_trivial_legacy_units_batch(con,limit=800)
                        if result['deleted'] or tick==1 or tick%5==0:
                            overview=purity_report(con)
                        else:overview=None
                if overview:
                    self.out.put(('purity_progress',overview))
                if result['completed']:
                    # Scan tail again later for newly created nodes.
                    self._purity_maintenance_stop.wait(12)
                else:
                    self._purity_maintenance_stop.wait(1.2)
            except Exception as exc:
                self.log('Warning: memory-quality maintenance paused: '+str(exc)[:180])
                self._purity_maintenance_stop.wait(8)

    def _retry_saved_incomplete_topics(self):
        """Repair a bounded number of failed/abandoned topics after workers drain.

        Each topic gets at most _retry_limit requeues in one build session. The
        retry set stays in SQLite on a permanent source failure; no hot loop.
        """
        if self.stopped.is_set():
            return 0, 0
        with contextlib.closing(database()) as con:
            # All queue jobs have finished. Repair work left claimed by a dead
            # worker; archive topics that really have final successful status.
            with con:
                con.execute("""UPDATE abc_topics SET state='interrupted',
                    message='Recovered abandoned topic after worker completion'
                    WHERE state='running' AND name IN
                    (SELECT name FROM flin_discovery_topics WHERE state='claimed')""")
                con.execute("""UPDATE flin_discovery_topics SET state='archived'
                    WHERE state='claimed' AND EXISTS
                    (SELECT 1 FROM abc_topics a WHERE a.name=flin_discovery_topics.name
                     AND a.state IN ('complete','no_candidates','off_topic'))""")
            rows=con.execute("""SELECT name FROM abc_topics WHERE state IN
                ('interrupted','partial','error','skipped_search') ORDER BY updated,name
                LIMIT 2000""").fetchall()
            orphaned=con.execute("""SELECT f.name FROM flin_discovery_topics f
                WHERE f.state='claimed' AND NOT EXISTS
                (SELECT 1 FROM abc_topics a WHERE a.name=f.name)""").fetchall()
            candidate_names=list(dict.fromkeys([r[0] for r in rows]+[r[0] for r in orphaned]))
            retry=[name for name in candidate_names if self._retry_attempts[name]<self._retry_limit]
            if retry:
                with con:
                    for name in retry:
                        self._retry_attempts[name]+=1
                        con.execute("""INSERT OR IGNORE INTO flin_discovery_topics
                            (name,url,origin) SELECT name,COALESCE(url,''),'auto_recovery'
                            FROM abc_topics WHERE name=?""",(name,))
                        con.execute("UPDATE flin_discovery_topics SET state='pending' WHERE name=?",(name,))
                    flin_clear_verified_frontier(con)
        return len(retry),len(candidate_names)

    def _retry_failed_categories(self):
        if self.stopped.is_set():return 0,0
        with contextlib.closing(database()) as con:
            rows=[r[0] for r in con.execute("SELECT name FROM flin_discovery_categories WHERE state='error'")]
            retry=[name for name in rows if self._retry_attempts['category:'+name]<self._retry_limit]
            if retry:
                with con:
                    for name in retry:
                        self._retry_attempts['category:'+name]+=1
                        con.execute("UPDATE flin_discovery_categories SET state='pending' WHERE name=?",(name,))
                    flin_clear_verified_frontier(con)
        return len(retry),len(rows)

    def _wait_before_recovery(self, attempt):
        delay=min(300,self._retry_wait*max(1,attempt))
        self._set_phase('recovery_wait',delay)
        self.log(f'Temporary source/build failure; automatic retry in {delay}s. '
                 'Existing memory is saved and collection will resume.')
        until=time.monotonic()+delay
        while not self.stopped.is_set() and time.monotonic()<until:
            self.wait_if_paused()
            self.stopped.wait(min(.3,until-time.monotonic()))


    def run(self):
        """Queue each theory immediately when discovered; never wait for N titles."""
        pool = []
        try:
            self._set_phase('starting')
            # Linux threads inherit their creator's affinity.  This affects
            # collector/worker threads only, not Tk or Ollama (another process).
            constrain_collector_cpu_affinity(self.cpu_budget, self.log)
            # API quota is not a reason to discard the Wikipedia theory queue.
            # Check alternatives independently. Do not bypass provider limits.
            session=requests.Session()
            source_ready=True  # arXiv public API needs no account / preflight.
            self.log('Research providers: arXiv, Crossref, OpenAIRE, DBLP (computer science), '
                     'Europe PMC (biomedical). OpenAlex is optional. Provider rate limits apply; availability is not guaranteed.')
            if os.environ.get('SEMANTIC_SCHOLAR_API_KEY','').strip():
                self.log('Semantic Scholar API key detected; Semantic Scholar enabled for this session.')
            else:self.log('Semantic Scholar API key not configured; continuing with other available providers.')
            if local_catalog_available():
                self.log(f'Local literature catalog: {local_catalog_count():,} indexed papers.')
            if self.openalex_enabled:
                try:
                    openalex_preflight(session,self.api_key,self.stopped,
                           on_retry=lambda msg:self.log('OpenAlex connectivity check: '+msg))
                    self.log('OpenAlex enabled and connectivity check passed.')
                except (OpenAlexSearchFailure,requests.RequestException,ValueError) as exc:
                    self.openalex_enabled=False
                    self.openalex_unavailable.set()
                    self.log('Warning: OpenAlex unavailable; disabled for this session. arXiv and Crossref remain active: '+str(exc)[:200])
            else:
                self.log('OpenAlex disabled; the network can be built without an OpenAlex API key or account.')
            session.close()
            # Recover older accepted abstracts without rediscovering the topics.
            # Bounded work prevents a massive old network from blocking startup.
            try:
                with contextlib.closing(database()) as restore_con:
                    recovered=flin_backfill_cached_abstracts(restore_con,limit=100)
                if recovered['scanned']:
                    self.log('Cached source recovery: '
                             f"{recovered['scanned']} inspected, "
                             f"{recovered['active']} new active memories, "
                             f"{recovered['edges']} association updates; "
                             f"{recovered['failed']} source errors.")
            except Exception as exc:
                self.log('Warning: cached-source recovery postponed: '+str(exc)[:220])
            for i in range(1, self.workers+1):
                thread = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
                thread.start()
                pool.append(thread)
            # ABC-only builds NEVER sweep, create, backfill or delete old graph nodes.
            self._purity_maintenance_stop=threading.Event()
            self._purity_maintenance_thread=None
            session = requests.Session()
            if not (self.retry_failed_only or self.references_only or self.manual_topics):
                # Retry old API failures ONCE at the start, not after each probe.
                with database() as retry_con, retry_con:
                    retry_con.execute("UPDATE flin_discovery_categories SET state='pending' WHERE state='error'")
            self.log(f'Starting {self.workers} parallel workers for mathematical literature discovery and FLIN learning.')
            self.out.put(('discovery', 'Streaming Wikipedia discovery; confirmed topics are queued immediately.'))

            def on_found(title, url, idx):
                # Name-based, durable frontier; no offset or positional skip.
                if self.enqueued >= self.count or self.stopped.is_set():
                    return False
                if self._put_job((title, url)):
                    self.enqueued += 1
                    self.out.put(('discovered', (self.enqueued,self.count,title,
                                                self.jobs.qsize())))
                    if self.enqueued <= 5 or self.enqueued % 20 == 0:
                        self.log(f'Queued topic {self.enqueued}: {title}')
                    return True
                return False

            try:
                if self.references_only:
                    with database() as con:
                        targets=con.execute("""SELECT name,url FROM abc_topics
                            WHERE url LIKE 'https://en.wikipedia.org/wiki/%'
                            ORDER BY updated,name LIMIT ?""",(self.count,)).fetchall()
                    self.log(f'Rescanning Wikipedia citations for {len(targets)} stored topics; standard topic discovery is skipped.')
                    self.out.put(('discovery',f'Rescanning Wikipedia citations for {len(targets)} stored topics.'))
                    for title,url in targets:
                        if self.stopped.is_set():break
                        on_found(title,url,self.start_offset)
                elif self.retry_failed_only:
                    with database() as con:
                        targets = con.execute("""SELECT name,url FROM abc_topics
                            WHERE state IN ('skipped_search','error','interrupted','partial')
                            ORDER BY updated,name LIMIT ?""",(self.count,)).fetchall()
                    self.log(f'Retrying {len(targets)} previously incomplete topics from SQLite; no Wikipedia rediscovery.')
                    self.out.put(('discovery',f'Retrying {len(targets)} previously failed topics.'))
                    for title,url in targets:
                        if self.stopped.is_set():break
                        on_found(title,url,self.start_offset)
                elif self.manual_topics:
                    self.out.put(('discovery',
                        f'Building {len(self.manual_topics)} selected topics using '
                        f'{min(self.workers, len(self.manual_topics))} concurrent workers. '
                        'Each worker independently verifies topics and retrieves literature.'))
                    # Queue raw inputs immediately. Previously the producer
                    # resolved every Wikipedia title sequentially before
                    # enqueueing, preventing true end-to-end concurrency.
                    for original in self.manual_topics:
                        if self.stopped.is_set():
                            break
                        if self._put_job(('manual_topic', original)):
                            self.enqueued += 1
                            self.out.put(('discovered',
                                (self.enqueued, self.count, original,
                                 self.jobs.qsize())))
                            self.log(f'Queued selected topic {self.enqueued}/{self.count}: {original}')
                    self.log(f'Queued {self.enqueued}/{len(self.manual_topics)} selected topics. '
                             f'Up to {self.workers} workers can verify, search, extract, and learn concurrently.')
                else:
                    # Continuous discovery must wait for in-flight literature workers
                    # to create new FLIN memories before calling the frontier exhausted.
                    idle_seconds=max(20,min(86400,int(os.environ.get('FLIN_IDLE_RETRY_SECONDS','60'))))
                    while not self.stopped.is_set():
                        self._set_phase('discovering')
                        with contextlib.closing(database()) as frontier_con:
                            self.discovery_outcome,self.discovery_stats=flin_stream_discovery(
                                frontier_con,session,self.count-self.enqueued,self.stopped,on_found,
                                log=self.log,wait_if_paused=self.wait_if_paused)
                        detail=self.discovery_stats
                        self.log(f'FLIN discovery phase: {self.discovery_outcome}; '
                                 f'{self.enqueued} topics queued in total; '
                                 f'{detail.get("pages",0)} Wikipedia category pages checked; '
                                 f'{detail.get("page_errors",0)} temporarily failed category pages.')
                        if not self.continuous or self.discovery_outcome in ('batch_limit','stopped'):
                            break
                        # The discovery producer may temporarily reach the end
                        # while worker threads are still extracting new units.
                        waiting=self.jobs.unfinished_tasks
                        if waiting:
                            self._set_phase('waiting_workers', waiting)
                            self.out.put(('discovery',
                                f'Waiting for {waiting} queued topics to finish learning before expanding discovery.'))
                            last_report = 0.0
                            while self.jobs.unfinished_tasks and not self.stopped.is_set():
                                self.wait_if_paused()
                                # Replace a worker that exited unexpectedly (not one
                                # still making an API request). Never kill live threads
                                # or run the same SQLite writer job twice.
                                for ix, thread in enumerate(pool):
                                    if not thread.is_alive() and not self.stopped.is_set():
                                        replacement=threading.Thread(target=self._worker_loop,
                                            args=(ix+1,),daemon=True,name=f'FLIN-Recovered-{ix+1}')
                                        replacement.start()
                                        pool[ix]=replacement
                                        self.log(f'Restarted unexpectedly exited literature worker {ix+1}.')
                                now = time.monotonic()
                                if now - last_report > 10.0:
                                    remaining_jobs = self.jobs.unfinished_tasks
                                    self.out.put(('collector_waiting',remaining_jobs))
                                    last_report = now
                                self.stopped.wait(.45)
                        if self.stopped.is_set():break
                        with contextlib.closing(database()) as con:
                            added,scanned=flin_expand_memory_topics(con,limit=8000)
                            pending=con.execute("SELECT COUNT(*) FROM flin_discovery_topics WHERE state='pending'").fetchone()[0]
                            if added:self.log(f'Expanded discovery with {added} source-grounded topics from new memory units.')
                        if pending or scanned:
                            continue
                        # Do not mark the source frontier complete while old
                        # accepted abstracts are still waiting to be converted
                        # into grounded, triggerable FLIN memories. Keep work
                        # bounded to 100 sources per idle pass; newly formed
                        # active units may themselves seed more discovery.
                        with self.writer_lock, contextlib.closing(database()) as recovery_con:
                            recovered=flin_backfill_cached_abstracts(recovery_con,limit=100)
                        if recovered['scanned']:
                            self.log('Cached learning catch-up: '
                                     f"{recovered['scanned']} saved sources, "
                                     f"{recovered['active']} new memories, "
                                     f"{recovered['edges']} association updates.")
                            self.out.put(('refresh',None))
                            continue
                        # No discovered work remains THIS PASS. Distinguish a
                        # genuinely drained source frontier from failed work.
                        # Repair/requeue failed workers/categories at most N times.
                        retry_topics,failed_topics=self._retry_saved_incomplete_topics()
                        retry_cats,failed_cats=self._retry_failed_categories()
                        if retry_topics or retry_cats:
                            self.out.put(('discovery',
                                f'Auto recovery: requeued {retry_topics} unfinished topics and '
                                f'{retry_cats} failed category pages. Saved data is intact.'))
                            self._wait_before_recovery(max(self._retry_attempts.values(),default=1))
                            continue
                        with contextlib.closing(database()) as health_con:
                            health=flin_frontier_health(health_con,
                                workers_pending=self.jobs.unfinished_tasks)
                        if health['complete'] and self.discovery_outcome=='frontier_idle':
                            self.discovery_outcome='source_frontier_exhausted'
                            self._verified_frontier=True
                            self.log('Current indexed literature frontier fully processed; '
                                     'not a claim that all mathematical knowledge is complete.')
                            break
                        # Some sources have failed repeatedly. Do not silently
                        # idle for 900 s or label this a complete trained network.
                        if failed_topics or failed_cats or health['unresolved']:
                            self.discovery_outcome='retry_exhausted'
                            self._auto_repair_status=(f'{failed_topics} incomplete topics, '
                                 f'{failed_cats} failed categories; status: {health}')[:550]
                            self.log('Automatic recovery reached its retry limit. '
                                     'The source frontier is NOT complete. '
                                     +self._auto_repair_status)
                            break
                        self.discovery_outcome='idle_wait'
                        self.wake_discovery.clear()
                        self.idle_until=time.monotonic()+idle_seconds
                        self._set_phase('idle', idle_seconds)
                        self.out.put(('discovery',
                            f'Provider cooldown: checking again within {idle_seconds} seconds. You can select Explore Now.'))
                        self.log(f'No new topics are available from the current discovery queue; '
                                 f'this does not establish mathematical completeness. '
                                 f'Provider cooldown: {idle_seconds} seconds; manual retry is available.')
                        while not self.stopped.is_set():
                            self.wait_if_paused()
                            if self.wake_discovery.is_set():
                                self.wake_discovery.clear()
                                self.log('Manual request received: recheck discovery providers immediately.')
                                break
                            remaining=self.idle_until-time.monotonic()
                            if remaining<=0:break
                            self.stopped.wait(min(0.5,remaining))
                        self.idle_until=0.0
                        if self.stopped.is_set():break
                        self._set_phase('discovering')
                        # Retry pending classification API failures after the
                        # cooldown; completed subjects refresh once per week.
                        with contextlib.closing(database()) as con,con:
                            con.execute("UPDATE flin_discovery_categories SET state='pending' WHERE state='error'")
                            con.execute('''UPDATE abc_topics SET state='refresh_due'
                                WHERE state='complete' AND updated < datetime('now','-7 days')
                                AND EXISTS(SELECT 1 FROM flin_discovery_topics f WHERE f.name=abc_topics.name)''')
                            con.execute('''UPDATE flin_discovery_topics SET state='pending'
                                WHERE state='archived' AND EXISTS(
                                  SELECT 1 FROM abc_topics a WHERE a.name=flin_discovery_topics.name
                                  AND a.state='refresh_due')''')
                        self.out.put(('discovery','Resuming multi-provider literature discovery after cooldown.'))
            except Exception as exc:
                self.log(f'Could not populate the discovery queue: {type(exc).__name__}: {exc}')
                if not self.enqueued:
                    self.out.put(('done','error'))
                    self.stopped.set()
                    return
            finally:
                session.close()
            # On stop, drop waiting jobs and let in-flight workers finish safely.
            if self.stopped.is_set():
                while True:
                    try:
                        self.jobs.get_nowait()
                        self.jobs.task_done()
                    except queue.Empty:
                        break
            for _ in pool:
                # If not stopped, enough worker capacity eventually becomes free.
                while True:
                    try:
                        self.jobs.put(None, timeout=.30)
                        break
                    except queue.Full:
                        if self.stopped.is_set():
                            continue
            for thread in pool:
                thread.join()
            if self._verified_frontier and not self.stopped.is_set():
                with contextlib.closing(database()) as done_con:
                    verification=flin_frontier_health(done_con,
                        workers_pending=self.jobs.unfinished_tasks)
                    if verification['complete']:
                        flin_store_verified_frontier(done_con,verification)
                    else:
                        self._verified_frontier=False
                        self._auto_repair_status=str(verification)[:450]
            result = ('service_error' if self.block_reason else
                      'stopped' if self.stopped.is_set() else
                      'source_frontier_exhausted' if self._verified_frontier else
                      'partial' if self.failed else
                      'complete_skipped' if self.skipped_search else
                      'discovery_limited' if self.discovery_outcome=='source_limited' else
                      'retry_exhausted' if self.discovery_outcome=='retry_exhausted' else
                      'frontier_idle' if self.discovery_outcome=='frontier_idle' else
                      'batch_limit' if self.discovery_outcome=='batch_limit' else 'complete')
            self.out.put(('done',result))
            self.log(f'Build summary: {self.enqueued} topics queued; {self.completed} processed; '
                     f'{self.succeeded} completed successfully; {self.no_candidates} without accepted sources; '
                     f'{self.skipped_search} provider searches failed; {self.failed} incomplete or failed. Data saved.')
        except Exception as exc:
            self.log(f'Collection system error: {type(exc).__name__}: {exc}')
            self.log(traceback.format_exc(limit=3))
            self.stopped.set()
            self.out.put(('done','error'))
        finally:
            self.phase='finished'
            self.idle_until=0.0
            stop=getattr(self,'_purity_maintenance_stop',None)
            if stop is not None:stop.set()
            cleanup=getattr(self,'_purity_maintenance_thread',None)
            if cleanup is not None:cleanup.join(timeout=4.0)
            # FLIN-only collection must not modify historical literature graph.
            self.out.put(('refresh',None))


def reactivate_math_network(seeds, query, relation_limit=55):
    """Reawaken a bounded, sourced subnetwork instead of using path endpoints.

    All returned evidence refers to persisted relation memories. Co-occurrence
    routes may be shown separately but never enter mathematical claim evidence.
    """
    context={'query':query,'matched':[], 'concepts':[], 'relations':[],
             'sources':[], 'warnings':[]}
    with database() as con:
        context['matched']=[{'id':uid,'label':label,'input':phrase,'match_score':round(float(score),2)}
                            for uid,label,phrase,score in seeds[:24]]
        if not seeds:
            context['warnings'].append(' No match to any what Memory unit .')
            return context
        # We use a bounded directed evidence traversal. Retrieval is allowed
        # to use explicit source-reference edges, which remain independent of
        # asserted mathematical implications.
        front={uid for uid,_,_,_ in seeds[:20]}
        traversed=set(front)
        relation_hits=set(uid for uid in front if uid.startswith('relation:'))
        for step in range(4):
            if not front:break
            newly=set()
            # Bounded per-node fan-out prevents popular paper hubs taking over.
            for uid in list(front)[:180]:
                if uid.startswith('relation:'):
                    relation_hits.add(uid)
                rows=con.execute("""SELECT dst,kind,weight FROM edges
                                    WHERE src=? AND kind IN
                                    ('concept-relation','source-relation',
                                     'relation-object','concept-paper-source',
                                     'concept-theory-source','paper-concept',
                                     'theory-paper') ORDER BY CASE WHEN kind IN ('concept-relation','source-relation') THEN 0 ELSE 1 END, weight DESC LIMIT 14""",
                                 (uid,)).fetchall()
                for target,kind,weight in rows:
                    if target.startswith('relation:'):relation_hits.add(target)
                    if target not in traversed:
                        newly.add(target)
            if len(traversed)>650:break
            front=set(list(newly)[:210]);traversed.update(front)
        if not relation_hits:
            context['warnings'].append(' There are currently no can activation ` contains Source research Relation Memory Unit `; existing Co-occurrence Link Cannot misrepresent inference .')
            return context
        seedids=set(uid for uid,_,_,_ in seeds[:20])
        seedtokens=set().union(*(set(lexical_tokens(label)) for _,label,_,_ in seeds[:15]))
        records=[]
        reverse_index = bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='index' "
                                         "AND name='idx_edges_dst'").fetchone())
        if not reverse_index:
            context['warnings'].append(' The reverse-edge index has not been built : relationship main term can may be missing ; can offline run  --build-fast-index.')
        # A large calculus neighborhood must not evict direct relations of
        # finance/linear algebra through arbitrary set ordering.
        directly_recalled=set()
        for uid in list(seedids):
            for (rid,) in con.execute("SELECT dst FROM edges WHERE src=? "
                                     "AND kind='concept-relation' LIMIT 32",(uid,)):
                directly_recalled.add(rid)
        ordered_relids=(sorted(directly_recalled)+
                        sorted(relation_hits-directly_recalled))[:420]
        for relid in ordered_relids:
            row=con.execute("SELECT label,description,support FROM units WHERE id=? AND kind='relation'",
                            (relid,)).fetchone()
            if row is None:continue
            label,description,support=row
            # Legacy relations may have connected unrelated educational / lab
            # words. Only admit a claim if BOTH endpoints are math concepts.
            if any(p in (label or '') for p in (' — relates to ', ' — used for ')):
                continue
            label_parts=re.split(r'\s*[—→]\s*',label or '')
            if len(label_parts)<3 or not (
                    math_concept_quality(label_parts[0])[0] and
                    math_concept_quality(label_parts[-1])[0]):
                continue
            quotes=con.execute("""SELECT source_id,sentence,source_url FROM relation_evidence
                                WHERE relation_id=? ORDER BY rowid DESC LIMIT 3""",(relid,)).fetchall()
            if not quotes:continue
            links=(con.execute("SELECT src FROM edges WHERE dst=? AND kind='concept-relation' LIMIT 3",
                               (relid,)).fetchall() if reverse_index else [])
            objects=con.execute("SELECT dst FROM edges WHERE src=? AND kind='relation-object' LIMIT 3",
                                (relid,)).fetchall()
            a=[v[0] for v in links];b=[v[0] for v in objects]
            toks=set(lexical_tokens(label))
            score=(8 if set(a+b)&seedids else 0)+3*len(toks&seedtokens)+min(2,math.log1p(support or 0))
            records.append((score,relid,label,a,b,quotes))
        records.sort(reverse=True,key=lambda x:x[0])
        # Round-robin source-backed mathematical statements per user topic.
        # This is independent from the left-hand path balancing: otherwise
        # the question-generation prompt could still be calculus-only.
        per_topic={}
        topic_order=list(dict.fromkeys(phrase for _,_,phrase,_ in seeds))
        for term in topic_order:
            ids={uid for uid,_,p,_ in seeds if p==term}
            toks=set().union(*(set(lexical_tokens(lb)) for uid,lb,p,_ in seeds if p==term))
            group=[]
            for record in records:
                _,rid,claim,parents,children,_quotes=record
                hit=len(ids.intersection(parents+children))
                overlap=len(set(lexical_tokens(claim))&toks)
                if hit or overlap:
                    group.append((hit*10+overlap*2+record[0],record))
            group.sort(key=lambda v:(-v[0],v[1][1]))
            per_topic[term]=[v[1] for v in group]
        chosen=[];visited=set()
        for step in range(relation_limit):
            changed=False
            for term in topic_order:
                pool=per_topic.get(term,[])
                for item in pool:
                    if item[1] not in visited:
                        chosen.append(item);visited.add(item[1]);changed=True
                        break
                if len(chosen)>=relation_limit:break
            if len(chosen)>=relation_limit or not changed:break
        if len(chosen)<relation_limit:
            for item in records:
                if item[1] not in visited:
                    chosen.append(item);visited.add(item[1])
                if len(chosen)>=relation_limit:break
        used_sources={};concept_ids=set(seedids)
        for i,(_,rid,label,parents,children,quotes) in enumerate(chosen,1):
            evidence=[]
            for source_id,sentence,url in quotes:
                evidence.append({'source_id':source_id,'quote':sentence,'url':url})
                if source_id not in used_sources:
                    source=con.execute('SELECT label,url FROM units WHERE id=?',(source_id,)).fetchone()
                    used_sources[source_id]={'id':source_id,'title':source[0] if source else source_id,
                                             'url':source[1] if source else url}
            context['relations'].append({'ref':f'R{i}','id':rid,'claim_label':label,
                                         'subject_ids':parents,'object_ids':children,
                                         'evidence':evidence})
            concept_ids.update(parents+children)
        for i in list(concept_ids)[:170]:
            if not i.startswith('concept:'):continue
            row=con.execute('SELECT label,description FROM units WHERE id=?',(i,)).fetchone()
            if row:
                context['concepts'].append({'id':i,'term':row[0],
                                            'source_excerpt':(row[1] or '')[:350]})
        context['sources']=list(used_sources.values())[:100]
        if len(records)>relation_limit:
            context['warnings'].append(' already truncate local Network high related relationship , its they relationship still save in Database .')
        context['warnings'].append(' rules extraction research relationship still is ` Candidate statement `, Cannot obtain generation Check original Paper .')
    return context


def evidence_only_report(context, paths=()):
    """Honest non-LLM output: no generic pretend-math problem templates."""
    lines=[' already activation concept Memory unit and relationship Evidence ( Not yet use languageModel)',
           ' input :'+str(context.get('query','')),
           f" match Node  {len(context.get('matched',[]))}  items ; research relationship  {len(context.get('relations',[]))}  items ; Source  {len(context.get('sources',[]))}  items .",
           '']
    if not context.get('relations'):
        lines+=[' Current missing Traceable research relationship , Cannot responsibly automatic assemble Research question .',
                ' please click ` reconstruct research Relation Memory Unit ` scan existing abstract , or Collect includes research statement more multiple Paper .','']
    else:
        lines+=[' activation relationship and its Source ( excerpts ):']
        for rel in context['relations'][:24]:
            ev=rel['evidence'][0]
            lines.extend([f"{rel['ref']}  {rel['claim_label']}",
                          f"     original passage :{ev['quote'][:290]}",
                          f"     Literature :{ev['source_id']}"])
    lines+=['','Use Related Concepts to inspect further associative paths from these memories.']
    for warning in context.get('warnings',[]):lines.append(' Note :'+warning)
    return '\n'.join(lines)


def compact_recall(context, paths, max_chars=36000):
    """Actual local memory with provenance, never cherry-pick path endpoints."""
    facts={
        'query':context.get('query',''),
        'matched':context.get('matched',[])[:24],
        'concepts':context.get('concepts',[])[:140],
        'relations':context.get('relations',[])[:80],
        'sources':context.get('sources',[])[:95],
        'warnings':context.get('warnings',[]),
        'paths':[{'labels':p.get('labels',[])[:10],
                  'weights':p.get('weights',[])[:9]} for p in paths[:25]],
    }
    for r in facts['relations']:
        r['evidence']=[dict(source_id=e.get('source_id',''),
                            quote=str(e.get('quote',''))[:330],
                            url=e.get('url','')) for e in r.get('evidence',[])[:2]]
    while len(json.dumps(facts,ensure_ascii=False)) > max_chars:
        if len(facts['relations'])>8:facts['relations'].pop()
        elif len(facts['paths'])>5:facts['paths'].pop()
        elif len(facts['sources'])>15:facts['sources'].pop()
        elif len(facts['concepts'])>25:facts['concepts'].pop()
        else:break
    return facts



# ---------------------------------------------------------------------------
# ABC associative memory experiment (v13.1, web-derived input clusters)
# Strictly separate from the literature / provenance graph.  `abc_edges`
# mean learned *activation preference*, NOT mathematical truth or citations.
# Legacy units/edges remain untouched and continue powering old retrieval.
# ---------------------------------------------------------------------------
from bisect import bisect_left, bisect_right

ABC_DEFAULTS = {
    'pulse_hz': 18.0, 'input_duration': 2.0, 'edge_dt': 0.0001,
    'frequency_window': 0.25, 'frequency_threshold': 2.0,
    'max_revisits': 2, 'max_steps': 32, 'quiet_window': 0.40,
    'sample_count': 90, 'learning_rate': 0.22, 'max_weight': 10.0,
}


_ABC_SCHEMA_READY = set()

def abc_schema(con):
    """Create independent FLIN graph tables; never mutate the legacy graph."""
    with _DB_SCHEMA_LOCK:
        key = con.execute('PRAGMA database_list').fetchone()[2]
        if key in _ABC_SCHEMA_READY:
            return
        con.executescript('''
        CREATE TABLE IF NOT EXISTS abc_units(
          id TEXT PRIMARY KEY, label TEXT NOT NULL, definition TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'candidate', quality INTEGER NOT NULL,
          evidence_count INTEGER NOT NULL DEFAULT 0,
          created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS abc_units_status ON abc_units(status,id);
        CREATE INDEX IF NOT EXISTS abc_units_label ON abc_units(label COLLATE NOCASE);
        CREATE TABLE IF NOT EXISTS abc_evidence(
          unit_id TEXT NOT NULL, source_id TEXT NOT NULL,
          explanation TEXT NOT NULL, url TEXT NOT NULL DEFAULT '',
          PRIMARY KEY(unit_id,source_id)
        );
        CREATE INDEX IF NOT EXISTS abc_evidence_source ON abc_evidence(source_id);
        CREATE TABLE IF NOT EXISTS abc_edges(
          src TEXT NOT NULL, dst TEXT NOT NULL,
          weight REAL NOT NULL, observations INTEGER NOT NULL DEFAULT 1,
          PRIMARY KEY(src,dst)
        );
        CREATE INDEX IF NOT EXISTS abc_edges_src_weight ON abc_edges(src,weight DESC);
        CREATE INDEX IF NOT EXISTS abc_edges_dst ON abc_edges(dst);
        CREATE TABLE IF NOT EXISTS abc_ssrs(
          unit_id TEXT PRIMARY KEY,
          priority REAL NOT NULL DEFAULT 0, exposures INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS abc_learning_events(
          source_id TEXT PRIMARY KEY, gate_label TEXT NOT NULL,
          activated_json TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS abc_runs(
          id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT NOT NULL,
          settings_json TEXT NOT NULL, result_json TEXT NOT NULL,
          created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS abc_pulse_events(
          run_id INTEGER NOT NULL, gate TEXT NOT NULL,
          unit_id TEXT NOT NULL, time_s REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS abc_pulse_events_run ON abc_pulse_events(run_id,time_s);
        CREATE TABLE IF NOT EXISTS abc_feedback(
          run_id INTEGER NOT NULL, gate TEXT NOT NULL,
          end_unit TEXT NOT NULL, reason TEXT NOT NULL,
          time_s REAL NOT NULL
        );
        -- Original online input clusters, independent of the provenance graph.
        CREATE TABLE IF NOT EXISTS abc_input_clusters(
          id TEXT PRIMARY KEY, paper_id TEXT NOT NULL,
          quote TEXT NOT NULL, url TEXT NOT NULL DEFAULT '',
          feature_count INTEGER NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS abc_input_clusters_paper ON abc_input_clusters(paper_id);
        CREATE TABLE IF NOT EXISTS abc_cluster_features(
          cluster_id TEXT NOT NULL, unit_id TEXT NOT NULL,
          position REAL NOT NULL, PRIMARY KEY(cluster_id,unit_id)
        );
        CREATE INDEX IF NOT EXISTS abc_cluster_features_unit ON abc_cluster_features(unit_id,cluster_id);
        -- Each qualified input event may reinforce a particular directed link ONCE.
        CREATE TABLE IF NOT EXISTS abc_cluster_links(
          cluster_id TEXT NOT NULL, src TEXT NOT NULL, dst TEXT NOT NULL,
          PRIMARY KEY(cluster_id,src,dst)
        );
        CREATE TABLE IF NOT EXISTS abc_replay_queue(
          cluster_id TEXT PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS abc_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS flin_ingest_diagnostics(
          source_id TEXT NOT NULL, topic TEXT NOT NULL DEFAULT '',
          extracted_clusters INTEGER NOT NULL DEFAULT 0,
          new_clusters INTEGER NOT NULL DEFAULT 0,
          new_active_units INTEGER NOT NULL DEFAULT 0,
          edge_updates INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT '',
          updated TEXT DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(source_id,topic)
        );
        CREATE INDEX IF NOT EXISTS idx_flin_ingest_status
          ON flin_ingest_diagnostics(status,topic);
        CREATE TABLE IF NOT EXISTS abc_sources(
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
          url TEXT NOT NULL DEFAULT '', abstract TEXT NOT NULL DEFAULT '',
          year INTEGER, citations INTEGER NOT NULL DEFAULT 0,
          processed TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS flin_source_depth(
          source_id TEXT PRIMARY KEY, provider TEXT NOT NULL,
          read_level TEXT NOT NULL, text_chars INTEGER NOT NULL DEFAULT 0,
          updated TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS abc_source_topics(
          source_id TEXT NOT NULL, topic TEXT NOT NULL,
          PRIMARY KEY(source_id,topic)
        );
        CREATE INDEX IF NOT EXISTS idx_abc_source_topics ON abc_source_topics(topic,source_id);
        CREATE TABLE IF NOT EXISTS abc_topics(
          name TEXT PRIMARY KEY, url TEXT NOT NULL DEFAULT '',
          state TEXT NOT NULL DEFAULT 'running', found INTEGER NOT NULL DEFAULT 0,
          processed INTEGER NOT NULL DEFAULT 0, linked INTEGER NOT NULL DEFAULT 0,
          failures INTEGER NOT NULL DEFAULT 0, message TEXT NOT NULL DEFAULT '',
          updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS abc_positions(
          unit_id TEXT PRIMARY KEY,
          x REAL NOT NULL, y REAL NOT NULL, z REAL NOT NULL
        );
        -- Efficiency-aware, source-grounded composite/shortcut memory evidence.
        -- Members are ordered inputs, NOT a mathematical proof/implication.
        CREATE TABLE IF NOT EXISTS flin_patterns(
          id TEXT PRIMARY KEY,
          members_json TEXT NOT NULL,
          distinct_sources INTEGER NOT NULL DEFAULT 0,
          estimated_uses REAL NOT NULL DEFAULT 0,
          reconstruction_cost REAL NOT NULL DEFAULT 0,
          shortcut_cost REAL NOT NULL DEFAULT 0,
          net_savings REAL NOT NULL DEFAULT 0,
          state TEXT NOT NULL DEFAULT 'observing',
          shortcut_unit_id TEXT NOT NULL DEFAULT '',
          updated TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS flin_pattern_evidence(
          pattern_id TEXT NOT NULL,
          evidence_source TEXT NOT NULL,
          cluster_id TEXT NOT NULL,
          quote TEXT NOT NULL DEFAULT '',
          PRIMARY KEY(pattern_id,evidence_source)
        );
        CREATE INDEX IF NOT EXISTS idx_flin_pattern_source ON
          flin_pattern_evidence(evidence_source);
        CREATE TABLE IF NOT EXISTS flin_shortcut_members(
          shortcut_id TEXT NOT NULL,
          member_id TEXT NOT NULL,
          member_order INTEGER NOT NULL,
          PRIMARY KEY(shortcut_id,member_order)
        );
        CREATE INDEX IF NOT EXISTS idx_flin_shortcut_member ON
          flin_shortcut_members(member_id,shortcut_id);
        CREATE TABLE IF NOT EXISTS flin_cost_decisions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          event_id TEXT NOT NULL,
          unit_id TEXT NOT NULL DEFAULT '',
          kind TEXT NOT NULL,
          action TEXT NOT NULL,
          old_cost REAL NOT NULL,
          new_cost REAL NOT NULL,
          net_savings REAL NOT NULL,
          explanation TEXT NOT NULL,
          created TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(event_id,unit_id,kind)
        );
        CREATE INDEX IF NOT EXISTS idx_flin_cost_kind ON flin_cost_decisions(kind,action);

        -- v16: restartable, order-independent mathematical literature discovery.
        CREATE TABLE IF NOT EXISTS flin_discovery_categories(
          name TEXT PRIMARY KEY COLLATE NOCASE,
          depth INTEGER NOT NULL DEFAULT 0,
          continuation TEXT NOT NULL DEFAULT '{}',
          state TEXT NOT NULL DEFAULT 'pending',
          pages INTEGER NOT NULL DEFAULT 0,
          failures INTEGER NOT NULL DEFAULT 0,
          last_error TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS flin_discovery_categories_state
          ON flin_discovery_categories(state,depth,pages);
        CREATE TABLE IF NOT EXISTS flin_discovery_topics(
          name TEXT PRIMARY KEY COLLATE NOCASE,
          url TEXT NOT NULL DEFAULT '',
          state TEXT NOT NULL DEFAULT 'pending',
          origin TEXT NOT NULL DEFAULT 'wikipedia'
        );
        CREATE INDEX IF NOT EXISTS flin_discovery_topics_state
          ON flin_discovery_topics(state);
        CREATE TABLE IF NOT EXISTS flin_discovery_meta(
          key TEXT PRIMARY KEY,value TEXT NOT NULL
        );
        ''')
        # FLIN v15: migrate old candidates formed by a single grounded input.
        # One source can form a memory. Source count is NOT a firing gate.
        already=con.execute("SELECT value FROM abc_meta WHERE key='flin_first_input_active_v1'").fetchone()
        upgraded=0
        if not already:
            with con:
                upgraded=int(con.execute('''SELECT COUNT(*) FROM abc_units
                    WHERE status='candidate' AND quality>=75 AND evidence_count>=1
                    AND EXISTS(SELECT 1 FROM abc_evidence e WHERE e.unit_id=abc_units.id)''').fetchone()[0])
                if upgraded:
                    con.execute('''INSERT OR IGNORE INTO abc_replay_queue(cluster_id)
                        SELECT DISTINCT f.cluster_id FROM abc_cluster_features f
                        JOIN abc_units u ON u.id=f.unit_id
                        WHERE u.status='candidate' AND u.quality>=75 AND u.evidence_count>=1
                        AND EXISTS(SELECT 1 FROM abc_evidence e WHERE e.unit_id=u.id)''')
                    con.execute('''UPDATE abc_units SET status='active'
                        WHERE status='candidate' AND quality>=75 AND evidence_count>=1
                        AND EXISTS(SELECT 1 FROM abc_evidence e WHERE e.unit_id=abc_units.id)''')
                if con.execute('SELECT 1 FROM abc_units LIMIT 1').fetchone():
                    con.execute("INSERT OR REPLACE INTO abc_meta(key,value) VALUES('flin_first_input_active_v1','1')")
        _ABC_SCHEMA_READY.add(key)
    if upgraded:
        # Resume processing automatically; remaining clusters are handled by
        # subsequent collection batches or the explicit reconcile command.
        abc_reconcile_pending(con,limit=500)


def abc_enabled(con):
    row=con.execute("SELECT value FROM abc_meta WHERE key='enabled'").fetchone()
    return bool(row and row[0]=='1')


def abc_enable(con):
    abc_schema(con)
    con.execute("INSERT OR REPLACE INTO abc_meta(key,value) VALUES('enabled','1')")
    con.commit()


def abc_status(con):
    abc_schema(con)
    counts=dict(con.execute('SELECT status,COUNT(*) FROM abc_units GROUP BY status').fetchall())
    return {'enabled':abc_enabled(con), 'active':counts.get('active',0),
            'candidates':counts.get('candidate',0),
            'edges':con.execute('SELECT COUNT(*) FROM abc_edges').fetchone()[0],
            'shortcuts':con.execute("SELECT COUNT(*) FROM flin_patterns WHERE state='shortcut'").fetchone()[0],
            'learned_sources':con.execute('SELECT COUNT(*) FROM abc_sources').fetchone()[0],
            'topics':con.execute('SELECT COUNT(*) FROM abc_topics').fetchone()[0],
            'runs':con.execute('SELECT COUNT(*) FROM abc_runs').fetchone()[0],
            'input_clusters':con.execute('SELECT COUNT(*) FROM abc_input_clusters').fetchone()[0],
            'pending_replay':con.execute('SELECT COUNT(*) FROM abc_replay_queue').fetchone()[0]}


def abc_key(label):
    """No lemmatization, loose fuzzy matching, or aliases: Q3 requires equivalence proof."""
    v=unicodedata.normalize('NFKC',str(label or '')).casefold().strip()
    return re.sub(r'\s+',' ',v)


def abc_identifier(label):
    return 'abc:'+hashlib.sha256(abc_key(label).encode('utf-8')).hexdigest()[:24]


def abc_explanatory_evidence(text):
    """Conservative syntactic guard; NOT a proof of mathematical meaning."""
    if len(text or '')<40 or len(re.findall(r'[A-Za-z]+',str(text)))<7:
        return False
    return bool(re.search(r'\b(?:is|are|means|denotes|defined|definition|represents|'
                          r'describes|satisfies|characterized|maps|equation|'
                          r'operator|approximates|corresponds|characterizes)\b',
                          text,flags=re.IGNORECASE))


def flin_math_terms_from_source(sentence, extra=()):
    """Recognize *literal* source terms, including previously unseen math phrases.

    The structural-noun and mathematical-quality gates remain mandatory. Every
    returned phrase must occur in the quoted source span; this does NOT infer
    semantic identity or mathematical implication.
    """
    found=list(math_terms_in_sentence(sentence,extra))
    words=list(re.finditer(r"\b[A-Za-z][A-Za-z0-9-]*\b",sentence))
    # An unknown mathematical construct should not require prior membership in
    # the fixed MATH_ANCHORS lexicon. Inspect only short noun-headed phrases.
    for end,match in enumerate(words):
        if _lemma(match.group().casefold()) not in MATH_CONCEPT_HEADS:
            continue
        for size in (5,4,3,2):
            begin=end-size+1
            if begin<0:continue
            first=words[begin]; phrase=sentence[first.start():match.end()]
            label=canonical_phrase(phrase)
            if (len(label)>100 or not _pure_math_concept_quality(label)[0] or
                    score_math_unit_purity(label,'concept')[0]<75):
                continue
            found.append((first.start(),match.end(),label))
            break  # prefer the longest admissible, literally occurring name
    # Within one overlapping span, the longest qualified label is preferred.
    # Non-overlapping distinct concepts retain their source-text order.
    chosen=[]
    for a,b,label in sorted(found,key=lambda r:(-(r[1]-r[0]),r[0],r[2])):
        if any(a<y and x<b for x,y,_ in chosen):continue
        if abc_key(label) not in abc_key(sentence[a:b]):continue
        chosen.append((a,b,label))
    return sorted(chosen,key=lambda r:(r[0],r[1]))


def _flin_source_sentence_spans(text, minimum=28, maximum=500, cap=260):
    """Preserve offsets, so adjacent-statement clusters quote actual source text."""
    text=str(text or '')
    boundaries=[0]+[m.end() for m in SENTENCE_RE.finditer(text)]+[len(text)]
    spans=[]
    for a,b in zip(boundaries,boundaries[1:]):
        while a<b and text[a].isspace():a+=1
        while b>a and text[b-1].isspace():b-=1
        if minimum<=b-a<=maximum:
            spans.append((a,b,text[a:b]))
            if len(spans)>=cap:break
    return spans


def abc_extract_input_clusters(paper_id, title, abstract, fulltext='', url='', *, max_clusters=32):
    """Extract ordered, grounded inputs, prioritizing evidence for REAL links.

    A title may create individual memories, but title co-mention does not invent
    an association. Separate, immediately adjacent statements within the SAME
    abstract/full text are observable input order: bridge only the last qualified
    feature in the first sentence to the first in the next. Neither source
    similarity nor sharing a paper alone licenses a directed link.

    Prepare candidates BEFORE applying max_clusters: the older first-N-sentences
    cutoff commonly exhausted its budget on singleton memories, silently
    discarding the multi-feature inputs that can actually learn associations.
    """
    raw=' '.join(str(x or '') for x in (title,abstract,(fulltext or '')[:48000]))
    if not raw.strip():return []
    cap=max(1,int(max_clusters))
    extra=[name for name,_ in keyphrases(raw,str(title or ''),limit=24)]
    candidates=[]
    ordinal=0

    def submit(quote,base_index,kind,*,title_input=False,bridge=None,recognized_terms=None):
        nonlocal ordinal
        if not 28<=len(quote)<=1100:return
        if bridge is None:
            terms=(recognized_terms if recognized_terms is not None else
                   flin_math_terms_from_source(quote,extra))
            selected=[];seen_units=set()
            for first,last,label in terms:
                if label in seen_units:continue
                seen_units.add(label)
                selected.append({'label':label,'explanation':quote,'url':url,
                                 'position':float(base_index)+first/max(1,len(quote))})
        else:
            selected=[]
            for off,label in bridge:
                selected.append({'label':label,'explanation':quote,'url':url,
                                 'position':float(base_index)+off/max(1,len(quote))})
        if not selected:return
        if bridge is None and not title_input and len(selected)<2 and not abc_explanatory_evidence(quote):
            return
        if title_input and len(selected)>1:
            # Unlike an observed multi-feature statement, a paper title is only
            # metadata. Multiple title terms get distinct singleton clusters.
            sets=[[one] for one in selected]
        else:
            sets=[selected]
        for items in sets:
            if bridge is not None:
                fingerprint=hashlib.sha256((abc_key(quote)+'|adjacent-boundary|'+
                    '|'.join(abc_key(x['label']) for x in items)).encode('utf-8')).hexdigest()[:24]
            elif title_input and len(selected)>1:
                # Preserve historic title cluster IDs for idempotent backfill.
                fingerprint=hashlib.sha256((abc_key(quote)+'|title:'+
                    abc_key(items[0]['label'])).encode('utf-8')).hexdigest()[:24]
            else:
                fingerprint=hashlib.sha256(abc_key(quote).encode('utf-8')).hexdigest()[:24]
            cluster_id='online:'+hashlib.sha256((str(paper_id)+'|'+fingerprint).encode('utf-8')).hexdigest()[:32]
            # Keep title concepts, then prioritize same-sentence multi-feature
            # input and adjacent abstract boundaries over unrelated singletons.
            priority=(0 if title_input else
                      2 if kind=='abstract' and bridge is not None else
                      1 if kind=='abstract' and len(items)>=2 else
                      4 if kind=='fulltext' and bridge is not None else
                      3 if kind=='fulltext' and len(items)>=2 else
                      5 if kind=='abstract' else 6)
            candidates.append((priority,ordinal,cluster_id,quote,items))
            ordinal+=1

    sections=[('title',str(title or ''),1),
              ('abstract',str(abstract or ''),160),
              ('fulltext',str(fulltext or '')[:48000],260)]
    global_index=0
    for kind,source,maxparts in sections:
        if not source:continue
        sentences=_flin_source_sentence_spans(source,28,500,maxparts)
        recognized=[]
        for a,b,quote in sentences:
            terms=flin_math_terms_from_source(quote,extra)
            recognized.append((a,b,quote,terms))
            submit(quote,global_index,kind,title_input=(kind=='title'),
                   recognized_terms=terms)
            global_index+=1
        if kind in ('abstract','fulltext'):
            for (a,b,left,lterms),(c,d,right,rterms) in zip(recognized,recognized[1:]):
                # A valid sentence boundary within the SAME original source.
                # Never bridge titles, unrelated papers, or distant paragraphs.
                if c-b>8 or d-a>1050 or not lterms or not rterms:continue
                left_last=lterms[-1]
                right_first=rterms[0]
                if left_last[2]==right_first[2]:continue
                original_quote=source[a:d]
                # Only this observed boundary pair, not every possible pair
                # across a document, becomes an ordered SSRS input.
                submit(original_quote,global_index,kind,bridge=(
                    (left_last[0],left_last[2]),
                    (c-a+right_first[0],right_first[2])))
                global_index+=1

    result=[];seen=set()
    for _priority,_order,cid,quote,features in sorted(candidates,key=lambda x:(x[0],x[1])):
        if cid in seen:continue
        seen.add(cid)
        result.append({'id':cid,'paper_id':str(paper_id),
                       'quote':quote,'url':str(url or ''),'features':features})
        if len(result)>=cap:break
    return result


# ---------------------------------------------------------------------------
# FLIN efficiency-aware memory formation (experimental, auditable policy).
# Model parameters are NOT claims about neurological or mathematical truth.
# All shortcut paths come from real, ordered SSRS effective-input clusters.
# ---------------------------------------------------------------------------
FLIN_SHORTCUT_MIN_MEMBERS = 4  # three edges -> at most two shortcut edges
FLIN_SHORTCUT_MAX_MEMBERS = 6
FLIN_SHORTCUT_MIN_SOURCES = 3
FLIN_COST_PER_HOP = 1.0
FLIN_COST_FORMATION = 2.5
FLIN_COST_STORAGE = 0.8
FLIN_COST_INTERFERENCE = 0.6
FLIN_COST_MIN_NET_BENEFIT = 0.5


def flin_estimate_association_cost(path_length, distinct_sources):
    '''Compare reusing the observed path vs. a two-hop shortcut.

    Sources approximate future reuse opportunity; no semantic/embedding model.
    Values are adjustable engineering assumptions. Missing conceptual knowledge
    is never discarded because a cost estimator guesses it is redundant.
    '''
    n = max(0, int(path_length))
    sources = max(0, int(distinct_sources))
    expected_uses = float(sources) * (1.0 + math.log1p(sources))
    original = expected_uses * max(0, n - 1) * FLIN_COST_PER_HOP
    shortcut = (expected_uses * 2.0 * FLIN_COST_PER_HOP
                + FLIN_COST_FORMATION + FLIN_COST_STORAGE
                + FLIN_COST_INTERFERENCE)
    return {'expected_uses': round(expected_uses, 6),
            'reconstruction_cost': round(original, 6),
            'shortcut_cost': round(shortcut, 6),
            'net_savings': round(original - shortcut, 6)}


def flin_record_cost_decision(con, event_id, uid, kind, action, old_cost,
                              new_cost, explanation):
    con.execute('''INSERT OR IGNORE INTO flin_cost_decisions
        (event_id,unit_id,kind,action,old_cost,new_cost,net_savings,explanation)
        VALUES(?,?,?,?,?,?,?,?)''',
        (str(event_id),str(uid),str(kind),str(action),float(old_cost),
         float(new_cost),float(old_cost-new_cost),str(explanation)[:650]))


def flin_observe_ssrs_path(con, cluster_id, groups):
    '''Observe one complete ordered source cluster after the SSRS pass.

    Concurrency groups are not arbitrarily sorted into a fictitious sequence.
    Only consecutive, unique, active, primitive feature memories qualify.
    Each independent document counts once per identical member sequence.
    '''
    if len(groups) < FLIN_SHORTCUT_MIN_MEMBERS:
        return 0
    row=con.execute('SELECT paper_id,quote,url FROM abc_input_clusters WHERE id=?',
                    (cluster_id,)).fetchone()
    if not row or not row[0]:
        return 0
    paper_id,quote,url=row
    if any(len(g[1]) != 1 for g in groups):
        return 0  # Concurrent input is never converted into fake directed order.
    ordered=[g[1][0] for g in groups]
    if len(set(ordered))!=len(ordered):
        return 0  # This prototype does not compress cycles/repeated concepts.
    # Exclude shortcuts from the source path to prevent shortcuts of shortcuts.
    for i in ordered:
        status=con.execute('SELECT status FROM abc_units WHERE id=?',(i,)).fetchone()
        if not status or status[0]!='active' or i.startswith('flin:shortcut:'):
            return 0
    made=0
    for offset in range(len(ordered)):
        for length in range(FLIN_SHORTCUT_MIN_MEMBERS,
                            min(FLIN_SHORTCUT_MAX_MEMBERS,len(ordered)-offset)+1):
            members=ordered[offset:offset+length]
            fingerprint='|'.join(members)
            pid='flin:pattern:'+hashlib.sha256(fingerprint.encode()).hexdigest()[:32]
            con.execute('INSERT OR IGNORE INTO flin_patterns(id,members_json) VALUES(?,?)',
                        (pid,json.dumps(members)))
            cursor=con.execute('''INSERT OR IGNORE INTO flin_pattern_evidence
                (pattern_id,evidence_source,cluster_id,quote) VALUES(?,?,?,?)''',
                (pid,str(paper_id),str(cluster_id),str(quote)[:1000]))
            # Even repeated clusters from the same paper do not increase support.
            if cursor.rowcount!=1:continue
            count=con.execute('SELECT COUNT(*) FROM flin_pattern_evidence WHERE pattern_id=?',
                              (pid,)).fetchone()[0]
            cost=flin_estimate_association_cost(len(members),count)
            existing=con.execute('SELECT state FROM flin_patterns WHERE id=?',(pid,)).fetchone()[0]
            action=('create_shortcut' if count>=FLIN_SHORTCUT_MIN_SOURCES and
                    cost['net_savings']>FLIN_COST_MIN_NET_BENEFIT else 'reuse_existing')
            con.execute('''UPDATE flin_patterns SET distinct_sources=?,estimated_uses=?,
                reconstruction_cost=?,shortcut_cost=?,net_savings=?,updated=CURRENT_TIMESTAMP
                WHERE id=?''',(count,cost['expected_uses'],cost['reconstruction_cost'],
                     cost['shortcut_cost'],cost['net_savings'],pid))
            flin_record_cost_decision(con,cluster_id,pid,'composite',action,
                 cost['reconstruction_cost'],cost['shortcut_cost'],
                 'SSRS-observed ordered features; association hop savings estimate, '
                 'not a theorem or proven equivalence.')
            if existing=='shortcut':
                sid='flin:shortcut:'+pid.split(':')[-1]
                con.execute('UPDATE abc_units SET evidence_count=? WHERE id=?',(count,sid))
                con.execute('''INSERT OR IGNORE INTO abc_evidence
                    (unit_id,source_id,explanation,url) VALUES(?,?,?,?)''',
                    (sid,str(paper_id),str(quote)[:1300],str(url)[:600]))
                # Reinforce the shortcut only once per new independent source.
                for a,b in ((members[0],sid),(sid,members[-1])):
                    old=con.execute('SELECT weight FROM abc_edges WHERE src=? AND dst=?',
                                    (a,b)).fetchone()
                    if old:
                        nw=float(old[0])+.12*(10.-float(old[0]))
                        con.execute('UPDATE abc_edges SET weight=?,observations=observations+1 '
                                    'WHERE src=? AND dst=?',(min(10.,nw),a,b))
                continue
            if action!='create_shortcut':continue
            sid='flin:shortcut:'+pid.split(':')[-1]
            labels=[]
            for uid in members:
                label_row=con.execute('SELECT label FROM abc_units WHERE id=?',(uid,)).fetchone()
                labels.append(label_row[0] if label_row else uid)
            display='Shortcut: '+' -> '.join(labels)
            if len(display)>480:display=display[:477]+'...'
            explanation=('Reusable association pattern backed by '+str(count)+
                 ' independent documents. Members: '+' -> '.join(labels)+
                 '. Shortcut is an engineering optimization, not mathematical implication.')
            con.execute('''INSERT OR IGNORE INTO abc_units
                (id,label,definition,status,quality,evidence_count)
                VALUES(?,?,?,'active',85,?)''',(sid,display,explanation,count))
            con.execute('''INSERT OR IGNORE INTO abc_ssrs(unit_id,priority,exposures)
                VALUES(?,0,0)''',(sid,))
            con.executemany('''INSERT OR IGNORE INTO flin_shortcut_members
                (shortcut_id,member_id,member_order) VALUES(?,?,?)''',
                [(sid,uid,i) for i,uid in enumerate(members)])
            # Distinct path shape A -> shortcut -> Z uses two directed hops.
            # Leave A->B->...->Z unmodified. This is a routing preference,
            # not a mathematically typed relation or equality assertion.
            for src,dst in ((members[0],sid),(sid,members[-1])):
                con.execute('''INSERT OR IGNORE INTO abc_edges
                    (src,dst,weight,observations) VALUES(?,?,0.6,1)''',(src,dst))
            con.execute('''UPDATE flin_patterns SET state='shortcut',shortcut_unit_id=?,
                updated=CURRENT_TIMESTAMP WHERE id=?''',(sid,pid))
            # Preserve individual source quotations in the existing evidence view.
            for source,source_quote,source_cluster in con.execute('''
                SELECT evidence_source,quote,cluster_id FROM flin_pattern_evidence
                WHERE pattern_id=?''',(pid,)):
                source_url=con.execute('SELECT url FROM abc_input_clusters WHERE id=?',
                                       (source_cluster,)).fetchone()
                con.execute('''INSERT OR IGNORE INTO abc_evidence
                    (unit_id,source_id,explanation,url) VALUES(?,?,?,?)''',
                    (sid,str(source),str(source_quote),source_url[0] if source_url else ''))
            made+=1
    return made


def flin_retrofit_history(con, limit=1000):
    """Incrementally evaluate existing SSRS clusters without re-downloading papers.

    The persisted source order, per-unit SSRS priorities, and evidence identity
    are reused. Repeated calls are resumable; existing edges stay unchanged.
    """
    abc_schema(con)
    previous=con.execute("SELECT value FROM abc_meta WHERE key='flin_cost_retrofit_rowid'").fetchone()
    after=int(previous[0]) if previous else 0
    rows=con.execute('SELECT rowid,id FROM abc_input_clusters WHERE rowid>? '
                     'ORDER BY rowid LIMIT ?',(after,max(1,min(10000,int(limit))))).fetchall()
    shortcuts=0
    with con:
        for rowid,cid in rows:
            features=con.execute("""SELECT f.unit_id,f.position,COALESCE(s.priority,0.)
                FROM abc_cluster_features f
                JOIN abc_units u ON u.id=f.unit_id AND u.status='active'
                LEFT JOIN abc_ssrs s ON s.unit_id=f.unit_id
                WHERE f.cluster_id=?""",(cid,)).fetchall()
            ordered=sorted(((max(0.,float(position))-.1*float(priority),uid)
                            for uid,position,priority in features),key=lambda x:(x[0],x[1]))
            groups=[]
            for position,uid in ordered:
                if not groups or abs(groups[-1][0]-position)>1e-8:
                    groups.append((position,[uid]))
                else:groups[-1][1].append(uid)
            shortcuts+=flin_observe_ssrs_path(con,cid,groups)
        if rows:
            con.execute("INSERT OR REPLACE INTO abc_meta(key,value) "
                        "VALUES('flin_cost_retrofit_rowid',?)",(str(rows[-1][0]),))
    return {'processed':len(rows),'created_shortcuts':shortcuts,
            'remaining':con.execute('SELECT COUNT(*) FROM abc_input_clusters WHERE rowid>?',
                                    (rows[-1][0] if rows else after,)).fetchone()[0]}


def flin_efficiency_report(con):
    abc_schema(con)
    totals={name:con.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
            for name in ('flin_patterns','flin_shortcut_members','flin_cost_decisions')}
    counts=dict(con.execute('SELECT state,COUNT(*) FROM flin_patterns GROUP BY state'))
    shortcuts=con.execute('''SELECT p.id,p.distinct_sources,p.net_savings,
        u.label FROM flin_patterns p JOIN abc_units u ON u.id=p.shortcut_unit_id
        WHERE p.state='shortcut' ORDER BY p.net_savings DESC LIMIT 12''').fetchall()
    return {'patterns':totals['flin_patterns'],
            'observing':counts.get('observing',0),
            'shortcuts':counts.get('shortcut',0),
            'shortcut_members':totals['flin_shortcut_members'],
            'cost_decisions':totals['flin_cost_decisions'],
            'policy':'Source-grounded observed association shortcuts; costs are experimental.',
            'top_shortcuts':[{'id':a,'independent_sources':b,'net_savings':c,'label':d}
                             for a,b,c,d in shortcuts]}


def abc_reconcile_pending(con, limit=100, *, eta=.22, max_weight=10.):
    """Learn links from stored clusters after later evidence activates concepts.

    Input-event contribution is idempotent. A cluster is never counted twice,
    even if later sources promote more of its candidate features.
    """
    abc_schema(con)
    todo=[r[0] for r in con.execute('SELECT cluster_id FROM abc_replay_queue '
                                    'ORDER BY rowid LIMIT ?', (max(1,int(limit)),))]
    made=0; new_links=0; reinforcements=0
    with con:
        for cid in todo:
            rows=con.execute("""SELECT f.unit_id,f.position,COALESCE(s.priority,0.)
                FROM abc_cluster_features f
                JOIN abc_units u ON u.id=f.unit_id AND u.status='active'
                LEFT JOIN abc_ssrs s ON s.unit_id=f.unit_id
                WHERE f.cluster_id=?""",(cid,)).fetchall()
            ordered=sorted(((max(0.,float(pos))-.1*float(prio),uid)
                            for uid,pos,prio in rows),key=lambda x:(x[0],x[1]))
            groups=[]
            for position,uid in ordered:
                if not groups or abs(groups[-1][0]-position)>1e-8:
                    groups.append((position,[uid]))
                else:groups[-1][1].append(uid)
            for (_,left),(_,right) in zip(groups,groups[1:]):
                for src in left:
                    for dst in right:
                        if src==dst:continue
                        cursor=con.execute('INSERT OR IGNORE INTO abc_cluster_links(cluster_id,src,dst) '
                                           'VALUES(?,?,?)',(cid,src,dst))
                        if cursor.rowcount!=1:continue
                        row=con.execute('SELECT weight FROM abc_edges WHERE src=? AND dst=?',
                                        (src,dst)).fetchone()
                        if row: reinforcements+=1
                        else: new_links+=1
                        current=float(row[0]) if row else 1.
                        new=current+max(0.,min(1.,float(eta)))*(max_weight-current)
                        con.execute('INSERT INTO abc_edges(src,dst,weight,observations) '
                            'VALUES(?,?,?,1) ON CONFLICT(src,dst) DO UPDATE SET '
                            'weight=excluded.weight,observations=observations+1',
                            (src,dst,min(max_weight,new)))
                        made+=1
            # Observe cost of the real SSRS-derived path; shortcut formation is
            # separate from and never replaces the effective-input experience.
            flin_observe_ssrs_path(con,cid,groups)
            con.execute('DELETE FROM abc_replay_queue WHERE cluster_id=?',(cid,))
    return {'processed':len(todo),'edges':made,
            'new_links':new_links,'reinforcements':reinforcements}


def abc_register_source(con, source_id, kind, title, url='', abstract='', year=None,
                        citations=0, topic=''):
    '''Record evidence metadata without adding a paper/theory node to FLIN.''' 
    abc_schema(con)
    with con:
        con.execute('''INSERT INTO abc_sources(id,kind,title,url,abstract,year,citations)
            VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
            url=CASE WHEN excluded.url!='' THEN excluded.url ELSE abc_sources.url END,
            abstract=CASE WHEN length(excluded.abstract)>length(abc_sources.abstract)
                THEN excluded.abstract ELSE abc_sources.abstract END,
            citations=MAX(abc_sources.citations,excluded.citations)''',
            (str(source_id),str(kind),str(title)[:500],str(url or '')[:800],
             str(abstract or '')[:20000],year,max(0,int(citations or 0))))
        if topic:
            con.execute('INSERT OR IGNORE INTO abc_source_topics(source_id,topic) VALUES(?,?)',
                        (str(source_id),str(topic)))


def flin_record_ingest_diagnostic(con, source_id, topic, outcome):
    """Audit why a verified paper did or did not grow the association graph.

    For multiple passes, retain the maximum observed counts so a later replay
    cannot overwrite a successful initial learning event with zero duplicates.
    """
    extracted=int(outcome.get('extracted',outcome.get('clusters',0)))
    fresh=int(outcome.get('clusters',0))
    active=int(outcome.get('promoted',0))
    edges=int(outcome.get('edges',0))
    state=('no_grounded_math_input' if not extracted else
           'already_observed' if not fresh else
           'new_triggerable_memories' if active else
           'associations_updated' if edges else 'existing_memory_reobserved')
    con.execute("""INSERT INTO flin_ingest_diagnostics
        (source_id,topic,extracted_clusters,new_clusters,new_active_units,
         edge_updates,status) VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(source_id,topic) DO UPDATE SET
        extracted_clusters=MAX(extracted_clusters,excluded.extracted_clusters),
        new_clusters=MAX(new_clusters,excluded.new_clusters),
        new_active_units=MAX(new_active_units,excluded.new_active_units),
        edge_updates=MAX(edge_updates,excluded.edge_updates),
        status=CASE WHEN excluded.new_active_units>0 THEN excluded.status
          WHEN flin_ingest_diagnostics.new_active_units>0 THEN flin_ingest_diagnostics.status
          WHEN excluded.new_clusters>0 THEN excluded.status
          ELSE flin_ingest_diagnostics.status END,
        updated=CURRENT_TIMESTAMP""",
        (str(source_id),str(topic),extracted,fresh,active,edges,state))
    return state


def flin_backfill_cached_abstracts(con, limit=12):
    """Recover grounded FLIN inputs from previously saved source abstracts.

    This is a one-pass, restartable sweep over *already stored* sources. It
    does not fetch literature, alter the legacy graph, or duplicate input
    events and link reinforcement already stored in SQLite.
    """
    if not abc_enabled(con):
        return {'scanned':0,'clusters':0,'active':0,'edges':0,'failed':0}
    meta='flin_source_input_backfill_v3_rowid'
    current=con.execute('SELECT value FROM abc_meta WHERE key=?',(meta,)).fetchone()
    after=int(current[0]) if current else 0
    rows=con.execute("""SELECT rowid,id,kind,title,abstract,url FROM abc_sources
        WHERE rowid>? ORDER BY rowid LIMIT ?""",(after,max(1,min(200,int(limit))))).fetchall()
    totals={'scanned':0,'clusters':0,'active':0,'edges':0,'failed':0}
    for rowid,source_id,kind,title,abstract,url in rows:
        try:
            if kind in ('paper','wikipedia') and (title or abstract):
                paper_id=(source_id[6:] if source_id.startswith('paper:') else source_id)
                outcome=abc_ingest_online_clusters(con,paper_id,title or '',abstract or '',
                                                    url=url or '')
                flin_record_ingest_diagnostic(con,source_id,'__cached_backfill__',outcome)
                totals['clusters']+=outcome['clusters']
                totals['active']+=outcome['promoted']
                totals['edges']+=outcome['edges']
        except (ValueError,TypeError,sqlite3.Error) as exc:
            totals['failed']+=1
            # A malformed legacy record must not block the entire sweep.
            con.execute("""INSERT INTO flin_ingest_diagnostics
                (source_id,topic,status) VALUES(?,'__cached_backfill__',?)
                ON CONFLICT(source_id,topic) DO UPDATE SET
                status=excluded.status,updated=CURRENT_TIMESTAMP""",
                (str(source_id),'error:'+str(exc)[:110]))
        finally:
            con.execute('INSERT OR REPLACE INTO abc_meta(key,value) VALUES(?,?)',
                        (meta,str(rowid)))
            con.commit()
            totals['scanned']+=1
    return totals


def abc_graph_totals(con):
    status=abc_status(con)
    return (status['topics'],status['learned_sources'],status['active'],status['edges'])


def flin_association_health(con):
    """Read-only evidence for distinguishing absent links from exhausted knowledge.

    No hardware/UI sampling, model inference, or graph mutation. A node may be
    active without an edge because one grounded concept suffices for formation,
    while learned directed edges require a source-observed ordered pair.
    """
    active,edges=con.execute("""SELECT
        (SELECT COUNT(*) FROM abc_units WHERE status='active'),
        (SELECT COUNT(*) FROM abc_edges)""").fetchone()
    source_count=con.execute('SELECT COUNT(*) FROM abc_sources').fetchone()[0]
    single,multi=con.execute("""SELECT
        COALESCE(SUM(CASE WHEN n=1 THEN 1 ELSE 0 END),0),
        COALESCE(SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END),0)
        FROM (SELECT COUNT(*) n FROM abc_cluster_features GROUP BY cluster_id)""").fetchone()
    isolated=con.execute("""SELECT COUNT(*) FROM abc_units u
        WHERE u.status='active' AND NOT EXISTS
            (SELECT 1 FROM abc_edges e WHERE e.src=u.id)
        AND NOT EXISTS (SELECT 1 FROM abc_edges e WHERE e.dst=u.id)""").fetchone()[0]
    bad_endpoints=con.execute("""SELECT COUNT(*) FROM abc_edges e
        WHERE NOT EXISTS (SELECT 1 FROM abc_units u WHERE u.id=e.src AND u.status='active')
           OR NOT EXISTS (SELECT 1 FROM abc_units u WHERE u.id=e.dst AND u.status='active')""").fetchone()[0]
    updated=con.execute('SELECT COALESCE(SUM(observations),0) FROM abc_edges').fetchone()[0]
    diagnostics=dict(con.execute('SELECT status,COUNT(*) FROM flin_ingest_diagnostics '
                                'GROUP BY status'))
    pending=con.execute('SELECT COUNT(*) FROM abc_replay_queue').fetchone()[0]
    cursor=con.execute("SELECT value FROM abc_meta WHERE key='flin_source_input_backfill_v3_rowid'").fetchone()
    return {'active_memories':active,'directed_links':edges,
            'link_observations_total':updated,'isolated_active_memories':isolated,
            'isolated_fraction':round(isolated/max(1,active),5),
            'stored_single_feature_clusters':single,
            'stored_multi_feature_clusters':multi,
            'stored_sources':source_count,'pending_link_replay':pending,
            'edges_with_inactive_or_missing_endpoint':bad_endpoints,
            'ingestion_statuses':diagnostics,
            'historical_link_recovery_cursor':int(cursor[0]) if cursor else 0,
            'interpretation':('A stagnant link count does NOT prove all links were learned. '
               'New singleton memories and source clusters can accumulate without '
               'an observed ordered feature pair. Compare multi-feature clusters, '
               'isolated nodes and link observations; repair cached sources incrementally.')}


def abc_ingest_online_clusters(con, paper_id, title, abstract='', fulltext='', url='',
                               *, prepared_clusters=None):
    """Web/arXiv/Crossref -> grounded clusters -> SSRS -> FLIN memory graph."""
    if not abc_enabled(con):return {'clusters':0,'promoted':0,'edges':0,'extracted':0}
    clusters=(prepared_clusters if prepared_clusters is not None else
              abc_extract_input_clusters(paper_id,title,abstract,fulltext,url))
    done=promoted=edges=0
    for item in clusters:
        res=abc_ingest_cluster(con,item['features'],item['id'],
                        defer_replay=True, evidence_source_id=(str(paper_id) if str(paper_id).startswith('wiki:') else 'paper:'+str(paper_id)),
                        gate_label='online_mathematical_input',
                        cluster_quote=item['quote'],paper_id=paper_id,
                        cluster_url=item.get('url') or url)
        if not res.get('duplicate'):
            done+=1;promoted+=res['promoted'];edges+=res['edges']
    # One bounded reconcile per paper, not one SQLite graph pass per sentence.
    replay=abc_reconcile_pending(con,limit=400)
    edges+=replay['edges']
    return {'clusters':done,'promoted':promoted,'edges':edges,'extracted':len(clusters),
            'new_links':replay['new_links'], 'reinforcements':replay['reinforcements']}


def abc_ingest_cluster(con, features, source_id, gate_label='source', *, eta=.22,
                       max_weight=10., allow_unverified=False, evidence_source_id=None,
                       cluster_quote=None, paper_id=None, cluster_url='',
                       defer_replay=False):
    """Commit one evidence-grounded effective input event.

    Each feature {label, explanation, position, url} originates in the cited
    document.  SSRS *decides* routing order by event position and learned
    SSRS priority. The separate learning policy reinforces adjacent groups
    from qualified inputs only. Mere similarity/recall never trains edges.
    """
    abc_schema(con)
    if not source_id or not isinstance(features,(list,tuple)):
        raise ValueError(' effective input must contains with unique Source and feature list ')
    source_id=str(source_id)
    previously_observed=bool(con.execute(
        'SELECT 1 FROM abc_learning_events WHERE source_id=?',(source_id,)).fetchone())
    if previously_observed and cluster_quote is None:
        return {'duplicate':True,'activated':[],'promoted':0,'edges':0}
    previous_features=({r[0] for r in con.execute(
        'SELECT unit_id FROM abc_cluster_features WHERE cluster_id=?',(source_id,))}
        if previously_observed else set())
    filtered={}
    for position,feature in enumerate(features[:96]):
        label=str(feature.get('label','')).strip()[:160]
        score,_=score_math_unit_purity(label,'concept')
        if score<75:continue
        explanation=str(feature.get('explanation','')).strip()[:1300]
        if not explanation or len(explanation)<28:continue
        if abc_key(label) not in abc_key(explanation) and not allow_unverified:
            # The cited paragraph must actually name the purported concept.
            continue
        uid=abc_identifier(label)
        item={'id':uid,'label':label,'explanation':explanation,
              'position':max(0.0,float(feature.get('position',position))),
              'url':str(feature.get('url',''))[:600],'quality':score}
        if uid not in filtered or item['position']<filtered[uid]['position']:
            filtered[uid]=item
    if previously_observed:
        # Parser improvements may discover a NEW feature in the exact same
        # recorded passage. Admit only the new feature, preserving the earlier
        # SSRS exposures, evidence votes, and idempotent abc_cluster_links.
        filtered={uid:item for uid,item in filtered.items() if uid not in previous_features}
        if not filtered:
            return {'duplicate':True,'activated':[],'promoted':0,'edges':0}
    if not filtered:
        return {'duplicate':False,'activated':[],'promoted':0,'edges':0}
    # SSRS is its own pluggable routing process; external text ordering is
    # evidence, not an association edge. Observed priority can alter grouping.
    with con:
        activated=[]; promoted=0;newly_promoted=[]
        if cluster_quote is not None:
            con.execute('INSERT OR IGNORE INTO abc_input_clusters '
                '(id,paper_id,quote,url,feature_count) VALUES(?,?,?,?,?)',
                (source_id,str(paper_id or ''),str(cluster_quote)[:1300],
                 str(cluster_url or '')[:600],len(filtered)))
            for item in filtered.values():
                con.execute('INSERT OR IGNORE INTO abc_cluster_features(cluster_id,unit_id,position) '
                    'VALUES(?,?,?)',(source_id,item['id'],item['position']))
        for uid,item in filtered.items():
            row=con.execute('SELECT status FROM abc_units WHERE id=?',(uid,)).fetchone()
            if row is None:
                con.execute('INSERT INTO abc_units(id,label,definition,status,quality) '
                            'VALUES(?,?,?,\'active\',?)',
                            (uid,item['label'],item['explanation'],item['quality']))
                flin_record_cost_decision(con,source_id,uid,'primitive',
                    'create_memory',FLIN_COST_FORMATION+FLIN_COST_STORAGE,
                    FLIN_COST_FORMATION+FLIN_COST_STORAGE,
                    'New, source-grounded mathematical feature: no verified equivalent '
                    'representation in existing memory; do not suppress first input.')
            evidence_source=str(evidence_source_id or source_id)
            older=con.execute('SELECT explanation FROM abc_evidence '
                'WHERE unit_id=? AND source_id=?',(uid,evidence_source)).fetchone()
            if older is None:
                con.execute('INSERT INTO abc_evidence(unit_id,source_id,explanation,url) '
                            'VALUES(?,?,?,?)',(uid,evidence_source,item['explanation'],item['url']))
            elif (not abc_explanatory_evidence(older[0]) and
                  abc_explanatory_evidence(item['explanation'])):
                # Keep exactly ONE vote per independent paper, but upgrade its
                # citation when a later sentence explains the concept better.
                con.execute('UPDATE abc_evidence SET explanation=?,url=? '
                    'WHERE unit_id=? AND source_id=?',
                    (item['explanation'],item['url'],uid,evidence_source))
            support=con.execute('SELECT COUNT(*) FROM abc_evidence WHERE unit_id=?',(uid,)).fetchone()[0]
            # A FIRST grounded effective input forms a triggerable memory.
            # Independent references are provenance/verification, NOT activation gates.
            # The feature has already passed quality, literal occurrence and
            # evidence admission above. Keep the original snippet as definition.
            new_status='active'
            if not row or row[0]!='active':
                promoted+=1;newly_promoted.append(uid)
            if abc_explanatory_evidence(item['explanation']):
                con.execute('UPDATE abc_units SET evidence_count=?,status=?,definition=? WHERE id=?',
                            (support,new_status,item['explanation'],uid))
            else:
                con.execute('UPDATE abc_units SET evidence_count=?,status=? WHERE id=?',
                            (support,new_status,uid))
            # A small learned routing bias is updated from qualified external
            # input events only. It does not learn from the pulses themselves.
            observed_position=item['position']
            bias=(1./(1.+observed_position)) if observed_position<1e6 else 0.
            con.execute('INSERT INTO abc_ssrs(unit_id,priority,exposures) VALUES(?,?,1) '
                        'ON CONFLICT(unit_id) DO UPDATE SET exposures=exposures+1,'
                        'priority=0.95*priority+0.05*excluded.priority',
                        (uid,bias))
            activated.append(item)
        # SSRS order is decided here, not by graph search or edge weights.
        # Learned route priority resolves near-simultaneous events. Events in
        # exactly the same group are concurrent: no invented direction.
        priorities={uid:p for uid,p in con.execute('SELECT unit_id,priority FROM abc_ssrs '
                                                   'WHERE unit_id IN ('+','.join('?'*len(filtered))+')',
                                                   tuple(filtered))}
        def ssrs_time(item):
            # Unknown source order remains concurrent, not invented by bias.
            if item['position']>=1e6:return item['position']
            return item['position']-0.1*priorities.get(item['id'],0.)
        activated.sort(key=lambda f:(ssrs_time(f),f['id']))
        groups=[]
        for item in activated:
            position=ssrs_time(item)
            if not groups or abs(groups[-1][0]-position)>1e-8:
                groups.append((position,[item]))
            else:groups[-1][1].append(item)
        # For persisted online clusters, links are learned through a replay
        # queue so candidates acquired from later INDEPENDENT papers can also
        # form associations with earlier experienced clusters. Links are
        # never strengthened twice from the same input event.
        updates=0
        if cluster_quote is not None:
            con.execute('INSERT OR IGNORE INTO abc_replay_queue(cluster_id) VALUES(?)',(source_id,))
            for uid in newly_promoted:
                con.execute('INSERT OR IGNORE INTO abc_replay_queue(cluster_id) '
                    'SELECT cluster_id FROM abc_cluster_features WHERE unit_id=?',(uid,))
            if not defer_replay:
                updates=abc_reconcile_pending(con,limit=90,eta=eta,max_weight=max_weight)['edges']
        else:
            # Compatibility for explicit external calls without a saved cluster.
            for (_,left),(_,right) in zip(groups,groups[1:]):
                for a in left:
                    for b in right:
                        if a['id']==b['id']:continue
                        existing=con.execute('SELECT weight FROM abc_edges WHERE src=? AND dst=?',
                                             (a['id'],b['id'])).fetchone()
                        w=existing[0] if existing else 1.0
                        w2=w+max(0.,min(1.,float(eta)))*(max_weight-w)
                        con.execute('INSERT INTO abc_edges(src,dst,weight,observations) '
                                    'VALUES(?,?,?,1) ON CONFLICT(src,dst) DO UPDATE SET '
                                    'weight=excluded.weight,observations=observations+1',
                                    (a['id'],b['id'],min(max_weight,w2)))
                        updates+=1
        if not previously_observed:
            con.execute('INSERT INTO abc_learning_events(source_id,gate_label,activated_json) '
                        'VALUES(?,?,?)', (source_id,str(gate_label)[:180],
                                json.dumps([v['id'] for v in activated],ensure_ascii=False)))
        else:
            # Preserve the original gate and add only truly new triggerable IDs.
            row=con.execute('SELECT activated_json FROM abc_learning_events '
                            'WHERE source_id=?',(source_id,)).fetchone()
            try:old_ids=json.loads(row[0]) if row else []
            except (TypeError,ValueError):old_ids=[]
            merged=list(dict.fromkeys([*old_ids,*(v['id'] for v in activated)]))
            con.execute('UPDATE abc_learning_events SET activated_json=? WHERE source_id=?',
                        (json.dumps(merged,ensure_ascii=False),source_id))
    return {'duplicate':False,'activated':[f['label'] for f in activated],
            'promoted':promoted,'edges':updates}


def abc_learn_paper(con, paper_id, *, fulltext='', prepared_clusters=None):
    """Replay original accepted online text as *clusters*, not isolated mentions."""
    if not abc_enabled(con):return None
    row=con.execute('SELECT title,abstract,url FROM papers WHERE id=?',(paper_id,)).fetchone()
    if not row:return {'clusters':0,'promoted':0,'edges':0}
    title,abstract,url=row
    return abc_ingest_online_clusters(con,paper_id,title,abstract,fulltext,url,
                                      prepared_clusters=prepared_clusters)


def abc_backfill(con,limit=100,progress=None):
    """Incrementally replay existing cited papers without re-downloading."""
    abc_schema(con)
    cursor=con.execute("SELECT value FROM abc_meta WHERE key='input_cluster_backfill_cursor'").fetchone()
    after=cursor[0] if cursor else ''
    rows=con.execute('SELECT id FROM papers WHERE id>? ORDER BY id LIMIT ?',
                     (after,max(1,min(10000,int(limit))))).fetchall()
    added=0
    for i,(paper_id,) in enumerate(rows,1):
        result=abc_learn_paper(con,paper_id)
        if result:added+=result.get('clusters',0)
        with con:
            con.execute("INSERT INTO abc_meta(key,value) VALUES('input_cluster_backfill_cursor',?) "
                        'ON CONFLICT(key) DO UPDATE SET value=excluded.value',(paper_id,))
        if progress and i%25==0:progress(i,len(rows))
    replay=abc_reconcile_pending(con,limit=300)
    return {'processed':len(rows),'new_events':added,'replay':replay,
            'finished':len(rows)<max(1,min(10000,int(limit)))}


def abc_recent_input_clusters(con, limit=25):
    """Read original online statements and features; no modifications."""
    abc_schema(con)
    rows=con.execute('SELECT id,paper_id,quote,url,feature_count,created '
                     'FROM abc_input_clusters ORDER BY rowid DESC LIMIT ?',
                     (max(1,min(300,int(limit))),)).fetchall()
    result=[]
    for cid,pid,quote,url,n,created in rows:
        labels=[r[0] for r in con.execute('SELECT u.label FROM abc_cluster_features f '
            'JOIN abc_units u ON u.id=f.unit_id WHERE f.cluster_id=? '
            'ORDER BY f.position,u.label',(cid,))]
        result.append({'id':cid,'paper_id':pid,'quote':quote,'url':url,
                       'feature_count':n,'features':labels,'created':created})
    return result


def abc_seed_units(con,query):
    """Deterministic lexical entry only; no embedding, LLM or Beam Search."""
    abc_schema(con)
    names=[v.strip() for v in re.split(r'[,，;；\n]+',str(query)) if v.strip()]
    matched=[];seen=set()
    for name in names[:12]:
        value=abc_key(name)
        row=con.execute('SELECT id,label FROM abc_units WHERE status=\'active\' '
                        'AND label=? COLLATE NOCASE LIMIT 1',(name,)).fetchone()
        if row is None:
            row=con.execute('SELECT id,label FROM abc_units WHERE status=\'active\' '
                            'AND label LIKE ? COLLATE NOCASE ORDER BY evidence_count DESC LIMIT 1',
                            (name+'%',)).fetchone()
        if row is not None and row[0] not in seen:
            seen.add(row[0]);matched.append((row[0],row[1],name))
    return matched


def abc_integrated_response(event_times, duration, window, threshold):
    """Exact integral of frequency & thresholded frequency (piecewise constant).

    Average readout does NOT depend on the number of GUI plot samples; short
    flashes cannot disappear simply because a display sample missed them.
    """
    changes=[]
    for t in event_times:
        if t>=duration:continue
        changes.append((max(0.,t),1))
        changes.append((min(duration,t+window),-1))
    changes.sort()
    previous=0.;active=0;raw_area=0.;visible_area=0.
    for t,delta in changes+[(duration,0)]:
        span=max(0.,t-previous)
        frequency=active/window
        raw_area+=span*frequency
        if frequency>=threshold:
            visible_area+=span*frequency
        active+=delta;previous=t
    return raw_area/duration,visible_area/duration


def flin_weighted_exit(con, current, previous, visited, max_revisits, rng, cache):
    """Draw exactly one eligible outgoing directed edge with P(edge)=w/sum(w).

    No extra probability-of-transmission roll or pulse attenuation. The known
    strength-to-probability mapping is a configurable engineering hypothesis,
    not an assertion of a verified biological law. Never truncate hubs to
    only their strongest edges; sample all positive-weight eligible exits.
    """
    if current not in cache:
        rows=con.execute('''SELECT e.dst,e.weight,u.label FROM abc_edges e
            JOIN abc_units u ON u.id=e.dst AND u.status='active'
            WHERE e.src=? AND e.weight>0 ORDER BY e.weight DESC,e.dst ASC LIMIT 1001''',
            (current,)).fetchall()
        cache[current]=(tuple(rows) if len(rows)<=1000 else None)
    stored=cache[current]
    if stored is None:
        choices=con.execute('''SELECT e.dst,e.weight,u.label FROM abc_edges e
            JOIN abc_units u ON u.id=e.dst AND u.status='active'
            WHERE e.src=? AND e.weight>0 ORDER BY e.weight DESC,e.dst ASC''',
            (current,))
    else:
        choices=stored
    chosen=None;total=0.0
    for dst,weight,label in choices:
        if dst==previous or visited[dst]>=max_revisits:continue
        strength=float(weight)
        if not math.isfinite(strength) or strength<=0:continue
        total+=strength
        if rng.random()*total<strength:
            chosen=(dst,strength,label)
    return chosen


def abc_simulate(con,query,*,pulse_hz=18.,input_duration=2.,edge_dt=.0001,
                 frequency_window=.25,frequency_threshold=2.,max_revisits=2,
                 max_steps=32,quiet_window=.4,sample_count=90,
                 max_pulses=1400,save=True,random_seed=None):
    """Finite-event, single-path, minimum-impedance pulse model.

    Continuous supply is separate from SSRS (which routes to memory inputs).
    A pulse has gate ID, no attenuation and one outgoing destination. Direct
    backtracking is forbidden; longer cycles permitted with a per-node cap.
    The reaction is *only* frequency in a sliding time window. Over-threshold
    time averages are then proportionally normalized (no winner-take-all).
    """
    abc_schema(con)
    if random_seed is None:
        random_seed=random.SystemRandom().getrandbits(64)
    rng=random.Random(random_seed)
    cfg={'routing':'weighted_one_path', 'random_seed':random_seed,
         'pulse_hz':float(pulse_hz),'input_duration':float(input_duration),
         'edge_dt':float(edge_dt),'frequency_window':float(frequency_window),
         'frequency_threshold':float(frequency_threshold),
         'max_revisits':int(max_revisits),'max_steps':int(max_steps),
         'quiet_window':float(quiet_window),'sample_count':int(sample_count)}
    if not (0.05<=cfg['pulse_hz']<=10000 and .001<=cfg['input_duration']<=120
            and 1e-8<=cfg['edge_dt']<=.5 and .001<=cfg['frequency_window']<=60
            and 0<=cfg['frequency_threshold']<=1e6 and 1<=cfg['max_revisits']<=20
            and 1<=cfg['max_steps']<=1024 and .001<=cfg['quiet_window']<=10
            and 4<=cfg['sample_count']<=400):
        raise ValueError(' Pulse exceeds parameter bounds safe simulation range ')
    seeds=abc_seed_units(con,query)
    if not seeds:
        raise ValueError('FLIN  Network cannot find match Memory unit ; # one imes valid Literature input exactly can Build can trigger Memory unit .')
    n_pulses=max(1,int(cfg['pulse_hz']*cfg['input_duration']))
    if n_pulses>max_pulses:
        raise ValueError(f' exceeds per-run imes simulation safety maximum  {max_pulses}  pulses Pulse , please adjust low Frequency or Time ')
    events=defaultdict(list); path_examples=[];feedback=[];pulse_records=[]
    edge_cache={}; labels={uid:label for uid,label,_ in seeds}
    next_releases=[]
    # All supply gates are active while their effective input exists. They
    # receive pulses from the external continuous source, not from SSRS.
    for j in range(n_pulses):
        gate=j%len(seeds)
        next_releases.append((j/cfg['pulse_hz'],gate,seeds[gate][0]))
    last_time=0.
    for start,gate_index,entry in next_releases:
        gate='gate:'+seeds[gate_index][2]
        current=entry;prev=None;visited=defaultdict(int);route=[]
        for depth in range(cfg['max_steps']):
            tick=start+depth*cfg['edge_dt']; last_time=max(last_time,tick)
            events[current].append(tick);pulse_records.append((gate,current,tick))
            visited[current]+=1;route.append(current)
            # The input is directly triggerable even on first experience.
            # Among several learned exits, newly formed weaker routes have
            # smaller (not zero) probability. Exactly ONE exit conducts.
            exit_edge=flin_weighted_exit(con,current,prev,visited,
                cfg['max_revisits'],rng,edge_cache)
            if exit_edge is None:
                feedback.append((gate,current,'no_eligible_exit',tick));break
            dst,w,label=exit_edge
            labels[dst]=label
            prev,current=current,dst
        else:
            feedback.append((gate,route[-1],'max_steps_guard',last_time))
        if len(path_examples)<15:path_examples.append([labels.get(uid,uid) for uid in route])
    # Finish only after the last event has left the frequency window AND
    # the external input has stopped; a quiet period alone is not enough.
    finish=max(cfg['input_duration'],last_time+max(cfg['quiet_window'],cfg['frequency_window']))
    duration=max(finish,1e-6)
    times=[duration*i/(cfg['sample_count']-1) for i in range(cfg['sample_count'])]
    raw_mean={};visible_mean={}
    # Compute exact B readout for *all* activated memory units using the
    # losslessly recorded pulse events. C is reconstructed from event times;
    # plotting series are only materialized for a small bounded subset.
    for uid,arr in events.items():
        arr.sort()
        raw_mean[uid],visible_mean[uid]=abc_integrated_response(
            arr,duration,cfg['frequency_window'],cfg['frequency_threshold'])
    total=sum(visible_mean.values())
    distribution=[{'id':uid,'label':labels.get(uid,uid),
                   'raw_average_hz':round(raw_mean[uid],6),
                   'visible_average_hz':round(visible_mean[uid],6),
                   'proportion':round(visible_mean[uid]/total,9) if total else 0.,
                   'visits':len(events[uid])}
                  for uid in events if visible_mean[uid]>0]
    distribution.sort(key=lambda x:(-x['visible_average_hz'],x['id']))
    # Select UI curves, NOT learning / readout nodes. All pulse events are
    # persisted, so the full time-varying reaction can be reconstructed later.
    display_ids=[v['id'] for v in distribution[:48]]
    display_ids+= [uid for uid in sorted(raw_mean,key=raw_mean.get,reverse=True)
                   if uid not in set(display_ids)][:12]
    frames=[]
    for uid in display_ids:
        arr=events[uid]
        raw=[];visible=[]
        for t in times:
            freq=(bisect_right(arr,t)-bisect_left(arr,t-cfg['frequency_window']))/cfg['frequency_window']
            raw.append(freq)
            visible.append(freq if freq>=cfg['frequency_threshold'] else 0.)
        frames.append((uid,raw,visible))
    result={'query':query,'settings':cfg,'matched':[{'id':uid,'label':label,'gate':name}
                   for uid,label,name in seeds],
            'input_pulses':n_pulses,'end_time_s':round(duration,6),
            'distribution':distribution,'activated_count':len(events),
            'visible_count':len(distribution),'feedback_count':len(feedback),
            'path_examples':path_examples,
            'time_samples_s':times,
            'response_curve_note':' complete  C  can by  abc_pulse_events  precisely reconstruct ; displayed response curve only Display representative Memory unit .',
            'response_series':[{'id':uid,'label':labels.get(uid,uid),
                                 'raw_hz':raw,'visible_hz':visible}
                               for uid,raw,visible in frames],
            'run_id':None,
            'notice':' Single-path routing uses weighted sampling by association strength ; Weight represents learned preference , NOT is Mathematics define principle credibility .'
                     ' long cycles are allowed but with limit imes Revisits ; feedback forward only to Source gate .'}
    if save:
        with con:
            cur=con.execute('INSERT INTO abc_runs(query,settings_json,result_json) VALUES(?,?,?)',
                            (query,json.dumps(cfg,ensure_ascii=False),json.dumps(result,ensure_ascii=False)))
            run_id=cur.lastrowid;result['run_id']=run_id
            con.executemany('INSERT INTO abc_pulse_events(run_id,gate,unit_id,time_s) VALUES(?,?,?,?)',
                            [(run_id,gate,uid,t) for gate,uid,t in pulse_records])
            # Trace gate tags correctly: a node's reaction does not depend on
            # them, but provenance / per-gate feedback still does.
            con.executemany('INSERT INTO abc_feedback(run_id,gate,end_unit,reason,time_s) '
                            'VALUES(?,?,?,?,?)',[(run_id,*row) for row in feedback])
            con.execute('UPDATE abc_runs SET result_json=? WHERE id=?',
                        (json.dumps(result,ensure_ascii=False),run_id))
    return result


def abc_question_context(con,result):
    '''Use activated FLIN memory units and real source quotes only.

    Associative links are learned from observed input order, NEVER interpreted
    as mathematical implication. Mathematical claims must be independently
    evaluated by the question author/reviewer.
    '''
    distribution=result.get('distribution',[])
    context={'query':result['query'],'matched':[], 'concepts':[],
             'relations':[], 'sources':[],
             'warnings':['FLIN  Link Strength represents input formed by learning routing preference ;'
                        ' Path and Response Cannot treat as Mathematics derivation or research novelty proof .'],
             'abc_reaction':distribution,'abc_run_id':result.get('run_id'),
             'abc_paths':result.get('path_examples',[])}
    seen=set()
    seed_terms={row['id']:row.get('gate','') for row in result.get('matched',[])}
    for item in distribution[:500]:
        context['matched'].append({'id':item['id'],'label':item['label'],
            'input':item['label'],'query':seed_terms.get(item['id'],''),
            'match_score':item['proportion'],
            'reaction_hz':item['visible_average_hz']})
        context['concepts'].append({'id':item['id'],'term':item['label'],
            'reaction_hz':item['visible_average_hz'],
            'proportion':item['proportion']})
        for source,quote,url in con.execute('''SELECT e.source_id,e.explanation,e.url
            FROM abc_evidence e WHERE e.unit_id=? ORDER BY e.source_id LIMIT 3''',
            (item['id'],)):
            if source in seen:continue
            seen.add(source)
            record=con.execute('SELECT title,kind FROM abc_sources WHERE id=?',
                               (source,)).fetchone()
            context['sources'].append({'id':source,'ref':'S'+str(len(seen)),
                'title':record[0] if record else source,
                'kind':record[1] if record else 'unknown',
                'url':url,'excerpt':quote[:480]})
            if len(seen)>=45:break
        if len(seen)>=45:break
    return context


def abc_save_as_association(con, result):
    """Reuse unchanged 10-question/review/export pipeline with FLIN recall."""
    context=abc_question_context(con,result)
    paths=[{'seed':result['query'],'labels':labels,'ids':[abc_identifier(x) for x in labels],
            'edge_kinds':['abc_learned' for _ in range(max(0,len(labels)-1))],
            'weights':[],'evidence_type':' actual  FLIN  Pulse single to walk ( example )','score':0}
           for labels in result.get('path_examples',[])[:15]]
    text=('FLIN  Pulse association ( above threshold overall distribution ):'+result['query']+'\n'
          +'\n'.join(f"{v['label']}| Frequency mean  {v['visible_average_hz']:.3f} Hz"
                     f"| Mode ratio  {v['proportion']:.2%}"
                     for v in result['distribution'][:35]))
    with con:
        cur=con.execute('INSERT INTO association_runs(query,paths_json,problem,model,matches_json) '
                        'VALUES(?,?,?,?,?)',(result['query'],json.dumps(paths,ensure_ascii=False),text,'FLIN pulse',
                          json.dumps(context['matched'],ensure_ascii=False)))
        run_id=cur.lastrowid
        con.execute('INSERT INTO association_context(run_id,context_json) VALUES(?,?)',
                    (run_id,json.dumps(context,ensure_ascii=False)))
    return run_id



# FLIN Knowledge Bridge Explorer — non-generative, read-only associative research.
# A bridge is a sampled route intersection or a real graph edge between sampled
# frontiers. It is NOT a logical deduction, new learned edge or mathematical proof.

def flin_bridge_explore(con, concepts, *, pulses_per_gate=360, max_steps=14,
                        max_revisits=2, random_seed=42, result_limit=60,
                        frontier_limit=120, stop_event=None, progress=None):
    """Explore independent single-path FLIN walks from 1..16 user concepts.

    Sampling calls the ORIGINAL flin_weighted_exit(), preserving routing
    eligibility, the reservoir-weighted distribution and one-path propagation.
    Does not write to the SQLite database, run table, links or learning weights.
    Finds (1) shared reachable nodes, (2) actual edges joining independently
    visited frontiers. Includes source-backed path explanations when available.
    """
    import heapq
    if isinstance(concepts,str):
        terms=[t.strip() for t in re.split(r'[,，;；\n]+',concepts) if t.strip()]
    else:
        terms=[str(t).strip() for t in concepts if str(t).strip()]
    if not (1<=len(terms)<=16):
        raise ValueError('Enter 1–16 distinct memory concepts (separate with commas).')
    if len({t.casefold() for t in terms})!=len(terms):
        raise ValueError('Repeated input concepts: each gate must be distinct.')
    pulses_per_gate=int(pulses_per_gate);max_steps=int(max_steps)
    max_revisits=int(max_revisits);result_limit=int(result_limit)
    if not (20<=pulses_per_gate<=4000 and 2<=max_steps<=64 and
            1<=max_revisits<=20 and 5<=result_limit<=300):
        raise ValueError('Pulses 20–4000; steps 2–64; revisits 1–20; results 5–300.')
    # Resolve identities without calling abc_schema() (which would write).
    gates=[];missing=[];used=set()
    for term in terms:
        row=con.execute('SELECT id,label FROM abc_units '
                        "WHERE status='active' AND label=? COLLATE NOCASE LIMIT 1",
                        (term,)).fetchone()
        if row is None:
            # Literal prefix matching; escape LIKE metacharacters in user input.
            prefix=term.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            row=con.execute("SELECT id,label FROM abc_units WHERE status='active' "
                            "AND label LIKE ? ESCAPE '\\' COLLATE NOCASE "
                            'ORDER BY evidence_count DESC,id LIMIT 1',(prefix+'%',)).fetchone()
        if row is None:
            missing.append(term)
        elif row[0] not in used:
            gates.append({'input':term,'id':row[0],'label':row[1]});used.add(row[0])
        else:
            missing.append(term+' (same memory as another gate)')
    if not gates:
        raise ValueError('No input has a triggerable FLIN memory. Try an exact memory label.')
    if missing:
        raise ValueError('Unmatched input concepts: '+', '.join(missing)+
                         '. All specified inputs must resolve before joint exploration.')
    # Keep immutable DB snapshot for reproducibility even during other learning.
    # Callers may BEGIN a read transaction; we only execute SELECT statements.
    n_gates=len(gates)
    labels={g['id']:g['label'] for g in gates}
    hit_counts=[defaultdict(int) for _ in gates]
    depth_sums=[defaultdict(int) for _ in gates]
    sample_paths=[{} for _ in gates]
    sample_edges=set()
    edge_cache={}
    import hashlib as _bridge_hash
    for gi,gate in enumerate(gates):
        stable_seed=int.from_bytes(_bridge_hash.sha256(
            (str(random_seed)+'|'+gate['id']).encode('utf-8')).digest()[:8],'big')
        rng=random.Random(stable_seed)
        for pulse_idx in range(pulses_per_gate):
            if stop_event is not None and stop_event.is_set():
                raise InterruptedError('Knowledge bridge exploration cancelled; no data changed.')
            node=gate['id'];previous=None;visited=defaultdict(int);path=[];seen=set()
            for step in range(max_steps):
                path.append(node);visited[node]+=1
                if node not in seen:
                    seen.add(node)
                    hit_counts[gi][node]+=1
                    depth_sums[gi][node]+=step
                    if node not in sample_paths[gi] or len(path)<len(sample_paths[gi][node]):
                        sample_paths[gi][node]=tuple(path)
                if step==max_steps-1:
                    break  # guard: no selected hop is claimed without arrival
                choice=flin_weighted_exit(con,node,previous,visited,max_revisits,rng,edge_cache)
                if choice is None:break
                dst,weight,label=choice
                if len(sample_edges)<120000:sample_edges.add((node,dst))
                labels[dst]=label
                previous,node=node,dst
            if progress and ((pulse_idx+1)%max(20,pulses_per_gate//8)==0):
                progress(gi+1,n_gates,pulse_idx+1,pulses_per_gate)
    # Include paths to the other ORIGINAL inputs: these are not ordinary hubs.
    all_ids=set().union(*(h.keys() for h in hit_counts))
    # Full graph degree, not a viewport sample: this discourages generic hubs.
    degree={}
    if all_ids:
        for offset in range(0,len(all_ids),400):
            batch=list(sorted(all_ids))[offset:offset+400]
            # IN-degree counts are limited to positive links into active FLIN nodes.
            for uid,n in con.execute('SELECT e.dst,COUNT(*) FROM abc_edges e '
                        'JOIN abc_units u ON u.id=e.src AND u.status=\'active\' '
                        'WHERE e.weight>0 AND e.dst IN ('+','.join('?'*len(batch))+') '
                        'GROUP BY e.dst',batch):
                degree[uid]=int(n)
    def gate_stats(uid):
        return [{'gate':g['label'],'input':g['input'],
                 'hits':hit_counts[i].get(uid,0),
                 'probability':round(hit_counts[i].get(uid,0)/pulses_per_gate,6),
                 'mean_first_depth':round(depth_sums[i][uid]/hit_counts[i][uid],3)
                     if hit_counts[i].get(uid,0) else None}
                for i,g in enumerate(gates)]
    def score_node(uid, indices):
        probs=[hit_counts[i][uid]/pulses_per_gate for i in indices]
        depths=[depth_sums[i][uid]/hit_counts[i][uid] for i in indices]
        # Multi-gate coverage is primary; all gates retain their own probabilities.
        coverage=(len(indices)/max(2,n_gates))**2
        common=(math.prod(probs))**(1/len(probs))
        # Favor evidence-bearing nontrivial hops without making unseen paths up.
        surprising=min(1.7,0.7+0.20*min(5,min(depths)))
        popularity=1.0/math.sqrt(1.0+math.log1p(degree.get(uid,0)))
        return round(coverage*common*surprising*popularity,9)
    bridge_items=[]
    gate_ids={g['id'] for g in gates}
    for uid in all_ids:
        indices=[i for i in range(n_gates) if hit_counts[i].get(uid,0)]
        if len(indices)<2:continue
        paths={gates[i]['input']:list(sample_paths[i][uid]) for i in indices}
        bridge_items.append({'type':'shared_memory','id':uid,
            'label':labels.get(uid,uid),'coverage':len(indices),
            'score':score_node(uid,indices),'incoming_degree':degree.get(uid,0),
            'gate_stats':gate_stats(uid),'paths':paths})
    bridge_items.sort(key=lambda x:(-x['coverage'],-x['score'],x['label'].casefold()))
    shared_count=len(bridge_items)
    # A frontier connection is a stored directed edge from a node sampled by
    # one gate to a node sampled by another. A real edge is required.
    connection_candidates=[]
    if n_gates>1 and all_ids:
        memberships={uid:{i for i in range(n_gates) if uid in hit_counts[i]}
                     for uid in all_ids}
        checked=0;limited=False
        ordered_ids=sorted(all_ids)
        for offset in range(0,len(ordered_ids),300):
            src_batch=ordered_ids[offset:offset+300]
            for src,dst,weight in con.execute('SELECT src,dst,weight FROM abc_edges '
                        'WHERE weight>0 AND src IN ('+','.join('?'*len(src_batch))+')',src_batch):
                checked+=1
                if checked>250000:
                    limited=True;break
                if dst not in memberships or src==dst:continue
                left=memberships[src];right=memberships[dst]
                # Only frontier edges that bridge DIFFERENT input contexts.
                paired=[(a,b) for a in left for b in right if a!=b]
                if not paired:continue
                a,b=max(paired,key=lambda ab:(min(hit_counts[ab[0]][src],
                                    hit_counts[ab[1]][dst]),-ab[0],-ab[1]))
                p_a=hit_counts[a][src]/pulses_per_gate
                p_b=hit_counts[b][dst]/pulses_per_gate
                s=round(math.sqrt(p_a*p_b)*min(1.,float(weight)/3.)
                    /math.sqrt(1.+math.log1p(degree.get(dst,0))),9)
                connection_candidates.append({'type':'frontier_edge','id':dst,
                    'label':labels.get(src,src)+' → '+labels.get(dst,dst),
                    'source_id':src,'target_id':dst,'weight':float(weight),
                    'score':s,'coverage':2,'incoming_degree':degree.get(dst,0),
                    'gate_stats':gate_stats(dst),
                    'paths':{gates[a]['input']:list(sample_paths[a][src]),
                             gates[b]['input']:list(sample_paths[b][dst])},
                    'joined_from':gates[a]['input'],'joined_to':gates[b]['input']})
            if limited:break
        connection_candidates.sort(key=lambda x:(-x['score'],x['label']))
    else:limited=False
    # Broad concept landscape: expose independent perspectives, not a single
    # top-K most related result. Each gate receives a substantial concept pool.
    landscapes=[]
    for i,g in enumerate(gates):
        cands=[uid for uid in hit_counts[i] if uid not in gate_ids]
        cands.sort(key=lambda u:(-hit_counts[i][u],u))
        popular=cands[:max(5,frontier_limit//3)]
        deep=sorted(cands,key=lambda u:(-len(sample_paths[i][u]),
                       -hit_counts[i][u],u))[:max(5,frontier_limit//3)]
        rare=sorted(cands,key=lambda u:(degree.get(u,0),-hit_counts[i][u],u))[:max(5,frontier_limit//3)]
        picked=list(dict.fromkeys(popular+deep+rare))[:frontier_limit]
        landscapes.append({'input':g['input'],'gate':g['label'],'count':len(cands),
            'concepts':[{'id':u,'label':labels.get(u,u),
                         'pulse_reach':round(hit_counts[i][u]/pulses_per_gate,6),
                         'observed_depth':round(depth_sums[i][u]/hit_counts[i][u],2),
                         'incoming_degree':degree.get(u,0),
                         'path':list(sample_paths[i][u])} for u in picked]})
    # Collect inspectable primary source evidence for selected paths. No search
    # model or claimed proof; missing evidence is represented explicitly.
    ranked_shared=bridge_items[:result_limit]
    ranked_edges=connection_candidates[:result_limit]
    results=ranked_shared+ranked_edges
    selected_paths=set()
    for item in results:
        for path in item['paths'].values():
            selected_paths.update(zip(path,path[1:]))
        if item['type']=='frontier_edge':
            selected_paths.add((item['source_id'],item['target_id']))
    source_records={};evidence_cache={}
    for src,dst in sorted(selected_paths):
        rows=con.execute('''SELECT c.paper_id,c.quote,c.url,
                       COALESCE(s.title,''),COALESCE(s.kind,'')
                FROM abc_cluster_links link
                JOIN abc_input_clusters c ON c.id=link.cluster_id
                LEFT JOIN abc_sources s ON s.id=c.paper_id
                WHERE link.src=? AND link.dst=?
                ORDER BY c.rowid DESC LIMIT 2''',(src,dst)).fetchall()
        evidence_cache[(src,dst)]=[{'source_id':sid,'quote':quote[:450],
                     'url':url,'title':title,'provider':kind}
                    for sid,quote,url,title,kind in rows]
    for item in results:
        traces=[];source_ids=set()
        for gate_input,path in item['paths'].items():
            links=[]
            for src,dst in zip(path,path[1:]):
                ev=evidence_cache.get((src,dst),[])
                source_ids.update(e['source_id'] for e in ev)
                links.append({'src':src,'dst':dst,'src_label':labels.get(src,src),
                              'dst_label':labels.get(dst,dst),'evidence':ev})
            traces.append({'input':gate_input,
                  'nodes':[{'id':v,'label':labels.get(v,v)} for v in path],
                  'edges':links})
        if item['type']=='frontier_edge':
            src=item['source_id'];dst=item['target_id']
            bridge_evidence=evidence_cache.get((src,dst),[])
            source_ids.update(e['source_id'] for e in bridge_evidence)
            item['connecting_edge']={'src':src,'dst':dst,'weight':item['weight'],
                                      'evidence':bridge_evidence}
        item['traces']=traces
        item['independent_sources_in_displayed_paths']=len(source_ids)
    return {'kind':'flin_knowledge_bridge_explorer_v1',
        'inputs':gates,'unmatched':missing,
        'parameters':{'pulses_per_gate':pulses_per_gate,'max_steps':max_steps,
                      'max_revisits':max_revisits,'random_seed':random_seed},
        'statistics':{'visited_units':len(all_ids),'shared_memories':shared_count,
                      'frontier_connection_candidates':len(connection_candidates),
                      'frontier_scan_limited':limited,
                      'recorded_route_edges':len(sample_edges)},
        'bridges':ranked_shared,'frontier_connections':ranked_edges,
        'concept_landscapes':landscapes,
        'notes':['All paths were sampled from the stored directed FLIN association graph.',
                 'Shared reachability and connected frontiers are hypotheses for exploration, not proven semantic equivalence or mathematical implication.',
                 'The result is a Monte Carlo estimate: more pulses can discover new intersections.',
                 'A graph edge without an abc_cluster_links record has no directly displayed source evidence.',
                 'No memory units, edge weights, pulse runs, or source data were modified.']}

class NetworkWindow:
    BG = "#0c111b"
    PANEL = "#111a28"
    FIELD = "#1a2637"
    FG = "#e2e8f0"
    MUTED = "#9eacc0"
    ACCENT = "#69b5fd"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        screen_w=max(1000,self.root.winfo_screenwidth())
        screen_h=max(700,self.root.winfo_screenheight())
        self.root.geometry(f"{min(1500,screen_w-36)}x{min(930,screen_h-76)}")
        self.root.minsize(900, 610)
        self.root.configure(bg=self.BG)
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.collector = None
        self._collector_completion_observed = False
        self._last_collector_heartbeat_ui = 0.0
        self._last_frontier_status_check = 0.0
        self._frontier_shown_complete = False
        # All GUI-owned Python workers are tracked on the Tk main thread.
        # Tk images/variables must not outlive the Tcl interpreter while any
        # worker still holds references to this window.
        self._background_threads = set()
        self._closing = False
        self._shutdown_job = None
        self._shutdown_started = None
        self.plot_data = {}
        self.coords = {}
        self.chosen = None
        self.path = []
        self.dragging = None
        self.axis_xlim = None
        self.zoom = 1.0
        self.timeline_latest = 0
        self.timeline_cursor = 0
        self.timeline_live = True
        self.replaying = False
        self.replay_job = None
        self._updating_timeline = False
        self._last_redraw = 0.0
        self._pending_refresh = False
        self.results_window = None
        self._analysis_active = False
        self._generate_after_query = False  # legacy metadata only
        self._analysis_loading = None
        self.last_run_id = None
        self.generated_question = ''
        self.has_started = False
        self.active_theory = None
        self.active_index = 0
        self.active_total = 0
        self.worker_states = {}
        self.cpu_info = detect_cpu_resources()
        self.enqueued_theories = 0
        self.finished_theories = 0
        self.skipped_theories = 0
        self.success_theories = 0
        self.empty_theories = 0
        self._setup_style()
        # Load positions only for visible nodes on demand, not millions at startup.
        self.coords = {}
        self._local_focus_ids = None
        self._stats_cache = None
        self._viewport_empty_reason = 'No memory units yet'
        self._build_ui()
        self._refresh_build_completion_state()
        with database() as con:
            if con.execute('SELECT 1 FROM units LIMIT 1').fetchone():
                self.has_started=True
                self._set_test_available(True)
                self.status.set('Saved network loaded; learning can resume')
                self.graph_phase.set('Saved graph loaded. Large graphs show a sampled overview; search loads local neighbors.')
        with database() as con:
            latest = con.execute("SELECT name,state,found,processed FROM theory_progress "
                                 "ORDER BY rowid DESC LIMIT 1").fetchone()
        if latest:
            name, state, found, completed = latest
            self.active_theory = name
            self.pipeline_title.set(f'Last topic: {name}')
            self.pipeline_detail.set(
                f'Saved status: {state}; Processed  {completed}/{found}  papers Literature .')
            self.pipeline_percentage.set(100*completed/max(1,found) if found else 0)
            self.graph_phase.set('Currently displaying the most recently processed topic: ' + name)
        with database() as con:
            historic = con.execute("""SELECT COUNT(*) FROM theory_progress
                WHERE state IN ('skipped_search','error','interrupted')""").fetchone()[0]
        if historic:
            self.pipeline_detail.set(
                f'⚠  existing Database with  {historic:,}  items unsuccessful Topic ; Check literature provider connection ,'
                ' then click ` only Retry Database in Failed Topic `.')
        self.load_topics()
        self.reload_network()
        self.refresh_history(reset=True)
        self._poll_job = self.root.after(200, self.poll)
        self._auto_repair_job = self.root.after(900, self._auto_repair)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _start_background_thread(self, *, target, name, daemon=True):
        """Start and track a non-Tk worker; its results belong in self.events.

        This method is called from the GUI thread. Tracking happens only on
        that thread so the shutdown monitor needs no locks or Tk worker calls.
        """
        if self._closing:
            return None
        # Drop completed worker references during long-running sessions.
        self._background_threads = {t for t in self._background_threads if t.is_alive()}
        thread = threading.Thread(target=target, name=name, daemon=daemon)
        self._background_threads.add(thread)
        try:
            thread.start()
        except BaseException:
            self._background_threads.discard(thread)
            raise
        return thread

    def _setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        basefont = ('Arial', 10)
        style.configure('Dark.TFrame', background=self.BG)
        style.configure('Side.TFrame', background=self.PANEL)
        style.configure('Dark.TLabel', background=self.BG, foreground=self.FG, font=basefont)
        style.configure('Side.TLabel', background=self.PANEL, foreground=self.FG, font=basefont)
        style.configure('Note.TLabel', background=self.PANEL, foreground=self.MUTED,
                        font=('Arial', 9))
        style.configure('Section.TLabel', background=self.PANEL, foreground=self.FG,
                        font=('Arial', 11, 'bold'))
        style.configure('Dark.TButton', padding=(9, 8), background=self.FIELD,
                        foreground=self.FG, borderwidth=0)
        style.map('Dark.TButton', background=[('active', '#30445f')],
                  foreground=[('disabled','#6b7789')])
        style.configure('Danger.TButton', padding=(9, 8), background='#562d38',
                        foreground='#ffd6d6', borderwidth=0)
        style.map('Danger.TButton', background=[('active','#7d3946')])
        style.configure('Accent.TButton', padding=(9, 9), background='#286fa6',
                        foreground='white', borderwidth=0)
        style.map('Accent.TButton', background=[('active','#3f88c0')])
        style.configure('Dark.TEntry', fieldbackground=self.FIELD, foreground=self.FG,
                        insertcolor=self.FG)
        style.configure('Dark.TCombobox', fieldbackground=self.FIELD, background=self.FIELD,
                        foreground=self.FG)
        style.map('Dark.TCombobox', fieldbackground=[('readonly', self.FIELD)],
                  foreground=[('readonly', self.FG)], selectbackground=[('readonly', self.FIELD)],
                  selectforeground=[('readonly', self.FG)])
        style.configure('Dark.TSpinbox', fieldbackground=self.FIELD, foreground=self.FG,
                        arrowcolor=self.FG)
        style.configure('Dark.Treeview', background=self.FIELD, foreground=self.FG,
                        fieldbackground=self.FIELD, rowheight=28, borderwidth=0,
                        font=('Arial', 10))
        style.map('Dark.Treeview', background=[('selected','#245b7b')],
                  foreground=[('selected','white')])
        style.configure('Dark.Treeview.Heading', background=self.PANEL, foreground=self.FG,
                        font=('Arial', 10, 'bold'), relief='flat')
        style.map('Dark.Treeview.Heading', background=[('active', '#30445f')])
        style.configure('Dark.TRadiobutton', background=self.PANEL, foreground=self.FG)
        style.map('Dark.TRadiobutton', background=[('active', self.PANEL)])
        style.configure('Dark.TCheckbutton', background=self.PANEL, foreground=self.FG)
        style.map('Dark.TCheckbutton', background=[('active', self.PANEL)])
        style.configure('Brain.Horizontal.TProgressbar', troughcolor=self.FIELD,
                        background='#338ec5', bordercolor=self.PANEL,
                        lightcolor='#338ec5', darkcolor='#338ec5', thickness=11)

    def label(self, parent, txt, note=False, **kw):
        return ttk.Label(parent, text=txt,
                         style='Note.TLabel' if note else 'Side.TLabel', **kw)

    def _group(self, parent, heading, hint=None):
        box = ttk.Frame(parent, style='Side.TFrame', padding=(14, 12))
        box.pack(fill='x', padx=(0, 3), pady=(0, 7))
        ttk.Label(box, text=heading, style='Section.TLabel').pack(anchor='w', pady=(0, 4))
        if hint:
            self.label(box, hint, note=True, wraplength=370).pack(anchor='w', pady=(0, 8))
        return box

    def _row(self, parent):
        box = ttk.Frame(parent, style='Side.TFrame')
        box.pack(fill='x', pady=(3, 4))
        return box

    def _build_ui(self):
        header=ttk.Frame(self.root,style='Dark.TFrame',padding=(16,9))
        header.pack(fill='x')
        ttk.Label(header,text='FLIN / RESEARCH',style='Dark.TLabel',
                  font=('DejaVu Sans',16,'bold')).pack(side='left')
        ttk.Label(header,text='FLIN Mathematical Association | Research Workspace',style='Dark.TLabel').pack(side='left',padx=8)
        self.status=tk.StringVar(value='Ready | Auto-save to SQLite')
        ttk.Label(header,textvariable=self.status,style='Dark.TLabel').pack(side='right')
        panes=tk.PanedWindow(self.root,orient='horizontal',bg=self.BG,sashwidth=6,
                             sashrelief='flat',showhandle=False,borderwidth=0)
        panes.pack(fill='both',expand=True,padx=(8,8),pady=(0,8))
        graph=ttk.Frame(panes,style='Dark.TFrame')
        side=ttk.Frame(panes,style='Side.TFrame',width=405)
        panes.add(graph,stretch='always',minsize=520)
        panes.add(side,stretch='never',minsize=360,width=405)
        top=ttk.Frame(graph,style='Dark.TFrame',padding=(9,5));top.pack(fill='x')
        ttk.Label(top,text='FLIN Memory Network | 3D',style='Dark.TLabel',
                  font=('Arial',12,'bold')).pack(side='left')
        self.graph_stats=tk.StringVar(value='No nodes in the database')
        # Status is deliberately on its own responsive row. A long count such
        # as '12,345/1,511,826' must not collide with the 3D view title.
        self.graph_stats_label=ttk.Label(graph,textvariable=self.graph_stats,
                style='Dark.TLabel',padding=(12,2),anchor='w',justify='left',wraplength=710)
        self.graph_stats_label.pack(fill='x')
        self.graph_phase=tk.StringVar(value='Overview mode: established memories; search loads actual local associations')
        self.graph_phase_label=ttk.Label(graph,textvariable=self.graph_phase,
                style='Dark.TLabel',padding=(12,3),justify='left',wraplength=710)
        self.graph_phase_label.pack(fill='x')
        for caption in (self.graph_stats_label,self.graph_phase_label):
            caption.bind('<Configure>',lambda ev,w=caption:
                w.configure(wraplength=max(240,ev.width-26)))
        foot=ttk.Frame(graph,style='Dark.TFrame',padding=(9,7));foot.pack(side='bottom',fill='x')
        legend=ttk.Frame(foot,style='Dark.TFrame');legend.pack(fill='x',pady=(0,4))
        for kind,spec in NODE_STYLES.items():
            if kind not in ('concept','candidate'):continue
            tk.Label(legend,text=spec['legend']+' '+spec['name'],bg=self.BG,
                     fg=spec['color'],font=('Arial',10,'bold')).pack(side='left',padx=(0,13))
        ttk.Label(foot,text='Drag to rotate | Scroll to zoom | Click to select | Shift-drag to move a node. Search loads local context without deleting any data.',
                  style='Dark.TLabel').pack(anchor='w')
        self.worker_summary=tk.StringVar(value='Workers 0/0')
        tk.Label(foot,textvariable=self.worker_summary,fg='#e7eef8',bg=self.BG,
                 font=('Arial',10,'bold'),anchor='w').pack(fill='x',pady=(6,2))
        self.worker_detail=tk.StringVar(value='Network build has not started')
        tk.Label(foot,textvariable=self.worker_detail,fg='#a7c0db',bg='#162338',
                 justify='left',anchor='nw',wraplength=1050,padx=9,pady=7,
                 font=('DejaVu Sans Mono',9)).pack(fill='x')
        self.fig=plt.Figure(figsize=(10,8),dpi=100,facecolor=self.BG)
        self.ax=self.fig.add_subplot(111,projection='3d',facecolor=self.BG)
        self.fig.subplots_adjust(left=0,right=1,top=1,bottom=0)
        self.canvas=FigureCanvasTkAgg(self.fig,master=graph)
        self.canvas.get_tk_widget().configure(bg=self.BG,highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill='both',expand=True)
        for event,handler in [('button_press_event',self.on_click),('button_release_event',self.on_release),
                              ('motion_notify_event',self.on_drag),('scroll_event',self.on_scroll)]:
            self.canvas.mpl_connect(event,handler)
        scroller=tk.Canvas(side,bg=self.PANEL,highlightthickness=0,borderwidth=0)
        sb=ttk.Scrollbar(side,orient='vertical',command=scroller.yview)
        scroller.configure(yscrollcommand=sb.set)
        sb.pack(side='right',fill='y');scroller.pack(side='left',fill='both',expand=True)
        inside=ttk.Frame(scroller,style='Side.TFrame',padding=(10,10))
        wid=scroller.create_window((0,0),window=inside,anchor='nw')
        inside.bind('<Configure>',lambda e:scroller.configure(scrollregion=scroller.bbox('all')))
        scroller.bind('<Configure>',lambda e:scroller.itemconfigure(wid,width=e.width))
        scroller.bind('<Enter>',lambda e:scroller.bind_all('<MouseWheel>',
            lambda ev:scroller.yview_scroll(-int(ev.delta/120),'units')))
        scroller.bind('<Leave>',lambda e:scroller.unbind_all('<MouseWheel>'))

        # Database-per-network manager: full separation of old and new graphs.
        box=self._group(inside,'Memory Network Manager','Create, switch, or import networks. Existing databases will not be deleted.')
        self.active_network_label=tk.StringVar(value=active_network_record()['name'])
        self.active_domain_label=tk.StringVar(value='Build scope:'+domain_name())
        self.label(box,'Current network:',note=True).pack(anchor='w')
        ttk.Label(box,textvariable=self.active_network_label,
                  style='Section.TLabel').pack(anchor='w',pady=(3,5))
        self.label(box,'',textvariable=self.active_domain_label,note=True).pack(anchor='w',pady=(0,5))
        ttk.Button(box,text='Manage / Create / Switch / Import Networks',
                   command=self.open_network_manager,style='Accent.TButton').pack(fill='x')


        box=self._group(inside,'01  FLIN Memories and Sources',
                        'Directed association links encode learned input preferences, not proven mathematical implications.')
        self.counter=tk.StringVar(value='Topics 0 | Papers 0 | Memories 0 | Links 0')
        self.label(box,'',textvariable=self.counter,wraplength=350).pack(anchor='w')
        self.network_math_count=tk.StringVar(value='Mathematical relation memories: 0')
        self.label(box,'',textvariable=self.network_math_count,note=True).pack(anchor='w',pady=(4,0))
        ttk.Button(box,text='Mathematics / Cross-Discipline Coverage',style='Dark.TButton',
                   command=self.open_math_coverage).pack(fill='x',pady=(5,3))

        box=self._group(inside,'02  Locate Memories and Explore Neighbors',
                        'Search FLIN memory units and inspect their real learned directed links.')
        self.search_var=tk.StringVar()
        row=self._row(box)
        search=ttk.Entry(row,textvariable=self.search_var,style='Dark.TEntry')
        search.pack(side='left',fill='x',expand=True)
        search.bind('<Return>',lambda e:self.focus_memory())
        ttk.Button(row,text='Locate',style='Accent.TButton',command=self.focus_memory).pack(side='left',padx=(5,0))
        row=self._row(box)
        ttk.Button(row,text='Show Overview',style='Dark.TButton',command=self.clear_focus).pack(
            side='left',fill='x',expand=True,padx=(0,4))
        ttk.Button(row,text='Reset Camera',style='Dark.TButton',command=self.reset_camera).pack(
            side='left',fill='x',expand=True)
        self.search_hint=tk.StringVar(value='No active search')
        self.label(box,'',textvariable=self.search_hint,note=True,wraplength=350).pack(anchor='w')
        self.detail=tk.Text(box,height=5,wrap='word',bg=self.FIELD,fg=self.FG,
                            relief='flat',padx=8,pady=7,font=('Arial',10),state='disabled')
        self.detail.pack(fill='x',pady=(5,0))
        row=self._row(box)
        ttk.Button(row,text='View Sources',style='Dark.TButton',command=self.open_source).pack(
            side='left',fill='x',expand=True,padx=(0,4))
        ttk.Button(row,text='Trigger FLIN Pulses',style='Dark.TButton',command=self.associate).pack(
            side='left',fill='x',expand=True)

        box=self._group(inside,'02A  FLIN Directed Pulse Association',
            'A first qualified input creates a triggerable memory. Stronger links have higher selection probability; each pulse takes one path.')
        self.abc_status_var=tk.StringVar(value='FLIN network not yet loaded')
        self.label(box,'',textvariable=self.abc_status_var,note=True,wraplength=345).pack(anchor='w',pady=(0,4))
        ttk.Button(box,text='New Empty FLIN Network (no data copied)',
                   command=self.abc_create_network,style='Dark.TButton').pack(fill='x',pady=2)
        ttk.Button(box,text='Learn From Saved Papers (batch)',
                   command=self.abc_learn_existing,style='Dark.TButton').pack_forget()
        self.abc_input=tk.StringVar(value='')
        ttk.Entry(box,textvariable=self.abc_input,style='Dark.TEntry').pack(fill='x',pady=(5,2))
        self.label(box,'Pulse input: separate mathematical concepts with commas; only established FLIN memories can be triggered.',
                   note=True,wraplength=345).pack(anchor='w')
        row=self._row(box)
        self.abc_rate=tk.DoubleVar(value=18.0)
        self.abc_duration=tk.DoubleVar(value=2.0)
        self.abc_threshold=tk.DoubleVar(value=2.0)
        for text,var in [('Rate (Hz)',self.abc_rate),('Duration (s)',self.abc_duration),('Threshold (Hz)',self.abc_threshold)]:
            cell=ttk.Frame(row,style='Side.TFrame');cell.pack(side='left',fill='x',expand=True,padx=2)
            self.label(cell,text,note=True).pack(anchor='w')
            ttk.Entry(cell,textvariable=var,width=7,style='Dark.TEntry').pack(fill='x')
        ttk.Button(box,text='Run Pulse Simulation / Response Distribution',
                   command=self.abc_start_simulation,style='Accent.TButton').pack(fill='x',pady=(7,2))
        self.abc_last_run_id=None
        self.abc_last_association_id=None
        self._last_abc_refresh=0.0
        self.abc_worker_active=False
        self.abc_activity=tk.StringVar(value='Ready for effective inputs, directed transmission, and response curves.')
        self.label(box,'',textvariable=self.abc_activity,note=True,wraplength=345).pack(anchor='w')
        self.abc_refresh_status()
        ttk.Button(box,text='View Source-Grounded Input Clusters',
                   command=self.abc_show_input_clusters,style='Dark.TButton').pack(fill='x',pady=(5,1))
        ttk.Button(box,text='Reevaluate Existing Input Costs (1,000 clusters)',
                   command=self.flin_ui_retrofit,style='Dark.TButton').pack(fill='x',pady=(5,1))
        ttk.Button(box,text='Shortcut and Cost Report',
                   command=self.flin_ui_cost_report,style='Dark.TButton').pack(fill='x',pady=(2,1))

        # FLIN's public research output: a broad list of associations from real
        # weighted single-path walks. There is no question generation or LLM UI.
        box=self._group(inside,'03  Related Concepts',
            'Enter one or several existing memory concepts (comma-separated). '
            'FLIN returns a broad collection of memories reached by its actual '
            'weighted associative paths. This is not a proof of mathematical relevance.')
        self.bridge_terms=tk.StringVar(value='')
        self.test_var=self.bridge_terms  # old node-selection/search actions share the input
        entry=ttk.Entry(box,textvariable=self.bridge_terms,style='Dark.TEntry')
        entry.pack(fill='x',pady=(3,5))
        entry.bind('<Return>',lambda _e:self.flin_start_bridge_explorer())
        row=self._row(box)
        self.bridge_pulses=tk.IntVar(value=360)
        self.label(row,'Association paths per input',note=True).pack(side='left',padx=(0,8))
        ttk.Spinbox(row,from_=20,to=4000,increment=20,width=9,
                    textvariable=self.bridge_pulses,
                    style='Dark.TSpinbox').pack(side='left')
        self.bridge_active=False
        self.bridge_button=ttk.Button(box,text='Find Related Concepts',
                          style='Accent.TButton',command=self.flin_start_bridge_explorer)
        self.bridge_button.pack(fill='x',pady=(6,3))
        self.test_button=self.bridge_button  # preserve legacy node-selection callbacks
        self.bridge_status=tk.StringVar(value='Results come from stored directed links; no Ollama or learning-state changes.')
        self.label(box,'',textvariable=self.bridge_status,note=True,
                   wraplength=345).pack(anchor='w')

        # Right: exactly the core collection controls in the reference image.
        self.topic_count=tk.IntVar(value=64)
        self.papers_count=tk.IntVar(value=100)
        self.continuous_discovery=tk.BooleanVar(value=True)
        self._resource_manual_override = False
        self.cpu_recommendation = recommend_build_resources(self.cpu_info, read_pdf=False)
        self.workers_count=tk.IntVar(value=self.cpu_recommendation['workers'])
        self.cpu_budget_count=tk.IntVar(value=self.cpu_recommendation['cpu_budget'])
        self.cpu_capacity_label=tk.StringVar(value=self._cpu_capacity_text())
        self.cpu_recommendation_label=tk.StringVar(value=self._cpu_recommendation_text())
        self.offset=tk.IntVar(value=0)
        self.pdf_mode=tk.BooleanVar(value=False)
        self.pdf_mode.trace_add('write', lambda *_: self.refresh_cpu_capacity(quiet=True))
        self.wiki_references_mode=tk.BooleanVar(value=True)
        box=self._group(inside,'04  Automatic Network Building',
            'Wikipedia, arXiv, Crossref, OpenAIRE, DBLP, Europe PMC; optional OpenAlex and Semantic Scholar. Sources directly train FLIN.')
        row=self._row(box)
        for title,var,maximum in [('Max Mathematics Topics (1,000,000)',self.topic_count,MAX_THEORIES),
                                  ('Max Papers per Topic (1,000,000)',self.papers_count,MAX_PAPERS_PER_THEORY)]:
            cell=ttk.Frame(row,style='Side.TFrame');cell.pack(side='left',fill='x',expand=True,padx=(0,6))
            self.label(cell,title,note=True).pack(anchor='w')
            ttk.Spinbox(cell,from_=1,to=maximum,width=9,textvariable=var,
                        style='Dark.TSpinbox').pack(fill='x',pady=(4,0))
        ttk.Checkbutton(box,text='Continuous discovery and periodic retry (until stopped)',
                        variable=self.continuous_discovery).pack(anchor='w',pady=(6,2))
        self.label(box,'Batch limits are used only when continuous mode is off. '
                       'SQLite stores each explored topic and category continuation token.',
                   note=True,wraplength=345).pack(anchor='w')
        self.label(box,'CPU and Parallel Collection Resources',note=True).pack(anchor='w',pady=(9,3))
        self.label(box,'',textvariable=self.cpu_capacity_label,note=True,wraplength=350).pack(anchor='w')
        row=self._row(box)
        cell=ttk.Frame(row,style='Side.TFrame');cell.pack(side='left',fill='x',expand=True,padx=(0,6))
        self.label(cell,'Collector CPU budget (logical CPUs)',note=True).pack(anchor='w')
        self.cpu_budget_spinner=ttk.Spinbox(cell,from_=1,to=self.cpu_info['available'],
                            width=9,textvariable=self.cpu_budget_count,style='Dark.TSpinbox',
                            command=self._mark_resource_override)
        self.cpu_budget_spinner.pack(fill='x',pady=(4,0))
        cell=ttk.Frame(row,style='Side.TFrame');cell.pack(side='left',fill='x',expand=True)
        self.label(cell,'Parallel topic workers',note=True).pack(anchor='w')
        self.workers_spinner=ttk.Spinbox(cell,from_=1,to=self.cpu_info['available'],
                            width=9,textvariable=self.workers_count,style='Dark.TSpinbox',
                            command=self._mark_resource_override)
        self.workers_spinner.pack(fill='x',pady=(4,0))
        for spinner in (self.cpu_budget_spinner, self.workers_spinner):
            spinner.bind('<KeyRelease>', self._mark_resource_override)
            spinner.bind('<FocusOut>', self._mark_resource_override)
        self.label(box,'',textvariable=self.cpu_recommendation_label,note=True,
                   wraplength=350).pack(anchor='w',pady=(7,2))
        row=self._row(box)
        ttk.Button(row,text='Use Recommended Resources',command=self.apply_cpu_recommendation,
                   style='Dark.TButton').pack(side='left',fill='x',expand=True,padx=(0,4))
        ttk.Button(row,text='Detect Again',command=self.refresh_cpu_capacity,
                   style='Dark.TButton').pack(side='left',fill='x',expand=True)
        self.label(box,'On Linux, CPU affinity applies to collector worker threads; on Windows, '
                       'the CPU budget is advisory and the worker count is enforced. '
                       'API rate limits and SQLite writes may cap throughput.',
                   note=True,wraplength=350).pack(anchor='w',pady=(2,4))
        self.label(box,'Discovery state is saved. The next build resumes newly found mathematical topics automatically.',
                   note=True,wraplength=345).pack(anchor='w',pady=(7,4))
        ttk.Checkbutton(box,text='Follow Wikipedia References (DOI / arXiv / Title)',
                        variable=self.wiki_references_mode,
                        style='Dark.TCheckbutton').pack(anchor='w',pady=(8,3))
        ttk.Checkbutton(box,text='Read Open-Access PDFs When Available (slower)',variable=self.pdf_mode,
                        style='Dark.TCheckbutton').pack(anchor='w',pady=(9,6))
        self.label(box,'Optional OpenAlex API key (set BRAIN_USE_OPENALEX=1 to enable)',note=True).pack(anchor='w')
        self.api_key=ttk.Entry(box,show='•',style='Dark.TEntry')
        initial_key=env_openalex_api_key()
        if initial_key:
            self.api_key.insert(0, initial_key)
        self.api_key.pack(fill='x',pady=(4,4))
        if initial_key:
            self.label(box,'Optional API key detected (used only when BRAIN_USE_OPENALEX=1)',note=True).pack(anchor='w',pady=(0,8))
        else:
            self.label(box,'No OpenAlex key needed for the default arXiv and Crossref sources.',note=True).pack(anchor='w',pady=(0,8))
        self.catalog_status=tk.StringVar(value=f'Offline literature index: {local_catalog_count():,} papers')
        self.math_quality_status=tk.StringVar(value='Quality screening ready. New concepts are scored, and unambiguous noise is cleaned in batches.')
        self.label(box,'',textvariable=self.math_quality_status,note=True,wraplength=345).pack(anchor='w',pady=(5,2))
        ttk.Button(box,text='Math Memory Quality Report',style='Dark.TButton',
                   command=self.show_quality_report).pack_forget()
        self.label(box,'Sources: Wikipedia, arXiv, Crossref, OpenAIRE, DBLP, Europe PMC, local catalog; optional OpenAlex and Semantic Scholar. Math relevance is screened before PDF retrieval.',note=True).pack(anchor='w',pady=(6,2))
        ttk.Button(box,text='Import OpenAlex Public Works JSONL/GZ Snapshot',
                   command=self.import_local_snapshot,style='Dark.TButton').pack(fill='x',pady=2)
        self.label(box,'Shared mathematics literature index: ~/.local/share/brain_project/literature_catalog.sqlite3 (automatically updated)',note=True).pack(anchor='w')
        self.label(box,'The offline index contains only imported/downloaded records; full text is not guaranteed.',note=True).pack(anchor='w')
        tk.Label(box,textvariable=self.catalog_status,bg=self.PANEL,fg=self.MUTED,
                 anchor='w').pack(fill='x',pady=(1,5))
        self.run_btn=ttk.Button(box,text='Start Building (Literature → FLIN)',style='Accent.TButton',command=self.start)
        self.run_btn.pack(fill='x')
        self.retry_btn=ttk.Button(box,text='Retry Previously Failed Topics (keep network)',
              style='Dark.TButton',command=lambda:self.start(retry_failed_only=True))
        self.retry_btn.pack(fill='x',pady=(6,2))
        self.wikiref_btn=ttk.Button(box,text='Rescan Wikipedia Citations for Saved Topics',
              style='Dark.TButton',command=lambda:self.start(references_only=True))
        self.wikiref_btn.pack(fill='x',pady=(5,2))
        row=self._row(box)
        self.pause_btn=ttk.Button(row,text='Pause',style='Dark.TButton',command=self.toggle_pause,state='disabled')
        self.pause_btn.pack(side='left',fill='x',expand=True,padx=(0,4))
        self.stop_btn=ttk.Button(row,text='Stop and Save',style='Dark.TButton',command=self.stop,state='disabled')
        self.stop_btn.pack(side='left',fill='x',expand=True)
        row=self._row(box)
        ttk.Button(row,text='Check Source Connectivity',command=self.check_connections,style='Dark.TButton').pack(
            side='left',fill='x',expand=True,padx=(0,4))
        ttk.Button(row,text='Save Snapshot',command=self.save_snapshot,style='Dark.TButton').pack(
            side='left',fill='x',expand=True)
        ttk.Button(box,text='Export Complete Network',
                   command=self.open_export_dialog,style='Accent.TButton').pack(fill='x',pady=(7,2))
        self.delete_btn=ttk.Button(box,text='Erase Current FLIN Network (irreversible)...',style='Danger.TButton',command=self.delete_network)
        self.delete_btn.pack(fill='x',pady=(6,0))
        self.pipeline_title=tk.StringVar(value='Ready')
        self.pipeline_detail=tk.StringVar(value='Collection has not started.')
        self.pipeline_percentage=tk.DoubleVar(value=0)
        self.label(box,'',textvariable=self.pipeline_title,note=True,wraplength=350).pack(anchor='w',pady=(9,1))
        self.label(box,'',textvariable=self.pipeline_detail,note=True,wraplength=350).pack(anchor='w')
        ttk.Progressbar(box,maximum=100,variable=self.pipeline_percentage).pack(fill='x',pady=(6,0))

        row=self._row(inside)
        row.pack_forget()  # old-graph repair/playback tools cannot mutate ABC data

        self.logline=tk.StringVar(value='Each finished paper is automatically saved to SQLite.')
        self.label(inside,'',note=True,textvariable=self.logline,wraplength=350).pack(anchor='w',pady=(7,0))

        # Compatibility fields for v6 background collectors and old DB migrations.
        self.filter_var=tk.StringVar(value=' All ')
        self.max_nodes=tk.StringVar(value=str(FAST_OVERVIEW_NODES))
        hidden=ttk.Frame(self.root,style='Side.TFrame')  # intentionally not packed
        self.filter_box=ttk.Combobox(hidden,values=[' All '])
        self.theory_states=ttk.Treeview(hidden,columns=('theory','state','papers'))
        self.test_locked_label=ttk.Label(hidden,text='')
        self.repair_status=tk.StringVar(value='Legacy graph not yet audited')
        self.repair_btn=ttk.Button(hidden,command=self.repair_network)
        self.math_repair_btn=ttk.Button(hidden,command=self.repair_math_relations)
        self.timeline_latest=0
        self.timeline_cursor=0
        self.timeline_live=True
        self._updating_timeline=False
        self.timeline_scale=ttk.Scale(hidden,from_=0,to=1)
        self.step_info=tk.StringVar(value='0 / 0  steps ')
        self.step_description=tk.StringVar(value='')
        self.log_text=tk.Text(hidden,height=10,state='disabled')
        self.focus_ids=set()
        self._focus_result_ids=[]
        self.question_windows={}
        self.iteration_jobs={}
        self.review_started={}
        self.review_activity={}
        self.generating_sets=set()
        self.generation_activity={}
        self.generation_jobs={}
        self.generation_started={}
        self.review_prompts={}
        self.append_log('GUI ready: interactive sampled overview; search retrieves associations from the complete database.')

    def abc_refresh_status(self):
        try:
            with database() as con:status=abc_status(con)
            flag='FLIN is enabled' if status['enabled'] else 'FLIN not enabled (legacy read-only)'
            self.abc_status_var.set(f"{flag} | triggerable memories {status['active']:,} | input clusters {status['input_clusters']:,}"
                                    f" | directed links {status['edges']:,} | sources {status['learned_sources']:,}")
        except Exception as exc:
            self.abc_status_var.set('FLIN  Status cannot obtain :'+str(exc)[:140])

    def abc_show_input_clusters(self):
        win=tk.Toplevel(self.root)
        win.title('FLIN | Source-Grounded Effective Input Clusters')
        win.geometry('900x590')
        win.configure(bg=self.BG)
        box=ttk.Frame(win,style='Dark.TFrame',padding=12);box.pack(fill='both',expand=True)
        self.label(box,' each group retain Source original sentence and its shared appear mathematical features ;'
                       ' Keyword lists are not automatically considered  FLIN  Link .',note=True).pack(anchor='w')
        text=tk.Text(box,wrap='word',bg='#101b2b',fg='#dfeaff',
                     font=('Noto Sans CJK TC',10),padx=10,pady=9)
        bar=ttk.Scrollbar(box,orient='vertical',command=text.yview)
        text.configure(yscrollcommand=bar.set)
        bar.pack(side='right',fill='y');text.pack(fill='both',expand=True,pady=(8,0))
        try:
            with database() as con:
                rows=abc_recent_input_clusters(con,40)
                status=abc_status(con)
            lines=[f'Online input clusters: {status["input_clusters"]:,}  clusters |'
                   f' pending strengthening Link :{status["pending_replay"]:,}  clusters \n']
            for j,r in enumerate(rows,1):
                lines.extend([f'[{j}]  Source :{r["paper_id"]}',
                    'Mathematical features:'+'、'.join(r['features']),
                    'Original passage:'+r['quote'], 'URL:'+r['url'],''])
            if not rows:
                lines.append('No input clusters available. Start building or replay saved papers.')
            text.insert('1.0','\n'.join(lines))
        except Exception as exc:
            text.insert('1.0',' read Input cluster Failed :'+str(exc))
        text.configure(state='disabled')

    def abc_create_network(self):
        if self._network_switch_allowed():
            messagebox.showwarning('Stop Background Work First','Stop building, reviewing, importing, and simulating before this operation.',parent=self.root)
            return
        if not messagebox.askyesno('Create a Separate FLIN Network',
            'Create a new isolated mathematics network; existing databases and indexes will be retained.\n'
            'New sources undergo mathematics screening before FLIN learning. Continue?',parent=self.root):
            return
        try:
            name='FLIN_Mathematics_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            netid=create_empty_network(name,activate=False,domain='mathematics')
            if not self._activate_network(netid):return
            with database() as con:abc_enable(con)
            self.abc_refresh_status()
            messagebox.showinfo('Created','Switched to '+name+'.\nYou can now click Start Building to collect mathematical literature.',parent=self.root)
        except Exception as exc:
            messagebox.showerror('Creation Failed',str(exc),parent=self.root)

    def abc_learn_existing(self):
        if self.abc_worker_active or (self.collector and self.collector.is_alive()):
            messagebox.showwarning('Please Wait','Wait until the current background job finishes.',parent=self.root);return
        with database() as con:
            if not abc_enabled(con):
                messagebox.showinfo('Not Enabled','Create or activate a FLIN network first.',parent=self.root);return
        self.abc_worker_active=True
        self.abc_activity.set('Replaying saved papers into SSRS input clusters (150 papers per batch)...')
        def work():
            try:
                with database() as con:res=abc_backfill(con,limit=150)
                self.events.put(('abc_backfill_done',res))
            except Exception as exc:self.events.put(('abc_worker_error',str(exc)))
        self._start_background_thread(target=work, name='FLIN_backfill')

    def flin_ui_retrofit(self):
        if self.abc_worker_active or (self.collector and self.collector.is_alive()):
            messagebox.showwarning('Busy',
                'Stop network building or pulse simulation before reevaluating existing inputs.',
                parent=self.root)
            return
        self.abc_worker_active=True
        self.abc_activity.set('Evaluating association costs for up to 1,000 saved input clusters...')
        def work():
            try:
                with database() as con:
                    result=flin_retrofit_history(con,1000)
                self.events.put(('flin_cost_retrofit_done',result))
            except Exception as exc:
                self.events.put(('abc_worker_error',str(exc)))
        self._start_background_thread(target=work,name='FLIN_cost_retrofit')

    def flin_ui_cost_report(self):
        try:
            with database() as con:
                report=flin_efficiency_report(con)
            window=tk.Toplevel(self.root)
            window.title('FLIN | Association Cost and Shortcut Memories')
            window.geometry('850x580')
            display=tk.Text(window,wrap='word',font=('DejaVu Sans Mono',10),
                            bg=self.FIELD,fg=self.FG)
            display.pack(fill='both',expand=True,padx=12,pady=12)
            display.insert('1.0',json.dumps(report,ensure_ascii=False,indent=2))
            display.configure(state='disabled')
        except Exception as exc:
            messagebox.showerror('Cost report failed',str(exc),parent=self.root)

    def flin_start_bridge_explorer(self):
        """Launch an observation-only multi-entry experiment off the Tk thread."""
        if getattr(self,'bridge_active',False):
            messagebox.showinfo('Related Concepts','Concept search is already running.',parent=self.root)
            return
        terms=self.bridge_terms.get().strip()
        try:
            pulses=int(self.bridge_pulses.get())
            if not (20<=pulses<=4000):raise ValueError
        except (ValueError,tk.TclError):
            messagebox.showerror('Invalid pulse count','Use 20–4000 paths per input.',parent=self.root)
            return
        if not terms:
            messagebox.showinfo('Related Concepts',
                'Enter one or more established memory labels, separated by commas.',parent=self.root)
            return
        self.bridge_active=True
        self.bridge_status.set('Sampling existing directed association paths…')
        self.bridge_button.configure(state='disabled')
        # This is a read-only SQLite connection: no new learning run, no changes
        # to abc_edges or abc_positions and no external language model calls.
        def work():
            try:
                with contextlib.closing(_read_only_database()) as con:
                    con.execute('BEGIN')  # one consistent DB snapshot
                    result=flin_bridge_explore(con,terms,
                          pulses_per_gate=pulses,max_steps=14,
                          random_seed=42,result_limit=60,frontier_limit=200,
                          progress=lambda g,n,done,total:self.events.put(
                              ('flin_bridge_progress',(g,n,done,total))))
                    con.rollback()
                self.events.put(('flin_bridge_done',result))
            except Exception as exc:
                self.events.put(('flin_bridge_error',type(exc).__name__+': '+str(exc)))
        thread=self._start_background_thread(target=work,name='FLIN_Related_Concepts')
        if thread is None:
            self.bridge_active=False
            self.bridge_button.configure(state='normal')

    def flin_show_related_results(self, report):
        """Display many actually reached concepts, not generated research questions.

        Each item reports the independent input(s) whose weighted walks reached
        it and a sampled real route. No inferred edge or source claim is made.
        """
        win=tk.Toplevel(self.root)
        win.title('FLIN | Related Concepts')
        win.geometry('1060x745');win.configure(bg=self.BG)
        self.label(win,'RELATED CONCEPTS — observations from FLIN associative memory').pack(
            anchor='w',padx=12,pady=(12,4))
        raw={}
        for landscape in report['concept_landscapes']:
            for rec in landscape['concepts']:
                dst=raw.setdefault(rec['id'],{'id':rec['id'],'label':rec['label'],
                                              'observations':[]})
                dst['observations'].append({**rec,'input':landscape['input']})
        items=list(raw.values())
        # Overlap is useful, but a concept reached by just one input must not be
        # hidden. Unlike a top-10 ranker, include up to 120+ concepts PER input.
        items.sort(key=lambda r:(-len(r['observations']),
                    -sum(o['pulse_reach'] for o in r['observations']),
                    min(o['observed_depth'] for o in r['observations']),
                    r['label'].casefold()))
        self.label(win,
            f"{len(items):,} different related memories | "
            f"{len(report['inputs'])} input(s) | "
            f"{report['parameters']['pulses_per_gate']} sampled paths per input | "
            f"{report['statistics']['visited_units']:,} observed memories in total",
            note=True).pack(anchor='w',padx=12,pady=(0,4))
        self.label(win,'Unobserved is not unrelated. Rows are sampled associations, not new logical or mathematical facts.',
            note=True).pack(anchor='w',padx=12,pady=(0,7))
        frame=ttk.Frame(win,style='Dark.TFrame',padding=8)
        frame.pack(fill='both',expand=True,padx=10)
        panes=tk.PanedWindow(frame,orient='vertical',sashwidth=5,bg=self.BG)
        panes.pack(fill='both',expand=True)
        top=ttk.Frame(panes,style='Dark.TFrame')
        lower=ttk.Frame(panes,style='Dark.TFrame')
        panes.add(top,height=425,minsize=180);panes.add(lower,minsize=125)
        columns=('label','gate_count','inputs','reach','depth')
        table=ttk.Treeview(top,columns=columns,show='headings',selectmode='browse')
        for key,title,width in [
            ('label','Related memory',330),('gate_count','Inputs',60),
            ('inputs','Reached from',290),('reach','Best reach rate',125),
            ('depth','Shortest observed depth',170)]:
            table.heading(key,text=title)
            table.column(key,width=width,stretch=(key in ('label','inputs')))
        sb=ttk.Scrollbar(top,orient='vertical',command=table.yview)
        table.configure(yscrollcommand=sb.set)
        table.pack(side='left',fill='both',expand=True)
        sb.pack(side='right',fill='y')
        for i,rec in enumerate(items):
            observations=rec['observations']
            table.insert('','end',iid=str(i),values=(rec['label'],
                len(observations),', '.join(o['input'] for o in observations),
                f"{max(o['pulse_reach'] for o in observations):.1%}",
                min(o['observed_depth'] for o in observations)))
        detail=tk.Text(lower,wrap='word',height=10,font=('DejaVu Sans Mono',10),
               bg=self.FIELD,fg=self.FG,insertbackground=self.FG,relief='flat')
        ds=ttk.Scrollbar(lower,orient='vertical',command=detail.yview)
        detail.configure(yscrollcommand=ds.set)
        detail.pack(side='left',fill='both',expand=True)
        ds.pack(side='right',fill='y')
        # Labels are resolved by ID, not guessed from graph layout or LLM.
        ids={uid for rec in items for o in rec['observations'] for uid in o['path']}
        labels={g['id']:g['label'] for g in report['inputs']}
        if ids:
            with contextlib.closing(_read_only_database()) as con:
                ordered=sorted(ids)
                for start in range(0,len(ordered),350):
                    part=ordered[start:start+350]
                    for uid,label in con.execute('SELECT id,label FROM abc_units WHERE id IN ('+
                        ','.join('?'*len(part))+')',part):
                        labels[uid]=label
        def show(_event=None):
            selection=table.selection()
            if not selection:return
            item=items[int(selection[0])]
            lines=['MEMORY: '+item['label'],
                   'This is an observed FLIN association, not a mathematical conclusion.','']
            for o in item['observations']:
                route='  →  '.join(labels.get(uid,uid) for uid in o['path'])
                lines.extend([f"INPUT: {o['input']}",
                    f"Pulse reach: {o['pulse_reach']:.2%} | "
                    f"Mean first depth: {o['observed_depth']}",
                    'Sampled real path: '+route,''])
            detail.configure(state='normal')
            detail.delete('1.0','end');detail.insert('1.0','\n'.join(lines))
            detail.configure(state='disabled')
        table.bind('<<TreeviewSelect>>',show)
        if items:
            table.selection_set('0');table.focus('0');show()
        else:
            detail.insert('1.0','No other memory was reached from these input concepts. '
                'The stored graph may have no eligible outgoing links. '
                'Try a different triggerable memory or build more source-grounded links.')
            detail.configure(state='disabled')
        def save():
            dest=filedialog.asksaveasfilename(parent=win,title='Save related concepts',
                    defaultextension='.json',filetypes=[('JSON','*.json')],
                    initialfile='flin_related_concepts.json')
            if not dest:return
            payload={'kind':'flin_related_concepts_v1','inputs':report['inputs'],
                'parameters':report['parameters'],'observed_memories':items,
                'total_observed':report['statistics']['visited_units'],
                'note':'Read-only, sampled directed associative paths. Not a mathematical implication.'}
            try:
                Path(dest).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
                messagebox.showinfo('Saved','Associated concepts saved as JSON.',parent=win)
            except OSError as exc:
                messagebox.showerror('Export failed',str(exc),parent=win)
        foot=ttk.Frame(win,style='Dark.TFrame',padding=8);foot.pack(fill='x')
        ttk.Button(foot,text='Export Concept List',command=save,
                   style='Accent.TButton').pack(side='right')
        win.protocol('WM_DELETE_WINDOW',win.destroy)

    def flin_show_bridge_results(self,report):
        """Readable, traceable research results. No claim of mathematical proof."""
        win=tk.Toplevel(self.root)
        win.title('FLIN | Knowledge Bridge Explorer — Evidence & Paths')
        win.geometry('1160x770');win.configure(bg=self.BG)
        self.label(win,'FLIN KNOWLEDGE BRIDGES — shared reachability and linked frontiers').pack(
            anchor='w',padx=12,pady=(9,3))
        st=report['statistics']
        self.label(win,('Observed '+str(st['visited_units'])+' distinct memories · '+
              str(st['shared_memories'])+' shared meeting points · '+
              str(st['frontier_connection_candidates'])+' linked frontier pairs · '+
              str(report['parameters']['pulses_per_gate'])+' pulses per input.'),
              note=True).pack(anchor='w',padx=12,pady=(0,4))
        self.label(win,'Results are sampled associative paths. A bridge is a research hint, NOT a mathematical proof.',
            note=True).pack(anchor='w',padx=12,pady=(0,8))
        notebook=ttk.Notebook(win);notebook.pack(fill='both',expand=True,padx=10,pady=4)
        evidence_panel=ttk.Frame(notebook,style='Dark.TFrame')
        context_panel=ttk.Frame(notebook,style='Dark.TFrame')
        notebook.add(evidence_panel,text='Bridge Candidates & Path Evidence')
        notebook.add(context_panel,text='Broader Concept Landscape')
        split=tk.PanedWindow(evidence_panel,orient='vertical',sashwidth=5,bg=self.BG)
        split.pack(fill='both',expand=True)
        upper=ttk.Frame(split,style='Dark.TFrame')
        bottom=ttk.Frame(split,style='Dark.TFrame')
        split.add(upper,minsize=140,height=310)
        split.add(bottom,minsize=200)
        cols=('kind','label','coverage','score','sources')
        tree=ttk.Treeview(upper,columns=cols,show='headings',height=10)
        for key,title,width in [('kind','Kind',122),('label','Observed bridge / connection',500),
                                ('coverage','Inputs',70),('score','Bridge index',100),
                                ('sources','Path sources',110)]:
            tree.heading(key,text=title);tree.column(key,width=width,stretch=key=='label')
        vertical=ttk.Scrollbar(upper,orient='vertical',command=tree.yview)
        tree.configure(yscrollcommand=vertical.set)
        tree.pack(side='left',fill='both',expand=True);vertical.pack(side='right',fill='y')
        entries=report['bridges']+report['frontier_connections']
        for idx,item in enumerate(entries):
            tree.insert('','end',iid=str(idx),values=(
                'Shared memory' if item['type']=='shared_memory' else 'Frontier edge',
                item['label'][:135],str(item['coverage'])+'/'+str(len(report['inputs'])),
                f"{item['score']:.5f}",item.get('independent_sources_in_displayed_paths',0)))
        info=tk.Text(bottom,wrap='word',font=('DejaVu Sans Mono',10),
                 bg=self.FIELD,fg=self.FG,insertbackground=self.FG,
                 relief='flat')
        scroll=ttk.Scrollbar(bottom,orient='vertical',command=info.yview)
        info.configure(yscrollcommand=scroll.set)
        info.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        def inspect(_=None):
            selection=tree.selection()
            if not selection:return
            item=entries[int(selection[0])]
            lines=['CANDIDATE — '+item['label'],
                   'Type: '+item['type']+' | Observation index: '+str(item['score']),
                   'Supported independent input routes: '+str(item['coverage'])+'/'+str(len(report['inputs'])),
                   'Source identifiers in displayed path evidence: '+str(
                       item.get('independent_sources_in_displayed_paths',0)),
                   'Note: paths are observed samples; frequency is not semantic truth.','']
            for stat in item.get('gate_stats',[]):
                if stat['hits']:
                    lines.append('%s: %d/%d paths (%.2f%%), mean depth %.2f'%(
                        stat['input'],stat['hits'],report['parameters']['pulses_per_gate'],
                        stat['probability']*100,stat['mean_first_depth']))
            for trace in item['traces']:
                lines+=['','INPUT: '+trace['input'],'  →  '.join(n['label'] for n in trace['nodes'])]
                for edge in trace['edges']:
                    if edge['evidence']:
                        for source in edge['evidence']:
                            lines.append('  SOURCE: '+(source['title'] or source['source_id']))
                            lines.append('  '+source['quote'][:280])
                            if source['url']:lines.append('  '+source['url'])
                    else:
                        lines.append('  EDGE: '+edge['src_label']+' → '+edge['dst_label']+
                                     ' [recorded link; no matching input-cluster evidence found]')
            if item['type']=='frontier_edge':
                edge=item['connecting_edge']
                lines+=['','FRONTIER JOIN: '+item['label'],
                        'This directed link exists in abc_edges, but neither entire'
                        ' cross-input route is claimed to have been sampled as one pulse.',
                        'Weight: '+str(edge['weight'])]
                for source in edge['evidence']:
                    lines.append('  SUPPORT: '+(source['title'] or source['source_id'])+
                                 ' — '+source['quote'][:280])
            lines+=['','Interpretation: Candidate for further comparison and research, '
                    'NOT an inferred theorem, causality, or equivalence.']
            info.configure(state='normal');info.delete('1.0','end')
            info.insert('1.0','\n'.join(lines));info.configure(state='disabled')
        tree.bind('<<TreeviewSelect>>',inspect)
        if entries:
            tree.selection_set('0');inspect()
        else:
            info.insert('1.0','No meeting nodes or joined frontiers were observed. '\
                'Inspect the Concept Landscape tab, add relevant established inputs, '\
                'or increase the pulse count. No cross-domain relationship is invented.')
            info.configure(state='disabled')
        context=tk.Text(context_panel,wrap='word',font=('DejaVu Sans Mono',10),
                        bg=self.FIELD,fg=self.FG)
        context.pack(fill='both',expand=True,padx=5,pady=5)
        for landscape in report['concept_landscapes']:
            context.insert('end','\nINPUT '+landscape['input']+'  ['+landscape['gate']+']\n')
            context.insert('end','Observed '+str(landscape['count'])+' reachable other memories. '\
                                'Balanced short-, long- and low-degree paths:\n\n')
            for row in landscape['concepts']:
                context.insert('end',f" • {row['label']} | reach {row['pulse_reach']:.1%} "
                                      f"| depth {row['observed_depth']} | in-degree {row['incoming_degree']}\n")
            context.insert('end','\n')
        context.configure(state='disabled')
        foot=ttk.Frame(win,style='Dark.TFrame',padding=8);foot.pack(fill='x')
        def save():
            dest=filedialog.asksaveasfilename(parent=win,title='Save FLIN Bridge Evidence',
                     defaultextension='.json',filetypes=[('JSON','*.json')],
                     initialfile='flin_knowledge_bridges.json')
            if not dest:return
            try:
                Path(dest).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                messagebox.showinfo('Saved','The full exploration report is saved.',parent=win)
            except OSError as exc:
                messagebox.showerror('Save failed',str(exc),parent=win)
        ttk.Button(foot,text='Export Full JSON with Paths & Evidence',command=save,
                   style='Accent.TButton').pack(side='right')
        ttk.Button(foot,text='View Bridge Paths in 3D',
                   command=lambda:self.flin_show_bridge_graph(report),
                   style='Dark.TButton').pack(side='left')

    def flin_show_bridge_graph(self,report):
        """Bounded 3D illustration of real sampled path edges (not a new graph)."""
        entries=report['bridges'][:20]+report['frontier_connections'][:10]
        graph=nx.DiGraph();gate_ids={g['id'] for g in report['inputs']}
        edge_weights={}
        for item in entries:
            for path in item.get('paths',{}).values():
                for node in path:graph.add_node(node)
                for a,b in zip(path,path[1:]):
                    graph.add_edge(a,b)
            if item['type']=='frontier_edge':
                graph.add_edge(item['source_id'],item['target_id'])
        if not graph.nodes:
            messagebox.showinfo('No bridge paths','No bridge paths to show yet.',parent=self.root)
            return
        # This graph intentionally shows only reported routes. No implied edges.
        ids=list(graph.nodes)
        with contextlib.closing(_read_only_database()) as con:
            names={uid:label for uid,label in con.execute('SELECT id,label FROM abc_units '
                  'WHERE id IN ('+','.join('?'*len(ids))+')',ids)}
            for a,b in graph.edges:
                row=con.execute('SELECT weight FROM abc_edges WHERE src=? AND dst=?',(a,b)).fetchone()
                edge_weights[(a,b)]=float(row[0]) if row else 0.0
        win=tk.Toplevel(self.root);win.title('FLIN | Observed Knowledge Bridge Paths (3D)')
        win.geometry('1050x750');win.configure(bg=self.BG)
        fig=plt.figure(figsize=(11,8));ax=fig.add_subplot(111,projection='3d')
        pos=nx.spring_layout(graph,dim=3,seed=19,iterations=85,
                             weight=None)
        for a,b in graph.edges:
            x,y=pos[a],pos[b]
            ax.plot([x[0],y[0]],[x[1],y[1]],[x[2],y[2]],
                    color='#6383a4',linewidth=.5+.35*min(8,edge_weights[(a,b)]),alpha=.65)
        for uid in ids:
            x,y,z=pos[uid]
            main=uid in gate_ids
            ax.scatter([x],[y],[z],s=65 if main else 17,
                       c=['#e87340' if main else '#68a5d8'])
            if main or len(ids)<45:
                ax.text(x,y,z,names.get(uid,uid)[:22],fontsize=7)
        ax.set_title('Recorded directed paths only · geometry is visualization, not a learned coordinate')
        fig.tight_layout()
        canvas=FigureCanvasTkAgg(fig,master=win);canvas.draw()
        toolbar=NavigationToolbar2Tk(canvas,win,pack_toolbar=False)
        toolbar.update();toolbar.pack(side='bottom',fill='x')
        canvas.get_tk_widget().pack(fill='both',expand=True)
        win.protocol('WM_DELETE_WINDOW',lambda:(plt.close(fig),win.destroy()))


    def abc_start_simulation(self):
        if self.abc_worker_active:
            messagebox.showinfo('Simulation in Progress','Wait for the previous FLIN task.',parent=self.root);return
        query=self.abc_input.get().strip()
        if not query:
            messagebox.showinfo('Enter a Memory Unit','For example: eigenvalue, matrix',parent=self.root);return
        try:
            rate=float(self.abc_rate.get());duration=float(self.abc_duration.get())
            threshold=float(self.abc_threshold.get())
        except (ValueError,tk.TclError):
            messagebox.showerror('Invalid Number','Rate, duration, and threshold must be valid numbers.',parent=self.root);return
        self.abc_worker_active=True
        self.abc_activity.set('Supplying pulses, following SSRS routes, measuring time-varying responses...')
        def work():
            try:
                with database() as con:
                    if not abc_enabled(con):raise ValueError('FLIN learning has not been enabled for this network.')
                    response=abc_simulate(con,query,pulse_hz=rate,
                        input_duration=duration,frequency_threshold=threshold)
                    associated=abc_save_as_association(con,response)
                self.events.put(('abc_simulation_done',(response,associated)))
            except Exception as exc:self.events.put(('abc_worker_error',str(exc)))
        self._start_background_thread(target=work, name='FLIN_pulse')

    def abc_show_response(self,result,associated):
        win=tk.Toplevel(self.root);win.title('FLIN Response Distribution | Above Threshold')
        win.geometry('930x650');win.configure(bg=self.BG)
        header=ttk.Frame(win,style='Dark.TFrame',padding=12);header.pack(fill='x')
        self.label(header,'FLIN | Time Response C → Threshold → Mean B → Distribution').pack(anchor='w')
        self.label(header,' route selection : Weighted proportional sampling ( one pulses Pulse select one route only );'
                   f" multiple present seed  {result['settings'].get('random_seed')}",note=True).pack(anchor='w')
        self.label(header,f" continuous Supply  {result['input_pulses']}  pulses | activation  {result['activated_count']}  units |"
                          f" above threshold  {result['visible_count']}  units | feedback  {result['feedback_count']}  items ",
                   note=True).pack(anchor='w')
        content=ttk.Frame(win,style='Dark.TFrame',padding=8);content.pack(fill='both',expand=True)
        table=ttk.Treeview(content,columns=('label','freq','ratio','visits'),show='headings',height=16)
        for key,title,width in [('label','Memory Unit',330),('freq','Time-averaged visible frequency (Hz)',180),
                                ('ratio','Response proportion',120),('visits','Actual activation count',120)]:
            table.heading(key,text=title);table.column(key,width=width)
        table.pack(fill='both',expand=True)
        for row in result['distribution']:
            table.insert('','end',values=(row['label'],round(row['visible_average_hz'],4),
                                           f"{row['proportion']:.2%}",row['visits']))
        buttons=ttk.Frame(win,style='Dark.TFrame',padding=9);buttons.pack(fill='x')
        ttk.Button(buttons,text='Show 3D FLIN Subnetwork',style='Dark.TButton',
                   command=lambda:self.abc_show_graph(result)).pack(side='left',padx=4)
        ttk.Button(buttons,text='View Full Response Curves',style='Dark.TButton',
                   command=lambda:self.abc_show_curves(result)).pack(side='left',padx=4)
        self.label(win,'Associative response is evidence of network reachability, not mathematical proof.',
                   note=True).pack(anchor='w',padx=13,pady=4)

    def abc_show_graph(self,result=None):
        """Interactive 3D preview of TRUE FLIN associative edges; no source hubs."""
        result=result or {'distribution':[]}
        highlighted={v['id']:v['visible_average_hz'] for v in result['distribution']}
        with database() as con:
            if highlighted:
                ids=list(highlighted)[:170]
                rows=con.execute('SELECT id,label FROM abc_units WHERE id IN ('+
                                 ','.join('?'*len(ids))+') AND status=\'active\'',ids).fetchall()
            else:
                rows=con.execute('SELECT id,label FROM abc_units WHERE status=\'active\' '
                                 'ORDER BY evidence_count DESC,id LIMIT 140').fetchall()
                ids=[r[0] for r in rows]
            if not rows:
                messagebox.showinfo('FLIN 3D','There are no source-grounded FLIN memory units yet.',parent=self.root)
                return
            ids=[r[0] for r in rows]
            links=con.execute('SELECT src,dst,weight FROM abc_edges WHERE src IN ('+
                              ','.join('?'*len(ids))+') AND dst IN ('+
                              ','.join('?'*len(ids))+')',ids+ids).fetchall()
        graph=nx.DiGraph()
        graph.add_nodes_from((uid,{'label':label}) for uid,label in rows)
        graph.add_weighted_edges_from(links)
        # Layout is a VIZUALIZATION, not an actual impedance or time dimension.
        layout=nx.spring_layout(graph,dim=3,seed=42,weight='weight',iterations=50)
        win=tk.Toplevel(self.root);win.title('FLIN Directed Memory Network | 3D')
        win.geometry('1050x730');win.configure(bg=self.BG)
        fig=plt.figure(figsize=(10,7));axis=fig.add_subplot(111,projection='3d')
        max_signal=max(highlighted.values(),default=1.) or 1.
        for src,dst,weight in links[:700]:
            a,b=layout[src],layout[dst]
            axis.plot([a[0],b[0]],[a[1],b[1]],[a[2],b[2]],
                      linewidth=.2+.9*min(1.,weight/10.),alpha=.24)
        for uid,label in rows:
            x,y,z=layout[uid]
            strength=highlighted.get(uid,0.)/max_signal
            axis.scatter([x],[y],[z],s=10+65*strength,
                         c=[(1.,.35,.17)] if uid in highlighted else [(0.25,.50,.73)])
            if len(rows)<=28 or (strength>.3 and len(highlighted)<=22):
                axis.text(x,y,z,label[:28],fontsize=7)
        axis.set_title('FLIN directed learned links · observed reaction emphasized')
        fig.tight_layout()
        canvas=FigureCanvasTkAgg(fig,master=win);canvas.draw()
        toolbar=NavigationToolbar2Tk(canvas,win,pack_toolbar=False);toolbar.update()
        toolbar.pack(side='bottom',fill='x')
        canvas.get_tk_widget().pack(fill='both',expand=True)
        win.protocol('WM_DELETE_WINDOW',lambda:(plt.close(fig),win.destroy()))

    def abc_show_curves(self,result):
        win=tk.Toplevel(self.root);win.title('FLIN Memory Response Over Time')
        win.geometry('880x600');win.configure(bg=self.BG)
        fig,axis=plt.subplots(figsize=(9,5))
        for series in sorted(result['response_series'],
                             key=lambda v:sum(v['visible_hz']),reverse=True)[:12]:
            axis.plot(result['time_samples_s'],series['raw_hz'],alpha=.3)
            axis.plot(result['time_samples_s'],series['visible_hz'],label=series['label'][:40])
        axis.set_xlabel('simulated time (s)');axis.set_ylabel('pulse frequency (Hz)')
        axis.legend(loc='upper right',fontsize=7);fig.tight_layout()
        canvas=FigureCanvasTkAgg(fig,master=win);canvas.draw()
        canvas.get_tk_widget().pack(fill='both',expand=True)
        win.protocol('WM_DELETE_WINDOW',lambda:(plt.close(fig),win.destroy()))

    def _network_switch_allowed(self):
        reasons = []
        if getattr(self,'abc_worker_active',False):
            reasons.append('FLIN  Pulse simulation or Literature return fill still in run ')
        if self.collector is not None and self.collector.is_alive():
            reasons.append(' Background building /Wikipedia  Collect still in run ')
        if self._analysis_active:
            reasons.append(' association analysis still in run ')
        if getattr(self, 'generating_sets', set()) or getattr(self, 'generation_jobs', {}):
            reasons.append('ModelProcessing Generate Research question ')
        if getattr(self, 'iteration_jobs', {}):
            reasons.append('ModelProcessing performReview/ Revision ')
        if getattr(self, '_repair_active', False) or getattr(self, '_math_repair_active', False):
            reasons.append(' Background Index / research relationship Repair still in run ')
        if getattr(self, '_export_active', False):
            reasons.append(' Network Export Not yet Completed ')
        if getattr(self, '_network_import_active', False):
            reasons.append(' Network Import Not yet Completed ')
        if getattr(self, '_catalog_import_active', False):
            reasons.append(' local Literature Index Import in ')
        return reasons

    def _activate_network(self, network_id):
        reasons = self._network_switch_allowed()
        if reasons:
            messagebox.showwarning('Cannot Switch Network', 'Wait until the following operations finish:\n'+'\n'.join(reasons),
                                   parent=self.root)
            return False
        if active_network_record()['id'] == network_id:
            return True
        try:
            self.persist_positions()
            if self.replay_job is not None:
                self.root.after_cancel(self.replay_job)
                self.replay_job = None
            self.replaying = False
            record = switch_active_network(network_id)
            # Discard all view state, cached sizes and pending events belonging
            # to the previous database; never mix two graphs in one window.
            self.events = queue.Queue()
            self.coords = {}
            self.plot_data = {}
            self.chosen = None
            self.path = []
            self.focus_ids = set()
            self._focus_result_ids = []
            self._local_focus_ids = None
            self._stats_cache = None
            self.zoom = 1.0
            self.axis_xlim = None
            self._viewport_empty_reason = ' none yet Memory Unit'
            self.last_run_id = None
            self.active_theory = None
            self.timeline_cursor = 0
            self.timeline_latest = 0
            self.timeline_live = True
            self.worker_states = {}
            self.enqueued_theories = 0
            self.finished_theories = 0
            self.skipped_theories = 0
            self.success_theories = 0
            self.empty_theories = 0
            self.active_total = 0
            self.has_started = False
            self.search_var.set('')
            self.test_var.set('')
            self.search_hint.set('No active search')
            self.detail.configure(state='normal')
            self.detail.delete('1.0','end')
            self.detail.configure(state='disabled')
            self.pipeline_title.set('Ready')
            self.pipeline_detail.set('You can build or extend the selected network.')
            self.pipeline_percentage.set(0)
            self.graph_phase.set('Switched to: ' + record['name'])
            self.active_network_label.set(record['name'])
            self.active_domain_label.set('Build scope:'+domain_name())
            self.abc_refresh_status()
            self.abc_last_run_id=None;self.abc_last_association_id=None
            self.math_quality_status.set('Mathematics mode: pure mathematics and mathematical models across disciplines.')
            self.status.set('✓ Active network: ' + record['name'])
            self.update_worker_panel()
            for win in list(getattr(self, 'question_windows', {}).values()):
                try:
                    # Child windows must not keep references to another DB.
                    w = win.get('win') if isinstance(win, dict) else win
                    if w and w.winfo_exists():
                        w.destroy()
                except (tk.TclError, AttributeError):
                    pass
            self.question_windows.clear()
            for prompt in list(self.review_prompts.values()):
                try:
                    if prompt.winfo_exists():
                        prompt.destroy()
                except (tk.TclError, AttributeError):
                    pass
            self.review_prompts.clear()
            if self.results_window is not None:
                try:
                    if self.results_window.winfo_exists():
                        self.results_window.destroy()
                except tk.TclError:
                    pass
                self.results_window = None
            self.load_topics()
            self.refresh_history(reset=True)
            self.reload_network()
            self.append_log('Switched to network: ' + record['name'] + ', use  ' + str(DB_PATH))
            return True
        except Exception as exc:
            messagebox.showerror('Network Switch Failed', str(exc), parent=self.root)
            return False

    def open_math_coverage(self):
        """Inspect source-grounded math breadth without materializing the graph."""
        win=tk.Toplevel(self.root)
        win.title('Mathematics Memory Network — Branch Coverage')
        win.geometry('740x540')
        win.configure(bg=self.BG)
        view=tk.Text(win,wrap='word',bg='#111c2b',fg='#e2edff',
                     font=('DejaVu Sans Mono',10),relief='flat',padx=16,pady=15)
        view.pack(expand=True,fill='both',padx=12,pady=12)
        view.insert('1.0','Compiling paper and mathematics-branch statistics from the active network...\n')
        view.configure(state='disabled')
        messages=queue.Queue()
        active_path=Path(DB_PATH)
        def worker():
            try:
                with contextlib.closing(sqlite3.connect(str(active_path),timeout=30)) as con:
                    messages.put(('ok',mathematical_coverage_report(con)))
            except Exception as exc:
                messages.put(('error',str(exc)))
        self._start_background_thread(target=worker, name='math_coverage')
        def poll():
            if not win.winfo_exists():return
            try:kind,data=messages.get_nowait()
            except queue.Empty:
                win.after(130,poll);return
            if kind=='error':body=' Unable to read coverage Statistics :'+data
            else:
                lines=[f'Indexed research papers: {data["papers"]:,} papers',
                    f'Papers with explicit cross-disciplinary application tags: {data["tagged_papers"]:,} papers',
                    f'Papers without an application tag (including pure or unclassified mathematics): {data["untagged_including_pure_math"]:,} papers',
                    '', 'Pure and applied mathematics: seed-topic coverage']
                for branch,row in data['mathematical_seed_branches'].items():
                    lines.append(f'{branch:<27} {row["covered_seed_topics"]:>2}/{row["known_seed_topics"]:<2}  Topic ;'
                                 f' Paper － Topic Associations  {row["paper_topic_links"]:,}')
                lines+=['','Cross-disciplinary applications (explicit textual evidence)']
                for branch,total in data['application_areas'].items():
                    lines.append(f'{branch:<27} {total:,} papers')
                lines+=['',data['note'],
                        'This report only summarizes indexed material. It does not establish coverage of all mathematical knowledge.']
                body='\n'.join(lines)
            view.configure(state='normal');view.delete('1.0','end')
            view.insert('1.0',body);view.configure(state='disabled')
        win.after(130,poll)

    def open_network_manager(self):
        """Manage independent SQLite networks, safely stage imports in background."""
        win = tk.Toplevel(self.root)
        win.title('Brain_Project · Memory Network Manager')
        win.geometry('750x550')
        win.configure(bg=self.PANEL)
        win.transient(self.root)
        main = ttk.Frame(win, style='Side.TFrame', padding=18)
        main.pack(fill='both', expand=True)
        self.label(main, 'Independent Memory Network Databases', note=False).pack(anchor='w', pady=(0,5))
        self.label(main, 'Each network is stored separately. SQLite imports preserve question and activity histories; portable imports preserve exported graph records and provenance.',
                   note=True, wraplength=690).pack(anchor='w', pady=(0,10))
        columns=('active','name','domain','size','path')
        table=ttk.Treeview(main,columns=columns,show='headings',height=8,style='Dark.Treeview')
        for col,label,width in [('active',' Current ',65),('name','Network Name',210),
                                ('domain',' Domain ',115),('size',' size ',85),('path','Database Path',235)]:
            table.heading(col,text=label)
            table.column(col,width=width,stretch=(col in ('name','path')))
        table.pack(fill='both',expand=True)
        def update_list(select=None):
            table.delete(*table.get_children())
            registry=read_network_registry()
            for record,path in network_entries():
                exists=path.is_file()
                size=(f'{path.stat().st_size/1024**2:,.1f} MB' if exists else ' new build / lost ')
                table.insert('', 'end', iid=record['id'], values=(
                    '●' if record['id']==registry['active'] else '',
                    record['name'],DOMAIN_PROFILES.get(record.get('domain','mathematics'),DOMAIN_PROFILES['general'])['name'],size,str(path)))
            chosen=select or registry['active']
            if table.exists(chosen):
                table.selection_set(chosen)
                table.see(chosen)
        update_list()
        status=tk.StringVar(value=' can BuildEmpty Network, switch , or Import  JSONL.gz/SQLite  backup .')
        self.label(main,'',textvariable=status,note=True,wraplength=700).pack(anchor='w',pady=(10,4))
        self.label(main,' new build and Import Network average use ` all Domain Mathematics ` building rules ; legacy network history Domain Settings for identification only .',
                   note=True,wraplength=680).pack(anchor='w',pady=(3,8))
        pb=ttk.Progressbar(main,mode='determinate',maximum=100)
        pb.pack(fill='x',pady=(0,8))
        working={'busy': False, 'cancel':threading.Event()}
        messages=queue.Queue()
        buttons=ttk.Frame(main,style='Side.TFrame')
        buttons.pack(fill='x',pady=(5,0))

        def selection():
            selected=table.selection()
            if not selected:
                messagebox.showinfo('Select a Network','Choose a network from the list first.',parent=win)
                return None
            return selected[0]

        def activate():
            choice=selection()
            if choice and self._activate_network(choice):
                update_list(choice)
                status.set('✓  already switch current network , can Start building .')

        def fresh():
            reason=self._network_switch_allowed()
            if reason:
                messagebox.showwarning('Please Wait', '\n'.join(reason),parent=win)
                return
            name=simpledialog.askstring(' Build all new network ',' new network name :',
                initialvalue=' new Mathematics Memory Unit Network ',parent=win)
            if name is None:
                return
            try:
                record=create_empty_network(name,activate=False,domain='mathematics')
                update_list(record)
                status.set('✓ CreatedEmpty Network; select after click ` switch use ` exactly can Start reconstruct .')
                if messagebox.askyesno('Switch to the New Network?',
                        'Created new empty Database , legacy network Preserved .\n present in switch and Start new building work ? ?',parent=win):
                    if self._activate_network(record):
                        update_list(record)
            except Exception as exc:
                messagebox.showerror('Creation Failed',str(exc),parent=win)

        def import_as(mode):
            reasons=self._network_switch_allowed()
            if reasons:
                messagebox.showwarning('Cannot Import While Busy',' Please first Waiting work Completed :\n'+'\n'.join(reasons),parent=win)
                return
            if mode=='sqlite':
                source=filedialog.askopenfilename(parent=win,title=' choose complete  SQLite  Network backup ',
                    filetypes=[('SQLite network','*.sqlite3 *.sqlite *.db'),('All files','*')])
                # Selecting the directory holding exported association.sqlite3 is
                # also supported via the CLI function, but file picker is clearest.
            else:
                source=filedialog.askdirectory(parent=win,title=' choose includes  manifest.json   JSONL.gz  Export folder ')
            if not source:
                return
            name=simpledialog.askstring(' ImportNetwork Name',' give Import Network obtain items name :',
                initialvalue=Path(source).stem,parent=win)
            if name is None:
                return
            working['busy']=True
            self._network_import_active=True
            working['cancel'].clear()
            self._network_import_cancel_event = working['cancel']
            for button in action_buttons:
                button.configure(state='disabled')
            status.set(' Processing Import to Independent temporary store Database ...')
            def worker():
                try:
                    ident=import_network(source,name,activate=False,domain='mathematics',
                        stop_event=working['cancel'],
                        progress=lambda stage,done,total:messages.put(('progress',stage,done,total)))
                    messages.put(('done',ident))
                except NetworkImportCancelled as exc:
                    messages.put(('cancel',str(exc)))
                except Exception as exc:
                    messages.put(('error',type(exc).__name__+': '+str(exc)))
            self._start_background_thread(target=worker, name='brain_network_import')

        def close_or_cancel():
            if working['busy']:
                working['cancel'].set()
                status.set(' Processing cancel Import and cleanup temporary store Data ...')
                return
            win.destroy()

        for title,func in [('＋  new createEmpty Network',fresh),('▶  switch use ',activate),
                           ('⇩  Import  SQLite',lambda:import_as('sqlite')),
                           ('⇩  Import  JSONL.gz',lambda:import_as('portable'))]:
            b=ttk.Button(buttons,text=title,style='Accent.TButton',command=func)
            b.pack(side='left',padx=(0,5))
        action_buttons=[w for w in buttons.winfo_children() if isinstance(w,ttk.Button)]
        ttk.Button(main,text=' close / cancel Import ',style='Dark.TButton',
                   command=close_or_cancel).pack(fill='x',pady=(11,0))
        win.protocol('WM_DELETE_WINDOW',close_or_cancel)
        def pump():
            if not win.winfo_exists():
                return
            last=None
            try:
                while True:
                    item=messages.get_nowait()
                    if item[0]=='progress':
                        last=item
                    elif item[0] in ('done','error','cancel'):
                        working['busy']=False
                        self._network_import_active=False
                        for button in action_buttons:
                            button.configure(state='normal')
                        if item[0]=='done':
                            update_list(item[1])
                            pb.configure(value=100)
                            status.set('✓  Import Completed ; select after can switch use .')
                            if messagebox.askyesno('Import Successful','The imported network is stored in a separate SQLite database. Switch to it now?',parent=win):
                                self._activate_network(item[1])
                                update_list(item[1])
                        elif item[0]=='cancel':
                            status.set(item[1])
                        else:
                            status.set('✕ Import Failed:'+item[1])
                            messagebox.showerror('Import Failed',item[1],parent=win)
            except queue.Empty:
                pass
            if last is not None and working['busy']:
                _,label,done,total=last
                if total:
                    pb.configure(value=min(100,100*done/max(1,total)))
                    status.set(f'{label}: {done:,}/{total:,}  records or pages ')
                else:
                    status.set(label)
            win.after(220,pump)
        pump()

    def open_tools(self):
        win=tk.Toplevel(self.root);win.title('Brain_Project ·  maintain and Log ')
        win.geometry('850x620');win.configure(bg=self.BG)
        outer=ttk.Frame(win,style='Dark.TFrame',padding=14);outer.pack(fill='both',expand=True)
        row=ttk.Frame(outer,style='Dark.TFrame');row.pack(fill='x')
        ttk.Button(row,text=' Repair term form Index and Source Link ',command=self.repair_network,
                   style='Dark.TButton').pack(side='left',padx=(0,6))
        ttk.Button(row,text=' again scan old Paper research relationship ',command=self.repair_math_relations,
                   style='Dark.TButton').pack(side='left')
        ttk.Label(outer,textvariable=self.repair_status,style='Dark.TLabel',wraplength=795).pack(anchor='w',pady=8)
        row=ttk.Frame(outer,style='Dark.TFrame');row.pack(fill='x')
        ttk.Label(row,textvariable=self.step_info,style='Dark.TLabel').pack(side='left')
        for title,fn in [('◀',self.history_prev),('▶',self.history_next),
                         (' playback / pause ',self.history_play),(' All / latest ',self.history_live_view)]:
            ttk.Button(row,text=title,style='Dark.TButton',command=fn).pack(side='right',padx=3)
        ttk.Scale(outer,from_=0,to=max(1,self.timeline_latest),orient='horizontal',
                  command=self.history_seek).pack(fill='x',pady=7)
        ttk.Label(outer,textvariable=self.step_description,style='Dark.TLabel',wraplength=795).pack(anchor='w')
        ttk.Button(outer,text=' research Network Purity Check ( NOT delete old Node )',style='Dark.TButton',
                   command=self.show_quality_report).pack(anchor='w',pady=(8,2))
        ttk.Button(outer,text=' View history literature provider Failed Record ',style='Dark.TButton',
                   command=self.show_openalex_failures).pack(anchor='w',pady=(8,2))
        ttk.Button(outer,text=' review  Wikipedia  cited paper Verify and Import Record ',
                   style='Dark.TButton',command=self.show_wikipedia_citations).pack(anchor='w',pady=(6,2))
        ttk.Label(outer,text=' Collect and process Record ',style='Dark.TLabel').pack(anchor='w',pady=(10,4))
        # A log clone avoids stealing the hidden writer and retains live additions.
        log=tk.Text(outer,bg=self.FIELD,fg=self.FG,wrap='word',padx=12,pady=10,
                    relief='flat',font=('DejaVu Sans Mono',9),state='normal')
        log.pack(fill='both',expand=True)
        log.insert('1.0',self.log_text.get('1.0','end'));log.configure(state='disabled')
        def refresh_log():
            if not win.winfo_exists():return
            log.configure(state='normal');log.delete('1.0','end')
            log.insert('1.0',self.log_text.get('1.0','end'));log.configure(state='disabled')
            win.after(1400,refresh_log)
        refresh_log()
        def cleanup():
            win.destroy()
        win.protocol('WM_DELETE_WINDOW',cleanup)

    def show_quality_report(self):
        with database() as con:
            purity=purity_report(con)
            states=quality_counts(con)
            old=con.execute('SELECT state,COUNT(*) FROM unit_quality_audit GROUP BY state').fetchall()
            rejected=con.execute("SELECT theory,reason,COUNT(*) n FROM paper_quality_decisions "
                "WHERE state='rejected' GROUP BY theory,reason ORDER BY n DESC LIMIT 8").fetchall()
        mean=purity['mean_heuristic_score']
        admission=purity['admission_rate_pct']
        lines=[' all Mathematics Memory Unit Quality Report ( heuristic , NOT equivalent to actual Mathematics accuracy )',
               f"Created and pass passed concept / relationship threshold :{purity['approved_candidates']:,}",
               f" already reject Memory Unit Candidate :{purity['rejected_candidates']:,}",
               f" New Candidate adoption rate :{admission if admission is not None else ' none yet Data '}%",
               f" already accept Node Average heuristic score :{mean if mean is not None else ' none yet Data '} / 100",
               f" Existing network scan record count :{purity['old_units_scanned']:,}",
               f" already scan old concept acceptance rate :{purity['old_concept_pass_rate_pct'] if purity['old_concept_pass_rate_pct'] is not None else ' not started '}%",
               f" already scan old concept Average heuristic score :{purity['old_concept_purity_score'] if purity['old_concept_purity_score'] is not None else ' not started '} / 100",
               f" clear noise already delete :{purity['deleted_noise_units']:,}",
               f" Mathematics Literature match accepted :{states.get('accepted',0):,}; rejected :{states.get('rejected',0):,}",
               f' old Memory Unit non-destructive Quality audit points :{dict(old)}',
               ' most frequently rejected Candidate term :']
        lines += [f'  {label[:38]}｜{reason}：{n:,}' for label,reason,n in purity['samples']]
        lines += [' Mathematics Literature common rejection reasons :']
        lines += [f'  {topic[:28]} | {reason}：{n:,}' for topic,reason,n in rejected]
        lines += ['', ' additional batch cleanup ( first backup and close  GUI):',
                  'python questioning.py --purity-clean --purity-limit 20000',
                  'python questioning.py --purity-report',
                  ' only delete Independent function term , academic redundancy term and short fragment ; ambiguous terminology NOT automatic delete .',
                  ' Source evidence and mathematics correctness still needs Independent Validate .']
        messagebox.showinfo('Memory Unit Quality Report','\n'.join(lines),parent=self.root)

    def focus_memory(self):
        """Zoom the viewport onto matched units but preserve all stored/visible units."""
        query=self.search_var.get().strip()
        if not query:return
        seeds=self._find_seed_nodes(query)
        if not seeds:
            self.search_hint.set(' not yet match to Memory Unit; can first Rebuild term form Index or Collect Literature .')
            return
        origins=[uid for uid,_,_,_ in seeds[:5]]
        keep=set(origins)
        with database() as con:
            indexed_back = bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='index' "
                                            "AND name='idx_edges_dst'").fetchone())
            for uid in origins:
                # Both directions: these are browse paths, not reverse implication.
                for (neighbour,) in con.execute('''SELECT dst FROM edges WHERE src=? ORDER BY weight DESC LIMIT 35''',(uid,)):
                    keep.add(neighbour)
                if indexed_back:
                    for (neighbour,) in con.execute('SELECT src FROM edges WHERE dst=? LIMIT 35',(uid,)):
                        keep.add(neighbour)
        self._local_focus_ids=keep
        self._focus_result_ids=list(origins)
        self.reload_network()
        self.focus_ids={key for key in keep if key in self.plot_data}
        self._focus_result_ids=[uid for uid in origins if uid in self.plot_data]
        matched=next((item for item in seeds if item[0] in self.plot_data),None)
        if matched is None:
            self.chosen=None
            self.search_hint.set(' found match Candidate , but There are currently no pass passed Quality filter can Display Node .')
            self.draw()
            return
        first=matched
        self.chosen=first[0]
        self.path=[]
        self.draw()
        pts=np.asarray([self.coords[k] for k in self.focus_ids if k in self.coords])
        if len(pts):
            center=pts.mean(axis=0)
            radius=max(.24,float(np.quantile(np.linalg.norm(pts-center,axis=1),.75))*1.5)
            radius=min(radius,max(1.0,float(np.max(np.abs(np.asarray(list(self.coords.values())))))))
            for dim,setlim in enumerate((self.ax.set_xlim,self.ax.set_ylim,self.ax.set_zlim)):
                setlim(center[dim]-radius,center[dim]+radius)
            self.canvas.draw_idle()
        self.search_hint.set(f' match  {len(origins)}  items primary Memory Unit; highlight  {len(self.focus_ids)}  items local Node .')
        if first[0] in self.all_nodes:self.select(first[0],repaint=False)

    def highlight_query_path(self):
        self.focus_ids={uid for uid in self.path if uid in self.plot_data}
        if self.path and self.path[0] in self.plot_data:
            self.chosen=self.path[0]
        self.draw(preserve_view=True)
        self.search_hint.set(f' already mark association path :{len(self.focus_ids)}  items Node .')

    def clear_focus(self):
        self._local_focus_ids=None
        self.focus_ids=set()
        self._focus_result_ids=[]
        self.chosen=None
        self.path=[]
        self.search_hint.set(' already restore global fast overview ( complete memory still retain in  SQLite).')
        self.reload_network()
        self.reset_camera()

    def _mark_resource_override(self, _event=None):
        """Preserve operator-chosen CPU/worker settings across a live refresh."""
        self._resource_manual_override = True

    def _cpu_capacity_text(self):
        info = self.cpu_info
        physical = info.get('physical_visible')
        quota = info.get('quota_cores')
        quota_note = f'; container quota {quota:g} CPUs' if quota is not None else ''
        load = info.get('cpu_load_pct')
        load_note = f'; current CPU usage {load:g}%' if load is not None else '; CPU usage unavailable'
        ram = info.get('memory_available_gib')
        ram_note = f'; free RAM {ram:g} GiB' if ram is not None else '; free RAM unavailable'
        return (f"Detected ({info.get('resource_backend', 'system')}): {info['system_logical']} logical / "
                f"{physical if physical else '?'} physical CPUs; "
                f"process allowed {info['affinity_logical']}; usable {info['available']}"
                f"{quota_note}{load_note}{ram_note}.")

    def _cpu_recommendation_text(self):
        advice = self.cpu_recommendation
        mode = 'PDF extraction' if advice.get('pdf_mode') else 'standard literature collection'
        manual = ' Manual selection retained.' if self._resource_manual_override else ''
        return (f"Live suggestion ({mode}): {advice['cpu_budget']} collector logical CPUs, "
                f"{advice['workers']} parallel workers (maximum {advice['worker_max']}). "
                f"Based on current CPU load, available RAM and process limits; "
                f"not an API/SQLite throughput benchmark.{manual}")

    def apply_cpu_recommendation(self):
        if self.collector and self.collector.is_alive():
            self.status.set('Collection is running. Settings will take effect on the next run.')
            return
        # "Use Recommended" always performs a new resource measurement.
        self._resource_manual_override = False
        self.refresh_cpu_capacity(quiet=True)
        self.cpu_budget_count.set(self.cpu_recommendation['cpu_budget'])
        self.workers_count.set(self.cpu_recommendation['workers'])
        self.cpu_recommendation_label.set(self._cpu_recommendation_text())
        self.status.set(f"Applied live hardware recommendation: "
                        f"CPU {self.cpu_recommendation['cpu_budget']}, "
                        f"workers {self.cpu_recommendation['workers']}.")

    def refresh_cpu_capacity(self, quiet=False):
        info = detect_cpu_resources()
        advice = recommend_build_resources(info, read_pdf=bool(self.pdf_mode.get()))
        self.cpu_info, self.cpu_recommendation = info, advice
        capacity = info['available']
        self.cpu_budget_spinner.configure(to=capacity)
        self.workers_spinner.configure(to=advice['worker_max'])
        # Explicit edits are respected; automatic values track each new measurement.
        if not self._resource_manual_override and not (self.collector and self.collector.is_alive()):
            self.cpu_budget_count.set(advice['cpu_budget'])
            self.workers_count.set(advice['workers'])
        else:
            for variable in (self.cpu_budget_count, self.workers_count):
                try:
                    value = int(variable.get())
                except (ValueError, tk.TclError):
                    value = advice['cpu_budget'] if variable is self.cpu_budget_count else advice['workers']
                variable.set(max(1, min(capacity, value)))
        self.cpu_capacity_label.set(self._cpu_capacity_text())
        self.cpu_recommendation_label.set(self._cpu_recommendation_text())
        if not quiet:
            if self.collector and self.collector.is_alive():
                self.status.set('Measured live resources; settings will apply on the next build.')
            else:
                self.status.set(f"Resources refreshed: {capacity} usable logical CPUs; "
                                f"recommend {advice['cpu_budget']} CPU / {advice['workers']} workers.")
 
    def _refresh_build_completion_state(self):
        """Show a validated per-network source frontier, not false global completeness."""
        if self.collector is not None and self.collector.is_alive():
            return False
        try:
            with contextlib.closing(database()) as con:
                completed=flin_recent_verified_frontier(con)
        except sqlite3.DatabaseError:
            completed=False
        self._frontier_shown_complete = bool(completed)
        if completed:
            self.run_btn.configure(state='disabled',text='Source Frontier Completed ✓')
            self.pipeline_title.set('✓ Current source frontier fully processed')
            self.pipeline_detail.set(
                'All discovered topics and categories have been processed, '
                'with no outstanding failures. Existing memory remains available. '
                f'New-source verification becomes available in up to {FLIN_FRONTIER_RECHECK_HOURS} hours.')
            self.status.set('Source frontier completed; FLIN knowledge can still grow when new sources appear.')
        else:
            self.run_btn.configure(state='normal',text='Start Building (Literature → FLIN)')
        return completed


    def start(self, retry_failed_only=False, references_only=False):
        if not retry_failed_only and not references_only and self._refresh_build_completion_state():
            messagebox.showinfo('Current Sources Fully Processed',
                'The current verified literature frontier has no remaining work. '
                'No new memories can be guaranteed without new sources; the automatic '
                f'recheck window is {FLIN_FRONTIER_RECHECK_HOURS} hours. '
                'This does not mean that all mathematics is known.')
            return
        if self.collector and self.collector.is_alive():
            if (not retry_failed_only and not references_only
                    and self.collector.request_immediate_discovery()):
                self.pipeline_detail.set('Immediate exploration requested; resuming discovery from provider cooldown...')
                self.status.set('Resuming FLIN discovery...')
            else:
                self.status.set('A build is still active. You can pause or stop and save.')
            return
        # Recheck load/RAM at launch: long-open desktop sessions may change.
        self.refresh_cpu_capacity(quiet=True)
        try:
            count = int(self.topic_count.get())
            per_theory = int(self.papers_count.get())
            offset = int(self.offset.get())
            workers = int(self.workers_count.get())
            cpu_budget = int(self.cpu_budget_count.get())
            capacity = detect_cpu_resources()['available']
            if not (1 <= count <= MAX_THEORIES and 1 <= per_theory <= MAX_PAPERS_PER_THEORY
                    and 0 <= offset <= MAX_WIKI_OFFSET and 1 <= workers <= capacity
                    and 1 <= cpu_budget <= capacity):
                raise ValueError(" Settings out of range range ")
        except (ValueError, tk.TclError):
            capacity = detect_cpu_resources()['available']
            messagebox.showerror("Configuration Error", "Topics and papers per topic must each be between 1 and 1,000,000;"
                                 f"worker count and collector CPU limit must each be in the 1~{capacity}  range.")
            return
        # No saved positional offset: durable SQLite frontier resumes by identity.
        manual_topics=[]
        offset=0
        continuous=bool(self.continuous_discovery.get()) and not (retry_failed_only or references_only)
        if continuous:
            # No fixed subject-count limit in continuous mode; only user stop,
            # actual discoverable frontier, or source failures end the run.
            count=sys.maxsize
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.active_theory = None
        self.active_index = 0
        self.active_total = count
        self.filter_var.set(' All ')
        self.worker_states = {}
        self.enqueued_theories = 0
        self.finished_theories = 0
        self.skipped_theories = 0
        self.success_theories = 0
        self.empty_theories = 0
        self._alert_shown = False
        if references_only:
            with database() as con:
                old_total=con.execute('SELECT COUNT(*) FROM abc_topics WHERE url LIKE ?',
                                      ('https://en.wikipedia.org/wiki/%',)).fetchone()[0]
            if not old_total:
                messagebox.showinfo('No Existing Topics','The database has no saved Wikipedia topics eligible for reference backfill.')
                return
            count=min(MAX_THEORIES,old_total)
            offset=0
            self.active_total=count
        if retry_failed_only:
            with database() as con:
                retry_total=con.execute("""SELECT COUNT(*) FROM abc_topics
                    WHERE state IN ('skipped_search','error','interrupted','partial')""").fetchone()[0]
            if retry_total == 0:
                messagebox.showinfo('No Failed Topics','There are no failed topics pending a retry.')
                return
            # Retry ALL saved failures, not the unrelated default '3 topics' cap.
            # The circuit breaker makes restarting thousands of failed jobs safe.
            count = min(MAX_THEORIES, retry_total)
            self.active_total = count
        self.update_worker_panel(workers)
        self.status.set(f'Preparing to start {workers}  parallel workers; CPU core limit {cpu_budget}/{capacity}')
        self.pipeline_title.set(f'{count:,} failed topics queued for resumption' if retry_failed_only
            else 'Starting continuous mathematical discovery and parallel learning' if continuous
            else 'Starting batched mathematical discovery and parallel learning')
        self.pipeline_detail.set('Backfilling citations, DOIs, arXiv IDs and titles for saved topics using SQLite.' if references_only
            else 'Requeueing previously failed topics from SQLite. Existing memories will be preserved.' if retry_failed_only
            else 'Resuming continuous mathematics discovery from the saved category frontier and topic queue until stopped or providers become unavailable.' if continuous
            else 'Exploring up to the current batch limit using persistent SQLite topic identities and category cursors (no positional Wikipedia skipping).')
        self.pipeline_percentage.set(0)
        self.has_started = True
        self.history_live_view()
        self._set_test_available(False)
        self._collector_completion_observed = False
        self.collector = Collector(self.events, self.stop_event, count, per_theory,
                                   offset, self.pdf_mode.get(), self.api_key.get().strip(),
                                   pause_event=self.pause_event, workers=workers,
                                   cpu_budget=cpu_budget,
                                   retry_failed_only=retry_failed_only,
                                   wikipedia_references=self.wiki_references_mode.get(),
                                   references_only=references_only,
                                   manual_topics=manual_topics,
                                   continuous=continuous)
        self.run_btn.configure(state='disabled',text='Start Building (Literature → FLIN)')
        self.retry_btn.configure(state="disabled")
        self.wikiref_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal", text="Pause")
        self.stop_btn.configure(state="normal")
        self.delete_btn.configure(state="disabled")
        self.status.set("Building in background...")
        self.collector.start()

    def toggle_pause(self):
        if not self.collector or not self.collector.is_alive():
            return
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_btn.configure(text="Pause")
            self._set_test_available(False)
            self.status.set("Building in background...")
        else:
            self.pause_event.set()
            self.pause_btn.configure(text="▶ Resume")
            self._set_test_available(True)
            self.status.set("Pause requested; it will take effect after the current request finishes.")
            self.reload_network()
            self.test_entry.focus_set()

    @staticmethod
    def _canonical_input(phrase):
        """Curated bilingual query normalization; does not alter stored graph IDs."""
        zh={
            '\u7dda\u6027\u4ee3\u6578':'linear algebra','\u5fae\u7a4d\u5206':'calculus',
            '\u8ca1\u91d1':'finance','\u91d1\u878d':'finance','\u8ca1\u52d9':'finance',
            '\u7d71\u8a08':'statistics','\u7d71\u8a08\u5b78':'statistics',
            '\u504f\u5fae\u5206\u65b9\u7a0b':'partial differential equation',
            '\u504f\u5c0e\u6578':'partial derivative','\u7279\u5fb5\u503c':'eigenvalue',
            '\u7279\u5fb5\u5411\u91cf':'eigenvector','\u77e9\u9663':'matrix','\u5411\u91cf':'vector',
            '\u91d1\u878d\u6578\u5b78':'mathematical finance','\u6295\u8cc7\u7d44\u5408':'portfolio',
            # Common cross-domain lexical equivalents (not inferred synonym graphs).
            '\u91ab\u5b78':'medicine','\u91ab\u7642':'medicine','\u81e8\u5e8a\u7814\u7a76':'clinical research',
            '\u81e8\u5e8a\u8a66\u9a57':'clinical trial','\u516c\u5171\u885b\u751f':'public health',
            '\u795e\u7d93\u79d1\u5b78':'neuroscience','\u6d41\u884c\u75c5\u5b78':'epidemiology',
            '\u85e5\u7406\u5b78':'pharmacology','\u764c\u75c7':'cancer','\u57fa\u56e0':'gene',
            '\u751f\u7269\u5b78':'biology','\u5206\u5b50\u751f\u7269\u5b78':'molecular biology',
            '\u751f\u7269\u5316\u5b78':'biochemistry','\u751f\u614b\u5b78':'ecology',
            '\u5de5\u7a0b':'engineering','\u6a5f\u68b0\u5de5\u7a0b':'mechanical engineering',
            '\u96fb\u6a5f\u5de5\u7a0b':'electrical engineering','\u63a7\u5236\u5de5\u7a0b':'control engineering',
            '\u6a5f\u5668\u4eba':'robotics','\u6a5f\u5668\u4eba\u5b78':'robotics','\u6750\u6599\u79d1\u5b78':'materials science',
            '\u8cc7\u8a0a\u79d1\u5b78':'computer science','\u96fb\u8166\u79d1\u5b78':'computer science',
            '\u4eba\u5de5\u667a\u6167':'artificial intelligence','\u6a5f\u5668\u5b78\u7fd2':'machine learning',
            '\u6df1\u5ea6\u5b78\u7fd2':'deep learning','\u96fb\u8166\u8996\u89ba':'computer vision',
            '\u8cc7\u8a0a\u5b89\u5168':'information security','\u8cc7\u6599\u5eab':'database',
            '\u5546\u696d':'business','\u7d93\u6fdf\u5b78':'economics','\u7d93\u6fdf':'economics',
            '\u7ba1\u7406\u5b78':'management','\u5e02\u5834\u884c\u92b7':'marketing','\u884c\u92b7':'marketing',
            '\u6703\u8a08':'accounting','\u8ca1\u52d9\u7ba1\u7406':'financial management',
            '\u793e\u6703\u5b78':'sociology','\u5fc3\u7406\u5b78':'psychology','\u5fc3\u7406':'psychology',
            '\u653f\u6cbb\u5b78':'political science','\u6559\u80b2\u5b78':'education',
            '\u4eba\u985e\u5b78':'anthropology','\u8a9e\u8a00\u5b78':'linguistics',
            '\u54f2\u5b78':'philosophy','\u502b\u7406\u5b78':'ethics','\u6b77\u53f2\u5b78':'history',
            '\u6587\u5b78':'literature','\u6587\u5316\u7814\u7a76':'cultural studies',
            '\u74b0\u5883\u79d1\u5b78':'environmental science','\u74b0\u5883\u5de5\u7a0b':'environmental engineering',
            ' agriculture ':'agriculture',' soil science ':'soil science',
            ' plant pathology ':'plant pathology',
        }
        return canonical_phrase(zh.get(phrase.strip(),phrase))

    @staticmethod
    def _query_topics(user_input):
        """Maintain original user topic order. A missing topic must remain visible."""
        return list(dict.fromkeys(p.strip() for p in re.split(r'[,，;；\n]+',user_input)
                                  if p.strip()))[:12]

    def _find_seed_nodes(self, user_input):
        """Fair, index-only multi-topic recall; never let one term absorb the pool.

        No whole-paper LIKE scans.  Up to five anchored matches per user term;
        each term has its own ranking, independent of the others' popularity.
        """
        phrases=self._query_topics(user_input)
        if not phrases:return []
        by_topic={}
        with database() as con:
            for phrase in phrases:
                canonical=self._canonical_input(phrase)
                tokens=list(lexical_tokens(canonical))[:7]
                if not tokens:
                    by_topic[phrase]=[]
                    continue
                ids=set()
                for uid in ('concept:'+norm_concept(canonical),
                            'theory:'+canonical.casefold()):
                    if con.execute('SELECT 1 FROM units WHERE id=?',(uid,)).fetchone():
                        ids.add(uid)
                # Prioritize the rarest token; for multi-token queries, look at
                # all tokens rather than requiring just the first one to match.
                for tok in sorted(tokens,key=len,reverse=True):
                    rows=con.execute('SELECT unit_id FROM unit_terms INDEXED BY idx_unit_terms_token '
                                     'WHERE token=? LIMIT 480',(tok,)).fetchall()
                    ids.update(uid for (uid,) in rows)
                if len(ids)<6:
                    for prefix in ('concept:'+norm_concept(canonical), 'theory:'+canonical):
                        ids.update(uid for (uid,) in con.execute(
                            'SELECT id FROM units WHERE id GLOB ? LIMIT 80',(prefix+'*',)))
                ranked=[]; query_tokens=set(tokens)
                ordered_ids=sorted(ids)
                for start in range(0,len(ordered_ids),300):
                    part=ordered_ids[start:start+300]
                    rows=con.execute('SELECT id,label,kind,support FROM units WHERE id IN ('+
                                     ','.join('?' for _ in part)+')',part).fetchall()
                    for uid,label,kind,support in rows:
                        label=label or ''
                        label_canonical=canonical_phrase(label)
                        lset=set(lexical_tokens(label))
                        shared=len(query_tokens & lset)
                        exact=(label_canonical==canonical)
                        if not shared and not exact:continue
                        if not exact and kind in ('concept','paper') and not quick_math_node_ok(label,kind):
                            continue
                        recall=shared/max(1,len(query_tokens))
                        precision=shared/max(1,len(lset))
                        score=(9.0 if exact else 3.7*recall+1.25*precision+
                               (1.4 if query_tokens.issubset(lset) else 0)+
                               (.18 if kind=='concept' else 0)+
                               min(.35,math.log1p(max(0,support or 0))/20))
                        if len(query_tokens)>1 and shared==1 and not exact:
                            score-=1.65
                        if kind=='paper': score-=.3
                        if score>=1.05:ranked.append((score,uid,label))
                ranked.sort(key=lambda item:(-item[0],len(item[2]),item[2].casefold(),item[1]))
                by_topic[phrase]=ranked[:5]
        # Interleave topic groups, ensuring that every recognized input
        # survives the 24-seed cap, regardless of lexicographic ordering.
        combined=[]; used=set()
        for row_no in range(5):
            for phrase in phrases:
                rows=by_topic.get(phrase,[])
                if row_no>=len(rows):continue
                score,uid,label=rows[row_no]
                if uid not in used:
                    combined.append((uid,label,phrase,score))
                    used.add(uid)
                if len(combined)>=max(24,len(phrases)):
                    return combined
        return combined

    def _association_chains(self, seeds, max_chains=25, depth=7):
        """Retrieve *directed existing paths* with topical evidence and fair coverage.

        Beam expansion uses original edges only (no invented semantic links).
        Scores reward mathematical relation nodes, relevant terminology, and
        paths that genuinely touch another user topic; generic hubs and long
        routes are disfavored.  Terminal candidates exist at EACH depth, not
        just the configured maximum depth.  All SQL probes stay bounded.
        """
        if not seeds:return []
        depth=max(1,min(8,int(depth)))
        max_chains=max(1,min(160,int(max_chains)))
        query_topics=list(dict.fromkeys(x[2] for x in seeds))
        topic_tokens={topic:set(lexical_tokens(self._canonical_input(topic)))
                      for topic in query_topics}
        topic_ids={topic:set(uid for uid,_,t,_ in seeds if t==topic)
                   for topic in query_topics}
        # Related terms are *ranking hints* only, NOT aliases or invented edges.
        # These are deliberately broad, but still favor mathematical vocabulary
        # over incidental laboratory / student / generic research phrasing.
        related_math={
            'calculus':{'derivative','partial','integral','gradient','jacobian',
                        'hessian','differential','equation','limit','variation'},
            'linear algebra':{'matrix','vector','eigenvalue','eigenvector','linear',
                              'operator','rank','determinant','spectral','decomposition'},
            'finance':{'finance','financial','asset','portfolio','option','pricing',
                       'risk','arbitrage','volatility','hedging','investment','stochastic'},
            'statistics':{'statistic','probability','regression','inference','estimate',
                          'distribution','variance','covariance','bayesian'},
        }
        math_vocab=set().union(*related_math.values())|{
            'theorem','lemma','proof','operator','functional','convex','optimal',
            'optimization','topology','geometry','manifold','boundary',
            'optimization','stochastic','kernel','norm','space','equilibrium',
            'tensor','function','convergence','eigen','pde','ode','sequence',
            'correlation','dynamics','numerical','algorithm','probability',
            'derivation','solution','inverse','transform','calculus','algebra'}
        if active_domain()!='mathematics':
            math_vocab=set(lexical_tokens(' '.join(domain_profile()['keywords'])))
            math_vocab|=set().union(*topic_tokens.values())
            related_math={}
        generic_hubs={'application','applications','analysis','student',
                      'students','engineering','mathematics','mathematical',
                      'method','methods','technique','techniques','approach',
                      'result','results','system','systems','education',
                      'study','studies','model','models','research','determination',
                      'use','used','general','high performance','separation'}
        edge_preference={
            'concept-relation':2.6,'relation-object':2.65,
            'source-relation':1.55, 'concept-concept':.65,
            'theory-paper':.32,'paper-concept':.85,
            'concept-paper-source':-.85,'concept-theory-source':-.5,
            'wiki-concept':.85,'wikipedia-cites-paper':.15,
        }
        def target_tags(label, kind):
            words=set(lexical_tokens(label))
            low=canonical_phrase(label)
            hits=set()
            for term, tks in topic_tokens.items():
                if tks and (tks.issubset(words) or low==self._canonical_input(term)):
                    hits.add(term)
            is_hub=low in generic_hubs
            if not is_hub and len(words)==1:
                is_hub=next(iter(words)) in generic_hubs
            math_signal=bool(words & math_vocab)
            related_signal=0
            for term in query_topics:
                related_signal+=len(words & related_math.get(self._canonical_input(term),set()))
            return hits,is_hub,math_signal,min(3,related_signal)

        with database() as con:
            info_cache={}
            edge_cache={}
            has_index=bool(con.execute("SELECT 1 FROM sqlite_master WHERE name='idx_edges_src_weight'").fetchone())
            def info(uid):
                if uid not in info_cache:
                    row=con.execute('SELECT label,kind FROM units WHERE id=?',(uid,)).fetchone()
                    lb,kind=(row[0] or uid,row[1] or 'unknown') if row else (uid,'unknown')
                    tags=target_tags(lb,kind)
                    info_cache[uid]=(lb,kind,*tags)
                return info_cache[uid]
            def outgoing(uid):
                if uid not in edge_cache:
                    if has_index:
                        rows=con.execute('SELECT dst,kind,weight FROM edges INDEXED BY idx_edges_src_weight '
                                         'WHERE src=? ORDER BY weight DESC LIMIT 90',(uid,)).fetchall()
                    else:
                        rows=con.execute('SELECT dst,kind,weight FROM edges INDEXED BY idx_edges_src '
                                         'WHERE src=? LIMIT 130',(uid,)).fetchall()
                    # Always reserve room for evidence-backed relationship
                    # edges: with millions of co-occurrence links, the raw
                    # top-90 weights can otherwise exclude ALL relation nodes.
                    rows+=con.execute("SELECT dst,kind,weight FROM edges INDEXED BY idx_edges_src "
                        "WHERE src=? AND kind IN ('concept-relation','relation-object',"
                        "'source-relation') LIMIT 50",
                        (uid,)).fetchall()
                    # Different edge types have different evidentiary meaning;
                    # top raw weight alone favors common concepts / papers.
                    best={}
                    for dst,kind,w in rows:
                        w=max(.001,float(w or 0))
                        edge_quality=(edge_preference.get(kind,0)+
                                      .20*math.log1p(min(15,w)))
                        prev=best.get((dst,kind))
                        if prev is None or edge_quality>prev[0]:
                            best[(dst,kind)]=(edge_quality,w)
                    ordered=sorted(((dst,kind,w,q) for (dst,kind),(q,w) in best.items()),
                                   key=lambda a:(-a[3],-a[2],a[0]))
                    edge_cache[uid]=ordered[:36]
                return edge_cache[uid]
            by_topic={t:[] for t in query_topics}
            # Most relevant seeds first per phrase, with strict per-phrase caps.
            for topic in query_topics:
                seed_items=sorted((v for v in seeds if v[2]==topic),key=lambda v:-v[3])[:3]
                for seed,_,_,seed_score in seed_items:
                    # Scores are normalized across hops. Cumulative edge weight
                    # alone must not make every result length=depth+1.
                    beam=[([seed],[],[],0.,0.,set([topic]))]
                    for level in range(depth):
                        grown=[]
                        for path,weights,kinds,quality,penalties,visited_topics in beam:
                            src=path[-1]
                            for dst,kind,w,evidence_score in outgoing(src):
                                if dst in path:continue
                                lb,nodekind,hits,is_hub,math_signal,rel_signal=info(dst)
                                # Generic scholarly terms do not justify a new
                                # mathematical association on their own.
                                penalty=(1.75 if is_hub else 0.)
                                if nodekind in ('concept','paper') and not hits:
                                    if not quick_math_node_ok(lb,nodekind):
                                        # Legacy network remains intact; weak
                                        # nodes are excluded from curated paths.
                                        continue
                                if nodekind=='paper':penalty+=.65
                                if not math_signal and nodekind=='concept' and not hits:
                                    penalty+=.7
                                target_touch=len(hits-set([topic]))>0 or any(
                                    dst in topic_ids[t] for t in query_topics if t!=topic)
                                step_score=(evidence_score+
                                            (1.65 if nodekind=='relation' else 0)+
                                            (.8 if math_signal else 0)+
                                            (.36*rel_signal)+
                                            (3.2 if target_touch else 0))
                                new_path=path+[dst]
                                new_w=weights+[round(w,3)]
                                new_k=kinds+[kind]
                                new_q=quality+step_score
                                new_pen=penalties+penalty
                                new_vis=visited_topics|hits
                                hops=len(new_k)
                                mean_quality=(new_q-new_pen)/hops
                                # Topical/evidential relevance & concise paths,
                                # not sheer route length, drive final ranking.
                                score=(.23*min(9,seed_score)+mean_quality+
                                       .72*len(new_vis-set([topic]))-
                                       .17*max(0,hops-3))
                                # Source-only paths are displayed as such;
                                # mathematical relation chains get more weight.
                                relation_edges=sum(1 for x in new_k if x in
                                    ('concept-relation','relation-object'))
                                complete_relation=('concept-relation' in new_k and
                                                   'relation-object' in new_k)
                                if complete_relation:score+=1.35
                                elif relation_edges:score+=.12
                                if kind in ('concept-paper-source','concept-theory-source') and hops>3:
                                    score-=.45
                                if not math_signal and is_hub: score-=.65
                                # Do not *display* irrelevant shallow stops, but
                                # allow them to serve as intermediate nodes if
                                # subsequent real edges lead back to a topic.
                                record={'seed':topic,'ids':new_path,
                                        'labels':[info(x)[0] for x in new_path],
                                        'weights':new_w,'edge_kinds':new_k,
                                        'score':round(score,3),
                                        'related_topics':[t for t in query_topics if t in new_vis],
                                        'evidence_type':(' Candidate research relationship ' if complete_relation else
                                                         ' relationship Node ( not yet expand open )' if relation_edges else
                                                         ' term compile Co-occurrence ' if 'concept-concept' in new_k else
                                                         ' Literature Associations ')}
                                # Every depth is eligible; low evidence stops
                                # are not recommendations. Traversal continues
                                # so a valid bridge through a hub is still findable.
                                if score>=2.2:
                                    by_topic[topic].append(record)
                                grown.append((new_path,new_w,new_k,new_q,new_pen,new_vis,
                                              score))
                        if not grown:break
                        # Keep exploratory diversity: no identical terminal node
                        # dominates the beam, while cross-topic hits survive.
                        grown.sort(key=lambda a:(-a[-1],len(a[0]),a[0][-1]))
                        next_beam=[];used_ends=set()
                        for item in grown:
                            endpoint=item[0][-1]
                            if endpoint in used_ends:continue
                            next_beam.append(item[:6]);used_ends.add(endpoint)
                            if len(next_beam)>=15:break
                        beam=next_beam
            # Deduplicate near-identical results by origin/endpoint/edge type,
            # then explicitly round-robin across ALL matched input topics.
            ranked={}
            for topic in query_topics:
                original=sorted(by_topic[topic],key=lambda p:(-p['score'],len(p['ids']),p['labels'][-1]))
                distinct=[]; seen=set();endpoint_count=defaultdict(int)
                for p in original:
                    key=(p['ids'][0],p['ids'][-1],p['evidence_type'])
                    if key in seen or endpoint_count[p['ids'][-1]]>=2:continue
                    seen.add(key);endpoint_count[p['ids'][-1]]+=1
                    distinct.append(p)
                    if len(distinct)>=max_chains:break
                ranked[topic]=distinct
            result=[]; used_paths=set()
            # Don't display 25 calculus paths followed by zero finance paths.
            for row_no in range(max_chains):
                progressed=False
                for topic in query_topics:
                    opts=ranked.get(topic,[])
                    if row_no>=len(opts):continue
                    item=opts[row_no]
                    key=tuple(item['ids'])
                    if key in used_paths:continue
                    used_paths.add(key)
                    result.append(item);progressed=True
                    if len(result)>=max_chains:return result
                if not progressed and all(len(ranked.get(t,[]))<=row_no for t in query_topics):
                    break
            return result

    def test_text(self, auto_generate=False):
        # Previous question-generation entry is intentionally removed.
        self.flin_start_bridge_explorer()

    def show_latest_results(self):
        with database() as con:
            row = con.execute('SELECT MAX(id) FROM association_runs').fetchone()
        if row and row[0]:
            self.show_results(int(row[0]))
        else:
            messagebox.showinfo('Association History', 'No association tests have been saved yet.')

    def show_results(self,run_id):
        with database() as con:
            row=con.execute('SELECT query,paths_json,created,matches_json FROM association_runs WHERE id=?',
                            (run_id,)).fetchone()
            ctxrow=con.execute('SELECT context_json FROM association_context WHERE run_id=?',
                               (run_id,)).fetchone()
        if not row:return
        query,raw,created,matches_raw=row
        paths=json.loads(raw or '[]')
        matches=json.loads(matches_raw or '[]')
        context=json.loads(ctxrow[0]) if ctxrow else {}
        win=tk.Toplevel(self.root)
        win.title(f' activation Memory Unit ·  Directed association chains  #{run_id}')
        win.geometry('1110x720');win.minsize(770,520);win.configure(bg=self.BG)
        top=ttk.Frame(win,style='Dark.TFrame',padding=(16,12));top.pack(fill='x')
        self.label(top,f' association query :{query[:125]}').pack(anchor='w')
        self.label(top,f' already match  {len(matches)}  items Memory Unit · {len(paths)}  edges Directed sequence  · '+
            f'{len(context.get("relations",[]))}  items Candidate research relationship  · {created}',note=True).pack(anchor='w')
        topics=self._query_topics(query)
        per_topic=[]
        for term in topics:
            nmatch=sum(1 for m in matches if m.get('query')==term)
            npath=sum(1 for path in paths if path.get('seed')==term)
            status=f'{term}:  match  {nmatch} /  Path  {npath}'
            if nmatch==0:status+='( missing can retrieval Memory Unit)'
            elif npath==0:status+='( temporary no can reached Directed Path )'
            per_topic.append(status)
        self.label(top,' each input Topic  · '+'  |  '.join(per_topic),
                   note=True,wraplength=1060).pack(anchor='w',pady=(4,0))
        core=ttk.Frame(win,style='Dark.TFrame',padding=(10,4));core.pack(fill='both',expand=True)
        left=ttk.Frame(core,style='Side.TFrame',padding=9);left.pack(side='left',fill='both',expand=True)
        right=ttk.Frame(core,style='Side.TFrame',padding=9);right.pack(side='left',fill='both',expand=True,padx=(8,0))
        self.label(left,' actual store in Directed Associations sequence ( single Path NOT is strict Domain Validate )').pack(anchor='w',pady=(0,6))
        table=ttk.Treeview(left,columns=('start','end','length','type','score'),
                           show='headings',height=15,style='Dark.Treeview')
        for col,name,width in [('start',' input term ',115),('end',' end points ',190),
                               ('length',' Node count ',55),('type',' relationship basis ',85),('score',' sort parts ',65)]:
            table.heading(col,text=name)
            table.column(col,width=width,stretch=(col in ('end',)))
        table.pack(fill='both',expand=True)
        for i,item in enumerate(paths):
            table.insert('','end',iid=str(i),values=(item.get('seed',''),
                (item.get('labels') or [''])[-1][:55],len(item.get('ids',[])),
                item.get('evidence_type',' history Path '),
                item.get('score','—')))
        detail=tk.Text(left,height=11,wrap='word',bg=self.FIELD,fg=self.FG,padx=9,pady=7,
                       relief='flat',font=('Noto Sans CJK TC',10))
        detail.pack(fill='x',pady=(7,0))
        def select_path(event=None):
            sel=table.selection()
            if not sel:return
            p=paths[int(sel[0])]
            detail.delete('1.0','end')
            labels=p.get('labels',[]); kinds=p.get('edge_kinds',[]); weights=p.get('weights',[])
            lines=[f' input Topic :{p.get("seed","")}  ·  {p.get("evidence_type"," already store Link ")}',
                   ' Path for  SQLite  actually exist in in single to edge , not strict Domain Validate .','']
            for k,unitlabel in enumerate(labels):
                lines.append(f'{k+1}. {unitlabel}')
                if k<len(kinds):
                    w=weights[k] if k<len(weights) else '?'
                    lines.append(f'      ↓ {kinds[k]}  ( Strength  {w})')
            detail.insert('1.0','\n'.join(lines))
            self.path=p.get('ids',[])
        table.bind('<<TreeviewSelect>>',select_path)
        if paths:
            table.selection_set('0');select_path()
        else:
            detail.insert('1.0',' There are currently no can reached Directed Path .\n'
                +' match :'+', '.join(m.get('label','') for m in matches[:15])
                +'\n please expand Memory Unit Data , Rebuild term form Index or Check Candidate relationship .')
        ttk.Button(left,text=' in left  3D  graph highlight selected Path ',style='Dark.TButton',
                   command=self.highlight_query_path).pack(fill='x',pady=(8,0))
        self.label(right,'Activated memories, associative paths and source records ').pack(anchor='w',pady=(0,6))
        area=tk.Text(right,wrap='word',bg=self.FIELD,fg=self.FG,relief='flat',
                     padx=11,pady=10,font=('Noto Sans CJK TC',10))
        area.pack(fill='both',expand=True)
        facts=compact_recall(context,paths,max_chars=24000)
        area.insert('1.0',evidence_only_report(context,paths)+'\n\n'
                    +' already match Memory Unit:\n'+'\n'.join(f'{m.get("label","")} [{m.get("id","")}]' for m in matches)
                    +'\n\n activation sub Network (JSON, Traceable ):\n'+json.dumps(facts,ensure_ascii=False,indent=2))
        area.configure(state='disabled')
        footer=ttk.Frame(win,style='Dark.TFrame',padding=(12,9));footer.pack(fill='x')
        self.label(win,'These are saved associative paths, not independently verified mathematical claims.',
                   note=True).pack(anchor='w',padx=12,pady=(0,8))
        win.lift();win.focus_set()

    def show_wikipedia_citations(self):
        """Auditable extraction record; missing PDFs are not called full text."""
        with database() as con:
            summary=con.execute("""SELECT status,COUNT(*) FROM wikipedia_references
                GROUP BY status ORDER BY COUNT(*) DESC""").fetchall()
            rows=con.execute("""SELECT theory,reference_key,doi,paper_title,status,work_id,error,
                citation_text,reference_url,read_level FROM wikipedia_references
                ORDER BY updated DESC LIMIT 400""").fetchall()
        win=tk.Toplevel(self.root);win.title('Wikipedia  citation source verification Record ')
        win.geometry('1050x640');win.configure(bg='#0c1421')
        ttk.Label(win,text='Wikipedia  references :'+
            '｜'.join(f'{status} {count:,}' for status,count in summary),
            style='Dark.TLabel').pack(fill='x',padx=12,pady=12)
        frame=ttk.Frame(win,style='Side.TFrame');frame.pack(fill='both',expand=True,padx=12,pady=(0,12))
        txt=tk.Text(frame,bg='#182438',fg='#dceafd',wrap='word',font=('DejaVu Sans Mono',10))
        scroll=ttk.Scrollbar(frame,command=txt.yview)
        scroll.pack(side='right',fill='y');txt.pack(side='left',fill='both',expand=True)
        txt.configure(yscrollcommand=scroll.set)
        for theory,refid,doi,title,status,wid,error,literal,link,read_level in rows:
            txt.insert('end',f'{theory}  |  {refid}  [{status}]\n')
            txt.insert('end',f'   title :{title or " not yet knowledge other "}\n  DOI:{doi or " no "}\n')
            txt.insert('end',f'  OpenAlex:{wid or " Not yet Verify "}| content depth :{read_level or " not yet read "}\n')
            if error:txt.insert('end',f'   reason :{error}\n')
            txt.insert('end',f'   original citation :{literal[:360]}\n  URL:{link}\n\n')
        txt.configure(state='disabled')

    def show_openalex_failures(self):
        with database() as con:
            rows=con.execute("""SELECT category,COALESCE(status,0),COUNT(*),MAX(reason)
                FROM openalex_failures GROUP BY category,status ORDER BY COUNT(*) DESC""").fetchall()
            recent=con.execute("""SELECT theory,page,category,COALESCE(status,0),reason,created
                FROM openalex_failures ORDER BY id DESC LIMIT 60""").fetchall()
            pending=con.execute("""SELECT COUNT(*) FROM theory_progress
                WHERE state IN ('skipped_search','error','interrupted')""").fetchone()[0]
        win=tk.Toplevel(self.root);win.title('OpenAlex  Error Diagnostics and pending retry Topic ')
        win.geometry('940x580');win.configure(bg=self.BG)
        box=tk.Text(win,wrap='word',bg=self.FIELD,fg=self.FG,font=('DejaVu Sans Mono',10))
        box.pack(fill='both',expand=True,padx=12,pady=12)
        box.insert('end',f' still needs Retry :{pending:,}  items Topic \n\n')
        if not rows:box.insert('end',' this is new version New Diagnostics Record . legacy can can No retain original Error reason .\n')
        for cat,status,n,reason in rows:
            box.insert('end',f'[{cat}] HTTP {status or " unknown "}:{n:,}  imes \n')
            box.insert('end',f'  {reason}\n')
        box.insert('end','\n Recent search failed :\n')
        for title,page,cat,status,reason,created in recent:
            box.insert('end',f'{created} · {title}  pages {page} · {cat} HTTP {status or " unknown "}\n  {reason}\n')
        box.configure(state='disabled')

    def _set_test_available(self, enabled):
        # v7 lookup is read-only and can run while harvesting continues.
        return

    def stop(self):
        self.stop_btn.configure(state='disabled')
        self.stop_event.set()
        self.pause_event.clear()
        self.status.set("Finishing the current request and saving data...")

    def delete_network(self):
        if getattr(self,'generating_sets',set()):
            messagebox.showwarning('Question Generation in Progress','Wait for background question generation to finish before deleting the network.')
            return
        if self.iteration_jobs:
            messagebox.showwarning('Review in Progress','Stop the review workflow and wait for the current model call to finish.')
            return
        if getattr(self,'_repair_active',False) or getattr(self,'_math_repair_active',False):
            messagebox.showwarning('Please Wait','A legacy index repair is in progress. Wait before deleting the network.')
            return
        if self.collector and self.collector.is_alive():
            messagebox.showwarning('Cannot Clear Network','Stop collection and wait for workers to finish before deleting the network.')
            return
        with database() as con:
            n_theory, n_paper, n_unit, n_edge = stats(con)
        if n_unit == 0:
            messagebox.showinfo('Empty Network','The selected network contains no memory units to delete.')
            return
        ok = messagebox.askyesno('Permanently Clear the Entire Network?',
            f' permanently delete Processing use Database in :\n\n'
            f'Memory Unit {n_unit:,}  items \n Directed Link  {n_edge:,}  edges \n'
            f' Topic  {n_theory:,}  items , Paper  {n_paper:,}  papers \n'
            ' with and building history and association test .\n\n'
            ' backup snapshot ( if with ) Will not together delete .\n\n confirm define clear ?',
            icon='warning',default='no')
        if not ok: return
        try:
            with database() as con:
                with con:
                    for table in ('wikipedia_reference_scans','wikipedia_references','question_feedback','question_candidates','question_sets','association_context','relation_evidence','association_runs','positions','build_events','mentions',
                                  'edges','paper_theories','openalex_failures','theory_progress','papers','theories','unit_terms','network_meta','units'):
                        con.execute('DELETE FROM '+table)
                    con.execute("DELETE FROM sqlite_sequence WHERE name IN ('build_events','association_runs','question_sets','question_candidates','question_feedback')")
            self.coords = {};self.chosen=None;self.path=[];self.plot_data={}
            self._stats_cache = None
            self._local_focus_ids = None
            self.focus_ids = set()
            self._focus_result_ids = []
            self.zoom = 1.0
            self.timeline_cursor=0;self.timeline_latest=0;self.timeline_live=True
            self.has_started=False
            self.active_theory=None
            self.worker_states={}
            self.enqueued_theories=0
            self.finished_theories=0
            self.update_worker_panel()
            self.pipeline_title.set(' Current not yet in Collect ')
            self.pipeline_detail.set('Network cleared.')
            self.pipeline_percentage.set(0)
            self.graph_phase.set('Network cleared.')
            self._set_test_available(False)
            self.test_var.set('')
            self.search_var.set('')
            self.status.set('Network cleared.')
            self.detail.configure(state='normal');self.detail.delete('1.0','end')
            self.detail.configure(state='disabled')
            self.load_topics();self.refresh_history(reset=True);self.reload_network()
            self.append_log(' already delete Current Database All Memory Unit, Link and history .')
        except Exception as exc:
            messagebox.showerror('Deletion Failed',str(exc))

    def append_log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", time.strftime("%H:%M:%S") + "  " + str(message) + "\n")
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 180:
            self.log_text.delete("1.0", f"{lines-150}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def import_local_snapshot(self):
        """Import a selected official works file without freezing Tk."""
        filename=filedialog.askopenfilename(parent=self.root,
            title=' select official  OpenAlex works   JSONL  or  JSONL.gz  file ',
            filetypes=[('OpenAlex work data','*.jsonl *.jsonl.gz'),('All files','*')])
        if not filename:return
        if self.collector and self.collector.is_alive():
            messagebox.showwarning('Import Deferred','Pause or stop collection before importing a catalog to reduce disk contention.')
            return
        if not messagebox.askyesno('Build Offline Index',
           ' file can may contain millions of records Literature , Import needs large amounts of storage space and Time .\n'
           ' per batch automatic store file , duplicate launch will also deduplicate . is whether Start ?',parent=self.root):return
        self.catalog_status.set(' Processing Import , please in tool Log View progress ...')
        self._catalog_import_active=True
        def job():
            try:
                scanned,added=import_openalex_snapshot(filename,
                    progress=lambda n,m:self.events.put(('catalog_progress',(n,m))))
                self.events.put(('catalog_done',(scanned,added)))
            except Exception as exc:
                self.events.put(('catalog_error',str(exc)[:420]))
        self._start_background_thread(target=job, name='BrainSnapshotIndexer')

    def check_connections(self):
        # Tkinter variables must be read in the main thread.
        key = self.api_key.get().strip()
        def safe_worker():
            session = requests.Session()
            source_openalex=False
            source_crossref=False
            source_arxiv=False
            source_local=local_catalog_available()
            try:
                topics = discover_theories(session)
                self.events.put(("log", f"✓ Wikipedia: found  {len(topics)}  items research Topic ( test maximum  100)"))
            except Exception as e:
                self.events.put(("log", f"✕ Wikipedia：{type(e).__name__}: {e}"))
            try:
                root=arxiv_request(session,{'search_query':'all:"graph theory"',
                    'start':0,'max_results':1})
                self.events.put(('log',f'✓ arXiv: response  {len(root.findall(_ARXIV_ATOM+"entry"))} papers'))
                source_arxiv=True
            except Exception as e:
                self.events.put(('log',f'✕ arXiv：{type(e).__name__}: {e}'))
            if os.environ.get('BRAIN_USE_OPENALEX','0')=='1':
                try:
                    result = openalex_preflight(session,key)
                    self.events.put(('log',f'✓ OpenAlex( selected ): response  {len(result["results"])} papers'))
                    source_openalex=True
                except Exception as e:
                    explanation=str(e).replace(key,'[API KEY]') if key else str(e)
                    self.events.put(('log',f'✕ OpenAlex：{type(e).__name__}: {explanation}'))
            else:
                self.events.put(('log','· OpenAlex API  not enabled ( NOT impact building )'))
            try:
                count=local_catalog_count()
                self.events.put(('log', f'✓  local Mathematics Literature Index :{count:,} papers' if count else
                                 '·  local Index none yet Literature ( first imes Search will automatic accumulated )'))
                data=crossref_request(session,{'query.bibliographic':'graph theory','rows':1})
                self.events.put(('log', f'✓ Crossref: response  {len(data.get("items",[]))}  papers ( respect rate limits Limit )'))
                source_crossref=True
            except Exception as exc:
                self.events.put(('log',f'✕ Crossref：{type(exc).__name__}: {exc}'))
            finally:session.close()
            ready=source_arxiv or source_openalex or source_crossref or source_local
            report=(' available Source :'+', '.join(label for label,flag in
                  [('arXiv',source_arxiv),('Crossref',source_crossref),(' local Index ',source_local),('OpenAlex( selected )',source_openalex)] if flag)) if ready else ' All literature provider average NOT available ; Check Network or Import snapshot .'
            self.events.put(('source_check',(ready,report)))
        self._start_background_thread(target=safe_worker, name='FLINBackgroundWorker')
        self.append_log(" Start test  Wikipedia,arXiv,Crossref  and local Index ...")

    def update_worker_panel(self, configured=None):
        capacity = configured if configured is not None else int(self.workers_count.get())
        active = [v for v in self.worker_states.values()
                  if v['phase'] not in (' Idle ',) and not v['phase'].startswith(' Completed :')]
        self.worker_summary.set(
            f' workers  {len(active)}/{capacity} · CPU  quota  {self.cpu_budget_count.get()}'
            f'/{self.cpu_info["available"]} ·  enqueue  {self.enqueued_theories:,}'
            f' ·  Completed  {self.finished_theories:,}( Successful  {self.success_theories:,}'
            f'/ no candidates  {self.empty_theories:,}/ search failed  {self.skipped_theories:,})')
        lines = []
        for worker in sorted(self.worker_states):
            item = self.worker_states[worker]
            title = item['title'][:33] if item['title'] else ' Waiting new Topic '
            phase = item['phase']
            paper_no = item['done']
            page = item['page']
            indicator = (f' literature search pages  {page}' if page and phase == ' Search page ' else
                         f' Paper  {paper_no}/{item["target"]}' if item['target'] else phase)
            lines.append(f'W{worker}  {title:<33}  {indicator}  |  {phase}')
        self.worker_detail.set('\n'.join(lines) if lines else ' Waiting Topic assign /Wikipedia  Discover ...')

    def poll(self):
        updated = False
        try:
            for _ in range(300):
                kind, msg = self.events.get_nowait()
                if kind == 'flin_bridge_progress':
                    g,total,done,cap=msg
                    self.bridge_status.set(f'Input {g}/{total}: {done}/{cap} observed paths · read-only')
                elif kind == 'flin_bridge_done':
                    self.bridge_active=False
                    self.bridge_button.configure(state='normal')
                    st=msg['statistics']
                    self.bridge_status.set('✓ '+str(st['visited_units'])+' memories reached; related concepts listed.')
                    self.flin_show_related_results(msg)
                elif kind == 'flin_bridge_error':
                    self.bridge_active=False
                    self.bridge_button.configure(state='normal')
                    self.bridge_status.set('✕ Could not find concepts: '+msg[:165])
                    self.append_log('Related concepts: '+msg)
                    messagebox.showerror('Related Concepts',msg[:1200],parent=self.root)
                elif kind == 'catalog_progress':
                    scanned,added=msg
                    self.catalog_status.set(f' Index scan  {scanned:,}  records , this run New  {added:,} papers')
                elif kind == 'catalog_done':
                    self._catalog_import_active=False
                    scanned,added=msg
                    self.catalog_status.set(f' Index shared  {local_catalog_count():,}  papers | this run New  {added:,} papers')
                    self.append_log(f'✓ OpenAlex  snapshot offline Index Completed : scan  {scanned:,}, New  {added:,}')
                elif kind == 'catalog_error':
                    self._catalog_import_active=False
                    self.catalog_status.set(' offline Index Failed , please View Log ')
                    self.append_log('✕  offline Index Failed :'+msg)
                elif kind == 'flin_cost_retrofit_done':
                    self.abc_worker_active=False
                    self.abc_activity.set('Cost retrofit finished: '+str(msg))
                    self.append_log('FLIN cost retrofit: '+str(msg))
                    self.abc_refresh_status()
                    self.reload_network()
                elif kind == 'abc_backfill_done':
                    self.abc_worker_active=False
                    self.abc_refresh_status()
                    self.abc_activity.set('✓  process  '+str(msg['processed'])+'  papers , New online Input cluster  '+str(msg['new_events'])+'  clusters .')
                elif kind == 'abc_simulation_done':
                    self.abc_worker_active=False
                    response,association_id=msg
                    self.abc_last_run_id=response['run_id']
                    self.abc_last_association_id=association_id
                    self.abc_activity.set('✓  time-varying Response already save ; reached Threshold Memory Unit:'+str(response['visible_count']))
                    self.abc_show_response(response,association_id)
                elif kind == 'abc_worker_error':
                    self.abc_worker_active=False
                    self.abc_activity.set('✕ FLIN  work Failed :'+msg[:210])
                    self.append_log('FLIN  work Failed :'+msg[:500])
                elif kind == 'discovered':
                    discovered, cap, title, pending = msg
                    self.enqueued_theories = discovered
                    self.active_total = cap
                    self.pipeline_title.set(
                        f'FLIN  Continuous exploration  ·  already New  {discovered:,}  items Topic ' if
                        (self.collector and self.collector.continuous) else
                        f' already enqueue  {discovered:,}/{cap:,}  items Topic ')
                    self.pipeline_detail.set(f'Recently discovered: {title}; Waiting queue  {pending}  items ')
                    self.update_worker_panel()
                    if self.filter_var.get() == ' In progress ':
                        self.graph_phase.set(
                            f' Continuous building : this rounds Discover  {discovered:,}  items Mathematics Topic ;' if
                            (self.collector and self.collector.continuous) else
                            f' sequence stream building : already discover  {discovered:,}/{cap:,}  items Topic ;')
                elif kind == 'purity_progress':
                    accepted=msg['approved_candidates']
                    rejected=msg['rejected_candidates']
                    deleted=msg['deleted_noise_units']
                    mean=msg['mean_heuristic_score']
                    grade=f'{mean:.1f}/100' if mean is not None else ' pending evaluation '
                    old_score=msg.get('old_concept_purity_score')
                    old_rate=msg.get('old_concept_pass_rate_pct')
                    old_txt=(f' old network scan  {msg["old_concepts_evaluated"]:,}  items concept ,'
                             f' acceptance rate  {old_rate:g}%/ average score  {old_score:g};'
                             if old_score is not None else ' old network scan pending action ;')
                    self.math_quality_status.set(
                        f'{old_txt} new memory Candidate average score  {grade}, accept  {accepted:,},'
                        f' blocked  {rejected:,}; confirmed noise already delete  {deleted:,}.'
                        ' score for rules estimate .')
                elif kind == 'source_check':
                    healthy,detail=msg
                    self.pipeline_detail.set(detail[:500])
                    self.status.set('✓  at least one items literature provider available ' if healthy else '✕ All literature providers unavailable')
                    if not healthy:
                        messagebox.showerror('Literature Provider Connectivity Check Failed',detail[:1000])
                elif kind == 'service_alert':
                    message=str(msg)
                    self.pipeline_title.set('🚨  There are currently no available literature provider ')
                    self.pipeline_detail.set(message[:550])
                    self.status.set('✕  All available literature providers failed ; already save existing Data ')
                    self.append_log('🚨 '+message)
                    if not getattr(self,'_alert_shown',False):
                        self._alert_shown=True
                        messagebox.showerror('Literature Provider Error',
                            message[:950]+'\n\n Check  arXiv/Crossref  Network , Later Retry Failed Topic .')
                elif kind == 'worker':
                    wid, title, phase, done, target, page, linked = msg
                    self.worker_states[wid] = dict(title=title, phase=phase, done=done,
                                                   target=target, page=page, linked=linked)
                    if title and phase != ' Idle ' and not phase.startswith(' Completed :'):
                        self.active_theory = title
                        if self.filter_var.get() == ' and along building ':
                            self.graph_phase.set(' and along  W'+str(wid)+':'+title)
                    self.update_worker_panel()
                    if self.filter_var.get() == ' In progress ':
                        active = sum(v['phase'] not in (' Idle ',) and
                                     not v['phase'].startswith(' Completed :')
                                     for v in self.worker_states.values())
                        self.graph_phase.set(f'Currently building in parallel: {active}  items Topic Memory Unit Network ')
                elif kind == 'theory_finished':
                    wid, title, state, processed, linked, finished = msg
                    self.finished_theories = finished
                    if state == 'skipped_search':
                        self.skipped_theories += 1
                    elif state == 'complete':
                        self.success_theories += 1
                    elif state == 'no_candidates':
                        self.empty_theories += 1
                    if self.collector and self.collector.continuous:
                        # There is no meaningful global denominator for world mathematics.
                        self.pipeline_percentage.set(0)
                        self.pipeline_title.set(
                            f'FLIN  Continuous exploration  ·  enqueue  {self.enqueued_theories:,},'
                            f' Processed  {finished:,}  items Topic ')
                    else:
                        self.pipeline_percentage.set(100 * finished / max(1, self.active_total))
                    if state == 'skipped_search':
                        self.pipeline_detail.set(
                            f'W{wid}  literature provider temporarily NOT available :{title}; already save  {processed}  papers ; can Retry ')
                    else:
                        self.pipeline_detail.set(f'W{wid}  Completed  {title}:{processed}  papers ; New  {linked}  edges Associations ')
                    self.update_worker_panel()
                    updated = True
                elif kind == 'collector_phase':
                    phase,info=msg
                    if phase=='idle':
                        self.run_btn.configure(state='normal',text='↻  Explore now ( Current waiting )')
                        self.pipeline_title.set('FLIN  already proceed enter provider cooldown  · Memory Unit Network already save ')
                        self.status.set('Waiting for provider retry. Click Explore Now to retry immediately.')
                    else:
                        self.run_btn.configure(state='disabled',text='Start Building (Literature → FLIN)')
                        if phase=='waiting_workers':
                            self.pipeline_title.set(' Waiting existing Literature workers Completed ')
                            self.status.set(f' still with  {info}  items Topic learning learning work not yet Completed ; can click abort and save ')
                        elif phase=='discovering':
                            self.status.set('FLIN is checking for new topics and literature sources.')
                        elif phase=='queue_backpressure':
                            self.pipeline_title.set(' Literature process queue already full  ·  Waiting Background workers ')
                            self.status.set(f'⏳  still with  {info}  items Literature work not yet Completed , can click abort and save ')
                elif kind == 'collector_waiting':
                    self.pipeline_detail.set(f' Background still with  {msg}  items Topic Processing process ; Waiting Network /PDF  please request Completed ')
                elif kind == 'discovery':
                    phase = getattr(self.collector,'phase','')
                    if phase!='idle':
                        self.pipeline_title.set('FLIN ·  Discover Mathematics Topic ')
                        self.status.set('Discovering mathematical research topics...' if phase!='waiting_workers'
                            else ' Waiting Background Literature workers Completed ...')
                    self.pipeline_detail.set(str(msg))
                elif kind == 'topic_begin':
                    n, total, title = msg
                    self.active_index, self.active_total, self.active_theory = n, total, title
                    self.pipeline_title.set(f' Topic  {n:,}/{total:,}:{title}')
                    self.pipeline_detail.set('Stage 1/3 — Reading Wikipedia article text')
                    self.graph_phase.set(f' Processing Build :{title}  ·   Topic  {n:,}/{total:,}  ·   exactly time Display Current Topic ')
                    self.pipeline_percentage.set(0)
                    updated = True
                elif kind == 'topic_phase':
                    phase, completed, total = msg
                    self.pipeline_detail.set('Stage 2/3 — ' + str(phase))
                elif kind == 'search_progress':
                    page, total_pages, candidates = msg
                    self.pipeline_detail.set(
                        f'Stage 2/3 —  multiple Source literature search #  {page}  pages ; Candidate  {candidates:,} papers')
                elif kind == 'topic_found':
                    (total_papers,) = msg
                    self.pipeline_detail.set(f'Stage 3/3 — Building memories from {total_papers:,}  papers Paper ')
                elif kind == 'paper_progress':
                    done, all_papers, added, errors = msg
                    # Progress is emitted after journalled paper commits; a live
                    # view must not reuse its pre-build database-wide counts.
                    updated = True
                    self.pipeline_percentage.set(100*done/max(1, all_papers))
                    self.pipeline_detail.set(
                        f'Stage 3/3 ·  Processed  {done:,}/{all_papers:,}  papers ; new Associations  {added:,}; Error  {errors}')
                elif kind == 'topic_end':
                    n, total, title, state, done, found, added, acknowledged = msg
                    # This branch redraws immediately, before the generic
                    # 'updated' invalidation at the end of poll().
                    self._stats_cache = None
                    self.active_index, self.active_total, self.active_theory = n, total, title
                    self.pipeline_title.set(f' Topic  {n:,}/{total:,}:{title} · {state}')
                    self.pipeline_detail.set(
                        f' Processed  {done:,}/{found:,}  papers ; New Paper Associations  {added:,}; already write  SQLite')
                    self.pipeline_percentage.set(100*done/max(1, found) if found else 0)
                    self.graph_phase.set(f'✓ {title}  Processed ({state}). All Memory Unit keep can see .')
                    try:
                        self.load_topics()
                        self.refresh_history()
                        self.reload_network()
                        self.canvas.draw()  # Draw BEFORE next theory is allowed to start.
                        self.root.update_idletasks()
                        updated = False
                        self._pending_refresh = False
                        self._last_redraw = time.monotonic()
                    finally:
                        acknowledged.set()
                elif kind == "log":
                    self.append_log(msg)
                    self.logline.set(str(msg).splitlines()[0][:250])
                elif kind == "refresh":
                    updated = True
                elif kind == 'math_repair_progress':
                    self.repair_status.set(str(msg))
                elif kind == 'math_repair_done':
                    self._math_repair_active=False
                    self.math_repair_btn.configure(state='normal')
                    if not getattr(self,'_repair_active',False):
                        self.delete_btn.configure(state='normal')
                    self.repair_status.set(f'✓  already scan  {msg["scanned"]:,}  papers Paper , Build  {msg["relations_added"]:,}  edges Source support ')
                    self.append_log(self.repair_status.get());updated=True
                elif kind == 'math_repair_error':
                    self._math_repair_active=False
                    self.math_repair_btn.configure(state='normal')
                    self.repair_status.set(' research relationship scan Failed :'+str(msg)[:240])
                    if not getattr(self,'_repair_active',False):
                        self.delete_btn.configure(state='normal')
                elif kind == 'repair_progress':
                    self.repair_status.set(msg)
                elif kind == 'repair_done':
                    self._repair_active=False
                    self.repair_btn.configure(state='normal')
                    if not (self.collector and self.collector.is_alive()):
                        self.delete_btn.configure(state='normal')
                    self.repair_status.set(
                        f"✓  Repair Completed : Index  {msg['indexed']:,}  items Node , Complete missing  {msg['bridged']:,}  edges reference edges " +
                        ('( before Completed )' if msg['cached'] else ''))
                    self.append_log(self.repair_status.get())
                    updated=True
                elif kind == 'repair_error':
                    self._repair_active=False
                    self.repair_btn.configure(state='normal')
                    if not (self.collector and self.collector.is_alive()):
                        self.delete_btn.configure(state='normal')
                    self.repair_status.set(' Index Repair Failed :'+msg[:180])
                elif kind == 'association_ready':
                    run_id, matched, total_paths = msg
                    self._analysis_active = False
                    self.test_button.configure(state='normal')
                    if self._analysis_loading is not None:
                        try: self._analysis_loading.destroy()
                        except tk.TclError: pass
                    self._analysis_loading = None
                    self.last_run_id = run_id
                    self.status.set(f'✓  activation Completed : match  {matched}  items Memory Unit,{total_paths}  sequence ; already save relationship Evidence ')
                    self.append_log(f' association  #{run_id}:{matched}  items match Node  / {total_paths}  edges Path  /  already store activation sub Network ')
                    try:
                        self.show_results(run_id)
                    except Exception as exc:
                        messagebox.showerror(' Results window Error ', f' Saved association  #{run_id}, but Display Failed :\n{exc}')
                elif kind == 'association_error':
                    self._analysis_active = False
                    self.test_button.configure(state='normal')
                    if self._analysis_loading is not None:
                        try: self._analysis_loading.destroy()
                        except tk.TclError: pass
                    self._analysis_loading = None
                    self.status.set('✕  association query Failed ( please View Error )')
                    self.append_log(' association analysis Failed :'+str(msg))
                    messagebox.showerror(' association analysis Failed ',str(msg)[:700])
                elif kind == "done":
                    self._collector_completion_observed = True
                    self.abc_refresh_status()
                    self.run_btn.configure(state='normal',text='Start Building (Literature → FLIN)')
                    self.retry_btn.configure(state="normal")
                    self.wikiref_btn.configure(state="normal")
                    self.pause_btn.configure(state="disabled", text="Pause")
                    self.stop_btn.configure(state="disabled")
                    self._set_test_available(True)
                    self.delete_btn.configure(state="normal")
                    self.update_worker_panel()
                    if msg=='source_frontier_exhausted':
                        self._refresh_build_completion_state()
                        self.append_log('✓ Current indexed source frontier verified complete; '
                                        'no undiscovered knowledge completeness is implied.')
                    elif msg=='retry_exhausted':
                        self.pipeline_title.set('⚠ Build paused: source/worker recovery exhausted')
                        self.pipeline_detail.set(getattr(self.collector,'_auto_repair_status','')[:540])
                        self.append_log('⚠ Persistent source failures; saved network retained. '
                                        'Check connectivity and retry failed topics.')
                    self.graph_phase.set('This build session has been saved. FLIN data remains in SQLite.')
                    self.status.set({"complete":"✓  this rounds Completed  ·  Data Saved ", "complete_skipped":
                                     f"⚠  this rounds with  {self.skipped_theories}  items search failed Topic  ·  Saved ",
                                     "stopped":"■  already Stop  ·  Saved , can resume Discover ",
                                     "partial":"⚠  this rounds with partially Literature process Failed  ·  Saved ",
                                     "error":"✕  occur Error , please see below Record ",
                                     "service_error":"🚨  literature provider average NOT available , Check connection / Import Index ",
                                     "batch_limit":"✓  this rounds Topic quota already full  ·  can resume Discover ",
                                     "source_frontier_exhausted":"✓ Current source frontier fully processed — no outstanding jobs or source failures",
                                     "retry_exhausted":"⚠ Automatic recovery limit reached — check failed topics/provider and retry",
                                     "frontier_idle":"◇ Temporarily no new sources; completeness unverified",
                                     "discovery_limited":"⚠ Wikipedia  category Source NOT complete  ·  Progress saved , next run can Retry "}.get(msg, " already Finish "))
        except queue.Empty:
            pass
        # Show a truthful heartbeat even during long network/PDF waits.
        # 'Alive' does NOT mean that new memories are currently being ingested.
        now=time.monotonic()
        if self.collector is not None and now-self._last_collector_heartbeat_ui >= 1.0:
            self._last_collector_heartbeat_ui=now
            active=self.collector.is_alive()
            phase=self.collector.phase
            if active and phase=='idle':
                remaining=max(0,math.ceil(self.collector.idle_until-now))
                self.run_btn.configure(state='normal',text='↻  Explore now ( Current waiting )')
                self.status.set(f'◇  provider cooldown  · {remaining}  seconds after Retry ( still in run )')
                self.pipeline_detail.set(f' No new Data write is expected Waiting Status ;{remaining}  seconds until the next check.'
                    ' can click Start button immediately multiple check , or click ` abort and save `.')
            elif active and phase in ('waiting_workers','queue_backpressure'):
                elapsed=int(now-self.collector.phase_started)
                pending=self.collector.jobs.unfinished_tasks
                self.status.set(f'⏳  Waiting  {pending}  items Literature work ( already Waiting  {elapsed}  seconds ); still can abort ')
            elif active and phase in ('discovering','starting'):
                quiet=int(now-self.collector.last_activity)
                if quiet>=40:
                    self.status.set(f'⏳ {quiet}  seconds No new progress return report : can can Processing Waiting Network / Database ; can click abort ')
            elif not active and not self._collector_completion_observed and self.events.empty():
                # Recover a disabled button if the producer exited without a
                # normal completion event (for example a fatal interpreter error).
                self._collector_completion_observed=True
                self.run_btn.configure(state='normal',text='Start Building (Literature → FLIN)')
                self.pause_btn.configure(state='disabled')
                self.stop_btn.configure(state='disabled')
                self.append_log('⚠  Background workers already exit , not yet collect to correct frequently Completed events ; already unlock button locked .')
                self.status.set('⚠ Background workers have exited. Check the logs before restarting.')
        if updated and time.monotonic()-getattr(self,'_last_abc_refresh',0)>20:
            self._last_abc_refresh=time.monotonic()
            self.abc_refresh_status()
        if updated:
            # Committed background writes invalidate previously cached totals.
            # Previously visible=243 / total=0 until a 150s cache expired.
            self._stats_cache = None
            self._pending_refresh = True
        if self._pending_refresh and time.monotonic() - self._last_redraw > (18.0 if len(self.plot_data)>2400 else 5.0):
            self._pending_refresh = False
            self._last_redraw = time.monotonic()
            self.load_topics()
            self.refresh_history()
            self.reload_network()
        # A verified frontier is a dated snapshot; let the user recheck when
        # its finite freshness window expires without restarting the desktop.
        if (self._frontier_shown_complete and
                not (self.collector and self.collector.is_alive()) and
                time.monotonic()-self._last_frontier_status_check > 60):
            self._last_frontier_status_check = time.monotonic()
            self._refresh_build_completion_state()
        self._poll_job = self.root.after(180, self.poll)

    def repair_math_relations(self):
        if getattr(self,'_math_repair_active',False) or getattr(self,'_repair_active',False):return
        if self.collector and self.collector.is_alive():
            messagebox.showinfo('Stop Collection First','Stop and save collection before rebuilding legacy paper-relation memories.')
            return
        self._math_repair_active=True
        self.math_repair_btn.configure(state='disabled')
        self.delete_btn.configure(state='disabled')
        self.repair_status.set(' Processing Background again scan existing Paper , batch by batch save research relationship Memory Unit...')
        def worker():
            try:
                result=repair_math_relation_memories(
                    progress=lambda text:self.events.put(('math_repair_progress',text)))
                self.events.put(('math_repair_done',result))
            except Exception as exc:
                self.events.put(('math_repair_error',str(exc)))
        self._start_background_thread(target=worker, name='MathRelationMigration')

    def _auto_repair(self):
        try:
            with database() as con:
                count=con.execute('SELECT COUNT(*) FROM units').fetchone()[0]
                ready=con.execute("SELECT value FROM network_meta WHERE key='lexical_v5'").fetchone()
            if 0 < count <= 50000 and not ready:
                self.repair_network()
            elif count > 50000 and not ready:
                self.append_log('⚠  large-scale Database NOT automatic run millions records legacy network Repair ; please in maintain window manual launch .')
        except Exception as exc:
            self.append_log(' automatic legacy network upgrade Failed :'+str(exc))

    def repair_network(self):
        if getattr(self,'_repair_active',False):return
        # Never erase existing data, and do not block the Tkinter event loop.
        self._repair_active=True
        self.repair_btn.configure(state='disabled')
        self.delete_btn.configure(state='disabled')
        self.repair_status.set(' Processing Background Index old Node and add missing with literature provider Link ...')
        def go():
            try:
                out=repair_existing_associations(
                    progress=lambda msg:self.events.put(('repair_progress',msg)))
                self.events.put(('repair_done',out))
            except Exception as exc:
                self.events.put(('repair_error',str(exc)))
        self._start_background_thread(target=go, name='BrainMemoryRepair')

    def load_topics(self):
        """Show recent 250 names, not the entire potentially million-title catalog.

        Searching arbitrary older topics remains available through the indexed
        text search. Rebuilding the entire combobox was a major UI stall.
        """
        with database() as con:
            recent=[r[0] for r in con.execute(
                'SELECT name FROM theories ORDER BY rowid DESC LIMIT 250')]
        current=self.filter_var.get()
        base=[' In progress ',' and along building ',' All ']
        choices=base+list(dict.fromkeys(([current] if current not in base else [])+recent))
        self.filter_box.configure(values=choices)
        if not current:self.filter_var.set(' All ')


    def get_network(self):
        """Only load rendered nodes/edges; the SQLite network itself has no display cap."""
        with database() as con:
            now = time.monotonic()
            if self._stats_cache is None or now - self._stats_cache[0] > 12:
                self._stats_cache = (now, stats(con))
            totals = self._stats_cache[1]
            try:
                limit = max(100, int(self.max_nodes.get()))
            except (ValueError,tk.TclError):
                limit = FAST_OVERVIEW_NODES
            limit = min(limit, FAST_OVERVIEW_NODES)
            if self._local_focus_ids:
                limit = min(FAST_LOCAL_NODES, max(limit, len(self._local_focus_ids)))
            allowed_topic = self.filter_var.get()
            if allowed_topic == ' In progress ':
                active_topics = [v['title'] for v in self.worker_states.values()
                    if v['title'] and v['phase'] not in (' Idle ',)]
                active_topics = list(dict.fromkeys(active_topics))
                if not active_topics:
                    allowed_topic = ' All '
            if allowed_topic == ' and along building ':
                if self.active_theory:
                    allowed_topic = self.active_theory
                else:
                    # After restart, show the latest theory rather than mixing all nodes.
                    row = con.execute("SELECT label FROM units WHERE kind='theory' "
                                      "ORDER BY rowid DESC LIMIT 1").fetchone()
                    allowed_topic = row[0] if row else ' All '
            selected = {}
            is_history = not self.timeline_live
            hist_clause = (" AND EXISTS (SELECT 1 FROM build_events h "
                           "WHERE h.unit_id=u.id AND h.action='node' AND h.id<=?)") if is_history else ''
            hist_args = [self.timeline_cursor] if is_history else []
            def add_rows(rows):
                for row in rows:
                    if row[2] not in NODE_STYLES:
                        # Imported unknown unit types have no shape/color and
                        # must not be counted as actually visible 3D nodes.
                        continue
                    if row[2] in ('concept','paper') and not quick_math_node_ok(row[1],row[2]):
                        # 1.5M historic memories remain in SQLite, but are
                        # isolated from the clean mathematical overview.
                        continue
                    if row[2]=='theory' and not math_topic_quality(row[1],row[3] or '')[0]:
                        continue
                    if row[2]=='relation':
                        parts=re.split(r'\s*[—→]\s*',row[1] or '')
                        if len(parts)<3 or not (math_concept_quality(parts[0])[0] and
                                               math_concept_quality(parts[-1])[0]):
                            continue
                    if row[0] not in selected and len(selected) < limit:
                        selected[row[0]] = {'label':row[1], 'kind':row[2],
                             'description':row[3], 'url':row[4],
                             'citations':row[5], 'support':row[6]}
            def get_type(kind,count,order):
                if count<=0: return
                sql = ("SELECT u.id,u.label,u.kind,u.description,u.url,u.citations,u.support "
                       "FROM units u WHERE u.kind=?" + hist_clause +
                       ' ORDER BY ' + order + ' LIMIT ?')
                add_rows(con.execute(sql,[kind]+hist_args+[count]).fetchall())
            if self._local_focus_ids:
                # Prioritise matched seeds; a set's arbitrary order can otherwise
                # omit the very node the user asked to inspect.
                priority=[x for x in self._focus_result_ids if x in self._local_focus_ids]
                visible_ids=list(dict.fromkeys(priority + sorted(self._local_focus_ids)))[:FAST_LOCAL_NODES]
                for begin in range(0, len(visible_ids), 200):
                    part=visible_ids[begin:begin+200]
                    sql=('SELECT u.id,u.label,u.kind,u.description,u.url,u.citations,u.support '
                         'FROM units u WHERE u.id IN ('+
                         ','.join('?' for _ in part)+')'+hist_clause)
                    add_rows(con.execute(sql,part+hist_args).fetchall())
            elif allowed_topic == ' In progress ':
                # Show a balanced sample of the networks being built by ALL workers.
                theory_ids = ['theory:'+title.casefold() for title in active_topics]
                for start in range(0,len(theory_ids),200):
                    ids=theory_ids[start:start+200]
                    sql=('SELECT u.id,u.label,u.kind,u.description,u.url,u.citations,u.support '
                         'FROM units u WHERE u.id IN ('+','.join('?' for _ in ids)+')'+hist_clause)
                    add_rows(con.execute(sql,ids+hist_args).fetchall())
                paper_ids=[]
                for title in active_topics:
                    portion=max(15,int(limit*.53/max(1,len(active_topics))))
                    paper_ids.extend(paper_unit_id(r[0]) for r in con.execute("""
                        SELECT paper_id FROM paper_theories WHERE theory=?
                        ORDER BY rowid DESC LIMIT ?""",(title,portion)).fetchall())
                for start in range(0,len(paper_ids),200):
                    ids=paper_ids[start:start+200]
                    sql=('SELECT u.id,u.label,u.kind,u.description,u.url,u.citations,u.support '
                         'FROM units u WHERE u.id IN ('+','.join('?' for _ in ids)+')'+hist_clause)
                    add_rows(con.execute(sql,ids+hist_args).fetchall())
                chosen_papers=[key for key in selected if key.startswith('paper:')]
                for start in range(0,len(chosen_papers),150):
                    ids=chosen_papers[start:start+150]
                    sql=('SELECT u.id,u.label,u.kind,u.description,u.url,u.citations,u.support '
                        'FROM units u WHERE u.id IN (SELECT e.dst FROM edges e WHERE e.src IN ('+
                        ','.join('?' for _ in ids)+") AND e.kind='paper-concept')" + hist_clause +
                        ' LIMIT ?')
                    add_rows(con.execute(sql,ids+hist_args+[max(0,limit-len(selected))]).fetchall())
            elif allowed_topic == ' All ':
                # Show every type fairly, and fill any unused quota from all types.
                if limit >= totals[2]:
                    # Full-network mode really loads ALL nodes, not only the
                    # first batch of each type or a biased 1,200-node sample.
                    get_type('theory',limit,'u.rowid DESC')
                    get_type('relation',limit-len(selected),'u.rowid DESC')
                    get_type('paper',limit-len(selected),'u.rowid DESC')
                    get_type('concept',limit-len(selected),'u.rowid DESC')
                else:
                    get_type('theory',min(limit//5, max(20,limit//5)), 'u.rowid DESC')
                    get_type('concept',int(limit*.55),'u.support DESC,u.rowid DESC')
                    get_type('paper',int(limit*.25),'u.rowid DESC')
                    get_type('relation',int(limit*.12),'u.support DESC,u.rowid DESC')
                    if len(selected)<limit:
                        get_type('paper',limit-len(selected),'u.citations DESC,u.rowid DESC')
                    if len(selected)<limit:
                        get_type('concept',limit-len(selected),'u.rowid DESC')
                    if len(selected)<limit:
                        get_type('relation',limit-len(selected),'u.rowid DESC')
                    if len(selected)<limit:
                        get_type('theory',limit-len(selected),'u.rowid DESC')
            else:
                theory_id='theory:'+allowed_topic.casefold()
                uidrow=con.execute("""SELECT id,label,kind,description,url,citations,support
                                       FROM units WHERE id=?""",(theory_id,)).fetchone()
                if uidrow:
                    if not is_history or con.execute("""SELECT 1 FROM build_events WHERE unit_id=?
                             AND action='node' AND id<=? LIMIT 1""",
                             (theory_id,self.timeline_cursor)).fetchone():
                        add_rows([uidrow])
                paper_ids = [paper_unit_id(r[0]) for r in con.execute("""
                         SELECT paper_id FROM paper_theories WHERE theory=?
                         ORDER BY score DESC LIMIT ?""",(allowed_topic,max(1000,limit))).fetchall()]
                pquota=max(1,int(limit*.46))
                for offset in range(0,min(len(paper_ids),pquota),250):
                    ids=paper_ids[offset:offset+250]
                    sql=('SELECT u.id,u.label,u.kind,u.description,u.url,u.citations,u.support '
                         'FROM units u WHERE u.id IN ('+','.join('?' for _ in ids)+')'+hist_clause)
                    add_rows(con.execute(sql,ids+hist_args).fetchall())
                # Concepts reachable from the papers chosen for the viewport.
                chosen_papers=[k for k in selected if k.startswith('paper:')]
                cids = set()
                for offset in range(0,len(chosen_papers),250):
                    ids=chosen_papers[offset:offset+250]
                    sql=('SELECT e.dst FROM edges e WHERE e.src IN ('+
                          ','.join('?' for _ in ids)+") AND e.kind='paper-concept' "
                          'GROUP BY e.dst ORDER BY SUM(e.weight) DESC LIMIT ?')
                    cids.update(r[0] for r in con.execute(sql,ids+[limit]).fetchall())
                # Mathematical statement memories attached to these papers.
                relation_ids=set()
                for offset in range(0,len(chosen_papers),250):
                    ids=chosen_papers[offset:offset+250]
                    if not ids:continue
                    sql=("SELECT dst FROM edges WHERE kind='source-relation' AND src IN ("+
                         ','.join('?' for _ in ids)+') GROUP BY dst ORDER BY SUM(weight) DESC LIMIT ?')
                    relation_ids.update(r[0] for r in con.execute(sql,ids+[max(0,limit-len(selected))]).fetchall())
                for offset in range(0,len(relation_ids),250):
                    ids=list(relation_ids)[offset:offset+250]
                    sql=('SELECT u.id,u.label,u.kind,u.description,u.url,u.citations,u.support '
                         'FROM units u WHERE u.id IN ('+
                         ','.join('?' for _ in ids)+')'+hist_clause)
                    add_rows(con.execute(sql,ids+hist_args).fetchall())
                for offset in range(0,len(cids),250):
                    ids=list(cids)[offset:offset+250]
                    sql=('SELECT u.id,u.label,u.kind,u.description,u.url,u.citations,u.support '
                         'FROM units u WHERE u.id IN ('+','.join('?' for _ in ids)+')'+hist_clause)
                    add_rows(con.execute(sql,ids+hist_args).fetchall())
            if not self._local_focus_ids and allowed_topic == ' All ' and len(selected)<min(limit,totals[2]):
                # No biased gap from overlapping top-N type queries.
                allrows=con.execute('SELECT u.id,u.label,u.kind,u.description,u.url,u.citations,u.support '
                                    'FROM units u WHERE 1=1'+hist_clause+' ORDER BY u.rowid DESC',
                                    hist_args).fetchmany(
                                        min(totals[2], max(3000,2*limit)))
                add_rows(allrows)
            # Always include the selected node and the currently matched trail,
            # even when the view is otherwise limited to one subject.
            for keep in dict.fromkeys(([self.chosen] if self.chosen else []) + self.path):
                if keep and keep not in selected:
                    # Historical playback must not leak memories created after
                    # the selected time step just because they were highlighted.
                    if is_history and not con.execute(
                            "SELECT 1 FROM build_events WHERE unit_id=? AND action='node' AND id<=? LIMIT 1",
                            (keep,self.timeline_cursor)).fetchone():
                        continue
                    row=con.execute('SELECT id,label,kind,description,url,citations,support '
                                    'FROM units WHERE id=?',(keep,)).fetchone()
                    if row:
                        if len(selected)>=limit:
                            selected.pop(next(reversed(selected)))
                        add_rows([row])
            if not selected:
                return {},[],totals,{}
            ids=list(selected)
            node_set=set(ids)
            rendered=[]
            # Choose edges whose BOTH endpoints actually appear in the viewport.
            # Limiting raw outgoing rows first causes popular hubs to displace
            # the few meaningful visible edges. The indexed SRC-side scan and
            # tiny temp membership table avoid a full multi-million-edge join.
            con.execute('CREATE TEMP TABLE IF NOT EXISTS _brain_visible(id TEXT PRIMARY KEY) WITHOUT ROWID')
            con.execute('DELETE FROM _brain_visible')
            con.executemany('INSERT OR IGNORE INTO _brain_visible(id) VALUES(?)', ((v,) for v in ids))
            group_size=100
            # Each source batch may contain most of the graph's links. An
            # even per-batch quota hid legitimate hub edges despite unused
            # global draw capacity. Cap each query at the GLOBAL limit, then
            # choose the strongest FAST_DRAW_EDGES overall.
            batch_cap=FAST_DRAW_EDGES
            for begin in range(0,len(ids),group_size):
                part=ids[begin:begin+group_size]
                marks=','.join('?' for _ in part)
                if is_history:
                    sql=("SELECT b.src,b.dst,b.edge_kind,SUM(b.delta),COUNT(*) FROM build_events b "
                         "WHERE b.action='edge' AND b.id<=? AND b.src IN ("+marks+") "
                         "AND b.dst IN (SELECT id FROM _brain_visible) "
                         "GROUP BY b.src,b.dst,b.edge_kind ORDER BY SUM(b.delta) DESC LIMIT ?")
                    rows=con.execute(sql,[self.timeline_cursor]+part+[batch_cap]).fetchall()
                    rendered.extend((a,b,k,float(w),c) for a,b,k,w,c in rows if a in node_set)
                else:
                    # CROSS JOIN pins the outer loop to the indexed source scan,
                    # then does O(log N) membership lookup on each destination.
                    sql=('SELECT e.src,e.dst,e.kind,e.weight,e.support '
                         'FROM edges e INDEXED BY idx_edges_src '
                         'CROSS JOIN _brain_visible v ON v.id=e.dst '
                         'WHERE e.src IN ('+marks+') '
                         'ORDER BY e.weight DESC LIMIT ?')
                    rendered.extend(con.execute(sql,part+[batch_cap]).fetchall())
            if len(rendered)>FAST_DRAW_EDGES:
                rendered.sort(key=lambda edge: edge[3],reverse=True)
                rendered=rendered[:FAST_DRAW_EDGES]
            # The rendered graph and totals must describe the same committed
            # SQLite snapshot even during rapid background writes.
            if len(selected)>totals[2] or len(rendered)>totals[3]:
                totals=stats(con)
                self._stats_cache=(time.monotonic(),totals)
            return selected, rendered, totals, selected

    def refresh_theory_states(self):
        if not hasattr(self, 'theory_states'):
            return
        with database() as con:
            rows = con.execute("SELECT name,state,found,processed FROM theory_progress "
                               "ORDER BY rowid DESC LIMIT 25").fetchall()
        table = self.theory_states
        table.delete(*table.get_children())
        labels = {'complete':' Completed ', 'partial':' partially Failed ', 'interrupted':' Cancelled ',
                  'no_candidates':' no Paper ', 'off_topic':' Quality reject Topic ', 'error':' Error ',
                  'skipped_search':' search failed  ·  already skip passed ', 'running':' In progress '}
        for name, state, found, done in rows:
            display_state = (' not yet Completed ' if state=='running' and
                             (not self.collector or not self.collector.is_alive())
                             else labels.get(state, state))
            table.insert('', 'end', values=(name,display_state, f'{done}/{found}'))

    def reload_network(self):
        try:
            previous_ids=set(self.plot_data)
            nodes, edges, totals, all_nodes = self.get_network()
            # Some updates arrive before the event queue is polled. Never show
            # impossible N/0 ratios or claim a cached total below visible data.
            if len(nodes)>totals[2] or len(edges)>totals[3]:
                with database() as con:
                    totals=stats(con)
                self._stats_cache=(time.monotonic(),totals)
            prefix=' history return put ' if not self.timeline_live else ' fast overview '
            self.graph_stats.set(
                f'{prefix}  Current Display  {len(nodes):,}  Node ,{len(edges):,}  Link   ·  '
                f' all database  {totals[2]:,}  Node ,{totals[3]:,}  Link ')
            self.counter.set(f' already accept Topic  {totals[0]:,}  /   already accept Paper  {totals[1]:,}\n'
                             f' all database Memory Unit {totals[2]:,}  /   already store Directed Link  {totals[3]:,}')
            with database() as con:
                count_rel=con.execute("SELECT COUNT(*) FROM units WHERE kind='relation'").fetchone()[0]
            self.network_math_count.set(f' Candidate research relationship Memory Unit {count_rel:,}| can see Node  {len(nodes):,}')
            self._viewport_empty_reason=(
                ' Database none yet Memory Unit, click right ` Start building ` exactly can Build .' if totals[2]==0 else
                ' Current history time points Not yet Build can Display Memory Unit.' if not self.timeline_live else
                ' this Search range No conforms to Purity filter Memory Unit; all database Data not yet was delete .'
                if self._local_focus_ids else
                ' Current under filtering no qualified Mathematics Memory Unit; all database Data still in  SQLite.')
            self.all_nodes = all_nodes
            self.plot_data = nodes
            self.edges = edges
            # An old selected memory must not remain highlighted after moving
            # to a different sample or historical time step.
            if self.chosen not in nodes:
                self.chosen=None
                self.path=[]
            self.focus_ids=set(getattr(self,'focus_ids',set())) & set(nodes)
            self.coords={key:value for key,value in self.coords.items()
                         if key in nodes and np.all(np.isfinite(value)) and
                         np.max(np.abs(value))<1e6}
            missing=[key for key in nodes if key not in self.coords]
            if missing:
                with database() as con:
                    for off in range(0,len(missing),300):
                        part=missing[off:off+300]
                        rows=con.execute('SELECT unit_id,x,y,z FROM positions WHERE unit_id IN ('+
                                         ','.join('?' for _ in part)+')',part).fetchall()
                        for uid,x,y,z in rows:
                            vector=np.asarray([x,y,z],dtype=float)
                            if np.all(np.isfinite(vector)) and np.max(np.abs(vector))<1e6:
                                self.coords[uid]=vector
            self._layout(nodes, edges)
            self.draw(preserve_view=bool(nodes) and previous_ids==set(nodes))
            self.refresh_theory_states()
        except Exception as exc:
            self.logline.set(f" visualization Error :{exc}")
            self.append_log(f" draw graph Error :{type(exc).__name__}: {exc}")

    def _layout(self, nodes, edges):
        """Incremental O(V+E) placement for big graphs; avoid spring's quadratic cost.

        Stronger edges influence a node's local barycentre more. This remains an
        *approximate* spatial encoding, not exact pairwise metric distances.
        """
        if not nodes:
            self.coords={}
            return
        prev={k:self.coords[k] for k in nodes if k in self.coords}
        if len(prev)==len(nodes):return
        if len(nodes)==1:
            self.coords[next(iter(nodes))]=np.zeros(3)
            return
        if len(nodes)<=300 and not prev:
            graph=nx.Graph()
            graph.add_nodes_from(nodes)
            for u,v,kind,w,c in edges:
                graph.add_edge(u,v,weight=math.log1p(max(0,w))+.2)
            pos=nx.spring_layout(graph,dim=3,seed=17,iterations=25,weight='weight',scale=2)
            self.coords.update({k:np.asarray(v) for k,v in pos.items()})
            return
        keys=list(nodes)
        idmap={k:i for i,k in enumerate(keys)}
        n=len(keys)
        pts=np.zeros((n,3),dtype=float)
        anchored=np.zeros(n,dtype=bool)
        jiggles=np.empty((n,3),dtype=float)
        # Stable seeded layout: theories around a sphere, their papers nearby,
        # concepts around the papers that cite them. This keeps node classes
        # visually distinguishable with 10k+ vertices (no total collapse).
        for i,k in enumerate(keys):
            seed=int.from_bytes(hashlib.blake2b(k.encode(),digest_size=8).digest(),'big')
            rng=np.random.default_rng(seed)
            jiggles[i]=rng.normal(0,1.0,3)
            if k in prev:
                pts[i]=prev[k]
                anchored[i]=True
            elif nodes[k]['kind']=='theory':
                direction=jiggles[i]/max(1e-9,np.linalg.norm(jiggles[i]))
                pts[i]=direction*4.2
                anchored[i]=True   # Stable global clusters; not pinned in SQLite.
            else:
                pts[i]=jiggles[i]*2.7
        # Evidenced ancestry sets the coarse layout: a concept's parent paper
        # (and a paper's parent theory), rather than only an abstract spring.
        papers_parent={}
        concepts_parent={}
        for u,v,kind,w,support in edges:
            if u not in idmap or v not in idmap:continue
            if kind=='theory-paper' and v not in papers_parent:
                papers_parent[v]=u
            elif kind=='paper-concept' and v not in concepts_parent:
                concepts_parent[v]=u
        for child,parent in papers_parent.items():
            idx=idmap[child]
            if not anchored[idx]:
                pts[idx]=pts[idmap[parent]]+jiggles[idx]*.82
        for child,parent in concepts_parent.items():
            idx=idmap[child]
            if not anchored[idx]:
                pts[idx]=pts[idmap[parent]]+jiggles[idx]*.58
        # A few sparse O(E) attraction passes, with low strength to preserve
        # global separation and avoid turning all node types into one dot.
        if edges:
            pairs=[(idmap[u],idmap[v],math.log1p(max(w,0))+.2)
                   for u,v,kind,w,support in edges if u in idmap and v in idmap]
            if pairs:
                arr=np.asarray(pairs,float)
                a=arr[:,0].astype(np.int32);b=arr[:,1].astype(np.int32)
                ws=arr[:,2].astype(float)
                for _ in range(2):
                    sums=np.zeros((n,3),dtype=float)
                    totals=np.zeros(n,dtype=float)
                    np.add.at(sums,a,pts[b]*ws[:,None])
                    np.add.at(sums,b,pts[a]*ws[:,None])
                    np.add.at(totals,a,ws)
                    np.add.at(totals,b,ws)
                    mobile=(totals>0)&(~anchored)
                    if not np.any(mobile):break
                    avg=sums[mobile]/totals[mobile,None]
                    pts[mobile]=.66*pts[mobile]+.34*avg+jiggles[mobile]*.075
        for k,point in zip(keys,pts):
            self.coords[k]=point

    def draw(self, preserve_view=False):
        ax = self.ax
        old_elev, old_azim = getattr(ax, "elev", 24), getattr(ax, "azim", -65)
        old_limits = ((ax.get_xlim(),ax.get_ylim(),ax.get_zlim())
                      if preserve_view and self.axis_xlim is not None else None)
        ax.cla()
        ax.set_facecolor(self.BG)
        ax.view_init(elev=old_elev, azim=old_azim)
        ax.set_axis_off()
        if not self.plot_data:
            ax.text2D(0.5, 0.53, " this View No can Display Memory Unit", transform=ax.transAxes, ha="center",
                      color=self.FG, fontsize=17)
            ax.text2D(0.5, 0.46, getattr(self,"_viewport_empty_reason", "No memory units yet"),
                      transform=ax.transAxes, ha="center",
                      color=self.MUTED, fontsize=10)
            self.canvas.draw_idle()
            return
        vals = np.vstack([self.coords[k] for k in self.plot_data])
        lim = max(1.5, float(np.max(np.abs(vals))) * 1.18) * self.zoom
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_zlim(-lim, lim)
        ax.set_box_aspect([1, 1, 1], zoom=1.28)
        self.axis_xlim = lim
        highlighted = set(zip(self.path[:-1], self.path[1:]))
        # Draw all edges with a few GPU-friendly collections instead of
        # thousands of individual Matplotlib artists.
        groups = {"weak": [], "adjacent": [], "path": []}
        for u, v, kind, weight, support in self.edges:
            group = ("path" if (u, v) in highlighted else
                     "adjacent" if self.chosen in (u, v) else "weak")
            groups[group].append((self.coords[u], self.coords[v]))
        focus=getattr(self,'focus_ids',set())
        if focus:
            groups['focus']=[]
            groups['weak']=[]
            for u,v,kind,weight,support in self.edges:
                if u in focus and v in focus:
                    groups['focus'].append((self.coords[u],self.coords[v]))
        for group, color, alpha, width in (
                ('weak','#54718e',.23,.45),
                ('adjacent','#6da6c8',.80,1.2),
                ('focus','#ffcf76',.85,1.25),
                ('path','#ffcf76',1.0,2.6)):
            if groups.get(group):
                ax.add_collection3d(Line3DCollection(groups[group],colors=color,
                                     alpha=alpha,linewidths=width))
        for kind in ('concept','candidate','relation','paper','theory'):
            spec=NODE_STYLES[kind]
            keys=[k for k in self.plot_data if self.plot_data[k]['kind']==kind]
            if not keys:continue
            count=len(self.plot_data)
            sz=(10 if kind=='concept' else 15 if kind=='relation' else 23 if kind=='paper' else 82) if count>6000 else spec['size']
            if not focus:
                arr=np.asarray([self.coords[k] for k in keys])
                ax.scatter(arr[:,0],arr[:,1],arr[:,2],s=sz,c=spec['color'],
                           marker=spec['marker'],edgecolors='none',depthshade=False,
                           alpha=.60 if kind=='concept' and count>6000 else 1.0)
            else:
                for ks,clr,alpha,factor in (
                    ([k for k in keys if k not in focus],'#445063',.045,.35),
                    ([k for k in keys if k in focus],spec['color'],1.0,2.0)):
                    if ks:
                        arr=np.asarray([self.coords[k] for k in ks])
                        ax.scatter(arr[:,0],arr[:,1],arr[:,2],s=sz*factor,c=clr,
                                   marker=spec['marker'],depthshade=False,
                                   alpha=alpha,edgecolors='none')
        if self.chosen in self.coords:
            p = self.coords[self.chosen]
            ax.scatter([p[0]], [p[1]], [p[2]], s=225, facecolors='none',
                       edgecolors='#ffffff', linewidths=1.6, alpha=1, depthshade=False)
            ax.text(p[0], p[1], p[2], " " + self.plot_data[self.chosen]["label"][:48],
                    color="#ffffff", fontsize=10)
        if focus:
            positions=np.asarray([self.coords[k] for k in focus if k in self.coords])
            if len(positions):
                mid=positions.mean(axis=0)
                dist=np.linalg.norm(positions-mid,axis=1)
                radius=max(.20,float(np.quantile(dist,.75))*1.5)
                for i,fun in enumerate((ax.set_xlim,ax.set_ylim,ax.set_zlim)):
                    fun(mid[i]-radius,mid[i]+radius)
        if old_limits is not None:
            for limits,setlim in zip(old_limits,(ax.set_xlim,ax.set_ylim,ax.set_zlim)):
                setlim(*limits)
        self.canvas.draw_idle()

    def _nearest(self, event):
        if (event.inaxes != self.ax or not self.plot_data or
                event.x is None or event.y is None):
            return None
        keys=list(self.plot_data)
        arr=np.asarray([self.coords[k] for k in keys])
        p=proj3d.proj_transform(arr[:,0],arr[:,1],arr[:,2],self.ax.get_proj())
        pixels=self.ax.transData.transform(np.column_stack((p[0],p[1])))
        distances=np.sum((pixels-np.array([event.x,event.y]))**2,axis=1)
        idx=int(np.argmin(distances))
        return keys[idx] if distances[idx]<18**2 else None

    def on_click(self, event):
        if event.button != 1:
            return
        match = self._nearest(event)
        if match is not None:
            self.select(match)
        if match is not None and event.key and "shift" in event.key:
            self.dragging = (match, event.x, event.y)
            # Matplotlib itself rotates on left-drag; disable while moving nodes.
            self.ax.mouse_init(rotate_btn=[3], zoom_btn=[2])

    def on_drag(self, event):
        if not self.dragging or not self.axis_xlim:
            return
        key, prev_x, prev_y = self.dragging
        if event.x is None or event.y is None:
            return
        dx, dy = event.x - prev_x, event.y - prev_y
        azim = math.radians(self.ax.azim)
        scale = 2 * self.axis_xlim / max(150, min(self.ax.bbox.width, self.ax.bbox.height))
        # Screen-space approximate move in the viewer-facing XY plane.
        right = np.array([math.cos(azim), math.sin(azim), 0.0])
        up = np.array([-math.sin(azim), math.cos(azim), 0.55])
        self.coords[key] = self.coords[key] + scale * (dx * right + dy * up)
        self.dragging = (key, event.x, event.y)
        self.draw(preserve_view=True)

    def on_release(self, event):
        if self.dragging:
            key = self.dragging[0]
            self.dragging = None
            self.ax.mouse_init(rotate_btn=[1], zoom_btn=[3])
            self.persist_positions(keys=[key])

    def on_scroll(self, event):
        if event.inaxes != self.ax or not self.axis_xlim or event.button not in ('up','down'):
            return
        factor = 0.85 if event.button == "up" else 1.18
        self.zoom = max(0.08, min(12.0, self.zoom * factor))
        for getlim, setlim in ((self.ax.get_xlim, self.ax.set_xlim),
                               (self.ax.get_ylim, self.ax.set_ylim),
                               (self.ax.get_zlim, self.ax.set_zlim)):
            a, b = getlim()
            middle = (a + b) / 2
            half = max(0.04, (b - a) / 2 * factor)
            setlim(middle - half, middle + half)
        self.canvas.draw_idle()

    def reset_camera(self):
        self.zoom = 1.0
        self.ax.view_init(elev=24, azim=-65)
        self.draw()

    def select(self, key, repaint=True):
        if key not in self.all_nodes:
            return
        self.chosen = key
        self.path = []
        node = self.all_nodes[key]
        with database() as con:
            matches = con.execute("""SELECT u.label,e.weight,e.kind FROM edges e JOIN units u ON u.id=e.dst
                              WHERE e.src=? ORDER BY e.weight DESC LIMIT 8""", (key,)).fetchall()
            origins = con.execute("""SELECT p.title,m.quote,p.url FROM mentions m JOIN papers p
                              ON p.id=m.paper_id WHERE m.unit_id=? LIMIT 4""", (key,)).fetchall()
        info = f"{node['label']}\n\n types type :{node['kind']}\n"
        if node["kind"] == "paper":
            info += f" citation imes count :{node['citations']}\n"
        if node["kind"] in ("concept","relation"):
            info += f" Source support imes count :{node['support']}\n"
        if node["kind"] == "relation":
            with database() as con:
                quote_rows=con.execute("SELECT sentence,source_id,source_url FROM relation_evidence WHERE relation_id=? LIMIT 6",(key,)).fetchall()
            info += "\n Source Candidate statement ( not yet automatic research Validate ):\n"+"\n".join(
                f'• {sentence[:250]} [{source_id}]' for sentence,source_id,url in quote_rows)
        info += "\n" + (node["description"] or " Current only title information ")[:2500]
        if matches:
            info += "\n\n Directed Link ( Co-occurrence / Source lookup , not causal relationship ; Weight )\n" + "\n".join(
                f"→ {label[:52]} ({w:.2f})" for label, w, kind in matches)
        if origins:
            info += "\n\n support Literature \n" + "\n".join(
                f"• {title[:75]}" for title, quote, url in origins)
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", info)
        self.detail.configure(state="disabled")
        if key in self.coords and repaint:
            self.draw(preserve_view=True)
        elif key not in self.coords:
            self.logline.set(' Not yet in graph above load This Memory Unit.')

    def awaken_selected(self):
        """Use the selected memory as the next association input."""
        if not self.chosen:
            messagebox.showinfo('Select a Memory Unit First','Select a concept or research-relation memory in the 3D graph.')
            return
        with database() as con:
            row=con.execute('SELECT label,kind FROM units WHERE id=?',(self.chosen,)).fetchone()
        if not row:return
        label,kind=row
        # A relation already encodes a complete claim. Feed the subject phrase
        # back into the lexical matching system to retrieve neighboring claims.
        if kind=='relation':
            label=label.split('  — ')[0]
        self.test_var.set(label)
        self.test_text()

    def search_unit(self):
        q=self.search_var.get().strip()
        if not q:return
        seeds=self._find_seed_nodes(q)
        if not seeds:
            self.logline.set(f' cannot find can recognize Memory Unit:{q}( can click Repair Index )')
            return
        uid,label,phrase,score=seeds[0]
        self.focus_memory()
        self.logline.set(f' term form / concept match :{q} → {label}( score  {score:.2f})')

    def open_source(self):
        node = self.all_nodes.get(self.chosen, {})
        url = node.get("url", "")
        if url and url.startswith("https://"):
            webbrowser.open(url)
        else:
            self.logline.set(" This Memory Unit No can open start external Source URL .")

    def associate(self):
        if self.chosen is None:
            self.logline.set(" Please first in graph in select one items Memory Unit, then click ` trigger association `.")
            return
        with database() as con:
            path, visited_edges, last = [self.chosen], set(), None
            for _ in range(8):
                current = path[-1]
                choices = con.execute("SELECT dst,weight FROM edges WHERE src=?", (current,)).fetchall()
                choices = [(v, max(float(w), .0001)) for v, w in choices
                           if (current, v) not in visited_edges and v != last]
                if not choices:
                    break
                dest = random.choices([v for v, w in choices],
                                      weights=[w for v, w in choices])[0]
                visited_edges.add((current, dest))
                last = current
                path.append(dest)
        self.path = [uid for uid in path if uid in self.plot_data]
        labels = [self.all_nodes.get(k, {}).get("label", k) for k in path]
        self.logline.set(" association path :" + " → ".join(x[:18] for x in labels)[:210] +
                         ('( partially Node NOT in fast overview , please use Search Locate in-depth View )'
                          if len(self.path)!=len(path) else ''))
        self.draw(preserve_view=True)

    def persist_positions(self, keys=None):
        # Coordinates are also persisted, separate from all network topology.
        subset = keys or list(self.coords)
        with database() as con:
            con.executemany("""INSERT INTO positions(unit_id,x,y,z) VALUES(?,?,?,?)
                    ON CONFLICT(unit_id) DO UPDATE SET x=excluded.x,y=excluded.y,z=excluded.z""",
                [(k, *map(float, self.coords[k])) for k in subset if k in self.coords])

    def open_export_dialog(self):
        """Nonblocking scalable export, with cancel, progress, and clear file format."""
        if getattr(self, '_export_active', False):
            messagebox.showinfo('Export in Progress','Another network export is already running.',parent=self.root)
            return
        win = tk.Toplevel(self.root)
        win.title('Brain_Project ·  Export complete Memory Unit Network ')
        win.geometry('590x390')
        win.configure(bg=self.PANEL)
        win.transient(self.root)
        main = ttk.Frame(win, style='Side.TFrame',padding=20)
        main.pack(fill='both',expand=True)
        self.label(main,' complete Network Export ',note=False).pack(anchor='w',pady=(0,7))
        self.label(main,'Complete FLIN export reads abc_units/abc_edges, not the legacy units/edges or sampled 3D view.',
                   note=True,wraplength=530).pack(anchor='w')
        mode = tk.StringVar(value='sqlite')
        row = ttk.Frame(main,style='Side.TFrame');row.pack(fill='x',pady=(12,7))
        ttk.Radiobutton(row,text=' can portable  JSONL.gz',value='portable',variable=mode,style='Dark.TRadiobutton').pack(side='left')
        ttk.Radiobutton(row,text='Full SQLite + FLIN graph (recommended)',value='sqlite',variable=mode,style='Dark.TRadiobutton').pack(side='left',padx=18)
        sources = tk.BooleanVar(value=True)
        chk=ttk.Checkbutton(main,text='JSONL  simultaneously Export Paper , original passage Evidence and literature provider ',
                            variable=sources,style='Dark.TCheckbutton')
        chk.pack(anchor='w',pady=(2,8))
        info=tk.StringVar(value='SQLite mode saves association.sqlite3 (restorable) and flin_graph.sqlite3 (all FLIN nodes/links for analysis).')
        self.label(main,'',textvariable=info,note=True,wraplength=530).pack(anchor='w')
        def change_mode(*_):
            chk.configure(state='normal' if mode.get()=='portable' else 'disabled')
        mode.trace_add('write',change_mode)
        status=tk.StringVar(value='Ready. Select Output folder .')
        self.label(main,'',textvariable=status,note=True,wraplength=530).pack(anchor='w',pady=(15,5))
        pb=ttk.Progressbar(main,mode='determinate',maximum=100)
        pb.pack(fill='x')
        buttons=ttk.Frame(main,style='Side.TFrame');buttons.pack(fill='x',pady=(15,5))
        cancel_flag=threading.Event()
        messages=queue.Queue()
        working={'value':False}

        def start():
            dest=filedialog.askdirectory(parent=win,title=' choose Export above level folder ',
                                         initialdir=str(Path.home()))
            if not dest:
                return
            if self.collector is not None and self.collector.is_alive():
                go=messagebox.askyesno('Export During Collection?',
                    ' Current building Processing write Database . for avoid lengthy Time Export cause  WAL  form long , recommendation pause or abort building then Export .\n still must resume ? ?',
                    parent=win)
                if not go:
                    return
            if not DB_PATH.is_file():
                messagebox.showerror('No Data to Export','The memory network database could not be found.',parent=win)
                return
            self._export_active=True
            self._export_cancel_flag=cancel_flag
            working['value']=True
            selected_mode=mode.get()
            selected_sources=sources.get()
            selected_network_db=Path(DB_PATH).resolve()
            cancel_flag.clear()
            start_button.configure(state='disabled')
            status.set(' prepare Export ,Please Wait...')
            def worker():
                try:
                    path=export_memory_network(dest,mode=selected_mode,with_sources=selected_sources,
                        stop_event=cancel_flag,source_db_path=selected_network_db,
                        progress=lambda stage,done,total: messages.put(('progress',stage,done,total)))
                    messages.put(('done',str(path)))
                except NetworkExportCancelled as exc:
                    messages.put(('cancel',str(exc)))
                except Exception as exc:
                    messages.put(('error',type(exc).__name__+': '+str(exc)))
            self._start_background_thread(target=worker, name='brain_network_export')

        start_button=ttk.Button(buttons,text=' choose folder and Start Export ',style='Accent.TButton',command=start)
        start_button.pack(side='left',fill='x',expand=True,padx=(0,6))
        def abort_or_close():
            if working['value']:
                cancel_flag.set()
                status.set(' Processing cancel and cleanup temporary files ...')
            else:
                win.destroy()
        cancel_button=ttk.Button(buttons,text=' cancel / close ',style='Dark.TButton',command=abort_or_close)
        cancel_button.pack(side='right')
        win.protocol('WM_DELETE_WINDOW',abort_or_close)

        def pump():
            if not win.winfo_exists():
                return
            last_progress=None
            while True:
                try: entry=messages.get_nowait()
                except queue.Empty: break
                if entry[0]=='progress':
                    last_progress=entry
                elif entry[0] in ('done','error','cancel'):
                    working['value']=False
                    self._export_active=False
                    start_button.configure(state='normal')
                    if entry[0]=='done':
                        pb.configure(value=100)
                        status.set('✓ FLIN export verified: '+entry[1])
                        report_path=Path(entry[1])/'FLIN_EXPORT_VERIFICATION.json'
                        summary=''
                        if report_path.is_file():
                            counts=json.loads(report_path.read_text(encoding='utf-8'))['counts']
                            summary=(f'\nFLIN active units: {counts["flin_units_active"]:,}'
                                     f'\nFLIN total units: {counts["flin_units_all"]:,}'
                                     f'\nFLIN directed edges: {counts["flin_edges_all"]:,}')
                        self.append_log('✓ Verified FLIN export: '+entry[1]+summary)
                        messagebox.showinfo('FLIN Export Verified',
                            'Exported ALL FLIN memory units and directed edges.\n'
                            'Open flin_graph.sqlite3 for standalone graph analysis, or\n'
                            'association.sqlite3 to restore the complete application.\n'
                            +entry[1]+summary,parent=win)
                    elif entry[0]=='cancel':
                        status.set(entry[1])
                    else:
                        status.set('✕ Export Failed:'+entry[1])
                        self.append_log('✕  NetworkExport Failed:'+entry[1])
                        messagebox.showerror('Export Failed',entry[1],parent=win)
            if last_progress is not None and working['value']:
                _,stage,done,total=last_progress
                if total:
                    pct=min(100,int(100*done/max(1,total)))
                    pb.configure(value=pct)
                    status.set(f'{stage} |  Node ＋ Link already Export  {done:,}/{total:,}({pct}%)')
                else:
                    status.set(stage)
            win.after(180,pump)
        pump()

    def save_snapshot(self):
        import datetime
        self.persist_positions()
        dest = DATA_DIR / "snapshots"
        dest.mkdir(parents=True, exist_ok=True)
        name = "brain_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            with database() as src, sqlite3.connect(str(dest / (name + ".sqlite3"))) as dst:
                src.backup(dst)
            # GraphML is optional on huge networks; SQLite backup always contains everything.
            with contextlib.closing(sqlite3.connect(str(dest / (name + '.sqlite3')))) as exported:
                counts=flin_export_counts(exported)
            _verify_sqlite_graph_file(dest / (name + '.sqlite3'),counts)
            skip_graphml = counts['flin_units_all'] > 65000 or counts['flin_edges_all'] > 180000
            if skip_graphml:
                self.append_log(' large-scale Network already backup  SQLite; Node / Link above passed  GraphML  install all Export maximum , omit passed  GraphML.')
            if not skip_graphml:
                self._export_graphml(dest / (name + '.graphml'))
            self.append_log('✓ Verified FLIN SQLite snapshot: '+str(dest/(name+'.sqlite3'))+
                            f' | units {counts["flin_units_all"]:,}, edges {counts["flin_edges_all"]:,}')
            messagebox.showinfo('Network Snapshot Saved',
                'SQLite  all amount backup Completed .' + (' large-scale Network omit passed  GraphML.' if skip_graphml else 'GraphML  also already Export .')
                + '\n store Path :\n' + str(dest))
        except Exception as e:
            self.append_log('✕ Save Snapshot Failed :' + str(e))
            messagebox.showerror('Failed to Save File',str(e))

    def _export_graphml(self, path):
        """Export the ACTIVE FLIN graph, not the separate legacy research graph."""
        with database() as con:
            graph = nx.DiGraph()
            for uid,label,status,quality,evidence_count in con.execute(
                    'SELECT id,label,status,quality,evidence_count FROM abc_units'):
                graph.add_node(uid,label=label or '',status=status,
                               quality=int(quality),evidence_count=int(evidence_count))
            for src,dst,weight,observations in con.execute(
                    'SELECT src,dst,weight,observations FROM abc_edges'):
                if src not in graph or dst not in graph:
                    raise RuntimeError('FLIN edge has a missing endpoint: '+str(src)+' -> '+str(dst))
                graph.add_edge(src,dst,weight=float(weight),
                               observations=int(observations))
        nx.write_graphml(graph,path)

    def open_scholar(self):
        info = self.all_nodes.get(self.chosen, {}) if hasattr(self, "all_nodes") else {}
        title = info.get("label") or self.active_theory or "research subject"
        url = "https://scholar.google.com/scholar?q=" + urllib.parse.quote('"' + title + '"')
        webbrowser.open(url)
        self.append_log(" in open in browser  Google Scholar  audit :" + title[:90])

    def refresh_history(self, reset=False):
        with database() as con:
            maximum = int(con.execute("SELECT COALESCE(MAX(id),0) FROM build_events").fetchone()[0])
        self.timeline_latest = maximum
        self.timeline_scale.configure(to=max(1, maximum))
        if self.timeline_live or reset:
            self.timeline_cursor = maximum
            self.timeline_live = True
        else:
            self.timeline_cursor = min(self.timeline_cursor, maximum)
        self._updating_timeline = True
        self.timeline_scale.set(self.timeline_cursor)
        self._updating_timeline = False
        self.update_step_label()

    def update_step_label(self):
        self.step_info.set(f"{self.timeline_cursor:,} / {self.timeline_latest:,}  steps " +
                           (" ·  exactly time " if self.timeline_live else " ·  history return put "))
        if self.timeline_cursor <= 0:
            self.step_description.set(" none yet events . click ` one key build network ` Start from  Wikipedia  collect set .")
            return
        with database() as con:
            row = con.execute("SELECT action,label,unit_id,src,dst FROM build_events WHERE id<=? "
                              "ORDER BY id DESC LIMIT 1", (self.timeline_cursor,)).fetchone()
        if row:
            action, label, uid, src, dst = row
            if action == "node":
                self.step_description.set("＋ Memory Unit：" + str(label or uid)[:110])
            else:
                self.step_description.set("→  Directed Link :" + str(label or "") + "   " +
                                          str(src or "")[-36:] + " → " + str(dst or "")[-36:])

    def history_seek(self, value):
        if self._updating_timeline:
            return
        seek = max(0, min(self.timeline_latest, int(round(float(value)))))
        if seek == self.timeline_cursor and not self.timeline_live:
            return
        self.timeline_cursor = seek
        self.timeline_live = (seek >= self.timeline_latest and not self.replaying)
        self.update_step_label()
        self.reload_network()

    def history_prev(self):
        self.replaying = False
        self.timeline_live = False
        self.timeline_cursor = max(0, self.timeline_cursor - 1)
        self.refresh_history()
        self.reload_network()

    def history_next(self):
        self.replaying = False
        self.timeline_live = False
        self.timeline_cursor = min(self.timeline_latest, self.timeline_cursor + 1)
        self.refresh_history()
        self.reload_network()

    def history_live_view(self):
        self.replaying = False
        if self.replay_job is not None:
            self.root.after_cancel(self.replay_job)
            self.replay_job = None
        self.timeline_live = True
        self.refresh_history()
        self.reload_network()

    def history_play(self):
        if self.replaying:
            self.replaying = False
            return
        if self.timeline_cursor >= self.timeline_latest:
            self.timeline_cursor = 0
        self.timeline_live = False
        self.replaying = True
        self.history_tick()

    def history_tick(self):
        self.replay_job = None
        if not self.replaying:
            return
        if self.timeline_cursor >= self.timeline_latest:
            self.replaying = False
            return
        self.timeline_cursor += 1
        self.refresh_history()
        self.reload_network()
        self.replay_job = self.root.after(350, self.history_tick)

    def close(self):
        """Cooperative, non-blocking shutdown with Tk destruction on UI thread.

        In FLIN v16 daemon workers could outlive root.destroy(). Their last
        references to Tk variables/images were then sometimes finalized in
        non-main threads, raising 'main thread is not in main loop'.
        """
        if self._closing:
            return
        self._closing = True
        self.stop_event.set()
        self.pause_event.clear()
        for stop in tuple(getattr(self,'generation_jobs',{}).values()):
            stop.set()
        for stop in tuple(getattr(self,'iteration_jobs',{}).values()):
            stop.set()
        for attr in ('_network_import_cancel_event', '_export_cancel_flag'):
            event = getattr(self, attr, None)
            if event is not None:
                event.set()
        # Prevent callback access to widgets after the root is destroyed.
        for attr in ('replay_job','_poll_job','_auto_repair_job'):
            job = getattr(self, attr, None)
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self,attr,None)
        self.replaying = False
        self._shutdown_started = time.monotonic()
        try:
            self.status.set(' Processing stop safely Background work and save Data ,Please Wait...')
        except tk.TclError:
            pass
        self._finish_shutdown()

    def _finish_shutdown(self):
        """Only the Tk main thread can destroy the interpreter and plots."""
        if not self._closing:
            return
        # Collector joins its internal topic workers before it exits, so only
        # the outer collector needs tracking here. Do not join on the GUI thread:
        # some HTTP/model requests can take time to honor cancellation.
        living = {thread for thread in self._background_threads if thread.is_alive()}
        self._background_threads = living
        if self.collector is not None and self.collector.is_alive():
            living = living | {self.collector}
        if living:
            elapsed = int(time.monotonic() - self._shutdown_started)
            names = ', '.join(sorted({t.name for t in living})[:3])
            try:
                self.status.set(f' Processing wait  {len(living)}  items Background work save / exit ({elapsed}  seconds ):{names}')
            except tk.TclError:
                pass
            self._shutdown_job = self.root.after(200, self._finish_shutdown)
            return
        self._shutdown_job = None
        try:
            self.persist_positions()
        except Exception:
            pass
        # Closing pyplot figures, then releasing image/variable finalizers from
        # this very thread prevents their Tcl calls from a daemon worker.
        try:
            plt.close('all')
        except Exception:
            pass
        import gc
        gc.collect()
        self.root.destroy()
        gc.collect()

    def run(self):
        self.root.mainloop()



class ABCNetworkWindow(NetworkWindow):
    """Single-interface FLIN mathematics workspace, no legacy-memory ingestion."""

    def __init__(self):
        # Existing users' original graph is never converted, deleted or reused.
        # Switching to an isolated SQLite database also avoids ambiguous totals.
        try:
            if active_network_record()['id']=='legacy':
                name='FLIN_Mathematics_'+datetime.datetime.now().strftime('%Y%m%d')
                create_empty_network(name,activate=True,domain='mathematics')
        except (OSError,sqlite3.Error,ValueError) as exc:
            print('FLIN network setup warning:',exc,file=sys.stderr)
        with database() as con:abc_enable(con)
        super().__init__()
        with database() as con:
            st=abc_status(con)
        self.has_started=st['active']>0
        self.status.set('FLIN mathematical network | Learn directly from verified source inputs')
        self.graph_phase.set('First qualified input creates a triggerable memory; evidence reinforces associations and influences routing probability.')
        self.abc_refresh_status()
        self.reload_network()

    def _auto_repair(self):
        # Never call old units/edges migrations during an ABC-only session.
        return

    def refresh_history(self, reset=False):
        self.timeline_latest=0;self.timeline_cursor=0;self.timeline_live=True

    def load_topics(self):
        if not hasattr(self,'theory_states'):return
        self.refresh_theory_states()

    def refresh_theory_states(self):
        with database() as con:
            rows=con.execute('SELECT name,state,found,processed FROM abc_topics '
                             'ORDER BY updated DESC LIMIT 25').fetchall()
        table=self.theory_states
        for item in table.get_children():table.delete(item)
        for name,state,found,done in rows:
            table.insert('','end',values=(name,state,f'{done}/{found}'))

    def get_network(self):
        """Bounded 3D view of actual FLIN units and actual directed FLIN edges."""
        with database() as con:
            totals=abc_graph_totals(con)
            limit=FAST_OVERVIEW_NODES
            selected={}
            if self._local_focus_ids:
                ids=list(dict.fromkeys(self._focus_result_ids+
                    sorted(self._local_focus_ids)))[:FAST_LOCAL_NODES]
                for start in range(0,len(ids),160):
                    part=ids[start:start+160]
                    sql=('SELECT id,label,definition,status,evidence_count FROM abc_units '
                         'WHERE id IN ('+','.join('?' for _ in part)+')')
                    for uid,label,definition,status,evidence in con.execute(sql,part):
                        selected[uid]={'label':label,
                            'kind':'concept' if status=='active' else 'candidate',
                            'description':definition,'url':'',
                            'citations':0,'support':evidence}
            else:
                # Prioritize active associative memories, then candidates.
                active_cap=int(limit*.79)
                for uid,label,definition,status,evidence in con.execute(
                      'SELECT id,label,definition,status,evidence_count FROM abc_units '
                      "WHERE status='active' ORDER BY evidence_count DESC,rowid DESC LIMIT ?",
                      (active_cap,)):
                    selected[uid]=dict(label=label,kind='concept',description=definition,
                        url='',citations=0,support=evidence)
                for uid,label,definition,status,evidence in con.execute(
                      'SELECT id,label,definition,status,evidence_count FROM abc_units '
                      "WHERE status='candidate' ORDER BY evidence_count DESC,rowid DESC LIMIT ?",
                      (limit-len(selected),)):
                    selected[uid]=dict(label=label,kind='candidate',description=definition,
                        url='',citations=0,support=evidence)
                if len(selected)<limit:
                    for uid,label,definition,status,evidence in con.execute(
                          'SELECT id,label,definition,status,evidence_count FROM abc_units '
                          "WHERE status='active' ORDER BY evidence_count DESC,rowid DESC "
                          'LIMIT ? OFFSET ?', (limit-len(selected),active_cap)):
                        selected[uid]=dict(label=label,kind='concept',description=definition,
                            url='',citations=0,support=evidence)
            if not selected:return {},[],totals,{}
            ids=list(selected)
            visible=set(ids)
            edges=[]
            for start in range(0,len(ids),75):
                part=ids[start:start+75]
                sql=('SELECT src,dst,weight,observations FROM abc_edges WHERE src IN ('+
                      ','.join('?' for _ in part)+') ORDER BY weight DESC LIMIT 1400')
                for a,b,w,n in con.execute(sql,part):
                    if b in visible and a!=b:
                        edges.append((a,b,'abc_learned',float(w),int(n)))
            edges=sorted(edges,key=lambda e:-e[3])[:FAST_DRAW_EDGES]
            # URLs only needed for displayed nodes; loaded lazily upon selection.
            return selected,edges,totals,dict(selected)

    def reload_network(self):
        try:
            previous=set(self.plot_data)
            nodes,edges,totals,all_nodes=self.get_network()
            with database() as con:status=abc_status(con)
            self.graph_stats.set(f"FLIN 3D: showing {len(nodes):,} memories / {len(edges):,} displayed links; "
                                 f"all triggerable {status['active']:,}; legacy candidates {status['candidates']:,}; "
                                 f"directed links {status['edges']:,}")
            self.counter.set(f"Source topics {status['topics']:,} / papers and Wikipedia {status['learned_sources']:,}\n"
                             f"FLIN triggerable memories {status['active']:,} / old candidates {status['candidates']:,}")
            self.network_math_count.set(f"FLIN links {status['edges']:,} | shortcuts {status['shortcuts']:,} | "
                                        f"effective input clusters {status['input_clusters']:,}")
            self._viewport_empty_reason='Start building to create FLIN memories directly from mathematics literature.'
            self.all_nodes=all_nodes;self.plot_data=nodes;self.edges=edges
            if self.chosen not in nodes:self.chosen=None;self.path=[]
            self.focus_ids=set(getattr(self,'focus_ids',set()))&set(nodes)
            self.coords={k:v for k,v in self.coords.items() if k in nodes and
                         np.all(np.isfinite(v))}
            missing=[k for k in nodes if k not in self.coords]
            with database() as con:
                for start in range(0,len(missing),200):
                    part=missing[start:start+200]
                    sql=('SELECT unit_id,x,y,z FROM abc_positions WHERE unit_id IN ('+
                        ','.join('?' for _ in part)+')')
                    for uid,x,y,z in con.execute(sql,part):
                        pos=np.asarray([x,y,z],dtype=float)
                        if np.all(np.isfinite(pos)):self.coords[uid]=pos
            self._layout(nodes,edges)
            self.draw(preserve_view=bool(nodes) and previous==set(nodes))
            self.refresh_theory_states()
        except Exception as exc:
            self.append_log('FLIN 3D rendering error: '+str(exc)[:250])
            self.logline.set('FLIN plot refresh failed: '+str(exc)[:150])

    def persist_positions(self,keys=None):
        subset=keys or list(self.coords)
        with database() as con:
            with con:
                con.executemany("""INSERT INTO abc_positions(unit_id,x,y,z) VALUES(?,?,?,?)
                    ON CONFLICT(unit_id) DO UPDATE SET x=excluded.x,y=excluded.y,
                    z=excluded.z""",[(k,*[float(x) for x in self.coords[k]])
                    for k in subset if k in self.coords])

    def select(self,key,repaint=True):
        if key not in self.plot_data:return
        self.chosen=key;self.path=[]
        node=self.plot_data[key]
        with database() as con:
            edges=con.execute("""SELECT u.label,e.weight,e.observations FROM abc_edges e
                JOIN abc_units u ON u.id=e.dst AND u.status='active'
                WHERE e.src=? AND e.weight>0 ORDER BY e.weight DESC LIMIT 10""",(key,)).fetchall()
            outgoing_total=con.execute("""SELECT COALESCE(SUM(e.weight),0.) FROM abc_edges e
                JOIN abc_units u ON u.id=e.dst AND u.status='active'
                WHERE e.src=? AND e.weight>0""",(key,)).fetchone()[0]
            exposure=con.execute('SELECT exposures FROM abc_ssrs WHERE unit_id=?',
                                 (key,)).fetchone()
            evidence=con.execute("""SELECT s.title,e.explanation,e.url FROM abc_evidence e
                LEFT JOIN abc_sources s ON s.id=e.source_id
                WHERE e.unit_id=? ORDER BY e.source_id LIMIT 7""",(key,)).fetchall()
        self._selected_abc_sources=[r[2] for r in evidence if r[2].startswith('https://')]
        lines=[node['label'],'','Status: '+('Established / Triggerable' if node['kind']=='concept' else 'Legacy candidate'),
               f"Effective input exposures: {exposure[0] if exposure else 0}",
               f"Independent sources: {node['support']}", '',node['description'][:850] or 'No text description']
        if edges:
            lines+=['','FLIN Directed Links (weight / observations / routing probability)']
            lines += [f'→ {label[:65]}  (w={w:.2f} / {n}  imes  / P≈{w/outgoing_total:.1%})'
                      for label,w,n in edges]
            lines+=[' routing probability by Currently eligible outgoing links Weight normalize ; prevent backtracking / Revisits Limit can can change proportions .']
        else:
            lines+=['','This memory can receive effective input but currently has no eligible outgoing links.']
        if evidence:
            lines+=['','Original source statements (not verified theorems)']
            lines += [f'• {(title or " Source ")[:85]}:{sentence[:210]}'
                      for title,sentence,url in evidence]
        self.detail.configure(state='normal');self.detail.delete('1.0','end')
        self.detail.insert('1.0','\n'.join(lines));self.detail.configure(state='disabled')
        if repaint:self.draw(preserve_view=True)

    def open_source(self):
        urls=getattr(self,'_selected_abc_sources',[])
        if urls:webbrowser.open(urls[0])
        else:self.logline.set('No usable source URL for this FLIN memory.')

    def focus_memory(self):
        q=self.search_var.get().strip()
        if not q:return
        with database() as con:
            names=[v.strip() for v in re.split(r'[,，;；]+',q) if v.strip()][:8]
            origins=[]
            for name in names:
                rows=con.execute("""SELECT id,label FROM abc_units WHERE label=? COLLATE NOCASE
                    UNION SELECT id,label FROM abc_units WHERE label LIKE ? COLLATE NOCASE
                    ORDER BY label LIMIT 8""",(name,'%'+name+'%')).fetchall()
                origins.extend(uid for uid,label in rows)
            origins=list(dict.fromkeys(origins))[:25]
            if not origins:
                self.search_hint.set(' cannot find  FLIN Memory Unit; can through passed building Add Literature input .');return
            keep=set(origins)
            for uid in origins[:8]:
                keep.update(x[0] for x in con.execute(
                    'SELECT dst FROM abc_edges WHERE src=? ORDER BY weight DESC LIMIT 60',(uid,)))
                keep.update(x[0] for x in con.execute(
                    'SELECT src FROM abc_edges WHERE dst=? ORDER BY weight DESC LIMIT 45',(uid,)))
        self._focus_result_ids=origins
        self._local_focus_ids=keep
        self.reload_network()
        self.focus_ids=keep&set(self.plot_data)
        selected=next((x for x in origins if x in self.plot_data),None)
        if selected:self.select(selected,repaint=False)
        self.search_hint.set(f'FLIN Memory Unit match  {len(origins)}  records ; local Display  {len(self.focus_ids)}  items .')
        self.draw()

    def associate(self):
        if not self.chosen:return
        with database() as con:
            row=con.execute("SELECT label FROM abc_units WHERE id=? AND status='active'",
                            (self.chosen,)).fetchone()
        if not row:
            messagebox.showinfo('Cannot Trigger Memory','The selected memory unit is not stored or lacks qualified effective-input evidence.');return
        self.abc_input.set(row[0]);self.abc_start_simulation()

    def awaken_selected(self):
        if self.chosen and self.chosen in self.plot_data:
            self.test_var.set(self.plot_data[self.chosen]['label'])
            self.test_text()

    def test_text(self, auto_generate=False):
        # Previous question-generation entry is intentionally removed.
        self.flin_start_bridge_explorer()

    def show_quality_report(self):
        self.open_math_coverage()

    def open_math_coverage(self):
        with database() as con:
            st=abc_status(con)
            topics=con.execute('SELECT name,state,processed FROM abc_topics '
                               'ORDER BY updated DESC LIMIT 25').fetchall()
            top=con.execute("SELECT label,evidence_count FROM abc_units WHERE status='active' "
                            'ORDER BY evidence_count DESC LIMIT 20').fetchall()
        messagebox.showinfo('FLIN  direct learning Report ',
           f" Mathematics Topic :{st['topics']:,}\n Source :{st['learned_sources']:,}\n"
           f" can trigger Memory Unit:{st['active']:,}\n old Candidate pending verification for :{st['candidates']:,}\n"
           f" single to edge :{st['edges']:,}\n valid Input cluster :{st['input_clusters']:,}\n\n"
           +' high Evidence count Memory Unit:\n'+ '\n'.join(f'{n}:{v}' for n,v in top)
           +'\n\n recent Topic :\n'+'\n'.join(f'{n} | {state} | {count}'
                                             for n,state,count in topics),parent=self.root)

    def delete_network(self):
        if (self.collector and self.collector.is_alive()) or self.abc_worker_active:
            messagebox.showwarning('Background Task in Progress','Stop Collection First/FLIN  simulation .');return
        if self.generating_sets or self.iteration_jobs:
            messagebox.showwarning('Question Workflow in Progress','Stop question generation and review before continuing.');return
        with database() as con:st=abc_status(con)
        if not st['active'] and not st['candidates']:
            messagebox.showinfo('Empty Network','There are no FLIN memory units in the active network.');return
        if not messagebox.askyesno('Clear Only the Current FLIN Network?',
            f" permanently clear  {st['active']+st['candidates']:,}  items  FLIN Memory Unit and  "
            f"{st['edges']:,}  edges association Link , with and  FLIN  Source and Pulse history .\n"
            ' Will not clear its they Saved Network or legacy Literature graph .',icon='warning',default='no'):
            return
        with database() as con:
            with con:
                for tab in ('abc_feedback','abc_pulse_events','abc_runs','abc_cluster_links',
                            'abc_cluster_features','abc_replay_queue','abc_input_clusters',
                            'abc_learning_events','abc_evidence','abc_ssrs','abc_edges',
                            'abc_positions','abc_units','abc_source_topics','abc_sources',
                            'flin_patterns','flin_pattern_evidence',
                            'flin_shortcut_members','flin_cost_decisions',
                            'abc_topics'):
                    con.execute('DELETE FROM '+tab)
                for (aid,) in con.execute("SELECT id FROM association_runs WHEREModelIN ('ABC pulse','FLIN pulse')"):
                    # Question histories for other legacy association runs are preserved.
                    for (sid,) in con.execute('SELECT id FROM question_sets WHERE run_id=?',(aid,)):
                        con.execute('DELETE FROM question_feedback WHERE candidate_id IN '
                                    '(SELECT id FROM question_candidates WHERE set_id=?)',(sid,))
                        con.execute('DELETE FROM question_candidates WHERE set_id=?',(sid,))
                        con.execute('DELETE FROM question_sets WHERE id=?',(sid,))
                    con.execute('DELETE FROM association_context WHERE run_id=?',(aid,))
                    con.execute('DELETE FROM association_runs WHERE id=?',(aid,))
        self.coords={};self.chosen=None;self.path=[]
        self._local_focus_ids=None;self._focus_result_ids=[];self.focus_ids=set()
        self.has_started=False
        self.abc_refresh_status();self.reload_network()


def audit_existing_math_units(batch_size=2000, max_rows=0, progress=None):
    """Non-destructive and restartable quality labeling of old memory units.

    Does not delete/mutate the original 1.5M nodes or 7M edges. Querying can
    avoid weak legacy terms immediately, without waiting for this audit.
    """
    scanned=0; accepted=0; rejected=0
    with database() as con:
        cursor=con.execute("SELECT value FROM network_meta WHERE key='math_audit_cursor'").fetchone()
        after=cursor[0] if cursor else ''
        while True:
            rows=con.execute('''SELECT id,label,kind FROM units WHERE id>?
                ORDER BY id LIMIT ?''' ,(after,batch_size)).fetchall()
            if not rows:
                with con:
                    con.execute("INSERT INTO network_meta(key,value) VALUES('math_audit_completed','1') "
                                "ON CONFLICT(key) DO UPDATE SET value=excluded.value")
                break
            with con:
                for uid,label,kind in rows:
                    if kind=='concept':okay,reason=math_concept_quality(label)
                    elif kind=='paper':
                        okay=quick_math_node_ok(label,'paper')
                        reason='paper_title_math' if okay else 'ambiguous_paper_title'
                    elif kind=='theory':
                        okay=math_topic_quality(label)[0]
                        reason='research_topic' if okay else 'ambiguous_topic_title'
                    elif kind=='relation':
                        parts=re.split(r'\s*[—→]\s*',label or '')
                        okay=(len(parts)>=3 and math_concept_quality(parts[0])[0]
                              and math_concept_quality(parts[-1])[0]
                              and not any(p in label.lower() for p in
                                          (' — used for ',' — relates to ')))
                        reason='math_relation' if okay else 'unverified_relation'
                    else:okay=True;reason='metadata_source'
                    con.execute('''INSERT INTO unit_quality_audit(unit_id,state,reason)
                        VALUES(?,?,?) ON CONFLICT(unit_id) DO UPDATE SET
                        state=excluded.state,reason=excluded.reason,
                        updated=CURRENT_TIMESTAMP''',(uid,'accepted' if okay else 'quarantined',reason))
                    scanned+=1
                    accepted+=bool(okay);rejected+=not okay
                after=rows[-1][0]
                con.execute("INSERT INTO network_meta(key,value) VALUES('math_audit_cursor',?) "
                            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",(after,))
            if progress: progress(scanned,accepted,rejected)
            if max_rows and scanned>=max_rows:break
    return scanned,accepted,rejected


def export_curated_math_network(parent_dir, progress=None):
    """Create an independent portable HIGH PRECISION graph, never mutate DB.

    Requires completion of the restartable quality audit; otherwise failing
    closed is safer than silently exporting a partly unchecked million nodes.
    Drops legacy lexical co-mentions (`concept-concept`) regardless of support.
    """
    staging,final=_safe_export_destination(parent_dir,prefix='math_curated_network')
    staging.mkdir(mode=0o700)
    try:
        with contextlib.closing(_read_only_database()) as con:
            finished=con.execute("SELECT value FROM network_meta "
                                 "WHERE key='math_audit_completed'").fetchone()
            if not finished or finished[0]!='1':
                raise RuntimeError(' legacy network Not yet Completed Quality audit points ; first run  python questioning.py --audit-math-quality')
            con.execute('BEGIN')
            query_units='''SELECT u.* FROM units u INNER JOIN unit_quality_audit q
                            ON q.unit_id=u.id WHERE q.state='accepted' '''
            query_edges='''SELECT e.* FROM edges e
                INNER JOIN unit_quality_audit a ON a.unit_id=e.src AND a.state='accepted'
                INNER JOIN unit_quality_audit b ON b.unit_id=e.dst AND b.state='accepted'
                WHERE e.kind!='concept-concept' '''
            query_ev='''SELECT v.* FROM relation_evidence v
                INNER JOIN unit_quality_audit q ON q.unit_id=v.relation_id AND q.state='accepted' '''
            meta={'schema_version':1,'format':'brain-project-curated-math',
                  'filter':'quality_audit_accepted_and_no_lexical_cooccurrence',
                  'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'notes':'Heuristic subject relevance; NOT independently verified.',
                  'tables':{}}
            for tab,sql in (('units',query_units),('edges',query_edges),('relation_evidence',query_ev)):
                cur=con.execute(sql)
                columns=[x[0] for x in cur.description];n=0
                with gzip.open(staging/(tab+'.jsonl.gz'),'wt',encoding='utf-8',compresslevel=4) as out:
                    while True:
                        rows=cur.fetchmany(1500)
                        if not rows:break
                        out.write(''.join(json.dumps(dict(zip(columns,row)),ensure_ascii=False,
                              separators=(',',':'),default=str)+'\n' for row in rows))
                        n+=len(rows)
                        if progress and n%30000<1500: progress(tab,n)
                meta['tables'][tab]={'file':tab+'.jsonl.gz','rows':n}
            con.rollback()
        (staging/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        (staging/'README.txt').write_text('Brain_Project  high Purity Candidate research Network ; The original network is not modified .\n'
            ' contains only non-destructive Quality audit accepted Node , both endpoints passed Directed Link , with and research relationship Evidence .\n'
            ' NOT include lexical Co-occurrence  concept-concept  edge . Classification is still heuristic , NOT equal to research Validate .\n',encoding='utf-8')
        staging.rename(final)
        return final
    except Exception:
        shutil.rmtree(staging,ignore_errors=True)
        raise


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description='FLIN — mathematical literature, associative memory, and research tools')
    parser.add_argument('--abc-info','--flin-info',action='store_true',help='Show FLIN associative-memory statistics for the current network')
    parser.add_argument('--abc-reconcile','--flin-reconcile',action='store_true',help='Reconcile previously pending input clusters after memory activation')
    parser.add_argument('--abc-clusters','--flin-clusters',nargs='?',const=20,type=int,metavar='N',
                        help='Show the N latest source-grounded input clusters (default: 20)')
    parser.add_argument('--abc-create-network','--flin-create-network',metavar='NAME',help='Create and select a separate mathematics memory network')
    parser.add_argument('--abc-enable','--flin-enable',action='store_true',help='Enable FLIN learning in the active network without changing legacy edges')
    parser.add_argument('--abc-learn-existing','--flin-learn-existing',action='store_true',help='Replay already collected papers as effective inputs in batches')
    parser.add_argument('--abc-batch','--flin-batch',type=int,default=150,help='Papers to replay per batch (default: 150)')
    parser.add_argument('--abc-simulate','--flin-simulate',metavar='QUERY',help='Run weighted single-path FLIN pulse simulation for a query')
    parser.add_argument('--abc-pulse-rate','--flin-pulse-rate',type=float,default=18.,help='Input pulse supply rate, in Hz (default: 18)')
    parser.add_argument('--abc-duration','--flin-duration',type=float,default=2.,help='Pulse-input duration, in seconds (default: 2)')
    parser.add_argument('--abc-threshold','--flin-threshold',type=float,default=2.,help='Display threshold for response frequency, in Hz (default: 2)')
    parser.add_argument('--abc-window','--flin-window',type=float,default=.25,help='Response-frequency observation window, in seconds (default: 0.25)')
    parser.add_argument('--abc-revisits','--flin-revisits',type=int,default=2,help='Maximum revisits per memory unit for a single pulse (default: 2)')
    parser.add_argument('--import-openalex',metavar='WORKS.jsonl[.gz]',
                        help='Import OpenAlex public works JSONL/GZ into the local FTS5 literature catalog')
    parser.add_argument('--import-limit',type=int,default=0,help='Maximum imported records; 0 means unlimited')
    parser.add_argument('--flin-discovery-info',action='store_true',help='Show persistent discovery frontier and progress in SQLite')
    parser.add_argument('--flin-source-report',action='store_true',help='Show source coverage, content depth, and the last stop reason')
    parser.add_argument('--flin-efficiency-report',action='store_true',help='Show association cost decisions and formed shortcut memories')
    parser.add_argument('--flin-related','--flin-bridges',dest='flin_bridges',metavar='CONCEPTS',
        help='Read-only related concepts reached from comma-separated memory inputs')
    parser.add_argument('--bridge-pulses',type=int,default=360,
        help='Observed single-path walks per input (20–4000; default 360)')
    parser.add_argument('--bridge-steps',type=int,default=14,
        help='Maximum hops in a bridge observation (2–64; default 14)')
    parser.add_argument('--bridge-limit',type=int,default=60,
        help='Maximum meeting nodes/frontier links returned (5–300; default 60)')
    parser.add_argument('--bridge-seed',type=int,default=42,
        help='Reproducible random sampling seed (default 42)')
    parser.add_argument('--bridge-json',metavar='FILE',
        help='Optionally save a full read-only knowledge bridge report as JSON')
    parser.add_argument('--flin-association-audit',action='store_true',help='Read-only diagnostic of triggerable memories, learned links and singleton input clusters')
    parser.add_argument('--flin-repair-associations',nargs='?',const=200,type=int,metavar='N',help='Idempotently rescan N cached sources with improved ordered-input extraction (default 200)')
    parser.add_argument('--flin-retrofit',action='store_true',help='Evaluate existing SSRS input clusters for reusable shortcut memories')
    parser.add_argument('--flin-retrofit-limit',type=int,default=1000,help='Maximum existing clusters per retrofit run (default: 1000)')
    parser.add_argument('--diagnose',action='store_true',help='Run offline database and Ollama diagnostics without revealing API keys')
    parser.add_argument('--display-check',action='store_true',help='Read-only check of graph totals and sampled missing nodes, edges, and positions')
    parser.add_argument('--catalog-info',action='store_true',help='Show local literature catalog counts, sources, query cache, and size')
    parser.add_argument('--catalog-search',metavar='QUERY',help='Search only the local literature index; no provider API requests')
    parser.add_argument('--catalog-import-network',nargs='?',const='__ACTIVE__',metavar='SQLITE',
                        help='Import bibliographic metadata from a network into the shared catalog (active network by default)')
    parser.add_argument('--catalog-backfill-keys',action='store_true',
                        help='Build DOI/title deduplication keys for older OpenAlex data without deleting papers')
    parser.add_argument('--catalog-limit',type=int,default=0,
                        help='Maximum records for catalog import or key backfill (0 means unlimited)')
    parser.add_argument('--source-info',action='store_true',help='Show configured literature providers and rate limits without network calls')
    parser.add_argument('--cpu-info',action='store_true',help='Show processor availability and recommended collector concurrency')
    parser.add_argument('--export-curated-network',metavar='OUTPUT_DIR',
                        help='Export a separately curated research subnetwork as compressed JSONL without altering the original')
    parser.add_argument('--audit-domain-quality','--audit-math-quality',dest='audit_math_quality',action='store_true',
                        help='Resume non-destructive quality auditing of legacy memories')
    parser.add_argument('--audit-limit',type=int,default=0,help='Maximum records for this audit run (0 means unlimited)')
    parser.add_argument('--list-networks',action='store_true',help='List all saved independent memory networks')
    parser.add_argument('--math-coverage',action='store_true',help='Report literature coverage by mathematical branch and application area')
    parser.add_argument('--purity-report',action='store_true',help='Show memory-unit lexical quality scores and rejection statistics')
    parser.add_argument('--purity-clean',action='store_true',help='Remove narrowly defined legacy lexical noise in batches; back up first')
    parser.add_argument('--purity-limit',type=int,default=10000,help='Maximum memories scanned in one purity-clean run (default: 10000)')
    parser.add_argument('--domain',choices=('mathematics',),default=None,
                        help='Legacy compatibility option; mathematics is the only supported research domain')
    parser.add_argument('--domain-seeds',default='',help='Legacy-only option; general-domain seeds are no longer supported')
    parser.add_argument('--domain-categories',default='',help='Legacy-only option; general-domain categories are no longer supported')
    parser.add_argument('--domain-keywords',default='',help='Legacy-only option; general-domain keyword lists are no longer supported')
    parser.add_argument('--new-network',metavar='NAME',help='Create and select an independent empty FLIN network')
    parser.add_argument('--switch-network',metavar='ID',help='Select a saved network (see --list-networks for IDs)')
    parser.add_argument('--import-network',metavar='PATH',help='Import and select a complete SQLite or JSONL.gz network')
    parser.add_argument('--network-name',metavar='NAME',help='Set the display name for a command-line network import')
    parser.add_argument('--verify-export',metavar='EXPORTED_SQLITE_OR_DIR',
                        help='Verify exported FLIN abc_units/abc_edges or analysis graph counts and SQLite integrity')
    parser.add_argument('--export-network',metavar='OUTPUT_DIR',help='Export the complete directed network to a destination directory')
    parser.add_argument('--export-format',choices=('portable','sqlite'),default='sqlite',
                        help='portable: compressed JSONL and manifest; sqlite: full database snapshot')
    parser.add_argument('--no-export-sources',action='store_true',
                        help='For portable exports, omit literature provenance and include only graph data and metadata')
    parser.add_argument('--build-fast-index',action='store_true',
                        help='Build reverse-edge and ordered outgoing-weight indexes; may require significant disk space')
    args=parser.parse_args()
    custom_opts=None
    if args.domain_seeds or args.domain_categories or args.domain_keywords:
        parser.error(' Custom research-domain seeds are not supported in the mathematics-only version ; please by directly from main interface Start all Mathematics automatic building .')
    if args.flin_bridges:
        try:
            with contextlib.closing(_read_only_database()) as con:
                con.execute('BEGIN')
                outcome=flin_bridge_explore(con,args.flin_bridges,
                    pulses_per_gate=args.bridge_pulses,max_steps=args.bridge_steps,
                    random_seed=args.bridge_seed,result_limit=args.bridge_limit)
                con.rollback()
            # Console returns a compact result; complete paths and sources stay
            # in the optional JSON file rather than flooding a terminal.
            summary={'inputs':outcome['inputs'],'statistics':outcome['statistics'],
                     'related_concepts':outcome['concept_landscapes']}
            print(json.dumps(summary,ensure_ascii=False,indent=2))
            if args.bridge_json:
                dst=Path(args.bridge_json).expanduser()
                dst.parent.mkdir(parents=True,exist_ok=True)
                dst.write_text(json.dumps(outcome,ensure_ascii=False,indent=2),encoding='utf-8')
                print('Detailed observed routes and source evidence:',dst)
        except Exception as exc:
            print('FLIN related-concepts search failed:',type(exc).__name__,str(exc),file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    if args.flin_association_audit:
        with database() as con:
            print(json.dumps(flin_association_health(con),ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.flin_repair_associations is not None:
        with database() as con:
            before=flin_association_health(con)
            restored=flin_backfill_cached_abstracts(con,limit=max(1,args.flin_repair_associations))
            after=flin_association_health(con)
            print(json.dumps({'recovery':restored,'before':before,'after':after},
                             ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.flin_source_report:
        with database() as con:
            depth=dict(con.execute('SELECT read_level,COUNT(*) FROM flin_source_depth GROUP BY read_level'))
            providers=dict(con.execute('SELECT provider,COUNT(*) FROM flin_source_depth GROUP BY provider'))
            latest=[{'topic':n,'state':st,'message':msg,'updated':t} for n,st,msg,t in
                con.execute('''SELECT name,state,message,updated FROM abc_topics
                    ORDER BY updated DESC LIMIT 15''')]
            data={'active_database':str(DB_PATH), 'source_depth':depth,
                  'providers':providers,'frontier':flin_discovery_counts(con),
                  'recent_topics':latest}
            print(json.dumps(data,ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.flin_discovery_info:
        with database() as con:
            print(json.dumps(flin_discovery_counts(con),ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.abc_create_network:
        network_id=create_empty_network(args.abc_create_network,activate=True,domain='mathematics')
        with database() as con:abc_enable(con)
        print('✓  already Build  FLIN  theory version Independent Mathematics Network :',network_id,DB_PATH)
        sys.exit(0)
    if args.abc_clusters is not None:
        with database() as con:print(json.dumps(abc_recent_input_clusters(con,args.abc_clusters),ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.abc_reconcile:
        with database() as con:print(json.dumps(abc_reconcile_pending(con,limit=max(1,args.abc_batch)),ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.abc_info:
        with database() as con:print(json.dumps(abc_status(con),ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.abc_enable:
        with database() as con:abc_enable(con)
        print('✓  current network enabled Independent  FLIN  learning learning ; original with Literature graph and Link retain .')
        sys.exit(0)
    if args.abc_learn_existing:
        with database() as con:
            if not abc_enabled(con):parser.error(' first run  --abc-enable  or from  GUI  Build Independent  FLIN  Network ')
            outcome=abc_backfill(con,max(1,args.abc_batch))
            print(json.dumps(outcome,ensure_ascii=False,indent=2))
            print(json.dumps(abc_status(con),ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.flin_efficiency_report:
        with database() as con:
            print(json.dumps(flin_efficiency_report(con),ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.flin_retrofit:
        with database() as con:
            print(json.dumps(flin_retrofit_history(con,args.flin_retrofit_limit),
                             ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.abc_simulate:
        with database() as con:
            if not abc_enabled(con):parser.error(' current network not yet not enabled  FLIN; Please first enable or Build independent network ')
            outcome=abc_simulate(con,args.abc_simulate,pulse_hz=args.abc_pulse_rate,
                input_duration=args.abc_duration,frequency_threshold=args.abc_threshold,
                frequency_window=args.abc_window,max_revisits=args.abc_revisits)
            association_id=abc_save_as_association(con,outcome)
            print(json.dumps({'run_id':outcome['run_id'],'association_id':association_id,
                'activated':outcome['activated_count'],'visible':outcome['visible_count'],
                'distribution':outcome['distribution'],'feedback_events':outcome['feedback_count']},
                ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.display_check:
        try:
            with contextlib.closing(_read_only_database()) as connection:
                print(json.dumps(inspect_display_health(connection),ensure_ascii=False,indent=2))
        except Exception as exc:
            print('✕  Display Diagnostics Failed :'+str(exc),file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    if args.catalog_info:
        print(json.dumps(catalog_statistics(),ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.catalog_search:
        stop=threading.Event()
        for rank,(score,work) in enumerate(stream_local_works(args.catalog_search,30,stop) or (),1):
            print(f'{rank:02d}  {score:.3f}  {work["display_name"][:130]}')
            print('    '+str(work.get('doi') or work.get('id')))
        sys.exit(0)
    if args.catalog_import_network is not None:
        path=None if args.catalog_import_network=='__ACTIVE__' else args.catalog_import_network
        scanned,added=catalog_import_network(path,limit=max(0,args.catalog_limit),
            progress=lambda n,m:print(f' scan  {n:,}| this run New  {m:,}',flush=True)
                if n and n%30000==0 else None)
        print(f'✓  from existing Mathematics Network Import : scan  {scanned:,}, New  {added:,}, shared Index total  {local_catalog_count():,} papers')
        sys.exit(0)
    if args.catalog_backfill_keys:
        scanned=catalog_backfill_keys(limit=max(0,args.catalog_limit),
            progress=lambda n:print(f' Build deduplication keys  {n:,}',flush=True) if n and n%30000==0 else None)
        print(f'✓  already scan  {scanned:,}  records legacy Index Data ; can multiple imes run , NOT delete Data .')
        sys.exit(0)
    if args.source_info:
        print(' Default Source order : local offline Index  → arXiv → Crossref → OpenAlex( only manual enable )')
        print('OpenAlex API:', ' enabled  BRAIN_USE_OPENALEX=1' if os.environ.get('BRAIN_USE_OPENALEX','0')=='1' else ' disable ( Default ; complete all NOT needs  API  quota )')
        print('arXiv: enabled , cross workers shared  ≥3.1  seconds please request interval ( no needs  API key)')
        print('Crossref: enabled , cross workers shared please request rate limit and concurrent Limit ;',
              'polite pool' if '@' in os.environ.get('CROSSREF_MAILTO','') else 'public pool')
        print(' local offline Index ( continue from remote automatic accumulated ):',f'{local_catalog_count():,} papers')
        print(' query fast obtain valid expiration :',os.environ.get('BRAIN_CATALOG_TTL_HOURS','72'),' Hours ;BRAIN_CATALOG_REFRESH=1  can force refresh new ')
        print(' Note : this command only Display Settings , No actual Check Network connection .')
        sys.exit(0)
    if args.purity_report:
        with database() as con:
            print(json.dumps(purity_report(con),ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.purity_clean:
        n=0;deleted=0
        with database() as con:
            while n<max(1,args.purity_limit):
                result=purge_trivial_legacy_units_batch(
                    con,limit=min(900,max(1,args.purity_limit)-n))
                n+=result['scanned'];deleted+=result['deleted']
                if result['completed'] or not result['scanned']:break
            # Flush remaining queued bad words on explicit maintenance run.
            tail=purge_trivial_legacy_units_batch(con,limit=0,flush=True)
            deleted+=tail['deleted']
            print(f' already scan  {n:,}  records ; this run already delete clear confirm no meaning concept  {deleted:,}  records .')
            print(json.dumps(purity_report(con),ensure_ascii=False,indent=2))
        sys.exit(0)
    if args.cpu_info:
        info=detect_cpu_resources()
        print(' system logical processors :', info['system_logical'])
        print(' this application can visible logical processors :', info['affinity_logical'])
        print(' can visible physical cores :', info['physical_visible'] if info['physical_visible'] else ' unknown ')
        print('cgroup CPU  quota :', info['quota_logical'] if info['quota_logical'] else ' not yet Limit / unknown ')
        rec=recommend_build_resources(info)
        print(' building  CPU  use maximum :', rec['cpu_max'])
        print(' parallel building workers maximum :', rec['worker_max'])
        print('Recommended: CPU  use count :', rec['cpu_budget'])
        print(' recommendation parallel workers count :', rec['workers'])
        if info.get('memory_available_gib') is not None:
            print(' Current available  RAM (GiB):', info['memory_available_gib'])
        print(' Current CPU load (% of permitted logical CPUs):', info.get('cpu_load_pct') if info.get('cpu_load_pct') is not None else 'unavailable')
        print(' Available RAM / total RAM (GiB):', info.get('memory_available_gib'), '/', info.get('memory_total_gib'))
        print(' Detection backend:', info.get('resource_backend'))
        print(' Note: these are live recommendations, not a performance benchmark. SQLite, remote provider limits and optional PDF parsing may reduce useful concurrency.')
        if os.name == 'nt':
            print(' Note: Windows worker count is enforced; a per-thread Linux-style CPU affinity limit is not available.')
    elif args.math_coverage:
        with database() as con:
            print(json.dumps(mathematical_coverage_report(con),ensure_ascii=False,indent=2))
    elif args.list_networks:
        current=read_network_registry()['active']
        for record,path in network_entries():
            print(('* ' if record['id']==current else '  ')+record['id']+'  '+record['name']+'  '+str(path),flush=True)
    elif args.new_network:
        network_id=create_empty_network(args.new_network,activate=True,domain='mathematics',custom_options=custom_opts)
        print('✓  already Build and switch to new network :',network_id,DB_PATH,flush=True)
    elif args.switch_network:
        record=switch_active_network(args.switch_network)
        print('✓ Switched to network: ',record['name'],DB_PATH,flush=True)
    elif args.import_network:
        name=args.network_name or (' Import :'+Path(args.import_network).stem)
        network_id=import_network(args.import_network,name,activate=True,domain='mathematics',custom_options=custom_opts,
            progress=lambda stage,n,total: print(f'{stage}: {n:,}/{total:,}',flush=True) if n and n%100000==0 else None)
        print('✓  already Import and switch Network :',network_id,DB_PATH,flush=True)
    elif args.domain:
        set_network_domain(active_network_record()['id'],'mathematics')
        print('✓  already change more current network Domain :',domain_name(),flush=True)
    elif args.export_curated_network:
        print(' Processing Export high Purity research sub Network ( NOT delete original Data )...',flush=True)
        output=export_curated_math_network(args.export_curated_network,
            progress=lambda table,n:print(f'{table} {n:,}...',flush=True))
        print(' Completed :',output,flush=True)
    elif args.verify_export:
        target=Path(args.verify_export).expanduser().resolve()
        if target.is_dir():
            target=target/'association.sqlite3'
        if not target.is_file():
            parser.error('Exported SQLite file not found: '+str(target))
        try:
            with contextlib.closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True)) as src:
                names={r[0] for r in src.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                if {'abc_units','abc_edges'}.issubset(names):
                    counts=flin_export_counts(src)
                    _verify_sqlite_graph_file(target,counts)
                elif {'units','edges','export_metadata'}.issubset(names):
                    counts=dict(src.execute('SELECT key,value FROM export_metadata'))
                    counts=json.loads(counts['counts_json'])
                    _verify_sqlite_graph_file(target,counts,mirror=True)
                else:
                    raise RuntimeError('No FLIN associative graph found in exported SQLite.')
            print(json.dumps({'file':str(target),'verified':True,'counts':counts},indent=2))
        except Exception as exc:
            print('FLIN integrity check failed:',str(exc),file=sys.stderr)
            sys.exit(1)
    elif args.export_network:
        try:
            print(' Start Export Memory unit Network ; large-scale Network needs sufficient disk space .', flush=True)
            last=[0.0]
            def status_export(stage,done,total):
                now=time.monotonic()
                if now-last[0] > 2 or stage == ' Completed ':
                    percent=f'{done/max(1,total)*100:.1f}%' if total else '—'
                    print(f'{stage}| cores Node ＋ Link  {done:,}/{total:,} {percent}', flush=True)
                    last[0]=now
            output=export_memory_network(args.export_network,mode=args.export_format,
                with_sources=not args.no_export_sources,progress=status_export)
            print('✓  complete Network already Export :',output,flush=True)
        except Exception as exc:
            print('✕ Export Failed:',type(exc).__name__,str(exc),file=sys.stderr,flush=True)
            sys.exit(1)
    elif args.audit_math_quality:
        print(' Start non-destructive legacy network Quality audit points ; NOT delete Node / Link , scan can resumable .',flush=True)
        done=0
        def quality_progress(n,a,b):
            if n%20000==0:print(f' already Check  {n:,}; can retain  {a:,}; quarantined  {b:,}',flush=True)
        counts=audit_existing_math_units(max_rows=max(0,args.audit_limit),progress=quality_progress)
        print(' this run Quality scan Completed :',counts,flush=True)
    elif args.diagnose:
        import shutil
        print('Brain_Project  local Diagnostics | Will not transmit Data or Display  API key',flush=True)
        try:
            import sqlite3 as _sq
            import shutil as _sh
            usage=_sh.disk_usage(str(DATA_DIR if DATA_DIR.exists() else Path.home()))
            print(' disk available :',round(usage.free/1024**3,2),'GiB')
            if DB_PATH.exists():
                print(' main Database :',DB_PATH,' size ',round(DB_PATH.stat().st_size/1024**3,2),'GiB')
                with database() as con:
                    print(' Topic / Paper / Node / Link :',*stats(con))
                    print(' Reverse Index :',bool(con.execute("SELECT 1 FROM sqlite_master WHERE name='idx_edges_dst'").fetchone()))
                    print(' association Strength Index :',bool(con.execute("SELECT 1 FROM sqlite_master WHERE name='idx_edges_src_weight'").fetchone()))
                    print(' term form Index ready :',con.execute("SELECT value FROM network_meta WHERE key='lexical_v5'").fetchone())
                    print(' New Literature Quality judge define :',quality_counts(con))
                    print(' old Memory unit Quality audit points :',con.execute('SELECT state,COUNT(*) FROM unit_quality_audit GROUP BY state').fetchall())
                    print(' latest search errors :',con.execute('SELECT category,status,substr(reason,1,170) FROM openalex_failures ORDER BY id DESC LIMIT 3').fetchall())
            else:print(' cannot find Saved main Database .')
        except Exception as exc:
            print(' Diagnostics abnormal :',type(exc).__name__,str(exc)[:450])
    elif args.build_fast_index:
        print(' Start Build Reverse Link Index ; Stop first  GUI  building , and confirm disk space sufficient .',flush=True)
        with database() as con:
            con.execute('PRAGMA busy_timeout=60000')
            con.execute('CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst)')
            print(' Processing Build according to Link Strength ordering outgoing edges Index ...',flush=True)
            con.execute('CREATE INDEX IF NOT EXISTS idx_edges_src_weight ON edges(src,weight DESC)')
            con.execute('PRAGMA optimize')
            con.commit()
        print('✓ idx_edges_dst  and  idx_edges_src_weight  already Build ; Reverse and high Weight association can use Index .',flush=True)
    elif args.import_openalex:
        print(' Processing Build offline  OpenAlex  other than full text Literature in continue Data Index ; Confirm disk space sufficient ...',flush=True)
        scanned,added=import_openalex_snapshot(args.import_openalex,
            limit=max(0,args.import_limit),
            progress=lambda n,m:print(f' scan  {n:,}| new Literature  {m:,}',flush=True) if n%30000==0 else None)
        print(f' Completed : scan  {scanned:,}  records ; New  {added:,}  papers | cumulative Index  {local_catalog_count():,} papers')
    else:
        ABCNetworkWindow().run()
