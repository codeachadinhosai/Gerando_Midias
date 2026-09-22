"""Wrapper compativel para o diagnostico seguro de configuracao."""

from pipeline_flow.services.diagnosticar_configuracao import *
from pipeline_flow.services.diagnosticar_configuracao import main

if __name__ == "__main__":
    raise SystemExit(main())
