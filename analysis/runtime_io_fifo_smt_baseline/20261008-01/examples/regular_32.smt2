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
 (let ((?x36 (ite admitted_0 (+ (ite (> 0.0 0.0) 0.0 0.0) service_time) 0.0)))
 (= completion_0 ?x36)))
(assert
 (= last_completion_0 (ite admitted_0 completion_0 0.0)))
(assert
 (let (($x216 (and admitted_0 (< (/ 3.0 2.0) completion_0))))
 (= late_0 $x216)))
(assert
 (let ((?x221 (+ (ite (and admitted_0 (< (/ 3.0 4.0) completion_0)) 1 0))))
 (= admitted_1 (< ?x221 3))))
(assert
 (let ((?x9 (ite (< (/ 3.0 4.0) last_completion_0) last_completion_0 (/ 3.0 4.0))))
 (= completion_1 (ite admitted_1 (+ ?x9 service_time) 0.0))))
(assert
 (= last_completion_1 (ite admitted_1 completion_1 last_completion_0)))
(assert
 (let (($x218 (and admitted_1 (< (/ 9.0 4.0) completion_1))))
 (= late_1 $x218)))
(assert
 (let ((?x162 (+ (ite (and admitted_0 (< (/ 3.0 2.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 3.0 2.0) completion_1)) 1 0))))
 (= admitted_2 (< ?x162 3))))
(assert
 (let ((?x87 (ite (< (/ 3.0 2.0) last_completion_1) last_completion_1 (/ 3.0 2.0))))
 (= completion_2 (ite admitted_2 (+ ?x87 service_time) 0.0))))
(assert
 (= last_completion_2 (ite admitted_2 completion_2 last_completion_1)))
(assert
 (let (($x95 (and admitted_2 (< 3.0 completion_2))))
 (= late_2 $x95)))
(assert
 (let ((?x288 (+ (ite (and admitted_0 (< (/ 9.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 9.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 9.0 4.0) completion_2)) 1 0))))
 (= admitted_3 (< ?x288 3))))
(assert
 (let ((?x275 (ite (< (/ 9.0 4.0) last_completion_2) last_completion_2 (/ 9.0 4.0))))
 (= completion_3 (ite admitted_3 (+ ?x275 service_time) 0.0))))
(assert
 (= last_completion_3 (ite admitted_3 completion_3 last_completion_2)))
(assert
 (let (($x307 (and admitted_3 (< (/ 15.0 4.0) completion_3))))
 (= late_3 $x307)))
(assert
 (let ((?x336 (+ (ite (and admitted_0 (< 3.0 completion_0)) 1 0) (ite (and admitted_1 (< 3.0 completion_1)) 1 0) (ite (and admitted_2 (< 3.0 completion_2)) 1 0) (ite (and admitted_3 (< 3.0 completion_3)) 1 0))))
 (= admitted_4 (< ?x336 3))))
(assert
 (let ((?x338 (ite (< 3.0 last_completion_3) last_completion_3 3.0)))
 (= completion_4 (ite admitted_4 (+ ?x338 service_time) 0.0))))
(assert
 (= last_completion_4 (ite admitted_4 completion_4 last_completion_3)))
(assert
 (let (($x348 (and admitted_4 (< (/ 9.0 2.0) completion_4))))
 (= late_4 $x348)))
(assert
 (let ((?x393 (+ (ite (and admitted_0 (< (/ 15.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 15.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 15.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 15.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 15.0 4.0) completion_4)) 1 0))))
 (= admitted_5 (< ?x393 3))))
(assert
 (let ((?x395 (ite (< (/ 15.0 4.0) last_completion_4) last_completion_4 (/ 15.0 4.0))))
 (= completion_5 (ite admitted_5 (+ ?x395 service_time) 0.0))))
(assert
 (= last_completion_5 (ite admitted_5 completion_5 last_completion_4)))
(assert
 (let (($x405 (and admitted_5 (< (/ 21.0 4.0) completion_5))))
 (= late_5 $x405)))
(assert
 (let ((?x457 (+ (ite (and admitted_0 (< (/ 9.0 2.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 9.0 2.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 9.0 2.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 9.0 2.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 9.0 2.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 9.0 2.0) completion_5)) 1 0))))
 (= admitted_6 (< ?x457 3))))
(assert
 (let ((?x459 (ite (< (/ 9.0 2.0) last_completion_5) last_completion_5 (/ 9.0 2.0))))
 (= completion_6 (ite admitted_6 (+ ?x459 service_time) 0.0))))
(assert
 (= last_completion_6 (ite admitted_6 completion_6 last_completion_5)))
(assert
 (let (($x468 (and admitted_6 (< 6.0 completion_6))))
 (= late_6 $x468)))
(assert
 (let ((?x527 (+ (ite (and admitted_0 (< (/ 21.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 21.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 21.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 21.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 21.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 21.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 21.0 4.0) completion_6)) 1 0))))
 (= admitted_7 (< ?x527 3))))
(assert
 (let ((?x529 (ite (< (/ 21.0 4.0) last_completion_6) last_completion_6 (/ 21.0 4.0))))
 (= completion_7 (ite admitted_7 (+ ?x529 service_time) 0.0))))
(assert
 (= last_completion_7 (ite admitted_7 completion_7 last_completion_6)))
(assert
 (let (($x539 (and admitted_7 (< (/ 27.0 4.0) completion_7))))
 (= late_7 $x539)))
(assert
 (let ((?x605 (+ (ite (and admitted_0 (< 6.0 completion_0)) 1 0) (ite (and admitted_1 (< 6.0 completion_1)) 1 0) (ite (and admitted_2 (< 6.0 completion_2)) 1 0) (ite (and admitted_3 (< 6.0 completion_3)) 1 0) (ite (and admitted_4 (< 6.0 completion_4)) 1 0) (ite (and admitted_5 (< 6.0 completion_5)) 1 0) (ite (and admitted_6 (< 6.0 completion_6)) 1 0) (ite (and admitted_7 (< 6.0 completion_7)) 1 0))))
 (= admitted_8 (< ?x605 3))))
(assert
 (let ((?x607 (ite (< 6.0 last_completion_7) last_completion_7 6.0)))
 (= completion_8 (ite admitted_8 (+ ?x607 service_time) 0.0))))
(assert
 (= last_completion_8 (ite admitted_8 completion_8 last_completion_7)))
(assert
 (let (($x617 (and admitted_8 (< (/ 15.0 2.0) completion_8))))
 (= late_8 $x617)))
(assert
 (let ((?x690 (+ (ite (and admitted_0 (< (/ 27.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 27.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 27.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 27.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 27.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 27.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 27.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 27.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 27.0 4.0) completion_8)) 1 0))))
 (= admitted_9 (< ?x690 3))))
(assert
 (let ((?x692 (ite (< (/ 27.0 4.0) last_completion_8) last_completion_8 (/ 27.0 4.0))))
 (= completion_9 (ite admitted_9 (+ ?x692 service_time) 0.0))))
(assert
 (= last_completion_9 (ite admitted_9 completion_9 last_completion_8)))
(assert
 (let (($x702 (and admitted_9 (< (/ 33.0 4.0) completion_9))))
 (= late_9 $x702)))
(assert
 (let ((?x782 (+ (ite (and admitted_0 (< (/ 15.0 2.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 15.0 2.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 15.0 2.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 15.0 2.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 15.0 2.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 15.0 2.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 15.0 2.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 15.0 2.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 15.0 2.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 15.0 2.0) completion_9)) 1 0))))
 (= admitted_10 (< ?x782 3))))
(assert
 (let ((?x784 (ite (< (/ 15.0 2.0) last_completion_9) last_completion_9 (/ 15.0 2.0))))
 (= completion_10 (ite admitted_10 (+ ?x784 service_time) 0.0))))
(assert
 (= last_completion_10 (ite admitted_10 completion_10 last_completion_9)))
(assert
 (let (($x793 (and admitted_10 (< 9.0 completion_10))))
 (= late_10 $x793)))
(assert
 (let ((?x880 (+ (ite (and admitted_0 (< (/ 33.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 33.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 33.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 33.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 33.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 33.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 33.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 33.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 33.0 4.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 33.0 4.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 33.0 4.0) completion_10)) 1 0))))
 (= admitted_11 (< ?x880 3))))
(assert
 (let ((?x882 (ite (< (/ 33.0 4.0) last_completion_10) last_completion_10 (/ 33.0 4.0))))
 (= completion_11 (ite admitted_11 (+ ?x882 service_time) 0.0))))
(assert
 (= last_completion_11 (ite admitted_11 completion_11 last_completion_10)))
(assert
 (let (($x892 (and admitted_11 (< (/ 39.0 4.0) completion_11))))
 (= late_11 $x892)))
(assert
 (let ((?x986 (+ (ite (and admitted_0 (< 9.0 completion_0)) 1 0) (ite (and admitted_1 (< 9.0 completion_1)) 1 0) (ite (and admitted_2 (< 9.0 completion_2)) 1 0) (ite (and admitted_3 (< 9.0 completion_3)) 1 0) (ite (and admitted_4 (< 9.0 completion_4)) 1 0) (ite (and admitted_5 (< 9.0 completion_5)) 1 0) (ite (and admitted_6 (< 9.0 completion_6)) 1 0) (ite (and admitted_7 (< 9.0 completion_7)) 1 0) (ite (and admitted_8 (< 9.0 completion_8)) 1 0) (ite (and admitted_9 (< 9.0 completion_9)) 1 0) (ite (and admitted_10 (< 9.0 completion_10)) 1 0) (ite (and admitted_11 (< 9.0 completion_11)) 1 0))))
 (= admitted_12 (< ?x986 3))))
(assert
 (let ((?x988 (ite (< 9.0 last_completion_11) last_completion_11 9.0)))
 (= completion_12 (ite admitted_12 (+ ?x988 service_time) 0.0))))
