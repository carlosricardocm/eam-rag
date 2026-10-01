# Genera la documentación en PDF del RAG con Memorias Asociativas Entrópicas.
import datetime
import os

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

# Carpeta PROYECTO (padre de eam_rag): ahí están rag_modificado.png y el PDF de salida.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'RAG_EAM_documentacion.pdf')
FONTS = r'C:\Windows\Fonts'

pdfmetrics.registerFont(TTFont('Arial', os.path.join(FONTS, 'arial.ttf')))
pdfmetrics.registerFont(TTFont('Arial-Bold', os.path.join(FONTS, 'arialbd.ttf')))
pdfmetrics.registerFont(TTFont('Arial-Italic', os.path.join(FONTS, 'ariali.ttf')))
pdfmetrics.registerFont(TTFont('Arial-BoldItalic', os.path.join(FONTS, 'arialbi.ttf')))
pdfmetrics.registerFont(TTFont('Consolas', os.path.join(FONTS, 'consola.ttf')))
pdfmetrics.registerFont(TTFont('Consolas-Bold', os.path.join(FONTS, 'consolab.ttf')))
from reportlab.pdfbase.pdfmetrics import registerFontFamily  # noqa: E402
registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial-Italic', boldItalic='Arial-BoldItalic')
registerFontFamily('Consolas', normal='Consolas', bold='Consolas-Bold', italic='Consolas', boldItalic='Consolas-Bold')

INK = colors.HexColor('#1f2933')
ACCENT = colors.HexColor('#1d4e89')
MUTED = colors.HexColor('#52606d')
RULE = colors.HexColor('#cbd2d9')
CODEBG = colors.HexColor('#f3f5f7')
HILITE = colors.HexColor('#e3ecf7')

base = ParagraphStyle('base', fontName='Arial', fontSize=10.5, leading=15, textColor=INK,
                      alignment=TA_JUSTIFY, spaceAfter=6)
S = {
    'body': base,
    'h1': ParagraphStyle('h1', parent=base, fontName='Arial-Bold', fontSize=17, leading=22,
                         textColor=ACCENT, spaceBefore=6, spaceAfter=10, alignment=0),
    'h2': ParagraphStyle('h2', parent=base, fontName='Arial-Bold', fontSize=13, leading=17,
                         textColor=ACCENT, spaceBefore=10, spaceAfter=6, alignment=0),
    'h3': ParagraphStyle('h3', parent=base, fontName='Arial-Bold', fontSize=11, leading=15,
                         textColor=INK, spaceBefore=6, spaceAfter=4, alignment=0),
    'bullet': ParagraphStyle('bullet', parent=base, leftIndent=16, bulletIndent=4, spaceAfter=3),
    'code': ParagraphStyle('code', fontName='Consolas', fontSize=8.6, leading=11.2, textColor=INK,
                           backColor=CODEBG, borderPadding=(6, 6, 6, 6), leftIndent=6,
                           rightIndent=6, spaceBefore=4, spaceAfter=10),
    'formula': ParagraphStyle('formula', parent=base, fontName='Arial', fontSize=10.5,
                              alignment=TA_CENTER, backColor=HILITE, borderPadding=(6, 6, 6, 6),
                              leftIndent=30, rightIndent=30, spaceBefore=4, spaceAfter=10),
    'caption': ParagraphStyle('caption', parent=base, fontName='Arial-Italic', fontSize=9,
                              leading=12, textColor=MUTED, alignment=TA_CENTER, spaceAfter=10),
    'cell': ParagraphStyle('cell', parent=base, fontSize=9, leading=12, alignment=0, spaceAfter=0),
    'cellb': ParagraphStyle('cellb', parent=base, fontName='Arial-Bold', fontSize=9, leading=12,
                            alignment=0, spaceAfter=0, textColor=colors.white),
    'note': ParagraphStyle('note', parent=base, fontSize=9.5, leading=13.5, backColor=HILITE,
                           borderPadding=(6, 8, 6, 8), leftIndent=8, rightIndent=8,
                           spaceBefore=4, spaceAfter=10),
}


class Doc(SimpleDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ('h1', 'h2'):
            level = 0 if f.style.name == 'h1' else 1
            text = f.getPlainText()
            key = f'h{id(f)}'
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
            self.notify('TOCEntry', (level, text, self.page, key))


def P(t, s='body'):
    return Paragraph(t, S[s])


def B(items):
    return [Paragraph(i, S['bullet'], bulletText='•') for i in items]


def code(t):
    return Preformatted(t.strip('\n'), S['code'])


def F(t):
    return Paragraph(t, S['formula'])


def table(rows, widths, header=True, hl_rows=(), tight=False):
    data = [[Paragraph(str(c), S['cellb'] if (header and i == 0) else S['cell']) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [('GRID', (0, 0), (-1, -1), 0.4, RULE),
          ('VALIGN', (0, 0), (-1, -1), 'TOP'),
          ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
          ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5)]
    if header:
        st.append(('BACKGROUND', (0, 0), (-1, 0), ACCENT))
    for r in hl_rows:
        st.append(('BACKGROUND', (0, r), (-1, r), HILITE))
    if tight:
        st += [('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2)]
    t.setStyle(TableStyle(st))
    return t


def arrow(d, x1, y1, x2, y2, color=MUTED):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.2))
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    L, W = 7, 3.5
    p1 = (x2 - L * math.cos(a) + W * math.sin(a), y2 - L * math.sin(a) - W * math.cos(a))
    p2 = (x2 - L * math.cos(a) - W * math.sin(a), y2 - L * math.sin(a) + W * math.cos(a))
    d.add(Polygon([x2, y2, p1[0], p1[1], p2[0], p2[1]], fillColor=color, strokeColor=color))


def box(d, x, y, w, h, lines, fill=colors.white, bold_first=True, stroke=ACCENT):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill, strokeColor=stroke, strokeWidth=1))
    n = len(lines)
    top = y + h / 2 + (n - 1) * 6
    for i, t in enumerate(lines):
        d.add(String(x + w / 2, top - i * 12 - 3, t, textAnchor='middle',
                     fontName='Arial-Bold' if (i == 0 and bold_first) else 'Arial',
                     fontSize=8.5 if i == 0 else 7.5, fillColor=INK))


def architecture():
    W = 482
    d = Drawing(W, 270)
    A, B, C, D, E = 0, 98, 192, 290, 400
    # fila superior: consulta
    box(d, A, 205, 80, 42, ['Consulta', 'del usuario'], fill=HILITE)
    box(d, B, 205, 76, 42, ['SONAR', 'spa_Latn, 1024-d'])
    box(d, C, 205, 80, 42, ['Quantizer', 'cue: 1024 enteros', 'en 0..15'])
    arrow(d, A + 80, 226, B, 226)
    arrow(d, B + 76, 226, C, 226)
    # fila inferior: base de conocimiento
    box(d, A, 40, 80, 56, ['Knowledge Base', 'datasets_csv', '693 obras', '11,185 fragm.'], fill=HILITE)
    box(d, B, 47, 76, 42, ['SONAR', '(mismos pesos)'])
    box(d, C, 47, 80, 42, ['Quantizer', 'cuantiles', 'por rasgo'])
    arrow(d, A + 80, 68, B, 68)
    arrow(d, B + 76, 68, C, 68)
    # EAM
    amber = colors.HexColor('#b7791f')
    d.add(Rect(D, 30, 92, 150, rx=6, ry=6, fillColor=colors.HexColor('#fff7e6'),
               strokeColor=amber, strokeWidth=1.2))
    for i, t in enumerate(['Memorias', 'Asociativas', 'Entrópicas']):
        d.add(String(D + 46, 166 - i * 10, t, textAnchor='middle', fontName='Arial-Bold', fontSize=8))
    for i in range(4):
        d.add(Rect(D + 12 + i * 5, 92 - i * 5, 52, 32, fillColor=colors.white,
                   strokeColor=amber, strokeWidth=0.8))
    d.add(String(D + 53, 83, 'R[k]: 16×1024', textAnchor='middle', fontName='Arial', fontSize=7))
    d.add(String(D + 46, 50, 'una memoria', textAnchor='middle', fontName='Arial', fontSize=7))
    d.add(String(D + 46, 40, 'por obra (K=693)', textAnchor='middle', fontName='Arial', fontSize=7))
    arrow(d, C + 80, 68, D, 80)
    d.add(String(C + 70, 84, 'register', fontName='Arial-Italic', fontSize=7, fillColor=MUTED))
    arrow(d, C + 80, 212, D + 14, 180)
    d.add(String(C + 86, 190, 'cue', fontName='Arial-Italic', fontSize=7, fillColor=MUTED))
    # retrieval, augmentation, generación
    box(d, D, 205, 92, 42, ['RETRIEVAL', '1) top-5 obras', '2) top-8 fragmentos'])
    arrow(d, D + 46, 180, D + 46, 205)
    box(d, E, 165, 82, 82, ['AUGMENTATION', 'pregunta +', 'fragmentos;', '"si no está,', 'di No lo sé"'], fill=HILITE)
    arrow(d, D + 92, 226, E, 226)
    box(d, E, 40, 82, 56, ['OpenAI', 'gpt-5.5', '→ respuesta'])
    arrow(d, E + 41, 165, E + 41, 96)
    # la consulta también llega directo a augmentation (flecha superior del diagrama)
    d.add(Line(A + 40, 247, A + 40, 260, strokeColor=MUTED, strokeWidth=1))
    d.add(Line(A + 40, 260, E + 41, 260, strokeColor=MUTED, strokeWidth=1))
    arrow(d, E + 41, 260, E + 41, 247)
    return d


def on_page(canv, doc):
    canv.saveState()
    if doc.page > 1:
        canv.setFont('Arial', 8)
        canv.setFillColor(MUTED)
        canv.drawString(2.2 * cm, 1.3 * cm, 'RAG con Memorias Asociativas Entrópicas · Documentación técnica')
        canv.drawRightString(letter[0] - 2.2 * cm, 1.3 * cm, f'{doc.page}')
        canv.setStrokeColor(RULE)
        canv.line(2.2 * cm, 1.6 * cm, letter[0] - 2.2 * cm, 1.6 * cm)
    canv.restoreState()


story = []
FW = letter[0] - 4.4 * cm  # ancho útil

