# DCP Python Job with remote data
This project demonstrates how to write and deploy distributed computing job on the Distributive Compute Platform (DCP) using:

* Main job script (`remote-job.py`)
* Data server and results sink (`server.py`)
* Browser or Standalone [DCP Workers](https://distributive.network/)

This example illustrates the complete end-to-end workflow for distributed ensemble modelling using remote data and results. Normally, job data is sent from the job client to the workers via the DCP Scheduler. By using remote data and results, the workers bypass the scheduler and can fetch data from user-specified allowed origins, and can push results to user-specified allowed origins.


## Overview

This repository is designed as a tutorial rather than a production-ready system. The code is intended to be clear and easy to understand, allowing developers to modify it as needed. Many configuration values are hard-coded (compute group join credentials, slice payment offer, etc.), but they can be adapted or turned into command prompts for more advanced/secure useage.

If you encounter any issues or have questions, you can reach the team via:

* Email: info@distributive.network
* Slack: [DCP Developers Slack](https://join.slack.com/t/dcp-devs/shared_invite/zt-56v87qj7-fkqZOXFUls8rNzO4mxHaIA)

## Requirements

* Node.js
* Python
* pip packages:
  * dcp
  * pythonmonkey
* DCP keystore files in the home directory:
```
~/.dcp/id.keystore
~/.dcp/default.keystore
```
To obtain keystore files, contact: dan@dcp.dev

## Running the Example

**1. Launch the data and results server:**
```
python3 server.py
```
You should see output similar to:
```
dandesjardins@Dans-MacBook-Air-2 remote % python3 server.py
 * Serving data on: http://122.148.6.59:5001
 * DCP results endpoint: http://122.148.6.59:5001/dcp-results
 * Serving Flask app 'server'
 * Debug mode: off
```

**2. Configure the job to use your server:**

Copy the URL from the server output, for example `http://122.148.6.59:5001`, and paste it into **line 26** of `remote-job.py`. This tells the workers where to fetch data and where to push results, useful for restricting sensitive data movements entirely **behind your firewall**.
```
server_url = 'http://122.148.6.59:5001'
```
Also edit **line 99** to specify your compute group:
```
job.computeGroups = [{'joinKey': '<key>', 'joinSecret': '<secret>'}]
```

**3. Configure Worker Allowed Origins**

Workers must be configured with the appropriate allowed origins.
By default, and for security reasons, workers only communicate with the public scheduler: `https://scheduler.distributed.computer`. To fetch input data from and submit results to your own server, you must explicitly allow additional origins.

How this is configured depends on the worker type.

**Docker Worker**

Documentation: [distributive.network/docs/worker-docker.pdf](https://distributive.network/docs/worker-docker.pdf)

Launch the worker with `--allow-origin`, along with your account and compute group credentials:
```
docker run -it \
  --earnings-account=<account> \
  --no-global \
  --join <key>,<secret> \
  --allow-origin <url:port>
```
* Replace `<account>` with your DCP earnings account number.
* Replace `<key>,<secret>` with your compute group join key and join secret.
* `<url:port>` should point to your data and results server.

**Linux Worker**

Documentation: [distributive.network/docs/worker-linux.pdf](https://distributive.network/docs/worker-linux.pdf)

If the worker is already installed, launch it with:
```
sudo --user=dcp /opt/dcp/bin/dcp-worker.sh \
  --earnings-account=<account> \
  --no-global \
  --join <key>,<secret> \
  --allow-origin <url:port>
```
The same credential and origin requirements apply as with the Docker worker.

**Browser worker**

Documentation: [distributive.network/docs/worker-browser.pdf](https://distributive.network/docs/worker-browser.pdf)

Open the following URL, replacing `key` with your compute group join key:
```
https://dcp.work/key
```
Enter the join secret when prompted.

Open the browser developer console and run:
```
dcpWorker.originManager.add('<url:port>', null, null);
```
**Mixed Content Warning (Browser Workers)**

By default, browsers block HTTP requests from HTTPS pages (“mixed content”).
If your server is using HTTP (common for local testing), you must explicitly allow it.

**Chrome steps:**

* Go to https://dcp.work
* Click the lock icon next to the URL.
* Select Site settings.
* Scroll to Insecure content and set it to Allow.
* Reload the page.

> **Important:**
> This configuration is unsafe for production environments but acceptable for local or internal testing.


**4. Launch the job:**
```
python3 remote-job.py
```
In your job client terminal, you should see:

```
State: exec
State: init
State: preauth
State: deploying
State: listeners
State: compute-groups
State: uploading
State: deployed
  Job ID: jCTpufKzW0ps0qifz6xZdX
  Job accepted, awaiting results...
    ✔ Slice 1: Result received
    ✔ Slice 2: Result received
    ✔ Slice 3: Result received
    ✔ Slice 4: Result received
    ✔ Slice 5: Result received
    ✔ Slice 6: Result received
    ✔ Slice 7: Result received
    ✔ Slice 8: Result received
    ✔ Slice 9: Result received
    ✔ Slice 10: Result received
Done.
```


## Project Structure
```
.
├── remote-job.py                             # Main job script
├── server.py.                                # data and results server
├── input/
│   └── GSE57383_ps_psa.txt                   # genomics dataset
└── results/
    └── GSE57383_PsA_vs_Ps_120126_214426.txt  # timestamped results file

```


## Configuration
The following parameters can be modified:

| Parameter        | Location            | Description                                        |
| ---------------- | ------------------- | -------------------------------------------------- |
| n_signatures     | `remote-job.py`     | number of signatures to test/compute               |
| computeGroups    | `job.computeGroups` | Set join key and join secret                       |
| name, description, and link | `job.public` | Publicly viwable information about your job    |
|slicePaymentOffer | `job.exec`          | How many compute credits offered per job slice     |
| id keystore      | `wallet.get`        | Specify which keystore file to use as identity     |
| account keystore | `wallet.get`        | Specify which keystore file to use to pay for job  |


## Extending the Example

This structure is very useful in enterprise, banking, and healthcare, for example, where data is not allowed to leave the building. This example can be extended to use:
* remote work functions
* remote input sets
* remote results
* federated clusters computing on local networks and aggregating results globally

The pattern remains:

```
job = compute_for(input_set, work_function, arguments)
job.exec()
results = job.wait()
```

*Happy computing*