(assert
 (= last_completion_12 (ite admitted_12 completion_12 last_completion_11)))
(assert
 (let (($x998 (and admitted_12 (< (/ 21.0 2.0) completion_12))))
 (= late_12 $x998)))
(assert
 (let ((?x1099 (+ (ite (and admitted_0 (< (/ 39.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 39.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 39.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 39.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 39.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 39.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 39.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 39.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 39.0 4.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 39.0 4.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 39.0 4.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 39.0 4.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 39.0 4.0) completion_12)) 1 0))))
 (= admitted_13 (< ?x1099 3))))
(assert
 (let ((?x1101 (ite (< (/ 39.0 4.0) last_completion_12) last_completion_12 (/ 39.0 4.0))))
 (= completion_13 (ite admitted_13 (+ ?x1101 service_time) 0.0))))
(assert
 (= last_completion_13 (ite admitted_13 completion_13 last_completion_12)))
(assert
 (let (($x1111 (and admitted_13 (< (/ 45.0 4.0) completion_13))))
 (= late_13 $x1111)))
(assert
 (let ((?x1219 (+ (ite (and admitted_0 (< (/ 21.0 2.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 21.0 2.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 21.0 2.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 21.0 2.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 21.0 2.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 21.0 2.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 21.0 2.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 21.0 2.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 21.0 2.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 21.0 2.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 21.0 2.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 21.0 2.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 21.0 2.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 21.0 2.0) completion_13)) 1 0))))
 (= admitted_14 (< ?x1219 3))))
(assert
 (let ((?x1221 (ite (< (/ 21.0 2.0) last_completion_13) last_completion_13 (/ 21.0 2.0))))
 (= completion_14 (ite admitted_14 (+ ?x1221 service_time) 0.0))))
(assert
 (= last_completion_14 (ite admitted_14 completion_14 last_completion_13)))
(assert
 (let (($x1231 (and admitted_14 (< 12.0 completion_14))))
 (= late_14 $x1231)))
(assert
 (let ((?x1346 (+ (ite (and admitted_0 (< (/ 45.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 45.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 45.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 45.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 45.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 45.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 45.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 45.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 45.0 4.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 45.0 4.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 45.0 4.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 45.0 4.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 45.0 4.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 45.0 4.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 45.0 4.0) completion_14)) 1 0))))
 (= admitted_15 (< ?x1346 3))))
(assert
 (let ((?x1348 (ite (< (/ 45.0 4.0) last_completion_14) last_completion_14 (/ 45.0 4.0))))
 (= completion_15 (ite admitted_15 (+ ?x1348 service_time) 0.0))))
(assert
 (= last_completion_15 (ite admitted_15 completion_15 last_completion_14)))
(assert
 (let (($x1358 (and admitted_15 (< (/ 51.0 4.0) completion_15))))
 (= late_15 $x1358)))
(assert
 (let ((?x1480 (+ (ite (and admitted_0 (< 12.0 completion_0)) 1 0) (ite (and admitted_1 (< 12.0 completion_1)) 1 0) (ite (and admitted_2 (< 12.0 completion_2)) 1 0) (ite (and admitted_3 (< 12.0 completion_3)) 1 0) (ite (and admitted_4 (< 12.0 completion_4)) 1 0) (ite (and admitted_5 (< 12.0 completion_5)) 1 0) (ite (and admitted_6 (< 12.0 completion_6)) 1 0) (ite (and admitted_7 (< 12.0 completion_7)) 1 0) (ite (and admitted_8 (< 12.0 completion_8)) 1 0) (ite (and admitted_9 (< 12.0 completion_9)) 1 0) (ite (and admitted_10 (< 12.0 completion_10)) 1 0) (ite (and admitted_11 (< 12.0 completion_11)) 1 0) (ite (and admitted_12 (< 12.0 completion_12)) 1 0) (ite (and admitted_13 (< 12.0 completion_13)) 1 0) (ite (and admitted_14 (< 12.0 completion_14)) 1 0) (ite (and admitted_15 (< 12.0 completion_15)) 1 0))))
 (= admitted_16 (< ?x1480 3))))
(assert
 (let ((?x1482 (ite (< 12.0 last_completion_15) last_completion_15 12.0)))
 (= completion_16 (ite admitted_16 (+ ?x1482 service_time) 0.0))))
(assert
 (= last_completion_16 (ite admitted_16 completion_16 last_completion_15)))
(assert
 (let (($x1492 (and admitted_16 (< (/ 27.0 2.0) completion_16))))
 (= late_16 $x1492)))
(assert
 (let ((?x1621 (+ (ite (and admitted_0 (< (/ 51.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 51.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 51.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 51.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 51.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 51.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 51.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 51.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 51.0 4.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 51.0 4.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 51.0 4.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 51.0 4.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 51.0 4.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 51.0 4.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 51.0 4.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 51.0 4.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 51.0 4.0) completion_16)) 1 0))))
 (= admitted_17 (< ?x1621 3))))