# ------------------------------------------------------------------ portada
story += [Spacer(1, 4.5 * cm),
          Paragraph('RAG con Memorias Asociativas Entrópicas',
                    ParagraphStyle('t', parent=S['h1'], fontSize=26, leading=32, alignment=TA_CENTER)),
          Spacer(1, 0.4 * cm),
          Paragraph('Recuperación aumentada por generación sobre un corpus de cuentistas '
                    'latinoamericanos, sustituyendo la base de datos vectorial por memorias '
                    'asociativas entrópicas (EAM) y embeddings SONAR',
                    ParagraphStyle('st', parent=base, fontSize=12.5, leading=18, alignment=TA_CENTER,
                                   textColor=MUTED)),
          Spacer(1, 1.2 * cm),
          Paragraph('Documentación técnica y manual de uso',
                    ParagraphStyle('st2', parent=base, fontName='Arial-Bold', fontSize=12,
                                   alignment=TA_CENTER)),
          Spacer(1, 0.3 * cm),
          Paragraph('Proyecto MAE2026 · IIMAS, UNAM',
                    ParagraphStyle('st3', parent=base, alignment=TA_CENTER, textColor=MUTED)),
          Paragraph(datetime.date(2026, 9, 28).strftime('%d/%m/%Y'),
                    ParagraphStyle('st4', parent=base, alignment=TA_CENTER, textColor=MUTED)),
          PageBreak()]

# ------------------------------------------------------------------ índice
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle('toc1', fontName='Arial-Bold', fontSize=10.5, leading=16, leftIndent=0),
    ParagraphStyle('toc2', fontName='Arial', fontSize=9.5, leading=13, leftIndent=16),
]
story += [Paragraph('Contenido', ParagraphStyle('tochead', parent=S['h1'])), toc, PageBreak()]

# ------------------------------------------------------------------ 1. resumen
story += [P('1. Resumen', 'h1'),
          P('Este documento describe el diseño, la implementación, la evaluación y la forma de uso '
            'de un sistema de <i>Retrieval-Augmented Generation</i> (RAG) en el que la base de datos '
            'vectorial tradicional se sustituye por <b>Memorias Asociativas Entrópicas</b> (EAM, '
            '<i>Entropic Associative Memories</i>), tomando como base el código del repositorio '
            '<font face="Consolas">dimex</font> (Pineda, Fuentes y Morales). El conocimiento es un '
            'corpus de 58 autores latinoamericanos con sus obras (cuentos, minicuentos, ensayos), y '
            'tanto las obras como las consultas se codifican con <b>SONAR</b>, el codificador de '
            'oraciones multilingüe de Meta.'),
          P('Cada obra tiene su propia memoria asociativa. Los embeddings de sus fragmentos se '
            'cuantizan y se <i>registran</i> en ella. Ante una pregunta, el embedding cuantizado de la '
            'pregunta actúa como <i>cue</i>: todas las memorias lo evalúan en paralelo, se eligen las '
            'obras mejor puntuadas y, dentro de ellas, los fragmentos más afines. Esos fragmentos se '
            'añaden a la pregunta (<i>augmentation</i>) y un modelo de lenguaje (GPT-5.5 de OpenAI) redacta la '
            'respuesta o responde “No lo sé”.'),
          P('Resultados principales:', 'h3')]
story += B([
    'Con preguntas reales sobre cuentos del corpus, la EAM identifica la obra correcta entre las '
    '5 recuperadas (configuración por defecto) en el <b>67 %</b> de los casos, frente al <b>62 %</b> '
    'de una base vectorial con similitud coseno sobre los mismos embeddings. Con solo 3 obras la '
    'ventaja es mayor (67 % frente a 48 %): la EAM acierta pronto y el coseno necesita más candidatos.',
    'El criterio de selección original de dimex (<i>entropy/weight</i>) no funciona en este dominio '
    '(0 %) porque favorece memorias con un solo registro; se propone y justifica un criterio de '
    'log-verosimilitud suave que generaliza los <i>mismatches</i> de la EAM.',
    'Para localizar una oración literal del texto, la base vectorial es mejor (72 % frente a 36 %): '
    'la memoria abstrae la obra completa y pierde el detalle del fragmento.',
    'La EAM puede rechazar consultas que no reconoce: con un umbral relativo rechaza 9 de 10 '
    'preguntas ajenas al corpus, a costa de rechazar también el 19 % de las válidas.',
    'El tamaño de la memoria casi no influye: con 4, 8 o 16 niveles de cuantización (filas) los '
    'resultados son prácticamente iguales, y m = 4 ocupa la cuarta parte del espacio.',
    'El port vectorizado de la memoria reproduce exactamente al original de dimex (prueba de '
    'fidelidad automática).',
])

# ------------------------------------------------------------------ 2. introducción
story += [CondPageBreak(7 * cm), P('2. Introducción y objetivo', 'h1'),
          P('2.1 RAG en su forma estándar', 'h2'),
          P('Un sistema RAG (Lewis et al., 2021; Gao et al., 2024) combina un modelo de lenguaje con '
            'un mecanismo de recuperación de documentos. En su forma habitual:'),
          ]
story += B(['Los documentos de la base de conocimiento se dividen en fragmentos y cada uno se '
            'convierte en un vector (embedding) con un modelo de lenguaje.',
            'Los vectores se guardan en una <i>vector database</i>.',
            'La pregunta del usuario se convierte en vector con el mismo modelo y se recuperan los '
            'fragmentos con menor distancia (o mayor similitud coseno).',
            'La pregunta y los fragmentos recuperados se combinan en un prompt (<i>augmentation</i>) '
            'con la instrucción de responder basándose en ellos y decir “no lo sé” si la respuesta '
            'no está.'])
story += [P('2.2 La modificación propuesta', 'h2'),
          P('El diagrama del proyecto (Figura 1) mantiene ese flujo pero introduce dos cambios: '
            '(1) tanto la consulta como la base de conocimiento se codifican con <b>SONAR</b>, y '
            '(2) <b>en vez de una base de datos vectorial se utilizan memorias asociativas '
            'entrópicas</b>. El ejemplo del diagrama es la pregunta “¿Qué enfermedad sufre Dahlmann '
            'tras golpearse la frente?” sobre el cuento <i>El sur</i> de Jorge Luis Borges (la '
            'respuesta es una septicemia).')]
img = Image(os.path.join(ROOT, 'rag_modificado.png'))
ratio = img.imageHeight / img.imageWidth
img.drawWidth = FW * 0.82
img.drawHeight = FW * 0.82 * ratio
story += [img, P('Figura 1. Diagrama del RAG modificado (rag_modificado.png), adaptado de Gao et al. '
                 '(2024) y Lewis et al. (2021).', 'caption'),
          KeepTogether([P('2.3 Objetivo', 'h2'),
          P('Construir un sistema funcional que implemente el diagrama sobre el corpus '
            '<font face="Consolas">datasets_csv</font>, reutilizando el modelo de memoria de '
            '<font face="Consolas">dimex/associative.py</font>, y medir si la recuperación con EAM '
            'es competitiva frente a la recuperación vectorial convencional.')])]

# ------------------------------------------------------------------ 3. fundamentos EAM
story += [CondPageBreak(7 * cm), P('3. Fundamentos: Memorias Asociativas Entrópicas', 'h1'),
          P('Las EAM (Pineda, Fuentes y Morales, 2021; Pineda y Morales, 2022) representan la memoria '
            'como una <b>relación</b> entre un dominio de <i>n</i> rasgos y un rango de <i>m</i> valores. '
            'Se implementa como una tabla R de <i>m</i> filas por <i>n</i> columnas: la celda '
            'R[i, j] cuenta cuántas veces se ha registrado el valor <i>i</i> en el rasgo <i>j</i>. '
            'Una fila adicional (la <i>m</i>+1) representa el valor indefinido, para funciones '
            'parciales.'),
          P('3.1 Operaciones', 'h2')]
story += [table([
    ['Operación', 'Definición (como en dimex)'],
    ['Registro (abstracción)', 'Un vector v con valores en {0, …, m−1}<super>n</super> se convierte en la relación r<sub>io</sub> '
     '(una marca por columna, en la fila v<sub>j</sub>) y se suma: R ← R + r<sub>io</sub>, '
     'saturando en 1023.'],
    ['Entropía', 'Para cada columna, p<sub>i</sub> = R[i,j] / Σ<sub>i</sub> R[i,j] y '
     'H<sub>j</sub> = −Σ<sub>i</sub> p<sub>i</sub> log<sub>2</sub> p<sub>i</sub>. La entropía de la '
     'memoria es la media de las H<sub>j</sub>. Mide qué tan “difusa” es la memoria.'],
    ['Relación iota', 'Versión de R donde se anulan las celdas por debajo de '
     'ι · (media de las celdas no nulas de la columna). Con ι = 0, es R.'],
    ['Mismatches', 'Número de rasgos j del cue v tales que la celda R<sub>ι</sub>[v<sub>j</sub>, j] '
     'está vacía: el cue “sale” de lo que la memoria contiene.'],
    ['Peso (weight)', 'w = media<sub>j</sub> R[v<sub>j</sub>, j] / max(R).'],
    ['Reconocimiento', 'La memoria acepta el cue si mismatches ≤ tolerance y '
     'w ≥ κ · (media de la memoria).'],
    ['Recuerdo (recall)', 'λ-reducción: para cada rasgo se muestrea un valor de la columna, '
     'ponderada por una gaussiana centrada en el valor del cue con desviación σ·m.'],
    ['Sistema de memorias', 'Con varias memorias (una por clase), se elige la que reconoce el cue '
     'con menor penalización entropy / weight.'],
], [3.6 * cm, FW - 3.6 * cm])]
story += [Spacer(1, 6), P('3.2 Parámetros', 'h2'),
          table([
              ['Parámetro', 'Significado', 'Valor usado'],
              ['n', 'Tamaño del dominio (número de rasgos). Dimensión de SONAR.', '1024'],
              ['m', 'Tamaño del rango (niveles de cuantización).', '16'],
              ['tolerance', 'Mismatches permitidos para reconocer un cue (en este sistema se expresa '
               'como fracción de n).', '1.0 (sin filtro)'],
              ['σ (sigma)', 'Desviación de la gaussiana, como fracción de m.', '0.3'],
              ['ι (iota)', 'Moderación de la relación.', '0'],
              ['κ (kappa)', 'Peso mínimo relativo a la media para reconocer.', '0'],
          ], [2.6 * cm, FW - 6.4 * cm, 3.8 * cm])]

