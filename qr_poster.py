"""Cartaz vetorial do salão, em folha A4 com tamanho de corte definido."""
from io import BytesIO

import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth


def poster_pdf(link, restaurant_name, size="10x15"):
    if size != "10x15":
        raise ValueError("Formato inválido")
    output = BytesIO()
    page_w, page_h = 210 * mm, 297 * mm
    width, height = (100 * mm, 150 * mm)
    x, y = (page_w - width) / 2, (page_h - height) / 2
    c = canvas.Canvas(output, pagesize=(page_w, page_h))
    c.setTitle("Cardápio no salão - " + str(restaurant_name))
    c.setAuthor(str(restaurant_name))
    # O cartaz é centralizado numa folha A4, para imprimir em tamanho real e recortar.
    c.saveState()
    c.translate(x, y)
    scale = 1
    c.scale(scale, scale)
    w, h = width, height
    c.setFillColorRGB(0.063, 0.11, 0.196)
    c.roundRect(1 * mm, 1 * mm, w - 2 * mm, h - 2 * mm, 2 * mm, fill=1, stroke=0)

    def centered(text, baseline, font_size, color, font="Helvetica-Bold", max_width=88 * mm):
        while stringWidth(text, font, font_size) > max_width and font_size > 6:
            font_size -= 0.5
        c.setFillColor(color)
        c.setFont(font, font_size)
        c.drawCentredString(w / 2, baseline, text)

    from reportlab.lib.colors import HexColor
    white, orange = HexColor("#ffffff"), HexColor("#ffad53")
    name = " ".join(str(restaurant_name or "Restaurante").split())
    # Nome em destaque, ajustado para até duas linhas sem invadir a chamada.
    font_size = 25
    while True:
        lines, line = [], ""
        for word in name.split():
            candidate = (line + " " + word).strip()
            if line and stringWidth(candidate, "Helvetica-Bold", font_size) > 88 * mm:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        if len(lines) <= 2 or font_size <= 7:
            break
        font_size -= 0.5
    if len(lines) > 2:
        lines = [name]
    for i, line in enumerate(lines):
        centered(line, h - (17 + i * 10) * mm, font_size, white)

    centered("Escaneie e peça", h - 39 * mm, 18, orange)
    centered("pelo seu celular", h - 46 * mm, 14, orange)
    # 70 mm incluindo margem branca: mesmo a menor matriz ocupa mais de 50 mm.
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    qr_size = 70 * mm
    qx, qy = (w - qr_size) / 2, h - 121 * mm
    c.setFillColor(white)
    c.rect(qx, qy, qr_size, qr_size, fill=1, stroke=0)
    cell = qr_size / len(matrix)
    c.setFillColorRGB(0, 0, 0)
    path = c.beginPath()
    for row, values in enumerate(matrix):
        for col, black in enumerate(values):
            if black:
                path.rect(qx + col * cell, qy + (len(matrix) - row - 1) * cell, cell, cell)
    c.drawPath(path, fill=1, stroke=0)
    centered("APONTE A CÂMERA PARA O QR CODE", h - 128 * mm, 7, orange)
    centered("Escolha seus produtos e faça seu pedido.", h - 135 * mm, 8, white, "Helvetica")
    centered("Informe seu nome e o número da mesa.", h - 140 * mm, 8, white, "Helvetica")
    centered("Precisa de ajuda? Chame o garçom.", h - 146 * mm, 7, white, "Helvetica")
    c.restoreState()
    if size == "10x15":
        c.setStrokeColorRGB(0.55, 0.55, 0.55)
        c.setLineWidth(0.4)
        c.setDash(3, 3)
        c.rect(x, y, width, height, fill=0, stroke=1)
        c.setDash()
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.setFont("Helvetica", 9)
        c.drawCentredString(page_w / 2, y - 8 * mm, "Recorte na linha pontilhada: 10 x 15 cm.")
        c.drawCentredString(page_w / 2, y - 13 * mm, "Imprima em A4, tamanho real / escala 100%. Não ajustar à página.")
    c.showPage()
    c.save()
    return output.getvalue()
