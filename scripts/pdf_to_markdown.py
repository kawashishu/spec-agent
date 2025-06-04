#!/usr/bin/env python3
# specbook_cli.py  (rút gọn, chỉ khác ở 2 nơi được đánh dấu ★)

from __future__ import annotations

import argparse
import asyncio
import base64
import concurrent.futures as cf
import io
import re
from pathlib import Path
from typing import Iterable, List

import cv2
import fitz
import numpy as np
from dotenv import load_dotenv
from PIL import Image

from spec.config import *
from spec.utils.llm import completion_with_backoff_response

# ── hằng số, prompt … ─────────────────────────────────────────────────────────
load_dotenv()
DEFAULT_MODEL, CTX_LIMIT = "gpt-4o", 10
SEM = asyncio.Semaphore(20)
PDF_PAGE_FORMAT_PROMPT = """
# Role and Objective
You are a skilled Document Structure Analyzer and Formatter. Your task is to precisely reformat raw text extracted from a PDF page to closely match the visual structure and formatting presented in an image screenshot of that same page.

# Instructions
## Analysis of Visual Structure
- Carefully examine the provided screenshot image to understand the visual layout, including:
  - Section or chapter titles
  - Paragraph breaks and indentation
  - Lists or bullet points
  - Tables
  - Figures, diagrams, or charts
- **Do not** include repetitive headers or footers from the page.

## Text Formatting
- Reorganize the provided raw text exactly as it appears (do NOT alter the original content) to match the structural organization seen in the image.
- Add formatting cues (paragraph breaks, lists, indentation, etc.) to match the visual layout.
- Exclude any repeated header or footer content.
- The reformatted content must **exclusively** contain the original raw text without adding, altering, or omitting any textual content beyond formatting adjustments and descriptive sentences for tables and figures as instructed.


## Special Formatting Instructions
- **Section or Chapter Titles:**
  - Clearly recognize titles from the image and rewrite them as complete sentences ending with a period.

- **Tables:**
  - Convert each row or record of the table into a sentence.
  - Each sentence should fully describe all values within that row clearly.

- **Figures, Charts, or Diagrams:**
  - Add a few concise yet informative sentences to briefly describe the content and purpose of the figure, chart, or diagram.

# Reasoning Steps
1. Inspect the image screenshot to clearly identify structural formatting elements.
2. Methodically map each section of the raw text to the identified visual structure.
3. Convert identified titles into clear sentences ending with periods.
4. Convert any table data into clearly descriptive sentences, one sentence per record.
5. Write clear and concise descriptions for figures, charts, or diagrams.
6. Remove repetitive header or footer text if present.

# Output Format
- Your output must **only** include the reformatted content of the **latest page**, clearly structured and segmented into:
  - Formatted text
  - Descriptive sentences for tables (if present)
  - Brief descriptions of figures, charts, or diagrams (if present)
- The entire content after reformatting **must** be enclosed within triple backticks followed by 'markdown':
```markdown
Your reformatted content here
```
- Do not include any additional explanations, commentary, instructions, or characters outside the reformatted content.

# Final instructions
Use the raw text exactly as provided. Match your formatting precisely to the visual structure of the image screenshot. Ensure absolutely no text beyond the reformatted content is included in the output. Think step by step and validate the completeness and clarity of your output.
"""

def encode_b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


def extract_num(s: str) -> int:
    m = re.search(r"\d+", s)
    return int(m.group()) if m else -1


