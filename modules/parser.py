import re, httpx, base64
from modules.ai_helper import ask_ai_json

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


async def ocr_image_bytes(image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post("https://api.ocr.space/parse/image",
                data={"apikey": "helloworld",
                      "base64Image": f"data:image/jpeg;base64,{b64}",
                      "language": "eng", "isTable": True, "scale": True,
                      "OCREngine": 2})
            res = r.json()
            if res.get("ParsedResults"):
                return res["ParsedResults"][0]["ParsedText"]
    except Exception as e:
        print(f"[OCR] {e}")
    return ""


def extract_pdf_text(pdf_bytes: bytes) -> str:
    if not HAS_FITZ:
        return ""
    try:
        doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "".join(page.get_text() for page in doc)
        return text[:20000]
    except Exception as e:
        print(f"[PDF] {e}")
        return ""


async def parse_pyq_sheet(raw_text: str, exam: str, subject: str,
                           source: str, exam_year: str = None,
                           lang: str = "en") -> list:
    """
    AI-powered PYQ extraction from raw text.
    Preserves exam_source, exam_year metadata.
    """
    year_hint = f"Year: {exam_year}" if exam_year else "Extract year from content if visible"

    prompt = f"""Extract ALL MCQ questions from this Previous Year Question paper/sheet.

Exam: {exam}
Subject: {subject}  
Source: {source}
{year_hint}
Language: {lang}

RAW TEXT:
{raw_text[:10000]}

Return a JSON ARRAY. Each question object MUST have:
{{
  "question": "complete question text",
  "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
  "answer": "A/B/C/D",
  "explanation": "why this answer is correct",
  "short_method": "shortcut trick for maths/reasoning or null",
  "subject": "{subject}",
  "section": "infer topic (e.g. Percentage/Polity/Mechanics)",
  "exam": "{exam}",
  "exam_source": "{source}",
  "exam_year": "{exam_year or 'Unknown'}",
  "difficulty": "Easy/Medium/Hard",
  "is_pyq": true,
  "source": "{source}",
  "lang": "{lang}"
}}

Rules:
- Extract ALL questions, do not skip any
- If answer key not given, make educated guess based on options
- Preserve exact question wording
- Return [] if no MCQ questions found"""

    try:
        result = await ask_ai_json(prompt)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for v in result.values():
                if isinstance(v, list):
                    return v
    except Exception as e:
        print(f"[Parser] Failed: {e}")
    return []


async def process_owner_upload(file_bytes: bytes, file_type: str,
                                exam: str, subject: str, source: str,
                                exam_year: str = None, lang: str = "en") -> list:
    raw_text = ""
    if file_type == "pdf":
        raw_text = extract_pdf_text(file_bytes)
    elif file_type == "image":
        raw_text = await ocr_image_bytes(file_bytes)
    elif file_type == "txt":
        raw_text = file_bytes.decode("utf-8", errors="ignore")

    if not raw_text.strip():
        return []

    return await parse_pyq_sheet(raw_text, exam, subject, source, exam_year, lang)
