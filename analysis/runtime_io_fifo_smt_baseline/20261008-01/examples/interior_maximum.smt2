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
(declare-fun admitted_2 () Bool)
(declare-fun completion_2 () Real)
(declare-fun last_completion_2 () Real)
(declare-fun late_2 () Bool)
(declare-fun admitted_3 () Bool)
(declare-fun completion_3 () Real)
(declare-fun last_completion_3 () Real)
(declare-fun late_3 () Bool)
(declare-fun failure_count () Int)
(assert
 (<= (/ 1.0 2.0) service_time))
(assert
 (>= 1.0 service_time))
(assert
 (= admitted_0 (< 0 2)))
(assert
 (let ((?x54 (ite admitted_0 (+ (ite (> 0.0 0.0) 0.0 0.0) service_time) 0.0)))
 (= completion_0 ?x54)))
(assert
 (= last_completion_0 (ite admitted_0 completion_0 0.0)))
(assert
 (= late_0 (and admitted_0 (< (/ 11.0 10.0) completion_0))))
(assert
 (let ((?x76 (+ (ite (and admitted_0 (< 0.0 completion_0)) 1 0))))
 (= admitted_1 (< ?x76 2))))
(assert
 (let ((?x78 (ite (< 0.0 last_completion_0) last_completion_0 0.0)))
 (= completion_1 (ite admitted_1 (+ ?x78 service_time) 0.0))))
(assert
 (= last_completion_1 (ite admitted_1 completion_1 last_completion_0)))
(assert
 (= late_1 (and admitted_1 (< (/ 11.0 10.0) completion_1))))
(assert
 (let ((?x116 (+ (ite (and admitted_0 (< (/ 19.0 20.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 19.0 20.0) completion_1)) 1 0))))
 (= admitted_2 (< ?x116 2))))
(assert
 (let ((?x118 (ite (< (/ 19.0 20.0) last_completion_1) last_completion_1 (/ 19.0 20.0))))
 (= completion_2 (ite admitted_2 (+ ?x118 service_time) 0.0))))
(assert
 (= last_completion_2 (ite admitted_2 completion_2 last_completion_1)))
(assert
 (= late_2 (and admitted_2 (< (/ 41.0 20.0) completion_2))))
(assert
 (let ((?x165 (+ (ite (and admitted_0 (< (/ 39.0 20.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 39.0 20.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 39.0 20.0) completion_2)) 1 0))))
 (= admitted_3 (< ?x165 2))))
(assert
 (let ((?x167 (ite (< (/ 39.0 20.0) last_completion_2) last_completion_2 (/ 39.0 20.0))))
 (= completion_3 (ite admitted_3 (+ ?x167 service_time) 0.0))))
(assert
 (= last_completion_3 (ite admitted_3 completion_3 last_completion_2)))
(assert
 (= late_3 (and admitted_3 (< (/ 61.0 20.0) completion_3))))
(assert
 (let ((?x220 (+ (ite (or (not admitted_0) late_0) 1 0) (ite (or (not admitted_1) late_1) 1 0) (ite (or (not admitted_2) late_2) 1 0) (ite (or (not admitted_3) late_3) 1 0))))
(= failure_count ?x220)))
(check-sat)
