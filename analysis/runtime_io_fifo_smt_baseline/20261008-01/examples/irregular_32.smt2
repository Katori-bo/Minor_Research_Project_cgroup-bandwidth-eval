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
(declare-fun admitted_4 () Bool)
(declare-fun completion_4 () Real)
(declare-fun last_completion_4 () Real)
(declare-fun late_4 () Bool)
(declare-fun admitted_5 () Bool)
(declare-fun completion_5 () Real)
(declare-fun last_completion_5 () Real)
(declare-fun late_5 () Bool)
(declare-fun admitted_6 () Bool)
(declare-fun completion_6 () Real)
(declare-fun last_completion_6 () Real)
(declare-fun late_6 () Bool)
(declare-fun admitted_7 () Bool)
(declare-fun completion_7 () Real)
(declare-fun last_completion_7 () Real)
(declare-fun late_7 () Bool)
(declare-fun admitted_8 () Bool)
(declare-fun completion_8 () Real)
(declare-fun last_completion_8 () Real)
(declare-fun late_8 () Bool)
(declare-fun admitted_9 () Bool)
(declare-fun completion_9 () Real)
(declare-fun last_completion_9 () Real)
(declare-fun late_9 () Bool)
(declare-fun admitted_10 () Bool)
(declare-fun completion_10 () Real)
(declare-fun last_completion_10 () Real)
(declare-fun late_10 () Bool)
(declare-fun admitted_11 () Bool)
(declare-fun completion_11 () Real)
(declare-fun last_completion_11 () Real)
(declare-fun late_11 () Bool)
(declare-fun admitted_12 () Bool)
(declare-fun completion_12 () Real)
(declare-fun last_completion_12 () Real)
(declare-fun late_12 () Bool)
(declare-fun admitted_13 () Bool)
(declare-fun completion_13 () Real)
(declare-fun last_completion_13 () Real)
(declare-fun late_13 () Bool)
(declare-fun admitted_14 () Bool)
(declare-fun completion_14 () Real)
(declare-fun last_completion_14 () Real)
(declare-fun late_14 () Bool)
(declare-fun admitted_15 () Bool)
(declare-fun completion_15 () Real)
(declare-fun last_completion_15 () Real)
(declare-fun late_15 () Bool)
(declare-fun admitted_16 () Bool)
(declare-fun completion_16 () Real)
(declare-fun last_completion_16 () Real)
(declare-fun late_16 () Bool)
(declare-fun admitted_17 () Bool)
(declare-fun completion_17 () Real)
(declare-fun last_completion_17 () Real)
(declare-fun late_17 () Bool)
(declare-fun admitted_18 () Bool)
(declare-fun completion_18 () Real)
(declare-fun last_completion_18 () Real)
(declare-fun late_18 () Bool)
(declare-fun admitted_19 () Bool)
(declare-fun completion_19 () Real)
(declare-fun last_completion_19 () Real)
(declare-fun late_19 () Bool)
(declare-fun admitted_20 () Bool)
(declare-fun completion_20 () Real)
(declare-fun last_completion_20 () Real)
(declare-fun late_20 () Bool)
(declare-fun admitted_21 () Bool)
(declare-fun completion_21 () Real)
(declare-fun last_completion_21 () Real)
(declare-fun late_21 () Bool)
(declare-fun admitted_22 () Bool)
(declare-fun completion_22 () Real)
(declare-fun last_completion_22 () Real)
(declare-fun late_22 () Bool)
(declare-fun admitted_23 () Bool)
(declare-fun completion_23 () Real)
(declare-fun last_completion_23 () Real)
(declare-fun late_23 () Bool)
(declare-fun admitted_24 () Bool)
(declare-fun completion_24 () Real)
(declare-fun last_completion_24 () Real)
(declare-fun late_24 () Bool)
(declare-fun admitted_25 () Bool)
(declare-fun completion_25 () Real)
(declare-fun last_completion_25 () Real)
(declare-fun late_25 () Bool)
(declare-fun admitted_26 () Bool)
(declare-fun completion_26 () Real)
(declare-fun last_completion_26 () Real)
(declare-fun late_26 () Bool)
(declare-fun admitted_27 () Bool)
(declare-fun completion_27 () Real)
(declare-fun last_completion_27 () Real)
(declare-fun late_27 () Bool)
(declare-fun admitted_28 () Bool)
(declare-fun completion_28 () Real)
(declare-fun last_completion_28 () Real)
(declare-fun late_28 () Bool)
(declare-fun admitted_29 () Bool)
(declare-fun completion_29 () Real)
(declare-fun last_completion_29 () Real)
(declare-fun late_29 () Bool)
(declare-fun admitted_30 () Bool)
(declare-fun completion_30 () Real)
(declare-fun last_completion_30 () Real)
(declare-fun late_30 () Bool)
(declare-fun admitted_31 () Bool)
(declare-fun completion_31 () Real)
(declare-fun last_completion_31 () Real)
(declare-fun late_31 () Bool)
(declare-fun failure_count () Int)
(assert
 (<= (/ 1.0 4.0) service_time))
(assert
 (>= 2.0 service_time))
(assert
 (= admitted_0 (< 0 3)))
(assert
 (let ((?x4510 (ite admitted_0 (+ (ite (> 0.0 (/ 1.0 2.0)) 0.0 (/ 1.0 2.0)) service_time) 0.0)))
 (= completion_0 ?x4510)))
(assert
 (= last_completion_0 (ite admitted_0 completion_0 0.0)))
(assert
 (= late_0 (and admitted_0 (< (/ 7.0 4.0) completion_0))))
(assert
 (let ((?x4532 (+ (ite (and admitted_0 (< (/ 1.0 2.0) completion_0)) 1 0))))
 (= admitted_1 (< ?x4532 3))))
(assert
 (let ((?x4534 (ite (< (/ 1.0 2.0) last_completion_0) last_completion_0 (/ 1.0 2.0))))
 (= completion_1 (ite admitted_1 (+ ?x4534 service_time) 0.0))))
(assert
 (= last_completion_1 (ite admitted_1 completion_1 last_completion_0)))
(assert
 (= late_1 (and admitted_1 (< (/ 7.0 4.0) completion_1))))
