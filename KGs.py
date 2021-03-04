import KG
import prase_core as pc


class KGs:
    default_lite_align_prob = 0.99

    def __init__(self, kg1: KG, kg2: KG, se_module=None, **kwargs):
        self.kg1 = kg1
        self.kg2 = kg2

        self.pr = pc.PRModule(kg1.kg_core, kg2.kg_core)
        self.se = None

        if se_module is not None:
            self.se = se_module(self, **kwargs)

    def _align_literals(self):
        for (lite_id, lite_name) in self.kg1.lite_id_name_dict.items():
            if self.kg2.name_lite_id_dict.__contains__(lite_name):
                lite_cp_id = self.kg2.name_lite_id_dict[lite_name]
                self.pr.update_lite_eqv(lite_id, lite_cp_id, KGs.default_lite_align_prob, False)
                self.pr.update_lite_eqv(lite_cp_id, lite_id, KGs.default_lite_align_prob, False)

    def init(self, align_lite=True):
        self.pr.init()
        if align_lite:
            self._align_literals()

    def run_pr(self):
        self.pr.run()

    def run_se(self, mapping_feedback=True, embedding_feedback=True, **kwargs):
        if self.se is not None:
            self.se.init()
            self.se.train()
            self.se.feed_back_to_pr_module(mapping_feedback, embedding_feedback, **kwargs)

    def get_entity_nums(self):
        return len(self.kg1.get_ent_id_set()) + len(self.kg2.get_ent_id_set())

    def get_attribute_nums(self):
        return len(self.kg1.get_attr_id_set()) + len(self.kg2.get_attr_id_set())

    def insert_forced_ent_eqv_both_way_by_name(self, ent_name, ent_cp_name, prob):
        ent_id = self.kg1.get_ent_id_by_name(ent_name)
        ent_cp_id = self.kg2.get_ent_id_by_name(ent_cp_name)
        if ent_id is None or ent_cp_id is None:
            print("fail to get ent ids")
            return
        self.pr.update_ent_eqv(ent_id, ent_cp_id, prob, True)
        self.pr.update_ent_eqv(ent_cp_id, ent_id, prob, True)

    def insert_ent_eqv_both_way_by_name(self, ent_name, ent_cp_name, prob):
        ent_id = self.kg1.get_ent_id_by_name(ent_name)
        ent_cp_id = self.kg2.get_ent_id_by_name(ent_cp_name)
        if ent_id is None or ent_cp_id is None:
            print("fail to get ent ids")
            return
        self.pr.update_ent_eqv(ent_id, ent_cp_id, prob, False)
        self.pr.update_ent_eqv(ent_cp_id, ent_id, prob, False)

    def insert_ent_eqv_both_way_by_id(self, ent_id, ent_cp_id, prob):
        if ent_id is None or ent_cp_id is None:
            print("fail to get ent ids")
            return
        self.pr.update_ent_eqv(ent_id, ent_cp_id, prob, False)
        self.pr.update_ent_eqv(ent_cp_id, ent_id, prob, False)

    def remove_forced_ent_eqv_by_id(self, idx_a, idx_b):
        return self.pr.remove_forced_eqv(idx_a, idx_b)

    def get_kg1_unaligned_candidate_ids(self):
        return self.pr.get_kg_a_unaligned_ents()

    def get_kg2_unaligned_candidate_ids(self):
        return self.pr.get_kg_b_unaligned_ents()

    def clear_kgs_ent_embed(self):
        self.kg1.clear_ent_embed()
        self.kg2.clear_ent_embed()
        self.pr.reset_emb_eqv()

    def get_ent_align_ids_result(self):
        return self.pr.get_ent_eqv_result()

    def get_rel_align_ids_result(self):
        sub_align_result, sup_align_result = set(), set()
        for (rel_id, rel_cp_id, prob) in self.pr.get_rel_eqv_result():
            if rel_id in self.kg1.rel_inv_dict:
                sub_align_result.add((rel_id, rel_cp_id, prob))
            elif rel_id in self.kg2.rel_inv_dict:
                sup_align_result.add((rel_cp_id, rel_id, prob))
        return sub_align_result, sup_align_result

    def get_ent_align_name_result(self):
        ent_align_eqv_set = set()
        for (ent_id, ent_cp_id, prob) in self.pr.get_ent_eqv_result():
            ent_name, ent_cp_name,  = self.kg1.get_ent_name_by_id(ent_id), self.kg2.get_ent_name_by_id(ent_cp_id)
            ent_align_eqv_set.add((ent_name, ent_cp_name, prob))
        return ent_align_eqv_set

    def get_rel_align_name_result(self):
        sub_align_result, sup_align_result = set(), set()
        for (rel_id, rel_cp_id, prob) in self.pr.get_rel_eqv_result():
            if rel_id in self.kg1.rel_inv_dict:
                rel_name, rel_cp_name = self.kg1.get_rel_name_by_id(rel_id), self.kg2.get_rel_name_by_id(rel_cp_id)
                sub_align_result.add((rel_name, rel_cp_name, prob))
            elif rel_id in self.kg2.rel_inv_dict:
                rel_name, rel_cp_name = self.kg2.get_rel_name_by_id(rel_id), self.kg1.get_rel_name_by_id(rel_cp_id)
                sup_align_result.add((rel_cp_name, rel_name, prob))
        return sub_align_result, sup_align_result

    def print_result(self):
        for item in self.pr.get_ent_eqv_result():
            print(item)

    def test(self, test_path, threshold=0.0):
        gold_result = set()
        with open(test_path, "r", encoding="utf8") as f:
            for line in f.readlines():
                params = str.strip(line).split("\t")
                ent_l, ent_r = params[0].strip(), params[1].strip()
                obj_l, obj_r = self.kg1.get_ent_id_by_name(ent_l), self.kg2.get_ent_id_by_name(ent_r)
                if obj_l is None:
                    print("Exception: fail to load Entity (" + ent_l + ")")
                if obj_r is None:
                    print("Exception: fail to load Entity (" + ent_r + ")")
                if obj_l is None or obj_r is None:
                    continue
                gold_result.add((obj_l, obj_r))

        threshold_list = []
        if isinstance(threshold, float) or isinstance(threshold, int):
            threshold_list.append(float(threshold))
        else:
            threshold_list = threshold

        for threshold_item in threshold_list:
            ent_align_result = set()
            for (ent_id, counterpart_id, prob) in self.pr.get_ent_eqv_result():
                if prob > threshold_item:
                    ent_align_result.add((ent_id, counterpart_id))

            correct_num = len(gold_result & ent_align_result)
            predict_num = len(ent_align_result)
            total_num = len(gold_result)

            if predict_num == 0:
                print("Threshold: " + format(threshold_item, ".3f") + "\tException: no satisfied alignment result")
                continue

            if total_num == 0:
                print("Threshold: " + format(threshold_item, ".3f") + "\tException: no satisfied instance for testing")
            else:
                precision, recall = correct_num / predict_num, correct_num / total_num
                if precision <= 0.0 or recall <= 0.0:
                    print("Threshold: " + format(threshold_item, ".3f") + "\tPrecision: " + format(precision, ".6f") +
                          "\tRecall: " + format(recall, ".6f") + "\tF1-Score: Nan")
                else:
                    f1_score = 2.0 * precision * recall / (precision + recall)
                    print("Threshold: " + format(threshold_item, ".3f") + "\tPrecision: " + format(precision, ".6f") +
                          "\tRecall: " + format(recall, ".6f") + "\tF1-Score: " + format(f1_score, ".6f"))
