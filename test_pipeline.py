import os
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from PIL import Image
import fitz  # PyMuPDF for PDF reading
from openai import OpenAI

# Set up OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---- CONFIG ----
MODEL = "gpt-4o-mini"  # cheap summarizer
USD_TO_INR = 84.0      # conversion rate (approx)
COST_PER_M_TOKENS = 0.15  # $ per 1M tokens for GPT-4o-mini

# ---- STEP 1: OCR ----
def extract_text(file_path):
    text = ""
    if file_path.lower().endswith(".pdf"):
        doc = fitz.open(file_path)
        for page in doc:
            pix = page.get_pixmap()  # convert PDF page to image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text += pytesseract.image_to_string(img, lang="eng") + "\n"
    else:
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img, lang="eng")
    return text.strip()

# ---- STEP 2: Summarize with GPT-4o-mini ----
def summarize_text(text):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a summarizer that produces clear, concise academic-style summaries."},
            {"role": "user", "content": text}
        ]
    )
    summary = response.choices[0].message.content

    # Token usage info
    tokens_used = response.usage.total_tokens
    cost_usd = (tokens_used / 1_000_000) * COST_PER_M_TOKENS
    cost_inr = cost_usd * USD_TO_INR

    return summary, tokens_used, cost_inr

# ---- MAIN TEST ----
if __name__ == "__main__":
    file_path = "sample.pdf"  # <-- replace with your file (PDF or image)

    print("Extracting text via OCR...")
    text = extract_text(file_path)

    print("Summarizing with GPT-4o-mini...")
    summary, tokens, cost_inr = summarize_text(text)

    print("\n===== SUMMARY =====")
    print(summary)

    print("\n===== COST ESTIMATION =====")
    print(f"Tokens used: {tokens}")
    print(f"Estimated Cost: ₹{cost_inr:.2f} per submission")
