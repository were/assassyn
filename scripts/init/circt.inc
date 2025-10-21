# CIRCT installation targets
# Simplified logic: skip if installed, always build from source, install from wheel if available

.PHONY: install-circt clean-circt patch-circt build-pycde-source verify-pycde-installation

# Patch target for circt
patch-circt: 3rd-party/circt/.patch-applied

# Marker file to track patch application
3rd-party/circt/.patch-applied:
	@echo "Checking circt patch status..."
	@cd 3rd-party/circt && \
		if bash ../../scripts/patch-apply.sh check ../../scripts/init/patches/circt.patch 2>/dev/null; then \
			echo "CIRCT patch already applied — skipping patch step."; \
		else \
			echo "Applying CIRCT patch..."; \
			bash ../../scripts/patch-apply.sh apply ../../scripts/init/patches/circt.patch; \
		fi && \
		touch $(CURDIR)/3rd-party/circt/.patch-applied

install-circt: 3rd-party/circt/.circt-built

# Build PyCDE from source
build-pycde-source:
	@echo "Building PyCDE from source..."
	@CIRCT_DIRECTORY="$(CURDIR)/3rd-party/circt" \
		CIRCT_EXTRA_CMAKE_ARGS="-DESI_RUNTIME=OFF -DZ3_DISABLE=ON -DOR_TOOLS_DISABLE=ON" \
		$(VENV_DIR)/bin/python -m build -C 3rd-party/circt/frontends/PyCDE
	@echo "PyCDE built successfully from source."

# Verify PyCDE installation
verify-pycde-installation:
	@echo "Verifying PyCDE installation..."
	@$(VENV_DIR)/bin/python -c "import pycde; print('PyCDE version:', getattr(pycde, '__version__', 'unknown'))"
	@echo "CIRCT installation completed successfully."

# Marker file to track build completion
3rd-party/circt/.circt-built: patch-circt
	@echo "Installing PyCDE..."
	@# Skip if already installed
	@if $(VENV_DIR)/bin/python -c "import pycde" 2>/dev/null; then \
		echo "PyCDE is already installed — skipping installation."; \
		touch $(CURDIR)/3rd-party/circt/.circt-built; \
	else \
		# Build from source if no wheel exists
		if [ ! -f "3rd-party/circt/frontends/PyCDE/dist/"*.whl ]; then \
			echo "No wheel found, building PyCDE from source..."; \
			$(MAKE) build-pycde-source; \
		fi && \
		# Install from wheel
		echo "Installing PyCDE from wheel..."; \
		$(VENV_DIR)/bin/pip install 3rd-party/circt/frontends/PyCDE/dist/*.whl && \
		$(MAKE) verify-pycde-installation && \
		touch $(CURDIR)/3rd-party/circt/.circt-built; \
	fi

clean-circt:
	@echo "Cleaning CIRCT build artifacts and uninstalling PyCDE..."
	@if [ -d "$(VENV_DIR)" ]; then \
		$(VENV_DIR)/bin/pip uninstall -y pycde 2>/dev/null || true; \
	fi
	@rm -rf 3rd-party/circt/dist 3rd-party/circt/build 3rd-party/circt/*.egg-info 2>/dev/null || true
	@bash scripts/patch-apply.sh reverse scripts/init/patches/circt.patch 2>/dev/null || true
	@rm -f 3rd-party/circt/.patch-applied 3rd-party/circt/.circt-built
	@echo "CIRCT clean completed."