(assert
 (let ((?x4572 (+ (ite (and admitted_0 (< (/ 9.0 5.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 9.0 5.0) completion_1)) 1 0))))
 (= admitted_2 (< ?x4572 3))))
(assert
 (let ((?x4574 (ite (< (/ 9.0 5.0) last_completion_1) last_completion_1 (/ 9.0 5.0))))
 (= completion_2 (ite admitted_2 (+ ?x4574 service_time) 0.0))))
(assert
 (= last_completion_2 (ite admitted_2 completion_2 last_completion_1)))
(assert
 (= late_2 (and admitted_2 (< (/ 61.0 20.0) completion_2))))
(assert
 (let ((?x4268 (+ (ite (and admitted_0 (< (/ 23.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 23.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 23.0 10.0) completion_2)) 1 0))))
 (= admitted_3 (< ?x4268 3))))
(assert
 (let ((?x4270 (ite (< (/ 23.0 10.0) last_completion_2) last_completion_2 (/ 23.0 10.0))))
 (= completion_3 (ite admitted_3 (+ ?x4270 service_time) 0.0))))
(assert
 (= last_completion_3 (ite admitted_3 completion_3 last_completion_2)))
(assert
 (= late_3 (and admitted_3 (< (/ 71.0 20.0) completion_3))))
(assert
 (let ((?x4324 (+ (ite (and admitted_0 (< (/ 27.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 27.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 27.0 10.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 27.0 10.0) completion_3)) 1 0))))
 (= admitted_4 (< ?x4324 3))))
(assert
 (let ((?x3870 (ite (< (/ 27.0 10.0) last_completion_3) last_completion_3 (/ 27.0 10.0))))
 (= completion_4 (ite admitted_4 (+ ?x3870 service_time) 0.0))))
(assert
 (= last_completion_4 (ite admitted_4 completion_4 last_completion_3)))
(assert
 (= late_4 (and admitted_4 (< (/ 79.0 20.0) completion_4))))
(assert
 (let ((?x4043 (+ (ite (and admitted_0 (< (/ 14.0 5.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 14.0 5.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 14.0 5.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 14.0 5.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 14.0 5.0) completion_4)) 1 0))))
 (= admitted_5 (< ?x4043 3))))
(assert
 (let ((?x4045 (ite (< (/ 14.0 5.0) last_completion_4) last_completion_4 (/ 14.0 5.0))))
 (= completion_5 (ite admitted_5 (+ ?x4045 service_time) 0.0))))
(assert
 (= last_completion_5 (ite admitted_5 completion_5 last_completion_4)))
(assert
 (= late_5 (and admitted_5 (< (/ 81.0 20.0) completion_5))))
(assert
 (let ((?x3780 (ite (and admitted_5 (< (/ 39.0 10.0) completion_5)) 1 0)))
 (let ((?x3777 (ite (and admitted_4 (< (/ 39.0 10.0) completion_4)) 1 0)))
 (let ((?x3774 (ite (and admitted_3 (< (/ 39.0 10.0) completion_3)) 1 0)))
 (let ((?x3865 (ite (and admitted_2 (< (/ 39.0 10.0) completion_2)) 1 0)))
 (let ((?x3860 (ite (and admitted_1 (< (/ 39.0 10.0) completion_1)) 1 0)))
 (let ((?x3867 (ite (and admitted_0 (< (/ 39.0 10.0) completion_0)) 1 0)))
 (let ((?x3781 (+ ?x3867 ?x3860 ?x3865 ?x3774 ?x3777 ?x3780)))
 (= admitted_6 (< ?x3781 3))))))))))
(assert
 (let ((?x3783 (ite (< (/ 39.0 10.0) last_completion_5) last_completion_5 (/ 39.0 10.0))))
 (= completion_6 (ite admitted_6 (+ ?x3783 service_time) 0.0))))
(assert
 (= last_completion_6 (ite admitted_6 completion_6 last_completion_5)))
(assert
 (= late_6 (and admitted_6 (< (/ 103.0 20.0) completion_6))))
(assert
 (let ((?x3780 (ite (and admitted_5 (< (/ 39.0 10.0) completion_5)) 1 0)))
 (let ((?x3777 (ite (and admitted_4 (< (/ 39.0 10.0) completion_4)) 1 0)))
 (let ((?x3774 (ite (and admitted_3 (< (/ 39.0 10.0) completion_3)) 1 0)))
 (let ((?x3865 (ite (and admitted_2 (< (/ 39.0 10.0) completion_2)) 1 0)))
 (let ((?x3860 (ite (and admitted_1 (< (/ 39.0 10.0) completion_1)) 1 0)))
 (let ((?x3867 (ite (and admitted_0 (< (/ 39.0 10.0) completion_0)) 1 0)))
 (let ((?x3840 (+ ?x3867 ?x3860 ?x3865 ?x3774 ?x3777 ?x3780 (ite (and admitted_6 (< (/ 39.0 10.0) completion_6)) 1 0))))
 (= admitted_7 (< ?x3840 3))))))))))
(assert
 (let ((?x3842 (ite (< (/ 39.0 10.0) last_completion_6) last_completion_6 (/ 39.0 10.0))))
 (= completion_7 (ite admitted_7 (+ ?x3842 service_time) 0.0))))
(assert
 (= last_completion_7 (ite admitted_7 completion_7 last_completion_6)))
(assert
 (= late_7 (and admitted_7 (< (/ 103.0 20.0) completion_7))))
(assert
 (let ((?x3578 (+ (ite (and admitted_0 (< (/ 24.0 5.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 24.0 5.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 24.0 5.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 24.0 5.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 24.0 5.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 24.0 5.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 24.0 5.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 24.0 5.0) completion_7)) 1 0))))
 (= admitted_8 (< ?x3578 3))))
(assert
 (let ((?x3580 (ite (< (/ 24.0 5.0) last_completion_7) last_completion_7 (/ 24.0 5.0))))
 (= completion_8 (ite admitted_8 (+ ?x3580 service_time) 0.0))))
(assert
 (= last_completion_8 (ite admitted_8 completion_8 last_completion_7)))
(assert
 (= late_8 (and admitted_8 (< (/ 121.0 20.0) completion_8))))