(assert
 (let ((?x1623 (ite (< (/ 51.0 4.0) last_completion_16) last_completion_16 (/ 51.0 4.0))))
 (= completion_17 (ite admitted_17 (+ ?x1623 service_time) 0.0))))
(assert
 (= last_completion_17 (ite admitted_17 completion_17 last_completion_16)))
(assert
 (let (($x1633 (and admitted_17 (< (/ 57.0 4.0) completion_17))))
 (= late_17 $x1633)))
(assert
 (let ((?x1769 (+ (ite (and admitted_0 (< (/ 27.0 2.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 27.0 2.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 27.0 2.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 27.0 2.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 27.0 2.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 27.0 2.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 27.0 2.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 27.0 2.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 27.0 2.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 27.0 2.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 27.0 2.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 27.0 2.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 27.0 2.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 27.0 2.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 27.0 2.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 27.0 2.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 27.0 2.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 27.0 2.0) completion_17)) 1 0))))
 (= admitted_18 (< ?x1769 3))))
(assert
 (let ((?x1771 (ite (< (/ 27.0 2.0) last_completion_17) last_completion_17 (/ 27.0 2.0))))
 (= completion_18 (ite admitted_18 (+ ?x1771 service_time) 0.0))))
(assert
 (= last_completion_18 (ite admitted_18 completion_18 last_completion_17)))
(assert
 (let (($x1781 (and admitted_18 (< 15.0 completion_18))))
 (= late_18 $x1781)))
(assert
 (let ((?x1924 (+ (ite (and admitted_0 (< (/ 57.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 57.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 57.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 57.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 57.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 57.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 57.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 57.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 57.0 4.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 57.0 4.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 57.0 4.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 57.0 4.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 57.0 4.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 57.0 4.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 57.0 4.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 57.0 4.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 57.0 4.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 57.0 4.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 57.0 4.0) completion_18)) 1 0))))
 (= admitted_19 (< ?x1924 3))))
(assert
 (let ((?x1926 (ite (< (/ 57.0 4.0) last_completion_18) last_completion_18 (/ 57.0 4.0))))
 (= completion_19 (ite admitted_19 (+ ?x1926 service_time) 0.0))))
(assert
 (= last_completion_19 (ite admitted_19 completion_19 last_completion_18)))
(assert
 (let (($x1936 (and admitted_19 (< (/ 63.0 4.0) completion_19))))
 (= late_19 $x1936)))
(assert
 (let ((?x2086 (+ (ite (and admitted_0 (< 15.0 completion_0)) 1 0) (ite (and admitted_1 (< 15.0 completion_1)) 1 0) (ite (and admitted_2 (< 15.0 completion_2)) 1 0) (ite (and admitted_3 (< 15.0 completion_3)) 1 0) (ite (and admitted_4 (< 15.0 completion_4)) 1 0) (ite (and admitted_5 (< 15.0 completion_5)) 1 0) (ite (and admitted_6 (< 15.0 completion_6)) 1 0) (ite (and admitted_7 (< 15.0 completion_7)) 1 0) (ite (and admitted_8 (< 15.0 completion_8)) 1 0) (ite (and admitted_9 (< 15.0 completion_9)) 1 0) (ite (and admitted_10 (< 15.0 completion_10)) 1 0) (ite (and admitted_11 (< 15.0 completion_11)) 1 0) (ite (and admitted_12 (< 15.0 completion_12)) 1 0) (ite (and admitted_13 (< 15.0 completion_13)) 1 0) (ite (and admitted_14 (< 15.0 completion_14)) 1 0) (ite (and admitted_15 (< 15.0 completion_15)) 1 0) (ite (and admitted_16 (< 15.0 completion_16)) 1 0) (ite (and admitted_17 (< 15.0 completion_17)) 1 0) (ite (and admitted_18 (< 15.0 completion_18)) 1 0) (ite (and admitted_19 (< 15.0 completion_19)) 1 0))))
 (= admitted_20 (< ?x2086 3))))
(assert
 (let ((?x2088 (ite (< 15.0 last_completion_19) last_completion_19 15.0)))
 (= completion_20 (ite admitted_20 (+ ?x2088 service_time) 0.0))))
(assert
 (= last_completion_20 (ite admitted_20 completion_20 last_completion_19)))
(assert
 (let (($x2098 (and admitted_20 (< (/ 33.0 2.0) completion_20))))
 (= late_20 $x2098)))
(assert
 (let ((?x2255 (+ (ite (and admitted_0 (< (/ 63.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 63.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 63.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 63.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 63.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 63.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 63.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 63.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 63.0 4.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 63.0 4.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 63.0 4.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 63.0 4.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 63.0 4.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 63.0 4.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 63.0 4.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 63.0 4.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 63.0 4.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 63.0 4.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 63.0 4.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 63.0 4.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 63.0 4.0) completion_20)) 1 0))))
 (= admitted_21 (< ?x2255 3))))
