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
 (<= 1.0 service_time))
(assert
 (>= (/ 6.0 5.0) service_time))
(assert
 (= admitted_0 (< 0 2)))
(assert
 (let ((?x10 (ite admitted_0 (+ (ite (> 0.0 0.0) 0.0 0.0) service_time) 0.0)))
 (= completion_0 ?x10)))
(assert
 (= last_completion_0 (ite admitted_0 completion_0 0.0)))
(assert
 (= late_0 (and admitted_0 (< (/ 13.0 10.0) completion_0))))
(assert
 (let ((?x125 (+ (ite (and admitted_0 (< 0.0 completion_0)) 1 0))))
 (= admitted_1 (< ?x125 2))))
(assert
 (let ((?x118 (ite (< 0.0 last_completion_0) last_completion_0 0.0)))
 (= completion_1 (ite admitted_1 (+ ?x118 service_time) 0.0))))
(assert
 (= last_completion_1 (ite admitted_1 completion_1 last_completion_0)))
(assert
 (= late_1 (and admitted_1 (< (/ 13.0 10.0) completion_1))))
(assert
 (let ((?x53 (+ (ite (and admitted_0 (< (/ 21.0 20.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 21.0 20.0) completion_1)) 1 0))))
 (= admitted_2 (< ?x53 2))))
(assert
 (let ((?x55 (ite (< (/ 21.0 20.0) last_completion_1) last_completion_1 (/ 21.0 20.0))))
 (= completion_2 (ite admitted_2 (+ ?x55 service_time) 0.0))))
(assert
 (= last_completion_2 (ite admitted_2 completion_2 last_completion_1)))
(assert
 (= late_2 (and admitted_2 (< (/ 47.0 20.0) completion_2))))
(assert
 (let ((?x62 (+ (ite (and admitted_0 (< (/ 21.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 21.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 21.0 10.0) completion_2)) 1 0))))
 (= admitted_3 (< ?x62 2))))
(assert
 (let ((?x105 (ite (< (/ 21.0 10.0) last_completion_2) last_completion_2 (/ 21.0 10.0))))
 (= completion_3 (ite admitted_3 (+ ?x105 service_time) 0.0))))
(assert
 (= last_completion_3 (ite admitted_3 completion_3 last_completion_2)))
(assert
 (= late_3 (and admitted_3 (< (/ 17.0 5.0) completion_3))))
(assert
 (let ((?x154 (ite (or (not admitted_3) late_3) 1 0)))
(let ((?x136 (ite (or (not admitted_2) late_2) 1 0)))
(let ((?x206 (ite (or (not admitted_0) late_0) 1 0)))
(= failure_count (+ ?x206 (ite (or (not admitted_1) late_1) 1 0) ?x136 ?x154))))))
(check-sat)
