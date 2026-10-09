sudo dnf config-manager setopt max_parallel_downloads=10 fastestmirror=True

sudo dnf install \
  cmake-filesystem hipblas hipcc numactl-libs rocblas \
  rocm-clang rocm-clang-devel rocm-clang-libs rocm-clang-runtime-devel \
  rocm-comgr rocm-device-libs rocm-hip rocm-libc++ rocm-libc++-devel \
  rocm-lld rocm-llvm rocm-llvm-devel rocm-llvm-filesystem \
  rocm-llvm-libs rocm-llvm-static rocm-runtime rocm-runtime-devel \
  rocsolver zlib-ng-compat-devel zstd

curl -fsSL https://ollama.com/install.sh | sh
curl -fsSL https://opencode.ai/v2/install | bash

ollama launch opencode --model qwen3.5:9b

# Tenant learning platform local setup performed on Fedora 44 Toolbx.
# OS: Fedora Linux 44 Toolbx Container Image.
# Kernel/architecture: Linux 7.2.8-200.fc44.x86_64, x86_64.
# System package managers detected: dnf5 5.4.6.0 and rpm.
# Other tools detected: git and npm.
# Not detected globally during setup: pip3, psql, sqlite3.
# Runtime language detected: Python 3.14.7.
# Python package command `pip3` was not installed globally; project dependencies
# were installed only inside the local `.venv` virtual environment.

python3 -m venv .venv

# Packaging tools installed/upgraded inside `.venv`:
# - pip 26.2.1: Python package installer used inside the virtualenv.
# - setuptools 84.0.0: Python packaging support installed by pip.
# - wheel 0.48.0: Wheel package support installed by pip.
# - packaging 26.3: Transitive dependency for wheel.
.venv/bin/python -m pip install --upgrade pip setuptools wheel

# Application dependencies installed inside `.venv`:
# - Django 6.1.2: web framework for the application.
# - djangorestframework 3.18.3: API framework for future REST endpoints.
# - psycopg 3.3.6 and psycopg-binary 3.3.6: PostgreSQL driver support.
# - asgiref 3.12.1 and sqlparse 0.6.0: Django transitive dependencies.
.venv/bin/python -m pip install Django djangorestframework "psycopg[binary]"

# Exact resolved Python dependencies were written to requirements.txt.