(assert
 (let ((?x2257 (ite (< (/ 63.0 4.0) last_completion_20) last_completion_20 (/ 63.0 4.0))))
 (= completion_21 (ite admitted_21 (+ ?x2257 service_time) 0.0))))
(assert
 (= last_completion_21 (ite admitted_21 completion_21 last_completion_20)))
(assert
 (let (($x2267 (and admitted_21 (< (/ 69.0 4.0) completion_21))))
 (= late_21 $x2267)))
(assert
 (let ((?x2431 (+ (ite (and admitted_0 (< (/ 33.0 2.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 33.0 2.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 33.0 2.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 33.0 2.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 33.0 2.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 33.0 2.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 33.0 2.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 33.0 2.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 33.0 2.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 33.0 2.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 33.0 2.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 33.0 2.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 33.0 2.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 33.0 2.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 33.0 2.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 33.0 2.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 33.0 2.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 33.0 2.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 33.0 2.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 33.0 2.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 33.0 2.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 33.0 2.0) completion_21)) 1 0))))
 (= admitted_22 (< ?x2431 3))))
(assert
 (let ((?x2433 (ite (< (/ 33.0 2.0) last_completion_21) last_completion_21 (/ 33.0 2.0))))
 (= completion_22 (ite admitted_22 (+ ?x2433 service_time) 0.0))))
(assert
 (= last_completion_22 (ite admitted_22 completion_22 last_completion_21)))
(assert
 (let (($x2443 (and admitted_22 (< 18.0 completion_22))))
 (= late_22 $x2443)))
(assert
 (let ((?x2614 (+ (ite (and admitted_0 (< (/ 69.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 69.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 69.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 69.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 69.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 69.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 69.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 69.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 69.0 4.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 69.0 4.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 69.0 4.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 69.0 4.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 69.0 4.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 69.0 4.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 69.0 4.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 69.0 4.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 69.0 4.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 69.0 4.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 69.0 4.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 69.0 4.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 69.0 4.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 69.0 4.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 69.0 4.0) completion_22)) 1 0))))
 (= admitted_23 (< ?x2614 3))))
(assert
 (let ((?x2616 (ite (< (/ 69.0 4.0) last_completion_22) last_completion_22 (/ 69.0 4.0))))
 (= completion_23 (ite admitted_23 (+ ?x2616 service_time) 0.0))))
(assert
 (= last_completion_23 (ite admitted_23 completion_23 last_completion_22)))
(assert
 (let (($x2626 (and admitted_23 (< (/ 75.0 4.0) completion_23))))
 (= late_23 $x2626)))
(assert
 (let ((?x2804 (+ (ite (and admitted_0 (< 18.0 completion_0)) 1 0) (ite (and admitted_1 (< 18.0 completion_1)) 1 0) (ite (and admitted_2 (< 18.0 completion_2)) 1 0) (ite (and admitted_3 (< 18.0 completion_3)) 1 0) (ite (and admitted_4 (< 18.0 completion_4)) 1 0) (ite (and admitted_5 (< 18.0 completion_5)) 1 0) (ite (and admitted_6 (< 18.0 completion_6)) 1 0) (ite (and admitted_7 (< 18.0 completion_7)) 1 0) (ite (and admitted_8 (< 18.0 completion_8)) 1 0) (ite (and admitted_9 (< 18.0 completion_9)) 1 0) (ite (and admitted_10 (< 18.0 completion_10)) 1 0) (ite (and admitted_11 (< 18.0 completion_11)) 1 0) (ite (and admitted_12 (< 18.0 completion_12)) 1 0) (ite (and admitted_13 (< 18.0 completion_13)) 1 0) (ite (and admitted_14 (< 18.0 completion_14)) 1 0) (ite (and admitted_15 (< 18.0 completion_15)) 1 0) (ite (and admitted_16 (< 18.0 completion_16)) 1 0) (ite (and admitted_17 (< 18.0 completion_17)) 1 0) (ite (and admitted_18 (< 18.0 completion_18)) 1 0) (ite (and admitted_19 (< 18.0 completion_19)) 1 0) (ite (and admitted_20 (< 18.0 completion_20)) 1 0) (ite (and admitted_21 (< 18.0 completion_21)) 1 0) (ite (and admitted_22 (< 18.0 completion_22)) 1 0) (ite (and admitted_23 (< 18.0 completion_23)) 1 0))))
 (= admitted_24 (< ?x2804 3))))
(assert
 (let ((?x2806 (ite (< 18.0 last_completion_23) last_completion_23 18.0)))
 (= completion_24 (ite admitted_24 (+ ?x2806 service_time) 0.0))))
(assert
 (= last_completion_24 (ite admitted_24 completion_24 last_completion_23)))
(assert
 (let (($x2816 (and admitted_24 (< (/ 39.0 2.0) completion_24))))
 (= late_24 $x2816)))
