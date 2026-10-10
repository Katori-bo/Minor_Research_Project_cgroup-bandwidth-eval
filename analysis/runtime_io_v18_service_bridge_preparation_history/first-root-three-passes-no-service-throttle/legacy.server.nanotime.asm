/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/analysis/runtime_io_v16_repeatability_build/binary_audit/legacy.server:     file format elf64-x86-64


Disassembly of section .text:

000000000048b780 <runtime.nanotime1.abi0>:
  48b780:	55                   	push   %rbp
  48b781:	48 89 e5             	mov    %rsp,%rbp
  48b784:	48 83 ec 10          	sub    $0x10,%rsp
  48b788:	49 89 e4             	mov    %rsp,%r12
  48b78b:	49 8b 5e 30          	mov    0x30(%r14),%rbx
  48b78f:	48 8b 8b 88 03 00 00 	mov    0x388(%rbx),%rcx
  48b796:	48 8b 93 80 03 00 00 	mov    0x380(%rbx),%rdx
  48b79d:	48 89 0c 24          	mov    %rcx,(%rsp)
  48b7a1:	48 89 54 24 08       	mov    %rdx,0x8(%rsp)
  48b7a6:	48 8d 54 24 20       	lea    0x20(%rsp),%rdx
  48b7ab:	48 8b 4a f8          	mov    -0x8(%rdx),%rcx
  48b7af:	48 89 8b 88 03 00 00 	mov    %rcx,0x388(%rbx)
  48b7b6:	48 89 93 80 03 00 00 	mov    %rdx,0x380(%rbx)
  48b7bd:	4c 3b b3 b8 00 00 00 	cmp    0xb8(%rbx),%r14
  48b7c4:	75 07                	jne    48b7cd <runtime.nanotime1.abi0+0x4d>
  48b7c6:	48 8b 13             	mov    (%rbx),%rdx
  48b7c9:	48 8b 62 38          	mov    0x38(%rdx),%rsp
  48b7cd:	48 83 ec 10          	sub    $0x10,%rsp
  48b7d1:	48 83 e4 f0          	and    $0xfffffffffffffff0,%rsp
  48b7d5:	bf 01 00 00 00       	mov    $0x1,%edi
  48b7da:	48 8d 34 24          	lea    (%rsp),%rsi
  48b7de:	48 8b 05 7b 60 56 00 	mov    0x56607b(%rip),%rax        # 9f1860 <runtime.vdsoClockgettimeSym>
  48b7e5:	48 83 f8 00          	cmp    $0x0,%rax
  48b7e9:	74 3a                	je     48b825 <runtime.nanotime1.abi0+0xa5>
  48b7eb:	ff d0                	call   *%rax
  48b7ed:	48 8b 04 24          	mov    (%rsp),%rax
  48b7f1:	48 8b 54 24 08       	mov    0x8(%rsp),%rdx
  48b7f6:	4c 89 e4             	mov    %r12,%rsp
  48b7f9:	48 8b 4c 24 08       	mov    0x8(%rsp),%rcx
  48b7fe:	48 89 8b 80 03 00 00 	mov    %rcx,0x380(%rbx)
  48b805:	48 8b 0c 24          	mov    (%rsp),%rcx
  48b809:	48 89 8b 88 03 00 00 	mov    %rcx,0x388(%rbx)
  48b810:	48 69 c0 00 ca 9a 3b 	imul   $0x3b9aca00,%rax,%rax
  48b817:	48 01 d0             	add    %rdx,%rax
  48b81a:	48 89 44 24 20       	mov    %rax,0x20(%rsp)
  48b81f:	48 83 c4 10          	add    $0x10,%rsp
  48b823:	5d                   	pop    %rbp
  48b824:	c3                   	ret
  48b825:	48 c7 c0 e4 00 00 00 	mov    $0xe4,%rax
  48b82c:	0f 05                	syscall
  48b82e:	eb bd                	jmp    48b7ed <runtime.nanotime1.abi0+0x6d>
