import io
import unittest
import xml.etree.ElementTree as ET
from scripts.preparar_insumos import serialize_sheet

class NamespaceTest(unittest.TestCase):
    def check(self, source):
        result = serialize_sheet(ET.fromstring(source), source)
        ns = dict(item for event, item in ET.iterparse(io.BytesIO(result), events=("start-ns",)))
        root = ET.fromstring(result)
        for prefix in root.attrib["{http://schemas.openxmlformats.org/markup-compatibility/2006}Ignorable"].split():
            self.assertIn(prefix, ns)
        return result

    def test_excel_declarations_survive_repeated_save(self):
        source = b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:custom="urn:custom" mc:Ignorable="custom"><sheetData/></worksheet>'
        self.check(self.check(source))

    def test_recover_old_writer_missing_declarations(self):
        self.check(b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" mc:Ignorable="x14ac xr xr2 xr3"><sheetData/></worksheet>')
