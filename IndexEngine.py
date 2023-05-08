import gzip
import sys
from pathlib import Path
import re
from datetime import datetime
import pickle
from nltk.stem import PorterStemmer

# Global dictionaries
lexicon_token_to_id = {}  # dictionary mapping a string to an integer
lexicon_id_to_token = {}  # dictionary mapping a integer to string
inv_index = {}  # dictionary mapping token id to postings array which contains doc id and count


# Helper function for removing html tags
def remove_html_tags(string):
    # use regex to strip tags
    formatted_line = re.compile('<.*?>')
    return re.sub(formatted_line, '', string).strip()


# Helper function to extract date from docno
def extract_date(docno, for_directory=False):
    extracted_date = docno.split("-")[0][2:]
    new_date = datetime.strptime(extracted_date, "%m%d%y")
    # use yyyy/mm/dd format to help with directory creation
    if for_directory:
        return datetime.strftime(new_date, "%Y/%m/%d")
    return datetime.strftime(new_date, "%B %d, %Y")


def regex_metadata_retrieval(document):
    raw_doc = document.raw_document
    regex_head = "<HEADLINE>[\s\S]+</HEADLINE>"
    regex_text = "<TEXT>[\s\S]+</TEXT>"
    regex_graphic = "<GRAPHIC>[\s\S]+</GRAPHIC>"

    headline = re.findall(regex_head, raw_doc)
    text = re.findall(regex_text, raw_doc)
    graphic = re.findall(regex_graphic, raw_doc)

    document.headline = remove_html_tags(headline[0]) if headline else ""
    document.text = remove_html_tags(text[0]) if text else ""
    document.graphic = remove_html_tags(graphic[0]) if graphic else ""


def tokenize(document, stem):
    tokens = []
    ps = PorterStemmer()

    for line in document.headline, document.text, document.graphic:
        line = line.lower()
        formatted_text = re.findall(r'[\w]+', line)
        if stem:
            for token in formatted_text:
                token = ps.stem(token)
                tokens.append(token)
        else:
            tokens.extend(formatted_text)
    return tokens


def convert_tokens_to_ids(tokens):
    token_ids = []

    for token in tokens:
        if token in lexicon_token_to_id:
            token_ids.append(lexicon_token_to_id[token])
        else:
            token_id = len(lexicon_token_to_id)
            lexicon_token_to_id[token] = token_id
            lexicon_id_to_token[token_id] = token
            token_ids.append(token_id)

    return token_ids


def count_words(token_ids):
    word_counts = {}

    for token_id in token_ids:
        if token_id in word_counts:
            word_counts[token_id] += 1
        else:
            word_counts[token_id] = 1

    return word_counts


def add_to_postings(word_counts, doc_id):
    for token_id in word_counts:
        count = word_counts[token_id]
        if token_id in inv_index:
            postings = inv_index[token_id]
            postings.append(doc_id)
            postings.append(count)
        else:
            inv_index[token_id] = [doc_id, count]


def inv_index_builder(internal_id, document, stem):
    tokens = tokenize(document, stem)
    document.length = len(tokens)

    token_ids = convert_tokens_to_ids(tokens)  # list of token ids
    word_counts = count_words(token_ids)  # a dictionary that maps token id to the count
    add_to_postings(word_counts, internal_id)


# Helper function to create document in the path inputted with the extracted meta data
def processing_and_document(document, directory_path, internal_id, stem):
    # retrieve headline, text and graphic content
    regex_metadata_retrieval(document)

    # build inverted index
    inv_index_builder(internal_id, document, stem)

    p = Path(directory_path, extract_date(document.docno, for_directory=True))
    p.mkdir(parents=True, exist_ok=True)
    new_file = Path(p, document.docno + ".pickle")
    with open(new_file, "wb") as doc:
        pickle.dump(document, doc)
        print("processed document ", document.internal_id)


# document class to store metadata
class Document:
    def __init__(self):
        self.docno = ""
        self.internal_id = ""
        self.doc_date = ""
        self.headline = ""
        self.graphic = ""
        self.text = ""
        self.raw_document = ""
        self.length = 0


# Helper function to extract meta data from gz file
def extract_metadata(file, directory_path, stem):
    line_arr = []
    doc_map = {}
    doc_count = 0

    # iterate through each line
    for line in file:
        line_arr.append(line)

        # <DOC> tag indicates start of new document so create a new instance of Document
        if "<DOC>" in line:
            doc_count += 1
            new_doc = Document()
        # extract docno by removing html tags and extract date from it as well for creating the directory
        elif "<DOCNO>" in line:
            new_doc.docno = remove_html_tags(line)
            new_doc.doc_date = extract_date(new_doc.docno)
        elif "</DOC>" in line:
            new_doc.raw_document = ''.join(line_arr)
            line_arr.clear()
            new_doc.internal_id = doc_count

            # send Document object to be processed
            processing_and_document(new_doc, directory_path, doc_count, stem)
            # keep a dictionary mapping internal id to docno for fetching purposes
            doc_map[doc_count] = new_doc.docno

    index_file_path = Path(directory_path, "document_index.pickle")
    # pickle the index file
    with open(index_file_path, "wb") as index_file:
        pickle.dump(doc_map, index_file)

    inv_index_file_path = Path(directory_path, "inverse_index.pickle")
    token_to_id_path = Path(directory_path, "lexicon_token_to_id.pickle")
    id_to_token_path = Path(directory_path, "lexicon_id_to_token.pickle")

    # pickle the inverse index and both lexicon dictionaries to the directory
    with open(inv_index_file_path, "wb") as inv_index_file:
        pickle.dump(inv_index, inv_index_file)

    with open(token_to_id_path, "wb") as token_to_id_file:
        pickle.dump(lexicon_token_to_id, token_to_id_file)

    with open(id_to_token_path, "wb") as id_to_token_file:
        pickle.dump(lexicon_id_to_token, id_to_token_file)


def main(argv):
    latimes_gz_path = Path(argv[1])
    directory_path = Path(argv[2])
    stem = True if argv[3].lower() == "t" else False

    # validate if directory currently exists
    if directory_path.is_dir():
        print("error: directory already exists")
    else:
        # create the directory based off of given input
        directory_path.mkdir(parents=True, exist_ok=True)

        # open file and send off for metadata extraction
        with gzip.open(latimes_gz_path, mode='rt') as file:
            extract_metadata(file, directory_path, stem)


if __name__ == "__main__":
    # validate there are correct number of arguments
    if len(sys.argv) < 4:
        print("invalid number of arguments, IndexEngine.py takes 2 arguments: "
              "file path of latimes.gz file and the path to create the desired directory. \n"
              "ex: python IndexEngine.py /Users/christian/latimes.gz /Users/christian/latimes-index")
    # validate if path for gz file is correct
    elif not Path(sys.argv[1]).exists():
        print("incorrect path to latimes.gz file")
    else:
        main(sys.argv)
