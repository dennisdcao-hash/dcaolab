"""
Parse .bib files organized by career stage and produce data/publications.json
for Hugo to render on the publications page.

Usage:
    python scripts/parse_bib.py

Structure:
    bibs/
    ├── undergrad/   *.bib files from undergraduate work
    ├── graduate/    *.bib files from graduate work
    └── independent/ *.bib files from independent career

Drop new .bib files into the appropriate folder and re-run this script.
"""

import glob
import json
import os
import re

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BIB_DIR = os.path.join(PROJECT_ROOT, "bibs")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "data", "publications.json")

CATEGORIES = [
    {"key": "independent", "label": "Independent Career"},
    {"key": "graduate", "label": "Graduate Work"},
    {"key": "undergrad", "label": "Undergraduate Work"},
]


def clean_author(author_str):
    """Convert 'Last, First and Last, First' to 'F. Last, F. Last' format."""
    authors = author_str.split(" and ")
    formatted = []
    for author in authors:
        author = author.strip()
        if "," in author:
            parts = [p.strip() for p in author.split(",", 1)]
            last = parts[0]
            firsts = parts[1].split()
            initials = ". ".join(f[0] for f in firsts if f) + "."
            formatted.append(f"{initials} {last}")
        else:
            formatted.append(author)
    return ", ".join(formatted)


def clean_latex(text):
    """Remove common LaTeX markup from text."""
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\\textit\s*", "", text)
    text = re.sub(r"\\textbf\s*", "", text)
    text = re.sub(r"\\emph\s*", "", text)
    text = re.sub(r"~", " ", text)
    return text.strip()


def parse_bib_files(folder):
    """Parse all .bib files in a folder, return list of publication dicts."""
    bib_files = glob.glob(os.path.join(folder, "*.bib"))
    if not bib_files:
        return []

    entries = []
    for bib_file in bib_files:
        parser = BibTexParser(common_strings=True)
        with open(bib_file, encoding="utf-8") as f:
            db = bibtexparser.load(f, parser=parser)
        for entry in db.entries:
            venue = entry.get("journal", "") or entry.get("booktitle", "")
            entry_type = entry.get("ENTRYTYPE", "article")
            bib_key = entry.get("ID", "")

            # Check for TOC image (supports .png, .jpg, .gif, .webp)
            image = ""
            img_dir = os.path.join(PROJECT_ROOT, "static", "img", "pubs")
            for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                if os.path.exists(os.path.join(img_dir, bib_key + ext)):
                    image = f"/img/pubs/{bib_key}{ext}"
                    break

            # Normalize page ranges: replace -- with single dash
            pages = entry.get("pages", "").replace("--", "–")

            pub = {
                "key": bib_key,
                "title": clean_latex(entry.get("title", "")),
                "author": clean_author(entry.get("author", "")),
                "journal": clean_latex(venue),
                "year": entry.get("year", ""),
                "volume": entry.get("volume", ""),
                "pages": pages,
                "doi": entry.get("doi", ""),
                "type": entry_type,
                "publisher": clean_latex(entry.get("publisher", "")),
                "abstract": clean_latex(entry.get("abstract", "")),
                "image": image,
                "source_file": os.path.basename(bib_file),
            }
            entries.append(pub)

    # Sort by year descending (newest first for display), but #1 = oldest paper
    entries.sort(key=lambda e: (-(int(e["year"]) if e["year"].isdigit() else 0), e["author"]))

    return entries


def main():
    output = {}
    total = 0

    for cat in CATEGORIES:
        folder = os.path.join(BIB_DIR, cat["key"])
        entries = parse_bib_files(folder)
        output[cat["key"]] = {
            "label": cat["label"],
            "entries": entries,
        }
        total += len(entries)
        print(f"  {cat['label']}: {len(entries)} entries")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nTotal: {total} entries -> {OUTPUT_FILE}")

    # Print image status for each entry
    print("\nImage status (save TOC graphics to static/img/pubs/<key>.png):")
    for cat in CATEGORIES:
        section = output[cat["key"]]
        if section["entries"]:
            print(f"\n  {section['label']}:")
            for e in section["entries"]:
                status = "HAS IMAGE" if e["image"] else "no image"
                print(f"    {status}  {e['key']}")


if __name__ == "__main__":
    main()
