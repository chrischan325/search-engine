import csv
import sys
from pathlib import Path
from parsers import ResultsParser, QrelsParser, ResultsParseError
import math
import GetDoc


# Document class
class Document:
    def __init__(self):
        self.docno = ""
        self.internal_id = ""
        self.doc_date = ""
        self.headline = ""
        self.raw_document = ""
        self.length = 0


def average_precision(qrels, results):
    avg_precision_dict = {}
    query_ids = qrels.get_query_ids()

    for id in query_ids:
        rank, precisions_acc = 0, 0
        topic_results = results.get_result(id)
        num_rel = len(qrels.query_2_reldoc_nos[id])

        if topic_results:
            topic_results.sort(key=lambda x: x.score, reverse=True)

            for idx, res in enumerate(topic_results):
                if qrels.get_relevance(id, res.doc_id) > 0:
                    rank += 1
                    score = float(rank/(idx + 1))
                    precisions_acc += score
            avg_precision_dict[id] = precisions_acc/float(num_rel)
        else:
            avg_precision_dict[id] = float(0)

    avg_precision = sorted(avg_precision_dict.items())
    return avg_precision


def precision_at_10(qrels, results):
    precision_at_10_dict = {}
    query_ids = qrels.get_query_ids()

    for id in query_ids:
        relevant_doc_count = 0
        topic_results = results.get_result(id)

        if topic_results:
            topic_results.sort(key=lambda x: x.score, reverse=True)

            for res in topic_results[:10]:
                if qrels.get_relevance(id, res.doc_id) > 0:
                    relevant_doc_count += 1
            precision_at_10_dict[id] = float(relevant_doc_count/10)
        else:
            precision_at_10_dict[id] = float(0)

    precision_at_10 = sorted(precision_at_10_dict.items())
    return precision_at_10


def ndcg_at_10(qrels, results):
    ndcg_at_10_dict = {}
    query_ids = qrels.get_query_ids()

    for id in query_ids:
        dcg, idcg = 0, 0
        topic_results = results.get_result(id)

        if topic_results:
            topic_results.sort(key=lambda x: x.score, reverse=True)

            for idx, res in enumerate(topic_results, start=1):
                if qrels.get_relevance(id, res.doc_id) > 0:
                    dcg += (qrels.get_relevance(id, res.doc_id)/math.log2(idx + 1))

                if idx == 10:
                    for j in range(1, min(len(qrels.query_2_reldoc_nos[id]) + 1, 11)):
                        idcg += (1 / math.log2(j + 1))
                    ndcg_at_10_dict[id] = dcg/idcg
                    break
        else:
            ndcg_at_10_dict[id] = float(0)


    ndcg_at_10 = sorted(ndcg_at_10_dict.items())
    return ndcg_at_10


def ndcg_at_1000(qrels, results):
    ndcg_at_1000_dict = {}
    query_ids = qrels.get_query_ids()

    for id in query_ids:
        dcg, idcg = 0, 0
        topic_results = results.get_result(id)

        if topic_results:
            topic_results.sort(key=lambda x: x.score, reverse=True)

            for idx, res in enumerate(topic_results, start=1):
                if qrels.get_relevance(id, res.doc_id) > 0:
                    dcg += (qrels.get_relevance(id, res.doc_id)/math.log2(idx + 1))

                if idx == min(1000, len(topic_results)):
                    num_rel = len(qrels.query_2_reldoc_nos[id]) if len(qrels.query_2_reldoc_nos[id]) != 0 else 1
                    for j in range(1, min(num_rel + 1, 1001)):
                        idcg += (1 / math.log2(j + 1))
                    ndcg_at_1000_dict[id] = dcg/idcg
                    break
        else:
            ndcg_at_1000_dict[id] = float(0)
    ndcg_at_1000 = sorted(ndcg_at_1000_dict.items())
    return ndcg_at_1000


def time_based_gain(qrels, results):
    time_based_gain_dict = {}
    query_ids = qrels.get_query_ids()

    for id in query_ids:
        tbg, tk, prev_tk = 0, 0, 0
        topic_results = results.get_result(id)

        if topic_results:
            topic_results.sort(key=lambda x: x.score, reverse=True)

            for idx, res in enumerate(topic_results, start=1):
                print(res.doc_id)
                doc = GetDoc.extract_given_docno(res.doc_id, '../latimes-index-stem')
                if not doc:
                    raise FileNotFoundError("Docno doesn't exist")

                if qrels.get_relevance(id, res.doc_id) > 0:
                    prev_tk += 4.4 + ((0.018 * doc.length) + 7.8) * 0.64
                    tbg += math.exp(-tk * (math.log(2)/224)) * 0.4928
                    tk += prev_tk
                    prev_tk = 0
                else:
                    tk += 4.4 + (0.018 * doc.length + 7.8) * 0.39
                time_based_gain_dict[id] = tbg

        else:
            time_based_gain_dict[id] = float(0)

    time_based_gain = sorted(time_based_gain_dict.items())
    return time_based_gain


def all_measures(qrels, results_file_path):
    csv_path = Path("result-csv-files")
    if not csv_path.is_dir():
        csv_path.mkdir(parents=True, exist_ok=True)
    measures = {}

    if not results_file_path.is_file():
        return "File Does Not Exist"

    try:
        results = ResultsParser(Path(results_file_path)).parse()
        measures["average precision"] = average_precision(qrels, results[1])
        measures["precision at 10"] = precision_at_10(qrels, results[1])
        measures["ndcg at 10"] = ndcg_at_10(qrels, results[1])
        measures["ndcg at 1000"] = ndcg_at_1000(qrels, results[1])
        measures["time based gain"] = time_based_gain(qrels, results[1])

        with open(Path(csv_path, "{}.csv".format(results_file_path.stem.split('.')[0])), "w") as csvfile:
            columns = ["measure type", "topic number", "value"]
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()

            for measure_type, measure in measures.items():
                for topic_id, value in measure:
                    writer.writerow({"measure type": measure_type, "topic number": topic_id, "value": value})

    except(ResultsParseError, FileNotFoundError, ValueError) as e:
        print(e)
        print("bad format for file: {}".format(results_file_path.name))
        with open(Path(csv_path, "{}.csv".format(results_file_path.stem.split('.')[0])), "w") as csvfile:
            columns = ["measure type", "topic number", "value"]
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            writer.writerow({"measure type": "bad format", "topic number": "bad format", "value": "bad format"})


def main(argv):
    qrels_path = Path(argv[1])
    qrels = QrelsParser(qrels_path).parse()
    results_file_path = Path(argv[2])
    all_measures(qrels, results_file_path)


if __name__ == "__main__":
    # validate there are correct number of arguments
    if len(sys.argv) < 2:
        print("invalid number of arguments")
    # validate if path for qrel file is correct
    elif not Path(sys.argv[1]).exists():
        print("incorrect path to qrels file")
    else:
        main(sys.argv)