# ------------------------------------------------------------------ 4. arquitectura
story += [CondPageBreak(7 * cm), KeepTogether([P('4. Arquitectura del sistema', 'h1'),
          P('La Figura 2 muestra la arquitectura implementada. Hay dos flujos: el de indexación '
            '(fila inferior, se ejecuta una vez) y el de consulta (fila superior, en cada pregunta). '
            'Ambos usan el mismo codificador SONAR y el mismo cuantizador, de modo que el cue y lo '
            'registrado en las memorias viven en el mismo espacio discreto.'),
          architecture(),
          P('Figura 2. Arquitectura implementada. Las flechas de la fila inferior corresponden a la '
            'construcción del índice; las de la superior, a una consulta.', 'caption')]),
          P('4.1 Componentes', 'h2'),
          table([
              ['Módulo', 'Responsabilidad'],
              ['config.py', 'Carga el archivo .env con la API key y el modelo de OpenAI.'],
              ['corpus.py', 'Carga los CSV, limpia duplicados y metadatos, parte cada obra en fragmentos.'],
              ['sonar_encoder.py', 'Codifica textos en español a vectores de 1024 dimensiones.'],
              ['eam_store.py · Quantizer', 'Convierte vectores reales en enteros 0..m−1 por rasgo.'],
              ['associative.py · MemoryBank', 'Las K memorias asociativas y todas sus operaciones.'],
              ['eam_store.py · EAMStore', 'Construye el índice, recupera en dos niveles, guarda y carga.'],
              ['generator.py', 'Arma el prompt aumentado y llama al modelo de OpenAI.'],
              ['rag.py', 'Interfaz de línea de comandos del pipeline completo.'],
              ['build_index.py', 'Interfaz para construir el índice.'],
              ['evaluate.py', 'Compara la EAM con recuperación coseno.'],
          ], [4.6 * cm, FW - 4.6 * cm])]

# ------------------------------------------------------------------ 5. datos
story += [CondPageBreak(7 * cm), P('5. Base de conocimiento y preprocesamiento', 'h1'),
          P('5.1 El corpus', 'h2'),
          P('La carpeta <font face="Consolas">datasets_csv</font> contiene 58 archivos, uno por autor '
            '(<font face="Consolas">borges_full_texts.csv</font>, '
            '<font face="Consolas">cortazar_full_texts.csv</font>, …). Cada archivo tiene tres '
            'columnas: <font face="Consolas">link</font> (URL de origen en ciudadseva.com), '
            '<font face="Consolas">text_metadata</font> (diccionario con título, género y autor) y '
            '<font face="Consolas">text</font> (texto completo). En total hay 719 filas y unos 5.8 '
            'millones de caracteres; la mediana de longitud es de 4,500 caracteres y la obra más '
            'larga tiene 63,000.'),
          P('Autores con más obras: Borges (60), Cortázar (55), Baldomero Lillo (50), Arreola (45), '
            'Monterroso (45), Alfonso Reyes (37), Anderson Imbert (36) y Benedetti (33).'),
          P('5.2 Limpieza', 'h2')]
story += B(['<b>Duplicados:</b> 26 filas repiten un link ya visto (por ejemplo, <i>Biografía de '
            'Tadeo Isidoro Cruz</i> aparece dos veces). Se conserva la primera aparición: quedan '
            '<b>693 obras</b>.',
            '<b>Metadatos desplazados:</b> en algunas filas el campo <i>author</i> contiene el '
            'género (“[Cuento - Texto completo.]”) y el año quedó en <i>metadata</i>. En esos casos '
            'el género se recupera de ese campo y el autor se toma como el más frecuente del archivo.',
            '<b>Codificación:</b> los archivos están en UTF-8 y se leen así explícitamente.'])
story += [P('5.3 Fragmentación (chunking)', 'h2'),
          P('SONAR es un codificador de <i>oraciones</i>: con textos largos el promedio de sus '
            'representaciones pierde detalle. Por eso cada obra se divide en oraciones (con una '
            'expresión regular que reconoce puntos, signos de interrogación y exclamación, comillas '
            'y rayas de diálogo) y las oraciones consecutivas se agrupan hasta unas 120 palabras. '
            'La última oración de cada fragmento se repite al inicio del siguiente (traslape de 1) '
            'para no cortar ideas. Resultado: <b>11,185 fragmentos</b>, con 108 palabras en promedio.')]

# ------------------------------------------------------------------ 6. SONAR y cuantización
story += [P('6. Embeddings SONAR', 'h1'),
          P('SONAR (Duquenne, Schwenk y Sagot, 2023) produce representaciones de oraciones de 1024 '
            'dimensiones en un espacio compartido por 200 idiomas. El paquete oficial '
            '(<font face="Consolas">sonar-space</font>) depende de <font face="Consolas">fairseq2</font>, '
            'que no tiene soporte para Windows. Se usa en su lugar el port a HuggingFace '
            '<font face="Consolas">cointegrated/SONAR_200_text_encoder</font>, que carga los mismos '
            'pesos del codificador en la clase <font face="Consolas">M2M100Encoder</font> de '
            '<font face="Consolas">transformers</font>.')]
story += B(['Idioma de entrada: <font face="Consolas">spa_Latn</font>.',
            'Representación: promedio de los estados ocultos de la última capa, ponderado por la '
            'máscara de atención (<i>mean pooling</i>), igual que SONAR.',
            'Longitud máxima: 512 tokens (los fragmentos más largos se truncan).',
            'En GPU se usa precisión media (fp16). Los 11,185 fragmentos se codificaron en 73 '
            'segundos en una NVIDIA RTX 3070.',
            'Los embeddings se guardan en <font face="Consolas">store/embeddings.npy</font> junto con '
            'una huella SHA-1 de los fragmentos: si el corpus no cambia, no se vuelven a calcular.'])
story += [P('6.1 Cuantización', 'h2'),
          P('<b>Por qué hace falta.</b> Una memoria asociativa es una tabla de conteos: las filas son '
            'los valores posibles (0 a 15) y las columnas los rasgos (1024). Registrar un fragmento '
            'significa sumar 1 en la celda [valor, rasgo] de cada columna. SONAR, en cambio, entrega '
            'números reales como −0.0034, y no existe una fila “−0.0034”. Por eso cada número real se '
            'convierte en un nivel entero entre 0 y m−1 (con m = 16): eso es cuantizar. Hay dos métodos:')]
story += B(['<b>minmax</b>: se toman el mínimo y el máximo de todo el corpus (todos los rasgos a la '
            'vez) y ese rango se divide en 16 partes iguales, igual que '
            '<font face="Consolas">msize_features</font> en <font face="Consolas">dimex/eam.py</font>.',
            '<b>quantile</b> (por defecto): para cada rasgo por separado, los 11,185 fragmentos se '
            'ordenan de menor a mayor y se cortan en 16 grupos del mismo tamaño. Los 15 valores de '
            'corte se guardan y se reutilizan después para la consulta.'])
story += [P('Ejemplo real: el rasgo 0 de SONAR', 'h3'),
          P('En el corpus, el rasgo 0 va de −0.0326 a +0.0287 y casi todos sus valores están muy '
            'cerca de 0. El rango global de min-max, en cambio, va de −0.170 a +0.105, porque lo fijan '
            'los valores extremos de <i>otros</i> rasgos. La Tabla 1 muestra cuántos fragmentos caen '
            'en cada nivel con cada método:'),
          table([['Nivel'] + [str(i) for i in range(16)],
                 ['min-max', '0', '0', '0', '0', '0', '0', '0', '1', '564', '7680', '2920', '20', '0', '0', '0', '0'],
                 ['cuantiles'] + ['699'] * 15 + ['700']],
                [1.7 * cm] + [(FW - 1.7 * cm) / 16] * 16, hl_rows=(2,), tight=True),
          P('Tabla 1. Fragmentos por nivel en el rasgo 0 (de 11,185).', 'caption'),
          P('Con min-max, el 69 % de los fragmentos cae en el nivel 9 y 11 de los 16 niveles quedan '
            'vacíos: la columna casi no distingue un fragmento de otro. Con cuantiles, los cortes del '
            'rasgo 0 quedan en −0.0132, −0.0100, −0.0078, …, 0.0084, 0.0116, y cada nivel recibe '
            '699 fragmentos. Todos los niveles se usan por igual, así que cada columna aporta la máxima '
            'información posible (entropía máxima, log<sub>2</sub> 16 = 4 bits). Además, cada rasgo '
            'tiene sus propios cortes, adaptados a su rango real.'),
          P('Ejemplo real: el fragmento de la septicemia y la pregunta', 'h3'),
          P('La Tabla 2 muestra los primeros cinco rasgos del fragmento de <i>El sur</i> que contiene la '
            'respuesta, y de la pregunta “¿Qué enfermedad sufre Dahlmann tras golpearse la frente?”:'),
          table([
              ['', 'rasgo 0', 'rasgo 1', 'rasgo 2', 'rasgo 3', 'rasgo 4'],
              ['Fragmento: valor SONAR', '−0.0034', '0.0076', '0.0033', '0.0047', '0.0038'],
              ['→ nivel con cuantiles', '<b>6</b>', '<b>13</b>', '<b>10</b>', '<b>7</b>', '<b>10</b>'],
              ['→ nivel con min-max', '9', '10', '9', '10', '9'],
              ['Pregunta: valor SONAR', '0.0094', '0.0022', '0.0060', '−0.0040', '0.0130'],
              ['→ nivel (el cue)', '<b>14</b>', '<b>10</b>', '<b>12</b>', '<b>1</b>', '<b>15</b>'],
          ], [4.6 * cm] + [(FW - 4.6 * cm) / 5] * 5, hl_rows=(2, 5)),
          P('Tabla 2. Cuantización de un fragmento y de la pregunta (primeros 5 de 1024 rasgos).', 'caption'),
          KeepTogether([P('Con min-max, el fragmento queda casi entero en los niveles 9 y 10, igual que casi todos '
            'los demás fragmentos. Con cuantiles, sus valores se reparten entre 0 y 15 y pueden '
            'compararse. La pregunta se cuantiza con <b>los mismos cortes</b> aprendidos del corpus, '
            'de modo que el cue y lo registrado en las memorias usan la misma escala. El resultado '
            'de cuantizar la pregunta es el <b>cue</b>: una lista de 1024 enteros entre 0 y 15.', 'note')])]