(assert
 (let ((?x3001 (+ (ite (and admitted_0 (< (/ 75.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 75.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 75.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 75.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 75.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 75.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 75.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 75.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 75.0 4.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 75.0 4.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 75.0 4.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 75.0 4.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 75.0 4.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 75.0 4.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 75.0 4.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 75.0 4.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 75.0 4.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 75.0 4.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 75.0 4.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 75.0 4.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 75.0 4.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 75.0 4.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 75.0 4.0) completion_22)) 1 0) (ite (and admitted_23 (< (/ 75.0 4.0) completion_23)) 1 0) (ite (and admitted_24 (< (/ 75.0 4.0) completion_24)) 1 0))))
 (= admitted_25 (< ?x3001 3))))
(assert
 (let ((?x3003 (ite (< (/ 75.0 4.0) last_completion_24) last_completion_24 (/ 75.0 4.0))))
 (= completion_25 (ite admitted_25 (+ ?x3003 service_time) 0.0))))
(assert
 (= last_completion_25 (ite admitted_25 completion_25 last_completion_24)))
(assert
 (let (($x3013 (and admitted_25 (< (/ 81.0 4.0) completion_25))))
 (= late_25 $x3013)))
(assert
 (let ((?x3205 (+ (ite (and admitted_0 (< (/ 39.0 2.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 39.0 2.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 39.0 2.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 39.0 2.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 39.0 2.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 39.0 2.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 39.0 2.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 39.0 2.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 39.0 2.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 39.0 2.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 39.0 2.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 39.0 2.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 39.0 2.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 39.0 2.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 39.0 2.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 39.0 2.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 39.0 2.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 39.0 2.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 39.0 2.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 39.0 2.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 39.0 2.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 39.0 2.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 39.0 2.0) completion_22)) 1 0) (ite (and admitted_23 (< (/ 39.0 2.0) completion_23)) 1 0) (ite (and admitted_24 (< (/ 39.0 2.0) completion_24)) 1 0) (ite (and admitted_25 (< (/ 39.0 2.0) completion_25)) 1 0))))
 (= admitted_26 (< ?x3205 3))))
(assert
 (let ((?x3207 (ite (< (/ 39.0 2.0) last_completion_25) last_completion_25 (/ 39.0 2.0))))
 (= completion_26 (ite admitted_26 (+ ?x3207 service_time) 0.0))))
(assert
 (= last_completion_26 (ite admitted_26 completion_26 last_completion_25)))
(assert
 (let (($x3217 (and admitted_26 (< 21.0 completion_26))))
 (= late_26 $x3217)))
(assert
 (let ((?x3416 (+ (ite (and admitted_0 (< (/ 81.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 81.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 81.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 81.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 81.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 81.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 81.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 81.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 81.0 4.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 81.0 4.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 81.0 4.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 81.0 4.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 81.0 4.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 81.0 4.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 81.0 4.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 81.0 4.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 81.0 4.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 81.0 4.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 81.0 4.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 81.0 4.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 81.0 4.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 81.0 4.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 81.0 4.0) completion_22)) 1 0) (ite (and admitted_23 (< (/ 81.0 4.0) completion_23)) 1 0) (ite (and admitted_24 (< (/ 81.0 4.0) completion_24)) 1 0) (ite (and admitted_25 (< (/ 81.0 4.0) completion_25)) 1 0) (ite (and admitted_26 (< (/ 81.0 4.0) completion_26)) 1 0))))
 (= admitted_27 (< ?x3416 3))))
(assert
 (let ((?x3418 (ite (< (/ 81.0 4.0) last_completion_26) last_completion_26 (/ 81.0 4.0))))
 (= completion_27 (ite admitted_27 (+ ?x3418 service_time) 0.0))))
(assert
 (= last_completion_27 (ite admitted_27 completion_27 last_completion_26)))
(assert
 (let (($x3428 (and admitted_27 (< (/ 87.0 4.0) completion_27))))
 (= late_27 $x3428)))
(assert
 (let ((?x3634 (+ (ite (and admitted_0 (< 21.0 completion_0)) 1 0) (ite (and admitted_1 (< 21.0 completion_1)) 1 0) (ite (and admitted_2 (< 21.0 completion_2)) 1 0) (ite (and admitted_3 (< 21.0 completion_3)) 1 0) (ite (and admitted_4 (< 21.0 completion_4)) 1 0) (ite (and admitted_5 (< 21.0 completion_5)) 1 0) (ite (and admitted_6 (< 21.0 completion_6)) 1 0) (ite (and admitted_7 (< 21.0 completion_7)) 1 0) (ite (and admitted_8 (< 21.0 completion_8)) 1 0) (ite (and admitted_9 (< 21.0 completion_9)) 1 0) (ite (and admitted_10 (< 21.0 completion_10)) 1 0) (ite (and admitted_11 (< 21.0 completion_11)) 1 0) (ite (and admitted_12 (< 21.0 completion_12)) 1 0) (ite (and admitted_13 (< 21.0 completion_13)) 1 0) (ite (and admitted_14 (< 21.0 completion_14)) 1 0) (ite (and admitted_15 (< 21.0 completion_15)) 1 0) (ite (and admitted_16 (< 21.0 completion_16)) 1 0) (ite (and admitted_17 (< 21.0 completion_17)) 1 0) (ite (and admitted_18 (< 21.0 completion_18)) 1 0) (ite (and admitted_19 (< 21.0 completion_19)) 1 0) (ite (and admitted_20 (< 21.0 completion_20)) 1 0) (ite (and admitted_21 (< 21.0 completion_21)) 1 0) (ite (and admitted_22 (< 21.0 completion_22)) 1 0) (ite (and admitted_23 (< 21.0 completion_23)) 1 0) (ite (and admitted_24 (< 21.0 completion_24)) 1 0) (ite (and admitted_25 (< 21.0 completion_25)) 1 0) (ite (and admitted_26 (< 21.0 completion_26)) 1 0) (ite (and admitted_27 (< 21.0 completion_27)) 1 0))))
 (= admitted_28 (< ?x3634 3))))
