APP_NAME := artincam-editor
ENTRYPOINT := src/main.py

PYTHON := uv run python
RUFF := uv run ruff
PYINSTALLER := uv run pyinstaller

BUILD_DIR := build
DIST_DIR := dist
SPEC_DIR := $(BUILD_DIR)/spec
PACKAGE_DIR := packages

.PHONY: help install sync run lint format check clean clean-build clean-dist clean-cache \
	build-linux build-linux-dir build-windows build-windows-dir \
	package-linux package-linux-dir package-windows package-windows-dir \
	rebuild-linux rebuild-linux-dir rebuild-windows rebuild-windows-dir

help:
	@echo "Available targets:"
	@echo "  install             Sync project dependencies with uv"
	@echo "  sync                Same as install"
	@echo "  run                 Run the app"
	@echo "  lint                Run Ruff lint"
	@echo "  format              Auto-fix lint and format code"
	@echo "  check               Run lint + formatting checks without modifying files"
	@echo "  clean               Remove build, dist, package, spec, and Python cache artifacts"
	@echo "  clean-build         Remove build artifacts"
	@echo "  clean-dist          Remove dist and packaged artifacts"
	@echo "  clean-cache         Remove Python cache artifacts"
	@echo "  build-linux         Build one-file Linux executable"
	@echo "  build-linux-dir     Build one-dir Linux bundle"
	@echo "  build-windows       Build one-file Windows executable"
	@echo "  build-windows-dir   Build one-dir Windows bundle"
	@echo "  package-linux       Build and archive one-file Linux output as .tar.gz"
	@echo "  package-linux-dir   Build and archive one-dir Linux output as .tar.gz"
	@echo "  package-windows     Build and archive one-file Windows output as .zip"
	@echo "  package-windows-dir Build and archive one-dir Windows output as .zip"
	@echo "  rebuild-linux       Clean and rebuild one-file Linux executable"
	@echo "  rebuild-linux-dir   Clean and rebuild one-dir Linux bundle"
	@echo "  rebuild-windows     Clean and rebuild one-file Windows executable"
	@echo "  rebuild-windows-dir Clean and rebuild one-dir Windows bundle"
	@echo ""
	@echo "Notes:"
	@echo "  - Build Linux targets on Linux."
	@echo "  - Build Windows targets on Windows."
	@echo "  - Windows 11 and Windows 12 use the same Windows build target."

install sync:
	uv sync --dev

run:
	$(PYTHON) $(ENTRYPOINT)

lint:
	$(RUFF) check .

format:
	$(RUFF) check . --fix
	$(RUFF) format .

check:
	$(RUFF) check .
	$(RUFF) format . --check

clean: clean-build clean-dist clean-cache
	rm -f *.spec

clean-build:
	rm -rf $(BUILD_DIR)

clean-dist:
	rm -rf $(DIST_DIR)
	rm -rf $(PACKAGE_DIR)

clean-cache:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

build-linux:
	$(PYINSTALLER) \
		--noconfirm \
		--clean \
		--onefile \
		--windowed \
		--name $(APP_NAME)-linux \
		--distpath $(DIST_DIR) \
		--workpath $(BUILD_DIR)/pyinstaller \
		--specpath $(SPEC_DIR) \
		$(ENTRYPOINT)

build-linux-dir:
	$(PYINSTALLER) \
		--noconfirm \
		--clean \
		--onedir \
		--windowed \
		--name $(APP_NAME)-linux \
		--distpath $(DIST_DIR) \
		--workpath $(BUILD_DIR)/pyinstaller \
		--specpath $(SPEC_DIR) \
		$(ENTRYPOINT)

build-windows:
	$(PYINSTALLER) \
		--noconfirm \
		--clean \
		--onefile \
		--windowed \
		--name $(APP_NAME)-windows \
		--distpath $(DIST_DIR) \
		--workpath $(BUILD_DIR)/pyinstaller \
		--specpath $(SPEC_DIR) \
		$(ENTRYPOINT)

build-windows-dir:
	$(PYINSTALLER) \
		--noconfirm \
		--clean \
		--onedir \
		--windowed \
		--name $(APP_NAME)-windows \
		--distpath $(DIST_DIR) \
		--workpath $(BUILD_DIR)/pyinstaller \
		--specpath $(SPEC_DIR) \
		$(ENTRYPOINT)

package-linux: build-linux
	mkdir -p $(PACKAGE_DIR)
	tar -czf $(PACKAGE_DIR)/$(APP_NAME)-linux-x64.tar.gz -C $(DIST_DIR) $(APP_NAME)-linux

package-linux-dir: build-linux-dir
	mkdir -p $(PACKAGE_DIR)
	tar -czf $(PACKAGE_DIR)/$(APP_NAME)-linux-x64-onedir.tar.gz -C $(DIST_DIR) $(APP_NAME)-linux

package-windows-ps: build-windows
	powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path '$(PACKAGE_DIR)' | Out-Null; Compress-Archive -Path '$(DIST_DIR)/$(APP_NAME)-windows.exe' -DestinationPath '$(PACKAGE_DIR)/$(APP_NAME)-windows-x64.zip' -Force"

package-windows-dir-ps: build-windows-dir
	powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path '$(PACKAGE_DIR)' | Out-Null; Compress-Archive -Path '$(DIST_DIR)/$(APP_NAME)-windows/*' -DestinationPath '$(PACKAGE_DIR)/$(APP_NAME)-windows-x64-onedir.zip' -Force"

rebuild-linux: clean build-linux
rebuild-linux-dir: clean build-linux-dir
rebuild-windows: clean build-windows
rebuild-windows-dir: clean build-windows-dir