# ------------------------------------------------------------------ 7. implementación EAM
story += [CondPageBreak(7 * cm), P('7. Implementación de las memorias', 'h1'),
          P('7.1 MemoryBank: port vectorizado', 'h2'),
          P('En dimex cada memoria es un objeto <font face="Consolas">AssociativeMemory</font> y sus '
            'operaciones recorren columnas con ciclos de Python. En el RAG hay 693 memorias y cada '
            'consulta debe evaluarse contra todas, así que se reescribió como '
            '<font face="Consolas">MemoryBank</font>: las K memorias se apilan en un tensor '
            'R[K, m+1, n] de enteros de 16 bits y todas las operaciones (entropía, medias, relación '
            'iota, mismatches, peso, reconocimiento, recuerdo) se calculan para las K memorias a la '
            'vez con operaciones de numpy. También se reemplazaron <font face="Consolas">np.int</font> '
            'y <font face="Consolas">np.bool</font>, eliminados de numpy desde la versión 1.24.'),
          P('El índice completo ocupa 62 MB en disco (memorias, códigos cuantizados de cada '
            'fragmento y embeddings originales).'),
          P('7.2 Prueba de fidelidad', 'h2'),
          P('El archivo <font face="Consolas">tests/test_fidelity.py</font> registra los mismos '
            'vectores aleatorios (con 5 % de valores indefinidos) en el '
            '<font face="Consolas">AssociativeMemory</font> original y en '
            '<font face="Consolas">MemoryBank</font>, y compara relación, mismatches, peso, '
            'reconocimiento, entropía y media para 20 cues en cuatro configuraciones de '
            '(ι, tolerance, κ). Todas coinciden. Durante el desarrollo esta prueba detectó una '
            'diferencia sutil: el original calcula el umbral iota incluyendo la fila de valores '
            'indefinidos, y el port se corrigió para hacer lo mismo.')]

# ------------------------------------------------------------------ 8. recuperación
story += [P('8. Recuperación con EAM', 'h1'),
          P('La recuperación tiene dos niveles: primero se eligen las obras (memorias) y después los '
            'fragmentos dentro de esas obras.'),
          P('8.1 Nivel obra: criterio original de dimex', 'h2'),
          P('En <font face="Consolas">AssociativeMemorySystem.recall</font>, entre las memorias que '
            'reconocen el cue se elige la de menor penalización:'),
          F('penalización<sub>k</sub> = entropía<sub>k</sub> / weight<sub>k</sub>(v)'),
          P('La <b>entropía</b> mide qué tan dispersos están los conteos de la memoria: si en una '
            'columna siempre se registró el mismo valor, su entropía es 0. El <b>peso</b> mide cuánto '
            'coincide el cue con lo registrado. La idea es preferir memorias “nítidas” (entropía baja) '
            'que coincidan con el cue. Tiene sentido en DIMEx, donde cada memoria es un fonema con miles '
            'de ejemplos: todas las memorias tienen muchos registros y sus entropías son comparables.'),
          P('El problema: obras de un solo fragmento', 'h3'),
          P('En este corpus, <b>128 de las 693 obras</b> producen un solo fragmento (minicuentos como '
            '<i>El dinosaurio</i>, <i>Alas</i> o <i>El diluvio</i>). Una memoria con un único registro '
            'tiene un solo 1 por columna, así que su entropía es exactamente 0, y entonces:'),
          F('penalización = 0 / peso = 0   (el mínimo posible, sin importar el cue)'),
          P('Esas memorias ganan <i>cualquier</i> pregunta, aunque no se parezcan en nada. La Tabla 3 '
            'lo muestra con la pregunta de Dahlmann:'),
          table([
              ['Obra', 'Fragmentos', 'Entropía', 'Peso', 'Penalización', 'Mismatches (de 1024)'],
              ['Alas', '1', '0.000', '0.066', '<b>0.000</b>', '956'],
              ['El diluvio', '1', '0.000', '0.066', '<b>0.000</b>', '956'],
              ['Esquemas de lo posible V', '1', '0.000', '0.071', '<b>0.000</b>', '951'],
              ['Jasón', '1', '0.000', '0.054', '<b>0.000</b>', '969'],
              ['La granada XXIV', '1', '0.000', '0.063', '<b>0.000</b>', '959'],
              ['…', '', '', '', '', ''],
              ['<b>El sur</b> (puesto 260)', '29', '3.479', '0.178', '19.541', '<b>146</b>'],
          ], [4.6 * cm, 2.5 * cm, 2 * cm, 1.8 * cm, 2.4 * cm, FW - 13.3 * cm], hl_rows=(7,)),
          P('Tabla 3. Top-5 del criterio entropy/weight para “¿Qué enfermedad sufre Dahlmann tras '
            'golpearse la frente?”.', 'caption'),
          P('<i>Alas</i> gana aunque 956 de los 1024 rasgos de la pregunta caen en celdas vacías de su '
            'memoria: casi no coincide en nada. <i>El sur</i> coincide mucho más (solo 146 rasgos en '
            'celdas vacías), pero por tener 29 fragmentos su entropía y su penalización son altas, y '
            'queda en el puesto 260. Por eso este criterio acierta el 0 % de las preguntas. Restringir '
            'con tolerance elimina las memorias de un fragmento, pero el orden sigue siendo pobre (ver '
            'sección 10). El criterio sigue disponible con <font face="Consolas">--criterion dimex</font>.'),
          P('8.2 Nivel obra: log-verosimilitud suave (criterio por defecto)', 'h2'),
          P('Para cada memoria, cada rasgo del cue recibe una puntuación y después se promedian:'),
          F('score<sub>k</sub>(v) = (1/n) Σ<sub>j</sub> log( Σ<sub>i</sub> R<sub>k</sub>[i, j] · '
            'G(i, v<sub>j</sub>) / N<sub>k</sub> + ε )'),
          P('donde G(i, v) = exp(−(i−v)² / 2(σm)²) es la misma gaussiana que dimex usa en el recuerdo, '
            'N<sub>k</sub> es el número de fragmentos registrados en la memoria y ε = 0.01.'),
          P('<b>Lectura intuitiva.</b> El término dentro del logaritmo es una <i>coincidencia suave</i> '
            'que responde a la pregunta: “de los fragmentos de esta obra, ¿qué fracción tenía en este '
            'rasgo un valor igual o cercano al del cue?”. Un valor exacto cuenta completo y un valor a '
            'uno o dos niveles cuenta parcialmente. El score de la obra es el promedio, sobre los 1024 '
            'rasgos, del logaritmo de esa coincidencia. Propiedades:')]
story += B(['<b>No depende del tamaño de la memoria.</b> Al dividir entre N<sub>k</sub>, una obra '
            'de 1 fragmento y otra de 29 se miden en la misma escala: tener pocos registros ya no da '
            'ventaja, y una memoria de un solo registro solo gana si el cue realmente coincide con él.',
            '<b>Generaliza los mismatches.</b> El logaritmo castiga fuerte las no-coincidencias: un '
            'rasgo con coincidencia 0 aporta log(0.01) ≈ −4.6, mientras que uno con coincidencia alta '
            'aporta cerca de 0. Un mismatch de la EAM (el cue cae en una celda vacía) es justo el caso '
            'que más se penaliza; con σ → 0 el criterio se reduce a contar mismatches (cada uno aporta '
            'log ε) más un peso normalizado para el resto. La diferencia es que aquí la penalización '
            'es graduada, no un conteo de sí o no.',
            '<b>Tolera cercanía.</b> Una pregunta nunca produce el mismo vector que el texto, así que '
            'un valor vecino debe contar algo; la gaussiana se encarga de ello.'])
story += [P('El mismo ejemplo, rasgo por rasgo', 'h3'),
          P('La Tabla 4 compara <i>El sur</i> con <i>Alas</i> (el ganador del criterio de dimex) en los '
            'primeros cinco rasgos del cue de la pregunta de Dahlmann:'),
          table([
              ['', 'rasgo 0', 'rasgo 1', 'rasgo 2', 'rasgo 3', 'rasgo 4'],
              ['<b>El sur</b>: coincidencia suave', '0.49', '0.58', '0.68', '0.23', '0.63'],
              ['<b>El sur</b>: log(coincidencia + ε)', '−0.69', '−0.53', '−0.38', '−1.42', '−0.45'],
              ['<b>Alas</b>: coincidencia suave', '0.58', '0.11', '1.00', '0.04', '0.98'],
              ['<b>Alas</b>: log(coincidencia + ε)', '−0.53', '<b>−2.09</b>', '0.01', '<b>−2.92</b>', '−0.01'],
          ], [5.6 * cm] + [(FW - 5.6 * cm) / 5] * 5, hl_rows=(2, 4)),
          P('Tabla 4. Contribución de cada rasgo al score de la obra.', 'caption'),
          P('<i>El sur</i> coincide de forma moderada y <b>constante</b>. <i>Alas</i> coincide '
            'perfecto en algunos rasgos, pero falla mucho en otros, y el logaritmo castiga fuerte esos '
            'fallos. Al promediar los 1024 rasgos, el orden se invierte (Tabla 5).'),
          table([
              ['Obra', 'Criterio dimex (entropy/weight)', 'Criterio log-verosimilitud'],
              ['<b>El sur</b>', 'puesto 260', '<b>puesto 1</b> (score −0.50)'],
              ['Alas', '<b>puesto 1</b>', 'puesto 669 (score −0.91)'],
          ], [4 * cm, (FW - 4 * cm) / 2, (FW - 4 * cm) / 2], hl_rows=(1,)),
          P('Tabla 5. Posición de cada obra entre las 693 memorias con cada criterio.', 'caption'),
          P('Con el nuevo criterio, las cinco mejores obras para esta pregunta son <i>El sur</i>, '
            '<i>Las ménades</i>, <i>Trenzas</i>, <i>La doble y única mujer</i> y <i>Míster Taylor</i>. '
            'En la evaluación completa (sección 10), el criterio acierta la obra en el 67 % de las '
            'preguntas, frente al 0 % del criterio de dimex y al 48 % de la búsqueda vectorial con coseno.'),
          P('<b>En resumen:</b> entropy/weight premia a las memorias “nítidas”, y una memoria con un '
            'solo registro es trivialmente nítida. La log-verosimilitud premia a las memorias donde el '
            'cue <b>coincide de forma consistente</b> con lo registrado, sin importar cuántos registros '
            'tengan.', 'note')]