(assert
 (let ((?x3636 (ite (< 21.0 last_completion_27) last_completion_27 21.0)))
 (= completion_28 (ite admitted_28 (+ ?x3636 service_time) 0.0))))
(assert
 (= last_completion_28 (ite admitted_28 completion_28 last_completion_27)))
(assert
 (let (($x3646 (and admitted_28 (< (/ 45.0 2.0) completion_28))))
 (= late_28 $x3646)))
(assert
 (let ((?x3859 (+ (ite (and admitted_0 (< (/ 87.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 87.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 87.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 87.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 87.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 87.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 87.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 87.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 87.0 4.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 87.0 4.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 87.0 4.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 87.0 4.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 87.0 4.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 87.0 4.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 87.0 4.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 87.0 4.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 87.0 4.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 87.0 4.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 87.0 4.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 87.0 4.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 87.0 4.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 87.0 4.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 87.0 4.0) completion_22)) 1 0) (ite (and admitted_23 (< (/ 87.0 4.0) completion_23)) 1 0) (ite (and admitted_24 (< (/ 87.0 4.0) completion_24)) 1 0) (ite (and admitted_25 (< (/ 87.0 4.0) completion_25)) 1 0) (ite (and admitted_26 (< (/ 87.0 4.0) completion_26)) 1 0) (ite (and admitted_27 (< (/ 87.0 4.0) completion_27)) 1 0) (ite (and admitted_28 (< (/ 87.0 4.0) completion_28)) 1 0))))
 (= admitted_29 (< ?x3859 3))))
(assert
 (let ((?x3861 (ite (< (/ 87.0 4.0) last_completion_28) last_completion_28 (/ 87.0 4.0))))
 (= completion_29 (ite admitted_29 (+ ?x3861 service_time) 0.0))))
(assert
 (= last_completion_29 (ite admitted_29 completion_29 last_completion_28)))
(assert
 (let (($x3871 (and admitted_29 (< (/ 93.0 4.0) completion_29))))
 (= late_29 $x3871)))
(assert
 (let ((?x4091 (+ (ite (and admitted_0 (< (/ 45.0 2.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 45.0 2.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 45.0 2.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 45.0 2.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 45.0 2.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 45.0 2.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 45.0 2.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 45.0 2.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 45.0 2.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 45.0 2.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 45.0 2.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 45.0 2.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 45.0 2.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 45.0 2.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 45.0 2.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 45.0 2.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 45.0 2.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 45.0 2.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 45.0 2.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 45.0 2.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 45.0 2.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 45.0 2.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 45.0 2.0) completion_22)) 1 0) (ite (and admitted_23 (< (/ 45.0 2.0) completion_23)) 1 0) (ite (and admitted_24 (< (/ 45.0 2.0) completion_24)) 1 0) (ite (and admitted_25 (< (/ 45.0 2.0) completion_25)) 1 0) (ite (and admitted_26 (< (/ 45.0 2.0) completion_26)) 1 0) (ite (and admitted_27 (< (/ 45.0 2.0) completion_27)) 1 0) (ite (and admitted_28 (< (/ 45.0 2.0) completion_28)) 1 0) (ite (and admitted_29 (< (/ 45.0 2.0) completion_29)) 1 0))))
 (= admitted_30 (< ?x4091 3))))
(assert
 (let ((?x4093 (ite (< (/ 45.0 2.0) last_completion_29) last_completion_29 (/ 45.0 2.0))))
 (= completion_30 (ite admitted_30 (+ ?x4093 service_time) 0.0))))
(assert
 (= last_completion_30 (ite admitted_30 completion_30 last_completion_29)))
(assert
 (= late_30 (and admitted_30 (< 24.0 completion_30))))