(assert
 (let ((?x3358 (+ (ite (and admitted_0 (< (/ 27.0 5.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 27.0 5.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 27.0 5.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 27.0 5.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 27.0 5.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 27.0 5.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 27.0 5.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 27.0 5.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 27.0 5.0) completion_8)) 1 0))))
 (= admitted_9 (< ?x3358 3))))
(assert
 (let ((?x3360 (ite (< (/ 27.0 5.0) last_completion_8) last_completion_8 (/ 27.0 5.0))))
 (= completion_9 (ite admitted_9 (+ ?x3360 service_time) 0.0))))
(assert
 (= last_completion_9 (ite admitted_9 completion_9 last_completion_8)))
(assert
 (= late_9 (and admitted_9 (< (/ 133.0 20.0) completion_9))))
(assert
 (let ((?x3155 (+ (ite (and admitted_0 (< (/ 28.0 5.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 28.0 5.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 28.0 5.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 28.0 5.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 28.0 5.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 28.0 5.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 28.0 5.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 28.0 5.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 28.0 5.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 28.0 5.0) completion_9)) 1 0))))
 (= admitted_10 (< ?x3155 3))))
(assert
 (let ((?x3157 (ite (< (/ 28.0 5.0) last_completion_9) last_completion_9 (/ 28.0 5.0))))
 (= completion_10 (ite admitted_10 (+ ?x3157 service_time) 0.0))))
(assert
 (= last_completion_10 (ite admitted_10 completion_10 last_completion_9)))
(assert
 (= late_10 (and admitted_10 (< (/ 137.0 20.0) completion_10))))
(assert
 (let ((?x2969 (+ (ite (and admitted_0 (< (/ 63.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 63.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 63.0 10.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 63.0 10.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 63.0 10.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 63.0 10.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 63.0 10.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 63.0 10.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 63.0 10.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 63.0 10.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 63.0 10.0) completion_10)) 1 0))))
 (= admitted_11 (< ?x2969 3))))
(assert
 (let ((?x2971 (ite (< (/ 63.0 10.0) last_completion_10) last_completion_10 (/ 63.0 10.0))))
 (= completion_11 (ite admitted_11 (+ ?x2971 service_time) 0.0))))
(assert
 (= last_completion_11 (ite admitted_11 completion_11 last_completion_10)))
(assert
 (= late_11 (and admitted_11 (< (/ 151.0 20.0) completion_11))))
(assert
 (let ((?x2442 (+ (ite (and admitted_0 (< (/ 67.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 67.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 67.0 10.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 67.0 10.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 67.0 10.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 67.0 10.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 67.0 10.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 67.0 10.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 67.0 10.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 67.0 10.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 67.0 10.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 67.0 10.0) completion_11)) 1 0))))
 (= admitted_12 (< ?x2442 3))))
(assert
 (let ((?x2800 (ite (< (/ 67.0 10.0) last_completion_11) last_completion_11 (/ 67.0 10.0))))
 (= completion_12 (ite admitted_12 (+ ?x2800 service_time) 0.0))))
(assert
 (= last_completion_12 (ite admitted_12 completion_12 last_completion_11)))
(assert
 (= late_12 (and admitted_12 (< (/ 159.0 20.0) completion_12))))
(assert
 (let ((?x2387 (+ (ite (and admitted_0 (< (/ 81.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 81.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 81.0 10.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 81.0 10.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 81.0 10.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 81.0 10.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 81.0 10.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 81.0 10.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 81.0 10.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 81.0 10.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 81.0 10.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 81.0 10.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 81.0 10.0) completion_12)) 1 0))))
 (= admitted_13 (< ?x2387 3))))
(assert
 (let ((?x2389 (ite (< (/ 81.0 10.0) last_completion_12) last_completion_12 (/ 81.0 10.0))))
 (= completion_13 (ite admitted_13 (+ ?x2389 service_time) 0.0))))
(assert
 (= last_completion_13 (ite admitted_13 completion_13 last_completion_12)))
(assert
 (= late_13 (and admitted_13 (< (/ 187.0 20.0) completion_13))))
(assert
 (let ((?x2095 (+ (ite (and admitted_0 (< (/ 44.0 5.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 44.0 5.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 44.0 5.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 44.0 5.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 44.0 5.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 44.0 5.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 44.0 5.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 44.0 5.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 44.0 5.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 44.0 5.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 44.0 5.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 44.0 5.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 44.0 5.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 44.0 5.0) completion_13)) 1 0))))
 (= admitted_14 (< ?x2095 3))))
(assert
 (let ((?x2088 (ite (< (/ 44.0 5.0) last_completion_13) last_completion_13 (/ 44.0 5.0))))
 (= completion_14 (ite admitted_14 (+ ?x2088 service_time) 0.0))))
(assert
 (= last_completion_14 (ite admitted_14 completion_14 last_completion_13)))
(assert
 (= late_14 (and admitted_14 (< (/ 201.0 20.0) completion_14))))
(assert
 (let ((?x1922 (+ (ite (and admitted_0 (< (/ 89.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 89.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 89.0 10.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 89.0 10.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 89.0 10.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 89.0 10.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 89.0 10.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 89.0 10.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 89.0 10.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 89.0 10.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 89.0 10.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 89.0 10.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 89.0 10.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 89.0 10.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 89.0 10.0) completion_14)) 1 0))))
 (= admitted_15 (< ?x1922 3))))
(assert
 (let ((?x1924 (ite (< (/ 89.0 10.0) last_completion_14) last_completion_14 (/ 89.0 10.0))))
 (= completion_15 (ite admitted_15 (+ ?x1924 service_time) 0.0))))
(assert
 (= last_completion_15 (ite admitted_15 completion_15 last_completion_14)))
(assert
 (= late_15 (and admitted_15 (< (/ 203.0 20.0) completion_15))))
(assert
 (let ((?x1486 (+ (ite (and admitted_0 (< (/ 51.0 5.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 51.0 5.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 51.0 5.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 51.0 5.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 51.0 5.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 51.0 5.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 51.0 5.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 51.0 5.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 51.0 5.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 51.0 5.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 51.0 5.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 51.0 5.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 51.0 5.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 51.0 5.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 51.0 5.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 51.0 5.0) completion_15)) 1 0))))
 (= admitted_16 (< ?x1486 3))))
(assert
 (let ((?x1433 (ite (< (/ 51.0 5.0) last_completion_15) last_completion_15 (/ 51.0 5.0))))
 (= completion_16 (ite admitted_16 (+ ?x1433 service_time) 0.0))))
(assert
 (= last_completion_16 (ite admitted_16 completion_16 last_completion_15)))
(assert
 (= late_16 (and admitted_16 (< (/ 229.0 20.0) completion_16))))
(assert
 (let ((?x1207 (+ (ite (and admitted_0 (< (/ 56.0 5.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 56.0 5.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 56.0 5.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 56.0 5.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 56.0 5.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 56.0 5.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 56.0 5.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 56.0 5.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 56.0 5.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 56.0 5.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 56.0 5.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 56.0 5.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 56.0 5.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 56.0 5.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 56.0 5.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 56.0 5.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 56.0 5.0) completion_16)) 1 0))))
 (= admitted_17 (< ?x1207 3))))
(assert
 (let ((?x1209 (ite (< (/ 56.0 5.0) last_completion_16) last_completion_16 (/ 56.0 5.0))))
 (= completion_17 (ite admitted_17 (+ ?x1209 service_time) 0.0))))
(assert
 (= last_completion_17 (ite admitted_17 completion_17 last_completion_16)))
(assert
 (= late_17 (and admitted_17 (< (/ 249.0 20.0) completion_17))))
(assert
 (let ((?x877 (+ (ite (and admitted_0 (< (/ 23.0 2.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 23.0 2.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 23.0 2.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 23.0 2.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 23.0 2.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 23.0 2.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 23.0 2.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 23.0 2.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 23.0 2.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 23.0 2.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 23.0 2.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 23.0 2.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 23.0 2.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 23.0 2.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 23.0 2.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 23.0 2.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 23.0 2.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 23.0 2.0) completion_17)) 1 0))))
 (= admitted_18 (< ?x877 3))))
(assert
 (let ((?x879 (ite (< (/ 23.0 2.0) last_completion_17) last_completion_17 (/ 23.0 2.0))))
 (= completion_18 (ite admitted_18 (+ ?x879 service_time) 0.0))))
(assert
 (= last_completion_18 (ite admitted_18 completion_18 last_completion_17)))
(assert
 (= late_18 (and admitted_18 (< (/ 51.0 4.0) completion_18))))
(assert
 (let ((?x462 (+ (ite (and admitted_0 (< (/ 59.0 5.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 59.0 5.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 59.0 5.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 59.0 5.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 59.0 5.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 59.0 5.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 59.0 5.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 59.0 5.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 59.0 5.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 59.0 5.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 59.0 5.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 59.0 5.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 59.0 5.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 59.0 5.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 59.0 5.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 59.0 5.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 59.0 5.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 59.0 5.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 59.0 5.0) completion_18)) 1 0))))
 (= admitted_19 (< ?x462 3))))
(assert
 (let ((?x464 (ite (< (/ 59.0 5.0) last_completion_18) last_completion_18 (/ 59.0 5.0))))
 (= completion_19 (ite admitted_19 (+ ?x464 service_time) 0.0))))
(assert
 (= last_completion_19 (ite admitted_19 completion_19 last_completion_18)))
(assert
 (= late_19 (and admitted_19 (< (/ 261.0 20.0) completion_19))))
(assert
 (let ((?x377 (+ (ite (and admitted_0 (< (/ 131.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 131.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 131.0 10.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 131.0 10.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 131.0 10.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 131.0 10.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 131.0 10.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 131.0 10.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 131.0 10.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 131.0 10.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 131.0 10.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 131.0 10.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 131.0 10.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 131.0 10.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 131.0 10.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 131.0 10.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 131.0 10.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 131.0 10.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 131.0 10.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 131.0 10.0) completion_19)) 1 0))))
 (= admitted_20 (< ?x377 3))))
(assert
 (let ((?x486 (ite (< (/ 131.0 10.0) last_completion_19) last_completion_19 (/ 131.0 10.0))))
 (= completion_20 (ite admitted_20 (+ ?x486 service_time) 0.0))))
(assert
 (= last_completion_20 (ite admitted_20 completion_20 last_completion_19)))
(assert
 (= late_20 (and admitted_20 (< (/ 287.0 20.0) completion_20))))
(assert
 (let ((?x1865 (+ (ite (and admitted_0 (< (/ 66.0 5.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 66.0 5.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 66.0 5.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 66.0 5.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 66.0 5.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 66.0 5.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 66.0 5.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 66.0 5.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 66.0 5.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 66.0 5.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 66.0 5.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 66.0 5.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 66.0 5.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 66.0 5.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 66.0 5.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 66.0 5.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 66.0 5.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 66.0 5.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 66.0 5.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 66.0 5.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 66.0 5.0) completion_20)) 1 0))))
 (= admitted_21 (< ?x1865 3))))
(assert
 (let ((?x2172 (ite (< (/ 66.0 5.0) last_completion_20) last_completion_20 (/ 66.0 5.0))))
 (= completion_21 (ite admitted_21 (+ ?x2172 service_time) 0.0))))
(assert
 (= last_completion_21 (ite admitted_21 completion_21 last_completion_20)))
(assert
 (= late_21 (and admitted_21 (< (/ 289.0 20.0) completion_21))))
(assert
 (let ((?x1024 (+ (ite (and admitted_0 (< (/ 141.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 141.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 141.0 10.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 141.0 10.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 141.0 10.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 141.0 10.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 141.0 10.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 141.0 10.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 141.0 10.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 141.0 10.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 141.0 10.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 141.0 10.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 141.0 10.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 141.0 10.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 141.0 10.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 141.0 10.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 141.0 10.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 141.0 10.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 141.0 10.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 141.0 10.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 141.0 10.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 141.0 10.0) completion_21)) 1 0))))
 (= admitted_22 (< ?x1024 3))))
(assert
 (let ((?x1026 (ite (< (/ 141.0 10.0) last_completion_21) last_completion_21 (/ 141.0 10.0))))
 (= completion_22 (ite admitted_22 (+ ?x1026 service_time) 0.0))))
