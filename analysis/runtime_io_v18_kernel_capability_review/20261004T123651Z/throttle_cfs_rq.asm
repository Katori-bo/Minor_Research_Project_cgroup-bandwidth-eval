
/usr/lib/modules/7.2.8-arch1-2/build/vmlinux:     file format elf64-x86-64


Disassembly of section .text:

ffffffff813d2410 <throttle_cfs_rq>:
ffffffff813d2410:	e8 8b 12 f6 ff       	call   ffffffff813336a0 <__fentry__>
ffffffff813d2415:	48 83 ec 40          	sub    $0x40,%rsp
ffffffff813d2419:	48 89 5c 24 10       	mov    %rbx,0x10(%rsp)
ffffffff813d241e:	48 89 fb             	mov    %rdi,%rbx
ffffffff813d2421:	48 89 6c 24 18       	mov    %rbp,0x18(%rsp)
ffffffff813d2426:	4c 89 64 24 20       	mov    %r12,0x20(%rsp)
ffffffff813d242b:	4c 89 74 24 30       	mov    %r14,0x30(%rsp)
ffffffff813d2430:	48 8b af 58 01 00 00 	mov    0x158(%rdi),%rbp
ffffffff813d2437:	4c 8b 67 58          	mov    0x58(%rdi),%r12
ffffffff813d243b:	4c 8b b7 38 01 00 00 	mov    0x138(%rdi),%r14
ffffffff813d2442:	48 8d bd c0 01 00 00 	lea    0x1c0(%rbp),%rdi
ffffffff813d2449:	e8 c2 51 1d 01       	call   ffffffff825a7610 <_raw_spin_lock>
ffffffff813d244e:	4d 85 e4             	test   %r12,%r12
ffffffff813d2451:	74 2f                	je     ffffffff813d2482 <throttle_cfs_rq+0x72>
ffffffff813d2453:	41 80 7c 24 58 00    	cmpb   $0x0,0x58(%r12)
ffffffff813d2459:	74 27                	je     ffffffff813d2482 <throttle_cfs_rq+0x72>
ffffffff813d245b:	8b 05 77 69 48 02    	mov    0x2486977(%rip),%eax        # ffffffff83858dd8 <sysctl_sched_cfs_bandwidth_slice>
ffffffff813d2461:	48 69 c0 e8 03 00 00 	imul   $0x3e8,%rax,%rax
ffffffff813d2468:	48 83 bd d0 01 00 00 	cmpq   $0xffffffffffffffff,0x1d0(%rbp)
ffffffff813d246f:	ff 
ffffffff813d2470:	0f 84 a6 00 00 00    	je     ffffffff813d251c <throttle_cfs_rq+0x10c>
ffffffff813d2476:	48 2b 83 68 01 00 00 	sub    0x168(%rbx),%rax
ffffffff813d247d:	49 89 c0             	mov    %rax,%r8
ffffffff813d2480:	eb 1d                	jmp    ffffffff813d249f <throttle_cfs_rq+0x8f>
ffffffff813d2482:	48 83 bd d0 01 00 00 	cmpq   $0xffffffffffffffff,0x1d0(%rbp)
ffffffff813d2489:	ff 
ffffffff813d248a:	0f 84 5b 01 00 00    	je     ffffffff813d25eb <throttle_cfs_rq+0x1db>
ffffffff813d2490:	b8 01 00 00 00       	mov    $0x1,%eax
ffffffff813d2495:	48 2b 83 68 01 00 00 	sub    0x168(%rbx),%rax
ffffffff813d249c:	49 89 c0             	mov    %rax,%r8
ffffffff813d249f:	80 bd f9 01 00 00 00 	cmpb   $0x0,0x1f9(%rbp)
ffffffff813d24a6:	75 5d                	jne    ffffffff813d2505 <throttle_cfs_rq+0xf5>
ffffffff813d24a8:	c6 85 f9 01 00 00 01 	movb   $0x1,0x1f9(%rbp)
ffffffff813d24af:	48 8b 95 c8 01 00 00 	mov    0x1c8(%rbp),%rdx
ffffffff813d24b6:	48 8d bd 00 02 00 00 	lea    0x200(%rbp),%rdi
ffffffff813d24bd:	4c 89 44 24 08       	mov    %r8,0x8(%rsp)
ffffffff813d24c2:	48 89 14 24          	mov    %rdx,(%rsp)
ffffffff813d24c6:	e8 75 f6 0b 00       	call   ffffffff81491b40 <hrtimer_cb_get_time>
ffffffff813d24cb:	48 8b 14 24          	mov    (%rsp),%rdx
ffffffff813d24cf:	48 8d bd 00 02 00 00 	lea    0x200(%rbp),%rdi
ffffffff813d24d6:	48 89 c6             	mov    %rax,%rsi
ffffffff813d24d9:	e8 62 d8 0b 00       	call   ffffffff8148fd40 <hrtimer_forward>
ffffffff813d24de:	48 8b b5 40 02 00 00 	mov    0x240(%rbp),%rsi
ffffffff813d24e5:	48 8b 95 28 02 00 00 	mov    0x228(%rbp),%rdx
ffffffff813d24ec:	b9 02 00 00 00       	mov    $0x2,%ecx
ffffffff813d24f1:	48 8d bd 00 02 00 00 	lea    0x200(%rbp),%rdi
ffffffff813d24f8:	48 29 f2             	sub    %rsi,%rdx
ffffffff813d24fb:	e8 b0 ed 0b 00       	call   ffffffff814912b0 <hrtimer_start_range_ns>
ffffffff813d2500:	4c 8b 44 24 08       	mov    0x8(%rsp),%r8
ffffffff813d2505:	48 8b 95 d8 01 00 00 	mov    0x1d8(%rbp),%rdx
ffffffff813d250c:	48 85 d2             	test   %rdx,%rdx
ffffffff813d250f:	0f 85 f1 00 00 00    	jne    ffffffff813d2606 <throttle_cfs_rq+0x1f6>
ffffffff813d2515:	48 8b 83 68 01 00 00 	mov    0x168(%rbx),%rax
ffffffff813d251c:	48 89 83 68 01 00 00 	mov    %rax,0x168(%rbx)
ffffffff813d2523:	48 85 c0             	test   %rax,%rax
ffffffff813d2526:	0f 8f ca 00 00 00    	jg     ffffffff813d25f6 <throttle_cfs_rq+0x1e6>
ffffffff813d252c:	48 8b b5 a8 02 00 00 	mov    0x2a8(%rbp),%rsi
ffffffff813d2533:	48 8d 95 a0 02 00 00 	lea    0x2a0(%rbp),%rdx
ffffffff813d253a:	48 8d bb a8 01 00 00 	lea    0x1a8(%rbx),%rdi
ffffffff813d2541:	48 3b 16             	cmp    (%rsi),%rdx
ffffffff813d2544:	0f 85 05 a2 e3 ff    	jne    ffffffff8120c74f <throttle_cfs_rq.cold>
ffffffff813d254a:	48 39 f7             	cmp    %rsi,%rdi
ffffffff813d254d:	0f 84 fc a1 e3 ff    	je     ffffffff8120c74f <throttle_cfs_rq.cold>
ffffffff813d2553:	48 39 fa             	cmp    %rdi,%rdx
ffffffff813d2556:	0f 84 f3 a1 e3 ff    	je     ffffffff8120c74f <throttle_cfs_rq.cold>
ffffffff813d255c:	48 89 93 a8 01 00 00 	mov    %rdx,0x1a8(%rbx)
ffffffff813d2563:	48 89 b3 b0 01 00 00 	mov    %rsi,0x1b0(%rbx)
ffffffff813d256a:	48 89 3e             	mov    %rdi,(%rsi)
ffffffff813d256d:	48 89 bd a8 02 00 00 	mov    %rdi,0x2a8(%rbp)
ffffffff813d2574:	48 8d bd c0 01 00 00 	lea    0x1c0(%rbp),%rdi
ffffffff813d257b:	e8 a0 51 1d 01       	call   ffffffff825a7720 <_raw_spin_unlock>
ffffffff813d2580:	e8 7b a9 08 00       	call   ffffffff8145cf00 <__rcu_read_lock>
ffffffff813d2585:	48 8b bb 58 01 00 00 	mov    0x158(%rbx),%rdi
ffffffff813d258c:	4c 89 f1             	mov    %r14,%rcx
ffffffff813d258f:	48 c7 c2 e0 73 3c 81 	mov    $0xffffffff813c73e0,%rdx
ffffffff813d2596:	48 c7 c6 80 34 3d 81 	mov    $0xffffffff813d3480,%rsi
ffffffff813d259d:	e8 7e 4d ff ff       	call   ffffffff813c7320 <walk_tg_tree_from>
ffffffff813d25a2:	e8 09 35 09 00       	call   ffffffff81465ab0 <__rcu_read_unlock>
ffffffff813d25a7:	80 8b a0 01 00 00 01 	orb    $0x1,0x1a0(%rbx)
ffffffff813d25ae:	48 83 bb 78 01 00 00 	cmpq   $0x0,0x178(%rbx)
ffffffff813d25b5:	00 
ffffffff813d25b6:	0f 85 a1 00 00 00    	jne    ffffffff813d265d <throttle_cfs_rq+0x24d>
ffffffff813d25bc:	4d 85 e4             	test   %r12,%r12
ffffffff813d25bf:	74 08                	je     ffffffff813d25c9 <throttle_cfs_rq+0x1b9>
ffffffff813d25c1:	41 80 7c 24 58 00    	cmpb   $0x0,0x58(%r12)
ffffffff813d25c7:	75 64                	jne    ffffffff813d262d <throttle_cfs_rq+0x21d>
ffffffff813d25c9:	b8 01 00 00 00       	mov    $0x1,%eax
ffffffff813d25ce:	48 8b 5c 24 10       	mov    0x10(%rsp),%rbx
ffffffff813d25d3:	48 8b 6c 24 18       	mov    0x18(%rsp),%rbp
ffffffff813d25d8:	4c 8b 64 24 20       	mov    0x20(%rsp),%r12
ffffffff813d25dd:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
ffffffff813d25e2:	48 83 c4 40          	add    $0x40,%rsp
ffffffff813d25e6:	e9 c5 70 1d 01       	jmp    ffffffff825a96b0 <__pi___x86_return_thunk>
ffffffff813d25eb:	48 c7 83 68 01 00 00 	movq   $0x1,0x168(%rbx)
ffffffff813d25f2:	01 00 00 00 
ffffffff813d25f6:	48 8d bd c0 01 00 00 	lea    0x1c0(%rbp),%rdi
ffffffff813d25fd:	e8 1e 51 1d 01       	call   ffffffff825a7720 <_raw_spin_unlock>
ffffffff813d2602:	31 c0                	xor    %eax,%eax
ffffffff813d2604:	eb c8                	jmp    ffffffff813d25ce <throttle_cfs_rq+0x1be>
ffffffff813d2606:	49 39 d0             	cmp    %rdx,%r8
ffffffff813d2609:	4c 89 c0             	mov    %r8,%rax
ffffffff813d260c:	c6 85 f8 01 00 00 00 	movb   $0x0,0x1f8(%rbp)
ffffffff813d2613:	48 0f 47 c2          	cmova  %rdx,%rax
ffffffff813d2617:	48 29 c2             	sub    %rax,%rdx
ffffffff813d261a:	48 89 95 d8 01 00 00 	mov    %rdx,0x1d8(%rbp)
ffffffff813d2621:	48 03 83 68 01 00 00 	add    0x168(%rbx),%rax
ffffffff813d2628:	e9 ef fe ff ff       	jmp    ffffffff813d251c <throttle_cfs_rq+0x10c>
ffffffff813d262d:	49 8b 7e 18          	mov    0x18(%r14),%rdi
ffffffff813d2631:	48 8d b7 28 04 00 00 	lea    0x428(%rdi),%rsi
ffffffff813d2638:	48 39 b7 28 04 00 00 	cmp    %rsi,0x428(%rdi)
ffffffff813d263f:	75 88                	jne    ffffffff813d25c9 <throttle_cfs_rq+0x1b9>
ffffffff813d2641:	f7 47 2c 04 00 20 00 	testl  $0x200004,0x2c(%rdi)
ffffffff813d2648:	0f 85 7b ff ff ff    	jne    ffffffff813d25c9 <throttle_cfs_rq+0x1b9>
ffffffff813d264e:	ba 01 00 00 00       	mov    $0x1,%edx
ffffffff813d2653:	e8 e8 21 fd ff       	call   ffffffff813a4840 <task_work_add>
ffffffff813d2658:	e9 6c ff ff ff       	jmp    ffffffff813d25c9 <throttle_cfs_rq+0x1b9>
ffffffff813d265d:	0f 0b                	ud2
ffffffff813d265f:	e9 58 ff ff ff       	jmp    ffffffff813d25bc <throttle_cfs_rq+0x1ac>

Disassembly of section .data:

Disassembly of section .init.text:

Disassembly of section .altinstr_aux:

Disassembly of section .altinstr_replacement:

Disassembly of section .exit.text:
