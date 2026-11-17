"""Geometry-aware row reconstruction for lab PDFs.
Groups words by vertical position to rebuild visual table rows, which survives
the column-jumbling that linear text extraction causes on hospital templates."""
import sys, fitz

def rows_for_pdf(path, ytol=3.0):
    doc = fitz.open(path)
    all_rows = []
    for pno, page in enumerate(doc):
        words = page.get_text("words")  # x0,y0,x1,y1,word,block,line,wno
        words.sort(key=lambda w: (round(w[1]/ytol), w[0]))
        rows = []
        cur = []
        cur_y = None
        for w in words:
            y = w[1]
            if cur_y is None or abs(y - cur_y) <= ytol:
                cur.append(w); cur_y = y if cur_y is None else cur_y
            else:
                rows.append(cur); cur = [w]; cur_y = y
        if cur:
            rows.append(cur)
        for r in rows:
            r.sort(key=lambda w: w[0])
            text = " ".join(w[4] for w in r)
            xs = [(round(w[0]), w[4]) for w in r]
            all_rows.append((pno+1, round(r[0][1]), text, xs))
    doc.close()
    return all_rows

if __name__ == "__main__":
    path = sys.argv[1]
    for pno, y, text, xs in rows_for_pdf(path):
        print(f"[p{pno} y{y:4}] {text}")
