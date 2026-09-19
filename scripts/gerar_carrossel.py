'''Wrapper compatível para pipeline_flow.services.gerar_carrossel.'''

from pipeline_flow.services.gerar_carrossel import *  # noqa: F403
from pipeline_flow.services.gerar_carrossel import main


if __name__ == '__main__':
    raise SystemExit(main())
