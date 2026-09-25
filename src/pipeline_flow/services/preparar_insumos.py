"""Preparação local de insumos Flow. Apenas biblioteca padrão; nunca chama geração."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from copy import copy
from datetime import UTC, datetime
from pathlib import Path

from pipeline_flow.config import load_config
from pipeline_flow.domain import (
    STATE_FIELDS,
    CarouselStatus,
    ImageStatus,
    PipelineStatus,
    VideoStatus,
    normalize_state,
    normalize_states,
)
from pipeline_flow.services.execution_control import (
    LockError,
    acquire_lock,
    release_lock,
)

ROOT = Path(__file__).resolve().parents[3]
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MAIN = NS["m"]
LEGACY_HEADERS = "classifica arquivo produto_id producao_id ordem papel_na_producao link_produto usar_com tipo_referencia material_existente uso_material instrucao status classificacao fluxo plano_arquivo imagem_status imagem_arquivo aprovacao video_status video_arquivo erro atualizado_em fala_audio".split()
CAROUSEL_HEADERS = "gerar_carrossel cta_destino cta_palavra texto_carrossel subtexto_carrossel carrossel_status carrossel_arquivo".split()
HEADERS = LEGACY_HEADERS + CAROUSEL_HEADERS
HUMAN = HEADERS[:12] + ["aprovacao", "fala_audio", "gerar_carrossel", "cta_destino", "cta_palavra"]
FLOW_NAMES = ["abertura_julia", "apresentacao_julia", "pov_pegar", "pov_apresentar", "detalhes_produto", "demonstracao_uso", "lifestyle", "ambientacao", "cta_final"]
CATEGORIES = ["AberturaJulia", "ApresentacaoJulia", "POVPegar", "POVApresentar", "DetalhesProduto", "DemonstracaoUso", "Lifestyle", "Ambientacao", "CTAFinal"]
FLOWS = {f"{i:02d}_{name}": cat for i, (name, cat) in enumerate(zip(FLOW_NAMES, CATEGORIES), 1)}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MEDIA_EXT = IMAGE_EXT | {".mp4", ".mov", ".mkv", ".webm"}
REF_TYPES = {"base_edicao", "produto", "inspiracao", "detalhe", "ambiente", "identidade_rosto", "identidade_corpo", "identidade_mao", "material_existente"}
SHEET_REF_TYPES = {"", "base_edicao", "produto", "inspiracao", "detalhe", "ambiente", "outro"}

class Invalid(ValueError):
    pass

def norm(value):
    return "".join(c for c in unicodedata.normalize("NFD", str(value or "").strip().lower()) if unicodedata.category(c) != "Mn")

def require(condition, message):
    if not condition:
        raise Invalid(message)

def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def signature(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def safe_id(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,119}", value), f"ID inválido: {value!r}")
    return value

def inside(base, relative):
    require(isinstance(relative, str) and relative, "Caminho vazio.")
    base = Path(base).resolve()
    p = (base / relative).resolve()
    require(p.is_relative_to(base), f"Caminho fora do pacote: {relative}")
    return p

def now():
    return datetime.now(UTC).isoformat()

def column_name(index):
    """Converte indice baseado em zero para coluna Excel (A, Z, AA...)."""
    result = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result

def serialize_sheet(tree, original):
    """Keep namespace declarations referenced by MC attribute values."""
    namespaces = {}
    for event, item in ET.iterparse(io.BytesIO(original), events=("start-ns", "start")):
        if event == "start":
            break
        namespaces[item[0]] = item[1]
    # Recover declarations lost by older versions of this writer.
    known = {
        "x14ac": "http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac",
        "xr": "http://schemas.microsoft.com/office/spreadsheetml/2014/revision",
        "xr2": "http://schemas.microsoft.com/office/spreadsheetml/2015/revision2",
        "xr3": "http://schemas.microsoft.com/office/spreadsheetml/2016/revision3",
    }
    mc = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Ignorable"
    for element in tree.iter():
        for prefix in element.get(mc, "").split():
            if prefix not in namespaces:
                require(prefix in known, f"Namespace desconhecido: {prefix}")
                namespaces[prefix] = known[prefix]
    result = ET.tostring(tree, encoding="unicode")
    root_end = result.index(">")
    declarations = dict(re.findall(r'xmlns(?::([\w.-]+))?="([^"]*)"', result[:root_end]))
    from xml.sax.saxutils import quoteattr
    additions = []
    for prefix, uri in namespaces.items():
        if prefix in declarations:
            require(declarations[prefix] == uri, f"Namespace conflitante: {prefix}")
        else:
            name = "xmlns:" + prefix if prefix else "xmlns"
            additions.append(" " + name + "=" + quoteattr(uri))
    result = result[:root_end] + "".join(additions) + result[root_end:]
    return ('<?xml version="1.0" encoding="utf-8"?>\n' + result).encode("utf-8")

def serialized_workbook_save(method):
    def wrapper(self, *args, **kwargs):
        lock_path = (
            self.path.parent
            / 'backups'
            / ('.' + self.path.name + '.lock')
        )
        try:
            handle = acquire_lock(
                lock_path,
                'salvar-planilha',
                context={'planilha': str(self.path.resolve())},
            )
        except LockError as exc:
            raise Invalid(str(exc)) from exc
        try:
            result = method(self, *args, **kwargs)
        except BaseException as operation_error:
            try:
                release_lock(handle)
            except LockError as lock_error:
                operation_error.add_note(
                    f'Falha adicional ao liberar lock da planilha: {lock_error}'
                )
            raise
        try:
            release_lock(handle)
        except LockError as exc:
            raise Invalid(str(exc)) from exc
        return result

    return wrapper


class Workbook:
    """Preserva partes XLSX não editadas; Controle usa linhas 1, 2, 3 e dados desde 4."""
    def __init__(self, path, allow_legacy=False):
        self.path = Path(path)
        self.original_hash = digest(self.path)
        with zipfile.ZipFile(self.path) as z:
            self.parts = {n: z.read(n) for n in z.namelist()}
        wb = ET.fromstring(self.parts["xl/workbook.xml"])
        rels = {r.attrib["Id"]: r.attrib["Target"] for r in ET.fromstring(self.parts["xl/_rels/workbook.xml.rels"])}
        sheet = next((s for s in wb.find("m:sheets", NS) if s.attrib["name"] == "Controle"), None)
        require(sheet is not None, "Aba Controle ausente.")
        target = rels[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
        self.sheet_path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        self.tree = ET.fromstring(self.parts[self.sheet_path])
        self.strings = []
        if "xl/sharedStrings.xml" in self.parts:
            self.strings = ["".join(e.itertext()) for e in ET.fromstring(self.parts["xl/sharedStrings.xml"]).findall("m:si", NS)]
        self.rows = {}
        for row in self.tree.findall("m:sheetData/m:row", NS):
            values = {}
            for c in row.findall("m:c", NS):
                v = c.find("m:v", NS)
                value = v.text if v is not None else ""
                if c.attrib.get("t") == "s":
                    value = self.strings[int(value)]
                elif c.attrib.get("t") == "inlineStr":
                    inline = c.find("m:is", NS)
                    value = "".join(inline.itertext()) if inline is not None else ""
                require(c.find("m:f", NS) is None, f"Fórmulas não são aceitas em Controle: {c.attrib['r']}")
                values[re.sub(r"\d", "", c.attrib["r"])] = value or ""
            self.rows[int(row.attrib["r"])] = values
        actual = [self.rows.get(1, {}).get(column_name(i)) for i in range(len(HEADERS))]
        self.legacy = actual[:len(LEGACY_HEADERS)] == LEGACY_HEADERS and not any(actual[len(LEGACY_HEADERS):])
        require(actual == HEADERS or (allow_legacy and self.legacy), f"Cabeçalhos de Controle diferentes do contrato de {len(HEADERS)} colunas. Execute corrigir-planilha.")

    def raw_records(self):
        return [
            {
                **{
                    name: cols.get(column_name(i), '').strip()
                    for i, name in enumerate(HEADERS)
                },
                '_linha': index,
            }
            for index, cols in self.rows.items()
            if index >= 4 and any(cols.values())
        ]

    def records(self):
        return [normalize_states(record) for record in self.raw_records()]

    def set(self, index, field, value):
        require(field in HEADERS[12:], "Não alterar campo humano.")
        if field == "aprovacao":
            require(
                str(value) == "",
                "O sistema pode somente revogar aprovação; nunca aprová-la.",
            )
        self._set_cell(index, field, value)

    def set_human_approval(self, index, value):
        # Caminho reservado a uma decisão humana confirmada pela interface.
        value = norm(value)
        require(
            value in {'aprovada', 'rejeitada'},
            'Decisão humana deve ser aprovada ou rejeitada.',
        )
        self._set_cell(index, 'aprovacao', value)

    def _set_cell(self, index, field, value):
        if field in STATE_FIELDS:
            value = normalize_state(field, value)
        data = self.tree.find("m:sheetData", NS)
        row = next((r for r in data if int(r.attrib["r"]) == index), None)
        require(row is not None, f"Linha ausente: {index}")
        address = column_name(HEADERS.index(field)) + str(index)
        cell = next((c for c in row if c.attrib.get("r") == address), None)
        if cell is None:
            cell = ET.SubElement(row, f"{{{MAIN}}}c", {"r": address})
        for child in list(cell):
            cell.remove(child)
        cell.set("t", "inlineStr")
        ET.SubElement(ET.SubElement(cell, f"{{{MAIN}}}is"), f"{{{MAIN}}}t").text = str(value)
        row[:] = sorted(row, key=lambda c: (len(re.sub(r"\d", "", c.attrib["r"])), re.sub(r"\d", "", c.attrib["r"])))

    def fix_validations(self):
        validations = self.tree.find("m:dataValidations", NS)
        removed = []
        if validations is not None:
            for v in list(validations):
                if v.attrib.get("sqref") in {"O4:O500", "R4:R500"}:
                    removed.append(v.attrib["sqref"])
                    validations.remove(v)
            validations.set("count", str(len(validations)))
        return removed

    def ensure_carousel_dropdowns(self):
        validations = self.tree.find("m:dataValidations", NS)
        if validations is None:
            validations = ET.Element(f"{{{MAIN}}}dataValidations", {"count": "0"})
            sheet_data = self.tree.find("m:sheetData", NS)
            children = list(self.tree)
            self.tree.insert(children.index(sheet_data) + 1, validations)
        existing = {v.attrib.get("sqref"): v for v in validations}
        specs = [
            ("Y4:Y500", '"sim,não"', True, "Escolha sim para gerar o card ou não para ignorar."),
            ("Z4:Z500", '"grupo de achadinhos,direct,link da bio,comentários,WhatsApp"', True, "Escolha para onde a chamada deve direcionar a pessoa."),
            ("AA4:AA500", '"QUARTO,COZINHA,ORGANIZAÇÃO,WAFFLE,CASA,ACHADINHOS"', False, "Escolha uma sugestão ou digite outra palavra curta em maiúsculas."),
        ]
        added = []
        for target, formula, strict, message in specs:
            if target == "Z4:Z500":
                formula = '"grupo de achadinhos,direct,link da bio,coment\u00e1rios,WhatsApp,link da bio; coment\u00e1rios,direct; coment\u00e1rios"'
                strict = False
                message = "Escolha uma combinacao ou digite destinos separados por ponto e virgula."
            attrs = {"type": "list", "allowBlank": "1", "showInputMessage": "1", "showErrorMessage": "1" if strict else "0",
                     "showDropDown": "0", "sqref": target, "promptTitle": "Carrossel", "prompt": message}
            validation = existing.get(target)
            formula_node = validation.find("m:formula1", NS) if validation is not None else None
            current_formula = formula_node.text if formula_node is not None else None
            if validation is None:
                validation = ET.SubElement(validations, f"{{{MAIN}}}dataValidation", attrs)
                formula_node = ET.SubElement(validation, f"{{{MAIN}}}formula1")
            if current_formula != formula or any(validation.attrib.get(key) != value for key, value in attrs.items()):
                validation.attrib.clear()
                validation.attrib.update(attrs)
                if formula_node is None:
                    formula_node = ET.SubElement(validation, f"{{{MAIN}}}formula1")
                formula_node.text = formula
                added.append(target)
        validations.set("count", str(len(validations)))
        return added

    def add_carousel_columns(self):
        if not self.legacy:
            return []
        owners = ["VOCÊ", "VOCÊ/IA", "VOCÊ/IA", "SISTEMA", "SISTEMA", "SISTEMA", "SISTEMA"]
        descriptions = [
            "sim = gerar card 9:16 após aprovação; não ou vazio = não gerar.",
            "Destino autorizado da CTA; se vazio no card CTA, a IA escolhe uma ação segura.",
            "Palavra-chave autorizada; se vazia no card CTA, a IA escolhe uma palavra coerente.",
            "Título editorial criado pela IA; máximo de 52 caracteres e 3 linhas.",
            "Faixa curta de destaque; máximo de 28 caracteres e 2 linhas.",
            "Estado da renderização local do carrossel.",
            "Caminho do card 9:16 exportado em entregas_flow.",
        ]
        sheet_data = self.tree.find("m:sheetData", NS)
        for offset, header in enumerate(CAROUSEL_HEADERS, len(LEGACY_HEADERS)):
            column = column_name(offset)
            for row_number, value in ((1, header), (2, owners[offset-len(LEGACY_HEADERS)]), (3, descriptions[offset-len(LEGACY_HEADERS)])):
                row = next(r for r in sheet_data if int(r.attrib["r"]) == row_number)
                address = column + str(row_number)
                cell = ET.SubElement(row, f"{{{MAIN}}}c", {"r": address})
                template = next((c for c in row if c.attrib.get("r") == column_name(len(LEGACY_HEADERS)-1) + str(row_number)), None)
                if template is not None and template.attrib.get("s"):
                    cell.set("s", template.attrib["s"])
                cell.set("t", "inlineStr")
                ET.SubElement(ET.SubElement(cell, f"{{{MAIN}}}is"), f"{{{MAIN}}}t").text = value
                self.rows.setdefault(row_number, {})[column] = value
        dimension = self.tree.find("m:dimension", NS)
        if dimension is not None:
            dimension.set("ref", f"A1:{column_name(len(HEADERS)-1)}500")
        self.legacy = False
        return CAROUSEL_HEADERS

    @serialized_workbook_save
    def save(self):
        require(digest(self.path) == self.original_hash, "Excel mudou durante a operação. Reexecute para preservar a edição humana.")
        self.parts[self.sheet_path] = serialize_sheet(self.tree, self.parts[self.sheet_path])
        backup = self.path.parent / "backups" / (self.path.stem + "_" + self.original_hash[:12] + ".xlsx")
        backup.parent.mkdir(exist_ok=True)
        if not backup.exists():
            shutil.copy2(self.path, backup)
        handle, temporary = tempfile.mkstemp(suffix=".xlsx", dir=self.path.parent)
        os.close(handle)
        try:
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as z:
                for name, content in self.parts.items():
                    z.writestr(name, content)
            require(digest(self.path) == self.original_hash, "Excel mudou antes de salvar.")
            os.replace(temporary, self.path)
        finally:
            if Path(temporary).exists():
                Path(temporary).unlink()


def _control_snapshot(sheet):
    rows = []
    for row_number in range(4, max(sheet.max_row, 4) + 1):
        row = []
        for column in range(1, len(HEADERS) + 1):
            cell = sheet.cell(row_number, column)
            hyperlink = cell.hyperlink.target if cell.hyperlink else None
            value = None if cell.value in (None, '') else cell.value
            row.append((value, hyperlink))
        rows.append(tuple(row))
    return tuple(rows)


def _identity_type(filename, description):
    value = norm(f'{filename} {description}')
    if 'mao' in value or 'unha' in value:
        return 'identidade_mao'
    if 'corpo' in value or 'silhueta' in value:
        return 'identidade_corpo'
    return 'identidade_rosto'


def _spreadsheet_structure_is_current(path):
    from openpyxl import Workbook as OpenpyxlWorkbook
    from openpyxl import load_workbook

    from pipeline_flow.services.gerar_modelo_planilha import (
        add_example,
        add_guide,
        configure_control,
    )

    def values(sheet):
        return tuple(
            tuple(
                None if cell.value in (None, '') else cell.value
                for cell in row
            )
            for row in sheet.iter_rows()
        )

    def validations(sheet):
        return sorted(
            (
                str(item.sqref),
                item.formula1,
                bool(item.showErrorMessage),
            )
            for item in sheet.data_validations.dataValidation
        )

    def view_state(sheet):
        pane = sheet.sheet_view.pane
        pane_state = None if pane is None else (
            pane.xSplit,
            pane.ySplit,
            pane.topLeftCell,
            pane.activePane,
            pane.state,
        )
        selections = tuple(
            (item.pane, item.activeCell, str(item.sqref))
            for item in sheet.sheet_view.selection
        )
        return pane_state, selections

    expected = OpenpyxlWorkbook()
    configure_control(expected.active)
    add_guide(expected)
    add_example(expected)
    workbook = load_workbook(path)
    try:
        required = {
            'Controle',
            'Guia',
            'Referencias_Identidade',
            'Exemplo_Producao',
        }
        if not required.issubset(workbook.sheetnames):
            return False
        control = workbook['Controle']
        expected_control = expected['Controle']
        return all(
            [
                control.cell(row, column).value
                for column in range(1, len(HEADERS) + 1)
            ]
            == [
                expected_control.cell(row, column).value
                for column in range(1, len(HEADERS) + 1)
            ]
            for row in (1, 2, 3)
        ) and all(
            (
                str(control.freeze_panes) == str(expected_control.freeze_panes),
                view_state(control) == view_state(expected_control),
                control.auto_filter.ref == expected_control.auto_filter.ref,
                validations(control) == validations(expected_control),
                len(control.conditional_formatting)
                == len(expected_control.conditional_formatting),
                values(workbook['Guia']) == values(expected['Guia']),
                values(workbook['Exemplo_Producao'])
                == values(expected['Exemplo_Producao']),
                [
                    workbook['Referencias_Identidade'].cell(1, column).value
                    for column in range(1, 4)
                ]
                == ['tipo', 'arquivo', 'observação'],
            )
        )
    finally:
        workbook.close()
        expected.close()


def update_spreadsheet_structure(path):
    from openpyxl import load_workbook

    from pipeline_flow.services.gerar_modelo_planilha import (
        DESCRIPTIONS,
        OWNERS,
        add_example,
        add_guide,
        configure_control,
        style_header,
    )

    path = Path(path).resolve()
    require(path.is_file(), f'Planilha ausente: {path}')
    original_hash = digest(path)
    Workbook(path, allow_legacy=True)
    if _spreadsheet_structure_is_current(path):
        workbook = load_workbook(path)
        snapshot = _control_snapshot(workbook['Controle'])
        sheets = workbook.sheetnames
        workbook.close()
        return {
            'planilha': str(path),
            'backup': None,
            'linhas_operacionais_preservadas': sum(
                1
                for row in snapshot
                if any(value not in (None, '') for value, _ in row)
            ),
            'abas': sheets,
            'referencias_atualizadas': [],
            'estrutura': [],
            'resultado': 'planilha ja sincronizada',
        }
    lock_path = path.parent / 'backups' / ('.' + path.name + '.lock')
    try:
        handle = acquire_lock(
            lock_path,
            'atualizar-estrutura-planilha',
            context={'planilha': str(path)},
        )
    except LockError as exc:
        raise Invalid(str(exc)) from exc

    temporary = None
    result = None
    try:
        workbook = load_workbook(path)
        control = workbook['Controle']
        before = _control_snapshot(control)
        actual_headers = [
            control.cell(1, index).value
            for index in range(1, len(HEADERS) + 1)
        ]
        current = actual_headers == HEADERS
        legacy = (
            actual_headers[:len(LEGACY_HEADERS)] == LEGACY_HEADERS
            and not any(actual_headers[len(LEGACY_HEADERS):])
        )
        require(current or legacy, 'Cabeçalhos de Controle não reconhecidos.')

        control.data_validations.dataValidation = []
        control.conditional_formatting._cf_rules.clear()
        configure_control(control)

        guide_index = (
            workbook.sheetnames.index('Guia')
            if 'Guia' in workbook.sheetnames
            else 1
        )
        if 'Guia' in workbook.sheetnames:
            workbook.remove(workbook['Guia'])
        add_guide(workbook, guide_index)

        reference_updates = []
        if (
            'Referencias_Julia' in workbook.sheetnames
            and 'Referencias_Identidade' in workbook.sheetnames
        ):
            raise Invalid(
                'As abas Referencias_Julia e Referencias_Identidade coexistem; '
                'revise antes de migrar.'
            )
        if 'Referencias_Julia' in workbook.sheetnames:
            references = workbook['Referencias_Julia']
            references.title = 'Referencias_Identidade'
            legacy_rows = list(references.iter_rows(min_row=2, values_only=True))
            references.delete_rows(1, references.max_row)
            references.append(['tipo', 'arquivo', 'observação'])
            for filename, description, management, *_ in legacy_rows:
                if not any(value not in (None, '') for value in (filename, description, management)):
                    continue
                observation = '. '.join(
                    str(value).strip().rstrip('.')
                    for value in (description, management)
                    if value not in (None, '')
                )
                if observation:
                    observation += '.'
                references.append([
                    _identity_type(filename, description),
                    filename,
                    observation,
                ])
            reference_updates.append('Referencias_Julia -> Referencias_Identidade')
        elif 'Referencias_Identidade' in workbook.sheetnames:
            references = workbook['Referencias_Identidade']
            references.cell(1, 1, 'tipo')
            references.cell(1, 2, 'arquivo')
            references.cell(1, 3, 'observação')
        else:
            raise Invalid('Aba de referências de identidade ausente.')
        style_header(references)
        references.column_dimensions['A'].width = 24
        references.column_dimensions['B'].width = 38
        references.column_dimensions['C'].width = 70
        for row in references.iter_rows(min_row=2):
            for cell in row:
                alignment = copy(cell.alignment)
                alignment.wrap_text = True
                alignment.vertical = 'top'
                cell.alignment = alignment

        example_index = (
            workbook.sheetnames.index('Exemplo_Producao')
            if 'Exemplo_Producao' in workbook.sheetnames
            else len(workbook.sheetnames)
        )
        if 'Exemplo_Producao' in workbook.sheetnames:
            workbook.remove(workbook['Exemplo_Producao'])
        add_example(workbook, example_index)
        workbook.active = workbook.sheetnames.index('Controle')

        after = _control_snapshot(control)
        require(before == after, 'Dados operacionais mudaram durante a atualização.')
        require(
            [control.cell(2, index).value for index in range(1, len(HEADERS) + 1)]
            == [OWNERS[name] for name in HEADERS],
            'Responsáveis da planilha não foram sincronizados.',
        )
        require(
            [control.cell(3, index).value for index in range(1, len(HEADERS) + 1)]
            == [DESCRIPTIONS[name] for name in HEADERS],
            'Descrições da planilha não foram sincronizadas.',
        )

        backup = (
            path.parent
            / 'backups'
            / f'{path.stem}_{original_hash[:12]}.xlsx'
        )
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(path, backup)

        descriptor, temporary_name = tempfile.mkstemp(
            suffix='.xlsx',
            dir=path.parent,
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        workbook.save(temporary)
        workbook.close()

        Workbook(temporary)
        verification = load_workbook(temporary)
        require(
            _control_snapshot(verification['Controle']) == before,
            'Verificação final detectou alteração nos dados operacionais.',
        )
        verification.close()
        require(
            digest(path) == original_hash,
            'Excel mudou durante a operação. Reexecute para preservar a edição humana.',
        )
        os.replace(temporary, path)
        temporary = None
        result = {
            'planilha': str(path),
            'backup': str(backup),
            'linhas_operacionais_preservadas': sum(
                1
                for row in before
                if any(value not in (None, '') for value, _ in row)
            ),
            'abas': workbook.sheetnames,
            'referencias_atualizadas': reference_updates,
            'estrutura': [
                'metadados de Controle',
                'listas suspensas',
                'formatação condicional',
                'Guia',
                'Exemplo_Producao',
            ],
        }
    except BaseException as operation_error:
        if temporary is not None and temporary.exists():
            temporary.unlink()
        try:
            release_lock(handle)
        except LockError as lock_error:
            operation_error.add_note(
                f'Falha adicional ao liberar lock da planilha: {lock_error}'
            )
        raise
    try:
        release_lock(handle)
    except LockError as exc:
        raise Invalid(str(exc)) from exc
    return result


def resolve_file(name, roots):
    require(name and not Path(name).is_absolute() and not re.match(r"^[A-Za-z]:", name), f"Use caminho relativo: {name}")
    matches = set()
    for root in roots:
        root = Path(root).resolve()
        p = (root / name).resolve()
        if p.is_relative_to(root) and p.is_file():
            matches.add(p)
        if Path(name).name == name and root.exists():
            for p in root.rglob(name):
                if p.is_file() and p.resolve().is_relative_to(root) and "backups" not in p.parts:
                    matches.add(p.resolve())
    require(len(matches) == 1, f"Arquivo ausente ou ambíguo: {name} ({len(matches)} correspondências)")
    p = matches.pop()
    require(p.suffix.lower() in MEDIA_EXT, f"Formato de referência não aceito: {p.name}")
    return p

def human_snapshot(record, *, include_audio=True):
    fields = HUMAN if include_audio else [field for field in HUMAN if field != "fala_audio"]
    return {key: record.get(key, "") for key in fields}

def validate_revision_migration(operational):
    image_status = normalize_state('imagem_status', operational.get('imagem_status', ''))
    video_status = normalize_state('video_status', operational.get('video_status', ''))
    require(image_status != ImageStatus.GENERATING and
            video_status not in {VideoStatus.GENERATED, VideoStatus.GENERATING, VideoStatus.REUSED},
            "Linha com ativo em andamento ou video concluido: nao sobrescrever estado com importacao.")
    if image_status == ImageStatus.GENERATED:
        supplied = Path(operational.get("imagem_arquivo", "")).resolve()
        require(supplied.is_file() and supplied.suffix.lower() in IMAGE_EXT,
                "Imagem gerada deve existir em imagem_arquivo para migrar a revisao.")


def same_plan_revision(operational, plan_path):
    current = operational.get('plano_arquivo')
    if not current:
        return False
    try:
        return Path(current).resolve() == Path(plan_path).resolve()
    except (OSError, TypeError, ValueError):
        return False


def prepare(root, sheet, roots, output_dir=None):
    root, sheet = Path(root), Path(sheet)
    output_dir = Path(output_dir).resolve() if output_dir else root / "preparados"
    wb = Workbook(sheet)
    groups, errors, seen = {}, [], set()
    for record in wb.records():
        try:
            require(norm(record["classifica"]) in {"sim", "nao"}, "classifica deve ser sim ou não.")
            if norm(record["classifica"]) == "nao":
                continue
            production = safe_id(record["producao_id"])
            require(record["ordem"].isdigit() and int(record["ordem"]) > 0, "ordem deve ser inteiro positivo.")
            order = int(record["ordem"])
            key = (production, order)
            require(key not in seen, "Ordem duplicada na produção.")
            seen.add(key)
            role = norm(record["papel_na_producao"]) or "automatico"
            require(role in {"automatico", "abertura", "principal", "cta"}, "papel_na_producao inválido.")
            if record["produto_id"]:
                safe_id(record["produto_id"])
            require(record["produto_id"] or role in {"abertura", "cta"}, "produto_id ausente para clipe principal/automático.")
            require(norm(record["tipo_referencia"]) in SHEET_REF_TYPES, "tipo_referencia inválido.")
            require(norm(record["gerar_carrossel"]) in {"", "sim", "nao"}, "gerar_carrossel deve ser sim ou não.")
            require(norm(record["uso_material"]) in {"", "automatico", "reutilizar", "adaptar", "referencia"}, "uso_material inválido.")
            require(not record["uso_material"] or record["material_existente"], "uso_material informado sem material_existente.")
            names = [record["arquivo"]] + [x.strip() for x in record["usar_com"].split(";") if x.strip()]
            if record["material_existente"]:
                names.append(record["material_existente"])
            refs = {name: resolve_file(name, roots) for name in names}
            item = {"linha": record["_linha"], "id_clipe": f"{production}_{order:02d}", "ordem": order,
                    "entrada": human_snapshot(record), "referencias": refs}
            groups.setdefault(production, []).append(item)
        except Invalid as exc:
            errors.append({"linha": record["_linha"], "producao_id": record["producao_id"], "erro": str(exc)})
    invalid_groups = {e["producao_id"] for e in errors}
    outputs = []
    classifier = root / "entradas/CLASSIFICADOR_UNIVERSAL.txt"
    require(classifier.is_file(), "Classificador v2 ausente em entradas.")
    for production, items in groups.items():
        if production in invalid_groups:
            continue
        items.sort(key=lambda i: i["ordem"])
        global_refs = {p.name: p for p in (root / "identidade").glob("*") if p.suffix.lower() in IMAGE_EXT}
        identity = root / "identidade/identidade.txt"
        contract = root / "CONTRATO_INSUMOS.md"
        contract_hashes = {"classificador": digest(classifier), "contrato": digest(contract)}
        identity_hash = digest(identity) if identity.exists() else None
        material = {"items": [{**i, "referencias": {n: {"origem": str(p), "sha256": digest(p)} for n, p in i["referencias"].items()}} for i in items],
                    "globais": {n: digest(p) for n, p in global_refs.items()}, "identidade": identity_hash, "contratos": contract_hashes}
        rev = signature(material)
        dest = output_dir / "pacotes" / production / rev[:16]
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            temp = Path(tempfile.mkdtemp(prefix=".pacote-", dir=dest.parent))
            try:
                inventory = {}
                def attach(p):
                    p = Path(p)
                    rid = "ref_" + signature(str(p.resolve()))[:16]
                    if rid not in inventory:
                        relative = "anexos/" + rid + p.suffix.lower()
                        (temp / "anexos").mkdir(exist_ok=True)
                        shutil.copy2(p, temp / relative)
                        inventory[rid] = {"id": rid, "arquivo": relative, "nome_original": p.name,
                                          "origem": str(p.resolve()), "sha256": digest(p)}
                    return rid
                global_ids = {n: attach(p) for n,p in global_refs.items()}
                clean_items = []
                for i in items:
                    clean_items.append({**i, "referencias": {n: attach(p) for n,p in i["referencias"].items()}})
                manifest = {"versao": "2.4-insumos", "producao_id": production, "pacote_sha256": rev,
                            "planilha": str(sheet.resolve()), "clipes": clean_items, "referencias_globais": global_ids,
                            "inventario": inventory, "contratos": contract_hashes, "identidade_sha256": identity_hash,
                            "dados_produto": [], "avisos": ["Links não consultados automaticamente; não presumir dados dessas páginas."]}
                write_json(temp / "manifesto.json", manifest)
                shutil.copy2(classifier, temp / "CLASSIFICADOR_UNIVERSAL.txt")
                shutil.copy2(contract, temp / "CONTRATO_INSUMOS.md")
                if identity.exists():
                    shutil.copy2(identity, temp / "identidade.txt")
                (temp / "ENVIAR_A_IA.txt").write_text(
                    "Envie CLASSIFICADOR_UNIVERSAL.txt + CONTRATO_INSUMOS.md + manifesto.json + identidade.txt (se aplicável) e os arquivos REAIS de anexos/.\n"
                    "O manifesto não substitui os anexos. Retorne resposta_ia.json conforme contrato, sem executar geração.\n", encoding="utf-8")
                os.replace(temp, dest)
            finally:
                if temp.exists():
                    shutil.rmtree(temp)
        outputs.append({"producao_id": production, "pacote": str(dest), "revisao": rev})
    report = {"pacotes": outputs, "pendencias": errors}
    write_json(output_dir / "relatorio_preparacao.json", report)
    return report

def text_field(value, field):
    require(isinstance(value, str) and value.strip(), f"Texto obrigatório: {field}")
    require(not any(t in value for t in ["ID_REAL", "TODO", "{{", "<preencher>"]), f"Placeholder em {field}")

def validate_response(response, manifest, package):
    require(isinstance(response, dict), "Resposta deve ser objeto JSON.")
    require(response.get("pacote_sha256") == manifest["pacote_sha256"], "Resposta pertence a outra revisão do pacote.")
    require(isinstance(response.get("clipes"), list), "Lista clipes ausente.")
    require(manifest.get("versao") in {"2.1-insumos", "2.2-insumos", "2.3-insumos", "2.4-insumos"}, "Versão de pacote não suportada.")
    complete = manifest["versao"] in {"2.2-insumos", "2.3-insumos", "2.4-insumos"}
    prod = response.get("plano_producao", {})
    require(prod.get("producao_id") == manifest["producao_id"] and prod.get("versao") == "2.0", "Produção/versão divergente.")
    expected = {c["id_clipe"]: c for c in manifest["clipes"]}
    plans = {}
    for entry in response["clipes"]:
        require(isinstance(entry, dict) and isinstance(entry.get("plano"), dict), "Cada clipe precisa de plano.")
        require(type(entry.get("incluir_bloco_identidade", True)) is bool, "incluir_bloco_identidade deve ser booleano.")
        p = entry["plano"]
        cid = safe_id(p.get("id_clipe"))
        require(cid in expected and cid not in plans, "Clipe desconhecido ou duplicado.")
        require(p.get("producao_id") == manifest["producao_id"] and p.get("versao") == "2.0", "Plano fora da produção/versão.")
        source = expected[cid]
        require(p.get("status") in {"pronto", "pendente"}, "Status de plano inválido.")
        if p["status"] == "pendente":
            text_field(p.get("motivo"), "motivo")
            require(not entry.get("prompt_imagem") and not entry.get("prompt_video"), "Pendente não pode ter prompt pronto.")
            plans[cid] = entry
            continue
        require(p.get("ordem") == source["ordem"] and p.get("produto_id") == source["entrada"]["produto_id"], "Ordem/produto foram alterados.")
        role = p.get("papel_na_producao")
        require(role in {"abertura","principal","cta"}, "Papel inválido.")
        wanted = norm(source["entrada"]["papel_na_producao"])
        require(wanted in {"","automatico",role}, "Papel humano não foi respeitado.")
        flow = p.get("classificacao", {}).get("fluxo")
        pipeline = p.get("pipeline", {})
        for flag in ("gerar_imagem", "gerar_video", "usar_ativo_existente", "aprovacao_necessaria"):
            require(type(pipeline.get(flag)) is bool, f"Booleano obrigatório: pipeline.{flag}")
        if pipeline["gerar_imagem"] or pipeline["gerar_video"]:
            require(flow in FLOWS and p["classificacao"].get("categoria") == FLOWS[flow], "Fluxo/categoria desconhecido ou incompatível.")
            expected_role = "abertura" if flow.startswith("01_") else "cta" if flow.startswith("09_") else "principal"
            require(role == expected_role, "Fluxo incompatível com papel.")
        require(pipeline.get("aspecto") == "9:16", "Aspecto deve ser 9:16.")
        require(pipeline.get("duracao_video_s") == 8 or not pipeline["gerar_video"], "Vídeos novos devem ter 8 segundos.")
        require(pipeline.get("metodo_video") in {"i2v","r2v","nenhum",None}, "Método de vídeo inválido.")
        carousel_requested = norm(source["entrada"].get("gerar_carrossel")) == "sim"
        carousel = p.get("carrossel")
        if carousel_requested:
            require(isinstance(carousel, dict) and carousel.get("ativo") is True, "Plano de carrossel obrigatório.")
            require(carousel.get("formato") == "9:16", "Carrossel deve usar formato 9:16.")
            for field, limit in (("texto", 52), ("subtexto", 28)):
                text_field(carousel.get(field), "carrossel." + field)
                require(len(carousel[field]) <= limit, f"carrossel.{field} excede {limit} caracteres.")
            cta_text = carousel.get("cta", "")
            if role == "cta":
                text_field(cta_text, "carrossel.cta")
                require(len(cta_text) <= 54, "carrossel.cta excede 54 caracteres.")
                text_field(carousel.get("cta_destino"), "carrossel.cta_destino")
                text_field(carousel.get("cta_palavra"), "carrossel.cta_palavra")
                for field in ("cta_destino", "cta_palavra"):
                    informed = source["entrada"].get(field)
                    if informed:
                        require(carousel.get(field) == informed, "carrossel." + field + " deve preservar a planilha.")
            else:
                require(cta_text in {"", None}, "Somente o card com papel cta pode exibir chamada para acao.")
                require(carousel.get("cta_destino") in {"", None}, "Somente o card cta pode definir cta_destino.")
                require(carousel.get("cta_palavra") in {"", None}, "Somente o card cta pode definir cta_palavra.")
        else:
            require(carousel is None or carousel is False or (isinstance(carousel, dict) and carousel.get("ativo") is False), "Não criar carrossel sem autorização humana.")
        refs = p.get("referencias")
        require(isinstance(refs, list), "Lista referencias ausente.")
        allowed = set(source["referencias"].values()) | set(manifest["referencias_globais"].values())
        # Demais imagens do mesmo produto podem contextualizar o clipe.
        for sibling in manifest["clipes"]:
            if source["entrada"]["produto_id"] and sibling["entrada"]["produto_id"] == source["entrada"]["produto_id"]:
                allowed.update(sibling["referencias"].values())
        ids = []
        for ref in refs:
            rid = ref.get("ref_id")
            require(rid in allowed and rid not in ids, "Referência ausente, duplicada ou de outro produto.")
            require(ref.get("tipo") in REF_TYPES, "Tipo de referência inválido.")
            require(ref.get("arquivo") == manifest["inventario"][rid]["arquivo"], "arquivo não corresponde ao ref_id.")
            text_field(ref.get("uso"), "referencias.uso")
            ids.append(rid)
        identity = p.get("identidade_julia", {})
        for flag in ("necessaria","rosto","rosto_1","corpo","mao"):
            require(type(identity.get(flag)) is bool, f"identidade_julia.{flag} deve ser booleano.")
        required_types = {"rosto":"identidade_rosto","rosto_1":"identidade_rosto","corpo":"identidade_corpo","mao":"identidade_mao"}
        for flag, typ in required_types.items():
            if identity[flag]:
                require(identity["necessaria"], "Referências pessoais requerem identidade necessária.")
                matching = [r for r in refs if r["tipo"] == typ]
                require(bool(matching), f"Referência {flag} exigida mas não anexada.")
        if identity["rosto"] and identity["rosto_1"]:
            require(len([r for r in refs if r["tipo"]=="identidade_rosto"]) >= 2, "Duas referências faciais exigidas.")
        if identity["necessaria"]:
            require((Path(package)/"identidade.txt").is_file(), "Identidade textual ausente.")
        mode = p.get("origem_clipe", {}).get("modo")
        require(mode in {"gerar","adaptar","reutilizar"}, "Origem inválida.")
        if norm(source["entrada"]["uso_material"]) == "reutilizar":
            require(mode == "reutilizar", "Reutilização solicitada não pode ser substituída silenciosamente.")
        if not pipeline["gerar_imagem"]:
            require(not entry.get("prompt_imagem"), "Não produzir prompt quando imagem não será gerada.")
            existing = p.get("frame_existente_ref_id") or p.get("ativo_existente_ref_id")
            require(existing in allowed, "Reutilização precisa identificar o ativo/frame existente.")
        else:
            require(pipeline.get("metodo_imagem") == "i2i", "Esta primeira etapa exporta i2i; extrair_frame/storyboard devem voltar como pendência.")
            require(bool(refs), "Imagem precisa de referências.")
            if manifest["versao"] in {"2.3-insumos", "2.4-insumos"}:
                require(mode == "adaptar", "Nova imagem exige modo=adaptar.")
                require(entry.get("incluir_bloco_identidade") is False, "Usar incluir_bloco_identidade=false.")
                edit = p.get("edicao_imagem")
                require(isinstance(edit, dict), "edicao_imagem obrigatória.")
                require(edit.get("base_ref_id") == refs[0]["ref_id"], "Imagem-base deve ser a Referência 1.")
                require(not refs[0]["tipo"].startswith("identidade_"), "Identidade não é base de cena.")
                declared_base = norm(source["entrada"]["tipo_referencia"]) == "base_edicao"
                if declared_base:
                    source_base_id = source["referencias"].get(source["entrada"]["arquivo"])
                    require(source_base_id == refs[0]["ref_id"], "A referência marcada base_edicao na planilha deve ser a Referência 1 e a base_ref_id.")
                    require(refs[0]["tipo"] == "base_edicao", "A referência marcada base_edicao deve manter esse tipo no plano.")
                for field in ("preservar", "alterar"):
                    require(isinstance(edit.get(field), list) and bool(edit[field]), f"edicao_imagem.{field} exige lista não vazia.")
                    for value in edit[field]:
                        text_field(value, "edicao_imagem." + field)
                require(isinstance(entry.get("prompt_imagem"), str) and entry["prompt_imagem"].startswith("Edite a Referência 1 como imagem-base. Não recrie a cena do zero."), "Prompt deve iniciar com edição da Referência 1.")

            require(all(inside(package, r["arquivo"]).suffix.lower() in IMAGE_EXT for r in refs), "i2i aceita somente imagens; extrair frame antes.")
            require(not pipeline["usar_ativo_existente"], "Geração de imagem e ativo final reutilizado são incompatíveis.")
            if pipeline["gerar_video"]:
                require(pipeline["aprovacao_necessaria"], "Frame novo para vídeo exige aprovação.")
            for name in ("estado_inicial", "estado_final"):
                text_field(p.get(name), name)
            for name in ("ambiente","origem_ambiente","apoio","luz","camera","enquadramento","roupa","maos"):
                text_field(p.get("cena", {}).get(name), "cena."+name)
            require(p["cena"]["origem_ambiente"] in {"referencia","inferido"}, "Origem do ambiente inválida.")
            text_field(p.get("acao", {}).get("descricao"), "acao.descricao")
            text_field(entry.get("prompt_imagem"), "prompt_imagem")
            require("9:16" in entry["prompt_imagem"], "Prompt de imagem deve explicitar 9:16.")
        if pipeline["gerar_video"]:
            require(pipeline["aprovacao_necessaria"], "Toda geracao nova de video exige aprovacao humana explicita.")
            require(pipeline.get("metodo_video") in {"i2v","r2v"}, "Vídeo requer método.")
            timeline = p.get("cronograma", [])
            require(len(timeline) == 4, "Cronograma requer quatro intervalos.")
            for step, limits in zip(timeline, [(0,1.2),(1.2,3),(3,6.5),(6.5,8)]):
                require((step.get("inicio_s"),step.get("fim_s")) == limits, "Cronograma deve cobrir oito segundos.")
                text_field(step.get("acao"), "cronograma.acao")
            audio = p.get("audio", {})
            require(type(audio.get("ativo")) is bool, "audio.ativo obrigatório.")
            speech = audio.get("fala_exata", "")
            require(isinstance(speech, str), "Fala deve ser texto.")
            audio_input = str(source["entrada"].get("fala_audio", "") or "").strip()
            silence_requested = norm(audio_input) == "sem_audio"
            if manifest["versao"] == "2.4-insumos":
                if silence_requested:
                    require(not audio["ativo"] and not speech, "sem_audio exige áudio inativo e fala vazia.")
                else:
                    require(audio["ativo"], "Pacote 2.4 exige fala da Julia; use sem_audio para desativar.")
                    if audio_input:
                        require(speech == audio_input, "A fala_audio humana deve ser preservada exatamente.")
            if audio["ativo"]:
                text_field(speech, "fala_exata")
                start, end = audio.get("inicio_s"), audio.get("fim_maximo_s")
                require(type(start) in {int,float} and type(end) in {int,float} and 0 <= start < end <= 6.8, "Tempo da fala inválido.")
                if role == "abertura":
                    require(speech.startswith("Bora...") and start == 0, "Abertura exige Bora... em 0s.")
                else:
                    require(not re.match(r"^bora\b", speech, re.I), "Bora somente na abertura.")
            else:
                if manifest["versao"] == "2.4-insumos":
                    require(silence_requested and not speech, "Áudio inativo exige fala_audio=sem_audio.")
                else:
                    require(not speech and role == "principal", "Abertura/CTA novos precisam de fala.")
        video_prompt = entry.get("prompt_video")
        if pipeline["gerar_video"] and (complete or video_prompt is not None):
            text_field(video_prompt, "prompt_video")
            require("9:16" in video_prompt, "Prompt de vídeo deve explicitar 9:16.")
            require(p.get("arquivos_saida", {}).get("prompt_video") == "prompt_video.txt", "Saída de vídeo deve ser prompt_video.txt.")
            if p["audio"]["ativo"]:
                require(p["audio"]["fala_exata"] in video_prompt, "Prompt de vídeo deve conter a fala exata do plano.")
        elif not pipeline["gerar_video"]:
            require(video_prompt is None and p.get("arquivos_saida", {}).get("prompt_video") is None, "Sem geração de vídeo, prompt_video deve ser null.")
        plans[cid] = entry
    require(set(plans) == set(expected), "Resposta deve representar todos os clipes da produção.")
    require(prod.get("total_clipes") == len(expected), "total_clipes divergente.")
    summaries = prod.get("clipes", [])
    require([s.get("id_clipe") for s in summaries] == list(expected), "Resumo da produção deve conter os clipes em ordem.")
    for summary in summaries:
        p = plans[summary["id_clipe"]]["plano"]
        if p["status"] == "pronto":
            require(summary.get("ordem") == p["ordem"] and summary.get("fluxo") == p["classificacao"]["fluxo"]
                    and summary.get("papel") == p["papel_na_producao"], "Resumo e plano individual divergem.")
    return plans

def import_response(root, package, response_file, update_excel=False, output_dir=None):
    root, package = Path(root), Path(package).resolve()
    output_dir = Path(output_dir).resolve() if output_dir else root / "preparados"
    manifest = read_json(package / "manifesto.json")
    # Integridade dos anexos e contratos da rodada.
    for ref in manifest["inventario"].values():
        require(digest(inside(package, ref["arquivo"])) == ref["sha256"], "Anexo alterado após preparação.")
    for key, filename in (("classificador","CLASSIFICADOR_UNIVERSAL.txt"),("contrato","CONTRATO_INSUMOS.md")):
        require(digest(package/filename) == manifest["contratos"][key], "Contrato do pacote alterado.")
    if manifest["identidade_sha256"]:
        require(digest(package/"identidade.txt") == manifest["identidade_sha256"], "Identidade do pacote alterada.")
    wb = Workbook(manifest["planilha"])
    current = {r["_linha"]: r for r in wb.records()}
    include_audio = manifest.get("versao") == "2.4-insumos"
    for item in manifest["clipes"]:
        require(
            item["linha"] in current
            and human_snapshot(current[item["linha"]], include_audio=include_audio)
            == human_snapshot(item["entrada"], include_audio=include_audio),
            "Campos humanos mudaram; prepare um novo pacote.",
        )
    response = read_json(response_file)
    plans = validate_response(response, manifest, package)
    rev = signature(response)
    dest = output_dir / "flow" / manifest["producao_id"] / rev[:16]
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = Path(tempfile.mkdtemp(prefix=".insumos-", dir=dest.parent))
        try:
            write_json(temp/"plano_producao.json", response["plano_producao"])
            write_json(temp/"resposta_ia.json", response)
            for cid, entry in plans.items():
                plan = entry["plano"]
                folder = temp / cid
                folder.mkdir()
                write_json(folder/"plano_clipe.json", plan)
                if plan["status"] == "pendente":
                    (folder/"PENDENCIA.txt").write_text(plan["motivo"], encoding="utf-8")
                    continue
                refs_out = []
                for index, ref in enumerate(plan["referencias"], 1):
                    src = inside(package, ref["arquivo"])
                    relative = f"referencias/{index:02d}_{src.name}"
                    (folder/"referencias").mkdir(exist_ok=True)
                    shutil.copy2(src, folder/relative)
                    refs_out.append({**ref, "ordem":index,"arquivo":relative,"sha256":digest(src)})
                if plan["pipeline"]["gerar_imagem"]:
                    prompt = entry["prompt_imagem"].strip()
                    if plan["identidade_julia"]["necessaria"]:
                        shutil.copy2(package/"identidade.txt",folder/"identidade.txt")
                        if entry.get("incluir_bloco_identidade", True):
                            prompt = (package/"identidade.txt").read_text(encoding="utf-8") + "\n\n" + prompt
                    prompt += "\n\nORDEM EXATA DOS ANEXOS:\n" + "\n".join(
                        f"Referência {r['ordem']} = {r['arquivo']}; papel: {r['tipo']}; preservar: {r['uso']}" for r in refs_out)
                    (folder/"prompt_imagem.txt").write_text(prompt+"\n",encoding="utf-8")
                if entry.get("prompt_video"):
                    (folder/"prompt_video.txt").write_text(entry["prompt_video"].strip()+"\n", encoding="utf-8")
                write_json(folder/"insumos_video.json", {
                    "prompt": "prompt_video.txt" if entry.get("prompt_video") else None,
                    "gerar_video": plan["pipeline"]["gerar_video"],
                    "metodo": plan["pipeline"]["metodo_video"],
                    "aspecto": plan["pipeline"]["aspecto"],
                    "duracao_s": plan["pipeline"]["duracao_video_s"],
                    "aprovacao_necessaria": plan["pipeline"]["aprovacao_necessaria"],
                    "status": "sem_geracao_video" if not plan["pipeline"]["gerar_video"] else ("aguardando_imagem_e_aprovacao" if plan["pipeline"]["gerar_imagem"] else "consultar_plano_e_aprovacao"),
                    "video_gerado": False,
                    "orientacao": "Registro da exportação, não autorização para gerar. Confira a imagem real e a aprovação atual na planilha antes de usar o prompt. Pacotes 2.1 podem não conter prompt de vídeo."
                })
                write_json(folder/"insumos_flow.json", {"status":"pronto_para_gerar_imagem" if plan["pipeline"]["gerar_imagem"] else "sem_geracao_imagem",
                    "modelo_solicitado":"Nano Banana 2","aspecto":"9:16","metodo":plan["pipeline"]["metodo_imagem"],
                    "prompt":"prompt_imagem.txt" if plan["pipeline"]["gerar_imagem"] else None,"referencias":refs_out,
                    "edicao_imagem":plan.get("edicao_imagem"),"imagem_gerada":False,"aprovacao_imagem":"nao_realizada","pacote_sha256":manifest["pacote_sha256"]})
                (folder/"COMO_USAR.txt").write_text(
                    "Se status=pronto_para_gerar_imagem, cole prompt_imagem.txt no Flow e anexe SOMENTE referencias/, na ordem indicada em insumos_flow.json.\n"
                    "Selecione Nano Banana 2 e 9:16 na interface. Nenhuma geração foi executada por este programa.\n"
                    "plano_clipe.json contém as decisões; não anexar outros produtos nem arquivos históricos.\n"
                    "Se sem_geracao_imagem, consultar o plano; não regenerar o ativo.\n"
                    "VÍDEO: o classificador fornece prompt_video.txt quando há nova geração. Pacotes antigos podem não conter esse arquivo.\n"
                    "Salve a imagem gerada nesta pasta, mantendo sua extensão, e registre imagem_arquivo e imagem_status=gerada na planilha.\n"
                    "Revise a imagem e registre a decisão humana em aprovacao. Se exigida, somente aprovacao=aprovada permite seguir ao vídeo.\n"
                    "Para i2v, use a imagem aprovada como frame inicial e cole prompt_video.txt; para r2v, siga as referências do plano. Configure 9:16 e 8 segundos.\n"
                    "Se a imagem divergir do plano, corrija a imagem ou revise plano e prompts antes de seguir.\n"
                    "Salve o vídeo nesta pasta e registre seu caminho e resultado real na planilha. Esta ferramenta apenas prepara arquivos.\n",encoding="utf-8")
            os.replace(temp, dest)
        finally:
            if temp.exists():
                shutil.rmtree(temp)
    excel_error = None
    if update_excel:
        try:
            for item in manifest["clipes"]:
                cid = item["id_clipe"]; p = plans[cid]["plano"]; row = item["linha"]
                plan_path = dest/cid/"plano_clipe.json"
                fields = {"plano_arquivo":str(plan_path),"atualizado_em":now()}
                if manifest.get("versao") != "2.4-insumos":
                    fields["fala_audio"] = p.get("audio", {}).get("fala_exata", "") if p.get("audio", {}).get("ativo") else ""
                if not same_plan_revision(current[row], plan_path):
                    fields["aprovacao"] = ""
                carousel = p.get("carrossel") if isinstance(p.get("carrossel"), dict) else {}
                fields.update(texto_carrossel=carousel.get("texto", ""),
                              subtexto_carrossel=carousel.get("subtexto", ""),
                              carrossel_status=CarouselStatus.PENDING if carousel.get("ativo") else CarouselStatus.NOT_REQUESTED,
                              carrossel_arquivo="")
                if p["status"] == "pendente":
                    fields.update(status=PipelineStatus.PENDING,erro=p["motivo"])
                else:
                    validate_revision_migration(current[row])
                    fields.update(status=PipelineStatus.CLASSIFIED,classificacao=p["classificacao"].get("categoria") or "",
                                  fluxo=p["classificacao"].get("fluxo") or "",erro="",
                                  imagem_status=ImageStatus.PENDING if p["pipeline"]["gerar_imagem"] else ImageStatus.NOT_REQUIRED)
                for name,value in fields.items():
                    wb.set(row,name,value)
            wb.save()
        except (Invalid, OSError) as exc:
            excel_error = str(exc)
    result = {"destino":str(dest),"clipes":len(plans),"excel_atualizado":update_excel and not excel_error,"erro_excel":excel_error}
    write_json(output_dir/"ultima_importacao.json",result)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz",type=Path,default=ROOT)
    parser.add_argument("--saida",type=Path)
    sub = parser.add_subparsers(dest="command",required=True)
    for name in ("preparar","corrigir-planilha"):
        p=sub.add_parser(name); p.add_argument("--planilha",type=Path)
        if name=="preparar": p.add_argument("--fontes",nargs="+",type=Path)
    p=sub.add_parser("importar")
    p.add_argument("--pacote",required=True,type=Path)
    p.add_argument("--resposta",required=True,type=Path)
    p.add_argument("--atualizar-excel",action="store_true")
    args=parser.parse_args()
    try:
        config=load_config(args.raiz)
        output_dir=(args.saida or config.output_dir).resolve()
        spreadsheet=config.spreadsheet
        if args.command=="corrigir-planilha":
            result=update_spreadsheet_structure(args.planilha or spreadsheet)
        elif args.command=="preparar":
            roots=args.fontes or [args.raiz/"entradas",args.raiz/"referencia_gflow_original/Fila Flow"]
            result=prepare(args.raiz,args.planilha or spreadsheet,roots,output_dir=output_dir)
        else:
            result=import_response(
                args.raiz,args.pacote,args.resposta,args.atualizar_excel,output_dir=output_dir
            )
        print(json.dumps(result,ensure_ascii=True,indent=2))
        return 2 if result.get("pendencias") or result.get("erro_excel") else 0
    except (Invalid,OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as exc:
        print(json.dumps({"erro":str(exc)},ensure_ascii=True))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