story += [P('8.3 Reconocimiento y rechazo (min_z)', 'h2'),
          P('Una ventaja de la EAM sobre una base vectorial es que puede <i>no reconocer</i> un cue. '
            'El valor absoluto del score no sirve como umbral (una pregunta ajena al corpus obtiene '
            'scores del mismo orden que una válida), pero sí la posición relativa de la mejor '
            'memoria respecto al conjunto:'),
          F('z<sub>k</sub> = (score<sub>k</sub> − media de los scores) / desviación estándar de los scores'),
          P('Con <font face="Consolas">--min-z</font>, una memoria solo reconoce el cue si '
            'z<sub>k</sub> ≥ min_z. Es el análogo relativo de κ en dimex, que también compara el '
            'peso con la media. Si ninguna memoria reconoce el cue, no se recupera nada y el sistema '
            'responde “No lo sé.” sin llamar al modelo de lenguaje.'),
          P('8.4 Nivel fragmento', 'h2'),
          P('Dentro de las obras seleccionadas (5 por defecto), cada fragmento c se puntúa con el '
            'peso suavizado que tendría una memoria que contuviera solo ese fragmento:'),
          F('score(c) = (1/n) Σ<sub>j</sub> G(c<sub>j</sub>, v<sub>j</sub>),  con σ<sub>frag</sub> = 0.2'),
          P('Es matemáticamente idéntico a construir una memoria por fragmento, pero se calcula '
            'directamente sobre los códigos cuantizados, sin almacenar 11,185 tablas. Todos los '
            'fragmentos de las obras seleccionadas compiten juntos y se devuelven los 8 mejor '
            'puntuados en total (no 8 por obra), así que pueden venir todos de la misma obra.')]

# ------------------------------------------------------------------ 8.5 ejemplo
story += [CondPageBreak(6 * cm), P('8.5 Ejemplo paso a paso', 'h2'),
          P('Para seguir el capítulo a mano, el sistema se reduce a <b>3 obras, 4 rasgos y 4 niveles</b> '
            '(0 a 3). En el sistema real hay 693 obras, 1024 rasgos y 16 niveles, pero las operaciones '
            'son exactamente las mismas. Todos los números se calcularon con el código del proyecto '
            '(<font face="Consolas">MemoryBank</font>, con σ = 1 nivel y ε = 0.01).'),
          P('Las obras y sus memorias', 'h3')]
story += B(['<b>Obra A</b>, un minicuento con 1 fragmento: [1, 0, 2, 1]',
            '<b>Obra B</b>, un cuento con 4 fragmentos: [1,2,0,3], [1,2,1,3], [2,2,0,3], [1,3,0,2]',
            '<b>Obra C</b>, un cuento con 3 fragmentos: [0,1,3,0], [0,1,3,1], [1,0,3,0]'])
story += [P('Cada número es el nivel de un rasgo. Al registrar los fragmentos, cada memoria queda como '
            'una tabla de conteos (filas = nivel, columnas = rasgo):'),
          code("""
Memoria A (1 fragm.)      Memoria B (4 fragm.)      Memoria C (3 fragm.)
        r0 r1 r2 r3               r0 r1 r2 r3               r0 r1 r2 r3
nivel 0  0  1  0  0       nivel 0  0  0  3  0       nivel 0  2  1  0  2
nivel 1  1  0  0  1       nivel 1  3  0  1  0       nivel 1  1  2  0  1
nivel 2  0  0  1  0       nivel 2  1  3  0  1       nivel 2  0  0  0  0
nivel 3  0  0  0  0       nivel 3  0  1  0  3       nivel 3  0  0  3  0
"""),
          P('La pregunta del usuario trata de la obra B y, cuantizada, produce el cue '
            '<b>[1, 2, 1, 2]</b>. El sistema debería elegir B.'),
          P('Paso 1: criterio de dimex (entropy/weight)', 'h3'),
          P('El <b>peso</b> lee, en cada rasgo j, la celda R[cue<sub>j</sub>, j], promedia y divide '
            'entre el máximo de la tabla. Una celda en 0 es un <b>mismatch</b>. La <b>entropía</b> de B es '
            '0.811 bits (cada columna reparte 3/4 y 1/4), la de C es 0.689 y la de A es 0, porque un '
            'solo fragmento deja un único 1 por columna.'),
          table([
              ['Obra', 'R[cue<sub>j</sub>, j] (r0 r1 r2 r3)', 'Peso', 'Entropía', 'Penalización', 'Mismatches'],
              ['<b>A</b>', '1  0  0  0', '0.250', '0.000', '<b>0.000 ← gana</b>', '3 de 4'],
              ['B', '3  3  1  1', '0.667', '0.811', '1.217', '<b>0 de 4</b>'],
              ['C', '1  0  0  0', '0.083', '0.689', '8.265', '3 de 4'],
          ], [1.5 * cm, 4.3 * cm, 1.8 * cm, 2.0 * cm, 3.4 * cm, FW - 13.0 * cm], hl_rows=(1,)),
          P('Tabla 6. Criterio de dimex en el ejemplo.', 'caption'),
          P('Gana A aunque falla en 3 de los 4 rasgos, mientras que B coincide en todos: 0 dividido '
            'entre cualquier peso positivo da 0. Basta que el minicuento coincida en un solo rasgo para '
            'ganar. Es lo mismo que ocurrió con la pregunta real: <i>Alas</i> ganó con 956 mismatches de 1024.'),
          P('Paso 2: log-verosimilitud suave', 'h3'),
          P('La <b>coincidencia suave</b> de un rasgo suma cada conteo multiplicado por un peso que '
            'decae con la distancia al nivel del cue (G = 1.00, 0.61, 0.14 y 0.01 para distancias 0, 1, '
            '2 y 3) y divide entre el número de fragmentos de la obra. Por ejemplo, para B en el rasgo 2 '
            '(cue = 1) hay 3 fragmentos en el nivel 0 y 1 en el nivel 1: (3 × 0.61 + 1 × 1.00) / 4 = 0.705. '
            'Después se aplica log(coincidencia + 0.01) y se promedia sobre los rasgos.'),
          table([
              ['', 'r0', 'r1', 'r2', 'r3', 'Score'],
              ['A: coincidencia', '1.00', '0.14', '0.61', '0.61', ''],
              ['A: log', '0.01', '<b>−1.93</b>', '−0.48', '−0.48', '−0.722'],
              ['B: coincidencia', '0.90', '0.90', '0.71', '0.71', ''],
              ['B: log', '−0.09', '−0.09', '−0.34', '−0.34', '<b>−0.214 ← gana</b>'],
              ['C: coincidencia', '0.74', '0.45', '0.14', '0.29', ''],
              ['C: log', '−0.29', '−0.78', '<b>−1.93</b>', '−1.20', '−1.048'],
          ], [3.6 * cm] + [(FW - 7.6 * cm) / 4] * 4 + [4.0 * cm], hl_rows=(4,)),
          P('Tabla 7. Log-verosimilitud suave en el ejemplo.', 'caption'),
          P('Ahora gana B. A coincide perfecto en r0, pero en r1 su único fragmento está lejos del cue y '
            'el logaritmo lo castiga. B nunca coincide perfecto en todo, pero coincide bien en todos los '
            'rasgos. Como se divide entre el número de fragmentos, tener uno solo ya no da ventaja.'),
          P('Paso 3: filtro de reconocimiento (min_z)', 'h3'),
          P('El promedio de los tres scores es −0.661 y su desviación estándar 0.343. El z-score indica '
            'cuánto destaca cada obra sobre las demás:'),
          table([
              ['Obra', 'Score', 'z', '¿Reconoce el cue con min_z = 1.1?'],
              ['A', '−0.722', '−0.18', 'No'],
              ['<b>B</b>', '−0.214', '<b>1.30</b>', '<b>Sí</b>'],
              ['C', '−1.048', '−1.13', 'No'],
          ], [2.0 * cm, 2.6 * cm, 2.2 * cm, FW - 6.8 * cm], hl_rows=(2,)),
          P('Tabla 8. Z-scores en el ejemplo.', 'caption'),
          P('Solo B supera el umbral. Si ninguna obra lo superara, el sistema respondería “No lo sé.” '
            'sin llamar al LLM. Con datos reales, la pregunta de Dahlmann obtiene z = 1.43 en su mejor '
            'obra (aceptada) y “¿Cuál es la capital de Australia?” obtiene z = 1.00 (rechazada).'),
          KeepTogether([P('Paso 4: elegir los fragmentos', 'h3'),
          P('Dentro de la obra elegida, cada fragmento se compara con el cue rasgo por rasgo con la misma '
            'gaussiana y se promedia:'),
          table([
              ['Fragmento de B', 'r0', 'r1', 'r2', 'r3', 'Score'],
              ['[1, 2, 1, 3]', '1.00', '1.00', '1.00', '0.61', '<b>0.902 ← el mejor</b>'],
              ['[1, 2, 0, 3]', '1.00', '1.00', '0.61', '0.61', '0.803'],
              ['[1, 3, 0, 2]', '1.00', '0.61', '0.61', '1.00', '0.803'],
              ['[2, 2, 0, 3]', '0.61', '1.00', '0.61', '0.61', '0.705'],
          ], [3.6 * cm] + [(FW - 7.6 * cm) / 4] * 4 + [4.0 * cm], hl_rows=(1,)),
          P('Tabla 9. Puntuación de los fragmentos de la obra B.', 'caption')]),
          P('En este nivel todos los candidatos tienen un solo registro, así que no aparece el sesgo del '
            'paso 1: no hay memorias grandes y pequeñas que comparar.'),
          P('El recorrido completo con la pregunta real', 'h3'),
          table([
              ['Paso', 'Resultado para “¿Qué enfermedad sufre Dahlmann tras golpearse la frente?”'],
              ['SONAR + cuantización', 'cue de 1024 niveles: [14, 10, 12, 1, 15, …]'],
              ['Nivel obra (8.2)', 'Top-5: <i>El sur</i> (−0.501), <i>Las ménades</i> (−0.539), <i>Trenzas</i> (−0.541), '
               '<i>La doble y única mujer</i> (−0.543), <i>Míster Taylor</i> (−0.544); 213 fragmentos candidatos'],
              ['Reconocimiento (8.3)', 'Mejor obra con z = 1.43: aceptada incluso con min_z = 1.1'],
              ['Nivel fragmento (8.4)', 'De los 8 mejores (scores 0.497 a 0.476), 6 son de <i>El sur</i>, uno de '
               '<i>Míster Taylor</i> y uno de <i>Las ménades</i>; los de <i>El sur</i> incluyen el del golpe en la '
               'frente y el de la septicemia'],
              ['Augmentation + LLM', 'GPT-5.5: “Dahlmann sufre una septicemia, según <i>El sur</i> de Jorge Luis Borges.”'],
          ], [4.2 * cm, FW - 4.2 * cm]),
          P('Tabla 10. Recorrido completo del capítulo con la pregunta del diagrama.', 'caption')]

