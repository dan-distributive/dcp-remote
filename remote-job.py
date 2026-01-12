# This is a sample Python script, searching for gene signatures that distinguish psoriatic arthritis from proriasis


import json
import pythonmonkey as pm
import dcp
dcp.init()
from dcp.range_object import RangeObject # see docs.dcp.dev/api/compute/classes/range-object.html
from dcp import wallet # see wallet API: docs.dcp.dev/api/wallet/index.html)

# Set an ID key: jobs will be owned and manageable with this key.
# wallet.get(<name>) looks in ~/.dcp for <name>.keystore
# Can also specify absolute path but must include the .keystore extension e.g. "/Users/dandesjardins/.dcp/default.keystore"
id = wallet.get("id").js_ref
dcp.identity.set(id)

# Add a payment key: compute credits will be withdrawn from this account to pay for jobs.
pay = wallet.get("default").js_ref
wallet.add(pay)

# define and use URL from JS via pythonmonkey until available within DCP API
def URL(url):
    return pm.eval('(x) => new URL(x)')(url)

# set URl for data server and results receiver
server_url = 'http://192.168.6.49:5001'

# work function arguments
n_signatures = 9
min_sig_length = 5
max_sig_length = 9
seed = 42
GSE57383_ps_psa = URL(f'{server_url}/GSE57383_ps_psa') # <<<<<< Bypasses Scheduler; workers fetch data directly from remote server


# INPUT SET
signature_range = RangeObject(1, n_signatures + 1, 1)

# WORK FUNCTION
def search_signatures(i, n_signatures, min_sig_length, max_sig_length, seed, GSE57383_ps_psa):
    """
    Randomly choose subsets of probesets and evaluate them as predictive signatures
    :param n_signatures: number of signatures to try
    :param min_sig_length: minimum length of signature
    :param max_sig_length: maximum length of signature
    :return:
    """
    dcp.progress()
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, BaggingClassifier
    from sklearn.svm import SVC
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.model_selection import cross_val_predict
    from sklearn import metrics
    import pandas as pd
    import random
    random.seed(i)
    from io import StringIO


    classifiers = {'LR' : LogisticRegression(max_iter=400, tol=1e-2),
                   'L1' : LogisticRegression(penalty='l1', solver='liblinear', max_iter=400, tol=1e-2),
                   'BA' : BaggingClassifier(n_estimators=100),
                   'RF' : RandomForestClassifier(n_estimators=100, random_state=41),
                   'SVM': SVC(probability=True),
                   'DT' : DecisionTreeClassifier()}

    d_df = pd.read_csv(StringIO(str(GSE57383_ps_psa)), delimiter="\t", header=0)
    x_df = d_df.iloc[:, 1:]
    y_s = np.multiply(d_df['phenotype'] == 'Psoriatic Arthritis', 1)
    probesets = sorted(x_df.columns)

    min_sig_length = max(min_sig_length, 1)
    max_sig_length = min(max_sig_length, len(probesets))

    k = round(n_signatures / (max_sig_length - min_sig_length + 1))
    sig_length = min(min_sig_length + (i // k) - 1, max_sig_length)
    probesets_sample = random.sample(probesets, sig_length)

    result_str = ""
    for classifier_name, classifier in classifiers.items():
        probs_a = cross_val_predict(classifier, x_df[probesets_sample], y_s, cv=10, method='predict_proba')
        auc = round(metrics.roc_auc_score(y_s, probs_a[:, 1]), 3)
        acc = round(metrics.accuracy_score(y_s, np.round(probs_a[:, 1])), 3)
        result_str += f"{acc}\t{classifier_name}\t{auc}\t{', '.join(probesets_sample)}\n"

    #if i % k == 0:
        #print(f"n signatures: {i}  signature length: {sig_length}")

    return result_str


# DCP job
job = dcp.compute_for(signature_range, search_signatures, [n_signatures, min_sig_length, max_sig_length, seed, GSE57383_ps_psa])

# DCP job config
job.modules = ['pandas', 'numpy', 'scikit-learn']
job.computeGroups = [{'joinKey': 'ibm', 'joinSecret': 'dcp'}]
job.setResultStorage(f'{server_url}/dcp-results', {'elementType': 'results'}) # <<<<<< Bypasses Scheduler; workers send results directly to remote server

# Publicly-viewable optional info
job.public.name = 'PsA sig search'
job.public.description = 'Analyzing gene subsets to identify biomarkers for psoriatic arthritis'
job.public.link = 'https://www.youtube.com/watch?v=p6Tf0guqqGw'

# configure events
job.on('readystatechange', lambda s: print(f"State: {s}"))
job.on('accepted', lambda _: print(f'  Job ID: {job.id}\n  Job accepted, awaiting results...'))
job.on('result', lambda res: print(f'    ✔ Slice {int(res.sliceNumber)}: {res.result}'))
job.on('error', lambda err: print(json.dumps(err, indent=4).replace('\\n', '\n')))
job.on('nofunds', lambda nof: print(json.dumps(nof, indent=4).replace('\\n', '\n')))

# execute job and wait for completion
job.exec()
job.wait()
print('Done.')
