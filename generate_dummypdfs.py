from fpdf import FPDF
import os

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.multi_cell(0, 10, "Algebra Notes\n\nThis is a sample resource for testing the student dashboard.\n- Topic 1: Equations\n- Topic 2: Inequalities\n- Topic 3: Quadratic formulas")
pdf.output(os.path.join(UPLOAD_DIR, "algebra.pdf"))