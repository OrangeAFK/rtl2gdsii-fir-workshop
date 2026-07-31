# Workshop image: OpenLane 2 toolchain + sky130 PDK + workshop scripts.
# Pin versions carefully — timing calibration depends on this digest.
ARG OPENLANE_TAG=2.3.10
FROM ghcr.io/efabless/openlane2:${OPENLANE_TAG}

LABEL org.opencontainers.image.title="rtl2gdsii-fir-workshop"
LABEL org.opencontainers.image.description="IEEE SSCS ASIC PD workshop (FIR timing narrative)"

ENV WORKSHOP_ROOT=/workshop \
    PDK=sky130A \
    STD_CELL_LIBRARY=sky130_fd_sc_hd \
    # volare/ciel default PDK location inside OpenLane images
    PDK_ROOT=/home/openlane/.ciel

USER root
WORKDIR /workshop

# Bake sky130 PDK into the image so the session needs no network for tools/PDK.
# Uses OpenLane's volare/ciel helper when available.
RUN set -e; \
    if command -v openlane >/dev/null 2>&1; then \
      openlane --version || true; \
    fi; \
    if command -v volare >/dev/null 2>&1; then \
      volare enable --pdk sky130 $(volare ls-remote --pdk sky130 2>/dev/null | head -n1 || true) || \
      volare enable sky130 || true; \
    elif command -v ciel >/dev/null 2>&1; then \
      ciel enable --pdk sky130 || true; \
    else \
      echo "WARNING: volare/ciel not found — ensure PDK is present in base image"; \
    fi

COPY design /workshop/design
COPY config /workshop/config
COPY scripts /workshop/scripts
COPY run_stage.sh /workshop/run_stage.sh
COPY docs /workshop/docs
COPY slides /workshop/slides
COPY README.md /workshop/README.md

RUN chmod +x /workshop/run_stage.sh \
    /workshop/scripts/openroad_gui \
    && ln -sf /workshop/scripts/openroad_gui /usr/local/bin/openroad_gui \
    && ln -sf "$(command -v klayout || echo /usr/bin/klayout)" /usr/local/bin/klayout-workshop || true

# Non-root when the base image provides an openlane user
RUN if id openlane >/dev/null 2>&1; then chown -R openlane:openlane /workshop; fi
USER openlane

WORKDIR /workshop
CMD ["bash"]
