import unittest
from core.dataset.service import build_manifest, DatasetError

def item(wid,event,cls=0):
    return {"window":{"window_id":wid,"source_file":"capture.bin","source_event_id":event},
            "label":{"class_code":cls,"quality_review":"confirmed"}}

class DatasetServiceTests(unittest.TestCase):
    def test_group_split_never_leaks_events(self):
        items=[item(f"W{i}",ev,i%2) for ev in range(12) for i in range(2)]
        m=build_manifest(items,(.7,.15,.15),seed=7)
        sets=[{(x["source_file"],str(x["source_event_id"])) for x in m["splits"][p]}
              for p in ("train","validation","test")]
        self.assertFalse(sets[0]&sets[1]); self.assertFalse(sets[0]&sets[2]); self.assertFalse(sets[1]&sets[2])
        self.assertEqual(sum(len(m["splits"][p]) for p in ("train","validation","test")),len(items))
    def test_rejects_unconfirmed_labels(self):
        x=item("W1",1);x["label"]["quality_review"]="pending"
        with self.assertRaises(DatasetError): build_manifest([x])
    def test_rejects_missing_event_id(self):
        x=item("W1",1);x["window"]["source_event_id"]=None
        with self.assertRaises(DatasetError): build_manifest([x])
    def test_rejects_bad_ratios(self):
        with self.assertRaises(DatasetError): build_manifest([item("W1",1)],(.6,.2,.1))
if __name__=="__main__": unittest.main()
