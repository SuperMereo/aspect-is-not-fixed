# Docker environment

A single image contains R 4.6, brms, ordbetareg, tidyverse, and CmdStan for
running [`analysis/reproduce.ipynb`](../analysis/reproduce.ipynb).
The image also contains Python with pandas and scipy, plus Node, for the
data-preparation and stimulus-generation scripts in
[`data/scripts/`](../data/scripts/README.md) and
[`materials/scripts/`](../materials/README.md), and the layers-record generator
and validator. The validator also requires `npm install` in
`data/scripts/`.

The base image is pinned by digest, so a rebuild reproduces the same R 4.6.1
and the same CRAN-as-apt package snapshot even after the `rocker/r2u:noble`
tag moves. Running natively is possible, but brms fits are
sensitive to the Stan version underneath them, and the runtimes and the cached
`.rds` files quoted elsewhere all assume this image.

The image exposes exactly one Jupyter kernel, **R 4.6 (brms)**, so if the
picker offers anything else, the session is not running in the container.

---

## 1. Prerequisites

- Docker Desktop 4.30+ (macOS/Windows) or Docker Engine 24+ with the Compose v2 plugin (Linux).
- ~4 GB free disk for the image.
- ~4 GB RAM headroom; Stan sampling will use more if available.

Check:

```bash
docker --version
docker compose version
```

---

## 2. Build

From the repository root:

```bash
cd docker
docker compose build
```

The first build takes 10–20 minutes (downloads CmdStan, brms binaries).
Subsequent builds are cached.

To rebuild from scratch:

```bash
docker compose build --no-cache
```

---

## 3. Run

```bash
docker compose up
```

Jupyter is at http://localhost:8888 with no token (see the security note
below).

To stop: `Ctrl-C`, or in another terminal `docker compose down`.

To run detached and follow the logs:

```bash
docker compose up -d
docker compose logs -f
```

Shell into the running container (for `Rscript`, debugging):

```bash
docker compose exec aspectual-similarity bash
```

### Security note

The default command launches Jupyter with no token and no password bound
to `0.0.0.0:8888`. The default Compose mapping, `8888:8888`, may expose that
port on every host interface. Run it only on a trusted machine and network, or
change the mapping to `127.0.0.1:8888:8888` before starting the container.

---

## 4. Write access to the repo

The repository is bind-mounted at `/workspace`:

```yaml
volumes:
  - ..:/workspace
```

Anything the notebook writes under `/workspace/...` lands in the working tree
on the host: `analysis/fits/*.rds`, `analysis/cache/*.rds`, and
`figures/*.{pdf,png}`.

### Ownership

- On macOS/Windows Docker Desktop, ownership is mapped transparently, so there is nothing to do.
- On Linux, the container runs as root by default. Either `sudo chown -R $USER:$USER ../figures` afterwards, or uncomment the `user:` line in `docker/docker-compose.yml` and export the host IDs:
    ```bash
    export HOST_UID=$(id -u) HOST_GID=$(id -g)
    docker compose up
    ```

---

## 5. Notebook

Open [`analysis/reproduce.ipynb`](../analysis/reproduce.ipynb) and select the
**R 4.6 (brms)** kernel. The notebook is ordered by paper section. Run cells
top to bottom. See [`analysis/README.md`](../analysis/README.md) for inputs,
outputs, and runtime.

### CmdStan

CmdStan is preinstalled at `/opt/cmdstan` and registered with `cmdstanr`. brms
uses its default `rstan` backend. Pass `backend = "cmdstanr"` per fit for
faster compiles.

---

## 6. Other scripts (Python and Node)

The Python data-preparation and stimulus-generation scripts and the Node layers
validator run in the same image. Use `docker compose run --rm` for a single run, or
`docker compose exec` against an already-running container:

```bash
# Rebuild the cloze stimulus lists
docker compose run --rm aspectual-similarity \
    python3 materials/scripts/make_items_json.py

# Regenerate the layers records
docker compose run --rm aspectual-similarity \
    python3 data/scripts/generate_metadata.py

# Validate them: the layers lexicons live outside the repo, so mount the
# checkout and point LAYERS_LEXICONS at it inside the container.
docker compose run --rm \
    -v /path/to/layers-0.9.0/lexicons:/lexicons:ro \
    -e LAYERS_LEXICONS=/lexicons \
    aspectual-similarity node data/scripts/validate_metadata.mjs
```

The scripts that read the raw JATOS dumps or the OntoNotes tarball need those
inputs mounted, since neither is shipped, and validation likewise needs the
layers lexicons mounted. See [`data/scripts/README.md`](../data/scripts/README.md).

---

## 7. Common operations

```bash
# Rebuild after editing the Dockerfile
docker compose build

# Tail the Jupyter log
docker compose logs -f

# Open a shell to install ad-hoc packages
docker compose exec aspectual-similarity bash
#   R -e 'install.packages("foo")'

# Wipe the brms compiled-model cache
docker compose down -v
```

---

## 8. Troubleshooting

| Symptom                                                        | Fix                                                                                       |
|----------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| `Port 8888 already in use`                                     | Change the host side of the mapping in `docker-compose.yml`, e.g. `"8899:8888"`.          |
| R kernel missing from the picker                               | The IRkernel install step failed. `docker compose build --no-cache` and watch the output. |
| brms model recompiles every notebook run                       | Ensure the `r-cache` named volume is mounted (default). Inspect with `docker volume ls`.  |
| `Permission denied` writing under the repo (Linux)             | See the Ownership section above; switch to `user: "$HOST_UID:$HOST_GID"`.                 |
| Stan complains about `/dev/shm`                                | Increase `shm_size` in `docker-compose.yml` (default 2 GB).                               |
