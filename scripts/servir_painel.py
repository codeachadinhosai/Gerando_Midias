'''Wrapper compatível para o backend local somente leitura.'''

from pipeline_flow.web.app import main


if __name__ == '__main__':
    raise SystemExit(main())
