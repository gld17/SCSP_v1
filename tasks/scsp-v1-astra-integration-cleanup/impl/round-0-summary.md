# Round 0 Implementation Summary

## Files Modified
1. scsp/models.py
2. scsp/config.py
3. scsp/astra_sim_bridge.py
4. web/index.html
5. README-astra-integration.md

## AC Implementation Status
- AC-1: Implemented — legacy fields removed from models.py and astra_sim_bridge.py; archived in README.
- AC-2: Implemented — frontend KPI uses astra fields; bottleneck_stage derived from gpu_time_ns/comm_time_ns.
- AC-3: Implemented — mock fallback with explicit toast and dev-only guard.
- AC-4: Implemented — config aligned with stage CLI; direct parameter passing; model_type from registry.
- AC-5: Implemented — py_compile passes; run_scsp.py --help OK; run_web.py --help OK; web_api imports OK.

## Blockers/Issues
None.

## Verification Commands
```bash
cd /share/guolidong-nfs/SeeSpace/SCSP_v1
git diff --stat
python3 -m py_compile scsp/*.py
python3 run_scsp.py --help
python3 run_web.py --help
/share/guolidong-nfs/.venv/seespace/bin/python3 -c "from scsp.web_api import app; print('OK')"
```