# ── PDF → [(ảnh, text)] ────────────────────────────────────────────────────────
def pdf_to_assets(
    pdf: Path,
    out_dir: Path,
    *,
    dpi: int = 300,
    header: int = 0,
    footer: int = 0,
    thr: int = 240,
) -> List[tuple[Path, str]]:
    """
    Trả về danh sách (img_path, raw_text) cho từng trang PDF.
    Ảnh đã crop header/footer + viền trắng; raw_text lấy trực tiếp từ trang PDF.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    assets: list[tuple[Path, str]] = []

    with fitz.open(pdf) as doc:
        for i in range(doc.page_count):
            page = doc.load_page(i)
            page_text = page.get_text("text")  # raw text
            img = Image.open(io.BytesIO(page.get_pixmap(matrix=mat).tobytes("png")))

            # crop header/footer nếu có
            if header or footer:
                w, h = img.size
                img = img.crop((0, header, w, h - footer if footer < h else h))

            # auto-trim viền trắng
            g = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
            _, mask = cv2.threshold(g, thr, 255, cv2.THRESH_BINARY_INV)
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if cnts:
                pts = np.vstack(cnts).reshape(-1, 2)
                x_min, y_min = pts[:, 0].min(), pts[:, 1].min()
                x_max, y_max = pts[:, 0].max(), pts[:, 1].max()
                img = img.crop((x_min, y_min, x_max, y_max))

            img_path = out_dir / f"p{i + 1}.png"
            img.save(img_path)
            assets.append((img_path, page_text))
            
            print(f"Page {i+1}: size = {img.size}")

    return assets


# ── Gọi OpenAI (đồng bộ, nội bộ dùng asyncio.run) ─────────────────────────────
def llm_extract(assets: list[tuple[Path, str]], model: str) -> str:
    """
    Chạy lần lượt từng trang qua OpenAI và gom kết quả.
    Hàm đồng bộ; nội bộ dùng asyncio.run() để gọi hàm async acompletion_with_backoff.
    """
    msgs = [{"role": "system", "content": PDF_PAGE_FORMAT_PROMPT}]
    out_txt: list[str] = []

    for idx, (img, raw_text) in enumerate(assets, 1):
        msgs.append(
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": raw_text},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{encode_b64(img)}",
                    },
                ],
            }
        )

        # gọi hàm async → chạy đồng bộ
        rsp = completion_with_backoff_response(
            model=model,
            input=msgs,
        )
        
        output_text = rsp.output_text

        # Extract text inside ```markdown ... ``` if present, else keep raw text
        import re
        match = re.search(r"```markdown\s*([\s\S]*?)```", output_text, re.IGNORECASE)
        page_text = match.group(1).strip() if match else output_text

        out_txt.append(f"Page {idx}\n{page_text}")

        # cắt bối cảnh để không vượt CTX_LIMIT
        if len(msgs) > CTX_LIMIT:
            msgs = msgs[:1] + msgs[-(CTX_LIMIT - 1) :]

    return "\n".join(out_txt)


# ── Xử lý một PDF (đồng bộ) ────────────────────────────────────────────────────
def process_pdf(
    pdf: Path,
    md_dir: Path,
    img_tmp: Path,
    model: str,
    header: int,
    footer: int,
    dpi: int,
    overwrite: bool,
):
    print(f"Processing {pdf}")
    md_path = md_dir / f"{pdf.stem}.txt"
    if md_path.exists() and not overwrite:
        print(f"▲ Skip (đã có): {md_path}")
        return

    # Tạo thư mục cache ảnh riêng cho PDF
    asset_dir = img_tmp / pdf.stem
    assets = pdf_to_assets(pdf, asset_dir, dpi=dpi, header=header, footer=footer)

    # bảo đảm thứ tự trang
    assets.sort(key=lambda t: extract_num(t[0].name))

    md_content = llm_extract(assets, model=model)
    md_path.write_text(md_content, encoding="utf-8")
    print(f"✓ Saved: {md_path}")


# ── CLI ─────────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Extract markdown from PDF spec-books.")
    sub = p.add_subparsers(dest="cmd", required=True)

    ext = sub.add_parser("extract", help="Convert PDF(s) to markdown.")
    ext.add_argument("src", type=Path, help="PDF file hoặc thư mục.")
    ext.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("data/specbook/specbook_md_rewrite"),
        help="Thư mục lưu .txt",
    )
    ext.add_argument(
        "--tmp", type=Path, default=Path("data/specbook/specbook_imgs"), help="Cache ảnh"
    )
    ext.add_argument("--dpi", type=int, default=300)
    ext.add_argument("--header", type=int, default=300)
    ext.add_argument("--footer", type=int, default=300)
    ext.add_argument("--model", default=DEFAULT_MODEL)

    # ★ giữ nguyên flag -c / --continue
    ext.add_argument(
        "-c",
        "--continue",
        dest="cont",
        action="store_true",
        help="Bỏ qua PDF đã có file .txt (không ghi đè).",
    )

    # ★ thêm số luồng song song tuỳ chỉnh
    ext.add_argument(
        "-w",
        "--workers",
        type=int,
        default=4,
        help="Số luồng xử lý song song (mặc định 4).",
    )
    return p


def iter_pdfs(p: Path) -> Iterable[Path]:
    return p.rglob("*.pdf") if p.is_dir() else [p]


def main_extract(args):
    args.out.mkdir(parents=True, exist_ok=True)
    args.tmp.mkdir(parents=True, exist_ok=True)

    pdfs = list(iter_pdfs(args.src))
    print(f"Found {len(pdfs)} PDF(s).   (overwrite = {not args.cont})")

    # Dùng ThreadPoolExecutor để chạy đa luồng
    with cf.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                process_pdf,
                pdf,
                args.out,
                args.tmp,
                args.model,
                args.header,
                args.footer,
                args.dpi,
                overwrite=not args.cont,
            )
            for pdf in pdfs
        ]

        # đợi tất cả hoàn thành, lấy exception nếu có
        for f in cf.as_completed(futures):
            try:
                f.result()
            except Exception as exc:
                print(f"[ERROR] {exc}")


def main():
    args = build_parser().parse_args()
    if args.cmd == "extract":
        main_extract(args)


if __name__ == "__main__":
    main()