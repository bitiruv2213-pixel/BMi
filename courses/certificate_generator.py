from io import BytesIO

from django.conf import settings


class CertificateGenerator:
    """
    Lightweight PDF generator without external binary dependencies.
    """

    def __init__(self, certificate, theme="classic"):
        self.certificate = certificate
        self.site_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")
        self.theme = theme if theme in {"classic", "royal", "modern"} else "classic"

    def generate(self):
        w, h = 842, 595  # A4 landscape in points
        cx = w / 2
        palette = self._palette()

        student_name = self._safe_text(
            self.certificate.student.get_full_name() or self.certificate.student.username
        )
        teacher_name = self._safe_text(
            self.certificate.course.teacher.get_full_name() or self.certificate.course.teacher.username
        )
        course_title = self._safe_text(self.certificate.course.title)
        if len(course_title) > 72:
            course_title = f"{course_title[:69]}..."

        date_str = self.certificate.issued_at.strftime("%d.%m.%Y")
        cert_no = self._safe_text(self.certificate.certificate_number)
        verify_url = self._safe_text(f"{self.site_url}/certificates/verify/{cert_no}/")

        # Styled PDF drawing commands
        stream = "\n".join(
            [
                # Background
                f"{palette['bg']} rg",
                f"0 0 {w} {h} re f",
                # Top/Bottom bands
                f"{palette['band']} rg",
                f"0 {h-36} {w} 36 re f",
                f"0 0 {w} 36 re f",
                # Double border
                f"{palette['border1']} RG 2.2 w",
                f"28 28 {w-56} {h-56} re S",
                f"{palette['border2']} RG 0.8 w",
                f"40 40 {w-80} {h-80} re S",
                # Watermark
                "q",
                f"{palette['watermark']} rg",
                "BT /F1 80 Tf 305 300 Td (LMS) Tj ET",
                "Q",
                # Title
                f"{palette['title']} rg",
                "BT /F2 40 Tf 282 495 Td (SERTIFIKAT) Tj ET",
                f"{palette['subtitle']} rg",
                "BT /F1 14 Tf 286 474 Td (CERTIFICATE OF COMPLETION) Tj ET",
                # Intro line
                f"{palette['text']} rg",
                "BT /F1 14 Tf 262 435 Td (Ushbu sertifikat quyidagiga topshiriladi:) Tj ET",
                # Student name
                f"{palette['name']} rg",
                f"BT /F2 34 Tf {max(100, cx - (len(student_name) * 7.2)):.1f} 390 Td ({self._esc(student_name)}) Tj ET",
                # Name underline
                f"{palette['accent']} RG 1.2 w",
                f"{cx-170:.1f} 377 m {cx+170:.1f} 377 l S",
                # Course intro
                f"{palette['text']} rg",
                "BT /F1 14 Tf 208 350 Td (quyidagi kursni muvaffaqiyatli yakunlagani uchun:) Tj ET",
                # Course title
                f"{palette['course']} rg",
                f"BT /F2 24 Tf {max(80, cx - (len(course_title) * 4.9)):.1f} 320 Td ({self._esc(course_title)}) Tj ET",
                # Meta card
                f"{palette['card']} rg",
                f"150 255 {w-300} 52 re f",
                f"{palette['text']} rg",
                f"BT /F1 12 Tf 305 286 Td (Oqituvchi: {self._esc(teacher_name)}) Tj ET",
                f"BT /F1 12 Tf 335 268 Td (Darslar soni: {self.certificate.course.total_lessons} ta) Tj ET",
                # Left info
                f"{palette['text']} rg",
                f"BT /F1 10 Tf 62 120 Td (Berilgan sana: {date_str}) Tj ET",
                f"BT /F1 10 Tf 62 104 Td (Sertifikat raqami: {self._esc(cert_no)}) Tj ET",
                # Signature lines
                f"{palette['sigline']} RG 0.9 w",
                "120 88 m 300 88 l S",
                "542 88 m 722 88 l S",
                f"{palette['sigtext']} rg",
                "BT /F3 13 Tf 170 96 Td (LMS Admin) Tj ET",
                f"BT /F3 13 Tf 570 96 Td ({self._esc(teacher_name[:20])}) Tj ET",
                "BT /F1 10 Tf 160 72 Td (Platforma mamuriyati) Tj ET",
                "BT /F1 10 Tf 605 72 Td (Instruktor) Tj ET",
                # Footer
                f"{palette['title']} rg",
                "BT /F2 13 Tf 368 50 Td (LMS Platform) Tj ET",
                f"{palette['subtitle']} rg",
                f"BT /F1 9 Tf 182 32 Td (Tasdiqlash: {self._esc(verify_url)}) Tj ET",
            ]
        ).encode("latin-1", errors="replace")

        return self._build_pdf(stream)

    def _build_pdf(self, stream_bytes):
        objects = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] "
            b"/Resources << /Font << /F1 5 0 R /F2 6 0 R /F3 7 0 R >> >> "
            b"/Contents 4 0 R >>"
        )
        objects.append(
            b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n" + stream_bytes + b"\nendstream"
        )
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>")

        pdf = BytesIO()
        pdf.write(b"%PDF-1.4\n")
        offsets = [0]

        for idx, obj in enumerate(objects, start=1):
            offsets.append(pdf.tell())
            pdf.write(f"{idx} 0 obj\n".encode("ascii"))
            pdf.write(obj)
            pdf.write(b"\nendobj\n")

        xref_pos = pdf.tell()
        pdf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.write(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            pdf.write(f"{off:010d} 00000 n \n".encode("ascii"))

        trailer = (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_pos}\n"
            "%%EOF"
        )
        pdf.write(trailer.encode("ascii"))
        pdf.seek(0)
        return pdf

    @staticmethod
    def _safe_text(value):
        # Keep text compatible with standard PDF Type1 fonts.
        if not value:
            return ""
        return (
            str(value)
            .replace("'", "")
            .replace('"', "")
            .replace("\n", " ")
            .replace("\r", " ")
        )

    @staticmethod
    def _esc(text):
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _palette(self):
        palettes = {
            "classic": {
                "bg": "0.98 0.96 0.91",
                "band": "0.91 0.86 0.73",
                "border1": "0.63 0.50 0.20",
                "border2": "0.78 0.66 0.34",
                "watermark": "0.93 0.90 0.82",
                "title": "0.18 0.15 0.10",
                "subtitle": "0.40 0.34 0.21",
                "text": "0.31 0.26 0.16",
                "name": "0.12 0.10 0.06",
                "accent": "0.67 0.54 0.24",
                "course": "0.48 0.36 0.10",
                "card": "0.95 0.92 0.84",
                "sigline": "0.72 0.63 0.43",
                "sigtext": "0.45 0.38 0.23",
            },
            "royal": {
                "bg": "0.94 0.96 1.00",
                "band": "0.79 0.86 0.98",
                "border1": "0.14 0.27 0.55",
                "border2": "0.28 0.42 0.74",
                "watermark": "0.86 0.90 0.98",
                "title": "0.10 0.20 0.42",
                "subtitle": "0.18 0.31 0.58",
                "text": "0.16 0.26 0.45",
                "name": "0.06 0.12 0.25",
                "accent": "0.25 0.43 0.75",
                "course": "0.13 0.30 0.58",
                "card": "0.90 0.94 1.00",
                "sigline": "0.44 0.56 0.80",
                "sigtext": "0.22 0.33 0.56",
            },
            "modern": {
                "bg": "0.95 0.98 0.96",
                "band": "0.84 0.93 0.88",
                "border1": "0.10 0.35 0.24",
                "border2": "0.21 0.50 0.36",
                "watermark": "0.88 0.94 0.90",
                "title": "0.07 0.26 0.19",
                "subtitle": "0.14 0.39 0.29",
                "text": "0.13 0.31 0.24",
                "name": "0.05 0.17 0.12",
                "accent": "0.20 0.49 0.36",
                "course": "0.09 0.35 0.25",
                "card": "0.90 0.96 0.92",
                "sigline": "0.43 0.65 0.55",
                "sigtext": "0.19 0.39 0.30",
            },
        }
        return palettes[self.theme]