(assert
 (= last_completion_22 (ite admitted_22 completion_22 last_completion_21)))
(assert
 (= late_22 (and admitted_22 (< (/ 307.0 20.0) completion_22))))
(assert
 (let ((?x797 (+ (ite (and admitted_0 (< (/ 78.0 5.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 78.0 5.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 78.0 5.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 78.0 5.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 78.0 5.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 78.0 5.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 78.0 5.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 78.0 5.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 78.0 5.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 78.0 5.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 78.0 5.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 78.0 5.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 78.0 5.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 78.0 5.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 78.0 5.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 78.0 5.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 78.0 5.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 78.0 5.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 78.0 5.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 78.0 5.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 78.0 5.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 78.0 5.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 78.0 5.0) completion_22)) 1 0))))
 (= admitted_23 (< ?x797 3))))
(assert
 (let ((?x799 (ite (< (/ 78.0 5.0) last_completion_22) last_completion_22 (/ 78.0 5.0))))
 (= completion_23 (ite admitted_23 (+ ?x799 service_time) 0.0))))
(assert
 (= last_completion_23 (ite admitted_23 completion_23 last_completion_22)))
(assert
 (= late_23 (and admitted_23 (< (/ 337.0 20.0) completion_23))))
(assert
 (let ((?x2479 (+ (ite (and admitted_0 (< 16.0 completion_0)) 1 0) (ite (and admitted_1 (< 16.0 completion_1)) 1 0) (ite (and admitted_2 (< 16.0 completion_2)) 1 0) (ite (and admitted_3 (< 16.0 completion_3)) 1 0) (ite (and admitted_4 (< 16.0 completion_4)) 1 0) (ite (and admitted_5 (< 16.0 completion_5)) 1 0) (ite (and admitted_6 (< 16.0 completion_6)) 1 0) (ite (and admitted_7 (< 16.0 completion_7)) 1 0) (ite (and admitted_8 (< 16.0 completion_8)) 1 0) (ite (and admitted_9 (< 16.0 completion_9)) 1 0) (ite (and admitted_10 (< 16.0 completion_10)) 1 0) (ite (and admitted_11 (< 16.0 completion_11)) 1 0) (ite (and admitted_12 (< 16.0 completion_12)) 1 0) (ite (and admitted_13 (< 16.0 completion_13)) 1 0) (ite (and admitted_14 (< 16.0 completion_14)) 1 0) (ite (and admitted_15 (< 16.0 completion_15)) 1 0) (ite (and admitted_16 (< 16.0 completion_16)) 1 0) (ite (and admitted_17 (< 16.0 completion_17)) 1 0) (ite (and admitted_18 (< 16.0 completion_18)) 1 0) (ite (and admitted_19 (< 16.0 completion_19)) 1 0) (ite (and admitted_20 (< 16.0 completion_20)) 1 0) (ite (and admitted_21 (< 16.0 completion_21)) 1 0) (ite (and admitted_22 (< 16.0 completion_22)) 1 0) (ite (and admitted_23 (< 16.0 completion_23)) 1 0))))
 (= admitted_24 (< ?x2479 3))))
(assert
 (let ((?x2481 (ite (< 16.0 last_completion_23) last_completion_23 16.0)))
 (= completion_24 (ite admitted_24 (+ ?x2481 service_time) 0.0))))
(assert
 (= last_completion_24 (ite admitted_24 completion_24 last_completion_23)))
(assert
 (= late_24 (and admitted_24 (< (/ 69.0 4.0) completion_24))))
(assert
 (let ((?x3232 (+ (ite (and admitted_0 (< (/ 173.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 173.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 173.0 10.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 173.0 10.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 173.0 10.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 173.0 10.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 173.0 10.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 173.0 10.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 173.0 10.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 173.0 10.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 173.0 10.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 173.0 10.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 173.0 10.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 173.0 10.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 173.0 10.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 173.0 10.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 173.0 10.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 173.0 10.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 173.0 10.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 173.0 10.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 173.0 10.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 173.0 10.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 173.0 10.0) completion_22)) 1 0) (ite (and admitted_23 (< (/ 173.0 10.0) completion_23)) 1 0) (ite (and admitted_24 (< (/ 173.0 10.0) completion_24)) 1 0))))
 (= admitted_25 (< ?x3232 3))))
(assert
 (let ((?x3234 (ite (< (/ 173.0 10.0) last_completion_24) last_completion_24 (/ 173.0 10.0))))
 (= completion_25 (ite admitted_25 (+ ?x3234 service_time) 0.0))))
(assert
 (= last_completion_25 (ite admitted_25 completion_25 last_completion_24)))
(assert
 (= late_25 (and admitted_25 (< (/ 371.0 20.0) completion_25))))
(assert
 (let ((?x4216 (+ (ite (and admitted_0 (< (/ 37.0 2.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 37.0 2.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 37.0 2.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 37.0 2.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 37.0 2.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 37.0 2.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 37.0 2.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 37.0 2.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 37.0 2.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 37.0 2.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 37.0 2.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 37.0 2.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 37.0 2.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 37.0 2.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 37.0 2.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 37.0 2.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 37.0 2.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 37.0 2.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 37.0 2.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 37.0 2.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 37.0 2.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 37.0 2.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 37.0 2.0) completion_22)) 1 0) (ite (and admitted_23 (< (/ 37.0 2.0) completion_23)) 1 0) (ite (and admitted_24 (< (/ 37.0 2.0) completion_24)) 1 0) (ite (and admitted_25 (< (/ 37.0 2.0) completion_25)) 1 0))))
 (= admitted_26 (< ?x4216 3))))
(assert
 (let ((?x4217 (ite (< (/ 37.0 2.0) last_completion_25) last_completion_25 (/ 37.0 2.0))))
 (= completion_26 (ite admitted_26 (+ ?x4217 service_time) 0.0))))
(assert
 (= last_completion_26 (ite admitted_26 completion_26 last_completion_25)))
(assert
 (= late_26 (and admitted_26 (< (/ 79.0 4.0) completion_26))))
