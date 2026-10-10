/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/analysis/runtime_io_v16_repeatability_build/loadgen:     file format elf64-x86-64


Disassembly of section .text:

000000000048b8c0 <runtime.nanotime1.abi0>:
  48b8c0:	55                   	push   %rbp
  48b8c1:	48 89 e5             	mov    %rsp,%rbp
  48b8c4:	48 83 ec 10          	sub    $0x10,%rsp
  48b8c8:	49 89 e4             	mov    %rsp,%r12
  48b8cb:	49 8b 5e 30          	mov    0x30(%r14),%rbx
  48b8cf:	48 8b 8b 88 03 00 00 	mov    0x388(%rbx),%rcx
  48b8d6:	48 8b 93 80 03 00 00 	mov    0x380(%rbx),%rdx
  48b8dd:	48 89 0c 24          	mov    %rcx,(%rsp)
  48b8e1:	48 89 54 24 08       	mov    %rdx,0x8(%rsp)
  48b8e6:	48 8d 54 24 20       	lea    0x20(%rsp),%rdx
  48b8eb:	48 8b 4a f8          	mov    -0x8(%rdx),%rcx
  48b8ef:	48 89 8b 88 03 00 00 	mov    %rcx,0x388(%rbx)
  48b8f6:	48 89 93 80 03 00 00 	mov    %rdx,0x380(%rbx)
  48b8fd:	4c 3b b3 b8 00 00 00 	cmp    0xb8(%rbx),%r14
  48b904:	75 07                	jne    48b90d <runtime.nanotime1.abi0+0x4d>
  48b906:	48 8b 13             	mov    (%rbx),%rdx
  48b909:	48 8b 62 38          	mov    0x38(%rdx),%rsp
  48b90d:	48 83 ec 10          	sub    $0x10,%rsp
  48b911:	48 83 e4 f0          	and    $0xfffffffffffffff0,%rsp
  48b915:	bf 01 00 00 00       	mov    $0x1,%edi
  48b91a:	48 8d 34 24          	lea    (%rsp),%rsi
  48b91e:	48 8b 05 ab 3e 59 00 	mov    0x593eab(%rip),%rax        # a1f7d0 <runtime.vdsoClockgettimeSym>
  48b925:	48 83 f8 00          	cmp    $0x0,%rax
  48b929:	74 3a                	je     48b965 <runtime.nanotime1.abi0+0xa5>
  48b92b:	ff d0                	call   *%rax
  48b92d:	48 8b 04 24          	mov    (%rsp),%rax
  48b931:	48 8b 54 24 08       	mov    0x8(%rsp),%rdx
  48b936:	4c 89 e4             	mov    %r12,%rsp
  48b939:	48 8b 4c 24 08       	mov    0x8(%rsp),%rcx
  48b93e:	48 89 8b 80 03 00 00 	mov    %rcx,0x380(%rbx)
  48b945:	48 8b 0c 24          	mov    (%rsp),%rcx
  48b949:	48 89 8b 88 03 00 00 	mov    %rcx,0x388(%rbx)
  48b950:	48 69 c0 00 ca 9a 3b 	imul   $0x3b9aca00,%rax,%rax
  48b957:	48 01 d0             	add    %rdx,%rax
  48b95a:	48 89 44 24 20       	mov    %rax,0x20(%rsp)
  48b95f:	48 83 c4 10          	add    $0x10,%rsp
  48b963:	5d                   	pop    %rbp
  48b964:	c3                   	ret
  48b965:	48 c7 c0 e4 00 00 00 	mov    $0xe4,%rax
  48b96c:	0f 05                	syscall
  48b96e:	eb bd                	jmp    48b92d <runtime.nanotime1.abi0+0x6d>
