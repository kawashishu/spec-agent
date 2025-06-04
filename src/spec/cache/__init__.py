import os
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from spec.config import *
from spec.models import Specbook
from spec.utils.notebook import Notebook
from spec.utils.s3 import S3Manager
from spec.utils.utils import load_txt

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"

SPECBOOK_DIR = DATA_DIR / "specbook"
PLM_DIR = DATA_DIR / "PLM"

SPECBOOK_MD_FOLDER = SPECBOOK_DIR / "specbook_md_xml"
# PART_IN_BOM_FILE = str(PLM_DIR / "parts_in_BOM.parquet")
PART_PARENT_CHILD_RELATIONSHIP_FILE = str(PLM_DIR / "part_parent_child_relationship.csv")
ALL_PARTS_IN_BOM_VECTOR_STORE_FILE = "PDF_search/vector_store/vinfast_part.pkl"  # AWS S3 bucket

def build_specbook_number_to_basenames(folder_path: str):
    # Build mapping from specbook number to list of basenames
    result = {}
    for filename in os.listdir(folder_path):
        full_path = os.path.join(folder_path, filename)
        if os.path.isfile(full_path):
            match = re.search(r'(VFD[A-Za-z0-9]+)', filename)
            if match:
                specbook_number = match.group(1)
                if specbook_number == "VFDSXVEEP9149":
                    continue
                basename = os.path.splitext(filename)[0]
                result.setdefault(specbook_number, []).append(basename)
    return result

TMPL = """
<Specbook>
<SpecbookNumber>{num}</SpecbookNumber>
<SpecbookFiles>
    {files}
</SpecbookFiles>
</Specbook>
"""

@dataclass
class Cache:
    BOM_df: pd.DataFrame
    specbooks: dict
    s3: S3Manager

@st.cache_resource(show_spinner=False)
def get_cache() -> Cache:
    s3 = S3Manager()
    BOM_df = pd.read_csv(PART_PARENT_CHILD_RELATIONSHIP_FILE)

    specbook_number_to_basenames = build_specbook_number_to_basenames(SPECBOOK_MD_FOLDER)

    specbooks: dict[str, Specbook] = {}
    for num, names in specbook_number_to_basenames.items():
        files = [load_txt(SPECBOOK_MD_FOLDER / f"{name}.txt") for name in names]
        xml = TMPL.format(num=num, files="\n".join(files))
        specbooks[num] = Specbook(specbook_number=num, content=xml)

    return Cache(
        BOM_df=BOM_df,
        specbooks=specbooks,
        s3=s3
    )

cache = get_cache()
BOM_df = cache.BOM_df
total_specbook = len(cache.specbooks)
notebook = Notebook(env=globals())