# ------------------------------------------------------------------ 9. augmentation
story += [CondPageBreak(7 * cm), P('9. Augmentation y generación', 'h1'),
          P('Los fragmentos recuperados se insertan en el prompt siguiendo la plantilla del '
            'diagrama. Cada fragmento lleva el título de la obra y el autor para que la respuesta '
            'pueda citarlos:'),
          code('''
<documentos>
<documento indice="1" obra="El sur" autor="Jorge Luis Borges">
... texto del fragmento ...
</documento>
...
</documentos>

Responde la siguiente pregunta basándote en los documentos anteriores.
Si la respuesta no está en los documentos, di "No lo sé."

<pregunta>¿Qué enfermedad sufre Dahlmann tras golpearse la frente?</pregunta>
'''),
          P('El mensaje de sistema indica que el asistente es experto en literatura latinoamericana, '
            'que responde en español usando solo los fragmentos, que menciona obra y autor, y que '
            'responde exactamente “No lo sé.” si la información no está.'),
          P('Configuración de la llamada a OpenAI:')]
story += B(['Modelo por defecto <font face="Consolas">gpt-5.5</font> (se cambia con '
            '<font face="Consolas">--model</font>; por ejemplo <font face="Consolas">gpt-5.4-mini</font> '
            'para reducir costo).',
            'API de Chat Completions de OpenAI con <i>streaming</i>: el texto aparece en la terminal '
            'conforme se genera.',
            'Si la EAM no recupera fragmentos (con <font face="Consolas">--min-z</font>), el sistema '
            'responde “No lo sé.” sin llamar al modelo.',
            'Credenciales: <font face="Consolas">OPENAI_API_KEY</font> y <font face="Consolas">OPENAI_MODEL</font> '
            'se leen del archivo <font face="Consolas">.env</font> mediante <font face="Consolas">config.py</font>.'])

# ------------------------------------------------------------------ 10. evaluación
story += [P('10. Evaluación', 'h1'),
          P('10.1 Metodología', 'h2'),
          P('Se compara la recuperación con EAM contra una base vectorial convencional: similitud '
            'coseno entre el embedding SONAR de la consulta y los embeddings SONAR de todos los '
            'fragmentos (los mismos que alimentan a las memorias, así que la única diferencia es el '
            'mecanismo de recuperación). Dos conjuntos de consultas:')]
story += B(['<b>Sintético (300 consultas):</b> de fragmentos elegidos al azar (semilla fija) se '
            'toma una oración interior de al menos 10 palabras. El objetivo es recuperar su obra '
            '(obra@1, obra@5) y su fragmento (frag@8). Mide la localización de texto literal.',
            '<b>Preguntas (31):</b> 21 preguntas escritas a mano sobre cuentos conocidos del corpus '
            '(El sur, El Aleph, Casa tomada, Axolotl, Luvina, El eclipse, El guardagujas, Viaje a la '
            'semilla, etc.) y 10 preguntas ajenas al corpus (capital de Australia, fórmula de la '
            'cafeína, mole poblano…). Para las primeras se mide si la obra correcta aparece entre '
            'las 5 recuperadas; para las segundas, si la EAM las rechaza. Con la configuración por '
            'defecto se recuperan 5 obras y 8 fragmentos (obra@5, frag@8).'])
story += [P('10.2 Resultados', 'h2'),
          table([
              ['Configuración', 'Sint. obra@1', 'Sint. obra@5', 'Sint. frag@8', 'Preg. obra@5', 'Acepta válidas', 'Rechaza ajenas'],
              ['Vector DB (coseno)', '0.72', '0.85', '0.84', '0.62', '—', '—'],
              ['EAM dimex, tol = 1.0', '0.00', '0.00', '0.00', '0.00', '1.00', '0.00'],
              ['EAM dimex, tol = 0.5', '0.01', '0.08', '0.07', '0.00', '1.00', '0.00'],
              ['EAM dimex suave, tol = 0.5', '0.01', '0.06', '0.05', '0.00', '1.00', '0.00'],
              ['EAM loglik, σ = 0.1', '0.30', '0.43', '0.40', '0.38', '1.00', '0.00'],
              ['EAM loglik, σ = 0.2', '0.35', '0.51', '0.47', '0.57', '1.00', '0.00'],
              ['EAM loglik, σ = 0.3 (defecto)', '0.36', '0.49', '0.47', '0.67', '1.00', '0.00'],
              ['EAM loglik, σ = 0.4', '0.31', '0.46', '0.44', '0.67', '1.00', '0.00'],
              ['EAM loglik, σ = 0.3, min_z = 1.05', '0.34', '0.44', '0.41', '0.67', '1.00', '0.50'],
              ['EAM loglik, σ = 0.3, min_z = 1.10', '0.30', '0.36', '0.35', '0.57', '0.81', '0.90'],
              ['EAM loglik, σ = 0.3, min_z = 1.15', '0.26', '0.29', '0.27', '0.38', '0.52', '0.90'],
          ], [4.9 * cm] + [(FW - 4.9 * cm) / 6] * 6, hl_rows=(7,)),
          P('Tabla 11. Resultados de <font face="Consolas">python evaluate.py --grid --n 300</font> '
            '(m = 16, cuantización por cuantiles, 5 obras y 8 fragmentos). “Sint.” = conjunto sintético; '
            '“Preg.” = preguntas.', 'caption'),
          P('Efecto de recuperar más obras y fragmentos', 'h3'),
          P('La versión anterior del sistema recuperaba 3 obras y 5 fragmentos. La Tabla 11b compara '
            'ambas configuraciones con σ = 0.3 (obra@1 no cambia porque no depende de cuántas obras '
            'se recuperan):'),
          table([
              ['Recuperación', 'Método', 'Sint. obra@K', 'Sint. frag@K', 'Preg. obra@K'],
              ['3 obras / 5 fragmentos', 'EAM loglik', '0.43', '0.40', '0.67'],
              ['3 obras / 5 fragmentos', 'Coseno', '0.81', '0.81', '0.48'],
              ['5 obras / 8 fragmentos (defecto)', 'EAM loglik', '0.49', '0.47', '0.67'],
              ['5 obras / 8 fragmentos (defecto)', 'Coseno', '0.85', '0.84', '0.62'],
          ], [5.2 * cm, 3.0 * cm] + [(FW - 8.2 * cm) / 3] * 3, hl_rows=(3,)),
          P('Tabla 11b. obra@K y frag@K con K = 3/5 (arriba) y K = 5/8 (abajo).', 'caption'),
          P('Con preguntas reales, la EAM ya encontraba entre sus 3 primeras obras todas las que '
            'encuentra entre 5: las 7 preguntas que falla quedan fuera de las 5 primeras. El coseno, '
            'en cambio, pasa de 10 a 13 aciertos de 21 al ampliar a 5 obras, así que la ventaja de la '
            'EAM se reduce de 4 preguntas a 1. Para el LLM, pasar a 8 fragmentos da más contexto a '
            'cambio de un prompt más largo, y en el conjunto sintético el fragmento exacto aparece más '
            'a menudo (0.40 → 0.47).', 'note'),
          P('También se probaron ε = 0.001, 0.01 y 0.1, una variante ponderada por entropía y un '
            'criterio híbrido que suma el score de la obra con el mejor fragmento. La ponderación por '
            'entropía empeora ligeramente; el híbrido sube obra@1 sintético hasta 0.58 pero baja las '
            'preguntas a 8–10 de 21, por lo que no se adoptó. El efecto del tamaño de la memoria se '
            'analiza en la sección 10.3.'),
          P('10.3 Tamaño de la memoria: m = 4, 8 y 16', 'h2'),
          P('Cada memoria es una tabla de <b>m filas por n columnas</b>: n = 1024 es el dominio (los '
            'rasgos de SONAR) y m es el rango (los niveles de cuantización). Las filas <i>son</i> los '
            'niveles, así que variar el número de filas equivale a variar m. El experimento es válido '
            'sin volver a codificar con SONAR: los embeddings de los fragmentos y de las consultas son '
            'los mismos, y para cada m sólo se recalculan los cortes del cuantizador y se vuelven a '
            'registrar las 693 memorias. Como σ se expresa como fracción de m, además del valor por '
            'defecto (σ = 0.3) se barrió σ de 0.1 a 0.5 para cada tamaño.'),
          table([
              ['Memoria (m × n)', 'Entropía media (máx.)', 'Tamaño de R', 'Sint. obra@1', 'Sint. obra@5',
               'Sint. frag@8', 'Preg. obra@5'],
              ['4 × 1024', '1.23 bits (2)', '6.8 MB', '0.360', '0.510', '0.467', '0.67'],
              ['8 × 1024', '1.74 bits (3)', '12.2 MB', '0.360', '0.500', '0.470', '0.67'],
              ['16 × 1024 (defecto)', '2.13 bits (4)', '23.0 MB', '0.357', '0.493', '0.467', '0.67'],
              ['Coseno (referencia)', '—', '—', '0.723', '0.850', '0.840', '0.62'],
          ], [3.4 * cm, 2.9 * cm] + [(FW - 6.3 * cm) / 5] * 5, hl_rows=(3,)),
          P('Tabla 12. Tamaño de la memoria con σ = 0.3 y sin umbral '
            '(<font face="Consolas">python evaluate.py --m 4 8 16</font>).', 'caption'),
          table([
              ['m', 'σ = 0.1', 'σ = 0.2', 'σ = 0.3', 'σ = 0.4', 'σ = 0.5'],
              ['4', '0.29 / 0.33', '0.35 / 0.57', '0.36 / 0.67', '0.34 / 0.67', '0.25 / 0.62'],
              ['8', '0.31 / 0.43', '0.35 / 0.57', '0.36 / 0.67', '0.32 / 0.67', '0.23 / 0.57'],
              ['16', '0.30 / 0.38', '0.35 / 0.57', '0.36 / 0.67', '0.31 / 0.67', '0.21 / 0.48'],
          ], [1.6 * cm] + [(FW - 1.6 * cm) / 5] * 5, hl_rows=()),
          P('Tabla 13. Efecto de σ para cada m: sintético obra@1 / preguntas obra@5.', 'caption'),
          table([
              ['m', 'Acepta válidas', 'Preg. obra@5', 'Rechaza ajenas'],
              ['4', '0.90', '0.57', '0.70'],
              ['8', '0.81', '0.57', '0.90'],
              ['16', '0.81', '0.57', '0.90'],
          ], [1.6 * cm] + [(FW - 1.6 * cm) / 3] * 3),
          P('Tabla 14. Reconocimiento con umbral min_z = 1.10 (σ = 0.3).', 'caption')]
