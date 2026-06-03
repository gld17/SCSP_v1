# AC-1 uv seespace environment record

Date: 2026-06-03

Environment path:

```bash
/share/guolidong-nfs/.venv/seespace
```

Commands run:

```bash
uv venv --python 3.12 /share/guolidong-nfs/.venv/seespace
source /share/guolidong-nfs/.venv/seespace/bin/activate
python3 --version
uv pip install -r stage/requirements.txt
uv pip install sympy pandas numpy 'protobuf>=4.21.0' graphviz tqdm networkx
python3 -c "import sympy, google.protobuf, tqdm, pandas; print('OK')"
python3 -c "import graphviz, numpy, networkx; print(graphviz.__version__)"
uv pip list
```

Notes:

- `uv pip install -r stage/requirements.txt` failed because `python-graphviz` is not a PyPI distribution name.
- Installed `graphviz==0.21`, the PyPI package that provides the Python Graphviz bindings.
- `stage/requirements.txt` was not modified.

Verification output:

```text
OK
```

Installed packages:

```text
graphviz        0.21
mpmath          1.3.0
networkx        3.6.1
numpy           2.4.6
pandas          3.0.3
protobuf        7.35.0
python-dateutil 2.9.0.post0
six             1.17.0
sympy           1.14.0
tqdm            4.67.3
```
