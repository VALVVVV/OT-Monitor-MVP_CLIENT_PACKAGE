import json

with open("data/mchs_documents_filtered.json", "r", encoding="utf-8") as f:
    d = json.load(f)

print("Всего:", len(d))
print("PDF:", sum(1 for x in d if x.get("url", "").lower().endswith(".pdf")))
print("DOC/DOCX:", sum(1 for x in d if x.get("url", "").lower().endswith((".doc", ".docx"))))
print("XLS/XLSX:", sum(1 for x in d if x.get("url", "").lower().endswith((".xls", ".xlsx"))))
print("Страницы:", sum(1 for x in d if "/dokumenty/vse-dokumenty/" in x.get("url", "")))
print("Название Скачать:", sum(1 for x in d if x.get("title", "").strip().lower() == "скачать"))