(assert
 (let ((?x4330 (+ (ite (and admitted_0 (< (/ 93.0 4.0) completion_0)) 1 0) (ite (and admitted_1 (< (/ 93.0 4.0) completion_1)) 1 0) (ite (and admitted_2 (< (/ 93.0 4.0) completion_2)) 1 0) (ite (and admitted_3 (< (/ 93.0 4.0) completion_3)) 1 0) (ite (and admitted_4 (< (/ 93.0 4.0) completion_4)) 1 0) (ite (and admitted_5 (< (/ 93.0 4.0) completion_5)) 1 0) (ite (and admitted_6 (< (/ 93.0 4.0) completion_6)) 1 0) (ite (and admitted_7 (< (/ 93.0 4.0) completion_7)) 1 0) (ite (and admitted_8 (< (/ 93.0 4.0) completion_8)) 1 0) (ite (and admitted_9 (< (/ 93.0 4.0) completion_9)) 1 0) (ite (and admitted_10 (< (/ 93.0 4.0) completion_10)) 1 0) (ite (and admitted_11 (< (/ 93.0 4.0) completion_11)) 1 0) (ite (and admitted_12 (< (/ 93.0 4.0) completion_12)) 1 0) (ite (and admitted_13 (< (/ 93.0 4.0) completion_13)) 1 0) (ite (and admitted_14 (< (/ 93.0 4.0) completion_14)) 1 0) (ite (and admitted_15 (< (/ 93.0 4.0) completion_15)) 1 0) (ite (and admitted_16 (< (/ 93.0 4.0) completion_16)) 1 0) (ite (and admitted_17 (< (/ 93.0 4.0) completion_17)) 1 0) (ite (and admitted_18 (< (/ 93.0 4.0) completion_18)) 1 0) (ite (and admitted_19 (< (/ 93.0 4.0) completion_19)) 1 0) (ite (and admitted_20 (< (/ 93.0 4.0) completion_20)) 1 0) (ite (and admitted_21 (< (/ 93.0 4.0) completion_21)) 1 0) (ite (and admitted_22 (< (/ 93.0 4.0) completion_22)) 1 0) (ite (and admitted_23 (< (/ 93.0 4.0) completion_23)) 1 0) (ite (and admitted_24 (< (/ 93.0 4.0) completion_24)) 1 0) (ite (and admitted_25 (< (/ 93.0 4.0) completion_25)) 1 0) (ite (and admitted_26 (< (/ 93.0 4.0) completion_26)) 1 0) (ite (and admitted_27 (< (/ 93.0 4.0) completion_27)) 1 0) (ite (and admitted_28 (< (/ 93.0 4.0) completion_28)) 1 0) (ite (and admitted_29 (< (/ 93.0 4.0) completion_29)) 1 0) (ite (and admitted_30 (< (/ 93.0 4.0) completion_30)) 1 0))))
 (= admitted_31 (< ?x4330 3))))
(assert
 (let ((?x4332 (ite (< (/ 93.0 4.0) last_completion_30) last_completion_30 (/ 93.0 4.0))))
 (= completion_31 (ite admitted_31 (+ ?x4332 service_time) 0.0))))
(assert
 (= last_completion_31 (ite admitted_31 completion_31 last_completion_30)))
(assert
 (= late_31 (and admitted_31 (< (/ 99.0 4.0) completion_31))))
(assert
 (let ((?x4578 (+ (ite (or (not admitted_0) late_0) 1 0) (ite (or (not admitted_1) late_1) 1 0) (ite (or (not admitted_2) late_2) 1 0) (ite (or (not admitted_3) late_3) 1 0) (ite (or (not admitted_4) late_4) 1 0) (ite (or (not admitted_5) late_5) 1 0) (ite (or (not admitted_6) late_6) 1 0) (ite (or (not admitted_7) late_7) 1 0) (ite (or (not admitted_8) late_8) 1 0) (ite (or (not admitted_9) late_9) 1 0) (ite (or (not admitted_10) late_10) 1 0) (ite (or (not admitted_11) late_11) 1 0) (ite (or (not admitted_12) late_12) 1 0) (ite (or (not admitted_13) late_13) 1 0) (ite (or (not admitted_14) late_14) 1 0) (ite (or (not admitted_15) late_15) 1 0) (ite (or (not admitted_16) late_16) 1 0) (ite (or (not admitted_17) late_17) 1 0) (ite (or (not admitted_18) late_18) 1 0) (ite (or (not admitted_19) late_19) 1 0) (ite (or (not admitted_20) late_20) 1 0) (ite (or (not admitted_21) late_21) 1 0) (ite (or (not admitted_22) late_22) 1 0) (ite (or (not admitted_23) late_23) 1 0) (ite (or (not admitted_24) late_24) 1 0) (ite (or (not admitted_25) late_25) 1 0) (ite (or (not admitted_26) late_26) 1 0) (ite (or (not admitted_27) late_27) 1 0) (ite (or (not admitted_28) late_28) 1 0) (ite (or (not admitted_29) late_29) 1 0) (ite (or (not admitted_30) late_30) 1 0) (ite (or (not admitted_31) late_31) 1 0))))
(= failure_count ?x4578)))
(check-sat)
