# Replaces cooking units & terms with unicode symbols, optionally removing newlines from OCR scans
def replace(text, replist):
    # execute replacements in the provided text
    for r in replist:
        text = text.replace(r[0], r[1])
    return text


def remove_newlines(text):
    # fixes the newlines added to the end of each line by OCR readers
    text = text.replace('-\n', '')  # join hyphenated words wrapped between lines
    text = text.replace('\n\n', '%^&*||*&^%')
    text = text.replace('\n', ' ')
    text = text.replace('%^&*||*&^%', '\n\n')
    return text


# define filenames
rfile = "replacements.txt"
ifile = "input.txt"
ofile = "output.txt"
replist = []

# fix the newlines added by OCR data entry?
ocr = input("Fix OCR newlines? ")
if ocr in('Y', 'y', '1', 'Yes', 'yes'):
    ocr = True
else:
    ocr = False

# read the replacements file, store as a list of tuples
with open(rfile) as f:
    for line in f:
        line = line.strip("\n")
        tup = line.split(",")  # list is comma-delimited
        replist.append([tup[0], tup[1]])

# read & process the input
with open(ifile) as f:
    data = f.read()
    if ocr:
        output = replace(remove_newlines(data), replist)
    else:
        output = replace(data, replist)

# write the output
with open(ofile, 'w') as o: o.write(output)

print("Output file:", ofile)
print("")
