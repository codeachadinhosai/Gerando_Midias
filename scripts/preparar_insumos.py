'''Wrapper compatível para pipeline_flow.services.preparar_insumos.'''

from pipeline_flow.services.preparar_insumos import *  # noqa: F403
from pipeline_flow.services.preparar_insumos import main


if __name__ == '__main__':
    raise SystemExit(main())
