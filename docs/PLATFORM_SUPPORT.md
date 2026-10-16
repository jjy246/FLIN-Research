# Supported platform matrix and verification status

This repository contains **one cross-platform Python program**, three source launchers and GitHub Actions workflows to build native distribution packages on four host targets. **Build scripts are not the same as already-tested production binaries.**

| Platform | Run from source | Launch script | GitHub Actions native target | Native output | Local GUI testing status |
| --- | --- | --- | --- | --- | --- |
| Windows x64 | Python 3.12 | `start_windows.bat` | `windows-2022` | `dist/FLIN/FLIN.exe` inside a ZIP | Not exercised in this Linux workspace; CI configured |
| macOS Intel | Python 3.12 | `start_macos.command` | `macos-15-intel` | `FLIN.app` ZIP | Not exercised here; CI configured |
| macOS Apple Silicon | Python 3.12 arm64 | `start_macos.command` | `macos-15` | `FLIN.app` ZIP | Not exercised here; CI configured |
| Ubuntu/Linux x64 | Python 3.12 | `start_linux.sh` | `ubuntu-24.04` | `FLIN/` TAR.GZ | Headless tests possible here; GUI still needs a display |

## Native-package lifecycle

1. Push the repository to GitHub.
2. Open **Actions → FLIN source checks** to see syntax/import/SQLite/pulse tests for Windows, Intel macOS, Apple Silicon macOS and Linux.
3. Trigger **Build unsigned native desktop packages** with `workflow_dispatch`, or push a version tag beginning with `v`.
4. Download the four named artifacts. They are **zip/tar archives**, not `.msi`, `.dmg`, or signed installers.
5. Run on actual Windows/macOS/Linux systems, manually verify the GUI and Ollama connectivity; only then publish a formal release.
6. To distribute to general macOS users, sign and notarize through Apple. To build a trusted Windows installer, optionally add signed MSI/MSIX via a controlled release process.

## Why CI needs native runners

[PyInstaller](https://pyinstaller.org/en/stable/) bundles for the **host operating system** and does not cross-compile Windows `.exe` or macOS `.app` from Linux. GitHub's [hosted runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) lists `macos-15-intel` and arm64 `macos-15` images.

## What remains unverified

The tests **do not** automatically operate the Tk GUI, validate native trackpad/window rendering, contact all literature providers, confirm all bundled Tcl/Tk runtime variants, or prove numerical/scientific validity. Record results in `docs/ROADMAP.md` when those checks are complete.
