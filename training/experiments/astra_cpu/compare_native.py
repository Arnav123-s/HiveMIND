"""Compare the final original and blocked-CE adapters numerically from saved safetensors."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from safetensors import safe_open


def compare(original, candidate):
    start = "grow/t80+astrastudy.start.safetensors"
    after = "grow/t80+astrastudy/adapter_model.safetensors"
    metrics=dict(squared_delta=0.,squared_old_update=0.,squared_new_update=0.,dot_updates=0.,max_abs_delta=0.,
                 changed_values=0,values=0,tensors=0)
    with (safe_open(original/start,framework="np") as a0,safe_open(candidate/start,framework="np") as b0,
          safe_open(original/after,framework="np") as a1,safe_open(candidate/after,framework="np") as b1):
        assert set(a0.keys())==set(b0.keys())==set(a1.keys())==set(b1.keys())
        for key in a0.keys():
            w=a0.get_tensor(key).astype(np.float64)
            assert np.array_equal(a0.get_tensor(key),b0.get_tensor(key)),key
            a=a1.get_tensor(key).astype(np.float64)
            b=b1.get_tensor(key).astype(np.float64)
            old_update,new_update=a-w,b-w
            delta=a-b
            metrics["squared_delta"]+=float(np.sum(delta*delta))
            metrics["squared_old_update"]+=float(np.sum(old_update*old_update))
            metrics["squared_new_update"]+=float(np.sum(new_update*new_update))
            metrics["dot_updates"]+=float(np.sum(old_update*new_update))
            metrics["max_abs_delta"]=max(metrics["max_abs_delta"],float(np.max(np.abs(delta))))
            metrics["changed_values"]+=int(np.count_nonzero(delta))
            metrics["values"]+=int(delta.size);metrics["tensors"]+=1
    metrics["relative_difference_in_updates"]=math.sqrt(metrics["squared_delta"]/metrics["squared_old_update"])
    metrics["update_cosine"]=metrics["dot_updates"]/math.sqrt(metrics["squared_old_update"]*metrics["squared_new_update"])
    return metrics


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original",type=Path);p.add_argument("candidate",type=Path)
    print(json.dumps(compare(**vars(p.parse_args())),indent=2))
