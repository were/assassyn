# CIRCT installation targets
# Converted from scripts/init/circt.sh

.PHONY: install-circt clean-circt patch-circt check-pycde-installed install-pycde-wheel install-pycde-pip build-pycde-source verify-pycde-installation

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

# Check if PyCDE is already installed
check-pycde-installed:
	@echo "Step 1: Checking if PyCDE is already installed..."
	@if $(VENV_DIR)/bin/python -c "import pycde" 2>/dev/null; then \
		echo "PyCDE is already installed — skipping installation."; \
		touch $(CURDIR)/3rd-party/circt/.circt-built; \
		exit 0; \
	fi

# Install PyCDE from existing wheel
install-pycde-wheel:
	@echo "Step 2: PyCDE wheel found, installing..."
	@$(VENV_DIR)/bin/pip install 3rd-party/circt/frontends/PyCDE/dist/*.whl
	@echo "PyCDE installed successfully from existing wheel."

# Try to install PyCDE via pip
install-pycde-pip:
	@echo "Step 2: No existing wheel found. Attempting to install PyCDE via pip..."
	@if $(VENV_DIR)/bin/pip install pycde 2>/dev/null; then \
		echo "PyCDE installed successfully via pip."; \
	else \
		echo "Failed to install PyCDE via pip. Proceeding to build from source..."; \
		exit 1; \
	fi

# Build PyCDE from source
build-pycde-source:
	@echo "Step 3: Building PyCDE from source..."
	@CIRCT_DIRECTORY="$(CURDIR)/3rd-party/circt" \
		CIRCT_EXTRA_CMAKE_ARGS="-DESI_RUNTIME=OFF -DZ3_DISABLE=ON -DOR_TOOLS_DISABLE=ON" \
		$(VENV_DIR)/bin/python -m build -C 3rd-party/circt/frontends/PyCDE
	@echo "Step 4: Installing PyCDE wheel..."
	@$(VENV_DIR)/bin/pip install 3rd-party/circt/frontends/PyCDE/dist/*.whl
	@echo "PyCDE built and installed successfully from source."

# Verify PyCDE installation
verify-pycde-installation:
	@echo "Step 5: Verifying PyCDE installation..."
	@$(VENV_DIR)/bin/python -c "import pycde; print('PyCDE version:', getattr(pycde, '__version__', 'unknown'))"
	@echo "CIRCT installation completed successfully."

# Marker file to track build completion
3rd-party/circt/.circt-built: patch-circt
	@echo "Installing PyCDE..."
	@$(MAKE) check-pycde-installed || \
		if [ -f "3rd-party/circt/frontends/PyCDE/dist/"*.whl ]; then \
			$(MAKE) install-pycde-wheel; \
		else \
			$(MAKE) install-pycde-pip || $(MAKE) build-pycde-source; \
		fi && \
		$(MAKE) verify-pycde-installation && \
		touch $(CURDIR)/$@

clean-circt:
	@echo "Cleaning CIRCT build artifacts and uninstalling PyCDE..."
	@if [ -d "$(VENV_DIR)" ]; then \
		$(VENV_DIR)/bin/pip uninstall -y pycde 2>/dev/null || true; \
	fi
	@rm -rf 3rd-party/circt/dist 3rd-party/circt/build 3rd-party/circt/*.egg-info 2>/dev/null || true
	@bash scripts/patch-apply.sh reverse scripts/init/patches/circt.patch 2>/dev/null || true
	@rm -f 3rd-party/circt/.patch-applied 3rd-party/circt/.circt-built
	@echo "CIRCT clean completed."
