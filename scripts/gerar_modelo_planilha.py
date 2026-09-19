'''Wrapper compatível para pipeline_flow.services.gerar_modelo_planilha.'''

from pipeline_flow.services.gerar_modelo_planilha import *  # noqa: F403
from pipeline_flow.services.gerar_modelo_planilha import main


if __name__ == '__main__':
    raise SystemExit(main())
