# Artincam Editor

A lightweight desktop image editor built with **Python**, **PySide6**, and **Pillow**. The app allows you to prototype color channel filters and then apply those filters to large batches of images.

The project is designed to run on:

* **Ubuntu 22.04 (Linux)**
* **Windows 11 / Windows 12**

It can be packaged as a standalone executable using **PyInstaller**.

---

# Features

## Prototype Image Filters

The **Prototype** tab allows you to experiment with color operations in real time and chain them into reusable pipelines.

Features include:

* Load an image from a directory

* View **original image** and **processed preview** side-by-side

* Apply operation modes:

  * Grayscale
  * Custom RGB expression

* Build a multi-step pipeline by stacking operations
* Reorder, remove, and edit pipeline steps
* See cumulative stage previews for each pipeline step
* Inspect the expected RGB output formula for the active operation

* See live preview updates instantly

Grayscale uses fixed weights:

```
Red   = 30
Green = 59
Blue  = 11
```

---

## Batch Processing

The **Batch Processing** tab allows you to apply your chosen operation or committed pipeline to many images.

Capabilities:

* Select an input folder
* Select an output folder
* Apply the current operation or committed pipeline configuration
* Process all images in the directory
* Save processed results automatically

Supported image formats include:

* PNG
* JPG
* JPEG

---

# Technology Stack

| Component   | Purpose                                    |
| ----------- | ------------------------------------------ |
| Python      | Core application                           |
| PySide6     | GUI framework (Qt)                         |
| Pillow      | Image processing                           |
| uv          | Python environment + dependency management |
| Ruff        | Linting and formatting                     |
| PyInstaller | Building executables                       |

---

# Project Structure

```
.
├── main.py
├── Makefile
├── pyproject.toml
├── README.md
├── build/
├── dist/
└── packages/
```

* **main.py** → application source
* **Makefile** → build, lint, run, and package commands
* **dist/** → raw PyInstaller output
* **packages/** → compressed release artifacts

---

# Development Setup

Install dependencies using **uv**:

```bash
uv sync --dev
```

Run the application:

```bash
make run
```

---

# Linting and Formatting

This project uses **Ruff**.

Check code:

```bash
make lint
```

Auto-format code:

```bash
make format
```

Verify formatting without changes:

```bash
make check
```

---

# Building Executables

Executables are built using **PyInstaller**.

## Linux Build

Run on Ubuntu:

```bash
make build-linux
```

or

```bash
make build-linux-dir
```

## Windows Build

Run on Windows:

```bash
make build-windows
```

or

```bash
make build-windows-dir
```

Note: PyInstaller does **not reliably cross-compile**, so build each OS on its own platform.

---

# Packaging Distributables

The Makefile can also package builds for distribution.

### Linux

```bash
make package-linux
```

or

```bash
make package-linux-dir
```

Creates:

```
packages/artincam-editor-linux-x64.tar.gz
```

### Windows

```bash
make package-windows
```

or

```bash
make package-windows-dir
```

Creates:

```
packages/artincam-editor-windows-x64.zip
```

These packaged files are suitable for **GitHub Releases**.

---

# Cleaning Build Artifacts

Remove build artifacts:

```bash
make clean
```

---

# Roadmap Ideas

Possible future improvements:

* Brightness / contrast controls
* Image histogram visualization
* Edge detection filters
* Color channel curves
* GPU acceleration
* Drag-and-drop image loading
* Preset filter saving

---

# License

This project is open-source and intended for experimentation and learning.

You may adapt and extend it as needed.
