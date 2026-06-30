import camelot

tables = camelot.read_pdf("file.pdf", pages="all", flavor="stream")

df = tables[0].df
df.to_excel("output.xlsx", index=False)