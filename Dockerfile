ARG OPENLANE_TAG=2.3.10
FROM ghcr.io/efabless/openlane2:${OPENLANE_TAG}

ENV WORKSHOP_ROOT=/workshop \
    PDK=sky130A \
    STD_CELL_LIBRARY=sky130_fd_sc_hd

USER root
WORKDIR /workshop

# Bake the PDK revision OpenLane 2.3.10 expects (avoids re-download each run).
RUN set -e; \
    if command -v volare >/dev/null 2>&1; then \
      volare enable --pdk sky130 0fe599b2afb6708d281543108caf8310912f54af || \
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
COPY README.md /workshop/README.md

ENV PATH="/workshop/scripts:${PATH}"

RUN chmod +x /workshop/run_stage.sh /workshop/scripts/openroad_gui

WORKDIR /workshop
CMD ["bash"]