story += B(['<b>Los tres tamaños dan prácticamente lo mismo.</b> Las diferencias están dentro del '
            'ruido: con 300 consultas sintéticas el error típico es de ±0.03, y en las preguntas '
            'una sola pregunta equivale a 0.05.',
            '<b>Por qué.</b> Con cuantización por cuantiles cada nivel contiene la misma cantidad de '
            'datos, y σ se mide como fracción de m. Con σ = 0.3 la gaussiana cubre la misma porción '
            'de la distribución de cada rasgo con 4, 8 o 16 niveles; reducir m sólo elimina detalle '
            'fino que la propia gaussiana ya estaba difuminando. Por lo mismo, el mejor σ (0.2–0.3) '
            'es el mismo para los tres tamaños.',
            '<b>Costo y rechazo.</b> m = 4 ocupa la cuarta parte de m = 16 sin perder precisión, '
            'pero con el umbral rechaza menos preguntas ajenas (7 de 10 frente a 9 de 10). m = 8 '
            'conserva el rechazo con la mitad del espacio.',
            '<b>Entropía.</b> En los tres casos queda muy por debajo del máximo (log<sub>2</sub> m): '
            'muchas obras tienen pocos fragmentos y no llegan a llenar las columnas, así que más '
            'niveles no aportan información.',
            '<b>El tamaño no explica la brecha con el coseno</b> en frases literales (0.36 frente a '
            '0.72); esa brecha viene de abstraer la obra completa en una sola memoria.'])
story += [P('10.4 Análisis', 'h2')]
story += B(['<b>El criterio entropy/weight falla por construcción</b> en este dominio, como se '
            'explicó en 8.1: las obras de un fragmento ganan siempre.',
            '<b>Con preguntas, la EAM supera a la base vectorial (0.67 frente a 0.62 con 5 obras; '
            '0.67 frente a 0.48 con 3).</b> La memoria de una obra abstrae la distribución de todos sus '
            'fragmentos; una pregunta, que mezcla personajes, lugares y temas de la obra sin repetir '
            'ninguna oración, se parece más a esa abstracción que a un fragmento concreto. La EAM '
            'pone la obra correcta más arriba en la lista; el coseno la alcanza si se le dan más '
            'candidatos. Con 21 preguntas, la diferencia con 5 obras es de una sola pregunta.',
            '<b>Para localizar una oración literal, la base vectorial gana (0.72 frente a 0.36).</b> '
            'La misma abstracción que ayuda con las preguntas diluye el detalle de un pasaje exacto, '
            'sobre todo en obras largas.',
            '<b>σ controla la tolerancia:</b> con σ = 0.1 la memoria es demasiado estricta; entre '
            '0.2 y 0.4 se obtiene el mejor equilibrio; con 0.5 todo se parece a todo.',
            '<b>El rechazo tiene un costo.</b> Con min_z = 1.10 se rechazan 9 de 10 preguntas ajenas, '
            'pero también 4 de 21 válidas. Como el modelo ya responde “No lo sé” cuando los fragmentos '
            'no contienen la respuesta, el umbral viene desactivado por defecto.',
            '<b>Tamaño de muestra:</b> 21 y 10 preguntas son pocas; las diferencias deben tomarse '
            'como indicativas. Ampliar el conjunto de preguntas es el siguiente paso natural.'])

story += [P('10.5 Ejemplo: la pregunta del diagrama', 'h2'),
          P('Para “¿Qué enfermedad sufre Dahlmann tras golpearse la frente?” la memoria de <i>El sur</i> '
            'obtiene el mejor score y 6 de los 8 fragmentos recuperados pertenecen a esa obra; los otros '
            'dos vienen de <i>Míster Taylor</i> y <i>Las ménades</i>. El cuarto contiene la respuesta '
            '(“…el cirujano le dijo que había estado a punto de morir de una septicemia…”) y el quinto '
            'describe el golpe en la frente con la arista de un batiente. Los dos fragmentos ajenos no '
            'estorban: el modelo responde con los de <i>El sur</i>.')]

# ------------------------------------------------------------------ 11. instalación y uso
story += [CondPageBreak(7 * cm), P('11. Instalación', 'h1'),
          P('11.1 Requisitos', 'h2')]
story += B(['Windows, Linux o macOS con Anaconda o Miniconda.',
            'Opcional pero recomendado: GPU NVIDIA con al menos 4 GB (el codificador ocupa ~1.5 GB '
            'en fp16). En CPU funciona, pero la construcción del índice tarda bastante más.',
            '~4 GB de disco para el modelo SONAR (se descarga automáticamente la primera vez en la '
            'caché de HuggingFace).',
            'Una API key de OpenAI para el paso de generación. La recuperación funciona sin ella.'])
story += [P('11.2 Crear el entorno', 'h2'),
          code('''
conda create -n eamrag python=3.11
conda activate eamrag
pip install torch --index-url https://download.pytorch.org/whl/cu124
cd D:\\DOCUMENTOS\\TRABAJO\\IIMAS\\PROYECTOS\\MAE2026\\PROYECTO\\eam_rag
pip install -r requirements.txt
'''),
          P('Sin GPU, la segunda línea de pip se sustituye por <font face="Consolas">pip install torch</font>.'),
          P('11.3 Configurar la API key (.env)', 'h2'),
          P('La key se guarda en el archivo <font face="Consolas">eam_rag/.env</font>. '
            'Hay una plantilla en <font face="Consolas">.env.example</font>:'),
          code('''
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-5.5        # opcional
'''),
          P('El módulo <font face="Consolas">eam_rag/config.py</font> carga ese archivo al importarse y '
            'expone <font face="Consolas">OPENAI_API_KEY</font> y <font face="Consolas">OPENAI_MODEL</font> '
            'al resto del proyecto (<font face="Consolas">from config import OPENAI_API_KEY</font>). '
            'Si existe una variable de entorno del sistema con el mismo nombre, tiene prioridad. '
            'El <font face="Consolas">.env</font> está en <font face="Consolas">.gitignore</font> para que '
            'nunca se suba a un repositorio.', 'note'),
          P('12. Uso', 'h1'),
          P('Todos los comandos de este capítulo se ejecutan dentro de la carpeta '
            '<font face="Consolas">eam_rag</font> y con el entorno <font face="Consolas">eamrag</font> '
            'activado. Por eso, cada vez que se abre una terminal nueva, primero hay que seguir el '
            'paso 0.'),
          P('12.1 Paso 0: activar el entorno', 'h2'),
          P('Abra <b>Anaconda Prompt</b> (o una terminal donde <font face="Consolas">conda</font> esté '
            'disponible), active el entorno creado en 11.2 y entre a la carpeta del proyecto:'),
          code('''
conda activate eamrag
cd D:\\DOCUMENTOS\\TRABAJO\\IIMAS\\PROYECTOS\\MAE2026\\PROYECTO\\eam_rag
'''),
          P('El nombre del entorno aparece al inicio de la línea de comandos, por ejemplo '
            '<font face="Consolas">(eamrag) D:\\...\\eam_rag&gt;</font>. Para comprobar que se está '
            'usando el Python correcto y que PyTorch ve la GPU:'),
          code('''
python -c "import torch, transformers; print(torch.__version__, torch.cuda.is_available())"
2.x.x+cu124 True
'''),
          P('Si aparece <font face="Consolas">False</font>, el sistema funciona igual pero en CPU '
            '(más lento). Si aparece <font face="Consolas">ModuleNotFoundError</font>, el entorno '
            'no está activado o falta el paso 11.2.'),
          P('<b>Problemas comunes.</b> Si en PowerShell o en la terminal de VS Code aparece '
            '“conda no se reconoce como un comando”, ejecute una sola vez '
            '<font face="Consolas">conda init powershell</font> desde Anaconda Prompt y abra una '
            'terminal nueva. También se puede evitar la activación llamando directamente al Python '
            'del entorno: <font face="Consolas">D:\\anaconda3\\envs\\eamrag\\python.exe rag.py "..."</font> '
            '(la ruta depende de dónde esté instalado Anaconda). Al terminar, '
            '<font face="Consolas">conda deactivate</font> sale del entorno.', 'note'),
          P('12.2 Paso 1: construir el índice', 'h2'),
          code('python build_index.py'),
          P('Lee el corpus, lo fragmenta, calcula los embeddings SONAR, construye las 693 memorias y '
            'guarda todo en <font face="Consolas">eam_rag/store/</font>. Salida esperada:'),
          code('''
693 obras, 11185 fragmentos
SONAR: 100%|██████████| 350/350 [01:12<00:00,  4.82batch/s]
Embeddings SONAR (11185, 1024) en 73s (cuda)
Memorias: 693 x (16 x 1024); entropía media 2.128 bits
Guardado en ...\\eam_rag\\store
'''.replace('██████████', '##########')),
          table([
              ['Opción', 'Por defecto', 'Descripción'],
              ['--data', '../datasets_csv', 'Carpeta con los CSV del corpus.'],
              ['--out', 'store', 'Carpeta donde se guarda el índice.'],
              ['--m', '16', 'Niveles de cuantización (rango de la memoria).'],
              ['--quant', 'quantile', 'Método de cuantización: quantile o minmax.'],
              ['--max-words', '120', 'Palabras aproximadas por fragmento.'],
              ['--overlap', '1', 'Oraciones repetidas entre fragmentos consecutivos.'],
              ['--batch-size', '32', 'Fragmentos por lote al codificar con SONAR.'],
          ], [3 * cm, 3.2 * cm, FW - 6.2 * cm]),
          Spacer(1, 6),
          P('Si solo se cambia <font face="Consolas">--m</font> o <font face="Consolas">--quant</font>, '
            'los embeddings se reutilizan y la reconstrucción tarda segundos. Si se cambia la '
            'fragmentación, se recalculan.'),
          P('12.3 Paso 2: hacer preguntas', 'h2'),
          code('''
python rag.py "¿Qué enfermedad sufre Dahlmann tras golpearse la frente?"
'''),
          P('Muestra los fragmentos recuperados (autor, obra, score del fragmento, score de la obra '
            'y mismatches) y después la respuesta del modelo en streaming. Otras formas:'),
          code('''
python rag.py                          # modo interactivo (Ctrl+C para salir)
python rag.py --no-llm "..."           # solo recuperación + prompt, sin LLM
python rag.py --min-z 1.1 "..."        # activa el rechazo de consultas no reconocidas
python rag.py --top-works 3 --top-chunks 5 "..."   # recuperación más acotada
python rag.py --criterion dimex --tolerance 0.5 "..."   # criterio original de dimex
python rag.py --sigma 0.2 "..."        # memoria más estricta
python rag.py --model gpt-5.4-mini "..."   # modelo más barato
'''),
          table([
              ['Opción', 'Por defecto', 'Descripción'],
              ['query', '(vacío)', 'La pregunta. Sin ella se abre el modo interactivo.'],
              ['--store', 'store', 'Carpeta del índice.'],
              ['--top-works', '5', 'Número de obras (memorias) que se recuperan.'],
              ['--top-chunks', '8', 'Número de fragmentos que se pasan al modelo.'],
              ['--criterion', 'loglik', 'loglik (recomendado) o dimex (entropy/weight).'],
              ['--min-z', 'desactivado', 'Umbral de reconocimiento relativo; 1.1 es un buen punto de partida.'],
              ['--sigma', '0.3', 'Desviación de la gaussiana, fracción de m.'],
              ['--tolerance', '1.0', 'Mismatches permitidos, fracción de n.'],
              ['--iota', '0', 'Moderación de la relación (criterio dimex).'],
              ['--kappa', '0', 'Peso mínimo relativo a la media (criterio dimex).'],
              ['--model', 'gpt-5.5', 'Modelo de OpenAI para la generación.'],
              ['--no-llm', '—', 'No llama al LLM; imprime el prompt aumentado.'],
          ], [3 * cm, 3.2 * cm, FW - 6.2 * cm])]

