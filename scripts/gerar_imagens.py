'''Wrapper compativel para pipeline_flow.services.gerar_imagens.'''

from pipeline_flow.services.gerar_imagens import *  # noqa: F403
from pipeline_flow.services.gerar_imagens import main


if __name__ == '__main__':
    raise SystemExit(main())
