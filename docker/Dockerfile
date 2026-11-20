# Analysis image for White, Grimm, & Glass (2026).
#
# R 4.6 kernel with brms + ordbetareg + tidyverse for the cloze,
# proportion, and similarity analyses in analysis/reproduce.ipynb. Python
# (pandas, scipy) and Node provide the runtimes used by the repository scripts.
#
# Build:   docker build -f docker/Dockerfile -t aspectual-similarity:latest .
# Run:     docker compose up   (see docker/docker-compose.yml)

# rocker/r2u ships current Ubuntu R + r2u + bspm preconfigured (CRAN as
# apt binaries). Plain rocker/r-ver gives a different R version than r2u's
# noble repo expects, which breaks the apt install below. The base is pinned by
# digest so rebuilds reproduce the same R 4.6.1 and CRAN-as-apt snapshot rather
# than tracking the moving :noble tag.
FROM rocker/r2u:noble@sha256:816279dd028627eef4c06416a25fb47f8943bab5f505f81510db55d5386667c5

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# System libraries for brms, CmdStan compilation, and Cairo/font rendering in
# showtext and ggsave (SVG/PDF/PNG).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl wget gnupg lsb-release \
        build-essential gfortran make cmake git \
        libcurl4-openssl-dev libssl-dev libxml2-dev \
        libfontconfig1-dev libfreetype6-dev libpng-dev libjpeg-dev libtiff5-dev \
        libcairo2-dev libxt-dev libharfbuzz-dev libfribidi-dev \
        libv8-dev libnode-dev \
        pandoc \
        zlib1g-dev liblzma-dev libbz2-dev \
    && rm -rf /var/lib/apt/lists/*

# R packages via r2u (apt repo is already configured by the base image).
# Notebook: brms, ordbetareg, posterior, betareg, tidyverse, ggrepel,
#           patchwork, MASS, showtext, scales.
# Jupyter R kernel: IRkernel + supporting deps.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        r-cran-brms \
        r-cran-tidyverse \
        r-cran-posterior \
        r-cran-betareg \
        r-cran-ggrepel \
        r-cran-patchwork \
        r-cran-mass \
        r-cran-showtext \
        r-cran-scales \
        r-cran-rstan \
        r-cran-irkernel \
        r-cran-repr \
        r-cran-pbdzmq \
        r-cran-uuid \
        r-cran-digest \
        r-cran-evaluate \
        r-cran-jsonlite \
        r-cran-crayon \
        jupyter-notebook \
    && rm -rf /var/lib/apt/lists/*

# Python and Node runtimes for data preparation, stimulus generation, and
# metadata validation:
#   - data/scripts/make_{cloze,proportion,similarity}_data.py and the
#     materials/scripts/*.ipynb stimulus generators need pandas (+ scipy).
#   - data/scripts/make_propbank_sense_distribution.py, generate_metadata.py,
#     anonymize.py, and materials/scripts/make_items_json.py are standard
#     library only.
#   - data/scripts/validate_metadata.mjs needs Node; its @atproto/lexicon
#     dependency is installed with `npm install` in data/scripts at run time.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-pip \
        python3-pandas python3-scipy python3-numpy \
        nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# ordbetareg is on CRAN but not always packaged in r2u; install via R (bspm
# will still resolve dependencies to binaries where possible).
RUN R -e "install.packages('ordbetareg')"

# cmdstanr is not on CRAN; install from the stan-dev R-universe.
RUN R -e "install.packages('cmdstanr', repos = c('https://stan-dev.r-universe.dev', getOption('repos')))"

# CmdStan toolchain (brms can dispatch to cmdstanr backend for faster compiles).
ENV CMDSTAN=/opt/cmdstan
RUN R -e "cmdstanr::install_cmdstan(dir = '/opt', cores = 2)" \
    && CMDSTAN_DIR="$(ls -d /opt/cmdstan-* | tail -n1)" \
    && ln -sfn "${CMDSTAN_DIR}" /opt/cmdstan \
    && R -e "cmdstanr::set_cmdstan_path('/opt/cmdstan')"

# betareg (used for the §5.5 dissimilarity smooth) calls statmod::gauss.quad at
# fit time but only Suggests statmod, so r2u does not install it automatically.
# Add it explicitly; without it the similarity_by_match figure cell fails.
RUN apt-get update \
    && apt-get install -y --no-install-recommends r-cran-statmod \
    && rm -rf /var/lib/apt/lists/*

# The jupyter-notebook package is minimal: it ships neither `jupyter kernelspec`
# (which IRkernel::installspec calls to register the kernel) nor
# `jupyter nbconvert` (used to execute analysis/reproduce.ipynb end-to-end).
# Add both so the R kernel registers and the notebook runs headless.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        jupyter-client jupyter-nbconvert \
    && rm -rf /var/lib/apt/lists/*

# Register the R kernel for the system Jupyter.
RUN R -e "IRkernel::installspec(name = 'ir', displayname = 'R 4.6 (brms)', user = FALSE)"

WORKDIR /workspace
EXPOSE 8888

# Default: tokenless Jupyter server. Restrict the published host port in Compose.
CMD ["jupyter", "notebook", \
     "--ip=0.0.0.0", "--port=8888", "--no-browser", \
     "--ServerApp.token=", "--ServerApp.password=", \
     "--ServerApp.root_dir=/workspace", \
     "--allow-root"]