story += [KeepTogether([P('12.4 Ejemplo de salida', 'h2'), code('''
Recuperación (EAM):
  [1] Jorge Luis Borges - «El sur»  frag=0.497 obra=-0.501 mismatches=146
      Dahlmann se inclinó a recoger la daga y sintió dos cosas. ...
  [2] Jorge Luis Borges - «El sur»  frag=0.492 obra=-0.501 mismatches=146
      Dahlmann no se extrañó de que el otro, ahora, lo conociera, ...
  [3] Jorge Luis Borges - «El sur»  frag=0.490 obra=-0.501 mismatches=146
      Dalhman, perplejo, decidió que nada había ocurrido y abrió ...
  [4] Jorge Luis Borges - «El sur»  frag=0.490 obra=-0.501 mismatches=146
      En esos días, Dahlmann minuciosamente se odió; ... había estado
      a punto de morir de una septicemia ...
  [5] Jorge Luis Borges - «El sur»  frag=0.488 obra=-0.501 mismatches=146
      Dahlmann había conseguido, esa tarde, un ejemplar descabalado ...
  [6] Augusto Monterroso - «Míster Taylor»  frag=0.479 obra=-0.544 mismatches=173
      Este impulso fue particularmente comprobable en una nueva ...
  [7] Jorge Luis Borges - «El sur»  frag=0.478 obra=-0.501 mismatches=146
      Del otro lado de las vías quedaba la estación, que era poco ...
  [8] Julio Cortázar - «Las ménades»  frag=0.476 obra=-0.539 mismatches=22
      La chica de Epifanía me miró, reconociéndome, y me gritó algo, ...

Respuesta:
Dahlmann sufre una **septicemia** tras golpearse la frente, según
*“El sur”* de **Jorge Luis Borges**.
''')]),
          P('<b>frag</b> es el score del fragmento (entre 0 y 1; mayor es mejor), <b>obra</b> es el '
            'score log-verosímil de la memoria (mayor es mejor) y <b>mismatches</b> el número de '
            'rasgos del cue que caen en celdas vacías de esa memoria (de 1024).', 'note'),
          P('12.5 Paso 3 (opcional): evaluar', 'h2'),
          code('''
python evaluate.py               # evalúa la configuración guardada
python evaluate.py --grid        # barrido de criterios y parámetros (Tabla 11)
python evaluate.py --m 4 8 16    # tamaños de memoria (Tablas 12 a 14)
python evaluate.py -v            # detalle por pregunta: obras de la EAM y del coseno
python evaluate.py --n 1000      # más consultas sintéticas (por defecto 300)
'''),
          P('Para añadir preguntas de evaluación, edite <font face="Consolas">questions.json</font>: '
            'cada entrada tiene <font face="Consolas">q</font> (pregunta), '
            '<font face="Consolas">title</font> (título exacto de la obra, o '
            '<font face="Consolas">null</font> si la pregunta es ajena al corpus) y '
            '<font face="Consolas">author</font>. Los embeddings de las consultas se guardan en '
            '<font face="Consolas">store/eval_queries_N.npz</font> junto con una huella SHA-1 de '
            'sus textos, y se recalculan si cambia cualquier pregunta. La obra correcta se identifica '
            'por título y autor, porque hay títulos repetidos entre autores.'),
          KeepTogether([P('12.6 Uso desde Python', 'h2'), code('''
from eam_store import EAMStore
from sonar_encoder import SonarEncoder
from generator import answer, build_prompt

store = EAMStore.load("store")
store.set_params(sigma=0.3, min_z=None)       # ajustes sin reconstruir
encoder = SonarEncoder()

pregunta = "¿Qué hace la gallina que la salva de ser cocinada?"
hits = store.retrieve(encoder.encode(pregunta), top_works=5, top_chunks=8)
for h in hits:
    print(h.author, h.title, round(h.chunk_score, 3))

print(build_prompt(pregunta, hits))           # prompt aumentado
print(answer(pregunta, hits))                 # usa la key del .env

# Acceso directo a las memorias
bank = store.bank                             # MemoryBank con R[693, 17, 1024]
cue = store.quantizer.transform(encoder.encode(pregunta))[0]
scores = bank.log_likelihood(cue)             # score por obra
mis = bank.mismatches(cue)                    # mismatches por obra
recuerdo, ok = bank.recall(0, cue)            # λ-reducción de la memoria 0
''')]),
          P('12.7 Prueba de fidelidad', 'h2'),
          P('Requiere numpy anterior a 1.24 (el código original usa '
            '<font face="Consolas">np.int</font>), por ejemplo el entorno <font face="Consolas">eam</font>:'),
          code('D:\\anaconda3\\envs\\eam\\python.exe eam_rag\\tests\\test_fidelity.py\n'
               'OK: MemoryBank == dimex AssociativeMemory')]

# ------------------------------------------------------------------ 13. archivos
story += [CondPageBreak(7 * cm), KeepTogether([P('13. Estructura de archivos', 'h1'), code('''
PROYECTO/
├── rag_modificado.png         diagrama del sistema
├── datasets_csv/              corpus: 58 CSV (link, text_metadata, text)
├── dimex/                     código original de las EAM (Pineda et al.)
├── RAG_EAM_documentacion.pdf  este documento
└── eam_rag/
    ├── .env                   API key de OpenAI (no se comparte)
    ├── .env.example           plantilla del .env
    ├── .gitignore             excluye .env y store/
    ├── config.py              carga .env (OPENAI_API_KEY, OPENAI_MODEL)
    ├── associative.py         MemoryBank (EAM vectorizada)
    ├── corpus.py              carga, limpieza y fragmentación
    ├── sonar_encoder.py       codificador SONAR
    ├── eam_store.py           Quantizer + EAMStore (índice y recuperación)
    ├── generator.py           augmentation + OpenAI
    ├── build_index.py         CLI: construir índice
    ├── rag.py                 CLI: preguntar
    ├── evaluate.py            CLI: evaluar contra coseno
    ├── questions.json         preguntas de evaluación
    ├── requirements.txt
    ├── README.md
    ├── tests/
    │   └── test_fidelity.py   comparación con dimex
    └── store/                 índice generado (62 MB)
        ├── memories.npz       relaciones R, códigos, cuantizador
        ├── store.json         configuración, obras y fragmentos
        ├── embeddings.npy     embeddings SONAR de los fragmentos
        └── embeddings.sha1    huella del corpus fragmentado
''')]),
          P('14. Limitaciones y trabajo futuro', 'h1')]
story += B(['<b>Conjunto de evaluación pequeño.</b> Convendría ampliar las preguntas (por ejemplo, '
            'generarlas por obra y revisarlas a mano) y evaluar también la calidad de la respuesta '
            'final, no solo la recuperación.',
            '<b>Detalle fino.</b> La memoria por obra pierde precisión para localizar pasajes '
            'exactos. Opciones: memorias por sección de la obra en obras largas, o un nivel '
            'intermedio de memorias por grupos de fragmentos.',
            '<b>Preguntas frente a narración.</b> SONAR codifica igual una pregunta que una oración '
            'narrativa; reformular la pregunta como afirmación antes de codificarla podría acercar '
            'el cue al texto.',
            '<b>Memorias por autor.</b> Un nivel superior de 58 memorias (una por autor) permitiría '
            'responder preguntas del tipo “¿qué autor escribe sobre…?” y acotar la búsqueda.',
            '<b>Uso del recuerdo.</b> La λ-reducción (recall) reconstruye un vector completo a partir '
            'del cue; podría decodificarse con el decodificador de SONAR para inspeccionar qué '
            '“recuerda” cada memoria.',
            '<b>Calibración del rechazo.</b> El umbral min_z se ajustó con 31 preguntas; con más '
            'datos podría calibrarse para una tasa de falsos rechazos objetivo.'])

# ------------------------------------------------------------------ referencias
story += [P('15. Referencias', 'h1')]
refs = [
    'Duquenne, P.-A., Schwenk, H. y Sagot, B. (2023). <i>SONAR: Sentence-Level Multimodal and '
    'Language-Agnostic Representations</i>. arXiv:2308.11466.',
    'Gao, Y. et al. (2024). <i>Retrieval-Augmented Generation for Large Language Models: A Survey</i>. '
    'arXiv:2312.10997.',
    'Lewis, P. et al. (2021). <i>Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks</i>. '
    'NeurIPS 2020; arXiv:2005.11401.',
    'Pineda, L. A., Fuentes, G. y Morales, R. (2021). <i>An entropic associative memory</i>. '
    'Scientific Reports, 11, 6948.',
    'Pineda, L. A. y Morales, R. (2022, en revisión). <i>Weighted Entropic Associative Memory: A Case '
    'Study on Phonetic Representation and Learning</i>. Código: repositorio eam-experiments/dimex.',
    'Pineda, L. A. et al. (2010). <i>The Corpus DIMEx100: Transcription and Evaluation</i>. '
    'Language Resources and Evaluation, 44, 347–370.',
    'Port de SONAR a HuggingFace: huggingface.co/cointegrated/SONAR_200_text_encoder.',
    'Corpus de textos: ciudadseva.com.',
]
story += [Paragraph(r, ParagraphStyle('ref', parent=base, leftIndent=18, firstLineIndent=-18,
                                      alignment=0, spaceAfter=5)) for r in refs]

doc = Doc(OUT, pagesize=letter, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
          topMargin=2 * cm, bottomMargin=2.2 * cm,
          title='RAG con Memorias Asociativas Entrópicas', author='Proyecto MAE2026 (IIMAS)',
          subject='Documentación técnica y manual de uso')
doc.multiBuild(story, onFirstPage=on_page, onLaterPages=on_page)
print('PDF:', OUT)
