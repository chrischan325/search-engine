import pickle
import sys
from pathlib import Path
from datetime import datetime


# Document class
class Document:
    def __init__(self):
        self.docno = ""
        self.internal_id = ""
        self.doc_date = ""
        self.headline = ""
        self.raw_document = ""
        self.length = 0


# extract yyyy mm dd values separately to build path to find correct file based on given docno
def extract_date_directory(docno):
    # for the case of invalid docno id
    try:
        extracted_date = docno.split("-")[0][2:]
        new_date = datetime.strptime(extracted_date, "%m%d%y")
        format_date = datetime.strftime(new_date, "%Y/%m/%d")
        pathing = format_date.split("/")
        return pathing[0], pathing[1], pathing[2]
    except ValueError:
        print("invalid docno")
        return None, None, None


# given docno identifier, retrieve file from latimes-index directory
def extract_given_docno(doc_id, latimes_index_path):
    # if opening file fails, file may not exist
    try:
        year, month, day = extract_date_directory(doc_id)
        if year and month and day:
            # build file path by appending year month day values
            file_path = Path(str(latimes_index_path), year, month, day, doc_id + ".pickle")
            with open(file_path, "rb") as pickled_doc:
                doc = pickle.load(pickled_doc)
                return doc
    except FileNotFoundError:
        print("File not found")


# given internal id, go into index file and retrieve associated docno
def extract_given_internal_id(internal_id, latimes_index_path):
    index_file_path = Path(latimes_index_path, "document_index.pickle")

    with open(index_file_path, "rb") as index_doc:
        doc = pickle.load(index_doc)

    # for the case where id doesn't exist, error out, else get docno and use extract_given_docno for retrieval
    try:
        docno = doc[int(internal_id)]
        extract_given_docno(docno, latimes_index_path)
    except ValueError:
        print("invalid document id")


def main(argv):
    latimes_index_path = Path(argv[1])

    retrieve_val = argv[2]
    doc_id = argv[3]

    if retrieve_val == "docno":
        extract_given_docno(doc_id, latimes_index_path)
    elif retrieve_val == "id":
        extract_given_internal_id(doc_id, latimes_index_path)


if __name__ == "__main__":
    # validate there are enough input arguments
    if len(sys.argv) < 4:
        print("not enough arguments, GetDoc.py takes 3 arguments, the path to latimes-index, docno or id, and either "
              "internal id or the docno. \nFor example: python GetDoc.py /Users/christian/latimes-index id 13")
    # validate that latimes-index directory input exists
    elif not Path(sys.argv[1]).is_dir():
        print("not a valid directory")
    # validate if second argument is either acceptable value
    elif sys.argv[2] != "docno" and sys.argv[2] != "id":
        print("invalid input: either docno or id")
    else:
        main(sys.argv)
