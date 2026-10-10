; benchmark generated from python API
(set-info :status unknown)
(declare-fun service_time () Real)
(declare-fun admitted_0 () Bool)
(declare-fun completion_0 () Real)
(declare-fun last_completion_0 () Real)
(declare-fun late_0 () Bool)
(declare-fun admitted_1 () Bool)
(declare-fun completion_1 () Real)
(declare-fun last_completion_1 () Real)
(declare-fun late_1 () Bool)
(declare-fun failure_count () Int)
(assert
 (<= (/ 1.0 2.0) service_time))
(assert
 (>= (/ 3.0 4.0) service_time))
(assert
 (= admitted_0 (< 0 2)))
(assert
 (let ((?x63 (ite admitted_0 (+ (ite (> 0.0 0.0) 0.0 0.0) service_time) 0.0)))
 (= completion_0 ?x63)))
(assert
 (= last_completion_0 (ite admitted_0 completion_0 0.0)))
(assert
 (= late_0 (and admitted_0 (< 1.0 completion_0))))
(assert
 (let ((?x91 (+ (ite (and admitted_0 (< 0.0 completion_0)) 1 0))))
 (= admitted_1 (< ?x91 2))))
(assert
 (let ((?x182 (ite (< 0.0 last_completion_0) last_completion_0 0.0)))
 (= completion_1 (ite admitted_1 (+ ?x182 service_time) 0.0))))
(assert
 (= last_completion_1 (ite admitted_1 completion_1 last_completion_0)))
(assert
 (= late_1 (and admitted_1 (< 1.0 completion_1))))
(assert
 (let ((?x121 (ite (or (not admitted_1) late_1) 1 0)))
(= failure_count (+ (ite (or (not admitted_0) late_0) 1 0) ?x121))))
(check-sat)