(assert
 (let ((?x3099 (+ (ite (and admitted_0 (< (/ 193.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 193.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 193.0 10.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 193.0 10.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 193.0 10.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 193.0 10.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 193.0 10.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 193.0 10.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 193.0 10.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 193.0 10.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 193.0 10.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 193.0 10.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 193.0 10.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 193.0 10.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 193.0 10.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 193.0 10.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 193.0 10.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 193.0 10.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 193.0 10.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 193.0 10.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 193.0 10.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 193.0 10.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 193.0 10.0) completion_22)) 1 0) (ite (and admitted_23 (< (/ 193.0 10.0) completion_23)) 1 0) (ite (and admitted_24 (< (/ 193.0 10.0) completion_24)) 1 0) (ite (and admitted_25 (< (/ 193.0 10.0) completion_25)) 1 0) (ite (and admitted_26 (< (/ 193.0 10.0) completion_26)) 1 0))))
 (= admitted_27 (< ?x3099 3))))
(assert
 (let ((?x3101 (ite (< (/ 193.0 10.0) last_completion_26) last_completion_26 (/ 193.0 10.0))))
 (= completion_27 (ite admitted_27 (+ ?x3101 service_time) 0.0))))
(assert
 (= last_completion_27 (ite admitted_27 completion_27 last_completion_26)))
(assert
 (= late_27 (and admitted_27 (< (/ 411.0 20.0) completion_27))))
(assert
 (let ((?x3906 (+ (ite (and admitted_0 (< (/ 203.0 10.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 203.0 10.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 203.0 10.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 203.0 10.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 203.0 10.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 203.0 10.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 203.0 10.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 203.0 10.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 203.0 10.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 203.0 10.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 203.0 10.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 203.0 10.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 203.0 10.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 203.0 10.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 203.0 10.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 203.0 10.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 203.0 10.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 203.0 10.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 203.0 10.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 203.0 10.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 203.0 10.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 203.0 10.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 203.0 10.0) completion_22)) 1 0) (ite (and admitted_23 (< (/ 203.0 10.0) completion_23)) 1 0) (ite (and admitted_24 (< (/ 203.0 10.0) completion_24)) 1 0) (ite (and admitted_25 (< (/ 203.0 10.0) completion_25)) 1 0) (ite (and admitted_26 (< (/ 203.0 10.0) completion_26)) 1 0) (ite (and admitted_27 (< (/ 203.0 10.0) completion_27)) 1 0))))
 (= admitted_28 (< ?x3906 3))))
(assert
 (let ((?x3908 (ite (< (/ 203.0 10.0) last_completion_27) last_completion_27 (/ 203.0 10.0))))
 (= completion_28 (ite admitted_28 (+ ?x3908 service_time) 0.0))))
(assert
 (= last_completion_28 (ite admitted_28 completion_28 last_completion_27)))
(assert
 (= late_28 (and admitted_28 (< (/ 431.0 20.0) completion_28))))
(assert
 (let ((?x3440 (ite (and admitted_28 (< (/ 102.0 5.0) completion_28)) 1 0)))
 (let ((?x3433 (ite (and admitted_27 (< (/ 102.0 5.0) completion_27)) 1 0)))
 (let ((?x3430 (ite (and admitted_26 (< (/ 102.0 5.0) completion_26)) 1 0)))
 (let ((?x504 (ite (and admitted_25 (< (/ 102.0 5.0) completion_25)) 1 0)))
 (let ((?x1721 (ite (and admitted_24 (< (/ 102.0 5.0) completion_24)) 1 0)))
 (let ((?x2720 (ite (and admitted_23 (< (/ 102.0 5.0) completion_23)) 1 0)))
 (let ((?x2716 (ite (and admitted_22 (< (/ 102.0 5.0) completion_22)) 1 0)))
 (let ((?x2713 (ite (and admitted_21 (< (/ 102.0 5.0) completion_21)) 1 0)))
 (let ((?x2710 (ite (and admitted_20 (< (/ 102.0 5.0) completion_20)) 1 0)))
 (let ((?x2705 (ite (and admitted_19 (< (/ 102.0 5.0) completion_19)) 1 0)))
 (let ((?x2702 (ite (and admitted_18 (< (/ 102.0 5.0) completion_18)) 1 0)))
 (let ((?x2699 (ite (and admitted_17 (< (/ 102.0 5.0) completion_17)) 1 0)))
 (let ((?x2696 (ite (and admitted_16 (< (/ 102.0 5.0) completion_16)) 1 0)))
 (let ((?x2691 (ite (and admitted_15 (< (/ 102.0 5.0) completion_15)) 1 0)))
 (let ((?x2688 (ite (and admitted_14 (< (/ 102.0 5.0) completion_14)) 1 0)))
 (let ((?x2685 (ite (and admitted_13 (< (/ 102.0 5.0) completion_13)) 1 0)))
 (let ((?x2682 (ite (and admitted_12 (< (/ 102.0 5.0) completion_12)) 1 0)))
 (let ((?x2677 (ite (and admitted_11 (< (/ 102.0 5.0) completion_11)) 1 0)))
 (let ((?x2674 (ite (and admitted_10 (< (/ 102.0 5.0) completion_10)) 1 0)))
 (let ((?x2671 (ite (and admitted_9 (< (/ 102.0 5.0) completion_9)) 1 0)))
 (let ((?x2668 (ite (and admitted_8 (< (/ 102.0 5.0) completion_8)) 1 0)))
 (let ((?x2665 (ite (and admitted_7 (< (/ 102.0 5.0) completion_7)) 1 0)))
 (let ((?x2662 (ite (and admitted_6 (< (/ 102.0 5.0) completion_6)) 1 0)))
 (let ((?x2657 (ite (and admitted_5 (< (/ 102.0 5.0) completion_5)) 1 0)))
 (let ((?x2651 (ite (and admitted_4 (< (/ 102.0 5.0) completion_4)) 1 0)))
 (let ((?x2648 (ite (and admitted_3 (< (/ 102.0 5.0) completion_3)) 1 0)))
 (let ((?x2643 (ite (and admitted_2 (< (/ 102.0 5.0) completion_2)) 1 0)))
 (let ((?x2640 (ite (and admitted_1 (< (/ 102.0 5.0) completion_1)) 1 0)))
 (let ((?x2635 (ite (and admitted_0 (< (/ 102.0 5.0) completion_0)) 1 0)))
 (let ((?x3441 (+ ?x2635 ?x2640 ?x2643 ?x2648 ?x2651 ?x2657 ?x2662 ?x2665 ?x2668 ?x2671 ?x2674 ?x2677 ?x2682 ?x2685 ?x2688 ?x2691 ?x2696 ?x2699 ?x2702 ?x2705 ?x2710 ?x2713 ?x2716 ?x2720 ?x1721 ?x504 ?x3430 ?x3433 ?x3440)))
 (= admitted_29 (< ?x3441 3)))))))))))))))))))))))))))))))))
