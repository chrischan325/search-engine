import sys
from pathlib import Path
import GetDoc
import math
import pickle
import re

from IndexEngine import tokenize
from nltk.stem import PorterStemmer


# Parameters
K1 = 1.2
b = 0.75
K2 = 7


class Document:
    def __init__(self):
        self.docno = ""
        self.internal_id = ""
        self.doc_date = ""
        self.headline = ""
        self.raw_document = ""
        self.length = 0


def tokenize(query):
    tokens = []

    string = query.lower()
    tokens.extend(re.findall(r'[\w]+', string))
    return tokens


def extract_query_info(query_number, query_string, file):  # make two lists that store topic number and query string
    for i, line in enumerate(file):
        if i % 2 == 0:
            query_number.append(line.strip())
        else:
            query_string.append(line)


def find_average_length(index_path, document_index):
    total = 0
    for docid, docno in document_index.items():
        total += GetDoc.extract_given_docno(docno, index_path).length
    return total/len(document_index)


def bm25_retrieval(topic_id, query, token_to_id, inv_index, document_index, average_length, index_path, stem):
    tokens = tokenize(query)
    N = len(document_index)
    scores = {}

    for token in tokens:
        tf_query = ((K2 + 1) * tokens.count(token)) / (K2 + tokens.count(token))

        if stem:
            ps = PorterStemmer()
            token = ps.stem(token)

        token_id = token_to_id[token]
        posting = inv_index[token_id]
        ni = len(posting[::2])
        term = (N - ni + 0.5) / (ni + 0.5)
        idf = math.log(term)

        for i in range(0, len(posting), 2):
            doc_id = posting[i]
            docno = document_index[doc_id]
            doc = GetDoc.extract_given_docno(docno, index_path)
            fi = posting[i + 1]
            K = K1 * ((1 - b) + b * (doc.length/average_length))

            tf_doc = ((K1 + 1) * fi)/(K + fi)
            score = tf_doc * tf_query * idf
            if docno in scores:
                scores[docno] += score
            else:
                scores[docno] = score

    print("Done: {}".format(topic_id))
    scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
    return scores


def main(argv):
    index_path = Path(argv[1])
    queries_path = Path(argv[2])
    stem = True if argv[4].lower() == "t" else False
    results_path = Path("BM25-baseline-results") if stem is False else Path("BM25-stem-results")

    if not results_path.is_dir():
        results_path.mkdir(parents=True, exist_ok=True)

    query_number = []
    query_string = []

    # open lexicon dictionaries
    with open(Path(index_path, "lexicon_token_to_id.pickle"), "rb") as token_to_id:
        token_to_id = pickle.load(token_to_id)

    # open document index file
    with open(Path(index_path, "document_index.pickle"), "rb") as doc_index:
        document_index = pickle.load(doc_index)

    # open inverted index file
    with open(Path(index_path, "inverse_index.pickle"), "rb") as doc_index:
        inv_index = pickle.load(doc_index)

    # get list of topic numbers and list of queries
    with open(queries_path, "rt") as file:
        extract_query_info(query_number, query_string, file)

    # get average length of documents
    average_length = find_average_length(index_path, document_index)
    print(average_length)

    with open(Path(results_path, "{}".format(argv[3])), 'w') as file:
        for idx, query in enumerate(query_string):
            res = bm25_retrieval(query_number[idx], query, token_to_id, inv_index, document_index, average_length, index_path, stem)

            i = 1
            for docno, score in res.items():
                if stem:
                    file.write("{} Q0 {} {} {} c267chan_stem\n".format(query_number[idx], docno, i, score))
                else:
                    file.write("{} Q0 {} {} {} c267chan_baseline\n".format(query_number[idx], docno, i, score))
                i += 1
                if i > 100:
                    break


if __name__ == "__main__":
    # validate there are correct number of arguments
    if len(sys.argv) < 5:
        print("invalid number of arguments, BM25.py takes 4 arguments")
    # validate if path for gz file is correct
    elif not Path(sys.argv[1]).exists():
        print("incorrect path to index folder")
    elif not Path(sys.argv[2]).exists():
        print("incorrect path to queries file")
    else:
        main(sys.argv)