(assert
 (let ((?x3443 (ite (< (/ 102.0 5.0) last_completion_28) last_completion_28 (/ 102.0 5.0))))
 (= completion_29 (ite admitted_29 (+ ?x3443 service_time) 0.0))))
(assert
 (= last_completion_29 (ite admitted_29 completion_29 last_completion_28)))
(assert
 (= late_29 (and admitted_29 (< (/ 433.0 20.0) completion_29))))
(assert
 (let ((?x651 (ite (and admitted_29 (< (/ 102.0 5.0) completion_29)) 1 0)))
 (let ((?x3440 (ite (and admitted_28 (< (/ 102.0 5.0) completion_28)) 1 0)))
 (let ((?x3433 (ite (and admitted_27 (< (/ 102.0 5.0) completion_27)) 1 0)))
 (let ((?x3430 (ite (and admitted_26 (< (/ 102.0 5.0) completion_26)) 1 0)))
 (let ((?x504 (ite (and admitted_25 (< (/ 102.0 5.0) completion_25)) 1 0)))
 (let ((?x1721 (ite (and admitted_24 (< (/ 102.0 5.0) completion_24)) 1 0)))
 (let ((?x2720 (ite (and admitted_23 (< (/ 102.0 5.0) completion_23)) 1 0)))
 (let ((?x2716 (ite (and admitted_22 (< (/ 102.0 5.0) completion_22)) 1 0)))
 (let ((?x2713 (ite (and admitted_21 (< (/ 102.0 5.0) completion_21)) 1 0)))
 (let ((?x2710 (ite (and admitted_20 (< (/ 102.0 5.0) completion_20)) 1 0)))
 (let ((?x2705 (ite (and admitted_19 (< (/ 102.0 5.0) completion_19)) 1 0)))
 (let ((?x2702 (ite (and admitted_18 (< (/ 102.0 5.0) completion_18)) 1 0)))
 (let ((?x2699 (ite (and admitted_17 (< (/ 102.0 5.0) completion_17)) 1 0)))
 (let ((?x2696 (ite (and admitted_16 (< (/ 102.0 5.0) completion_16)) 1 0)))
 (let ((?x2691 (ite (and admitted_15 (< (/ 102.0 5.0) completion_15)) 1 0)))
 (let ((?x2688 (ite (and admitted_14 (< (/ 102.0 5.0) completion_14)) 1 0)))
 (let ((?x2685 (ite (and admitted_13 (< (/ 102.0 5.0) completion_13)) 1 0)))
 (let ((?x2682 (ite (and admitted_12 (< (/ 102.0 5.0) completion_12)) 1 0)))
 (let ((?x2677 (ite (and admitted_11 (< (/ 102.0 5.0) completion_11)) 1 0)))
 (let ((?x2674 (ite (and admitted_10 (< (/ 102.0 5.0) completion_10)) 1 0)))
 (let ((?x2671 (ite (and admitted_9 (< (/ 102.0 5.0) completion_9)) 1 0)))
 (let ((?x2668 (ite (and admitted_8 (< (/ 102.0 5.0) completion_8)) 1 0)))
 (let ((?x2665 (ite (and admitted_7 (< (/ 102.0 5.0) completion_7)) 1 0)))
 (let ((?x2662 (ite (and admitted_6 (< (/ 102.0 5.0) completion_6)) 1 0)))
 (let ((?x2657 (ite (and admitted_5 (< (/ 102.0 5.0) completion_5)) 1 0)))
 (let ((?x2651 (ite (and admitted_4 (< (/ 102.0 5.0) completion_4)) 1 0)))
 (let ((?x2648 (ite (and admitted_3 (< (/ 102.0 5.0) completion_3)) 1 0)))
 (let ((?x2643 (ite (and admitted_2 (< (/ 102.0 5.0) completion_2)) 1 0)))
 (let ((?x2640 (ite (and admitted_1 (< (/ 102.0 5.0) completion_1)) 1 0)))
 (let ((?x2635 (ite (and admitted_0 (< (/ 102.0 5.0) completion_0)) 1 0)))
 (let ((?x649 (+ ?x2635 ?x2640 ?x2643 ?x2648 ?x2651 ?x2657 ?x2662 ?x2665 ?x2668 ?x2671 ?x2674 ?x2677 ?x2682 ?x2685 ?x2688 ?x2691 ?x2696 ?x2699 ?x2702 ?x2705 ?x2710 ?x2713 ?x2716 ?x2720 ?x1721 ?x504 ?x3430 ?x3433 ?x3440 ?x651)))
 (= admitted_30 (< ?x649 3))))))))))))))))))))))))))))))))))
(assert
 (let ((?x2269 (ite (< (/ 102.0 5.0) last_completion_29) last_completion_29 (/ 102.0 5.0))))
 (= completion_30 (ite admitted_30 (+ ?x2269 service_time) 0.0))))
(assert
 (= last_completion_30 (ite admitted_30 completion_30 last_completion_29)))
(assert
 (= late_30 (and admitted_30 (< (/ 433.0 20.0) completion_30))))
(assert
 (let ((?x651 (ite (and admitted_29 (< (/ 102.0 5.0) completion_29)) 1 0)))
 (let ((?x3440 (ite (and admitted_28 (< (/ 102.0 5.0) completion_28)) 1 0)))
 (let ((?x3433 (ite (and admitted_27 (< (/ 102.0 5.0) completion_27)) 1 0)))
 (let ((?x3430 (ite (and admitted_26 (< (/ 102.0 5.0) completion_26)) 1 0)))
 (let ((?x504 (ite (and admitted_25 (< (/ 102.0 5.0) completion_25)) 1 0)))
 (let ((?x1721 (ite (and admitted_24 (< (/ 102.0 5.0) completion_24)) 1 0)))
 (let ((?x2720 (ite (and admitted_23 (< (/ 102.0 5.0) completion_23)) 1 0)))
 (let ((?x2716 (ite (and admitted_22 (< (/ 102.0 5.0) completion_22)) 1 0)))
 (let ((?x2713 (ite (and admitted_21 (< (/ 102.0 5.0) completion_21)) 1 0)))
 (let ((?x2710 (ite (and admitted_20 (< (/ 102.0 5.0) completion_20)) 1 0)))
 (let ((?x2705 (ite (and admitted_19 (< (/ 102.0 5.0) completion_19)) 1 0)))
 (let ((?x2702 (ite (and admitted_18 (< (/ 102.0 5.0) completion_18)) 1 0)))
 (let ((?x2699 (ite (and admitted_17 (< (/ 102.0 5.0) completion_17)) 1 0)))
 (let ((?x2696 (ite (and admitted_16 (< (/ 102.0 5.0) completion_16)) 1 0)))
 (let ((?x2691 (ite (and admitted_15 (< (/ 102.0 5.0) completion_15)) 1 0)))
 (let ((?x2688 (ite (and admitted_14 (< (/ 102.0 5.0) completion_14)) 1 0)))
 (let ((?x2685 (ite (and admitted_13 (< (/ 102.0 5.0) completion_13)) 1 0)))
 (let ((?x2682 (ite (and admitted_12 (< (/ 102.0 5.0) completion_12)) 1 0)))
 (let ((?x2677 (ite (and admitted_11 (< (/ 102.0 5.0) completion_11)) 1 0)))
 (let ((?x2674 (ite (and admitted_10 (< (/ 102.0 5.0) completion_10)) 1 0)))
 (let ((?x2671 (ite (and admitted_9 (< (/ 102.0 5.0) completion_9)) 1 0)))
 (let ((?x2668 (ite (and admitted_8 (< (/ 102.0 5.0) completion_8)) 1 0)))
 (let ((?x2665 (ite (and admitted_7 (< (/ 102.0 5.0) completion_7)) 1 0)))
 (let ((?x2662 (ite (and admitted_6 (< (/ 102.0 5.0) completion_6)) 1 0)))
 (let ((?x2657 (ite (and admitted_5 (< (/ 102.0 5.0) completion_5)) 1 0)))
 (let ((?x2651 (ite (and admitted_4 (< (/ 102.0 5.0) completion_4)) 1 0)))
 (let ((?x2648 (ite (and admitted_3 (< (/ 102.0 5.0) completion_3)) 1 0)))
 (let ((?x2643 (ite (and admitted_2 (< (/ 102.0 5.0) completion_2)) 1 0)))
 (let ((?x2640 (ite (and admitted_1 (< (/ 102.0 5.0) completion_1)) 1 0)))
 (let ((?x2635 (ite (and admitted_0 (< (/ 102.0 5.0) completion_0)) 1 0)))
 (let ((?x2314 (+ ?x2635 ?x2640 ?x2643 ?x2648 ?x2651 ?x2657 ?x2662 ?x2665 ?x2668 ?x2671 ?x2674 ?x2677 ?x2682 ?x2685 ?x2688 ?x2691 ?x2696 ?x2699 ?x2702 ?x2705 ?x2710 ?x2713 ?x2716 ?x2720 ?x1721 ?x504 ?x3430 ?x3433 ?x3440 ?x651 (ite (and admitted_30 (< (/ 102.0 5.0) completion_30)) 1 0))))
 (= admitted_31 (< ?x2314 3))))))))))))))))))))))))))))))))))
(assert
 (let ((?x2316 (ite (< (/ 102.0 5.0) last_completion_30) last_completion_30 (/ 102.0 5.0))))
 (= completion_31 (ite admitted_31 (+ ?x2316 service_time) 0.0))))
(assert
 (= last_completion_31 (ite admitted_31 completion_31 last_completion_30)))
(assert
 (= late_31 (and admitted_31 (< (/ 433.0 20.0) completion_31))))
(assert
 (let ((?x3323 (+ (ite (or (not admitted_0) late_0) 1 0) (ite (or (not admitted_1) late_1) 1 0) (ite (or (not admitted_2) late_2) 1 0) (ite (or (not admitted_3) late_3) 1 0) (ite (or (not admitted_4) late_4) 1 0) (ite (or (not admitted_5) late_5) 1 0) (ite (or (not admitted_6) late_6) 1 0) (ite (or (not admitted_7) late_7) 1 0) (ite (or (not admitted_8) late_8) 1 0) (ite (or (not admitted_9) late_9) 1 0) (ite (or (not admitted_10) late_10) 1 0) (ite (or (not admitted_11) late_11) 1 0) (ite (or (not admitted_12) late_12) 1 0) (ite (or (not admitted_13) late_13) 1 0) (ite (or (not admitted_14) late_14) 1 0) (ite (or (not admitted_15) late_15) 1 0) (ite (or (not admitted_16) late_16) 1 0) (ite (or (not admitted_17) late_17) 1 0) (ite (or (not admitted_18) late_18) 1 0) (ite (or (not admitted_19) late_19) 1 0) (ite (or (not admitted_20) late_20) 1 0) (ite (or (not admitted_21) late_21) 1 0) (ite (or (not admitted_22) late_22) 1 0) (ite (or (not admitted_23) late_23) 1 0) (ite (or (not admitted_24) late_24) 1 0) (ite (or (not admitted_25) late_25) 1 0) (ite (or (not admitted_26) late_26) 1 0) (ite (or (not admitted_27) late_27) 1 0) (ite (or (not admitted_28) late_28) 1 0) (ite (or (not admitted_29) late_29) 1 0) (ite (or (not admitted_30) late_30) 1 0) (ite (or (not admitted_31) late_31) 1 0))))
(= failure_count ?x3323)))
(check-sat)
